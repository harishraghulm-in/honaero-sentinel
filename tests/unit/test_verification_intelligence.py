import io
import zipfile
import base64
import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_file_tree_and_source_content_api(client: TestClient):
    # 1. Create project
    res_proj = client.post("/api/v1/projects", json={
        "name": "Avionics Display Controller",
        "description": "DO-178C Level A display software"
    })
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    # 2. Add multiple nested source files
    src1 = client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "display.c",
        "filepath": "src/display/display.c",
        "content": "int render_display(int mode) { if (mode > 0) return 1; return 0; }",
        "is_target": True
    })
    assert src1.status_code == 201
    src1_id = src1.json()["id"]

    src2 = client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "display.h",
        "filepath": "include/display.h",
        "content": "int render_display(int mode);",
        "is_target": False
    })
    assert src2.status_code == 201

    # 3. Analyze to extract functions
    res_an = client.post(f"/api/v1/projects/{proj_id}/analyze")
    assert res_an.status_code == 200

    # 4. Request file tree
    res_tree = client.get(f"/api/v1/projects/{proj_id}/file-tree")
    assert res_tree.status_code == 200
    tree_data = res_tree.json()
    assert tree_data["project_id"] == proj_id
    assert tree_data["total_files"] == 2
    assert tree_data["total_directories"] >= 2
    assert len(tree_data["tree"]) >= 2

    # Verify hierarchical structure
    dir_names = [n["name"] for n in tree_data["tree"]]
    assert "src" in dir_names or "include" in dir_names

    # 5. Test source content by ID
    res_content = client.get(f"/api/v1/projects/{proj_id}/sources/{src1_id}/content")
    assert res_content.status_code == 200
    content_obj = res_content.json()
    assert content_obj["id"] == src1_id
    assert "render_display" in content_obj["content"]
    assert content_obj["lines_of_code"] >= 1
    assert content_obj["size_bytes"] > 0

    # 6. Test source content by relative path
    res_by_path = client.get(f"/api/v1/projects/{proj_id}/sources/by-path", params={"path": "src/display/display.c"})
    assert res_by_path.status_code == 200
    assert res_by_path.json()["id"] == src1_id


def test_test_prioritization_and_override_workflow(client: TestClient):
    # 1. Create project
    res_proj = client.post("/api/v1/projects", json={
        "name": "Flight Management Prioritization Test",
        "description": "Prioritization test"
    })
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    # 2. Add source
    res_src = client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "nav_computer.c",
        "filepath": "src/nav_computer.c",
        "content": """
        int compute_waypoint(int alt, int speed) {
            if (alt > 10000 && speed > 250) {
                return 1;
            } else if (alt <= 10000 && speed <= 250) {
                return 2;
            }
            return 0;
        }
        """,
        "is_target": True
    })
    assert res_src.status_code == 201

    res_an = client.post(f"/api/v1/projects/{proj_id}/analyze")
    assert res_an.status_code == 200
    fn_id = res_an.json()["functions"][0]["id"]

    # 3. Add requirement (Level A)
    res_req = client.post(f"/api/v1/projects/{proj_id}/requirements", json={
        "identifier": "REQ-NAV-001",
        "title": "Waypoint Altitude Logic",
        "description": "Level A safety critical waypoint computation constraint.",
        "req_type": "HLR",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # 4. Add test suite and 2 test cases
    res_suite = client.post(f"/api/v1/projects/{proj_id}/test-suites", json={
        "name": "Navigation Suite",
        "description": "Suite 1"
    })
    suite_id = res_suite.json()["id"]

    res_tc1 = client.post(f"/api/v1/projects/{proj_id}/test-cases", json={
        "test_suite_id": suite_id,
        "target_function_id": fn_id,
        "requirement_id": req_id,
        "name": "TC_Nav_Critical_HighAlt",
        "inputs": {"alt": 12000, "speed": 300},
        "expected_outputs": {"return": 1}
    })
    tc1_id = res_tc1.json()["id"]

    res_tc2 = client.post(f"/api/v1/projects/{proj_id}/test-cases", json={
        "test_suite_id": suite_id,
        "target_function_id": fn_id,
        "name": "TC_Nav_LowPriority_Default",
        "inputs": {"alt": 5000, "speed": 200},
        "expected_outputs": {"return": 2}
    })
    tc2_id = res_tc2.json()["id"]

    # 5. Check initial prioritization (tc1 has Level A requirement so it should rank higher)
    res_prio = client.get(f"/api/v1/projects/{proj_id}/prioritization")
    assert res_prio.status_code == 200
    prio_data = res_prio.json()
    assert prio_data["total_ranked_items"] == 2
    items = prio_data["priorities"]
    assert items[0]["priority_rank"] == 1
    assert items[0]["item_id"] == tc1_id  # Ranked #1 due to Level A requirement
    assert items[0]["safety_criticality"] == "LEVEL_A"
    assert "REQ-NAV-001" in items[0]["rationale"]

    # 6. Apply manual override on tc2 to elevate it to HIGH
    res_over = client.put(f"/api/v1/projects/{proj_id}/prioritization/override", json={
        "target_id": tc2_id,
        "manual_priority": "HIGH",
        "manual_score": 98.5,
        "override_reason": "Flight test squawk #402 requires immediate retest priority"
    })
    assert res_over.status_code == 200
    assert res_over.json()["manual_score"] == 98.5

    # 7. Verify prioritization re-ranks tc2 to #1
    res_prio2 = client.get(f"/api/v1/projects/{proj_id}/prioritization")
    assert res_prio2.status_code == 200
    items2 = res_prio2.json()["priorities"]
    assert items2[0]["item_id"] == tc2_id
    assert items2[0]["priority_rank"] == 1
    assert items2[0]["priority_score"] == 98.5
    assert items2[0]["is_overridden"] is True
    assert "Flight test squawk" in items2[0]["override_reason"]

    # 8. Delete override
    res_del = client.delete(f"/api/v1/projects/{proj_id}/prioritization/override/{tc2_id}")
    assert res_del.status_code == 204

    # 9. Verify reverted priority ranking
    res_prio3 = client.get(f"/api/v1/projects/{proj_id}/prioritization")
    assert res_prio3.status_code == 200
    assert res_prio3.json()["priorities"][0]["item_id"] == tc1_id


def test_execution_events_sse_stream(client: TestClient):
    # 1. Create project & test case
    res_proj = client.post("/api/v1/projects", json={
        "name": "SSE Event Stream Project",
        "description": "SSE testing"
    })
    proj_id = res_proj.json()["id"]

    res_src = client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "simple.c",
        "filepath": "src/simple.c",
        "content": "int simple_check(int x) { return x + 1; }",
        "is_target": True
    })
    res_an = client.post(f"/api/v1/projects/{proj_id}/analyze")
    fn_id = res_an.json()["functions"][0]["id"]

    res_suite = client.post(f"/api/v1/projects/{proj_id}/test-suites", json={"name": "Suite S"})
    suite_id = res_suite.json()["id"]

    res_tc = client.post(f"/api/v1/projects/{proj_id}/test-cases", json={
        "test_suite_id": suite_id,
        "target_function_id": fn_id,
        "name": "TC_Simple_Passing",
        "inputs": {"x": 5},
        "expected_outputs": {"return": 6}
    })
    tc_id = res_tc.json()["id"]

    # Execute test
    res_exec = client.post(f"/api/v1/projects/{proj_id}/executions", json={
        "test_case_id": tc_id,
        "timeout_seconds": 10
    })
    assert res_exec.status_code == 201
    exec_id = res_exec.json()["id"]

    # Stream SSE events
    res_events = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/events")
    assert res_events.status_code == 200
    assert "text/event-stream" in res_events.headers["content-type"]
    body = res_events.text
    assert "event: stage" in body
    assert "QUEUED" in body
    assert "BUILDING" in body
    assert "RUNNING" in body
    assert "COVERAGE_ANALYSIS" in body
    assert "event: completed" in body
    assert "COMPLETED" in body


