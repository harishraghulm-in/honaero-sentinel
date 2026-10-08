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


class TraceabilityService:
    """Builds and exposes the complete verification traceability graph."""

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

        # Requirements
        for r in requirements:
            r_id = f"REQ:{r.identifier}"
            nodes.append(TraceabilityNode(
                id=r_id,
                type="requirement",
                label=f"{r.identifier}: {r.title}",
                metadata={"req_type": r.req_type.value if hasattr(r.req_type, "value") else str(r.req_type)}
            ))

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
        )

