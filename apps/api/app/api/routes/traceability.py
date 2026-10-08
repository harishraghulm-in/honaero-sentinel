from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import (
    Project,
    Requirement,
    FunctionModel,
    TestCase,
    Execution,
    EvidenceRecord,
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

