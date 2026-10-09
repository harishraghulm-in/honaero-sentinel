"""End-to-end integration test verifying the complete HonAero Sentinel verification workflow.

Workflow:
Requirement document -> structured requirements -> candidate test cases ->
human review -> source project import (multi-file ZIP) -> analysis ->
requirement-to-code traceability -> execution (real GCC compilation & runner) ->
real results -> coverage/MC/DC evidence -> report export.
"""

import base64
import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app




def test_full_end_to_end_verification_workflow(client):
    # -------------------------------------------------------------------------
    # Step 1: Create Project
    # -------------------------------------------------------------------------
    res_proj = client.post("/api/v1/projects", json={
        "name": "Cabin Pressure DO-178C System Verification",
        "description": "Full lifecycle verification of environmental cabin pressure controller.",
    })
    assert res_proj.status_code == 201
    proj_data = res_proj.json()
    proj_id = proj_data["id"]
    assert proj_id is not None

    # -------------------------------------------------------------------------
    # Step 2: Upload Requirement Document (.md)
    # -------------------------------------------------------------------------
    spec_markdown = """# Section 3.1 Cabin Pressure System

## HLR-CP-001: Cabin Pressure Regulation
When cabin pressure is above 900 hPa and flight altitude is below 10000 ft, cabin_pressure_control shall return 1.
Acceptance Criteria: cabin_pressure_control returns 1 when pressure > 900 and altitude < 10000.
Verification Method: TEST

## HLR-CP-002: Variable Valve Modulation
The outflow valve shall modulate appropriately as needed.
Acceptance Criteria: System adjusts airflow.
Verification Method: TEST
"""
    res_doc = client.post(f"/api/v1/projects/{proj_id}/requirements/documents", json={
        "filename": "cabin_pressure_spec.md",
        "content": spec_markdown,
        "revision": "1.0",
    })
    assert res_doc.status_code == 201
    doc_id = res_doc.json()["id"]

    # -------------------------------------------------------------------------
    # Step 3: Extract Structured Requirements & Verify Ambiguity Analysis
    # -------------------------------------------------------------------------
    res_ext = client.post(f"/api/v1/projects/{proj_id}/requirements/extract?document_id={doc_id}")
    assert res_ext.status_code == 201
    extracted_reqs = res_ext.json()
    assert len(extracted_reqs) == 2

    hlr1 = next(r for r in extracted_reqs if r["identifier"] == "HLR-CP-001")
    assert hlr1["ambiguity_status"] == "CLEAR"
    assert hlr1["section"] == "3.1 Cabin Pressure System"
    req1_id = hlr1["id"]

    hlr2 = next(r for r in extracted_reqs if r["identifier"] == "HLR-CP-002")
    assert hlr2["ambiguity_status"] == "AMBIGUOUS"
    assert len(hlr2["ambiguity_notes"]) > 0

    # -------------------------------------------------------------------------
    # Step 4: Import Multi-File C Source Code via ZIP Archive
    #         Preserving directory hierarchy: include/cabin.h, drivers/sensor.c, src/cabin.c
    # -------------------------------------------------------------------------
    header_content = """#ifndef CABIN_H
#define CABIN_H

int sensor_read(void);
int cabin_pressure_control(int pressure, int altitude);

#endif // CABIN_H
"""
    sensor_driver = """#include "cabin.h"

int sensor_read(void) {
    return 0; // Default hardware reading
}
"""
    cabin_c = """#include "cabin.h"

int cabin_pressure_control(int pressure, int altitude) {
    int sensor = sensor_read();
    if (pressure > 900 && altitude < 10000 && sensor > 900) {
        return 1;
    }
    return 0;
}
"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("include/cabin.h", header_content)
        zf.writestr("drivers/sensor.c", sensor_driver)
        zf.writestr("src/cabin_pressure.c", cabin_c)
    zip_b64 = base64.b64encode(zip_buffer.getvalue()).decode("utf-8")

    res_zip = client.post(f"/api/v1/projects/{proj_id}/sources/import-zip", json={
        "archive_base64": zip_b64,
        "archive_format": "zip",
    })
    assert res_zip.status_code == 201
    zip_data = res_zip.json()
    assert zip_data["imported_sources"] == 3
    imported_paths = [f["filepath"] for f in zip_data["files"]]
    assert "src/cabin_pressure.c" in imported_paths
    assert "include/cabin.h" in imported_paths

    # -------------------------------------------------------------------------
    # Step 5: Static Analysis of Imported Sources
    # -------------------------------------------------------------------------
    res_analysis = client.post(f"/api/v1/projects/{proj_id}/analyze")
    assert res_analysis.status_code == 200
    analysis_data = res_analysis.json()
    assert len(analysis_data["functions"]) >= 1

    fn_obj = next(f for f in analysis_data["functions"] if f["name"] == "cabin_pressure_control")
    fn_id = fn_obj["id"]
    assert fn_obj["return_type"] == "int"
    param_names = [p["name"] for p in fn_obj["parameters"]]
    assert "pressure" in param_names
    assert "altitude" in param_names

    dep_obj = next(d for d in analysis_data["dependencies"] if d["name"] == "sensor_read")
    dep_id = dep_obj["id"]

    # -------------------------------------------------------------------------
    # Step 6: Generate Candidate Test Cases from Requirements
    # -------------------------------------------------------------------------
    res_cands = client.post(
        f"/api/v1/projects/{proj_id}/requirements/{req1_id}/generate-candidates?target_function_name=cabin_pressure_control"
    )
    assert res_cands.status_code == 201
    candidates = res_cands.json()
    assert len(candidates) >= 3

    nominal_cand = next(c for c in candidates if c["case_category"] == "NORMAL")
    assert nominal_cand["approval_status"] == "PENDING_REVIEW"
    assert nominal_cand["input_vectors"][0]["inputs"]["pressure"] > 900
    assert nominal_cand["input_vectors"][0]["inputs"]["altitude"] < 10000
    assert nominal_cand["input_vectors"][0]["expected_outputs"]["return"] == 1

    # -------------------------------------------------------------------------
    # Step 7: Human Approval -> Promote Candidate to Executable Test Case
    # -------------------------------------------------------------------------
    res_appr = client.post(
        f"/api/v1/projects/{proj_id}/candidate-test-cases/{nominal_cand['id']}/approve",
        json={"target_function_id": fn_id},
    )
    assert res_appr.status_code == 201
    test_case = res_appr.json()
    tc_id = test_case["id"]
    assert test_case["target_function_id"] == fn_id
    assert test_case["requirement_id"] == req1_id

    # -------------------------------------------------------------------------
    # Step 8: Configure Scope & Dependencies/Stubs
    # -------------------------------------------------------------------------
    res_scope = client.put(f"/api/v1/projects/{proj_id}/scope", json={
        "target_function_id": fn_id,
        "selected_functions": ["cabin_pressure_control"],
    })
    assert res_scope.status_code == 200

    # Configure sensor_read stub to return 950 (sensor reading above threshold)
    res_stub = client.post(f"/api/v1/projects/{proj_id}/stubs", json={
        "dependency_id": dep_id,
        "function_name": "sensor_read",
        "mode": "STUB",
        "return_values": [950, 950, 950],
        "expected_call_count": 1,
    })
    assert res_stub.status_code == 201

    # -------------------------------------------------------------------------
    # Step 9: Suggest and Establish Traceability Link
    # -------------------------------------------------------------------------
    res_sug = client.post(f"/api/v1/projects/{proj_id}/traceability/suggest")
    assert res_sug.status_code == 201
    suggestions = res_sug.json()
    assert len(suggestions) >= 1
    link_id = suggestions[0]["id"]

    res_confirm = client.put(
        f"/api/v1/projects/{proj_id}/traceability/links/{link_id}?status_str=CONFIRMED"
    )
    assert res_confirm.status_code == 200
    assert res_confirm.json()["status"] == "CONFIRMED"

    # -------------------------------------------------------------------------
    # Step 10: Real GCC Compilation & Execution via Local Engine
    # -------------------------------------------------------------------------
    res_exec = client.post(f"/api/v1/projects/{proj_id}/executions", json={
        "test_case_id": tc_id,
        "timeout_seconds": 10,
    })
    assert res_exec.status_code == 201
    exec_data = res_exec.json()
    exec_id = exec_data["id"]
    assert exec_data["status"] == "PASSED"
    assert exec_data["exit_code"] == 0

    # -------------------------------------------------------------------------
    # Step 11: Retrieve Coverage, MC/DC, Traceability Matrix & Evidence Export
    # -------------------------------------------------------------------------
    # Coverage
    res_cov = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/coverage")
    assert res_cov.status_code == 200
    cov_data = res_cov.json()
    assert cov_data["statement_coverage_pct"] > 0
    assert cov_data["statement"] == cov_data["statement_coverage_pct"]

    # MC/DC
    res_mcdc = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/mcdc")
    assert res_mcdc.status_code == 200
    mcdc_data = res_mcdc.json()
    assert "decisions" in mcdc_data
    assert len(mcdc_data["decisions"]) >= 1
    assert "conditions" in mcdc_data["decisions"][0]
    assert "gap_recommendations" in mcdc_data

    # Traceability Matrix
    res_trace = client.get(f"/api/v1/projects/{proj_id}/traceability")
    assert res_trace.status_code == 200
    trace_data = res_trace.json()
    assert "links" in trace_data
    assert len(trace_data["links"]) >= 1
    assert any(l["reqId"] == "HLR-CP-001" for l in trace_data["links"])

    # Traceability Matrix Export
    res_mat_exp = client.get(f"/api/v1/projects/{proj_id}/traceability/matrix/export?format=json")
    assert res_mat_exp.status_code == 200
    mat_records = res_mat_exp.json()["matrix"]
    assert len(mat_records) >= 1
    assert mat_records[0]["requirement"]["identifier"] == "HLR-CP-001"

    # Project Evidence & Export
    res_ev = client.get(f"/api/v1/projects/{proj_id}/evidence")
    assert res_ev.status_code == 200
    ev_data = res_ev.json()
    assert ev_data["freshness"] == "CURRENT"
    assert ev_data["source_checksum"] is not None

    # Evidence Export (JSON and Markdown)
    res_exp_json = client.get(f"/api/v1/projects/{proj_id}/evidence/export?format=json")
    assert res_exp_json.status_code == 200

    res_exp_md = client.get(f"/api/v1/projects/{proj_id}/evidence/export?format=md")
    assert res_exp_md.status_code == 200
    assert len(res_exp_md.content) > 0


def test_regression_rerun_config_and_diagnostics_workflow(client):
    """Verifies build config management, failure diagnostics, regression comparison, historical rerun, and AI assistant."""
    # 1. Create project
    res_proj = client.post("/api/v1/projects", json={
        "name": "Actuator Flight Control Integration",
        "description": "Integration testing for flight control actuator with fail-safe logic."
    })
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    # 2. Compiler configuration GET and PUT
    res_cfg_get = client.get(f"/api/v1/projects/{proj_id}/config")
    assert res_cfg_get.status_code == 200
    cfg = res_cfg_get.json()
    assert "compiler" in cfg
    assert "cStandard" in cfg

    res_cfg_put = client.put(f"/api/v1/projects/{proj_id}/config", json={
        "compiler": "gcc",
        "optimization": "-O0",
        "warnings": ["-Wall", "-Wextra"],
        "defines": ["SENTINEL_SIM=1"],
        "includeDirs": ["include"],
        "cStandard": "c11"
    })
    assert res_cfg_put.status_code == 200
    updated_cfg = res_cfg_put.json()
    assert updated_cfg["optimization"] == "-O0"
    assert "SENTINEL_SIM=1" in updated_cfg["defines"]

    # 3. AI assistant endpoints
    res_models = client.get("/api/v1/ai/models")
    assert res_models.status_code == 200
    models = res_models.json()
    assert len(models) >= 1
    assert any("nim" in m["id"] or "llama" in m["id"] for m in models)

    res_ai_req = client.post(f"/api/v1/projects/{proj_id}/ai/requirements", json={
        "document": "The actuator shall extend when commanded and pressure > 100 psi."
    })
    assert res_ai_req.status_code == 200
    assert "DO-178C" in res_ai_req.json()["disclaimer"]

    # 4. Import source code
    source_c = """
