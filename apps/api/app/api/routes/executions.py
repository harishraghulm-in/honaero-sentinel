import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import (
    Project,
    SourceFile,
    FunctionModel,
    TestCase,
    StubConfiguration,
    UserHook,
    Execution,
    CoverageResult,
    MCDCResult,
    EvidenceRecord,
)
from apps.api.app.domain.enums import ExecutionStatus, EvidenceFreshness
from apps.api.app.application.services import (
    StubGeneratorService,
    StubDefinition,
    StubParameterSpec,
    HarnessGeneratorService,
    HarnessGeneratorRequest,
    HookDefinition,
    TestVectorDefinition,
    MCDCAnalyzerService,
    EvidenceService,
)
from apps.api.app.domain.interfaces.source_parser import (
    NormalizedFunction,
    NormalizedParameter,
    NormalizedDecision,
    NormalizedCondition,
)
from apps.api.app.infrastructure.execution.process_engine import LocalProcessExecutionEngine
from apps.api.app.infrastructure.execution.interface import ExecutionRequest
from apps.api.app.infrastructure.coverage.gcov import GcovCoverageProvider
from apps.api.app.schemas.sentinel_api import (
    ExecutionCreate,
    ExecutionResponse,
    CoverageResponse,
    MCDCResponse,
)

router = APIRouter(prefix="/projects/{project_id}/executions", tags=["Executions & Verification"])

stub_service = StubGeneratorService()
harness_service = HarnessGeneratorService()
execution_engine = LocalProcessExecutionEngine()
coverage_provider = GcovCoverageProvider()
mcdc_analyzer = MCDCAnalyzerService()
evidence_service = EvidenceService()


@router.post("", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
def trigger_execution(project_id: str, payload: ExecutionCreate, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter_by(id=payload.test_case_id, project_id=project_id).first()
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TEST_CASE_NOT_FOUND", "message": f"Test case {payload.test_case_id} not found"},
        )

    fn = tc.target_function
    if not fn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_TARGET_FUNCTION", "message": "Test case has no target function defined"},
        )

    # 1. Fetch sources
    sources = db.query(SourceFile).filter_by(project_id=project_id).all()
    source_map = {s.filename: s.content for s in sources}
    if not source_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_SOURCES", "message": "No source files available for execution"},
        )

    # 2. Fetch stubs
    stubs = db.query(StubConfiguration).filter_by(project_id=project_id).all()
    stub_defs = []
    for s in stubs:
        dep = s.dependency
        ret_t = dep.return_type if (dep and dep.return_type) else "int"
        param_specs = []
        if dep and dep.parameters:
            for p in dep.parameters:
                param_specs.append(
                    StubParameterSpec(
                        name=p.get("name", "arg"),
                        type=p.get("type", "int"),
                        is_pointer=p.get("is_pointer", False),
                    )
                )
        stub_defs.append(
            StubDefinition(
                function_name=s.function_name,
                return_type=ret_t,
                parameters=param_specs,
                return_values=s.return_values,
                output_params=s.output_params,
                expected_call_count=s.expected_call_count,
                call_order=s.call_order,
                custom_c_body=s.custom_c_body,
            )
        )
    gen_stubs = stub_service.generate_stubs(stub_defs) if stub_defs else None

    # 3. Fetch hooks
    hooks = db.query(UserHook).filter_by(project_id=project_id, is_active=True).all()
    hook_defs = [
        HookDefinition(stage=h.stage, code_snippet=h.code_snippet, order_index=h.order_index)
        for h in hooks
    ]

    # 4. Fetch test vectors
    vector_defs = [
        TestVectorDefinition(vector_index=v.vector_index, inputs=v.inputs, expected_outputs=v.expected_outputs)
        for v in sorted(tc.test_vectors, key=lambda x: x.vector_index)
    ]

    # Reconstruct normalized function
    norm_fn = NormalizedFunction(
        name=fn.name,
        return_type=fn.return_type,
        parameters=[NormalizedParameter(**p) for p in fn.parameters],
        decisions=[NormalizedDecision(**d) for d in fn.decisions],
    )

    harness_req = HarnessGeneratorRequest(
        target_function=norm_fn,
        has_stubs=bool(gen_stubs),
        hooks=hook_defs,
        test_vectors=vector_defs,
    )
    harness_code = harness_service.generate_harness(harness_req)

    # 5. Create Execution DB record
    exec_id = f"exec-{uuid.uuid4().hex[:12]}"
    src_checksum = evidence_service.compute_source_checksum(source_map)
    stub_checksum = evidence_service.compute_config_checksum([s.model_dump() for s in stub_defs]) if stub_defs else None
    vec_checksum = evidence_service.compute_config_checksum([v.model_dump() for v in vector_defs]) if vector_defs else None

    exec_record = Execution(
        id=exec_id,
        project_id=project_id,
        test_case_id=tc.id,
        status=ExecutionStatus.RUNNING,
        source_checksum=src_checksum,
        stub_checksum=stub_checksum,
        vector_checksum=vec_checksum,
    )
    db.add(exec_record)
    db.commit()

    # 6. Execute in isolated engine
    exec_req = ExecutionRequest(
        execution_id=exec_id,
        source_files=source_map,
        harness_content=harness_code,
        stub_header_content=gen_stubs.header_content if gen_stubs else None,
        stub_source_content=gen_stubs.source_content if gen_stubs else None,
        timeout_seconds=payload.timeout_seconds,
        compiler_flags=payload.compiler_flags,
    )
    run_res = execution_engine.execute(exec_req)

    exec_record.status = run_res.status
    exec_record.exit_code = run_res.exit_code
    exec_record.stdout = run_res.stdout
    exec_record.stderr = run_res.stderr
    exec_record.duration_ms = run_res.duration_ms
    exec_record.results_summary = run_res.results_json or {"status": run_res.status.value}
    db.commit()

    # 7. Coverage
    cov_rep = coverage_provider.parse_coverage(Path(run_res.workspace_dir), fn.source_file.filename if fn.source_file else "target.c")
    cov_record = CoverageResult(
        execution_id=exec_id,
        statement_coverage_pct=cov_rep.statement_coverage_pct,
        branch_coverage_pct=cov_rep.branch_coverage_pct,
        function_coverage_pct=cov_rep.function_coverage_pct,
        line_coverage_pct=cov_rep.line_coverage_pct,
        raw_coverage_data=cov_rep.raw_data,
    )
    db.add(cov_record)

    # 8. MC/DC Analysis
    vector_inputs = []
    for idx, v in enumerate(sorted(tc.test_vectors, key=lambda x: x.vector_index)):
        env_dict = dict(v.inputs)
        for s in stubs:
            ret_val = s.return_values[idx] if idx < len(s.return_values) else (s.return_values[-1] if s.return_values else 0)
            env_dict[s.function_name] = ret_val
            if s.function_name.startswith("sensor"):
                env_dict["sensor_val"] = ret_val
                env_dict["sensor"] = ret_val
        vector_inputs.append(env_dict)

    mcdc_output = mcdc_analyzer.analyze(norm_fn.decisions, vector_inputs)
    mcdc_record = MCDCResult(
        execution_id=exec_id,
        coverage_percentage=mcdc_output.coverage_percentage,
        decisions=[d.model_dump() for d in mcdc_output.decisions],
        gap_analysis=[g.model_dump() for g in mcdc_output.gap_recommendations],
    )
    db.add(mcdc_record)

    # 9. Evidence Record
    evidence_report = evidence_service.build_evidence_record(
        evidence_id=f"EVID-{exec_id[:8]}",
        project_id=project_id,
        execution_id=exec_id,
        target_function=fn.name,
        requirement_ids=[tc.requirement.identifier] if tc.requirement else [],
        source_files=source_map,
        stubs=[s.model_dump() for s in stub_defs],
        vectors=[v.model_dump() for v in vector_defs],
        compiler_info={"name": "gcc", "flags": payload.compiler_flags},
        execution_status=run_res.status,
        duration_ms=run_res.duration_ms,
        stdout=run_res.stdout,
        stderr=run_res.stderr,
        coverage_data=cov_rep.model_dump(),
        mcdc_data=mcdc_output.model_dump(),
    )
    ev_record = EvidenceRecord(
        id=evidence_report.evidence_id,
        project_id=project_id,
        execution_id=exec_id,
        freshness=EvidenceFreshness.CURRENT,
        source_checksum=src_checksum,
        stub_checksum=stub_checksum,
        vector_checksum=vec_checksum,
        evidence_json=evidence_report.model_dump(),
    )
    db.add(ev_record)
    db.commit()
    db.refresh(exec_record)

    return ExecutionResponse(
        execution_id=exec_record.id,
        project_id=exec_record.project_id,
        test_case_id=exec_record.test_case_id,
        status=exec_record.status,
        exit_code=exec_record.exit_code,
        duration_ms=exec_record.duration_ms,
        results_summary=exec_record.results_summary,
        created_at=exec_record.created_at,
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution(project_id: str, execution_id: str, db: Session = Depends(get_db)):
    ex = db.query(Execution).filter_by(id=execution_id, project_id=project_id).first()
    if not ex:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXECUTION_NOT_FOUND", "message": f"Execution {execution_id} not found"},
        )
    return ExecutionResponse(
        execution_id=ex.id,
        project_id=ex.project_id,
        test_case_id=ex.test_case_id,
        status=ex.status,
        exit_code=ex.exit_code,
        duration_ms=ex.duration_ms,
        results_summary=ex.results_summary,
        created_at=ex.created_at,
    )


