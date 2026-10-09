from datetime import datetime, timezone
import pytest
from apps.api.app.schemas.sentinel_api import ExecutionResponse, ExecutionStatus


def test_execution_response_schema_compatibility():
    """Verify that ExecutionResponse synchronizes id and execution_id bi-directionally."""
    now = datetime.now(timezone.utc)

    # Case 1: Initialized with execution_id only
    resp1 = ExecutionResponse(
        execution_id="exec-001",
        project_id="proj-001",
        status=ExecutionStatus.PASSED,
        results_summary={},
        created_at=now,
    )
    assert resp1.id == "exec-001"
    assert resp1.execution_id == "exec-001"
    dump1 = resp1.model_dump()
    assert dump1["id"] == "exec-001"
    assert dump1["execution_id"] == "exec-001"

    # Case 2: Initialized with id only
    resp2 = ExecutionResponse(
        id="exec-002",
        project_id="proj-001",
        status=ExecutionStatus.PASSED,
        results_summary={},
        created_at=now,
    )
    assert resp2.id == "exec-002"
    assert resp2.execution_id == "exec-002"
    dump2 = resp2.model_dump()
    assert dump2["id"] == "exec-002"
    assert dump2["execution_id"] == "exec-002"

    # Case 3: Initialized with both
    resp3 = ExecutionResponse(
        id="exec-003",
        execution_id="exec-003",
        project_id="proj-001",
        status=ExecutionStatus.PASSED,
        results_summary={},
        created_at=now,
    )
    assert resp3.id == "exec-003"
    assert resp3.execution_id == "exec-003"


def test_list_test_suites_nonexistent_project(client):
    """Verify that listing test suites for a non-existent project returns 404."""
    res = client.get("/api/v1/projects/nonexistent-proj-uuid-9999/test-suites")
    assert res.status_code == 404
    err = res.json()
    assert err["error"]["code"] == "PROJECT_NOT_FOUND"


def test_list_test_suites_empty(client):
    """Verify that a valid project with no test suites returns an empty list []."""
    res = client.post("/api/v1/projects", json={
        "name": "Empty Suite Project",
        "description": "Testing empty test suites list"
    })
    assert res.status_code == 201
    proj_id = res.json()["id"]

    res_suites = client.get(f"/api/v1/projects/{proj_id}/test-suites")
    assert res_suites.status_code == 200
    assert res_suites.json() == []


def test_list_test_suites_with_suites_and_isolation(client):
    """Verify that created test suites are listed properly and isolated across projects."""
    # 1. Create Project A
    res_a = client.post("/api/v1/projects", json={
        "name": "Project Alpha",
        "description": "Isolation Test Project A"
    })
    assert res_a.status_code == 201
    proj_a_id = res_a.json()["id"]

    # 2. Create Project B
    res_b = client.post("/api/v1/projects", json={
        "name": "Project Beta",
        "description": "Isolation Test Project B"
    })
    assert res_b.status_code == 201
    proj_b_id = res_b.json()["id"]

    # 3. Add suites to Project A
    res_s_a1 = client.post(f"/api/v1/projects/{proj_a_id}/test-suites", json={
        "name": "Suite A1",
        "description": "Alpha Suite 1"
    })
    assert res_s_a1.status_code == 201
    suite_a1_id = res_s_a1.json()["id"]

    res_s_a2 = client.post(f"/api/v1/projects/{proj_a_id}/test-suites", json={
        "name": "Suite A2",
        "description": "Alpha Suite 2"
    })
    assert res_s_a2.status_code == 201
    suite_a2_id = res_s_a2.json()["id"]

    # 4. Add suite to Project B
    res_s_b1 = client.post(f"/api/v1/projects/{proj_b_id}/test-suites", json={
        "name": "Suite B1",
        "description": "Beta Suite 1"
    })
    assert res_s_b1.status_code == 201
    suite_b1_id = res_s_b1.json()["id"]

    # 5. Retrieve Project A suites and verify isolation
    res_list_a = client.get(f"/api/v1/projects/{proj_a_id}/test-suites")
    assert res_list_a.status_code == 200
    suites_a = res_list_a.json()
    assert len(suites_a) == 2
    suite_a_ids = {s["id"] for s in suites_a}
    assert suite_a1_id in suite_a_ids
    assert suite_a2_id in suite_a_ids
    assert suite_b1_id not in suite_a_ids

    # Verify attributes
    for s in suites_a:
        assert s["project_id"] == proj_a_id
        assert "name" in s
        assert "description" in s

    # 6. Retrieve Project B suites and verify isolation
    res_list_b = client.get(f"/api/v1/projects/{proj_b_id}/test-suites")
    assert res_list_b.status_code == 200
    suites_b = res_list_b.json()
    assert len(suites_b) == 1
    assert suites_b[0]["id"] == suite_b1_id
    assert suites_b[0]["project_id"] == proj_b_id
    assert suites_b[0]["name"] == "Suite B1"


def test_execution_api_id_and_execution_id_matching(client):
    """Verify that execution endpoints return identical id and execution_id values."""
    # 1. Create Project
    res = client.post("/api/v1/projects", json={
        "name": "Execution ID Regression Project",
        "description": "Testing ExecutionResponse id field"
    })
    assert res.status_code == 201
    proj_id = res.json()["id"]

    # 2. Upload and analyze source
    c_source = "int simple_func(void) { return 42; }"
    res_src = client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "simple.c",
        "content": c_source,
        "is_target": True
    })
    assert res_src.status_code == 201
    source_id = res_src.json()["id"]

    res_an = client.post(f"/api/v1/projects/{proj_id}/analyze")
    assert res_an.status_code == 200
    fn_id = res_an.json()["functions"][0]["id"]

    # 3. Configure scope
    res_sc = client.post(f"/api/v1/projects/{proj_id}/scope", json={
        "target_function_id": fn_id,
        "target_source_id": source_id,
        "environment_source_ids": []
    })
    assert res_sc.status_code == 200

    # 4. Create test case
    res_tc = client.post(f"/api/v1/projects/{proj_id}/test-cases", json={
        "name": "TC-Simple",
        "target_function_id": fn_id,
        "vectors": [
            {
                "vector_index": 1,
                "inputs": {},
                "expected_outputs": {"return": 42}
            }
        ]
    })
    assert res_tc.status_code == 201
    tc_id = res_tc.json()["id"]

    # 5. Trigger execution (POST)
    res_exec = client.post(f"/api/v1/projects/{proj_id}/executions", json={
        "test_case_id": tc_id,
        "timeout_seconds": 10
    })
    assert res_exec.status_code == 201
    exec_data = res_exec.json()
    assert "id" in exec_data
    assert "execution_id" in exec_data
    assert exec_data["id"] == exec_data["execution_id"]
    persisted_id = exec_data["id"]

    # 6. Retrieve execution (GET)
    res_get = client.get(f"/api/v1/projects/{proj_id}/executions/{persisted_id}")
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["id"] == persisted_id
    assert get_data["execution_id"] == persisted_id
    assert get_data["id"] == get_data["execution_id"]
