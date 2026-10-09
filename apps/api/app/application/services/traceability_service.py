from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TraceabilityNode(BaseModel):
    id: str
    type: str  # requirement, function, test_case, execution, coverage, evidence
    label: str
    status: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TraceabilityEdge(BaseModel):
    source: str
    target: str
    relation: str  # verified_by, executed_in, covers, documented_by


class TraceabilityGraph(BaseModel):
    project_id: str
    nodes: List[TraceabilityNode] = Field(default_factory=list)
    edges: List[TraceabilityEdge] = Field(default_factory=list)
    links: List[Dict[str, Any]] = Field(default_factory=list)


class TraceabilityService:
    """Builds and exposes the complete verification traceability graph and requirement mapping."""

    def build_graph(
        self,
        project_id: str,
        requirements: List[Any],
        functions: List[Any],
        test_cases: List[Any],
        executions: List[Any],
        evidences: List[Any],
    ) -> TraceabilityGraph:
        nodes: List[TraceabilityNode] = []
        edges: List[TraceabilityEdge] = []
        links_for_frontend: List[Dict[str, Any]] = []

        # Requirements
        for r in requirements:
            r_id = f"REQ:{r.identifier}"
            nodes.append(TraceabilityNode(
                id=r_id,
                type="requirement",
                label=f"{r.identifier}: {r.title}",
                metadata={"req_type": r.req_type.value if hasattr(r.req_type, "value") else str(r.req_type)}
            ))
            links_for_frontend.append({
                "reqId": r.identifier,
                "description": r.title,
            })

        # Functions
        for f in functions:
            f_id = f"FUNC:{f.name}"
            nodes.append(TraceabilityNode(
                id=f_id,
                type="function",
                label=f.name,
                metadata={"return_type": f.return_type}
            ))

        # Test Cases
        for tc in test_cases:
            tc_id = f"TC:{tc.name}"
            nodes.append(TraceabilityNode(
                id=tc_id,
                type="test_case",
                label=tc.name,
            ))
            # Link to requirement
            if tc.requirement:
                r_id = f"REQ:{tc.requirement.identifier}"
                edges.append(TraceabilityEdge(source=r_id, target=tc_id, relation="verified_by"))
            # Link to target function
            if tc.target_function:
                f_id = f"FUNC:{tc.target_function.name}"
                edges.append(TraceabilityEdge(source=f_id, target=tc_id, relation="tested_by"))

        # Executions
        for ex in executions:
            ex_id = f"RUN:{ex.id[:8]}"
            nodes.append(TraceabilityNode(
                id=ex_id,
                type="execution",
                label=f"Run {ex.id[:8]}",
                status=ex.status.value if hasattr(ex.status, "value") else str(ex.status),
            ))
            if ex.test_case:
                tc_id = f"TC:{ex.test_case.name}"
                edges.append(TraceabilityEdge(source=tc_id, target=ex_id, relation="executed_in"))

            # Coverage & Evidence
            if ex.coverage:
                cov_id = f"COV:{ex.id[:8]}"
                nodes.append(TraceabilityNode(
                    id=cov_id,
                    type="coverage",
                    label=f"Stmt: {ex.coverage.statement_coverage_pct}% | Branch: {ex.coverage.branch_coverage_pct}%",
                    metadata={"statement_pct": ex.coverage.statement_coverage_pct}
                ))
                edges.append(TraceabilityEdge(source=ex_id, target=cov_id, relation="covers"))

            if ex.evidence:
                ev_id = f"EVID:{ex.evidence.id[:8]}"
                nodes.append(TraceabilityNode(
                    id=ev_id,
                    type="evidence",
                    label=f"Evidence ({ex.evidence.freshness.value})",
                    status=ex.evidence.freshness.value,
                ))
                edges.append(TraceabilityEdge(source=ex_id, target=ev_id, relation="documented_by"))

        return TraceabilityGraph(
            project_id=project_id,
            nodes=nodes,
            edges=edges,
            links=links_for_frontend,
        )

    def suggest_links(
        self,
        requirements: List[Any],
        functions: List[Any],
        confidence_threshold: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """Suggests candidate links between requirements and functions without assuming code correctness."""
        suggestions: List[Dict[str, Any]] = []

        for req in requirements:
            req_text = f"{req.identifier} {req.title} {req.description}".lower()
            for fn in functions:
                score = 0.0
                reasons: List[str] = []

                # Exact function name mentioned
                if fn.name.lower() in req_text:
                    score += 0.6
                    reasons.append(f"Function name '{fn.name}' explicitly mentioned in requirement")

                # Keyword overlap with function name parts
                fn_parts = [p for p in fn.name.lower().split("_") if len(p) > 2]
                matched_parts = [p for p in fn_parts if p in req_text]
                if matched_parts:
                    part_score = min(0.3, len(matched_parts) * 0.1)
                    score += part_score
                    reasons.append(f"Matched keyword tokens: {', '.join(matched_parts)}")

                # Parameter references in requirement
                if hasattr(fn, "parameters") and fn.parameters:
                    param_names = [p.get("name", "").lower() for p in fn.parameters if isinstance(p, dict)]
                    matched_params = [p for p in param_names if p and p in req_text]
                    if matched_params:
                        score += min(0.3, len(matched_params) * 0.15)
                        reasons.append(f"Matched parameter tokens: {', '.join(matched_params)}")

                score = min(1.0, score)
                if score >= confidence_threshold:
                    suggestions.append({
                        "requirement_id": req.id,
                        "requirement_identifier": req.identifier,
                        "function_id": fn.id,
                        "function_name": fn.name,
                        "confidence_score": round(score, 2),
                        "rationale": "; ".join(reasons),
                        "status": "SUGGESTED",
                    })

        return suggestions

