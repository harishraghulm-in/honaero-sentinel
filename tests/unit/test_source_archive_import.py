import io
import base64
import zipfile
import pytest


def _create_zip_buffer(file_dict: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in file_dict.items():
            zf.writestr(path, content)
    buf.seek(0)
    return buf.getvalue()


def test_source_zip_import_nested_files(client):
    """Verify importing a multi-file C/C++ project zip preserves nested folder hierarchy."""
    res_proj = client.post("/api/v1/projects", json={"name": "Zip Import Project"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    files = {
        "src/controller/pressure.c": "int get_pressure(void) { return 1000; }",
        "include/controller/pressure.h": "int get_pressure(void);",
        "drivers/sensor.c": "int read_sensor(void) { return 50; }",
        "README.md": "# Readme text should be safely skipped",
    }
    zip_bytes = _create_zip_buffer(files)
    b64_str = base64.b64encode(zip_bytes).decode("utf-8")

    res = client.post(f"/api/v1/projects/{proj_id}/sources/import-zip", json={
        "filename": "flight_controller.zip",
        "archive_base64": b64_str,
        "overwrite": False,
    })
    assert res.status_code == 201
    data = res.json()
    assert data["total_files_in_archive"] == 4
    assert data["imported_sources"] == 3  # 3 C source/header files, README.md skipped
    assert data["skipped_files"] == 1

    imported_paths = {f["filepath"] for f in data["files"]}
    assert "src/controller/pressure.c" in imported_paths
    assert "include/controller/pressure.h" in imported_paths
    assert "drivers/sensor.c" in imported_paths

    # Verify sources list endpoint preserves relative paths and content
    res_list = client.get(f"/api/v1/projects/{proj_id}/sources")
    assert res_list.status_code == 200
    listed = res_list.json()
    assert len(listed) == 3
    press_c = next(s for s in listed if s["filepath"] == "src/controller/pressure.c")
    assert press_c["filename"] == "pressure.c"
    assert "get_pressure" in press_c["content"]
    assert len(press_c["checksum_sha256"]) == 64


def test_source_zip_path_traversal_rejected(client):
    """Verify that path traversal attempts inside archives are strictly rejected."""
    res_proj = client.post("/api/v1/projects", json={"name": "Zip Security Test"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    traversal_files = {
        "../../etc/passwd.c": "int evil(void) { return 0; }",
    }
    zip_bytes = _create_zip_buffer(traversal_files)
    b64_str = base64.b64encode(zip_bytes).decode("utf-8")

    res = client.post(f"/api/v1/projects/{proj_id}/sources/import-zip", json={
        "filename": "malicious.zip",
        "archive_base64": b64_str,
    })
    assert res.status_code == 400
    err = res.json()
    assert err["error"]["code"] == "ARCHIVE_IMPORT_ERROR"
    assert "path traversal" in err["error"]["message"].lower()


def test_source_zip_malformed_rejected(client):
    """Verify that malformed or corrupt archives return 400 error."""
    res_proj = client.post("/api/v1/projects", json={"name": "Malformed Zip Test"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    corrupt_bytes = b"This is not a zip file at all"
    b64_str = base64.b64encode(corrupt_bytes).decode("utf-8")

    res = client.post(f"/api/v1/projects/{proj_id}/sources/import-zip", json={
        "filename": "corrupt.zip",
        "archive_base64": b64_str,
    })
    assert res.status_code == 400
    err = res.json()
    assert err["error"]["code"] == "ARCHIVE_IMPORT_ERROR"


def test_source_zip_duplicate_handling(client):
    """Verify that duplicate files are skipped when overwrite=False and updated when overwrite=True."""
    res_proj = client.post("/api/v1/projects", json={"name": "Duplicate Zip Test"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    files_v1 = {"src/app.c": "int v1(void) { return 1; }"}
    zip_v1 = base64.b64encode(_create_zip_buffer(files_v1)).decode("utf-8")

    res1 = client.post(f"/api/v1/projects/{proj_id}/sources/import-zip", json={
        "archive_base64": zip_v1,
        "overwrite": False,
    })
    assert res1.status_code == 201
    assert res1.json()["imported_sources"] == 1

    # Second import without overwrite -> skipped
    files_v2 = {"src/app.c": "int v2(void) { return 2; }"}
    zip_v2 = base64.b64encode(_create_zip_buffer(files_v2)).decode("utf-8")

    res2 = client.post(f"/api/v1/projects/{proj_id}/sources/import-zip", json={
        "archive_base64": zip_v2,
        "overwrite": False,
    })
    assert res2.status_code == 201
    assert res2.json()["skipped_files"] == 1
    assert res2.json()["imported_sources"] == 0

    # Third import with overwrite -> updated
    res3 = client.post(f"/api/v1/projects/{proj_id}/sources/import-zip", json={
        "archive_base64": zip_v2,
        "overwrite": True,
    })
    assert res3.status_code == 201
    assert res3.json()["imported_sources"] == 1
    assert "int v2" in res3.json()["files"][0]["content"]
