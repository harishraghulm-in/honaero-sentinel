from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from apps.api.app.domain.enums import ExecutionStatus


class ExecutionRequest(BaseModel):
    execution_id: str
    source_files: Dict[str, str]  # filename -> content
    harness_content: str
    stub_header_content: Optional[str] = None
    stub_source_content: Optional[str] = None
    timeout_seconds: int = 10
    compiler_flags: List[str] = Field(default_factory=lambda: ["-O0", "-g", "--coverage", "-fprofile-arcs", "-ftest-coverage"])


class ExecutionArtifactMeta(BaseModel):
    artifact_type: str
    filename: str
    file_path: str
    file_size_bytes: int
    checksum_sha256: str


class ExecutionResult(BaseModel):
    execution_id: str
    status: ExecutionStatus
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    command: List[str] = Field(default_factory=list)
    results_json: Optional[Dict[str, Any]] = None
    artifacts: List[ExecutionArtifactMeta] = Field(default_factory=list)
    workspace_dir: str


class IExecutionEngine(ABC):
    @abstractmethod
    def execute(self, req: ExecutionRequest) -> ExecutionResult:
        """Executes a verification run in an isolated environment."""
        pass

