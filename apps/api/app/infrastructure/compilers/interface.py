from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class CompilationRequest(BaseModel):
    workspace_dir: Path
    source_files: List[str]
    output_binary: str = "harness_bin.exe"
    compiler_flags: List[str] = Field(default_factory=lambda: ["-O0", "-g", "--coverage", "-fprofile-arcs", "-ftest-coverage"])
    include_dirs: List[str] = Field(default_factory=lambda: ["."])
    defines: List[str] = Field(default_factory=list)


class CompilationResult(BaseModel):
    success: bool
    compiler_name: str
    compiler_version: str
    command: List[str]
    command_str: str
    exit_code: int
    stdout: str
    stderr: str
    output_binary_path: Optional[Path] = None
    generated_artifacts: List[Path] = Field(default_factory=list)


class ICompilerProvider(ABC):
    @abstractmethod
    def compile(self, req: CompilationRequest) -> CompilationResult:
        """Compiles C/C++ source and harness files into an executable binary with coverage flags."""
        pass

