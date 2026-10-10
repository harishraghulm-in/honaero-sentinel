import os
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional

from apps.api.app.infrastructure.compilers.interface import (
    ICompilerProvider,
    CompilationRequest,
    CompilationResult,
)
from apps.api.app.core.config import get_settings


class GccCompilerProvider(ICompilerProvider):
    def __init__(self, gcc_path: Optional[str] = None):
        settings = get_settings()
        self.gcc_path = gcc_path or settings.GCC_PATH
        if not Path(self.gcc_path).exists() and not shutil.which(self.gcc_path):
            # Fallback to system PATH gcc if default path doesn't exist
            system_gcc = shutil.which("gcc")
            if system_gcc:
                self.gcc_path = system_gcc

    def _get_version(self) -> str:
        try:
            res = subprocess.run([self.gcc_path, "--version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return res.stdout.splitlines()[0]
            return f"GCC (code {res.returncode})"
        except Exception as e:
            return f"Unknown GCC ({str(e)})"

    def compile(self, req: CompilationRequest) -> CompilationResult:
        compiler_version = self._get_version()
        out_bin = req.workspace_dir / req.output_binary

        cmd = [self.gcc_path]
        cmd.extend(req.compiler_flags)

        for inc in req.include_dirs:
            cmd.extend(["-I", str(inc)])

        for d in req.defines:
            cmd.append(f"-D{d}")

        for sf in req.source_files:
            cmd.append(str(sf))

        cmd.extend(["-o", str(req.output_binary)])

        cmd_str = " ".join(cmd)

        env = os.environ.copy()
        gcc_parent = str(Path(self.gcc_path).parent.resolve())
        env["PATH"] = f"{gcc_parent};{env.get('PATH', '')}"

        try:
            process = subprocess.run(
                cmd,
                cwd=str(req.workspace_dir),
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            success = (process.returncode == 0) and out_bin.exists()
            artifacts: List[Path] = []
            if success:
                artifacts.append(out_bin)
                # Look for .gcno files
                for f in req.workspace_dir.glob("*.gcno"):
                    artifacts.append(f)

            return CompilationResult(
                success=success,
                compiler_name="gcc",
                compiler_version=compiler_version,
                command=cmd,
                command_str=cmd_str,
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                output_binary_path=out_bin if success else None,
                generated_artifacts=artifacts,
            )
        except subprocess.TimeoutExpired:
            return CompilationResult(
                success=False,
                compiler_name="gcc",
                compiler_version=compiler_version,
                command=cmd,
                command_str=cmd_str,
                exit_code=-1,
                stdout="",
                stderr="Compilation timed out after 30 seconds",
                output_binary_path=None,
                generated_artifacts=[],
            )
        except Exception as e:
            return CompilationResult(
                success=False,
                compiler_name="gcc",
                compiler_version=compiler_version,
                command=cmd,
                command_str=cmd_str,
                exit_code=-1,
                stdout="",
                stderr=f"Compilation execution failed: {str(e)}",
                output_binary_path=None,
                generated_artifacts=[],
            )
