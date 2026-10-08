import ast
import operator
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from apps.api.app.domain.interfaces.source_parser import (
    NormalizedDecision,
    NormalizedCondition,
)
from apps.api.app.domain.enums import MCDCConditionStatus


class MCDCConditionReport(BaseModel):
    id: str  # C1, C2
    expression: str
    status: MCDCConditionStatus
    independence_proven: bool
    independence_pair: Optional[Tuple[int, int]] = None  # (vector_idx_A, vector_idx_B)


class MCDCDecisionReport(BaseModel):
    decision_id: str
    expression: str
    decision_outcomes_tested: List[bool] = Field(default_factory=list)
    conditions: List[MCDCConditionReport] = Field(default_factory=list)
    coverage_percentage: float = 0.0


class MCDCRecommendation(BaseModel):
    decision_id: str
    condition_id: str
    condition_expression: str
    status: str = "NOT_PROVEN"
    rationale: str
    recommended_truth_assignment: Dict[str, bool]
    candidate_test_vector_inputs: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = (
        "Candidate vector advisory only. DO-178C verification requires engineering review and qualification."
    )


class MCDCAnalysisOutput(BaseModel):
    coverage_percentage: float
    total_conditions: int
    proven_conditions: int
    decisions: List[MCDCDecisionReport]
    gap_recommendations: List[MCDCRecommendation]


class ExpressionEvaluator:
    """Safely evaluates boolean condition expressions given vector inputs."""
    
    SAFE_OPS = {
        ast.Gt: operator.gt,
        ast.Lt: operator.lt,
        ast.GtE: operator.ge,
        ast.LtE: operator.le,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
        ast.Not: operator.not_,
    }

    @classmethod
    def eval_condition(cls, expr: str, inputs: Dict[str, Any]) -> bool:
        # Normalize C operators to Python if needed
        py_expr = expr.replace("&&", " and ").replace("||", " or ").replace("!", " not ")
        try:
            tree = ast.parse(py_expr, mode="eval")
            return bool(cls._eval_node(tree.body, inputs))
        except Exception:
            # Fallback evaluation with safe variable substitution
            safe_env = {k: v for k, v in inputs.items() if isinstance(v, (int, float, bool))}
            try:
                return bool(eval(py_expr, {"__builtins__": {}}, safe_env))
            except Exception:
                return False

    @classmethod
    def _eval_node(cls, node: ast.AST, env: Dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            raise ValueError(f"Unknown variable {node.id}")
        elif isinstance(node, ast.Compare):
            left = cls._eval_node(node.left, env)
            for op, comparator in zip(node.ops, node.comparators):
                right = cls._eval_node(comparator, env)
                op_type = type(op)
                if op_type in cls.SAFE_OPS:
                    if not cls.SAFE_OPS[op_type](left, right):
                        return False
                    left = right
                else:
                    raise ValueError(f"Unsupported comparator operator {op}")
            return True
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(cls._eval_node(val, env) for val in node.values)
            elif isinstance(node.op, ast.Or):
                return any(cls._eval_node(val, env) for val in node.values)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not cls._eval_node(node.operand, env)
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left, env)
            right = cls._eval_node(node.right, env)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if isinstance(node.op, ast.Div): return left / right
        raise ValueError(f"Unsupported node type: {type(node)}")


