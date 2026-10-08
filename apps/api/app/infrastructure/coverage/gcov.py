import gzip
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

from apps.api.app.core.config import get_settings
from apps.api.app.infrastructure.coverage.interface import (
    ICoverageProvider,
    CoverageReport,
    LineCoverageDetail,
)


class GcovCoverageProvider(ICoverageProvider):
    def __init__(self, gcov_path: Optional[str] = None):
        settings = get_settings()
        self.gcov_path = gcov_path or settings.GCOV_PATH
        if not Path(self.gcov_path).exists() and not shutil.which(self.gcov_path):
            system_gcov = shutil.which("gcov")
            if system_gcov:
                self.gcov_path = system_gcov

    def parse_coverage(self, workspace_dir: Path, target_source_file: str) -> CoverageReport:
        # Find matching .gcno file for target
        clean_target_name = Path(target_source_file).name
        target_stem = Path(target_source_file).stem

        gcno_files = list(workspace_dir.glob("*.gcno"))
        matched_gcno = None
        for gf in gcno_files:
            if target_stem in gf.name:
                matched_gcno = gf
                break

        if not matched_gcno and gcno_files:
            matched_gcno = gcno_files[0]

        if not matched_gcno:
            return CoverageReport(target_file=target_source_file)

        # Run gcov with json-format, branch probabilities (-b), and counts (-c)
        env = os.environ.copy()
        gcov_parent = str(Path(self.gcov_path).parent.resolve())
        env["PATH"] = f"{gcov_parent};{env.get('PATH', '')}"

        cmd = [self.gcov_path, "-b", "-c", "--json-format", matched_gcno.name]
        try:
            subprocess.run(
                cmd,
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )
        except Exception:
            pass

        # Look for .gcov.json.gz or .gcov.json in workspace
        json_gz_files = list(workspace_dir.glob("*.gcov.json.gz"))
        json_files = list(workspace_dir.glob("*.gcov.json"))

        target_json_data: Optional[Dict[str, Any]] = None
        raw_artifact_path = None

        for jgz in json_gz_files:
            if target_stem in jgz.name or not target_json_data:
                try:
                    with gzip.open(jgz, "rt", encoding="utf-8") as f:
                        data = json.load(f)
                        raw_artifact_path = str(jgz.resolve())
                        target_json_data = data
                except Exception:
                    continue

        if not target_json_data and json_files:
            try:
                target_json_data = json.loads(json_files[0].read_text(encoding="utf-8"))
                raw_artifact_path = str(json_files[0].resolve())
            except Exception:
                pass

        if not target_json_data:
            # Fallback to parsing text output if json format unsupported
            return self._parse_text_fallback(workspace_dir, clean_target_name)

        return self._extract_from_json(target_json_data, clean_target_name, raw_artifact_path)

    def _extract_from_json(self, data: Dict[str, Any], target_file: str, raw_path: Optional[str]) -> CoverageReport:
        files_data = data.get("files", [])
        matched_file_data = None
        for fd in files_data:
            if Path(fd.get("file", "")).name == target_file:
                matched_file_data = fd
                break

        if not matched_file_data and files_data:
            matched_file_data = files_data[0]

        if not matched_file_data:
            return CoverageReport(target_file=target_file, raw_artifact_path=raw_path, raw_data=data)

        lines_list = matched_file_data.get("lines", [])
        total_executable_lines = len(lines_list)
        executed_lines = sum(1 for l in lines_list if l.get("count", 0) > 0)

        total_branches = 0
        covered_branches = 0
        lines_detail: List[LineCoverageDetail] = []

        for l in lines_list:
            ln_no = l.get("line_number", 0)
            cnt = l.get("count", 0)
            branches = l.get("branches", [])
            lines_detail.append(LineCoverageDetail(
                line_number=ln_no,
                count=cnt,
                branches=branches
            ))
            for b in branches:
                total_branches += 1
                if b.get("count", 0) > 0:
                    covered_branches += 1

        functions_list = matched_file_data.get("functions", [])
        total_funcs = len(functions_list)
        covered_funcs = sum(1 for fn in functions_list if fn.get("execution_count", 0) > 0)

        line_pct = (executed_lines / total_executable_lines * 100.0) if total_executable_lines > 0 else 0.0
        stmt_pct = line_pct  # Executable statements align with executable statement lines in GCC C
        branch_pct = (covered_branches / total_branches * 100.0) if total_branches > 0 else 100.0
        func_pct = (covered_funcs / total_funcs * 100.0) if total_funcs > 0 else 100.0

        return CoverageReport(
            target_file=target_file,
            statement_coverage_pct=round(stmt_pct, 2),
            branch_coverage_pct=round(branch_pct, 2),
            function_coverage_pct=round(func_pct, 2),
            line_coverage_pct=round(line_pct, 2),
            total_lines=total_executable_lines,
            covered_lines=executed_lines,
            total_branches=total_branches,
            covered_branches=covered_branches,
            lines_detail=lines_detail,
            raw_artifact_path=raw_path,
            raw_data=matched_file_data,
        )

    def _parse_text_fallback(self, workspace_dir: Path, target_file: str) -> CoverageReport:
        # Standard .gcov text file fallback parsing
        gcov_txt = list(workspace_dir.glob("*.gcov"))
        if not gcov_txt:
            return CoverageReport(target_file=target_file)
        
        lines_detail: List[LineCoverageDetail] = []
        total_lines = 0
        covered_lines = 0

        for line in gcov_txt[0].read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split(":", 2)
            if len(parts) >= 2:
                count_str = parts[0].strip()
                try:
                    line_no = int(parts[1].strip())
                    if count_str == "-":
                        continue
                    total_lines += 1
                    if count_str != "#####":
                        cnt = int(count_str)
                        covered_lines += 1
                    else:
                        cnt = 0
                    lines_detail.append(LineCoverageDetail(line_number=line_no, count=cnt))
                except ValueError:
                    continue

        line_pct = (covered_lines / total_lines * 100.0) if total_lines > 0 else 0.0
        return CoverageReport(
            target_file=target_file,
            statement_coverage_pct=round(line_pct, 2),
            branch_coverage_pct=100.0,
            function_coverage_pct=100.0,
            line_coverage_pct=round(line_pct, 2),
            total_lines=total_lines,
            covered_lines=covered_lines,
            lines_detail=lines_detail,
        )

