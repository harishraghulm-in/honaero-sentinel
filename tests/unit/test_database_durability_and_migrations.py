import os
import tempfile
import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient

from apps.api.app.main import app, sync_sqlite_schema
from apps.api.app.infrastructure.database.base import Base
from apps.api.app.infrastructure.database.session import get_db, enable_sqlite_foreign_keys
from apps.api.app.domain.models import (
    Project,
    SourceFile,
    Requirement,
    RequirementDocument,
    CandidateTestCase,
    TestCase,
    TestVector,
    FunctionModel,
    Execution,
    CoverageResult,
    MCDCResult,
    EvidenceRecord,
    TraceabilityLink,
)
from apps.api.app.domain.enums import ExecutionStatus, EvidenceFreshness, RequirementType


SAMPLE_C_CODE = """
#include <stdbool.h>

int cabin_pressure_control(int current_pressure, int target_pressure, bool manual_override) {
    if (manual_override) {
        return 0;
    }
    if (current_pressure < target_pressure) {
        return 1;
    } else if (current_pressure > target_pressure) {
        return -1;
    }
    return 0;
}
"""


def test_persistence_across_application_restart():
    """
    Test genuine database persistence across application restart using an on-disk SQLite database.
    Verifies that projects, requirements, approved candidates, executions, and evidence
    persist completely when the connection/engine is closed and reopened.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_url = f"sqlite:///{db_path}"
    engine1 = create_engine(db_url, connect_args={"check_same_thread": False})
    enable_sqlite_foreign_keys(engine1)

    Base.metadata.create_all(bind=engine1)
    sync_sqlite_schema(engine1)

    TestingSession1 = sessionmaker(autocommit=False, autoflush=False, bind=engine1)

    def override_get_db1():
        db = TestingSession1()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db1
    client1 = TestClient(app)

    try:
        # Phase 1: Create Project & Data
        proj_resp = client1.post("/api/v1/projects", json={"name": "Durability Test Project", "description": "Testing persistence"})
        assert proj_resp.status_code == 201
        proj_id = proj_resp.json()["id"]

        # Upload C source file
        src_resp = client1.post(f"/api/v1/projects/{proj_id}/sources", json={"filename": "cabin.c", "content": SAMPLE_C_CODE})
        assert src_resp.status_code == 201

        # Run source analysis
        ana_resp = client1.post(f"/api/v1/projects/{proj_id}/analyze")
        assert ana_resp.status_code == 200
        assert len(ana_resp.json()["functions"]) > 0

        # Upload requirement doc
        req_doc_resp = client1.post(
            f"/api/v1/projects/{proj_id}/requirements/documents",
            json={"filename": "cabin_reqs.md", "content": "REQ-001: Cabin pressure shall increase when below target."},
        )
        assert req_doc_resp.status_code == 201
        doc_id = req_doc_resp.json()["id"]

        # Extract requirements
        extract_resp = client1.post(f"/api/v1/projects/{proj_id}/requirements/extract")
        assert extract_resp.status_code == 201
        extracted = extract_resp.json()
        assert len(extracted) >= 1
        req_id = extracted[0]["id"]

        # Generate candidates & approve one
        gen_resp = client1.post(f"/api/v1/projects/{proj_id}/requirements/{req_id}/generate-candidates")
        assert gen_resp.status_code == 201
        candidates = gen_resp.json()
        assert len(candidates) > 0
        cand_id = candidates[0]["id"]

        appr_resp = client1.post(
            f"/api/v1/projects/{proj_id}/candidate-test-cases/{cand_id}/approve",
            json={"target_function_name": "cabin_pressure_control"},
        )
        assert appr_resp.status_code == 201
        test_case_id = appr_resp.json()["id"]

        # Execute test case
        exec_resp = client1.post(
            f"/api/v1/projects/{proj_id}/executions",
            json={"test_case_id": test_case_id},
        )
        assert exec_resp.status_code == 201
        exec_id = exec_resp.json()["id"]
        assert exec_resp.json()["status"] == ExecutionStatus.PASSED.value

        # Fetch evidence
        ev_resp = client1.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/evidence")
        assert ev_resp.status_code == 200
        assert ev_resp.json()["freshness"] == "CURRENT"
        orig_source_checksum = ev_resp.json()["source_checksum"]

        # Phase 2: Simulate Application Shutdown by closing DB engine and session
        engine1.dispose()
        app.dependency_overrides.clear()

        # Phase 3: Simulate Application Restart with new engine/session
        engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
        enable_sqlite_foreign_keys(engine2)
        TestingSession2 = sessionmaker(autocommit=False, autoflush=False, bind=engine2)

        def override_get_db2():
            db = TestingSession2()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db2
        client2 = TestClient(app)

        # Verify all entities persist intact
        proj_get = client2.get(f"/api/v1/projects/{proj_id}")
        assert proj_get.status_code == 200
        assert proj_get.json()["name"] == "Durability Test Project"

        reqs_get = client2.get(f"/api/v1/projects/{proj_id}/requirements")
        assert reqs_get.status_code == 200
        reqs_list = reqs_get.json()
        assert len(reqs_list) >= 1
        assert reqs_list[0]["id"] == req_id

        # Verify test cases
        tc_get = client2.get(f"/api/v1/projects/{proj_id}/test-cases")
        assert tc_get.status_code == 200
        tc_list = tc_get.json()
        assert any(t["id"] == test_case_id for t in tc_list)

        # Verify execution record & evidence
        exec_get = client2.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}")
        assert exec_get.status_code == 200
        assert exec_get.json()["status"] == ExecutionStatus.PASSED.value

        ev_get = client2.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/evidence")
        assert ev_get.status_code == 200
        assert ev_get.json()["freshness"] == "CURRENT"
        assert ev_get.json()["source_checksum"] == orig_source_checksum

        engine2.dispose()

    finally:
        app.dependency_overrides.clear()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass


def test_legacy_schema_migration_safety():
    """
    Test schema upgrade safety from the legacy schema (migration 577a48cdd49f).
    Ensures that existing legacy data is preserved without corruption,
    missing tables are created, and missing columns are safely backfilled.
    """
    legacy_engine = create_engine("sqlite:///:memory:")
    enable_sqlite_foreign_keys(legacy_engine)

    # 1. Create legacy schema tables
    with legacy_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE projects (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE requirements (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                identifier VARCHAR(100) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                req_type VARCHAR(10) NOT NULL,
                created_at DATETIME NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE source_files (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                filepath VARCHAR(1024) NOT NULL,
                content TEXT NOT NULL,
                checksum_sha256 VARCHAR(64) NOT NULL,
                is_target BOOLEAN NOT NULL,
                is_environment BOOLEAN NOT NULL,
                created_at DATETIME NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE test_cases (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                test_suite_id VARCHAR(36),
                target_function_id VARCHAR(36),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                created_at DATETIME NOT NULL
            );
        """))
        conn.commit()

        # Insert legacy data
        conn.execute(text("""
            INSERT INTO projects (id, name, description, created_at, updated_at)
            VALUES ('proj-legacy-1', 'Legacy Avionics Project', 'Created in v1', '2026-01-01 00:00:00', '2026-01-01 00:00:00');
        """))
        conn.execute(text("""
            INSERT INTO requirements (id, project_id, identifier, title, description, req_type, created_at)
            VALUES ('req-legacy-1', 'proj-legacy-1', 'LEG-REQ-1', 'Altitude Limit', 'Maintain safe altitude', 'HLR', '2026-01-01 00:00:00');
        """))
        conn.commit()

    # 2. Run schema synchronization (simulate lifespan)
    Base.metadata.create_all(bind=legacy_engine)
    sync_sqlite_schema(legacy_engine)

    # 3. Verify legacy data is preserved intact
    with legacy_engine.connect() as conn:
        p_row = conn.execute(text("SELECT id, name FROM projects WHERE id = 'proj-legacy-1'")).fetchone()
        assert p_row is not None
        assert p_row[1] == "Legacy Avionics Project"

        r_row = conn.execute(text("SELECT id, identifier, ambiguity_status FROM requirements WHERE id = 'req-legacy-1'")).fetchone()
        assert r_row is not None
        assert r_row[1] == "LEG-REQ-1"
        assert r_row[2] == "CLEAR"  # Default successfully populated by sync_sqlite_schema

    # 4. Verify new tables were successfully created
    insp = inspect(legacy_engine)
    assert insp.has_table("requirement_documents")
    assert insp.has_table("candidate_test_cases")
    assert insp.has_table("traceability_links")

    # 5. Verify ORM operations work cleanly on the upgraded database
    LegacySession = sessionmaker(bind=legacy_engine)
    db = LegacySession()
    try:
        cand = CandidateTestCase(
            project_id="proj-legacy-1",
            requirement_id="req-legacy-1",
            name="Upgraded Case 1",
            rationale="Verifies upgraded candidate compatibility",
        )
        db.add(cand)
        db.commit()
        assert cand.id is not None
    finally:
        db.close()
        legacy_engine.dispose()


