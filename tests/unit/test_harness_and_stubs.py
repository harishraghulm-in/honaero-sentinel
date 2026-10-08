import pytest
from apps.api.app.application.services import (
    StubGeneratorService,
    StubDefinition,
    HarnessGeneratorService,
    HarnessGeneratorRequest,
    HookDefinition,
    TestVectorDefinition,
)
from apps.api.app.domain.interfaces.source_parser import NormalizedFunction, NormalizedParameter
from apps.api.app.domain.enums import HookStage


def test_stub_generator_successive_returns():
    service = StubGeneratorService()
    stubs = [
        StubDefinition(
            function_name="sensor_read",
            return_type="int",
            return_values=[950, 945, 960],
            expected_call_count=3,
        )
    ]
    code = service.generate_stubs(stubs)

    assert "int sensor_read(void);" in code.header_content
    assert "sentinel_stub_reset_sensor_read" in code.header_content
    assert "__sentinel_stub_call_count_sensor_read = 0;" in code.source_content
    assert "950, 945, 960" in code.source_content
    assert "int sensor_read(void)" in code.source_content


def test_harness_generator():
    service = HarnessGeneratorService()
    fn = NormalizedFunction(
        name="cabin_pressure_control",
        return_type="int",
        parameters=[
            NormalizedParameter(name="pressure", type="int"),
            NormalizedParameter(name="altitude", type="int"),
        ],
    )
    req = HarnessGeneratorRequest(
        target_function=fn,
        has_stubs=True,
        hooks=[
            HookDefinition(
                stage=HookStage.SETUP,
                code_snippet='printf("Setup initialized\\n");',
                order_index=0,
            ),
            HookDefinition(
                stage=HookStage.TEARDOWN,
                code_snippet='printf("Teardown complete\\n");',
                order_index=0,
            ),
        ],
        test_vectors=[
            TestVectorDefinition(
                vector_index=1,
                inputs={"pressure": 950, "altitude": 8000},
                expected_outputs={"return": 1},
            ),
            TestVectorDefinition(
                vector_index=2,
                inputs={"pressure": 850, "altitude": 8000},
                expected_outputs={"return": 0},
            ),
        ],
    )

    harness = service.generate_harness(req)
    assert "extern int cabin_pressure_control(int pressure, int altitude);" in harness
    assert '#include "generated_stubs.h"' in harness
    assert "Setup initialized" in harness
    assert "Teardown complete" in harness
    assert "cabin_pressure_control(arg_pressure, arg_altitude)" in harness
    assert "sentinel_result.json" in harness