class MCDCAnalyzerService:
    """
    Deterministic Modified Condition / Decision Coverage (MC/DC) analyzer and Gap Advisor.
    Identifies condition independence pairs and candidate vector gaps.
    """

    def analyze(
        self,
        decisions: List[NormalizedDecision],
        test_vectors: List[Dict[str, Any]],  # List of vector input dicts
    ) -> MCDCAnalysisOutput:
        total_conditions_count = 0
        proven_conditions_count = 0
        decision_reports: List[MCDCDecisionReport] = []
        all_recommendations: List[MCDCRecommendation] = []

        for dec in decisions:
            conditions = dec.conditions
            if not conditions:
                continue

            num_conditions = len(conditions)
            total_conditions_count += num_conditions

            # 1. Build evaluation matrix for all test vectors
            # vector_evals[vector_idx] = {"conditions": {C1: bool, C2: bool}, "decision": bool}
            vector_evals: List[Dict[str, Any]] = []
            for v_idx, vec_inputs in enumerate(test_vectors):
                cond_results: Dict[str, bool] = {}
                for cond in conditions:
                    c_val = ExpressionEvaluator.eval_condition(cond.expression, vec_inputs)
                    cond_results[cond.id] = c_val

                # Evaluate overall decision
                d_val = ExpressionEvaluator.eval_condition(dec.expression, vec_inputs)
                vector_evals.append({
                    "vector_index": v_idx + 1,
                    "inputs": vec_inputs,
                    "conditions": cond_results,
                    "decision": d_val,
                })

            # Check decision outcomes tested
            decision_outcomes = list({v["decision"] for v in vector_evals})

            # 2. Check MC/DC independence pair for each condition
            cond_reports: List[MCDCConditionReport] = []
            proven_in_decision = 0

            for target_cond in conditions:
                cid = target_cond.id
                independence_found = False
                found_pair = None

                # Search for two vectors v1 and v2:
                # - v1[cid] != v2[cid]
                # - for all other c != cid: v1[c] == v2[c] (Unique Cause MC/DC)
                # - v1[decision] != v2[decision]
                for i in range(len(vector_evals)):
                    if independence_found:
                        break
                    v1 = vector_evals[i]
                    for j in range(i + 1, len(vector_evals)):
                        v2 = vector_evals[j]
                        if v1["conditions"][cid] != v2["conditions"][cid]:
                            if v1["decision"] != v2["decision"]:
                                # Check if other conditions held constant
                                other_constant = True
                                for other_c in conditions:
                                    if other_c.id != cid:
                                        if v1["conditions"][other_c.id] != v2["conditions"][other_c.id]:
                                            other_constant = False
                                            break
                                if other_constant:
                                    independence_found = True
                                    found_pair = (v1["vector_index"], v2["vector_index"])
                                    break

                if independence_found:
                    status = MCDCConditionStatus.PROVEN
                    proven_in_decision += 1
                    proven_conditions_count += 1
                else:
                    status = MCDCConditionStatus.NOT_PROVEN
                    # Generate gap advisory recommendation
                    rec = self._generate_gap_recommendation(dec, target_cond, vector_evals)
                    if rec:
                        all_recommendations.append(rec)

                cond_reports.append(MCDCConditionReport(
                    id=cid,
                    expression=target_cond.expression,
                    status=status,
                    independence_proven=independence_found,
                    independence_pair=found_pair,
                ))

            dec_pct = (proven_in_decision / num_conditions * 100.0) if num_conditions > 0 else 100.0
            decision_reports.append(MCDCDecisionReport(
                decision_id=dec.id,
                expression=dec.expression,
                decision_outcomes_tested=decision_outcomes,
                conditions=cond_reports,
                coverage_percentage=round(dec_pct, 2),
            ))

        overall_pct = (
            (proven_conditions_count / total_conditions_count * 100.0)
            if total_conditions_count > 0
            else 100.0
        )

        return MCDCAnalysisOutput(
            coverage_percentage=round(overall_pct, 2),
            total_conditions=total_conditions_count,
            proven_conditions=proven_conditions_count,
            decisions=decision_reports,
            gap_recommendations=all_recommendations,
        )

    def _generate_gap_recommendation(
        self,
        decision: NormalizedDecision,
        missing_cond: NormalizedCondition,
        vector_evals: List[Dict[str, Any]],
    ) -> Optional[MCDCRecommendation]:
        """Identifies missing independent truth assignment and recommends candidate test vector."""
        if not vector_evals:
            return None

        # Take an existing vector where missing_cond had a known state
        base_vector = vector_evals[0]
        base_cond_state = base_vector["conditions"].get(missing_cond.id, True)
        needed_cond_state = not base_cond_state

        target_assignment = dict(base_vector["conditions"])
        target_assignment[missing_cond.id] = needed_cond_state

        # Synthesize candidate inputs from base vector
        candidate_inputs = dict(base_vector["inputs"])
        # Heuristic for comparison adjustments
        for var_name in missing_cond.variable_references:
            if var_name in candidate_inputs:
                curr_val = candidate_inputs[var_name]
                if isinstance(curr_val, (int, float)):
                    if ">" in missing_cond.expression:
                        # If needed false, decrement below threshold; if needed true, increment
                        candidate_inputs[var_name] = (curr_val - 100) if not needed_cond_state else (curr_val + 100)
                    elif "<" in missing_cond.expression:
                        candidate_inputs[var_name] = (curr_val + 5000) if not needed_cond_state else (curr_val - 5000)

        return MCDCRecommendation(
            decision_id=decision.id,
            condition_id=missing_cond.id,
            condition_expression=missing_cond.expression,
            status="NOT_PROVEN",
            rationale=(
                f"Condition {missing_cond.id} ({missing_cond.expression}) requires an independent condition effect "
                f"pair where other conditions remain fixed while {missing_cond.id} flips from {base_cond_state} to {needed_cond_state}."
            ),
            recommended_truth_assignment=target_assignment,
            candidate_test_vector_inputs=candidate_inputs,
        )

