from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project
from apps.api.app.schemas.sentinel_api import (
    PrioritizationResponse,
    PrioritizationOverrideRequest,
    PrioritizationOverrideResponse,
)
from apps.api.app.application.services.prioritization_service import PrioritizationService

router = APIRouter(prefix="/projects/{project_id}/prioritization", tags=["Prioritization"])
prioritization_service = PrioritizationService()


@router.get("", response_model=PrioritizationResponse)
def get_prioritization(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    return prioritization_service.compute_project_priorities(project_id, db)


@router.put("/override", response_model=PrioritizationOverrideResponse)
def set_priority_override(
    project_id: str,
    payload: PrioritizationOverrideRequest,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    try:
        return prioritization_service.set_override(
            project_id=project_id,
            target_id=payload.target_id,
            manual_priority=payload.manual_priority,
            manual_score=payload.manual_score,
            override_reason=payload.override_reason,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PRIORITIZATION_ERROR", "message": str(e)},
        )


@router.delete("/override/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_priority_override(
    project_id: str,
    target_id: str,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    deleted = prioritization_service.delete_override(project_id, target_id, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "OVERRIDE_NOT_FOUND", "message": f"Override for target {target_id} not found"},
        )
    return None

