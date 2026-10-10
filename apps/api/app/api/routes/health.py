import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.app.core.config import get_settings
from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.schemas.health import HealthResponse, ReadyResponse, ToolchainStatus

router = APIRouter(tags=["Health & Verification Readiness"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse, summary="Liveness Probe")
def get_health() -> HealthResponse:
    """Returns liveness status of the HonAero Sentinel service."""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/ready", response_model=ReadyResponse, summary="Readiness Probe")
def get_ready(db: Session = Depends(get_db)) -> ReadyResponse:
    """Validates that database, compilers, and coverage tools are operational."""
    # 1. Database check
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # 2. Toolchain checks
    toolchains = {}

    # GCC
    gcc_path = settings.GCC_PATH
    gcc_available = False
    gcc_version = None
    if Path(gcc_path).exists() or shutil.which(gcc_path):
        try:
            res = subprocess.run([gcc_path, "--version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                gcc_available = True
                gcc_version = res.stdout.splitlines()[0]
        except Exception as e:
            gcc_version = str(e)
    toolchains["gcc"] = ToolchainStatus(
        name="gcc",
        available=gcc_available,
        path=gcc_path,
        version=gcc_version
    )

    # GCOV
    gcov_path = settings.GCOV_PATH
    gcov_available = False
    gcov_version = None
    if Path(gcov_path).exists() or shutil.which(gcov_path):
        try:
            res = subprocess.run([gcov_path, "--version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                gcov_available = True
                gcov_version = res.stdout.splitlines()[0]
        except Exception as e:
            gcov_version = str(e)
    toolchains["gcov"] = ToolchainStatus(
        name="gcov",
        available=gcov_available,
        path=gcov_path,
        version=gcov_version
    )

    overall_ready = db_ok and gcc_available
    return ReadyResponse(
        status="ready" if overall_ready else "degraded",
        database=db_ok,
        toolchains=toolchains,
        details={
            "execution_engine": settings.EXECUTION_ENGINE,
            "workspace_base": str(settings.WORKSPACE_BASE_PATH),
            "artifact_storage": str(settings.ARTIFACT_STORAGE_PATH)
        }
    )

