from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StubParameterSpec(BaseModel):
    name: str
    type: str = "int"
    is_pointer: bool = False


class StubDefinition(BaseModel):
    function_name: str
    return_type: str = "int"
    parameters: List[StubParameterSpec] = Field(default_factory=list)
    return_values: List[Any] = Field(default_factory=list)
    output_params: Dict[str, Any] = Field(default_factory=dict)
    expected_call_count: Optional[int] = None
    call_order: Optional[int] = None
    custom_c_body: Optional[str] = None


class GeneratedStubCode(BaseModel):
    header_content: str
    source_content: str


class StubGeneratorService:
    """
    Generates deterministic, thread-safe C stub implementations with
    call-counting, successive return values, and output parameter mutation.
    """

    def generate_stubs(self, stubs: List[StubDefinition]) -> GeneratedStubCode:
        header_lines = [
            "/* HonAero Sentinel - Deterministic Verification Stubs Header */",
            "#ifndef SENTINEL_GENERATED_STUBS_H",
            "#define SENTINEL_GENERATED_STUBS_H",
            "",
            "#include <stdint.h>",
            "#include <stddef.h>",
            "",
            "#ifdef __cplusplus",
            'extern "C" {',
            "#endif",
            "",
        ]

        source_lines = [
            "/* HonAero Sentinel - Deterministic Verification Stubs Source */",
            '#include "generated_stubs.h"',
            "#include <stdio.h>",
            "#include <string.h>",
            "",
        ]

        for stub in stubs:
            fn = stub.function_name
            ret_type = stub.return_type.strip()
            
            # Format parameters
            if stub.parameters:
                param_decl_list = [f"{p.type} {p.name}" for p in stub.parameters]
                param_signature = ", ".join(param_decl_list)
            else:
                param_signature = "void"

            # Header declarations
            header_lines.append(f"/* Stub for {fn} */")
            header_lines.append(f"{ret_type} {fn}({param_signature});")
            header_lines.append(f"int sentinel_stub_get_call_count_{fn}(void);")
            header_lines.append(f"void sentinel_stub_reset_{fn}(void);")
            header_lines.append("")

            # Source implementations
            source_lines.append(f"/* State variables for {fn} */")
            source_lines.append(f"static int __sentinel_stub_call_count_{fn} = 0;")
            
            # Successive return values array
            ret_vals = stub.return_values if stub.return_values else [0]
            c_ret_vals = ", ".join(self._format_c_value(v, ret_type) for v in ret_vals)
            source_lines.append(f"static const {ret_type} __sentinel_stub_ret_vals_{fn}[] = {{ {c_ret_vals} }};")
            source_lines.append(f"static const int __sentinel_stub_ret_count_{fn} = {len(ret_vals)};")
            source_lines.append("")

            # Reset function
            source_lines.append(f"void sentinel_stub_reset_{fn}(void) {{")
            source_lines.append(f"    __sentinel_stub_call_count_{fn} = 0;")
            source_lines.append("}")
            source_lines.append("")

            # Query count function
            source_lines.append(f"int sentinel_stub_get_call_count_{fn}(void) {{")
            source_lines.append(f"    return __sentinel_stub_call_count_{fn};")
            source_lines.append("}")
            source_lines.append("")

            # Stub function body
            source_lines.append(f"{ret_type} {fn}({param_signature}) {{")
            source_lines.append(f"    int current_call = __sentinel_stub_call_count_{fn}++;")
            
            if stub.custom_c_body:
                source_lines.append(f"    {stub.custom_c_body}")
            else:
                # Handle output parameters if configured
                for param_name, param_val in stub.output_params.items():
                    source_lines.append(f"    if ({param_name} != NULL) {{")
                    source_lines.append(f"        *{param_name} = {param_val};")
                    source_lines.append("    }")

                if ret_type != "void":
                    source_lines.append(f"    if (current_call < __sentinel_stub_ret_count_{fn}) {{")
                    source_lines.append(f"        return __sentinel_stub_ret_vals_{fn}[current_call];")
                    source_lines.append("    }")
                    # Default to last return value for subsequent calls
                    source_lines.append(f"    return __sentinel_stub_ret_vals_{fn}[__sentinel_stub_ret_count_{fn} - 1];")

            source_lines.append("}")
            source_lines.append("")

        header_lines.extend([
            "#ifdef __cplusplus",
            "}",
            "#endif",
            "",
            "#endif /* SENTINEL_GENERATED_STUBS_H */"
        ])

        return GeneratedStubCode(
            header_content="\n".join(header_lines),
            source_content="\n".join(source_lines)
        )

    def _format_c_value(self, val: Any, ret_type: str) -> str:
        if isinstance(val, bool):
            return "1" if val else "0"
        elif isinstance(val, (int, float)):
            return str(val)
        elif isinstance(val, str):
            if ret_type in ("char*", "const char*"):
                return f'"{val}"'
            return val
        return str(val)

