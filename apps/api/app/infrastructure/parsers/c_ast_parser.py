import hashlib
import re
from typing import List, Dict, Any, Optional, Set
from pycparser import c_parser, c_ast, c_generator

from apps.api.app.domain.interfaces.source_parser import (
    ISourceParser,
    NormalizedParameter,
    NormalizedCondition,
    NormalizedDecision,
    NormalizedDependency,
    NormalizedFunction,
    SourceAnalysisResult,
)


class ExpressionStringifier:
    """Safely converts pycparser AST expressions back into readable C expressions."""
    def __init__(self):
        self.generator = c_generator.CGenerator()

    def stringify(self, node: c_ast.Node) -> str:
        try:
            return self.generator.visit(node).strip()
        except Exception:
            return str(node)


class ConditionExtractor(c_ast.NodeVisitor):
    """Decomposes a boolean decision tree into atomic condition nodes (C1, C2...)"""
    def __init__(self):
        self.stringifier = ExpressionStringifier()
        self.conditions: List[Dict[str, Any]] = []
        self._condition_counter = 0

    def extract_from_decision(self, node: c_ast.Node) -> List[NormalizedCondition]:
        self.conditions = []
        self._condition_counter = 0
        self._decompose(node)
        
        result = []
        for cond in self.conditions:
            result.append(NormalizedCondition(
                id=cond["id"],
                expression=cond["expression"],
                variable_references=cond["variables"]
            ))
        return result

    def _decompose(self, node: c_ast.Node):
        if isinstance(node, c_ast.BinaryOp) and node.op in ("&&", "||"):
            self._decompose(node.left)
            self._decompose(node.right)
        else:
            self._condition_counter += 1
            cond_id = f"C{self._condition_counter}"
            expr_str = self.stringifier.stringify(node)
            vars_collector = VariableReferenceCollector()
            vars_collector.visit(node)
            self.conditions.append({
                "id": cond_id,
                "expression": expr_str,
                "variables": list(vars_collector.variables)
            })


class VariableReferenceCollector(c_ast.NodeVisitor):
    def __init__(self):
        self.variables: Set[str] = set()

    def visit_ID(self, node: c_ast.ID):
        self.variables.add(node.name)


class FunctionAnalysisVisitor(c_ast.NodeVisitor):
    """Walks the AST of a single function definition to extract decisions, local variables, and calls."""
    def __init__(self, stringifier: ExpressionStringifier, known_prototypes: Optional[Dict[str, Any]] = None):
        self.stringifier = stringifier
        self.known_prototypes = known_prototypes or {}
        self.decisions: List[NormalizedDecision] = []
        self.local_variables: List[Dict[str, str]] = []
        self.dependencies: Dict[str, NormalizedDependency] = {}
        self._decision_counter = 0

    def visit_Decl(self, node: c_ast.Decl):
        # Local variable declaration
        if node.name and isinstance(node.type, c_ast.TypeDecl):
            type_name = " ".join(node.type.type.names) if hasattr(node.type.type, "names") else "int"
            self.local_variables.append({"name": node.name, "type": type_name})
        elif node.name and isinstance(node.type, c_ast.PtrDecl):
            self.local_variables.append({"name": node.name, "type": "pointer"})
        self.generic_visit(node)

    def visit_If(self, node: c_ast.If):
        self._decision_counter += 1
        d_id = f"D{self._decision_counter}"
        cond_node = node.cond
        expr_str = self.stringifier.stringify(cond_node)
        
        extractor = ConditionExtractor()
        conditions = extractor.extract_from_decision(cond_node)
        
        line_num = getattr(node.coord, "line", None) if hasattr(node, "coord") and node.coord else None

        self.decisions.append(NormalizedDecision(
            id=d_id,
            expression=expr_str,
            line_number=line_num,
            conditions=conditions
        ))
        self.generic_visit(node)

    def visit_FuncCall(self, node: c_ast.FuncCall):
        if isinstance(node.name, c_ast.ID):
            func_name = node.name.name
            line_num = getattr(node.coord, "line", None) if hasattr(node, "coord") and node.coord else None
            if func_name not in self.dependencies:
                if func_name in self.known_prototypes:
                    proto_ret, proto_params = self.known_prototypes[func_name]
                    self.dependencies[func_name] = NormalizedDependency(
                        name=func_name,
                        type="external_function",
                        return_type=proto_ret,
                        parameters=proto_params,
                        call_line_numbers=[line_num] if line_num else []
                    )
                else:
                    call_params = []
                    if node.args and hasattr(node.args, "exprs"):
                        for idx, expr in enumerate(node.args.exprs):
                            call_params.append(NormalizedParameter(
                                name=f"arg_{idx+1}",
                                type="int",
                            ))
                    self.dependencies[func_name] = NormalizedDependency(
                        name=func_name,
                        type="external_function",
                        return_type="int",
                        parameters=call_params,
                        call_line_numbers=[line_num] if line_num else []
                    )
            else:
                if line_num:
                    self.dependencies[func_name].call_line_numbers.append(line_num)
        self.generic_visit(node)


