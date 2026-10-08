import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.app.infrastructure.database.base import Base
from apps.api.app.domain.models import (
    Project,
    SourceFile,
    Requirement,
    FunctionModel,
    Dependency,
    StubConfiguration,
    TestCase,
    TestVector,
    Execution,
    CoverageResult,
    MCDCResult,
    EvidenceRecord,
)
from apps.api.app.domain.enums import (
    DependencyMode,
    ExecutionStatus,
    EvidenceFreshness,
    RequirementType,
)


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


def test_project_domain_creation_and_cascade(db_session):
    project = Project(name="Cabin Pressure Controller", description="Honeywell DO-178C Verification Target")
    db_session.add(project)
    db_session.commit()

    source = SourceFile(
        project_id=project.id,
        filename="cabin_pressure.c",
        filepath="src/cabin_pressure.c",
        content="int cabin_pressure_control(int p, int a) { return 0; }",
        checksum_sha256="abc12345",
        is_target=True,
    )
    db_session.add(source)

    req = Requirement(
        project_id=project.id,
        identifier="HLR-001",
        title="Cabin Pressure Regulation",
        description="Maintain cabin pressure between 900 and 10000 ft altitude",
        req_type=RequirementType.HLR,
    )
    db_session.add(req)
    db_session.commit()

    fn = FunctionModel(
        project_id=project.id,
        source_file_id=source.id,
        name="cabin_pressure_control",
        return_type="int",
        parameters=[{"name": "p", "type": "int"}, {"name": "a", "type": "int"}],
        is_target_under_test=True,
    )
    db_session.add(fn)
    db_session.commit()

    dep = Dependency(
        project_id=project.id,
        caller_function_id=fn.id,
        name="sensor_read",
        return_type="int",
        mode=DependencyMode.STUB,
    )
    db_session.add(dep)
    db_session.commit()

    stub = StubConfiguration(
        project_id=project.id,
        dependency_id=dep.id,
        function_name="sensor_read",
        mode=DependencyMode.STUB,
        return_values=[950, 945, 960],
        expected_call_count=3,
    )
    db_session.add(stub)

    tc = TestCase(
        project_id=project.id,
        target_function_id=fn.id,
        requirement_id=req.id,
        name="TC-001 High Altitude Normal Pressure",
    )
    db_session.add(tc)
    db_session.commit()

    vector = TestVector(
        test_case_id=tc.id,
        vector_index=1,
        inputs={"pressure": 950, "altitude": 8000},
        expected_outputs={"return": 1},
    )
    db_session.add(vector)

    execution = Execution(
        project_id=project.id,
        test_case_id=tc.id,
        status=ExecutionStatus.PASSED,
        exit_code=0,
        source_checksum="abc12345",
        results_summary={"status": "PASS"},
    )
    db_session.add(execution)
    db_session.commit()

    cov = CoverageResult(
        execution_id=execution.id,
        statement_coverage_pct=100.0,
        branch_coverage_pct=100.0,
        line_coverage_pct=100.0,
    )
    mcdc = MCDCResult(
        execution_id=execution.id,
        coverage_percentage=100.0,
        decisions=[{"decision_id": "D1", "conditions": [{"id": "C1", "independence_proven": True}]}],
    )
    evidence = EvidenceRecord(
        project_id=project.id,
        execution_id=execution.id,
        freshness=EvidenceFreshness.CURRENT,
        source_checksum="abc12345",
        evidence_json={"execution": "PASSED"},
    )
    db_session.add_all([cov, mcdc, evidence])
    db_session.commit()

    # Query and verify
    queried_proj = db_session.query(Project).filter_by(id=project.id).first()
    assert queried_proj is not None
    assert len(queried_proj.source_files) == 1
    assert len(queried_proj.requirements) == 1
    assert len(queried_proj.functions) == 1
    assert len(queried_proj.dependencies) == 1
    assert queried_proj.dependencies[0].stub_config.return_values == [950, 945, 960]
    assert len(queried_proj.test_cases) == 1
    assert len(queried_proj.test_cases[0].test_vectors) == 1
    assert queried_proj.executions[0].coverage.statement_coverage_pct == 100.0
    assert queried_proj.executions[0].mcdc.coverage_percentage == 100.0
    assert queried_proj.executions[0].evidence.freshness == EvidenceFreshness.CURRENT

