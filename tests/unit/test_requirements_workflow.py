import base64
import io
import json
import pytest
import docx


def test_unsupported_document_format_rejected(client):
    """Verify that unsupported document formats (.xlsx, .exe) are rejected clearly."""
    res_proj = client.post("/api/v1/projects", json={"name": "Doc Format Test"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    res_xlsx = client.post(f"/api/v1/projects/{proj_id}/requirements/documents", json={
        "filename": "requirements.xlsx",
        "content": "binary excel data...",
    })
    assert res_xlsx.status_code == 400
    err = res_xlsx.json()
    assert err["error"]["code"] == "UNSUPPORTED_DOCUMENT_FORMAT"
    assert ".xlsx is not supported" in err["error"]["message"]


def test_pdf_requirement_extraction_and_provenance(client):
    """Verify extraction of requirements from PDF document with page provenance."""
    res_proj = client.post("/api/v1/projects", json={"name": "PDF Req Project"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    # Minimal valid single-page PDF containing requirement text
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 120 >>\nstream\n"
        b"BT\n/F1 12 Tf\n72 712 Td\n(HLR-001: Cabin pressure control shall maintain nominal pressure when pressure > 900.) Tj\nET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000414 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n495\n%%EOF"
    )
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    res_doc = client.post(f"/api/v1/projects/{proj_id}/requirements/documents", json={
        "filename": "spec_cabin.pdf",
        "content": b64_pdf,
        "revision": "1.0",
    })
    assert res_doc.status_code == 201
    doc_id = res_doc.json()["id"]

    res_ext = client.post(f"/api/v1/projects/{proj_id}/requirements/extract?document_id={doc_id}")
    assert res_ext.status_code == 201
    reqs = res_ext.json()
    assert len(reqs) == 1
    assert reqs[0]["identifier"] == "HLR-001"
    assert "Page 1" in reqs[0]["section"]


def test_docx_requirement_extraction_and_provenance(client):
    """Verify extraction of requirements from DOCX document with section provenance."""
    res_proj = client.post("/api/v1/projects", json={"name": "DOCX Req Project"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    doc = docx.Document()
    doc.add_heading("Section 4.2 Valve Subsystem", level=1)
    doc.add_paragraph("HLR-050: The valve actuator shall open when delta_pressure > 50.")
    stream = io.BytesIO()
    doc.save(stream)
    b64_docx = base64.b64encode(stream.getvalue()).decode("utf-8")

    res_doc = client.post(f"/api/v1/projects/{proj_id}/requirements/documents", json={
        "filename": "valve_spec.docx",
        "content": b64_docx,
        "revision": "3.0",
    })
    assert res_doc.status_code == 201
    doc_id = res_doc.json()["id"]

    res_ext = client.post(f"/api/v1/projects/{proj_id}/requirements/extract?document_id={doc_id}")
    assert res_ext.status_code == 201
    reqs = res_ext.json()
    assert len(reqs) == 1
    assert reqs[0]["identifier"] == "HLR-050"
    assert "4.2 Valve Subsystem" in reqs[0]["section"]



def test_markdown_and_json_requirement_extraction(client):
    """Verify extraction of structured requirements from markdown documents."""
    res_proj = client.post("/api/v1/projects", json={"name": "Extraction Project"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    md_content = """# Section 3.1 Cabin Environmental Controls

## HLR-001: Cabin Pressure Regulation
The cabin pressure control system shall maintain nominal cabin pressure when pressure > 900 and altitude < 10000.
Acceptance Criteria: cabin_pressure_control returns 1 when pressure > 900 and altitude < 10000.

## HLR-002: Vague Pressure Optimization
The system shall optimize the valve position appropriately as needed.
"""
    # 1. Upload Markdown Document
    res_doc = client.post(f"/api/v1/projects/{proj_id}/requirements/documents", json={
        "filename": "cabin_requirements.md",
        "content": md_content,
        "revision": "2.1"
    })
    assert res_doc.status_code == 201
    doc_id = res_doc.json()["id"]
    assert res_doc.json()["checksum_sha256"] is not None

    # 2. Extract Requirements
    res_ext = client.post(f"/api/v1/projects/{proj_id}/requirements/extract?document_id={doc_id}")
    assert res_ext.status_code == 201
    reqs = res_ext.json()
    assert len(reqs) == 2

    # Check HLR-001
    hlr1 = next(r for r in reqs if r["identifier"] == "HLR-001")
    assert hlr1["title"] == "HLR-001: Cabin Pressure Regulation"
    assert hlr1["section"] == "3.1 Cabin Environmental Controls"
    assert hlr1["ambiguity_status"] == "CLEAR"
    assert hlr1["revision"] == "2.1"

    # Check HLR-002 (Ambiguous keywords 'optimize', 'appropriately', 'as needed')
    hlr2 = next(r for r in reqs if r["identifier"] == "HLR-002")
    assert hlr2["ambiguity_status"] == "AMBIGUOUS"
    assert "Ambiguous terms detected" in hlr2["ambiguity_notes"]

    # 3. Review Requirement (Human approval / update)
    res_rev = client.put(f"/api/v1/projects/{proj_id}/requirements/{hlr1['id']}/review", json={
        "review_status": "APPROVED",
        "acceptance_criteria": "Verified by test suite cabin_pressure_control"
    })
    assert res_rev.status_code == 200
    assert res_rev.json()["review_status"] == "APPROVED"
    assert res_rev.json()["acceptance_criteria"] == "Verified by test suite cabin_pressure_control"


def test_candidate_test_case_generation_and_promotion(client):
    """Verify deterministic candidate test case generation, boundary testing, and human approval."""
    res_proj = client.post("/api/v1/projects", json={"name": "Candidate Case Project"})
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    # 1. Upload source & analyze so target function exists
    c_source = """
    int cabin_pressure_control(int pressure, int altitude) {
        if (pressure > 900 && altitude < 10000) return 1;
        return 0;
    }
    """
    client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "cabin_pressure.c",
        "content": c_source,
        "is_target": True
    })
    res_an = client.post(f"/api/v1/projects/{proj_id}/analyze")
    fn_id = res_an.json()["functions"][0]["id"]
    fn_name = res_an.json()["functions"][0]["name"]

    # 2. Create Requirement with conditions: pressure > 900 and altitude < 10000
    res_req = client.post(f"/api/v1/projects/{proj_id}/requirements", json={
        "identifier": "HLR-010",
        "title": "Pressure Threshold Bounds",
        "description": "If pressure > 900 and altitude < 10000, cabin_pressure_control shall return 1.",
        "acceptance_criteria": "Shall return 1 on nominal pressure and altitude.",
        "verification_method": "TEST"
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # 3. Generate Candidate Test Cases
    res_cand = client.post(f"/api/v1/projects/{proj_id}/requirements/{req_id}/generate-candidates?target_function_name={fn_name}")
    assert res_cand.status_code == 201
    cands = res_cand.json()
    assert len(cands) >= 4  # NOMINAL, BOUNDARY-PASS, BOUNDARY-FAIL, OFF-NOMINAL, CONDITION_BASED

    categories = {c["case_category"] for c in cands}
    assert "NORMAL" in categories
    assert "BOUNDARY" in categories
    assert "INVALID_INPUT" in categories
    assert "CONDITION_BASED" in categories

    # Inspect nominal candidate
    nom_cand = next(c for c in cands if c["case_category"] == "NORMAL")
    assert nom_cand["approval_status"] == "PENDING_REVIEW"
    assert nom_cand["input_vectors"][0]["inputs"]["pressure"] > 900
    assert nom_cand["input_vectors"][0]["inputs"]["altitude"] < 10000
    assert nom_cand["input_vectors"][0]["expected_outputs"]["return"] == 1

    # 4. Human Approval of Candidate Test Case -> Promotes to executable TestCase
    res_appr = client.post(f"/api/v1/projects/{proj_id}/candidate-test-cases/{nom_cand['id']}/approve", json={
        "target_function_id": fn_id
    })
    assert res_appr.status_code == 201
    approved_tc = res_appr.json()
    assert approved_tc["name"] == nom_cand["name"]
    assert approved_tc["target_function_id"] == fn_id
    assert approved_tc["requirement_id"] == req_id
    assert approved_tc["vectors_count"] == 1
    tc_id = approved_tc["id"]

    # 5. Execute Approved Test Case through the real verification pipeline
    res_exec = client.post(f"/api/v1/projects/{proj_id}/executions", json={
        "test_case_id": tc_id,
        "timeout_seconds": 10
    })
    assert res_exec.status_code == 201
    exec_data = res_exec.json()
    assert exec_data["status"] == "PASSED"
    assert exec_data["exit_code"] == 0


def test_requirement_isolation_and_not_found(client):
    """Verify 404 responses for non-existent projects and cross-project isolation."""
    # 404 for non-existent project
    res = client.get("/api/v1/projects/non-existent-proj/requirements")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PROJECT_NOT_FOUND"

    res_doc = client.get("/api/v1/projects/non-existent-proj/requirements/documents")
    assert res_doc.status_code == 404

    # Cross-project isolation
    p1 = client.post("/api/v1/projects", json={"name": "Req Project 1"}).json()["id"]
    p2 = client.post("/api/v1/projects", json={"name": "Req Project 2"}).json()["id"]

    client.post(f"/api/v1/projects/{p1}/requirements", json={
        "identifier": "P1-REQ-01",
        "title": "P1 Only",
        "description": "Project 1 requirement",
    })
    client.post(f"/api/v1/projects/{p2}/requirements", json={
        "identifier": "P2-REQ-01",
        "title": "P2 Only",
        "description": "Project 2 requirement",
    })

    p1_reqs = client.get(f"/api/v1/projects/{p1}/requirements").json()
    p2_reqs = client.get(f"/api/v1/projects/{p2}/requirements").json()

    assert len(p1_reqs) == 1
    assert p1_reqs[0]["identifier"] == "P1-REQ-01"
    assert len(p2_reqs) == 1
    assert p2_reqs[0]["identifier"] == "P2-REQ-01"
