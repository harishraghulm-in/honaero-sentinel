from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class NormalizedParameter(BaseModel):
    name: str
    type: str
    is_pointer: bool = False
    is_array: bool = False


class NormalizedCondition(BaseModel):
    id: str  # e.g., C1, C2
    expression: str
    variable_references: List[str] = Field(default_factory=list)


class NormalizedDecision(BaseModel):
    id: str  # e.g., D1
    expression: str
    line_number: Optional[int] = None
    conditions: List[NormalizedCondition] = Field(default_factory=list)


class NormalizedDependency(BaseModel):
    name: str
    type: str = "external_function"
    return_type: str = "void"
    parameters: List[NormalizedParameter] = Field(default_factory=list)
    call_line_numbers: List[int] = Field(default_factory=list)


class NormalizedFunction(BaseModel):
    name: str
    return_type: str
    parameters: List[NormalizedParameter] = Field(default_factory=list)
    local_variables: List[Dict[str, str]] = Field(default_factory=list)
    decisions: List[NormalizedDecision] = Field(default_factory=list)
    dependencies: List[NormalizedDependency] = Field(default_factory=list)
    start_line: Optional[int] = None
    end_line: Optional[int] = None


class SourceAnalysisResult(BaseModel):
    filename: str
    checksum_sha256: str
    functions: List[NormalizedFunction] = Field(default_factory=list)
    global_variables: List[Dict[str, str]] = Field(default_factory=list)
    external_declarations: List[str] = Field(default_factory=list)


class ISourceParser(ABC):
    @abstractmethod
    def parse_source(self, filename: str, content: str) -> SourceAnalysisResult:
        """Parses C/C++ source code into a normalized Sentinel AST representation."""
        pass

