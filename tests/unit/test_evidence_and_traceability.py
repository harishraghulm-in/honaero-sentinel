import pytest
from apps.api.app.application.services import (
    ScalarComparator,
    StructuredComparator,
    EvidenceService,
    TraceabilityService,
)
from apps.api.app.domain.enums import ComparisonStatus, EvidenceFreshness, ExecutionStatus


def test_scalar_and_structured_comparator():
    scalar_comp = ScalarComparator(float_tolerance=0.01)
    # Integer comparison
    res_int = scalar_comp.compare(1, 1)
    assert res_int.status == ComparisonStatus.PASS
    assert res_int.all_passed is True

    # Float within tolerance
    res_float = scalar_comp.compare(10.005, 10.0)
    assert res_float.status == ComparisonStatus.PASS

    # Float outside tolerance
    res_float_fail = scalar_comp.compare(10.05, 10.0)
    assert res_float_fail.status == ComparisonStatus.FAIL

    # Structured comparison
    struct_comp = StructuredComparator(scalar_comp)
    act = {"valve_state": 1, "pressure_psi": 14.7}
    exp = {"valve_state": 1, "pressure_psi": 14.7}
    res_struct = struct_comp.compare(act, exp)
    assert res_struct.status == ComparisonStatus.PASS


def test_evidence_freshness_tracking():
    ev_service = EvidenceService()
    initial_sources = {"cabin_pressure.c": "int cabin_pressure_control() { return 1; }"}
    hash_v1 = ev_service.compute_source_checksum(initial_sources)

    # Initial evidence is CURRENT
    st_current = ev_service.evaluate_freshness(
        current_source_hash=hash_v1,
        evidence_source_hash=hash_v1,
    )
    assert st_current == EvidenceFreshness.CURRENT

    # When source changes, evidence becomes STALE
    modified_sources = {"cabin_pressure.c": "int cabin_pressure_control() { return 2; }"}
    hash_v2 = ev_service.compute_source_checksum(modified_sources)
    st_stale = ev_service.evaluate_freshness(
        current_source_hash=hash_v2,
        evidence_source_hash=hash_v1,
    )
    assert st_stale == EvidenceFreshness.STALE


def test_evidence_record_generation():
    ev_service = EvidenceService()
    report = ev_service.build_evidence_record(
        evidence_id="EVID-001",
        project_id="PROJ-001",
        execution_id="RUN-001",
        target_function="cabin_pressure_control",
        requirement_ids=["HLR-001"],
        source_files={"cabin_pressure.c": "int test();"},
        stubs=[{"function": "sensor_read", "mode": "STUB"}],
        vectors=[{"inputs": {"p": 1}, "expected": 1}],
        compiler_info={"name": "gcc", "version": "16.1.0"},
        execution_status=ExecutionStatus.PASSED,
        duration_ms=45.2,
        stdout="Passed",
        stderr="",
        coverage_data={"statement_coverage_pct": 100.0},
        mcdc_data={"coverage_percentage": 100.0},
    )

    assert report.evidence_id == "EVID-001"
    assert report.target_function == "cabin_pressure_control"
    assert report.freshness == EvidenceFreshness.CURRENT
    assert report.coverage["statement_coverage_pct"] == 100.0
    json_out = ev_service.export_json(report)
    assert "HonAero Sentinel" in json_out

