import io
import csv
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import (
    Project,
    Requirement,
    FunctionModel,
    TestCase,
    CandidateTestCase,
    Execution,
    EvidenceRecord,
    TraceabilityLink,
)
from apps.api.app.schemas.sentinel_api import (
    TraceabilitySuggestionRequest,
    TraceabilityLinkCreate,
    TraceabilityLinkResponse,
    TraceabilityMatrixResponse,
    TraceabilityMatrixItem,
    RequirementResponse,
    CandidateTestCaseResponse,
    TestCaseResponse,
    ExecutionResponse,
)
from apps.api.app.application.services.traceability_service import (
    TraceabilityService,
    TraceabilityGraph,
)

router = APIRouter(prefix="/projects/{project_id}/traceability", tags=["Traceability Matrix"])
trace_service = TraceabilityService()


@router.get("", response_model=TraceabilityGraph)
def get_traceability_graph(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    reqs = db.query(Requirement).filter_by(project_id=project_id).all()
    funcs = db.query(FunctionModel).filter_by(project_id=project_id).all()
    tcs = db.query(TestCase).filter_by(project_id=project_id).all()
    execs = db.query(Execution).filter_by(project_id=project_id).all()
    evids = db.query(EvidenceRecord).filter_by(project_id=project_id).all()

    return trace_service.build_graph(
        project_id=project_id,
        requirements=reqs,
        functions=funcs,
        test_cases=tcs,
        executions=execs,
        evidences=evids,
    )


@router.post("/suggest", response_model=List[TraceabilityLinkResponse], status_code=status.HTTP_201_CREATED)
def suggest_traceability_links(
    project_id: str,
    payload: TraceabilitySuggestionRequest = TraceabilitySuggestionRequest(),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    reqs = db.query(Requirement).filter_by(project_id=project_id).all()
    funcs = db.query(FunctionModel).filter_by(project_id=project_id).all()

    suggestions = trace_service.suggest_links(
        requirements=reqs,
        functions=funcs,
        confidence_threshold=payload.confidence_threshold,
    )

    created_links: List[TraceabilityLink] = []
    for sug in suggestions:
        existing = db.query(TraceabilityLink).filter_by(
            project_id=project_id,
            requirement_id=sug["requirement_id"],
            function_id=sug["function_id"],
        ).first()

        if existing:
            existing.confidence_score = sug["confidence_score"]
            existing.rationale = sug["rationale"]
            created_links.append(existing)
        else:
            link = TraceabilityLink(
                project_id=project_id,
                requirement_id=sug["requirement_id"],
                function_id=sug["function_id"],
                status="SUGGESTED",
                confidence_score=sug["confidence_score"],
                rationale=sug["rationale"],
            )
            db.add(link)
            created_links.append(link)

    db.commit()
    for lk in created_links:
        db.refresh(lk)
    return created_links


@router.post("/links", response_model=TraceabilityLinkResponse, status_code=status.HTTP_201_CREATED)
def create_traceability_link(
    project_id: str,
    payload: TraceabilityLinkCreate,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    link = TraceabilityLink(
        project_id=project_id,
        requirement_id=payload.requirement_id,
        function_id=payload.function_id,
        test_case_id=payload.test_case_id,
        status=payload.status,
        confidence_score=payload.confidence_score,
        rationale=payload.rationale,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.put("/links/{link_id}", response_model=TraceabilityLinkResponse)
def update_traceability_link(
    project_id: str,
    link_id: str,
    status_str: str,
    db: Session = Depends(get_db),
):
    link = db.query(TraceabilityLink).filter_by(id=link_id, project_id=project_id).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LINK_NOT_FOUND", "message": f"Traceability link {link_id} not found"},
        )

    link.status = status_str
    db.commit()
    db.refresh(link)
    return link


@router.get("/matrix", response_model=TraceabilityMatrixResponse)
def get_traceability_matrix(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    reqs = db.query(Requirement).filter_by(project_id=project_id).all()
    links = db.query(TraceabilityLink).filter_by(project_id=project_id).all()

    matrix_items: List[TraceabilityMatrixItem] = []
    for r in reqs:
        # Find linked functions
        req_links = [l for l in links if l.requirement_id == r.id]
        linked_fns = []
        for l in req_links:
            if l.function_id:
                fn = db.query(FunctionModel).filter_by(id=l.function_id).first()
                if fn:
                    linked_fns.append({
                        "link_id": l.id,
                        "function_id": fn.id,
                        "function_name": fn.name,
                        "status": l.status,
                        "confidence_score": l.confidence_score,
                        "rationale": l.rationale,
                    })

        cand_cases = db.query(CandidateTestCase).filter_by(requirement_id=r.id).all()
        tcs = db.query(TestCase).filter_by(requirement_id=r.id).all()
        execs = [ex for tc in tcs for ex in tc.executions]
        latest_ev = db.query(EvidenceRecord).filter_by(project_id=project_id).first()

        matrix_items.append(TraceabilityMatrixItem(
            requirement=RequirementResponse(
                id=r.id,
                project_id=r.project_id,
                document_id=r.document_id,
                identifier=r.identifier,
                title=r.title,
                description=r.description,
                req_type=r.req_type,
                section=r.section,
                page_or_line=r.page_or_line,
                acceptance_criteria=r.acceptance_criteria,
                verification_method=r.verification_method or "TEST",
                ambiguity_status=r.ambiguity_status,
                ambiguity_notes=r.ambiguity_notes,
                review_status=r.review_status,
                revision=r.revision,
                created_at=r.created_at,
            ),
            linked_functions=linked_fns,
            candidate_test_cases=[
                CandidateTestCaseResponse(
                    id=c.id,
                    project_id=c.project_id,
                    requirement_id=c.requirement_id,
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
                    approval_status=c.approval_status,
                    approved_test_case_id=c.approved_test_case_id,
                    created_at=c.created_at,
                )
                for c in cand_cases
            ],
            test_cases=[
                TestCaseResponse(
                    id=tc.id,
                    project_id=tc.project_id,
                    name=tc.name,
                    target_function_id=tc.target_function_id,
                    requirement_id=tc.requirement_id,
                    vectors_count=len(tc.test_vectors),
                    created_at=tc.created_at,
                )
                for tc in tcs
            ],
            executions=[
                ExecutionResponse(
                    id=ex.id,
                    execution_id=ex.id,
                    project_id=ex.project_id,
                    test_case_id=ex.test_case_id,
                    status=ex.status,
                    exit_code=ex.exit_code,
                    duration_ms=ex.duration_ms,
                    results_summary=ex.results_summary,
                    created_at=ex.created_at,
                )
                for ex in execs
            ],
            evidence=latest_ev.evidence_json if latest_ev else None,
        ))

    return TraceabilityMatrixResponse(project_id=project_id, matrix=matrix_items)


@router.get("/export")
@router.get("/matrix/export")
def export_traceability_matrix(
    project_id: str,
    format: str = "json",
    db: Session = Depends(get_db),
):
    matrix_resp = get_traceability_matrix(project_id=project_id, db=db)

    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Requirement ID", "Title", "Ambiguity", "Review", "Linked Functions", "Test Cases", "Executions", "Status"])
        for item in matrix_resp.matrix:
            fns = ", ".join(f["function_name"] for f in item.linked_functions)
            tcs = ", ".join(tc.name for tc in item.test_cases)
            execs = ", ".join(ex.status.value for ex in item.executions)
            writer.writerow([
                item.requirement.identifier,
                item.requirement.title,
                item.requirement.ambiguity_status,
                item.requirement.review_status,
                fns,
                tcs,
                execs,
                "VERIFIED" if any(ex.status.value == "PASSED" for ex in item.executions) else "UNVERIFIED"
            ])
        return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=traceability_{project_id}.csv"})

    elif format.lower() in ["md", "markdown"]:
        lines = [
            f"# Traceability Matrix — Project {project_id}\n",
            "| Requirement ID | Title | Ambiguity | Review Status | Functions | Test Cases | Execution Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for item in matrix_resp.matrix:
            fns = ", ".join(f["function_name"] for f in item.linked_functions) or "None"
            tcs = ", ".join(tc.name for tc in item.test_cases) or "None"
            exec_stat = ", ".join(ex.status.value for ex in item.executions) or "Not Run"
            lines.append(f"| {item.requirement.identifier} | {item.requirement.title} | {item.requirement.ambiguity_status} | {item.requirement.review_status} | {fns} | {tcs} | {exec_stat} |")
        return Response(content="\n".join(lines), media_type="text/markdown")

    return matrix_resp

