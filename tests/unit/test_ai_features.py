import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from apps.api.app.main import app
from apps.api.app.schemas.ai_schemas import (
    ProvenanceType,
    ProposalReviewStatus,
)
from apps.api.app.infrastructure.ai.nim_provider import NvidiaNimProvider


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_project(client):
    res = client.post("/api/v1/projects", json={"name": "AI Verification Test Project", "description": "DO-178C AI Unit Tests"})
    assert res.status_code == 201
    return res.json()


# ---------------------------------------------------------
# 1. Model Catalog and Status
# ---------------------------------------------------------

def test_get_ai_models(client):
    res = client.get("/api/v1/ai/models")
    assert res.status_code == 200
    models = res.json()
    assert isinstance(models, list)
    assert len(models) >= 3
    model_ids = [m["id"] for m in models]
    assert "meta/llama-3.3-70b-instruct" in model_ids
    assert "nvidia/nemotron-4-340b-instruct" in model_ids
    assert "google/gemma-2-27b-it" in model_ids


def test_get_ai_status(client):
    res = client.get("/api/v1/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "activeModel" in data
    assert "isConfigured" in data
    assert "do178cNotice" in data
    assert "advisory" in data["do178cNotice"].lower()


def test_select_ai_model(client):
    res = client.post("/api/v1/ai/models/select", json={"model_id": "google/gemma-2-27b-it"})
    assert res.status_code == 200
    assert res.json()["currentModel"] == "google/gemma-2-27b-it"

    # Reject unknown model
    err_res = client.post("/api/v1/ai/models/select", json={"model_id": "nonexistent-model-xyz"})
    assert err_res.status_code == 400


# ---------------------------------------------------------
# 2. Requirement Extraction and Approval Workflow
# ---------------------------------------------------------

def test_extract_and_approve_requirements(client, test_project):
    pid = test_project["id"]
    spec_text = (
        "REQ-PRS-001: The system shall calculate cabin altitude from pressure. "
        "Operational range: 0 to 50000 ft. When pressure is below 100 hPa, trigger emergency alert."
    )
    res = client.post(f"/api/v1/projects/{pid}/ai/requirements", json={"spec_text": spec_text})
    assert res.status_code == 200
    data = res.json()
    assert "modelUsed" in data
    assert "content" in data
    proposals = data["content"]
    assert len(proposals) > 0

    first_req = proposals[0]
    assert "proposalId" in first_req
    assert "identifier" in first_req
    assert "description" in first_req
    assert first_req["status"] == "PROPOSED"
    assert "provenance" in first_req

    # Now approve the requirement to promote to DB
    approve_res = client.post(
        f"/api/v1/projects/{pid}/ai/requirements/approve",
        json={"proposal": first_req, "reviewed_by": "Senior Systems Engineer"}
    )
    assert approve_res.status_code == 200
    approve_data = approve_res.json()
    assert approve_data["status"] == "APPROVED"
    approved_req = approve_data["requirement"]
    assert approved_req["review_status"] == "APPROVED"
    assert approved_req["project_id"] == pid

    # Verify it exists in project requirements endpoint
    reqs_res = client.get(f"/api/v1/projects/{pid}/requirements")
    assert reqs_res.status_code == 200
    req_ids = [r["id"] for r in reqs_res.json()]
    assert approved_req["id"] in req_ids


# ---------------------------------------------------------
# 3. Test Generation and Promotion Workflow
# ---------------------------------------------------------

def test_generate_and_approve_test_proposals(client, test_project):
    pid = test_project["id"]
    # Generate candidate proposals
    res = client.post(
        f"/api/v1/projects/{pid}/ai/test-proposals",
        json={"target_function": "calculate_cabin_altitude", "category": "BOUNDARY"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "content" in data
    proposals = data["content"]
    assert len(proposals) > 0

    proposal = proposals[0]
    assert proposal["category"] in ["NORMAL", "BOUNDARY", "INVALID_INPUT", "FAULT", "SEQUENCE", "FAULT_INJECTION", "SCENARIO"]
    assert "name" in proposal
    assert "inputs" in proposal
    assert proposal["status"] == "PROPOSED"

    # Approve and promote proposal to test suite
    promote_res = client.post(
        f"/api/v1/projects/{pid}/ai/test-proposals/approve",
        json={"proposal": proposal, "reviewed_by": "Test Lead"}
    )
    assert promote_res.status_code == 200
    promoted_data = promote_res.json()
    assert promoted_data["success"] is True
    assert "test_case" in promoted_data
    assert "test_vector" in promoted_data

    # Verify candidate promoted test case appears in project test cases
    tc_res = client.get(f"/api/v1/projects/{pid}/test-cases")
    assert tc_res.status_code == 200
    assert any(tc["id"] == promoted_data["test_case"]["id"] for tc in tc_res.json())


# ---------------------------------------------------------
# 4. Flight Envelope Scenarios & Fault Injections
# ---------------------------------------------------------

def test_generate_scenarios(client, test_project):
    pid = test_project["id"]
    res = client.post(
        f"/api/v1/projects/{pid}/ai/scenarios",
        json={"scenario_type": "TAKEOFF_AND_CLIMB"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "content" in data
    scenarios = data["content"]
    assert len(scenarios) > 0
    scenario = scenarios[0]
    assert "scenarioName" in scenario
    assert len(scenario["steps"]) > 0


def test_suggest_fault_injections(client, test_project):
    pid = test_project["id"]
    res = client.post(
        f"/api/v1/projects/{pid}/ai/faults",
        json={"fault_type": "SENSOR_SPIKE"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "content" in data
    faults = data["content"]
    assert len(faults) > 0
    fault = faults[0]
    assert "faultType" in fault
    assert "rationale" in fault


# ---------------------------------------------------------
# 5. Failure Explanations Grounded in Evidence
# ---------------------------------------------------------

def test_explain_failure_without_inventing_evidence(client, test_project):
    pid = test_project["id"]
    res = client.post(
        f"/api/v1/projects/{pid}/ai/explain",
        json={"run_id": "test-run-123"}
    )
    assert res.status_code == 200
    data = res.json()
    explanation = data["content"]
    assert "verdict" in explanation
    assert "observedEvidence" in explanation
    assert "DO-178C" in data["disclaimer"]


# ---------------------------------------------------------
# 6. Coverage Gaps, Retest, Optimization, Traceability, Environment, Report
# ---------------------------------------------------------

def test_coverage_gap_recommendations(client, test_project):
    pid = test_project["id"]
    res = client.post(f"/api/v1/projects/{pid}/ai/coverage-gaps")
    assert res.status_code == 200
    data = res.json()
    gaps = data["content"]
    assert len(gaps) > 0
    gap = gaps[0]
    assert "gapId" in gap
    assert "sourceLocation" in gap
    assert "proposedVector" in gap


def test_adaptive_retest(client, test_project):
    pid = test_project["id"]
    res = client.post(
        f"/api/v1/projects/{pid}/ai/adaptive-retest",
        json={"failed_run_id": "run-fail-abc"}
    )
    assert res.status_code == 200
    data = res.json()
    retest = data["content"]
    assert "diagnosticTestProposals" in retest
    assert "investigationGoal" in retest


def test_test_suite_optimization(client, test_project):
    pid = test_project["id"]
    res = client.post(f"/api/v1/projects/{pid}/ai/test-suite-optimization")
    assert res.status_code == 200
    data = res.json()
    opt = data["content"]
    assert "preservedCategories" in opt
    assert "DO-178C" in data["disclaimer"]


def test_suggest_traceability(client, test_project):
    pid = test_project["id"]
    res = client.post(f"/api/v1/projects/{pid}/ai/traceability")
    assert res.status_code == 200
    data = res.json()
    traces = data["content"]
    assert len(traces) > 0
    trace = traces[0]
    assert "requirementId" in trace
    assert trace["status"] == "PROPOSED"


def test_recommend_environment(client, test_project):
    pid = test_project["id"]
    res = client.post(f"/api/v1/projects/{pid}/ai/environment")
    assert res.status_code == 200
    data = res.json()
    rec = data["content"]
    assert "recommendedFlags" in rec


def test_generate_ai_report(client, test_project):
    pid = test_project["id"]
    res = client.post(f"/api/v1/projects/{pid}/ai/report")
    assert res.status_code == 200
    data = res.json()
    assert "content" in data
    assert isinstance(data["content"], str)
    assert len(data["content"]) > 100
    assert "DO-178C" in data["content"]


# ---------------------------------------------------------
# 7. NVIDIA NIM Provider Mocking and Error Handling
# ---------------------------------------------------------

def test_nim_provider_mock_response():
    provider = NvidiaNimProvider(api_key="mock-key-123456")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"proposals": [{"identifier": "REQ-MOCK-01"}]}'}}]
        }
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        text, is_live, err = provider.complete_chat(
            model="meta/llama-3.3-70b-instruct",
            messages=[{"role": "user", "content": "Extract requirements"}]
        )
        assert is_live is True
        assert err is None
        assert text is not None
        assert "REQ-MOCK-01" in text


def test_nim_provider_timeout_and_fallback():
    provider = NvidiaNimProvider(api_key="mock-key-123456")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = Exception("HTTP 504 Gateway Timeout")
        mock_client_cls.return_value = mock_client

        # Should gracefully return None, is_live=False, and error message
        text, is_live, err = provider.complete_chat(
            model="meta/llama-3.3-70b-instruct",
            messages=[{"role": "user", "content": "test"}]
        )
        assert is_live is False
        assert text is None
        assert "504" in err or "Timeout" in err


def test_nim_provider_unconfigured_operates_safely():
    provider = NvidiaNimProvider(api_key="")
    assert provider.is_configured() is False
    text, is_live, err = provider.complete_chat(
        model="meta/llama-3.3-70b-instruct",
        messages=[{"role": "user", "content": "test"}]
    )
    assert is_live is False
    assert text is None
    assert "not configured" in err
