from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class LineCoverageDetail(BaseModel):
    line_number: int
    count: int
    branches: List[Dict[str, Any]] = Field(default_factory=list)


class CoverageReport(BaseModel):
    target_file: str
    statement_coverage_pct: float = 0.0
    branch_coverage_pct: float = 0.0
    function_coverage_pct: float = 0.0
    line_coverage_pct: float = 0.0
    total_lines: int = 0
    covered_lines: int = 0
    total_branches: int = 0
    covered_branches: int = 0
    lines_detail: List[LineCoverageDetail] = Field(default_factory=list)
    raw_artifact_path: Optional[str] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class ICoverageProvider(ABC):
    @abstractmethod
    def parse_coverage(self, workspace_dir: Path, target_source_file: str) -> CoverageReport:
        """Parses raw compiler coverage artifacts into structured line and branch metrics."""
        pass