int actuator_command(int cmd, int pressure) {
    if (cmd == 1 && pressure > 100) {
        return 1;
    }
    return 0;
}
"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("src/actuator.c", source_c)
    zip_b64 = base64.b64encode(zip_buffer.getvalue()).decode("utf-8")

    res_zip = client.post(f"/api/v1/projects/{proj_id}/sources/import-zip", json={
        "archive_base64": zip_b64,
        "archive_format": "zip",
    })
    assert res_zip.status_code == 201

    res_analysis = client.post(f"/api/v1/projects/{proj_id}/analyze")
    assert res_analysis.status_code == 200
    fn_obj = res_analysis.json()["functions"][0]
    fn_id = fn_obj["id"]

    # 5. Suggest tests endpoint
    res_sug_tests = client.post(f"/api/v1/projects/{proj_id}/suggest-tests?function_id={fn_id}")
    assert res_sug_tests.status_code == 200
    sug_tests = res_sug_tests.json()
    assert len(sug_tests) >= 1

    # 6. Create Test Suite and Test Cases
    res_suite = client.post(f"/api/v1/projects/{proj_id}/test-suites", json={
        "name": "Actuator Unit Suite",
        "description": "Validation suite for actuator control logic."
    })
    assert res_suite.status_code == 201
    suite_id = res_suite.json()["id"]

    # Test Case 1: Passing test
    res_tc1 = client.post(f"/api/v1/projects/{proj_id}/test-cases", json={
        "test_suite_id": suite_id,
        "target_function_id": fn_id,
        "name": "TC_Actuator_Passing",
        "inputs": {"cmd": 1, "pressure": 150},
        "expected_outputs": {"return": 1}
    })
    assert res_tc1.status_code == 201
    tc1_id = res_tc1.json()["id"]

    # Test Case 2: Assertion failure test (expects 1 when function returns 0)
    res_tc2 = client.post(f"/api/v1/projects/{proj_id}/test-cases", json={
        "test_suite_id": suite_id,
        "target_function_id": fn_id,
        "name": "TC_Actuator_Failing_Assertion",
        "inputs": {"cmd": 0, "pressure": 50},
        "expected_outputs": {"return": 1}  # Function returns 0 for cmd=0
    })
    assert res_tc2.status_code == 201
    tc2_id = res_tc2.json()["id"]

    # 7. Execute both tests
    res_exec1 = client.post(f"/api/v1/projects/{proj_id}/executions", json={
        "test_case_id": tc1_id,
        "timeout_seconds": 10
    })
    assert res_exec1.status_code == 201
    exec1 = res_exec1.json()
    assert exec1["status"] in ("PASS", "PASSED")
    assert exec1["verdict"] == "PASS"

    res_exec2 = client.post(f"/api/v1/projects/{proj_id}/executions", json={
        "test_case_id": tc2_id,
        "timeout_seconds": 10
    })
    assert res_exec2.status_code == 201
    exec2 = res_exec2.json()
    assert exec2["status"] in ("FAIL", "FAILED")
    assert exec2["verdict"] == "FAIL"

    # AI explain endpoint on failing execution
    res_ai_exp = client.post(f"/api/v1/projects/{proj_id}/ai/explain", json={
        "failure_logs": exec2.get("logs", "Assertion failed: expected 1, actual 0")
    })
    assert res_ai_exp.status_code == 200
    assert "DO-178C" in res_ai_exp.json()["disclaimer"]

    # 8. Execution History
    res_history = client.get(f"/api/v1/projects/{proj_id}/executions")
    assert res_history.status_code == 200
    history = res_history.json()
    assert len(history) >= 2
    # Verify both executions exist in history
    hist_ids = [h["id"] for h in history]
    assert exec1["id"] in hist_ids
    assert exec2["id"] in hist_ids

    # 9. Execution Comparison / Regression
    res_comp = client.get(f"/api/v1/projects/{proj_id}/executions/compare?base={exec1['id']}&target={exec2['id']}")
    assert res_comp.status_code == 200
    comp = res_comp.json()
    assert "regressionCount" in comp
    assert "fixedCount" in comp

    # 10. Historical Rerun
    res_rerun = client.post(f"/api/v1/projects/{proj_id}/executions/{exec1['id']}/rerun")
    assert res_rerun.status_code == 201
    rerun_data = res_rerun.json()
    assert rerun_data["id"] != exec1["id"]  # Created new execution
    assert rerun_data["status"] in ("PASS", "PASSED")
    assert rerun_data["verdict"] == "PASS"

