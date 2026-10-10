import uuid
import pytest
from apps.api.app.application.services import (
    StubGeneratorService,
    StubDefinition,
    HarnessGeneratorService,
    HarnessGeneratorRequest,
    TestVectorDefinition,
)
from apps.api.app.domain.interfaces.source_parser import NormalizedFunction, NormalizedParameter
from apps.api.app.domain.enums import ExecutionStatus
from apps.api.app.infrastructure.execution.process_engine import LocalProcessExecutionEngine
from apps.api.app.infrastructure.execution.interface import ExecutionRequest


def test_compile_and_execute_cabin_pressure():
    # 1. Define target function
    fn = NormalizedFunction(
        name="cabin_pressure_control",
        return_type="int",
        parameters=[
            NormalizedParameter(name="pressure", type="int"),
            NormalizedParameter(name="altitude", type="int"),
        ],
    )

    c_source = """
    int sensor_read(void);

    int cabin_pressure_control(int pressure, int altitude) {
        int sensor = sensor_read();
        if (pressure > 900 && altitude < 10000 && sensor > 900) {
            return 1;
        }
        return 0;
    }
    """

    # 2. Stub sensor_read
    stub_service = StubGeneratorService()
    stub_def = StubDefinition(
        function_name="sensor_read",
        return_type="int",
        return_values=[950, 950, 950],
        expected_call_count=3,
    )
    stubs = stub_service.generate_stubs([stub_def])

    # 3. Generate test harness with test vectors
    harness_service = HarnessGeneratorService()
    vectors = [
        TestVectorDefinition(vector_index=1, inputs={"pressure": 950, "altitude": 8000}, expected_outputs={"return": 1}),
        TestVectorDefinition(vector_index=2, inputs={"pressure": 850, "altitude": 8000}, expected_outputs={"return": 0}),
    ]
    harness_req = HarnessGeneratorRequest(
        target_function=fn,
        has_stubs=True,
        test_vectors=vectors,
    )
    harness_code = harness_service.generate_harness(harness_req)

    # 4. Execute via LocalProcessExecutionEngine
    engine = LocalProcessExecutionEngine()
    exec_id = f"test-exec-{uuid.uuid4().hex[:8]}"
    exec_req = ExecutionRequest(
        execution_id=exec_id,
        source_files={"cabin_pressure.c": c_source},
        harness_content=harness_code,
        stub_header_content=stubs.header_content,
        stub_source_content=stubs.source_content,
        timeout_seconds=5,
    )

    result = engine.execute(exec_req)

    assert result.status == ExecutionStatus.PASSED
    assert result.exit_code == 0
    assert result.results_json is not None
    assert result.results_json["status"] == "PASSED"
    assert result.results_json["passed_count"] == 2
    assert result.results_json["failed_count"] == 0

    # Verify coverage files generated
    artifact_types = [a.artifact_type for a in result.artifacts]
    assert "binary" in artifact_types
    assert "gcno" in artifact_types
    assert "gcda" in artifact_types

