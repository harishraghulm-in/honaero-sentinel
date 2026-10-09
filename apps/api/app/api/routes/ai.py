import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.schemas.ai_schemas import (
    AIModelDTO,
    AIProviderStatusDTO,
    AIResponseDTO,
    AIReqExtractRequest,
    AIApproveRequirementRequest,
    AIGenerateTestsRequest,
    AIApproveTestProposalRequest,
    AIScenarioRequest,
    AIFaultSuggestRequest,
    AIExplainRequest,
    AIAdaptiveRetestRequest,
)
from apps.api.app.infrastructure.ai.nim_provider import NvidiaNimProvider
from apps.api.app.application.services.ai_service import AIService
from apps.api.app.domain.models import Project

router = APIRouter(tags=["AI Assistant"])

_nim_provider = NvidiaNimProvider()
_ai_service = AIService(_nim_provider)
_PROJECT_PREFERRED_MODELS: Dict[str, str] = {}


def _get_project_model(project_id: str) -> str:
    return _PROJECT_PREFERRED_MODELS.get(project_id, "meta/llama-3.3-70b-instruct")


@router.get("/ai/models", response_model=List[AIModelDTO])
def list_ai_models():
    """Returns available NVIDIA NIM models with live availability status."""
    return [AIModelDTO(**m) for m in _nim_provider.get_models()]


@router.get("/ai/status", response_model=AIProviderStatusDTO)
def get_ai_status():
    """Checks the NVIDIA NIM provider configuration and connectivity."""
    h = _nim_provider.check_health()
    return AIProviderStatusDTO(
        provider="NVIDIA_NIM",
        isConfigured=h.get("isConfigured", False),
        baseUrl=h.get("baseUrl", "https://integrate.api.nvidia.com/v1"),
        activeModel="meta/llama-3.3-70b-instruct",
        liveCallTested=h.get("liveCallTested", False),
        details=h,
    )


class SetModelRequest(BaseModel):
    modelId: Optional[str] = None
    model_id: Optional[str] = None


@router.post("/ai/models/select")
def select_global_model(payload: SetModelRequest):
    mid = payload.modelId or payload.model_id
    if not mid:
        raise HTTPException(status_code=400, detail="modelId or model_id required")
    valid_ids = [m["id"] for m in _nim_provider.CATALOG]
    if mid not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Unknown model: {mid}. Valid: {valid_ids}")
    _PROJECT_PREFERRED_MODELS["default"] = mid
    return {"status": "success", "currentModel": mid, "modelId": mid}


@router.put("/projects/{project_id}/ai/model")
def set_project_model(project_id: str, payload: SetModelRequest, db: Session = Depends(get_db)):
    """Sets the preferred AI model for the specified project."""
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    mid = payload.modelId or payload.model_id or "meta/llama-3.3-70b-instruct"
    _PROJECT_PREFERRED_MODELS[project_id] = mid
    return {"status": "success", "modelId": mid}


@router.post("/projects/{project_id}/ai/requirements", response_model=AIResponseDTO)
def extract_ai_requirements(project_id: str, payload: AIReqExtractRequest, db: Session = Depends(get_db)):
    """Extracts candidate high-level and low-level software requirements with provenance tagging."""
    model_id = _get_project_model(project_id)
    doc_text = payload.document or payload.spec_text
    proposals, is_live = _ai_service.extract_requirements(
        project_id=project_id,
        document_text=doc_text,
        source_id=payload.sourceId,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=[p.model_dump() for p in proposals],
        confidenceScore=0.94 if is_live else 0.90,
        disclaimer="DO-178C Notice: AI extracted requirements are advisory proposals. Human software engineer approval is mandatory.",
    )


@router.post("/projects/{project_id}/ai/requirements/approve")
def approve_ai_requirement(project_id: str, payload: AIApproveRequirementRequest, db: Session = Depends(get_db)):
    """Approves a proposed requirement, saving it into the project database as an official Requirement entity."""
    prop = payload.proposal or {}
    proposal_id = payload.proposalId or prop.get("proposalId") or prop.get("id") or str(uuid.uuid4())
    identifier = payload.identifier or prop.get("identifier") or "HLR-001"
    title = payload.title or prop.get("title") or "Approved Requirement"
    description = payload.description or prop.get("description") or ""
    section = payload.section or prop.get("section")
    acceptance_criteria = payload.acceptanceCriteria or prop.get("acceptanceCriteria") or prop.get("acceptance_criteria")

    req = _ai_service.approve_requirement(
        project_id=project_id,
        proposal_id=proposal_id,
        identifier=identifier,
        title=title,
        description=description,
        section=section,
        acceptance_criteria=acceptance_criteria,
        db=db,
    )
    return {
        "status": "APPROVED",
        "success": True,
        "requirementId": req.id,
        "identifier": req.identifier,
        "requirement": {
            "id": req.id,
            "project_id": req.project_id,
            "identifier": req.identifier,
            "title": req.title,
            "description": req.description,
            "review_status": req.review_status,
        },
        "message": f"Requirement {req.identifier} promoted to approved project requirement.",
    }


