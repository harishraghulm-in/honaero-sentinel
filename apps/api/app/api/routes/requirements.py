import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import (
    Project,
    RequirementDocument,
    Requirement,
    CandidateTestCase,
    TestCase,
    TestVector,
    FunctionModel,
)
from apps.api.app.schemas.sentinel_api import (
    RequirementDocumentUpload,
    RequirementDocumentResponse,
    RequirementCreate,
    RequirementUpdate,
    RequirementResponse,
    CandidateTestCaseResponse,
    CandidateApprovalRequest,
    TestCaseResponse,
)
from apps.api.app.application.services.requirement_service import RequirementService
from apps.api.app.infrastructure.ai.nim_provider import NvidiaNimProvider
from apps.api.app.application.services.ai_service import AIService

router = APIRouter(prefix="/projects/{project_id}", tags=["Requirements Engineering"])
req_service = RequirementService()
nim_provider = NvidiaNimProvider()
ai_service = AIService(nim_provider)


# --- Requirement Documents ---
@router.post("/requirements/documents", response_model=RequirementDocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_requirement_document(
    project_id: str,
    payload: RequirementDocumentUpload,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    if not payload.content or not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_DOCUMENT",
                "message": "Requirement document content cannot be empty.",
            },
        )

    ext = payload.filename.lower().split(".")[-1] if "." in payload.filename else "txt"
    allowed_exts = {"txt", "md", "json", "csv", "pdf", "docx"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_DOCUMENT_FORMAT",
                "message": f"Document format .{ext} is not supported (supported: .txt, .md, .json, .csv, .pdf, .docx).",
            },
        )

    checksum = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
    doc = RequirementDocument(
        project_id=project_id,
        filename=payload.filename,
        file_type=payload.file_type or ext,
        content=payload.content,
        checksum_sha256=checksum,
        revision=payload.revision,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/requirements/documents", response_model=List[RequirementDocumentResponse])
def list_requirement_documents(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    return db.query(RequirementDocument).filter_by(project_id=project_id).all()


@router.get("/requirements/documents/{doc_id}", response_model=RequirementDocumentResponse)
def get_requirement_document(project_id: str, doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(RequirementDocument).filter_by(id=doc_id, project_id=project_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": f"Document {doc_id} not found"},
        )
    return doc


# --- Structured Requirements Extraction & Management ---
@router.post("/requirements/extract", response_model=List[RequirementResponse], status_code=status.HTTP_201_CREATED)
def extract_requirements_from_document(
    project_id: str,
    document_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    query = db.query(RequirementDocument).filter_by(project_id=project_id)
    if document_id:
        doc = query.filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "DOCUMENT_NOT_FOUND", "message": f"Document {document_id} not found"},
            )
        docs = [doc]
    else:
        docs = query.all()
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "NO_DOCUMENTS_FOUND", "message": "No requirement documents uploaded for extraction"},
            )

    created_reqs: List[Requirement] = []
    for d in docs:
        try:
            extracted = req_service.extract_from_document(d.content, d.filename, d.file_type)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "EXTRACTION_FAILED", "message": str(e)},
            )

        for item in extracted:
            # Check if identifier already exists for project
            existing = db.query(Requirement).filter_by(project_id=project_id, identifier=item.identifier).first()
            if existing:
                existing.title = item.title
                existing.description = item.description
                existing.section = item.section
                existing.page_or_line = item.page_or_line
                existing.acceptance_criteria = item.acceptance_criteria
                existing.ambiguity_status = item.ambiguity_status
                existing.ambiguity_notes = item.ambiguity_notes
                created_reqs.append(existing)
            else:
                req = Requirement(
                    project_id=project_id,
                    document_id=d.id,
                    identifier=item.identifier,
                    title=item.title,
                    description=item.description,
                    req_type=item.req_type,
                    section=item.section,
                    page_or_line=item.page_or_line,
                    acceptance_criteria=item.acceptance_criteria,
                    verification_method=item.verification_method,
                    ambiguity_status=item.ambiguity_status,
                    ambiguity_notes=item.ambiguity_notes,
                    review_status="DRAFT",
                    revision=d.revision,
                )
                db.add(req)
                created_reqs.append(req)

    db.commit()
    for r in created_reqs:
        db.refresh(r)
    return created_reqs


