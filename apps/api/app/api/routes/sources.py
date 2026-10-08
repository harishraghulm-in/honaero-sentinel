import hashlib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project, SourceFile
from apps.api.app.schemas.sentinel_api import SourceCreate, SourceResponse

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["Sources"])


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def add_source_file(project_id: str, payload: SourceCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} does not exist"},
        )

    checksum = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
    source = SourceFile(
        project_id=project_id,
        filename=payload.filename,
        filepath=payload.filepath or f"src/{payload.filename}",
        content=payload.content,
        checksum_sha256=checksum,
        is_target=payload.is_target,
        is_environment=payload.is_environment,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("", response_model=List[SourceResponse])
def list_source_files(project_id: str, db: Session = Depends(get_db)):
    return db.query(SourceFile).filter_by(project_id=project_id).all()


@router.get("/{source_id}", response_model=SourceResponse)
def get_source_file(project_id: str, source_id: str, db: Session = Depends(get_db)):
    source = db.query(SourceFile).filter_by(id=source_id, project_id=project_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SOURCE_NOT_FOUND", "message": f"Source file {source_id} not found"},
        )
    return source

