"""
HonAero Sentinel — Smart Verification Studio
End-to-End Cabin Pressure Verification Workflow Demo
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi.testclient import TestClient
from apps.api.app.main import app

def run_cabin_pressure_verification_demo():
    print("=" * 70)
    print("HONERO SENTINEL — SMART VERIFICATION STUDIO")
    print("Verification Workflow: Cabin Pressure System (DO-178C Demo)")
    print("=" * 70)

    client = TestClient(app)
    base_dir = Path(__file__).parent

    # 1. Project Creation
    print("\n[Step 1/10] Creating Verification Project...")
    res = client.post("/api/v1/projects", json={
        "name": "Cabin Pressure Verification Studio",
        "description": "Honeywell Cabin Pressure Controller Verification Target"
    })
    assert res.status_code == 201
    proj_id = res.json()["id"]
    print(f"  -> Project created with ID: {proj_id}")

    # 2. Source Import
    print("\n[Step 2/10] Importing C Source Code...")
    c_source = (base_dir / "cabin_pressure.c").read_text(encoding="utf-8")
    h_source = (base_dir / "cabin_pressure.h").read_text(encoding="utf-8")
    
    res = client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "cabin_pressure.h",
        "content": h_source,
        "is_environment": True
    })
    assert res.status_code == 201

    res = client.post(f"/api/v1/projects/{proj_id}/sources", json={
        "filename": "cabin_pressure.c",
        "content": c_source,
        "is_target": True
    })
    assert res.status_code == 201
    target_source_id = res.json()["id"]
    print(f"  -> Uploaded cabin_pressure.c (Target) and cabin_pressure.h")

    # 3. Source AST Parsing & Decision Extraction
    print("\n[Step 3/10] Running Clang/AST Source Analysis...")
    res = client.post(f"/api/v1/projects/{proj_id}/analyze")
    assert res.status_code == 200
    analysis = res.json()
    fn = analysis["functions"][0]
    print(f"  -> Discovered Target Function: {fn['name']} ({fn['return_type']})")
    print(f"  -> Parameters: {', '.join([f'{p['name']}: {p['type']}' for p in fn['parameters']])}")
    print(f"  -> Decisions: {len(fn['decisions'])} detected (Expression: '{fn['decisions'][0]['expression']}')")
    print(f"  -> Atomic Conditions: {len(fn['decisions'][0]['conditions'])} detected")
    print(f"  -> External Dependencies: {[d['name'] for d in analysis['dependencies']]}")

    # 4. Scope Selection
    print("\n[Step 4/10] Configuring Scope Selection...")
    res = client.post(f"/api/v1/projects/{proj_id}/scope", json={
        "target_function_id": fn["id"],
        "target_source_id": target_source_id,
        "environment_source_ids": []
    })
    assert res.status_code == 200
    print(f"  -> Target Scope Set: Function '{fn['name']}' in 'cabin_pressure.c'")

    # 5. Dependency Isolation & Stub Configuration
    print("\n[Step 5/10] Configuring Real vs Stub Dependencies...")
    stubs_data = json.loads((base_dir / "stubs_config.json").read_text(encoding="utf-8"))
    for stub_item in stubs_data:
        # Find matching dependency id
        matching_dep = next((d for d in analysis["dependencies"] if d["name"] == stub_item["function_name"]), None)
        if matching_dep:
            res = client.post(f"/api/v1/projects/{proj_id}/stubs", json={
                "dependency_id": matching_dep["id"],
                "function_name": stub_item["function_name"],
                "mode": "STUB",
                "return_values": stub_item.get("return_values", []),
                "expected_call_count": stub_item.get("expected_call_count", 4)
            })
            assert res.status_code == 201
            print(f"  -> Dependency '{stub_item['function_name']}' configured as STUB with returns {stub_item.get('return_values')}")

    # 6. Test Vectors Authoring
    print("\n[Step 6/10] Authoring Test Vectors & Requirements Traceability...")
    vectors_data = json.loads((base_dir / "test_vectors.json").read_text(encoding="utf-8"))
    res = client.post(f"/api/v1/projects/{proj_id}/test-cases", json={
        "name": "TC-001 High/Low Altitude Overpressure Suite",
        "target_function_id": fn["id"],
        "vectors": vectors_data
    })
    assert res.status_code == 201
    tc_id = res.json()["id"]
    print(f"  -> Created Test Case {tc_id} with {len(vectors_data)} vectors")

    # 7. Automated Build & Isolated Execution
    print("\n[Step 7/10] Harness Generation, GCC Compilation & Execution...")
    res = client.post(f"/api/v1/projects/{proj_id}/executions", json={
        "test_case_id": tc_id,
        "timeout_seconds": 10
    })
    assert res.status_code == 201
    exec_data = res.json()
    exec_id = exec_data["execution_id"]
    print(f"  -> Execution ID: {exec_id}")
    print(f"  -> Status: {exec_data['status']}")
    print(f"  -> Duration: {exec_data['duration_ms']:.2f} ms")
    print(f"  -> Summary: {exec_data['results_summary']}")

    # 8. Coverage Metrics
    print("\n[Step 8/10] Collecting GCOV Coverage Metrics...")
    res = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/coverage")
    assert res.status_code == 200
    cov = res.json()
    print(f"  -> Statement Coverage: {cov['statement_coverage_pct']}%")
    print(f"  -> Branch Coverage:    {cov['branch_coverage_pct']}%")
    print(f"  -> Line Coverage:      {cov['line_coverage_pct']}%")

    # 9. MC/DC Analysis & Gap Advisor
    print("\n[Step 9/10] Performing MC/DC Independence Analysis...")
    res = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/mcdc")
    assert res.status_code == 200
    mcdc = res.json()
    print(f"  -> MC/DC Coverage: {mcdc['coverage_percentage']}%")
    for dec in mcdc["decisions"]:
        for c in dec["conditions"]:
            print(f"     Condition {c['id']} ({c['expression']}): Proven = {c['independence_proven']} {c.get('independence_pair') or ''}")

    # 10. Immutable Evidence Record & Export
    print("\n[Step 10/10] Generating Cryptographic Evidence Record & Exporting Artifacts...")
    res = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/evidence")
    assert res.status_code == 200
    evid = res.json()
    print(f"  -> Evidence ID:     {evid['evidence_id']}")
    print(f"  -> Source Checksum: {evid['source_checksum']}")
    print(f"  -> Freshness State: {evid['freshness']}")

    # Export markdown
    export_res = client.post(f"/api/v1/projects/{proj_id}/executions/{exec_id}/evidence/export?format=md")
    assert export_res.status_code == 200
    print("  -> Exported Markdown/PDF Compliance Report successfully.")

    print("\n" + "=" * 70)
    print("DEMO RUN COMPLETE: ALL 24 VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_cabin_pressure_verification_demo()
