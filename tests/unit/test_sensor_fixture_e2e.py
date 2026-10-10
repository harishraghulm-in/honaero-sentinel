import io
import base64
import json
import pytest
from fastapi.testclient import TestClient
from apps.api.app.main import app


def test_sensor_fixture_end_to_end_verification():
    with TestClient(app) as client:
        # 1. Create project
        p = client.post('/api/v1/projects', json={
            'name': 'Pitot-Static Sensor Studio',
            'description': 'DO-178C DAL-A Demonstration Project'
        })
        assert p.status_code == 201, p.text
        pid = p.json()['id']

        # 2. Upload sensor files via batch
        with open('fixtures/sensor_fixture/src/sensor.c', 'r') as f:
            c_code = f.read()
        with open('fixtures/sensor_fixture/include/sensor.h', 'r') as f:
            h_code = f.read()

        batch_resp = client.post(f'/api/v1/projects/{pid}/sources/batch', json={
            'files': [
                {'filepath': 'src/sensor.c', 'filename': 'sensor.c', 'content': c_code, 'is_target': True},
                {'filepath': 'include/sensor.h', 'filename': 'sensor.h', 'content': h_code, 'is_target': False}
            ]
        })
        assert batch_resp.status_code == 201, batch_resp.text
        assert batch_resp.json()['imported_count'] == 2

        # 3. Analyze AST
        an_resp = client.post(f'/api/v1/projects/{pid}/analyze')
        assert an_resp.status_code == 200, an_resp.text
        assert len(an_resp.json()['functions']) >= 2

        # 4. Upload Requirement Document & Extract
        with open('fixtures/sensor_fixture/requirements/requirements.md', 'r') as f:
            req_md = f.read()

        doc_resp = client.post(f'/api/v1/projects/{pid}/requirements/documents', json={
            'filename': 'requirements.md',
            'content': req_md,
            'file_type': 'md'
        })
        assert doc_resp.status_code == 201, doc_resp.text
        doc_id = doc_resp.json()['id']

        req_resp = client.post(f'/api/v1/projects/{pid}/requirements/extract?document_id={doc_id}')
        assert req_resp.status_code == 201, req_resp.text
        reqs = req_resp.json()
        assert len(reqs) >= 2

        # 5. Generate Candidate Test Cases
        target_req = reqs[0]
        req_id = target_req['id']
        cand_resp = client.post(f'/api/v1/projects/{pid}/requirements/{req_id}/generate-candidates')
        assert cand_resp.status_code in (200, 201), cand_resp.text
        cands = cand_resp.json()
        assert len(cands) >= 1

        # 6. Approve Candidate to Test Case
        cand_to_approve = cands[0]
        cand_id = cand_to_approve['id']
        appr_resp = client.post(f'/api/v1/projects/{pid}/candidate-test-cases/{cand_id}/approve')
        assert appr_resp.status_code in (200, 201), appr_resp.text
        appr_tc = appr_resp.json()

        # 7. Execute Test Case
        exec_resp = client.post(f'/api/v1/projects/{pid}/executions', json={'test_case_id': appr_tc['id']})
        assert exec_resp.status_code == 201, exec_resp.text
        exec_data = exec_resp.json()
        exec_id = exec_data['id']
        assert exec_data['exit_code'] == 0
        assert exec_data['status'] in ('PASSED', 'PASS')

        # 8. Fetch Coverage and MC/DC
        cov_resp = client.get(f'/api/v1/projects/{pid}/executions/{exec_id}/coverage')
        assert cov_resp.status_code == 200, cov_resp.text
        assert cov_resp.json()['statement_coverage_pct'] >= 0

        mcdc_resp = client.get(f'/api/v1/projects/{pid}/executions/{exec_id}/mcdc')
        assert mcdc_resp.status_code == 200, mcdc_resp.text

        # 9. Rerun execution
        rerun_resp = client.post(f'/api/v1/projects/{pid}/executions/{exec_id}/rerun')
        assert rerun_resp.status_code == 201, rerun_resp.text
        rerun_id = rerun_resp.json()['id']

        # 10. Compare executions
        comp_resp = client.get(f'/api/v1/projects/{pid}/executions/compare?base={exec_id}&target={rerun_id}')
        assert comp_resp.status_code == 200, comp_resp.text
        assert 'regressionCount' in comp_resp.json()

        # 11. Report verification
        rep_resp = client.get(f'/api/v1/projects/{pid}/report')
        assert rep_resp.status_code == 200, rep_resp.text
        report_data = rep_resp.json()
        assert report_data['project_name'] == 'Pitot-Static Sensor Studio'
        assert report_data['sources']['total_sources'] == 2
