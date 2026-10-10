import re
from pathlib import Path
from fastapi import HTTPException, status


SAFE_PATH_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.\/]+$")


def validate_safe_filename(filename: str) -> str:
    """Validates that a filename does not contain path traversal tokens."""
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": "Illegal path traversal detected in filename"}
        )
    return filename


def validate_workspace_path(base_path: Path, target_path: Path) -> Path:
    """Ensures target_path stays strictly within base_path."""
    resolved_base = base_path.resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PATH_TRAVERSAL_BLOCKED", "message": "Access outside designated workspace is prohibited"}
        )
    return resolved_target

