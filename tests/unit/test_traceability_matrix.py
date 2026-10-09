import pytest


def test_traceability_suggestion_and_matrix(client):
    """Verify requirement-to-code traceability suggestion, confirmation, matrix query and export."""
    # 1. Create project
    res_proj = client.post("/api/v1/projects", json={"name": "Traceability Matrix Test"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    # 2. Upload source code
    c_source = """
    int cabin_pressure_control(int pressure, int altitude) {
        if (pressure > 900 && altitude < 10000) return 1;
        return 0;
    }
    """
    res_src = client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "cabin_pressure.c",
        "content": c_source,
        "is_target": True
    })
    src_id = res_src.json()["id"]

    # 3. Analyze source
    res_an = client.post(f"/api/v1/projects/{proj_id}/analyze")
    assert res_an.status_code == 200
    assert "id" in res_an.json()
    assert res_an.json()["id"] == proj_id
    fn_id = res_an.json()["functions"][0]["id"]
    fn_name = res_an.json()["functions"][0]["name"]

    # 4. Create Requirement mentioning cabin_pressure_control, pressure, altitude
    res_req = client.post(f"/api/v1/projects/{proj_id}/requirements", json={
        "identifier": "HLR-101",
        "title": "Cabin Pressure Nominal Control",
        "description": "The function cabin_pressure_control shall regulate pressure and altitude to safe limits.",
        "acceptance_criteria": "Returns 1 when nominal",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # 5. Suggest Traceability Links (symbol & keyword overlap)
    res_sug = client.post(f"/api/v1/projects/{proj_id}/traceability/suggest", json={
        "confidence_threshold": 0.4
    })
    assert res_sug.status_code == 201
    suggestions = res_sug.json()
    assert len(suggestions) >= 1
    sug_link = suggestions[0]
    assert sug_link["requirement_id"] == req_id
    assert sug_link["function_id"] == fn_id
    assert sug_link["status"] == "SUGGESTED"
    assert sug_link["confidence_score"] > 0.5
    link_id = sug_link["id"]

    # 6. Confirm Link (Human review)
    res_conf = client.put(f"/api/v1/projects/{proj_id}/traceability/links/{link_id}?status_str=CONFIRMED")
    assert res_conf.status_code == 200
    assert res_conf.json()["status"] == "CONFIRMED"

    # 7. Configure Scope via PUT /scope (Frontend compatibility test)
    res_scope = client.put(f"/api/v1/projects/{proj_id}/scope", json={
        "target_function_id": fn_id,
        "target_source_id": src_id,
    })
    assert res_scope.status_code == 200
    scope_data = res_scope.json()
    assert "selectedFunctions" in scope_data
    assert "selected_functions" in scope_data
    assert scope_data["target_function_name"] == "cabin_pressure_control"

    # 8. Create Test Case & Vector
    res_tc = client.post(f"/api/v1/projects/{proj_id}/test-cases", json={
        "name": "TC-Pressure-01",
        "target_function_id": fn_id,
        "requirement_id": req_id,
        "vectors": [
            {
                "vector_index": 1,
                "inputs": {"pressure": 950, "altitude": 8000},
                "expected_outputs": {"return": 1}
            }
        ]
    })
    assert res_tc.status_code == 201
    tc_id = res_tc.json()["id"]

    # 9. Execute Test
    res_ex = client.post(f"/api/v1/projects/{proj_id}/executions", json={
        "test_case_id": tc_id,
    })
    assert res_ex.status_code == 201
    exec_id = res_ex.json()["id"]

    # 10. Check Coverage Response frontend fields
    res_cov = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/coverage")
    assert res_cov.status_code == 200
    cov_data = res_cov.json()
    assert "statement" in cov_data
    assert "decision" in cov_data
    assert cov_data["statement"] == cov_data["statement_coverage_pct"]

    # 11. Check Traceability Graph links for frontend
    res_graph = client.get(f"/api/v1/projects/{proj_id}/traceability")
    assert res_graph.status_code == 200
    graph_data = res_graph.json()
    assert "links" in graph_data
    assert len(graph_data["links"]) >= 1
    assert graph_data["links"][0]["reqId"] == "HLR-101"

    # 12. Check Project-level Evidence endpoints
    res_ev = client.get(f"/api/v1/projects/{proj_id}/evidence")
    assert res_ev.status_code == 200
    ev_data = res_ev.json()
    assert "generatedAt" in ev_data
    assert "freshness" in ev_data
    assert ev_data["freshness"] == "CURRENT"

    # 13. Query Full Traceability Matrix
    res_mat = client.get(f"/api/v1/projects/{proj_id}/traceability/matrix")
    assert res_mat.status_code == 200
    matrix_data = res_mat.json()
    assert len(matrix_data["matrix"]) == 1
    item = matrix_data["matrix"][0]
    assert item["requirement"]["identifier"] == "HLR-101"
    assert len(item["linked_functions"]) >= 1
    assert item["linked_functions"][0]["function_name"] == "cabin_pressure_control"
    assert len(item["test_cases"]) == 1
    assert len(item["executions"]) == 1

    # 14. Export Matrix in Markdown & CSV
    res_exp_md = client.get(f"/api/v1/projects/{proj_id}/traceability/export?format=md")
    assert res_exp_md.status_code == 200
    assert "HLR-101" in res_exp_md.text

    res_exp_csv = client.get(f"/api/v1/projects/{proj_id}/traceability/export?format=csv")
    assert res_exp_csv.status_code == 200
    assert "HLR-101" in res_exp_csv.text