@router.post("/requirements", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
def create_requirement(project_id: str, payload: RequirementCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    req = Requirement(
        project_id=project_id,
        document_id=payload.document_id,
        identifier=payload.identifier,
        title=payload.title,
        description=payload.description,
        req_type=payload.req_type,
        section=payload.section,
        page_or_line=payload.page_or_line,
        acceptance_criteria=payload.acceptance_criteria,
        verification_method=payload.verification_method or "TEST",
        ambiguity_status=payload.ambiguity_status,
        ambiguity_notes=payload.ambiguity_notes,
        review_status=payload.review_status,
        revision=payload.revision,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/requirements", response_model=List[RequirementResponse])
def list_requirements(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    return db.query(Requirement).filter_by(project_id=project_id).all()


@router.get("/requirements/{req_id}", response_model=RequirementResponse)
def get_requirement(project_id: str, req_id: str, db: Session = Depends(get_db)):
    req = db.query(Requirement).filter_by(id=req_id, project_id=project_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REQUIREMENT_NOT_FOUND", "message": f"Requirement {req_id} not found"},
        )
    return req


@router.put("/requirements/{req_id}/review", response_model=RequirementResponse)
def review_requirement(
    project_id: str,
    req_id: str,
    payload: RequirementUpdate,
    db: Session = Depends(get_db),
):
    req = db.query(Requirement).filter_by(id=req_id, project_id=project_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REQUIREMENT_NOT_FOUND", "message": f"Requirement {req_id} not found"},
        )

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(req, field, val)

    db.commit()
    db.refresh(req)
    return req


# --- Candidate Test Cases Generation & Review ---
@router.post("/requirements/{req_id}/generate-candidates", response_model=List[CandidateTestCaseResponse], status_code=status.HTTP_201_CREATED)
def generate_candidate_test_cases(
    project_id: str,
    req_id: str,
    target_function_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    req = db.query(Requirement).filter_by(id=req_id, project_id=project_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REQUIREMENT_NOT_FOUND", "message": f"Requirement {req_id} not found"},
        )

    created_candidates: List[CandidateTestCase] = []

    # Attempt live NVIDIA Nemotron candidate generation if configured
    if nim_provider.is_configured():
        target_fn = None
        if target_function_name:
            target_fn = db.query(FunctionModel).filter_by(project_id=project_id, name=target_function_name).first()
        if not target_fn:
            target_fn = db.query(FunctionModel).filter_by(project_id=project_id).first()

        fn_sig = ""
        if target_fn:
            param_str = ", ".join([f"{p.get('type', 'int')} {p.get('name', 'arg')}" for p in (target_fn.parameters or [])])
            fn_sig = f"{target_fn.return_type or 'int'} {target_fn.name}({param_str})"

        sys_prompt = (
            "You are an FAA DO-178C test automation engineer. Generate structured verification candidate test cases "
            "for the following software requirement and target C function signature.\n"
            "Return a JSON array of objects conforming to this schema:\n"
            "[\n"
            "  {\n"
            '    "name": "TC-REQ-001-NOMINAL",\n'
            '    "case_category": "NORMAL",\n'
            '    "rationale": "Verifies nominal requirement parameters",\n'
            '    "target_function_name": "target_func",\n'
            '    "preconditions": {"mode": "NORMAL"},\n'
            '    "input_vectors": [{"vector_index": 1, "inputs": {"param": 10}, "expected_outputs": {"return": 1}}],\n'
            '    "expected_outputs": {"return": 1},\n'
            '    "is_expected_result_uncertain": false,\n'
            '    "uncertainty_reason": null\n'
            "  }\n"
            "]\n"
            "Include NORMAL, BOUNDARY, and INVALID_INPUT test categories with genuine numeric parameters matching the requirement bounds.\n"
            "Return ONLY valid JSON."
        )
        user_prompt = (
            f"REQUIREMENT IDENTIFIER: {req.identifier}\n"
            f"TITLE: {req.title}\n"
            f"SPECIFICATION TEXT: {req.description}\n"
            f"ACCEPTANCE CRITERIA: {req.acceptance_criteria or 'Satisfy requirement specification bounds.'}\n"
            f"TARGET C FUNCTION: {fn_sig or target_function_name or 'verified_function'}\n"
        )
        raw_res, is_live, _ = nim_provider.complete_chat(
            model="nvidia/nemotron-4-340b-instruct",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
            response_format_json=True,
        )
        if is_live and raw_res:
            parsed = nim_provider.extract_json_payload(raw_res)
            if isinstance(parsed, list) and len(parsed) > 0:
                for item in parsed:
                    if isinstance(item, dict) and "name" in item:
                        cand = CandidateTestCase(
                            project_id=project_id,
                            requirement_id=req.id,
                            target_function_name=item.get("target_function_name") or target_function_name or (target_fn.name if target_fn else None),
                            name=item.get("name", f"TC-{req.identifier}-NEMOTRON"),
                            case_category=item.get("case_category", "NORMAL"),
                            rationale=item.get("rationale", "Generated by NVIDIA Nemotron-4 340B Instruct from requirement bounds."),
                            preconditions=item.get("preconditions") or {"requirement": req.identifier},
                            input_vectors=item.get("input_vectors") or [{"vector_index": 1, "inputs": {}, "expected_outputs": {}}],
                            expected_outputs=item.get("expected_outputs") or {},
                            is_expected_result_uncertain=bool(item.get("is_expected_result_uncertain", False)),
                            uncertainty_reason=item.get("uncertainty_reason"),
                            provenance="nvidia_nemotron_4_340b",
                            approval_status="PENDING_REVIEW",
                        )
                        db.add(cand)
                        created_candidates.append(cand)
                if created_candidates:
                    db.commit()
                    for cand in created_candidates:
                        db.refresh(cand)
                    return created_candidates

    # Deterministic AST boundary generator fallback
    cases_dto = req_service.generate_candidate_test_cases(
        identifier=req.identifier,
        description=req.description,
        target_function_name=target_function_name,
        acceptance_criteria=req.acceptance_criteria,
    )

    for c in cases_dto:
        cand = CandidateTestCase(
            project_id=project_id,
            requirement_id=req.id,
            target_function_name=c.target_function_name,
            name=c.name,
            case_category=c.case_category,
            rationale=c.rationale,
            preconditions=c.preconditions,
            input_vectors=c.input_vectors,
            expected_outputs=c.expected_outputs,
            is_expected_result_uncertain=c.is_expected_result_uncertain,
            uncertainty_reason=c.uncertainty_reason,
            provenance=c.provenance,
            approval_status="PENDING_REVIEW",
        )
        db.add(cand)
        created_candidates.append(cand)

    db.commit()
    for cand in created_candidates:
        db.refresh(cand)
    return created_candidates


@router.get("/candidate-test-cases", response_model=List[CandidateTestCaseResponse])
def list_candidate_test_cases(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    return db.query(CandidateTestCase).filter_by(project_id=project_id).all()


@router.post("/candidate-test-cases/{candidate_id}/approve", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def approve_candidate_test_case(
    project_id: str,
    candidate_id: str,
    payload: CandidateApprovalRequest = CandidateApprovalRequest(),
    db: Session = Depends(get_db),
):
    """Explicit human approval promotes candidate test case into an executable TestCase."""
    cand = db.query(CandidateTestCase).filter_by(id=candidate_id, project_id=project_id).first()
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CANDIDATE_NOT_FOUND", "message": f"Candidate test case {candidate_id} not found"},
        )

    # Find target function
    fn_id = payload.target_function_id
    if not fn_id:
        if cand.target_function_name:
            fn = db.query(FunctionModel).filter_by(project_id=project_id, name=cand.target_function_name).first()
            if fn:
                fn_id = fn.id
        if not fn_id:
            # Fall back to first discovered target function in project
            fn = db.query(FunctionModel).filter_by(project_id=project_id).first()
            if fn:
                fn_id = fn.id

    if not fn_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TARGET_FUNCTION_REQUIRED", "message": "Cannot approve candidate test case without a valid target function"},
        )

    # Create real TestCase
    tc = TestCase(
        project_id=project_id,
        name=cand.name,
        description=f"Approved from requirement {cand.requirement_id}. {cand.rationale}",
        target_function_id=fn_id,
        requirement_id=cand.requirement_id,
        test_suite_id=payload.test_suite_id,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)

    # Create TestVectors
    for idx, vec in enumerate(cand.input_vectors, start=1):
        tv = TestVector(
            test_case_id=tc.id,
            vector_index=vec.get("vector_index", idx),
            inputs=vec.get("inputs", {}),
            expected_outputs=vec.get("expected_outputs", cand.expected_outputs),
        )
        db.add(tv)

    # Update candidate record
    cand.approval_status = "APPROVED"
    cand.approved_test_case_id = tc.id

    db.commit()
    db.refresh(tc)

    return TestCaseResponse(
        id=tc.id,
        project_id=tc.project_id,
        name=tc.name,
        target_function_id=tc.target_function_id,
        requirement_id=tc.requirement_id,
        vectors_count=len(tc.test_vectors),
        created_at=tc.created_at,
    )
