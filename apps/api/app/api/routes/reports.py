from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project
from apps.api.app.schemas.sentinel_api import ProjectReportResponse
from apps.api.app.application.services.report_service import ReportService

router = APIRouter(prefix="/projects/{project_id}", tags=["Verification Report"])
report_service = ReportService()


@router.get("/report", response_model=ProjectReportResponse)
def get_project_verification_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    return report_service.generate_project_report(project_id, db)

