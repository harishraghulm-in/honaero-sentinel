def test_full_api_workflow(client):
    # 1. Create Project
    res = client.post("/api/v1/projects", json={
        "name": "Cabin Pressure API Test",
        "description": "DO-178C Verification Pipeline Test"
    })
    assert res.status_code == 201
    proj_data = res.json()
    proj_id = proj_data["id"]

    # 2. Upload Source Code
    c_source = """
    int sensor_read(void);

    int cabin_pressure_control(int pressure, int altitude)
    {
        int sensor = sensor_read();
        if (pressure > 900 && altitude < 10000 && sensor > 900)
            return 1;

        return 0;
    }
    """
    res = client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "cabin_pressure.c",
        "content": c_source,
        "is_target": True
    })
    assert res.status_code == 201
    source_id = res.json()["id"]

    # 3. Analyze Source
    res = client.post(f"/api/v1/projects/{proj_id}/analyze")
    assert res.status_code == 200
    analysis = res.json()
    assert len(analysis["functions"]) == 1
    fn_id = analysis["functions"][0]["id"]
    assert analysis["functions"][0]["name"] == "cabin_pressure_control"
    assert len(analysis["dependencies"]) == 1
    dep_id = analysis["dependencies"][0]["id"]
    assert analysis["dependencies"][0]["name"] == "sensor_read"

    # 4. Scope Selection
    res = client.post(f"/api/v1/projects/{proj_id}/scope", json={
        "target_function_id": fn_id,
        "target_source_id": source_id,
        "environment_source_ids": []
    })
    assert res.status_code == 200
    assert res.json()["target_function_name"] == "cabin_pressure_control"

    # 5. Dependency & Stub Configuration
    res = client.post(f"/api/v1/projects/{proj_id}/stubs", json={
        "dependency_id": dep_id,
        "function_name": "sensor_read",
        "mode": "STUB",
        "return_values": [950, 950, 950],
        "expected_call_count": 3
    })
    assert res.status_code == 201
    stub_id = res.json()["id"]

    # 6. Author Test Case & Vectors
    res = client.post(f"/api/v1/projects/{proj_id}/test-cases", json={
        "name": "TC-001 High Altitude Pressure Vector",
        "target_function_id": fn_id,
        "vectors": [
            {
                "vector_index": 1,
                "inputs": {"pressure": 950, "altitude": 8000},
                "expected_outputs": {"return": 1}
            },
            {
                "vector_index": 2,
                "inputs": {"pressure": 850, "altitude": 8000},
                "expected_outputs": {"return": 0}
            }
        ]
    })
    assert res.status_code == 201
    tc_id = res.json()["id"]

    # 7. Trigger Execution Pipeline
    res = client.post(f"/api/v1/projects/{proj_id}/executions", json={
        "test_case_id": tc_id,
        "timeout_seconds": 10
    })
    assert res.status_code == 201
    exec_data = res.json()
    exec_id = exec_data["execution_id"]
    assert exec_data["id"] == exec_id
    assert exec_data["status"] == "PASSED"
    assert exec_data["exit_code"] == 0

    # 8. Query Coverage
    res = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/coverage")
    assert res.status_code == 200
    cov = res.json()
    assert cov["statement_coverage_pct"] > 0

    # 9. Query MC/DC Analysis
    res = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/mcdc")
    assert res.status_code == 200
    mcdc = res.json()
    assert "decisions" in mcdc

    # 10. Query Traceability Graph
    res = client.get(f"/api/v1/projects/{proj_id}/traceability")
    assert res.status_code == 200
    trace = res.json()
    assert len(trace["nodes"]) > 0

    # 11. Query Evidence Record
    res = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/evidence")
    assert res.status_code == 200
    evid = res.json()
    assert evid["freshness"] == "CURRENT"
    assert evid["evidence_data"]["target_function"] == "cabin_pressure_control"

    # 12. Export Evidence (JSON & Markdown)
    res_json = client.post(f"/api/v1/projects/{proj_id}/executions/{exec_id}/evidence/export?format=json")
    assert res_json.status_code == 200

    res_md = client.post(f"/api/v1/projects/{proj_id}/executions/{exec_id}/evidence/export?format=md")
    assert res_md.status_code == 200
