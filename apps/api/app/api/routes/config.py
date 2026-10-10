from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import subprocess
import shutil
from pathlib import Path

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project, BuildConfiguration
from apps.api.app.schemas.sentinel_api import CompilerConfigDTO, CompilerConfigUpdateDTO
from apps.api.app.core.config import get_settings

router = APIRouter(prefix="/projects/{project_id}/config", tags=["Compiler & Build Configuration"])
settings = get_settings()


def get_detected_compiler_version(compiler_name: str = "gcc") -> str:
    try:
        bin_path = shutil.which(compiler_name) or compiler_name
        res = subprocess.run([bin_path, "--version"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return res.stdout.splitlines()[0]
    except Exception:
        pass
    return "16.2.0 (MinGW-W64)"


@router.get("", response_model=CompilerConfigDTO)
def get_compiler_config(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    bcfg = db.query(BuildConfiguration).filter_by(project_id=project_id).first()
    flags_list = ["-O0", "-g", "--coverage", "-fprofile-arcs", "-ftest-coverage"]
    inc_list = ["include", "."]
    opt_val = "-O0"
    warn_list = ["-Wall", "-Wextra"]
    def_list = []
    c_std = "c99"
    version = get_detected_compiler_version("gcc")

    if bcfg:
        if bcfg.compiler_flags:
            flags_list = [f.strip() for f in bcfg.compiler_flags.split() if f.strip()]
        if bcfg.include_dirs:
            inc_list = [i.strip() for i in bcfg.include_dirs.split(",") if i.strip()]
        compiler_name = bcfg.compiler
        version = get_detected_compiler_version(compiler_name)
    else:
        compiler_name = "gcc"

    # Extract parsed properties from flags
    for f in flags_list:
        if f.startswith("-O"):
            opt_val = f
        elif f.startswith("-W"):
            if f not in warn_list:
                warn_list.append(f)
        elif f.startswith("-D"):
            def_list.append(f[2:])
        elif f.startswith("-std="):
            c_std = f[5:]

    return CompilerConfigDTO(
        compiler=compiler_name,
        version=version,
        flags=flags_list,
        includePaths=inc_list,
        buildProfile="coverage" if "--coverage" in flags_list else "debug",
        optimization=opt_val,
        warnings=warn_list,
        defines=def_list,
        includeDirs=inc_list,
        cStandard=c_std,
    )


@router.put("", response_model=CompilerConfigDTO)
def update_compiler_config(project_id: str, payload: CompilerConfigUpdateDTO, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    bcfg = db.query(BuildConfiguration).filter_by(project_id=project_id).first()
    if not bcfg:
        bcfg = BuildConfiguration(project_id=project_id)
        db.add(bcfg)

    if payload.compiler:
        bcfg.compiler = payload.compiler

    # Merge flags from either direct flags array or granular fields
    if payload.flags is not None:
        bcfg.compiler_flags = " ".join(payload.flags)
    else:
        new_flags = []
        if payload.optimization:
            new_flags.append(payload.optimization)
        if payload.warnings:
            new_flags.extend(payload.warnings)
        if payload.defines:
            new_flags.extend([f"-D{d}" for d in payload.defines])
        if payload.cStandard:
            new_flags.append(f"-std={payload.cStandard}")
        if "--coverage" not in new_flags:
            new_flags.extend(["-g", "--coverage", "-fprofile-arcs", "-ftest-coverage"])
        if new_flags:
            bcfg.compiler_flags = " ".join(new_flags)

    if payload.includePaths is not None:
        bcfg.include_dirs = ",".join(payload.includePaths)
    elif payload.includeDirs is not None:
        bcfg.include_dirs = ",".join(payload.includeDirs)

    db.commit()
    db.refresh(bcfg)

    return get_compiler_config(project_id=project_id, db=db)
