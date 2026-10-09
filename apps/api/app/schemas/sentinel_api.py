from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

from apps.api.app.domain.enums import (
    DependencyMode,
    DependencyType,
    ExecutionStatus,
    EvidenceFreshness,
    RequirementType,
)


# --- Projects ---
class ProjectCreate(BaseModel):
    name: str = Field(..., examples=["Cabin Pressure Controller"])
    description: Optional[str] = Field(None, examples=["Honeywell DO-178C Verification Target"])


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


# --- Sources ---
class SourceCreate(BaseModel):
    filename: str = Field(..., examples=["cabin_pressure.c"])
    filepath: Optional[str] = Field(None, examples=["src/cabin_pressure.c"])
    content: str = Field(..., examples=["int cabin_pressure_control(int pressure, int altitude) { return 0; }"])
    is_target: bool = False
    is_environment: bool = False


class SourceResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    filepath: str
    checksum_sha256: str
    is_target: bool
    is_environment: bool
    created_at: datetime


# --- Analysis ---
class ConditionDTO(BaseModel):
    id: str
    expression: str
    variable_references: List[str] = Field(default_factory=list)


class DecisionDTO(BaseModel):
    id: str
    expression: str
    line_number: Optional[int] = None
    conditions: List[ConditionDTO] = Field(default_factory=list)


class ParameterDTO(BaseModel):
    name: str
    type: str
    is_pointer: bool = False
    is_array: bool = False


class FunctionDTO(BaseModel):
    id: str
    name: str
    return_type: str
    parameters: List[ParameterDTO] = Field(default_factory=list)
    decisions: List[DecisionDTO] = Field(default_factory=list)
    is_target_under_test: bool = False


class DependencyDTO(BaseModel):
    id: str
    name: str
    type: str
    return_type: str
    mode: DependencyMode


class AnalysisResponse(BaseModel):
    project_id: str
    total_sources: int
    functions: List[FunctionDTO] = Field(default_factory=list)
    dependencies: List[DependencyDTO] = Field(default_factory=list)


# --- Scope ---
class ScopeSetRequest(BaseModel):
    target_function_id: str
    target_source_id: str
    environment_source_ids: List[str] = Field(default_factory=list)


class ScopeResponse(BaseModel):
    project_id: str
    target_function_name: Optional[str]
    target_source_filename: Optional[str]
    environment_sources: List[str] = Field(default_factory=list)


# --- Stubs ---
class StubCreate(BaseModel):
    dependency_id: str
    function_name: str
    mode: DependencyMode = DependencyMode.STUB
    return_values: List[Any] = Field(default_factory=list)
    output_params: Dict[str, Any] = Field(default_factory=dict)
    expected_call_count: Optional[int] = None
    call_order: Optional[int] = None
    custom_c_body: Optional[str] = None


class StubUpdate(BaseModel):
    mode: Optional[DependencyMode] = None
    return_values: Optional[List[Any]] = None
    output_params: Optional[Dict[str, Any]] = None
    expected_call_count: Optional[int] = None
    call_order: Optional[int] = None
    custom_c_body: Optional[str] = None


class StubResponse(BaseModel):
    id: str
    project_id: str
    dependency_id: str
    function_name: str
    mode: DependencyMode
    return_values: List[Any]
    output_params: Dict[str, Any]
    expected_call_count: Optional[int]
    created_at: datetime


# --- Tests & Vectors ---
class VectorInputDTO(BaseModel):
    __test__ = False
    vector_index: int
    inputs: Dict[str, Any]
    expected_outputs: Dict[str, Any]


class TestSuiteCreate(BaseModel):
    __test__ = False
    name: str
    description: Optional[str] = None


class TestSuiteResponse(BaseModel):
    __test__ = False
    id: str
    project_id: str
    name: str
    description: Optional[str]


class TestCaseCreate(BaseModel):
    __test__ = False
    name: str
    target_function_id: str
    requirement_id: Optional[str] = None
    test_suite_id: Optional[str] = None
    vectors: List[VectorInputDTO] = Field(default_factory=list)


class TestCaseResponse(BaseModel):
    __test__ = False
    id: str
    project_id: str
    name: str
    target_function_id: Optional[str]
    requirement_id: Optional[str]
    vectors_count: int
    created_at: datetime


# --- Executions ---
class ExecutionCreate(BaseModel):
    test_case_id: str
    timeout_seconds: int = 10
    compiler_flags: List[str] = Field(default_factory=lambda: ["-O0", "-g", "--coverage", "-fprofile-arcs", "-ftest-coverage"])


class ExecutionResponse(BaseModel):
    id: Optional[str] = None
    execution_id: Optional[str] = None
    project_id: str
    test_case_id: Optional[str] = None
    status: ExecutionStatus
    exit_code: Optional[int] = None
    duration_ms: Optional[float] = None
    results_summary: Dict[str, Any]
    created_at: datetime

    @model_validator(mode="after")
    def sync_id_and_execution_id(self) -> "ExecutionResponse":
        if not self.id and self.execution_id:
            self.id = self.execution_id
        elif not self.execution_id and self.id:
            self.execution_id = self.id
        elif not self.id and not self.execution_id:
            raise ValueError("Either id or execution_id must be provided")
        elif self.id != self.execution_id:
            self.id = self.execution_id
        return self


# --- Coverage, MCDC, Traceability, Evidence ---
class CoverageResponse(BaseModel):
    execution_id: str
    statement_coverage_pct: float
    branch_coverage_pct: float
    function_coverage_pct: float
    line_coverage_pct: float
    total_lines: int
    covered_lines: int
    total_branches: int
    covered_branches: int
    raw_artifact: Optional[str] = None


class MCDCResponse(BaseModel):
    execution_id: str
    coverage_percentage: float
    decisions: List[Dict[str, Any]]
    gap_recommendations: List[Dict[str, Any]]


class EvidenceResponse(BaseModel):
    evidence_id: str
    project_id: str
    execution_id: str
    freshness: EvidenceFreshness
    source_checksum: str
    stub_checksum: Optional[str]
    vector_checksum: Optional[str]
    tool_version: str
    evidence_data: Dict[str, Any]
    created_at: datetime
