from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project, SourceFile, FunctionModel
from apps.api.app.schemas.sentinel_api import ScopeSetRequest, ScopeResponse

router = APIRouter(prefix="/projects/{project_id}/scope", tags=["Scope Selection"])


@router.post("", response_model=ScopeResponse)
def set_project_scope(project_id: str, payload: ScopeSetRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} does not exist"},
        )

    # Reset all functions and sources in project
    for f in db.query(FunctionModel).filter_by(project_id=project_id).all():
        f.is_target_under_test = (f.id == payload.target_function_id)

    target_src_name = None
    target_fn_name = None

    for s in db.query(SourceFile).filter_by(project_id=project_id).all():
        if s.id == payload.target_source_id:
            s.is_target = True
            s.is_environment = False
            target_src_name = s.filename
        elif s.id in payload.environment_source_ids:
            s.is_target = False
            s.is_environment = True
        else:
            s.is_target = False
            s.is_environment = False

    target_fn = db.query(FunctionModel).filter_by(id=payload.target_function_id, project_id=project_id).first()
    if target_fn:
        target_fn_name = target_fn.name

    db.commit()

    env_sources = [
        s.filename for s in db.query(SourceFile).filter_by(project_id=project_id, is_environment=True).all()
    ]

    return ScopeResponse(
        project_id=project_id,
        target_function_name=target_fn_name,
        target_source_filename=target_src_name,
        environment_sources=env_sources,
    )


@router.put("", response_model=ScopeResponse)
def update_project_scope(project_id: str, payload: ScopeSetRequest, db: Session = Depends(get_db)):
    return set_project_scope(project_id=project_id, payload=payload, db=db)


@router.get("", response_model=ScopeResponse)
def get_project_scope(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} does not exist"},
        )
    target_fn = db.query(FunctionModel).filter_by(project_id=project_id, is_target_under_test=True).first()
    target_src = db.query(SourceFile).filter_by(project_id=project_id, is_target=True).first()
    env_sources = [
        s.filename for s in db.query(SourceFile).filter_by(project_id=project_id, is_environment=True).all()
    ]

    return ScopeResponse(
        project_id=project_id,
        target_function_name=target_fn.name if target_fn else None,
        target_source_filename=target_src.filename if target_src else None,
        environment_sources=env_sources,
        selected_functions=[target_fn.name] if target_fn else [],
    )

