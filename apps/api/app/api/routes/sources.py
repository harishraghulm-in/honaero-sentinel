import os
import base64
import hashlib
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project, SourceFile
from apps.api.app.schemas.sentinel_api import (
    SourceCreate,
    SourceResponse,
    SourceBatchItem,
    SourceBatchUploadRequest,
    SourceBatchUploadResponse,
    SourceArchiveImportRequest,
    SourceArchiveImportResponse,
    FileTreeNode,
    FileTreeResponse,
    SourceContentResponse,
)
from apps.api.app.application.services.source_archive_service import SourceArchiveService

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["Sources"])
archive_service = SourceArchiveService()


@router.post("/batch", response_model=SourceBatchUploadResponse, status_code=status.HTTP_201_CREATED)
def batch_upload_sources(
    project_id: str,
    payload: SourceBatchUploadRequest,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} does not exist"},
        )

    ALLOWED_EXTENSIONS = {".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hh", ".hxx", ".cmake", ".mk"}
    ALLOWED_FILENAMES = {"cmakelists.txt", "makefile", "gnumakefile"}

    existing_files = {
        sf.filepath: sf for sf in db.query(SourceFile).filter_by(project_id=project_id).all()
    }

    imported_records = []
    skipped_count = 0

    for item in payload.files:
        norm_filepath = os.path.normpath(item.filepath).replace("\\", "/").strip("/")
        base_filename = item.filename or os.path.basename(norm_filepath)
        _, ext = os.path.splitext(base_filename.lower())

        if ext not in ALLOWED_EXTENSIONS and base_filename.lower() not in ALLOWED_FILENAMES:
            skipped_count += 1
            continue

        checksum = hashlib.sha256(item.content.encode("utf-8")).hexdigest()

        if norm_filepath in existing_files:
            if not payload.overwrite:
                skipped_count += 1
                continue
            else:
                existing_sf = existing_files[norm_filepath]
                existing_sf.content = item.content
                existing_sf.checksum_sha256 = checksum
                existing_sf.is_target = item.is_target
                existing_sf.is_environment = item.is_environment
                imported_records.append(existing_sf)
                continue

        sf = SourceFile(
            project_id=project_id,
            filename=base_filename,
            filepath=norm_filepath,
            content=item.content,
            checksum_sha256=checksum,
            is_target=item.is_target,
            is_environment=item.is_environment,
        )
        db.add(sf)
        imported_records.append(sf)

    db.commit()
    for r in imported_records:
        db.refresh(r)

    return SourceBatchUploadResponse(
        total_received=len(payload.files),
        imported_count=len(imported_records),
        skipped_count=skipped_count,
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
            for f in imported_records
        ],
    )



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