def test_sqlite_foreign_key_cascades_and_referential_integrity():
    """
    Test SQLite foreign key constraint enforcement and cascade deletion.
    """
    engine = create_engine("sqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. Verify foreign key violation on orphan insert
        orphan_src = SourceFile(
            project_id="non-existent-proj-id",
            filename="orphan.c",
            filepath="orphan.c",
            content="int x = 1;",
            checksum_sha256="abc123",
        )
        db.add(orphan_src)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 2. Create valid parent project and child source
        proj = Project(name="Cascade Parent")
        db.add(proj)
        db.commit()

        src = SourceFile(
            project_id=proj.id,
            filename="valid.c",
            filepath="valid.c",
            content="int y = 2;",
            checksum_sha256="def456",
        )
        db.add(src)
        db.commit()

        assert db.query(SourceFile).filter_by(project_id=proj.id).count() == 1

        # 3. Delete parent project and verify cascade
        db.delete(proj)
        db.commit()

        # Child record must be automatically cascaded away
        assert db.query(SourceFile).filter_by(id=src.id).count() == 0

    finally:
        db.close()
        engine.dispose()


def test_transaction_rollback_safety():
    """
    Test that an aborted transaction rolls back cleanly without leaving orphan data.
    """
    engine = create_engine("sqlite:///:memory:")
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        proj = Project(name="Rollback Test Project")
        db.add(proj)
        db.commit()

        # Attempt to insert two records in one transaction: one valid, one invalid
        try:
            req = Requirement(project_id=proj.id, identifier="R-1", title="Req 1", description="Valid req")
            db.add(req)

            # Invalid: foreign key to non-existent project
            invalid_req = Requirement(project_id="non-existent-proj", identifier="R-2", title="Req 2", description="Invalid req")
            db.add(invalid_req)

            db.commit()
            pytest.fail("Expected IntegrityError on invalid foreign key")
        except IntegrityError:
            db.rollback()

        # Verify no partial requirement records were saved
        assert db.query(Requirement).filter_by(project_id=proj.id).count() == 0

    finally:
        db.close()
        engine.dispose()


def test_evidence_freshness_invalidation_on_source_mutation(client):
    """
    Test that modifying project source files invalidates evidence freshness to STALE.
    """
    # Create project
    proj_resp = client.post("/api/v1/projects", json={"name": "Freshness Project"})
    proj_id = proj_resp.json()["id"]

    # Upload source & analyze
    src_resp = client.post(f"/api/v1/projects/{proj_id}/sources", json={"filename": "cabin.c", "content": SAMPLE_C_CODE})
    src_id = src_resp.json()["id"]
    client.post(f"/api/v1/projects/{proj_id}/analyze")

    # Configure scope for target function
    client.put(f"/api/v1/projects/{proj_id}/scope", json={"target_function_name": "cabin_pressure_control"})

    # Run execution
    exec_resp = client.post(f"/api/v1/projects/{proj_id}/executions", json={"pressure": 50, "altitude": 1000})
    assert exec_resp.status_code == 201
    exec_id = exec_resp.json()["id"]

    # Evidence is CURRENT
    ev_resp = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/evidence")
    assert ev_resp.status_code == 200
    assert ev_resp.json()["freshness"] == "CURRENT"

    # Mutate source file content via PUT
    mutated_c = SAMPLE_C_CODE + "\n// modified for freshness test\n"
    put_resp = client.put(f"/api/v1/projects/{proj_id}/sources/{src_id}", json={"filename": "cabin.c", "content": mutated_c})
    assert put_resp.status_code == 200

    # Query evidence again: must now detect stale checksum
    ev_resp2 = client.get(f"/api/v1/projects/{proj_id}/executions/{exec_id}/evidence")
    assert ev_resp2.status_code == 200
    assert ev_resp2.json()["freshness"] == "STALE"


def test_unapproved_candidate_execution_rejection(client):
    """
    Verify that unapproved candidate test cases or rejected cases cannot be executed.
    """
    proj_resp = client.post("/api/v1/projects", json={"name": "Rejection Gate Project"})
    proj_id = proj_resp.json()["id"]

    client.post(f"/api/v1/projects/{proj_id}/sources", json={"filename": "cabin.c", "content": SAMPLE_C_CODE})
    client.post(f"/api/v1/projects/{proj_id}/analyze")

    # Upload requirement & generate candidate
    doc_resp = client.post(
        f"/api/v1/projects/{proj_id}/requirements/documents",
        json={"filename": "spec.md", "content": "REQ-10: Pressure limit shall be maintained."},
    )
    assert doc_resp.status_code == 201
    extract_resp = client.post(f"/api/v1/projects/{proj_id}/requirements/extract")
    assert extract_resp.status_code == 201
    req_id = extract_resp.json()[0]["id"]

    gen_resp = client.post(f"/api/v1/projects/{proj_id}/requirements/{req_id}/generate-candidates")
    candidates = gen_resp.json()
    assert len(candidates) > 0
    candidate_id = candidates[0]["id"]

    # Attempt to execute using the unapproved candidate ID directly
    exec_resp = client.post(
        f"/api/v1/projects/{proj_id}/executions",
        json={"test_case_id": candidate_id},
    )
    assert exec_resp.status_code == 404
    err = exec_resp.json()
    assert (err.get("error", {}).get("code") == "TEST_CASE_NOT_FOUND" or
            err.get("detail", {}).get("code") == "TEST_CASE_NOT_FOUND")
