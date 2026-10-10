from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project, SourceFile, Execution, EvidenceRecord
from apps.api.app.application.services import EvidenceService
from apps.api.app.schemas.sentinel_api import EvidenceResponse
from apps.api.app.core.config import get_settings

router = APIRouter(prefix="/projects/{project_id}/executions/{execution_id}/evidence", tags=["Evidence"])
ev_service = EvidenceService()
settings = get_settings()


@router.get("", response_model=EvidenceResponse)
def get_execution_evidence(project_id: str, execution_id: str, db: Session = Depends(get_db)):
    ev = db.query(EvidenceRecord).filter_by(execution_id=execution_id, project_id=project_id).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVIDENCE_NOT_FOUND", "message": f"Evidence for execution {execution_id} not found"},
        )

    current_sources = {
        (s.filepath if s.filepath else s.filename): s.content
        for s in db.query(SourceFile).filter_by(project_id=project_id).all()
    }
    current_src_hash = ev_service.compute_source_checksum(current_sources)
    freshness = ev_service.evaluate_freshness(
        current_source_hash=current_src_hash,
        evidence_source_hash=ev.source_checksum,
    )
    if ev.freshness != freshness:
        ev.freshness = freshness
        db.commit()

    return EvidenceResponse(
        evidence_id=ev.id,
        project_id=ev.project_id,
        execution_id=ev.execution_id,
        freshness=ev.freshness,
        source_checksum=ev.source_checksum,
        stub_checksum=ev.stub_checksum,
        vector_checksum=ev.vector_checksum,
        tool_version=ev.tool_version,
        evidence_data=ev.evidence_json,
        created_at=ev.created_at,
    )


@router.post("/export")
def export_evidence_record(project_id: str, execution_id: str, format: str = "json", db: Session = Depends(get_db)):
    ev = db.query(EvidenceRecord).filter_by(execution_id=execution_id, project_id=project_id).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVIDENCE_NOT_FOUND", "message": f"Evidence for execution {execution_id} not found"},
        )

    if format.lower() == "json":
        return JSONResponse(
            content=ev.evidence_json,
            headers={"Content-Disposition": f'attachment; filename="evidence_{execution_id}.json"'},
        )
    elif format.lower() in ("md", "markdown", "pdf", "txt"):
        export_file = settings.ARTIFACT_STORAGE_PATH / f"evidence_{execution_id}.md"
        report_obj = ev_service.build_evidence_record(
            evidence_id=ev.id,
            project_id=ev.project_id,
            execution_id=ev.execution_id,
            target_function=ev.evidence_json.get("target_function", "unknown"),
            requirement_ids=ev.evidence_json.get("requirement_ids", []),
            source_files={f: "" for f in ev.evidence_json.get("source_files", [])},
            stubs=ev.evidence_json.get("stubs", []),
            vectors=ev.evidence_json.get("test_vectors", []),
            compiler_info=ev.evidence_json.get("compiler", {}),
            execution_status=ev.execution.status if ev.execution else "PASSED",
            duration_ms=ev.evidence_json.get("duration_ms", 0.0),
            stdout=ev.evidence_json.get("stdout", ""),
            stderr=ev.evidence_json.get("stderr", ""),
            coverage_data=ev.evidence_json.get("coverage", {}),
            mcdc_data=ev.evidence_json.get("mcdc", {}),
        )
        report_obj.freshness = ev.freshness
        report_path = ev_service.export_markdown_or_text(report_obj, export_file)
        return FileResponse(
            path=str(report_path),
            filename=f"evidence_{execution_id}.md",
            media_type="text/markdown",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_FORMAT", "message": f"Format '{format}' not supported. Use 'json' or 'md'"},
        )


project_evidence_router = APIRouter(prefix="/projects/{project_id}/evidence", tags=["Evidence"])


@project_evidence_router.get("", response_model=EvidenceResponse)
def get_latest_project_evidence(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    ev = db.query(EvidenceRecord).filter_by(project_id=project_id).order_by(EvidenceRecord.created_at.desc()).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVIDENCE_NOT_FOUND", "message": f"No evidence generated yet for project {project_id}"},
        )

    return get_execution_evidence(project_id=project_id, execution_id=ev.execution_id, db=db)


@project_evidence_router.get("/export")
@project_evidence_router.post("/export")
def export_latest_project_evidence(project_id: str, format: str = "json", db: Session = Depends(get_db)):
    ev = db.query(EvidenceRecord).filter_by(project_id=project_id).order_by(EvidenceRecord.created_at.desc()).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVIDENCE_NOT_FOUND", "message": f"No evidence generated yet for project {project_id}"},
        )
    return export_evidence_record(project_id=project_id, execution_id=ev.execution_id, format=format, db=db)