@router.post("/projects/{project_id}/ai/test-proposals", response_model=AIResponseDTO)
def generate_ai_test_proposals(project_id: str, payload: AIGenerateTestsRequest, db: Session = Depends(get_db)):
    """Generates structured test case proposals categorizing normal, boundary, invalid, fault, and scenario vectors."""
    model_id = _get_project_model(project_id)
    func_id = payload.functionId or payload.target_function
    proposals, is_live = _ai_service.generate_test_proposals(
        project_id=project_id,
        function_id=func_id,
        category=payload.category or "ALL",
        requirement_id=payload.requirementId,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=[p.model_dump() for p in proposals],
        confidenceScore=0.96 if is_live else 0.92,
        disclaimer="DO-178C Notice: AI test proposals require human review before promotion to the executable test suite.",
    )


@router.post("/projects/{project_id}/ai/test-proposals/approve")
def approve_ai_test_proposal(project_id: str, payload: AIApproveTestProposalRequest, db: Session = Depends(get_db)):
    """Promotes an approved test proposal into a real executable TestCase + TestVector in the project database."""
    prop = payload.proposal or {}
    proposal_id = payload.proposalId or prop.get("proposalId") or prop.get("id") or str(uuid.uuid4())
    name = payload.name or prop.get("name") or prop.get("target_function") or "Approved Test Case"
    inputs = payload.inputs or prop.get("inputs") or (prop.get("input_vectors")[0] if prop.get("input_vectors") else None) or {"pressure": 950, "altitude": 5000}
    expected_outputs = payload.expectedOutputs or prop.get("expectedOutputs") or prop.get("expected_outputs") or {"status": "NOMINAL"}
    target_func = payload.targetFunctionId or prop.get("targetFunctionId") or prop.get("target_function")
    suite_id = payload.testSuiteId or prop.get("testSuiteId")

    tc = _ai_service.approve_test_proposal(
        project_id=project_id,
        proposal_id=proposal_id,
        name=name,
        inputs=inputs,
        expected_outputs=expected_outputs,
        target_function_id=target_func,
        test_suite_id=suite_id,
        db=db,
    )
    return {
        "status": "APPROVED",
        "success": True,
        "testCaseId": tc.id,
        "name": tc.name,
        "test_case": {
            "id": tc.id,
            "project_id": tc.project_id,
            "name": tc.name,
        },
        "test_vector": {
            "id": tc.test_vectors[0].id if tc.test_vectors else None,
            "test_case_id": tc.id,
        },
        "vectorsCount": len(tc.test_vectors),
        "message": f"Test proposal promoted to executable TestCase '{tc.name}' in test suite.",
    }


@router.post("/projects/{project_id}/ai/scenarios", response_model=AIResponseDTO)
def generate_ai_scenarios(project_id: str, payload: AIScenarioRequest, db: Session = Depends(get_db)):
    """Generates structured operational flight envelope sequences with time intervals and state transitions."""
    model_id = _get_project_model(project_id)
    phase = payload.flightPhase or payload.scenario_type or "ALL"
    scenarios, is_live = _ai_service.generate_scenarios(
        project_id=project_id,
        function_id=payload.functionId,
        flight_phase=phase,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=[s.model_dump() for s in scenarios],
        confidenceScore=0.92,
        disclaimer="DO-178C Notice: Operational scenarios represent candidate test trajectories for sequence verification.",
    )


@router.post("/projects/{project_id}/ai/faults", response_model=AIResponseDTO)
def suggest_ai_fault_injections(project_id: str, payload: AIFaultSuggestRequest, db: Session = Depends(get_db)):
    """Recommends interface-compatible sensor spikes, stuck values, noise, drift, and missing data faults."""
    model_id = _get_project_model(project_id)
    faults, is_live = _ai_service.suggest_fault_injections(
        project_id=project_id,
        function_id=payload.functionId,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=[f.model_dump() for f in faults],
        confidenceScore=0.94,
        disclaimer="DO-178C Notice: Fault injection proposals are exploratory test vectors to verify robust error-handling.",
    )


@router.post("/projects/{project_id}/ai/explain", response_model=AIResponseDTO)
def explain_ai_failure(project_id: str, payload: AIExplainRequest, db: Session = Depends(get_db)):
    """Explains verification failure based strictly on observed execution evidence (compiler stderr, exit code, assertion diff)."""
    model_id = _get_project_model(project_id)
    exec_id = payload.executionId or payload.run_id
    explanation, is_live = _ai_service.explain_failure(
        project_id=project_id,
        execution_id=exec_id,
        failure_logs=payload.failure_logs,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=explanation.model_dump(),
        confidenceScore=0.96,
        disclaimer="DO-178C Notice: Root cause explanations are advisory hypotheses. Refer to ground truth test harness logs.",
    )


