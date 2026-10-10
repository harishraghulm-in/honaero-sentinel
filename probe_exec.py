import sys
sys.path.insert(0, r"F:\hackathon project\honaero-sentinel")

from apps.api.app.infrastructure.execution.process_engine import LocalProcessExecutionEngine
from apps.api.app.infrastructure.execution.interface import ExecutionRequest

engine = LocalProcessExecutionEngine()

source_files = {
    "actuator.c": """
int actuator_control(int cmd, int pressure) {
    if (cmd == 1 && pressure > 100) return 1;
    return 0;
}
""",
    "actuator.h": "int actuator_control(int cmd, int pressure);"
}

req_pass = ExecutionRequest(
    execution_id="probe_pass_1",
    source_files=source_files,
    harness_content="""
#include <stdio.h>
#include <assert.h>
#include "actuator.h"
int main() {
    int res = actuator_control(1, 150);
    assert(res == 1);
    FILE *fp = fopen("sentinel_result.json", "w");
    if (fp) {
        fprintf(fp, "{\\"status\\": \\\"PASSED\\", \\\"failures\\\": 0}");
        fclose(fp);
    }
    return 0;
}
""",
    compiler_flags=["--coverage"]
)

res1 = engine.execute(req_pass)
print("PASS run:", res1.status, res1.exit_code, repr(res1.stderr))

req_fail = ExecutionRequest(
    execution_id="probe_fail_1",
    source_files=source_files,
    harness_content="""
#include <stdio.h>
#include <assert.h>
#include "actuator.h"
int main() {
    int res = actuator_control(0, 50);
    assert(res == 1); /* will abort/assert fail! */
    FILE *fp = fopen("sentinel_result.json", "w");
    if (fp) {
        fprintf(fp, "{\\"status\\": \\\"PASSED\\", \\\"failures\\\": 0}");
        fclose(fp);
    }
    return 0;
}
""",
    compiler_flags=["--coverage"]
)

res2 = engine.execute(req_fail)
print("FAIL run:", res2.status, res2.exit_code, repr(res2.stderr))