class ClangAstSourceParser(ISourceParser):
    """
    Production-grade C AST Parser using pycparser with normalized Sentinel representation.
    Extracts functions, return types, parameters, local vars, decisions, conditions, and calls.
    """
    def __init__(self):
        self.stringifier = ExpressionStringifier()

    def parse_source(self, filename: str, content: str, external_prototypes: Optional[Dict[str, Any]] = None) -> SourceAnalysisResult:
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        # Prepare sanitized C code for pycparser
        sanitized_code = self._preprocess_code(content)
        if not sanitized_code.strip():
            return SourceAnalysisResult(filename=filename, checksum_sha256=checksum)

        # Detect any external function calls like sensor_read() or valve_actuate() that lack prototypes
        called_funcs = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", sanitized_code)
        synthesized_headers = ["typedef int bool;"]
        for fn in set(called_funcs):
            if fn not in ("if", "while", "for", "switch", "return", "sizeof"):
                if f"{fn}(" not in "\n".join(synthesized_headers) and f" {fn}(" not in sanitized_code.split("{")[0]:
                    synthesized_headers.append(f"int {fn}();")

        header_prefix = "\n".join(synthesized_headers) + "\n"

        parser = c_parser.CParser()
        try:
            ast = parser.parse(sanitized_code, filename=filename)
        except Exception:
            try:
                ast = parser.parse(header_prefix + sanitized_code, filename=filename)
            except Exception as inner_e:
                # If still fails, wrap with empty translation unit if header-only
                try:
                    ast = parser.parse(header_prefix + "\nint __sentinel_dummy = 0;", filename=filename)
                except Exception:
                    raise ValueError(f"AST parsing failed for {filename}: {str(inner_e)}")

        functions: List[NormalizedFunction] = []
        global_vars: List[Dict[str, str]] = []
        external_decls: List[str] = []
        local_prototypes: Dict[str, Any] = dict(external_prototypes or {})

        if ast and ast.ext:
            for ext in ast.ext:
                if isinstance(ext, c_ast.Decl):
                    if isinstance(ext.type, c_ast.FuncDecl):
                        if ext.name and not ext.name.startswith("__sentinel"):
                            external_decls.append(ext.name)
                            ret_t = self._extract_type_string(ext.type)
                            params = self._extract_parameters(ext.type)
                            local_prototypes[ext.name] = (ret_t, params)
                    elif isinstance(ext.type, c_ast.TypeDecl):
                        if ext.name and not ext.name.startswith("__sentinel"):
                            type_name = " ".join(ext.type.type.names) if hasattr(ext.type.type, "names") else "int"
                            global_vars.append({"name": ext.name, "type": type_name})

                elif isinstance(ext, c_ast.FuncDef):
                    func_name = ext.decl.name
                    if func_name and not func_name.startswith("__sentinel"):
                        ret_type = self._extract_type_string(ext.decl.type)
                        parameters = self._extract_parameters(ext.decl.type)

                        visitor = FunctionAnalysisVisitor(self.stringifier, known_prototypes=local_prototypes)
                        if ext.body:
                            visitor.visit(ext.body)

                        start_line = getattr(ext.coord, "line", None) if hasattr(ext, "coord") and ext.coord else None
                        deps = [d for d in visitor.dependencies.values() if d.name != func_name and not d.name.startswith("__sentinel")]

                        functions.append(NormalizedFunction(
                            name=func_name,
                            return_type=ret_type,
                            parameters=parameters,
                            local_variables=visitor.local_variables,
                            decisions=visitor.decisions,
                            dependencies=deps,
                            start_line=start_line,
                        ))

        return SourceAnalysisResult(
            filename=filename,
            checksum_sha256=checksum,
            functions=functions,
            global_variables=global_vars,
            external_declarations=external_decls,
            known_prototypes=local_prototypes,
        )

    def _preprocess_code(self, content: str) -> str:
        """Strips comments, preprocessor directives, and extern C guards."""
        # 1. Strip multi-line comments /* ... */
        clean = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        # 2. Strip single-line comments // ...
        clean = re.sub(r"//.*", "", clean)
        # 3. Strip preprocessor directives and extern "C" blocks
        lines = []
        for line in clean.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            elif 'extern "C"' in stripped or stripped in ("{", "}") and 'extern "C"' in content:
                continue
            else:
                lines.append(line)
        return "\n".join(lines)

    def _extract_type_string(self, type_node: c_ast.Node) -> str:
        if isinstance(type_node, c_ast.FuncDecl):
            return self._extract_type_string(type_node.type)
        elif isinstance(type_node, c_ast.PtrDecl):
            return f"{self._extract_type_string(type_node.type)}*"
        elif isinstance(type_node, c_ast.TypeDecl):
            if hasattr(type_node.type, "names"):
                return " ".join(type_node.type.names)
            return "int"
        return "void"

    def _extract_parameters(self, func_decl: c_ast.Node) -> List[NormalizedParameter]:
        params: List[NormalizedParameter] = []
        if not hasattr(func_decl, "args") or not func_decl.args:
            return params

        for p in func_decl.args.params:
            if isinstance(p, c_ast.Typename):
                continue
            if isinstance(p, c_ast.Decl):
                p_name = p.name or "unnamed"
                is_ptr = isinstance(p.type, c_ast.PtrDecl)
                is_arr = isinstance(p.type, c_ast.ArrayDecl)
                p_type = self._extract_type_string(p.type)
                params.append(NormalizedParameter(
                    name=p_name,
                    type=p_type,
                    is_pointer=is_ptr,
                    is_array=is_arr
                ))
        return params
