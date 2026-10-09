import base64
import hashlib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project, SourceFile
from apps.api.app.schemas.sentinel_api import (
    SourceCreate,
    SourceResponse,
    SourceArchiveImportRequest,
    SourceArchiveImportResponse,
)
from apps.api.app.application.services.source_archive_service import SourceArchiveService

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["Sources"])
archive_service = SourceArchiveService()


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


@router.post("/import-zip", response_model=SourceArchiveImportResponse, status_code=status.HTTP_201_CREATED)
def import_source_zip(
    project_id: str,
    payload: SourceArchiveImportRequest,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} does not exist"},
        )

    try:
        archive_bytes = base64.b64decode(payload.archive_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_BASE64", "message": f"Invalid base64 payload: {str(e)}"},
        )

    try:
        total, imported_count, skipped, files = archive_service.import_zip_archive(
            project_id=project_id,
            archive_bytes=archive_bytes,
            db=db,
            overwrite=payload.overwrite,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ARCHIVE_IMPORT_ERROR", "message": str(e)},
        )

    return SourceArchiveImportResponse(
        total_files_in_archive=total,
        imported_sources=imported_count,
        skipped_files=skipped,
        files=[
            SourceResponse(
                id=f.id,
                project_id=f.project_id,
                filename=f.filename,
                filepath=f.filepath,
                content=f.content,
                checksum_sha256=f.checksum_sha256,
                is_target=f.is_target,
                is_environment=f.is_environment,
                created_at=f.created_at,
            )
            for f in files
        ],
    )


@router.get("", response_model=List[SourceResponse])
def list_source_files(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} does not exist"},
        )
    sources = db.query(SourceFile).filter_by(project_id=project_id).all()
    return [
        SourceResponse(
            id=s.id,
            project_id=s.project_id,
            filename=s.filename,
            filepath=s.filepath,
            content=s.content,
            checksum_sha256=s.checksum_sha256,
            is_target=s.is_target,
            is_environment=s.is_environment,
            created_at=s.created_at,
        )
        for s in sources
    ]


@router.get("/{source_id}", response_model=SourceResponse)
def get_source_file(project_id: str, source_id: str, db: Session = Depends(get_db)):
    source = db.query(SourceFile).filter_by(id=source_id, project_id=project_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SOURCE_NOT_FOUND", "message": f"Source file {source_id} not found"},
        )
    return SourceResponse(
        id=source.id,
        project_id=source.project_id,
        filename=source.filename,
        filepath=source.filepath,
        content=source.content,
        checksum_sha256=source.checksum_sha256,
        is_target=source.is_target,
        is_environment=source.is_environment,
        created_at=source.created_at,
    )


@router.put("/{source_id}", response_model=SourceResponse)
def update_source_file(
    project_id: str,
    source_id: str,
    payload: SourceCreate,
    db: Session = Depends(get_db),
):
    source = db.query(SourceFile).filter_by(id=source_id, project_id=project_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SOURCE_NOT_FOUND", "message": f"Source file {source_id} not found"},
        )
    source.content = payload.content
    source.checksum_sha256 = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
    if payload.filename:
        source.filename = payload.filename
    if payload.filepath:
        source.filepath = payload.filepath
    db.commit()
    db.refresh(source)
    return SourceResponse(
        id=source.id,
        project_id=source.project_id,
        filename=source.filename,
        filepath=source.filepath,
        content=source.content,
        checksum_sha256=source.checksum_sha256,
        is_target=source.is_target,
        is_environment=source.is_environment,
        created_at=source.created_at,
    )

