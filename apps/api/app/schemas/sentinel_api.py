import uuid
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
    file: Optional[str] = ""
    isResolved: bool = True


class DiagnosticDTO(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file: str
    line: int
    column: Optional[int] = 1
    severity: str = "info"
    message: str


class AnalysisJobDTO(BaseModel):
    status: str = "completed"
    progress: int = 100
    currentFile: Optional[str] = None
    currentLine: Optional[int] = None


class AnalysisResponse(BaseModel):
    id: Optional[str] = None
    project_id: str
    total_sources: int
    functions: List[FunctionDTO] = Field(default_factory=list)
    dependencies: List[DependencyDTO] = Field(default_factory=list)
    job: Optional[AnalysisJobDTO] = Field(default_factory=lambda: AnalysisJobDTO(status="completed", progress=100))
    diagnostics: List[DiagnosticDTO] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_id(self) -> "AnalysisResponse":
        if not self.id:
            self.id = self.project_id
        if not self.job:
            self.job = AnalysisJobDTO(status="completed", progress=100)
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
    target_function_id: Optional[str] = None
    functionId: Optional[str] = None
    requirement_id: Optional[str] = None
    test_suite_id: Optional[str] = None
    suiteId: Optional[str] = None
    vectors: List[VectorInputDTO] = Field(default_factory=list)
    inputs: Optional[Dict[str, Any]] = None
    expected_outputs: Optional[Dict[str, Any]] = None
    expectedResults: Optional[Any] = None

    @model_validator(mode="after")
    def sync_suite_and_vectors(self) -> "TestCaseCreate":
        if not self.test_suite_id and self.suiteId:
            self.test_suite_id = self.suiteId
        if not self.target_function_id and self.functionId:
            self.target_function_id = self.functionId
        if not self.vectors and (self.inputs is not None or self.expected_outputs is not None or self.expectedResults is not None):
            exp_out = dict(self.expected_outputs or {})
            if not exp_out and self.expectedResults:
                if isinstance(self.expectedResults, list):
                    for item in self.expectedResults:
                        if isinstance(item, dict) and "name" in item and "value" in item:
                            exp_out[item["name"]] = item["value"]
                elif isinstance(self.expectedResults, dict):
                    exp_out = dict(self.expectedResults)
            self.vectors = [VectorInputDTO(
                vector_index=1,
                inputs=self.inputs or {},
                expected_outputs=exp_out
            )]
        return self


class TestCaseResponse(BaseModel):
    __test__ = False
    id: str
    project_id: str
    name: str
    target_function_id: Optional[str] = None
    functionId: Optional[str] = None
    requirement_id: Optional[str] = None
    test_suite_id: Optional[str] = None
    suiteId: Optional[str] = None
    vectors_count: int = 0
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    expectedResults: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime

    @model_validator(mode="after")
    def sync_ids(self) -> "TestCaseResponse":
        if not self.functionId:
            self.functionId = self.target_function_id
        if not self.suiteId:
            self.suiteId = self.test_suite_id
        return self


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
    testCaseId: Optional[str] = None
    test_suite_id: Optional[str] = None
    status: Any = ExecutionStatus.QUEUED
    verdict: Optional[str] = None
    exit_code: Optional[int] = None
    exitCode: Optional[int] = None
    duration_ms: Optional[float] = None
    results_summary: Dict[str, Any] = Field(default_factory=dict)
    expectedResult: Optional[str] = None
    actualResult: Optional[str] = None
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    logs: Optional[str] = None
    compilerOutput: Optional[str] = None
    compiler_output: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    crashed: bool = False
    timeout: bool = False
    timestamp: Optional[str] = None
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

        if not self.testCaseId and self.test_case_id:
            self.testCaseId = self.test_case_id
        if self.exitCode is None and self.exit_code is not None:
            self.exitCode = self.exit_code
        if not self.timestamp and self.created_at:
            self.timestamp = self.created_at.isoformat()

        # Extract expected and actual result from results_summary
        if self.results_summary and isinstance(self.results_summary, dict):
            vectors = self.results_summary.get("vectors", [])
            if vectors and isinstance(vectors, list) and len(vectors) > 0:
                first_v = vectors[0]
                if self.expectedResult is None and "expected" in first_v:
                    self.expectedResult = str(first_v["expected"])
                    self.expected_result = self.expectedResult
                if self.actualResult is None and "actual" in first_v:
                    self.actualResult = str(first_v["actual"])
                    self.actual_result = self.actualResult

        # Populate logs
        if not self.logs:
            out_parts = []
            if self.stdout:
                out_parts.append(f"[STDOUT]\n{self.stdout.strip()}")
            if self.stderr:
                out_parts.append(f"[STDERR]\n{self.stderr.strip()}")
            if out_parts:
                self.logs = "\n\n".join(out_parts)
            elif self.compilerOutput:
                self.logs = self.compilerOutput

        # Explicit verdicts mapping (PASS, FAIL, INCONCLUSIVE, ERROR, NOT RUN)
        status_val = self.status.value if hasattr(self.status, "value") else str(self.status)
        if status_val in ("PASSED", "PASS"):
            self.verdict = "PASS"
        elif status_val in ("FAILED", "FAIL"):
            self.verdict = "FAIL"
        elif status_val in ("BUILD_FAILED", "ERROR"):
            self.verdict = "ERROR"
            self.crashed = True
            if not self.compilerOutput and self.stderr:
                self.compilerOutput = self.stderr
        elif status_val == "TIMEOUT":
            self.verdict = "ERROR"
            self.timeout = True
        elif status_val in ("QUEUED", "BUILDING", "RUNNING"):
            self.verdict = "NOT RUN"
        else:
            self.verdict = "INCONCLUSIVE"

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
    branch: Optional[float] = None
    function: Optional[float] = None
    decision: Optional[float] = None
    available: bool = True
    raw_artifact: Optional[str] = None

    @model_validator(mode="after")
    def sync_frontend_coverage(self) -> "CoverageResponse":
        if self.statement is None:
            self.statement = self.statement_coverage_pct
        if self.branch is None:
            self.branch = self.branch_coverage_pct
        if self.function is None:
            self.function = self.function_coverage_pct
        if self.decision is None:
            self.decision = self.branch_coverage_pct
        self.available = True
        return self


class MCDCResponse(BaseModel):
    execution_id: str
    coverage_percentage: float
    decisions: List[Dict[str, Any]]
    gap_recommendations: List[Dict[str, Any]]
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    gapAdvisor: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def sync_mcdc_frontend(self) -> "MCDCResponse":
        if not self.conditions:
            cond_list = []
            for d in self.decisions:
                for c in d.get("conditions", []):
                    cond_list.append({
                        "id": c.get("id", "C"),
                        "description": c.get("expression", ""),
                        "evaluated": True,
                    })
            self.conditions = cond_list
        if self.gapAdvisor is None and self.gap_recommendations:
            rec = self.gap_recommendations[0]
            self.gapAdvisor = {
                "suggestedVector": rec.get("recommended_inputs") or rec.get("candidate_vector") or rec
            }
        return self


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


# --- Compiler Configuration ---
class CompilerConfigDTO(BaseModel):
    compiler: str = "gcc"
    version: str = "16.2.0"
    flags: List[str] = Field(default_factory=lambda: ["-O0", "-g", "--coverage", "-fprofile-arcs", "-ftest-coverage"])
    includePaths: List[str] = Field(default_factory=lambda: ["."])
    buildProfile: str = "coverage"
    optimization: str = "-O0"
    warnings: List[str] = Field(default_factory=lambda: ["-Wall", "-Wextra"])
    defines: List[str] = Field(default_factory=list)
    includeDirs: List[str] = Field(default_factory=lambda: ["include", "."])
    cStandard: str = "c99"


class CompilerConfigUpdateDTO(BaseModel):
    compiler: Optional[str] = None
    version: Optional[str] = None
    flags: Optional[List[str]] = None
    includePaths: Optional[List[str]] = None
    buildProfile: Optional[str] = None
    optimization: Optional[str] = None
    warnings: Optional[List[str]] = None
    defines: Optional[List[str]] = None
    includeDirs: Optional[List[str]] = None
    cStandard: Optional[str] = None


# --- Execution Comparison ---
class ExecutionComparisonResponse(BaseModel):
    regressionCount: int = 0
    fixedCount: int = 0
    diffs: List[Dict[str, Any]] = Field(default_factory=list)


# --- AI Assistant ---
class AIModelDTO(BaseModel):
    id: str
    name: str
    provider: str = "NVIDIA_NIM"
    available: bool = False


class AIResponseDTO(BaseModel):
    suggestionId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    modelUsed: str = "meta/llama-3.3-70b-instruct"
    content: Any
    confidenceScore: Optional[float] = 0.95
    disclaimer: str = "DO-178C Notice: AI output is an advisory proposal and does not constitute authoritative verification evidence."