def test_project_verification_report(client: TestClient):
    # 1. Create project
    res_proj = client.post("/api/v1/projects", json={
        "name": "Full Audit Verification Report Project",
        "description": "DO-178C Report Generation"
    })
    proj_id = res_proj.json()["id"]

    # 2. Add requirement
    client.post(f"/api/v1/projects/{proj_id}/requirements", json={
        "identifier": "REQ-AUDIT-01",
        "title": "Audit Compliance Check",
        "description": "Full verification check",
        "req_type": "HLR",
    })

    # 3. Add source and analyze
    client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "audit.c",
        "filepath": "src/audit.c",
        "content": "int audit_func(int a) { return a * 2; }",
        "is_target": True
    })
    client.post(f"/api/v1/projects/{proj_id}/analyze")

    # 4. Fetch project report
    res_rep = client.get(f"/api/v1/projects/{proj_id}/report")
    assert res_rep.status_code == 200
    rep = res_rep.json()
    assert rep["project_id"] == proj_id
    assert "DO-178C" in rep["compliance_standard"]
    assert rep["sources"]["total_sources"] == 1
    assert rep["sources"]["total_functions"] == 1
    assert rep["requirements"]["total_requirements"] == 1
    assert len(rep["audit_findings"]) >= 1
    assert len(rep["limitations_and_disclaimers"]) >= 2


def test_large_multi_file_archive_ingestion_scaling(client: TestClient):
    # 1. Create project
    res_proj = client.post("/api/v1/projects", json={
        "name": "Multi-File Archive Scaling Project",
        "description": "Ingests 60 source files safely"
    })
    proj_id = res_proj.json()["id"]

    # 2. Build a ZIP archive with 60 distinct C source files
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, 61):
            fn_code = f"int module_{i}_process(int val) {{ return val + {i}; }}\n"
            zf.writestr(f"modules/subsys_{i % 5}/mod_{i}.c", fn_code)
            zf.writestr(f"include/mod_{i}.h", f"int module_{i}_process(int val);\n")

    zip_bytes = zip_buf.getvalue()
    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")

    # 3. Import ZIP archive
    res_import = client.post(f"/api/v1/projects/{proj_id}/sources/import-zip", json={
        "archive_base64": zip_b64,
        "archive_format": "zip"
    })
    assert res_import.status_code == 201
    import_data = res_import.json()
    assert import_data["imported_sources"] == 120  # 60 .c files + 60 .h files

    # 4. Verify file tree representation contains all modules
    res_tree = client.get(f"/api/v1/projects/{proj_id}/file-tree")
    assert res_tree.status_code == 200
    tree_data = res_tree.json()
    assert tree_data["total_files"] == 120
    assert tree_data["total_directories"] >= 6  # modules, subsys_0..4, include