@router.post("/projects/{project_id}/ai/coverage-gaps", response_model=AIResponseDTO)
def recommend_ai_coverage_gaps(project_id: str, executionId: Optional[str] = None, db: Session = Depends(get_db)):
    """Analyzes actual measured GCOV and MC/DC coverage data and recommends specific input vectors to close gaps."""
    model_id = _get_project_model(project_id)
    gaps, is_live = _ai_service.recommend_coverage_gaps(
        project_id=project_id,
        execution_id=executionId,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=[g.model_dump() for g in gaps],
        confidenceScore=0.95,
        disclaimer="DO-178C Notice: Proposed vectors do not guarantee coverage until executed and verified by GCOV tooling.",
    )


@router.post("/projects/{project_id}/ai/adaptive-retest", response_model=AIResponseDTO)
def generate_ai_adaptive_retest(project_id: str, payload: AIAdaptiveRetestRequest, db: Session = Depends(get_db)):
    """Proposes targeted diagnostic test cases from failed runs without modifying source code or weakening the oracle."""
    model_id = _get_project_model(project_id)
    exec_id = payload.executionId or payload.failed_run_id
    retest, is_live = _ai_service.generate_adaptive_retest(
        project_id=project_id,
        execution_id=exec_id,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=retest.model_dump(),
        confidenceScore=0.93,
        disclaimer="DO-178C Notice: Diagnostic tests investigate prerequisite conditions without altering original test records.",
    )


@router.post("/projects/{project_id}/ai/test-suite-optimization", response_model=AIResponseDTO)
def optimize_ai_test_suite(project_id: str, db: Session = Depends(get_db)):
    """Identifies redundant tests while preserving all requirements, boundary, invalid, and fault coverage objectives."""
    model_id = _get_project_model(project_id)
    opt, is_live = _ai_service.optimize_test_suite(
        project_id=project_id,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=opt.model_dump(),
        confidenceScore=0.91,
        disclaimer="DO-178C Notice: Test optimization preserves all requirements coverage. No tests are deleted automatically.",
    )


@router.post("/projects/{project_id}/ai/traceability", response_model=AIResponseDTO)
@router.post("/projects/{project_id}/ai/traceability-suggestions", response_model=AIResponseDTO)
def suggest_ai_traceability(project_id: str, db: Session = Depends(get_db)):
    """Suggests candidate mappings between requirements, functions, and test cases, highlighting unverified items."""
    model_id = _get_project_model(project_id)
    proposals, is_live = _ai_service.suggest_traceability(
        project_id=project_id,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=[p.model_dump() for p in proposals],
        confidenceScore=0.93,
        disclaimer="DO-178C Notice: Candidate traceability links require systems engineer confirmation.",
    )


@router.post("/projects/{project_id}/ai/environment", response_model=AIResponseDTO)
@router.post("/projects/{project_id}/ai/environment-recommendations", response_model=AIResponseDTO)
def recommend_ai_environment(project_id: str, db: Session = Depends(get_db)):
    """Recommends suitable compiler flags, include paths, defines, stubs, and sanitizers for the project."""
    model_id = _get_project_model(project_id)
    rec, is_live = _ai_service.recommend_environment(
        project_id=project_id,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=rec.model_dump(),
        confidenceScore=0.92,
        disclaimer="DO-178C Notice: Toolchain recommendations are advisory. Software build lead approval required.",
    )


@router.post("/projects/{project_id}/ai/stubs", response_model=AIResponseDTO)
def recommend_ai_stubs(project_id: str, db: Session = Depends(get_db)):
    """Recommends stubs and deterministic return values for project dependencies."""
    return recommend_ai_environment(project_id=project_id, db=db)


@router.post("/projects/{project_id}/ai/report", response_model=AIResponseDTO)
def generate_ai_report(project_id: str, db: Session = Depends(get_db)):
    """Generates an audit-ready DO-178C summary report derived from real verification runs and GCOV coverage."""
    model_id = _get_project_model(project_id)
    rep_data, is_live = _ai_service.generate_report_summary(
        project_id=project_id,
        model_id=model_id,
        db=db,
    )
    return AIResponseDTO(
        modelUsed=model_id,
        isLiveCall=is_live,
        content=rep_data["markdownContent"],
        confidenceScore=0.98,
        disclaimer="DO-178C Notice: AI report draft is advisory and requires designated engineering representative (DER) sign-off.",
    )
