import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from apps.api.app.domain.interfaces.source_parser import NormalizedParameter, NormalizedFunction
from apps.api.app.domain.enums import HookStage


class HookDefinition(BaseModel):
    stage: HookStage
    code_snippet: str
    order_index: int = 0
    is_active: bool = True


class TestVectorDefinition(BaseModel):
    __test__ = False
    vector_index: int
    inputs: Dict[str, Any]
    expected_outputs: Dict[str, Any]


class HarnessGeneratorRequest(BaseModel):
    target_function: NormalizedFunction
    source_header_or_extern: Optional[str] = None
    has_stubs: bool = False
    hooks: List[HookDefinition] = Field(default_factory=list)
    test_vectors: List[TestVectorDefinition] = Field(default_factory=list)


class HarnessGeneratorService:
    """
    Generates standalone, compilable C test harness with automated setup/teardown,
    stub invocation, before/after test hooks, and machine-readable JSON result output.
    """

    def generate_harness(self, req: HarnessGeneratorRequest) -> str:
        fn = req.target_function
        ret_type = fn.return_type.strip()
        is_void = ret_type == "void"

        # Organize hooks by stage
        setup_hooks = [h.code_snippet for h in sorted(req.hooks, key=lambda x: x.order_index) if h.stage == HookStage.SETUP and h.is_active]
        before_hooks = [h.code_snippet for h in sorted(req.hooks, key=lambda x: x.order_index) if h.stage == HookStage.BEFORE_TEST and h.is_active]
        after_hooks = [h.code_snippet for h in sorted(req.hooks, key=lambda x: x.order_index) if h.stage == HookStage.AFTER_TEST and h.is_active]
        teardown_hooks = [h.code_snippet for h in sorted(req.hooks, key=lambda x: x.order_index) if h.stage == HookStage.TEARDOWN and h.is_active]

        lines = [
            "/* ========================================================================= */",
            "/* HonAero Sentinel - Automated Test Harness                              */",
            "/* Target Function: " + fn.name + " */",
            "/* ========================================================================= */",
            "",
            "#include <stdio.h>",
            "#include <stdlib.h>",
            "#include <stdint.h>",
            "#include <stdbool.h>",
            "#include <math.h>",
            "#include <string.h>",
            "",
        ]

        if req.has_stubs:
            lines.append('#include "generated_stubs.h"')
            lines.append("")

        # Extern declaration of target function
        param_decls = [f"{p.type} {p.name}" for p in fn.parameters]
        param_sig = ", ".join(param_decls) if param_decls else "void"
        lines.append(f"extern {ret_type} {fn.name}({param_sig});")
        lines.append("")

        # Equality comparator helpers
        lines.extend([
            "static bool sentinel_compare_int(int64_t actual, int64_t expected) {",
            "    return actual == expected;",
            "}",
            "",
            "static bool sentinel_compare_double(double actual, double expected, double tolerance) {",
            "    return fabs(actual - expected) <= tolerance;",
            "}",
            "",
        ])

        # Main / Exported Entrypoint
        lines.append("#ifdef _WIN32")
        lines.append('__declspec(dllexport)')
        lines.append("#endif")
        lines.append("int sentinel_execute_harness(void) {")
        lines.append('    FILE *out = fopen("sentinel_result.json", "w");')
        lines.append('    if (!out) { out = stdout; }')
        lines.append("    int total_vectors = " + str(len(req.test_vectors)) + ";")
        lines.append("    int passed_count = 0;")
        lines.append("    int failed_count = 0;")
        lines.append("")
        lines.append('    fprintf(out, "{\\n");')
        lines.append(f'    fprintf(out, "  \\\"target_function\\\": \\\"{fn.name}\\\",\\n");')
        lines.append('    fprintf(out, "  \\\"vectors\\\": [\\n");')
        lines.append("")

        # Setup hook
        if setup_hooks:
            lines.append("    /* --- SETUP HOOKS --- */")
            for sh in setup_hooks:
                lines.append(f"    {sh}")
            lines.append("")

        # Test vectors loop
        for i, vec in enumerate(req.test_vectors):
            is_last = (i == len(req.test_vectors) - 1)
            comma = "" if is_last else ","
            v_idx = vec.vector_index

            lines.append(f"    /* === TEST VECTOR {v_idx} === */")
            lines.append("    {")

            # Before-test hook
            if before_hooks:
                lines.append("        /* Before-test hook */")
                for bh in before_hooks:
                    lines.append(f"        {bh}")

            # Prepare argument values
            call_args = []
            for p in fn.parameters:
                val = vec.inputs.get(p.name, 0)
                lines.append(f"        {p.type} arg_{p.name} = {val};")
                call_args.append(f"arg_{p.name}")

            call_str = f"{fn.name}({', '.join(call_args)})"

            # Expected return value
            expected_ret = vec.expected_outputs.get("return", vec.expected_outputs.get("result", 0))

            if not is_void:
                lines.append(f"        {ret_type} actual_ret = {call_str};")
                lines.append(f"        {ret_type} expected_ret = {expected_ret};")
                if "double" in ret_type or "float" in ret_type:
                    lines.append("        bool vec_passed = sentinel_compare_double(actual_ret, expected_ret, 1e-6);")
                    lines.append('        const char *format_str = "%f";')
                else:
                    lines.append("        bool vec_passed = sentinel_compare_int((int64_t)actual_ret, (int64_t)expected_ret);")
                    lines.append('        const char *format_str = "%lld";')
            else:
                lines.append(f"        {call_str};")
                lines.append("        bool vec_passed = true;")

            lines.append("        if (vec_passed) { passed_count++; } else { failed_count++; }")
            lines.append("")
            lines.append('        fprintf(out, "    {\\n");')
            lines.append(f'        fprintf(out, "      \\\"vector_index\\\": {v_idx},\\n");')
            lines.append('        fprintf(out, "      \\\"status\\\": \\\"%s\\\",\\n", vec_passed ? "PASS" : "FAIL");')
            if not is_void:
                lines.append('        fprintf(out, "      \\\"actual\\\": ");')
                lines.append('        fprintf(out, format_str, actual_ret);')
                lines.append('        fprintf(out, ",\\n");')
                lines.append('        fprintf(out, "      \\\"expected\\\": ");')
                lines.append('        fprintf(out, format_str, expected_ret);')
                lines.append('        fprintf(out, "\\n");')
            lines.append(f'        fprintf(out, "    }}{comma}\\n");')

            # After-test hook
            if after_hooks:
                lines.append("        /* After-test hook */")
                for ah in after_hooks:
                    lines.append(f"        {ah}")

            lines.append("    }")
            lines.append("")

        # Summary output
        lines.append('    fprintf(out, "  ],\\n");')
        lines.append('    fprintf(out, "  \\\"passed_count\\\": %d,\\n", passed_count);')
        lines.append('    fprintf(out, "  \\\"failed_count\\\": %d,\\n", failed_count);')
        lines.append('    fprintf(out, "  \\\"status\\\": \\\"%s\\\"\\n", failed_count == 0 ? "PASSED" : "FAILED");')
        lines.append('    fprintf(out, "}\\n");')
        lines.append("")

        # Teardown hooks
        if teardown_hooks:
            lines.append("    /* --- TEARDOWN HOOKS --- */")
            for th in teardown_hooks:
                lines.append(f"    {th}")
            lines.append("")

        lines.append('    if (out != stdout) { fclose(out); }')
        lines.append("    return (failed_count == 0) ? 0 : 1;")
        lines.append("}")
        lines.append("")
        lines.append("int main(void) {")
        lines.append("    return sentinel_execute_harness();")
        lines.append("}")

        return "\n".join(lines)