def _build_file_tree(project_id: str, db: Session) -> FileTreeResponse:
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} does not exist"},
        )
    sources = db.query(SourceFile).filter_by(project_id=project_id).all()

    dir_tree: Dict[str, Any] = {"type": "dir", "children": {}}
    total_loc = 0
    total_files = len(sources)

    for sf in sources:
        content_lines = len(sf.content.splitlines()) if sf.content else 0
        total_loc += content_lines
        content_bytes = len(sf.content.encode("utf-8")) if sf.content else 0
        _, ext = os.path.splitext(sf.filename.lower())
        lang = "c" if ext in [".c", ".h"] else ("cpp" if ext in [".cpp", ".hpp", ".cc", ".cxx", ".hh", ".hxx"] else "other")
        fn_names = [f.name for f in sf.functions] if sf.functions else []
        decisions_count = sum(len(f.decisions or []) for f in sf.functions) if sf.functions else 0

        file_node_dict = {
            "id": sf.id,
            "name": sf.filename,
            "path": sf.filepath,
            "type": "file",
            "extension": ext,
            "language": lang,
            "size_bytes": content_bytes,
            "lines_of_code": content_lines,
            "functions_count": len(fn_names),
            "functions": fn_names,
            "complexity_score": decisions_count,
            "content": sf.content,
            "children": None,
        }

        clean_path = sf.filepath.replace("\\", "/").strip("/")
        parts = clean_path.split("/")
        curr = dir_tree
        for part in parts[:-1]:
            if part not in curr["children"]:
                curr["children"][part] = {"type": "dir", "name": part, "children": {}}
            curr = curr["children"][part]
        curr["children"][parts[-1]] = file_node_dict

    total_dirs = 0

    def _convert_node(name: str, node: Dict[str, Any], path_prefix: str) -> FileTreeNode:
        nonlocal total_dirs
        if node["type"] == "file":
            return FileTreeNode(**node)

        total_dirs += 1
        current_dir_path = f"{path_prefix}/{name}" if path_prefix else name
        children_nodes: List[FileTreeNode] = []
        dir_loc = 0
        dir_size = 0
        dir_fn_count = 0
        dir_complexity = 0
        dir_fns: List[str] = []

        for child_name, child_val in sorted(node["children"].items(), key=lambda x: (x[1]["type"] == "file", x[0])):
            child_tree_node = _convert_node(child_name, child_val, current_dir_path)
            children_nodes.append(child_tree_node)
            dir_loc += child_tree_node.lines_of_code
            dir_size += child_tree_node.size_bytes
            dir_fn_count += child_tree_node.functions_count
            dir_complexity += (child_tree_node.complexity_score or 0)
            dir_fns.extend(child_tree_node.functions)

        return FileTreeNode(
            id=None,
            name=name,
            path=current_dir_path,
            type="directory",
            extension=None,
            language=None,
            size_bytes=dir_size,
            lines_of_code=dir_loc,
            functions_count=dir_fn_count,
            functions=dir_fns,
            complexity_score=dir_complexity,
            children=children_nodes,
        )

    tree_nodes: List[FileTreeNode] = []
    for top_name, top_val in sorted(dir_tree["children"].items(), key=lambda x: (x[1]["type"] == "file", x[0])):
        tree_nodes.append(_convert_node(top_name, top_val, ""))

    return FileTreeResponse(
        project_id=project_id,
        total_files=total_files,
        total_directories=total_dirs,
        total_lines_of_code=total_loc,
        tree=tree_nodes,
    )


file_tree_router = APIRouter(prefix="/projects/{project_id}", tags=["File Tree"])


@file_tree_router.get("/file-tree", response_model=FileTreeResponse)
def get_file_tree_root(project_id: str, db: Session = Depends(get_db)):
    return _build_file_tree(project_id, db)


@router.get("/file-tree", response_model=FileTreeResponse)
def get_file_tree_sources(project_id: str, db: Session = Depends(get_db)):
    return _build_file_tree(project_id, db)


@router.get("/by-path", response_model=SourceContentResponse)
def get_source_by_path(project_id: str, path: str = Query(...), db: Session = Depends(get_db)):
    clean_path = path.replace("\\", "/").strip("/")
    source = db.query(SourceFile).filter(
        SourceFile.project_id == project_id,
        (SourceFile.filepath == clean_path) | (SourceFile.filename == clean_path),
    ).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SOURCE_NOT_FOUND", "message": f"Source with path '{path}' not found"},
        )
    return SourceContentResponse(
        id=source.id,
        project_id=source.project_id,
        filename=source.filename,
        filepath=source.filepath,
        content=source.content,
        lines_of_code=len(source.content.splitlines()) if source.content else 0,
        size_bytes=len(source.content.encode("utf-8")) if source.content else 0,
        checksum_sha256=source.checksum_sha256,
        is_target=source.is_target,
        is_environment=source.is_environment,
    )


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


@router.get("/{source_id}/content", response_model=SourceContentResponse)
def get_source_content(project_id: str, source_id: str, db: Session = Depends(get_db)):
    source = db.query(SourceFile).filter_by(id=source_id, project_id=project_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SOURCE_NOT_FOUND", "message": f"Source file {source_id} not found"},
        )
    return SourceContentResponse(
        id=source.id,
        project_id=source.project_id,
        filename=source.filename,
        filepath=source.filepath,
        content=source.content,
        lines_of_code=len(source.content.splitlines()) if source.content else 0,
        size_bytes=len(source.content.encode("utf-8")) if source.content else 0,
        checksum_sha256=source.checksum_sha256,
        is_target=source.is_target,
        is_environment=source.is_environment,
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

