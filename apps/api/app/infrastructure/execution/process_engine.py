import os
import sys
import time
import json
import hashlib
import subprocess
from pathlib import Path
from typing import List, Optional

from apps.api.app.core.config import get_settings
from apps.api.app.domain.enums import ExecutionStatus
from apps.api.app.infrastructure.compilers.gcc import GccCompilerProvider
from apps.api.app.infrastructure.compilers.interface import CompilationRequest
from apps.api.app.infrastructure.execution.interface import (
    IExecutionEngine,
    ExecutionRequest,
    ExecutionResult,
    ExecutionArtifactMeta,
)


class LocalProcessExecutionEngine(IExecutionEngine):
    def __init__(self, compiler: Optional[GccCompilerProvider] = None):
        self.compiler = compiler or GccCompilerProvider()
        self.settings = get_settings()

    def execute(self, req: ExecutionRequest) -> ExecutionResult:
        workspace_dir = self.settings.WORKSPACE_BASE_PATH / req.execution_id
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write source files
        source_filenames = []
        include_dirs = ["."]
        for fname, content in req.source_files.items():
            fpath = workspace_dir / fname
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")
            ext = fpath.suffix.lower()
            if ext in [".c", ".cpp", ".cc", ".cxx"]:
                source_filenames.append(fname)
            elif ext in [".h", ".hpp", ".hh", ".hxx"]:
                # Mirror header into workspace root so -I . resolves both bare and subpath includes cleanly
                root_header = workspace_dir / fpath.name
                if not root_header.exists():
                    root_header.write_text(content, encoding="utf-8")

        # 2. Write stubs if provided
        if req.stub_header_content and req.stub_source_content:
            (workspace_dir / "generated_stubs.h").write_text(req.stub_header_content, encoding="utf-8")
            (workspace_dir / "generated_stubs.c").write_text(req.stub_source_content, encoding="utf-8")
            source_filenames.append("generated_stubs.c")

        # 3. Write test harness
        harness_filename = "test_harness.c"
        (workspace_dir / harness_filename).write_text(req.harness_content, encoding="utf-8")
        source_filenames.append(harness_filename)

        # 4. Compile with GCC
        is_windows = os.name == "nt"
        output_name = "harness.exe" if is_windows else "harness_bin"
        compiler_flags = list(req.compiler_flags)
        if is_windows:
            compiler_flags.extend(["-static-libgcc"])

        comp_req = CompilationRequest(
            workspace_dir=workspace_dir,
            source_files=source_filenames,
            output_binary=output_name,
            compiler_flags=compiler_flags,
            include_dirs=include_dirs,
        )
        comp_result = self.compiler.compile(comp_req)

        artifacts: List[ExecutionArtifactMeta] = []

        if not comp_result.success:
            # Record build failure logs
            stdout_path = workspace_dir / "build_stdout.log"
            stderr_path = workspace_dir / "build_stderr.log"
            stdout_path.write_text(comp_result.stdout, encoding="utf-8")
            stderr_path.write_text(comp_result.stderr, encoding="utf-8")

            artifacts.append(self._create_artifact_meta(stderr_path, "build_stderr"))
            return ExecutionResult(
                execution_id=req.execution_id,
                status=ExecutionStatus.BUILD_FAILED,
                exit_code=comp_result.exit_code,
                stdout=comp_result.stdout,
                stderr=comp_result.stderr,
                command=comp_result.command,
                duration_ms=0.0,
                workspace_dir=str(workspace_dir),
                artifacts=artifacts,
            )

        # 5. Execute harness in isolated worker process
        bin_path = comp_result.output_binary_path
        start_time = time.perf_counter()
        proc_exit_code = None
        stdout_str = ""
        stderr_str = ""
        exec_status = ExecutionStatus.RUNNING

        try:
            gcc_parent = str(Path(self.compiler.gcc_path).parent.resolve())
            env = os.environ.copy()
            env["PATH"] = f"{gcc_parent};{env.get('PATH', '')}"

            cmd = [str(bin_path)]

            proc = subprocess.run(
                cmd,
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=req.timeout_seconds,
                env=env,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            proc_exit_code = proc.returncode
            stdout_str = proc.stdout
            stderr_str = proc.stderr

            # Check JSON results file
            result_json_path = workspace_dir / "sentinel_result.json"
            results_data = None
            if result_json_path.exists():
                try:
                    results_data = json.loads(result_json_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

            if proc_exit_code == 0 and (results_data is None or results_data.get("status") == "PASSED"):
                exec_status = ExecutionStatus.PASSED
            else:
                exec_status = ExecutionStatus.FAILED

        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            exec_status = ExecutionStatus.TIMEOUT
            stderr_str = f"Execution timed out after {req.timeout_seconds} seconds"
            results_data = None

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            exec_status = ExecutionStatus.ERROR
            stderr_str = f"Execution failed with internal error: {str(e)}"
            results_data = None

        # 6. Collect generated artifacts
        stdout_file = workspace_dir / "stdout.log"
        stderr_file = workspace_dir / "stderr.log"
        stdout_file.write_text(stdout_str, encoding="utf-8")
        stderr_file.write_text(stderr_str, encoding="utf-8")

        artifacts.append(self._create_artifact_meta(stdout_file, "stdout"))
        artifacts.append(self._create_artifact_meta(stderr_file, "stderr"))

        if bin_path and bin_path.exists():
            artifacts.append(self._create_artifact_meta(bin_path, "binary"))

        for f in workspace_dir.glob("*.gcno"):
            artifacts.append(self._create_artifact_meta(f, "gcno"))

        for f in workspace_dir.glob("*.gcda"):
            artifacts.append(self._create_artifact_meta(f, "gcda"))

        res_json = workspace_dir / "sentinel_result.json"
        if res_json.exists():
            artifacts.append(self._create_artifact_meta(res_json, "result_json"))

        return ExecutionResult(
            execution_id=req.execution_id,
            status=exec_status,
            exit_code=proc_exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            duration_ms=duration_ms,
            command=[str(bin_path)],
            results_json=results_data,
            artifacts=artifacts,
            workspace_dir=str(workspace_dir),
        )

    def _create_artifact_meta(self, file_path: Path, artifact_type: str) -> ExecutionArtifactMeta:
        content = file_path.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        return ExecutionArtifactMeta(
            artifact_type=artifact_type,
            filename=file_path.name,
            file_path=str(file_path.resolve()),
            file_size_bytes=len(content),
            checksum_sha256=checksum,
        )
