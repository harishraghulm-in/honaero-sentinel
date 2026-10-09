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
    content: Optional[str] = None
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
    id: Optional[str] = None
    project_id: str
    total_sources: int
    functions: List[FunctionDTO] = Field(default_factory=list)
    dependencies: List[DependencyDTO] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_id(self) -> "AnalysisResponse":
        if not self.id:
            self.id = self.project_id
        return self


# --- Scope ---
class ScopeSetRequest(BaseModel):
    target_function_id: Optional[str] = None
    target_source_id: Optional[str] = None
    environment_source_ids: List[str] = Field(default_factory=list)
    selectedFunctions: Optional[List[str]] = None
    selected_functions: Optional[List[str]] = None


class ScopeResponse(BaseModel):
    id: Optional[str] = None
    project_id: str
    target_function_name: Optional[str]
    target_source_filename: Optional[str]
    environment_sources: List[str] = Field(default_factory=list)
    selected_functions: List[str] = Field(default_factory=list)
    selectedFunctions: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_fields(self) -> "ScopeResponse":
        if not self.id:
            self.id = self.project_id
        if self.target_function_name and not self.selected_functions:
            self.selected_functions = [self.target_function_name]
        if not self.selectedFunctions and self.selected_functions:
            self.selectedFunctions = list(self.selected_functions)
        elif not self.selected_functions and self.selectedFunctions:
            self.selected_functions = list(self.selectedFunctions)
        return self


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
    suiteId: Optional[str] = None
    vectors: List[VectorInputDTO] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_suite_id(self) -> "TestCaseCreate":
        if not self.test_suite_id and self.suiteId:
            self.test_suite_id = self.suiteId
        return self


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
    test_case_id: Optional[str] = None
    timeout_seconds: int = 10
    compiler_flags: List[str] = Field(default_factory=lambda: ["-O0", "-g", "--coverage", "-fprofile-arcs", "-ftest-coverage"])
    pressure: Optional[int] = None
    altitude: Optional[int] = None
    inputs: Optional[Dict[str, Any]] = None


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
    statement: Optional[float] = None
    decision: Optional[float] = None
    raw_artifact: Optional[str] = None

    @model_validator(mode="after")
    def sync_frontend_coverage(self) -> "CoverageResponse":
        if self.statement is None:
            self.statement = self.statement_coverage_pct
        if self.decision is None:
            self.decision = self.branch_coverage_pct
        return self


class MCDCResponse(BaseModel):
    execution_id: str
    coverage_percentage: float
    decisions: List[Dict[str, Any]]
    gap_recommendations: List[Dict[str, Any]]


class EvidenceResponse(BaseModel):
    evidence_id: str
    id: Optional[str] = None
    project_id: str
    execution_id: str
    freshness: EvidenceFreshness
    source_checksum: str
    stub_checksum: Optional[str]
    vector_checksum: Optional[str]
    tool_version: str
    evidence_data: Dict[str, Any]
    generatedAt: Optional[str] = None
    created_at: datetime

    @model_validator(mode="after")
    def sync_evidence_fields(self) -> "EvidenceResponse":
        if not self.id:
            self.id = self.evidence_id
        if not self.generatedAt:
            self.generatedAt = self.created_at.isoformat()
        return self


# --- Requirements & Document Ingestion ---
class RequirementDocumentUpload(BaseModel):
    filename: str
    content: str
    file_type: Optional[str] = None
    revision: str = "1.0"


class RequirementDocumentResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_type: str
    checksum_sha256: str
    revision: str
    content: Optional[str] = None
    created_at: datetime


class RequirementCreate(BaseModel):
    identifier: str
    title: str
    description: str
    req_type: RequirementType = RequirementType.HLR
    document_id: Optional[str] = None
    section: Optional[str] = None
    page_or_line: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    verification_method: Optional[str] = "TEST"
    ambiguity_status: str = "CLEAR"
    ambiguity_notes: Optional[str] = None
    review_status: str = "DRAFT"
    revision: str = "1.0"


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    req_type: Optional[RequirementType] = None
    section: Optional[str] = None
    page_or_line: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    verification_method: Optional[str] = None
    ambiguity_status: Optional[str] = None
    ambiguity_notes: Optional[str] = None
    review_status: Optional[str] = None


class RequirementResponse(BaseModel):
    id: str
    project_id: str
    document_id: Optional[str] = None
    identifier: str
    title: str
    description: str
    req_type: RequirementType
    section: Optional[str] = None
    page_or_line: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    verification_method: Optional[str] = "TEST"
    ambiguity_status: str
    ambiguity_notes: Optional[str] = None
    review_status: str
    revision: str
    created_at: datetime


class CandidateTestCaseResponse(BaseModel):
    __test__ = False
    id: str
    project_id: str
    requirement_id: str
    target_function_name: Optional[str] = None
    name: str
    case_category: str
    rationale: str
    preconditions: Dict[str, Any] = Field(default_factory=dict)
    input_vectors: List[Dict[str, Any]] = Field(default_factory=list)
    expected_outputs: Dict[str, Any] = Field(default_factory=dict)
    is_expected_result_uncertain: bool
    uncertainty_reason: Optional[str] = None
    provenance: str
    approval_status: str
    approved_test_case_id: Optional[str] = None
    created_at: datetime


class CandidateApprovalRequest(BaseModel):
    target_function_id: Optional[str] = None
    test_suite_id: Optional[str] = None


# --- Source Archive Import ---
class SourceArchiveImportRequest(BaseModel):
    filename: str = "project_source.zip"
    archive_base64: str
    overwrite: bool = False


class SourceArchiveImportResponse(BaseModel):
    total_files_in_archive: int
    imported_sources: int
    skipped_files: int
    files: List[SourceResponse] = Field(default_factory=list)


# --- Traceability Links & Matrix ---
class TraceabilitySuggestionRequest(BaseModel):
    confidence_threshold: float = 0.4


class TraceabilityLinkCreate(BaseModel):
    requirement_id: str
    function_id: Optional[str] = None
    test_case_id: Optional[str] = None
    status: str = "CONFIRMED"
    confidence_score: float = 1.0
    rationale: Optional[str] = None


class TraceabilityLinkResponse(BaseModel):
    id: str
    project_id: str
    requirement_id: str
    function_id: Optional[str] = None
    test_case_id: Optional[str] = None
    execution_id: Optional[str] = None
    evidence_id: Optional[str] = None
    status: str
    confidence_score: float
    rationale: Optional[str] = None
    source_location: Optional[str] = None
    created_at: datetime


class TraceabilityMatrixItem(BaseModel):
    requirement: RequirementResponse
    linked_functions: List[Dict[str, Any]] = Field(default_factory=list)
    candidate_test_cases: List[CandidateTestCaseResponse] = Field(default_factory=list)
    test_cases: List[TestCaseResponse] = Field(default_factory=list)
    executions: List[ExecutionResponse] = Field(default_factory=list)
    evidence: Optional[Dict[str, Any]] = None


class TraceabilityMatrixResponse(BaseModel):
    project_id: str
    matrix: List[TraceabilityMatrixItem] = Field(default_factory=list)