@router.get("/{execution_id}/coverage", response_model=CoverageResponse)
def get_execution_coverage(project_id: str, execution_id: str, db: Session = Depends(get_db)):
    cov = db.query(CoverageResult).filter_by(execution_id=execution_id).first()
    if not cov:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "COVERAGE_NOT_FOUND", "message": f"Coverage for execution {execution_id} not found"},
        )
    return CoverageResponse(
        execution_id=cov.execution_id,
        statement_coverage_pct=cov.statement_coverage_pct,
        branch_coverage_pct=cov.branch_coverage_pct,
        function_coverage_pct=cov.function_coverage_pct,
        line_coverage_pct=cov.line_coverage_pct,
        total_lines=len(cov.raw_coverage_data.get("lines", [])),
        covered_lines=int(cov.line_coverage_pct * len(cov.raw_coverage_data.get("lines", [])) / 100.0) if cov.raw_coverage_data.get("lines") else 0,
        total_branches=sum(len(l.get("branches", [])) for l in cov.raw_coverage_data.get("lines", [])),
        covered_branches=sum(sum(1 for b in l.get("branches", []) if b.get("count", 0) > 0) for l in cov.raw_coverage_data.get("lines", [])),
    )


@router.get("/{execution_id}/mcdc", response_model=MCDCResponse)
def get_execution_mcdc(project_id: str, execution_id: str, db: Session = Depends(get_db)):
    mcdc = db.query(MCDCResult).filter_by(execution_id=execution_id).first()
    if not mcdc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MCDC_NOT_FOUND", "message": f"MC/DC for execution {execution_id} not found"},
        )
    return MCDCResponse(
        execution_id=mcdc.execution_id,
        coverage_percentage=mcdc.coverage_percentage,
        decisions=mcdc.decisions,
        gap_recommendations=mcdc.gap_analysis,
    )
