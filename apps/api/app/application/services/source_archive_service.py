import os
import io
import zipfile
import hashlib
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session

from apps.api.app.domain.models import SourceFile, Project


ALLOWED_SOURCE_EXTENSIONS = {
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hh", ".hxx",
    ".cmake", ".mk"
}
ALLOWED_SOURCE_FILENAMES = {
    "cmakelists.txt", "makefile", "gnumakefile"
}

MAX_ARCHIVE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_FILES_IN_ARCHIVE = 200
MAX_UNCOMPRESSED_FILE_SIZE = 2 * 1024 * 1024  # 2 MB per file


class SourceArchiveService:
    """Safely extracts and imports multi-file C/C++ projects from ZIP archives."""

    def import_zip_archive(
        self,
        project_id: str,
        archive_bytes: bytes,
        db: Session,
        overwrite: bool = False,
    ) -> Tuple[int, int, int, List[SourceFile]]:
        """
        Safely unpacks archive and creates SourceFile records.
        Returns (total_files_in_zip, imported_count, skipped_count, list_of_imported_sources).
        """
        if len(archive_bytes) > MAX_ARCHIVE_SIZE_BYTES:
            raise ValueError(
                f"Archive exceeds maximum allowed size of {MAX_ARCHIVE_SIZE_BYTES // (1024 * 1024)}MB."
            )

        try:
            zip_buffer = io.BytesIO(archive_bytes)
            zf = zipfile.ZipFile(zip_buffer, "r")
        except zipfile.BadZipFile as e:
            raise ValueError(f"Malformed ZIP archive: {str(e)}")

        infolist = zf.infolist()
        total_entries = len(infolist)
        if total_entries > MAX_FILES_IN_ARCHIVE:
            raise ValueError(
                f"Archive contains {total_entries} files, which exceeds limit of {MAX_FILES_IN_ARCHIVE}."
            )

        # Existing files in project for collision check
        existing_files = {
            sf.filepath: sf for sf in db.query(SourceFile).filter_by(project_id=project_id).all()
        }

        imported_records: List[SourceFile] = []
        skipped_count = 0

        for info in infolist:
            # Skip directories
            if info.is_dir():
                continue

            raw_path = info.filename

            # 1. Path safety and traversal prevention
            if not self._is_safe_path(raw_path):
                raise ValueError(
                    f"Security error: Archive contains invalid or dangerous path '{raw_path}' (path traversal or absolute path detected)."
                )

            # 2. Check uncompressed size
            if info.file_size > MAX_UNCOMPRESSED_FILE_SIZE:
                raise ValueError(
                    f"File '{raw_path}' uncompressed size {info.file_size} exceeds limit of {MAX_UNCOMPRESSED_FILE_SIZE // (1024*1024)}MB."
                )

            # 3. Check file extension or filename
            base_lower = os.path.basename(raw_path).lower()
            _, ext = os.path.splitext(raw_path.lower())
            if ext not in ALLOWED_SOURCE_EXTENSIONS and base_lower not in ALLOWED_SOURCE_FILENAMES:
                # Safely skip documentation, binaries, git files, etc.
                skipped_count += 1
                continue

            # 4. Read content safely in memory
            try:
                raw_content = zf.read(info)
            except Exception as e:
                raise ValueError(f"Could not read entry '{raw_path}': {str(e)}")

            # Decode text
            try:
                content_str = raw_content.decode("utf-8")
            except UnicodeDecodeError:
                content_str = raw_content.decode("latin-1")

            checksum = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
            norm_filepath = os.path.normpath(raw_path).replace("\\", "/")
            base_filename = os.path.basename(norm_filepath)

            # 5. Check duplicate or collision
            if norm_filepath in existing_files:
                if not overwrite:
                    skipped_count += 1
                    continue
                else:
                    # Update existing record
                    existing_sf = existing_files[norm_filepath]
                    existing_sf.content = content_str
                    existing_sf.checksum_sha256 = checksum
                    imported_records.append(existing_sf)
                    continue

            # Create new source file
            sf = SourceFile(
                project_id=project_id,
                filename=base_filename,
                filepath=norm_filepath,
                content=content_str,
                checksum_sha256=checksum,
                is_target=False,
                is_environment=False,
            )
            db.add(sf)
            imported_records.append(sf)

        if not imported_records and skipped_count == 0:
            raise ValueError("No valid C/C++ source or header files found in the uploaded archive.")

        db.commit()
        for r in imported_records:
            db.refresh(r)

        imported_count = len(imported_records)
        return total_entries, imported_count, skipped_count, imported_records

    def _is_safe_path(self, path: str) -> bool:
        """Validates that a path inside a ZIP archive does not perform path traversal."""
        if not path or "\0" in path:
            return False
        # Absolute paths (POSIX or Windows)
        if path.startswith("/") or path.startswith("\\"):
            return False
        if len(path) > 1 and path[1] == ":":
            return False
        # Traversal check
        normalized = os.path.normpath(path)
        parts = normalized.replace("\\", "/").split("/")
        if ".." in parts:
            return False
        if normalized.startswith(".."):
            return False
        return True
