from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from apps.api.app.domain.models import (
    Project,
    TestCase,
    FunctionModel,
    Requirement,
    Execution,
    CoverageResult,
    PrioritizationOverride,
)
from apps.api.app.domain.enums import ExecutionStatus
from apps.api.app.schemas.sentinel_api import (
    PrioritizedItemDTO,
    PrioritizationFactorDTO,
    PrioritizationResponse,
    PrioritizationOverrideResponse,
)


class PrioritizationService:
    """
    Deterministic DO-178C test prioritization engine.
    Computes explainable ranking based on safety criticality, coverage gaps,
    failure history, static cyclomatic complexity, and external dependencies.
    """

    def compute_project_priorities(self, project_id: str, db: Session) -> PrioritizationResponse:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # 1. Fetch test cases with relations
        test_cases = db.query(TestCase).filter_by(project_id=project_id).all()
        overrides = {
            o.target_id: o
            for o in db.query(PrioritizationOverride).filter_by(project_id=project_id).all()
        }

        ranked_items: List[PrioritizedItemDTO] = []

        if test_cases:
            for tc in test_cases:
                item = self._score_test_case(tc, overrides.get(tc.id), db)
                ranked_items.append(item)
        else:
            # If no test cases authored yet, rank target functions
            functions = db.query(FunctionModel).filter_by(project_id=project_id).all()
            for fn in functions:
                item = self._score_function(fn, overrides.get(fn.id), db)
                ranked_items.append(item)

        # Sort by priority score descending
        ranked_items.sort(key=lambda x: x.priority_score, reverse=True)

        # Assign integer ranks
        for idx, item in enumerate(ranked_items, start=1):
            item.priority_rank = idx

        return PrioritizationResponse(
            project_id=project_id,
            generated_at=datetime.now(timezone.utc),
            total_ranked_items=len(ranked_items),
            priorities=ranked_items,
        )

    def set_override(
        self,
        project_id: str,
        target_id: str,
        manual_priority: str,
        manual_score: Optional[float],
        override_reason: str,
        db: Session,
    ) -> PrioritizationOverrideResponse:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        override = db.query(PrioritizationOverride).filter_by(
            project_id=project_id, target_id=target_id
        ).first()

        if not override:
            override = PrioritizationOverride(
                project_id=project_id,
                target_id=target_id,
                manual_priority=manual_priority.upper(),
                manual_score=manual_score,
                override_reason=override_reason,
            )
            db.add(override)
        else:
            override.manual_priority = manual_priority.upper()
            override.manual_score = manual_score
            override.override_reason = override_reason

        db.commit()
        db.refresh(override)

        return PrioritizationOverrideResponse(
            id=override.id,
            project_id=override.project_id,
            target_id=override.target_id,
            manual_priority=override.manual_priority,
            manual_score=override.manual_score,
            override_reason=override.override_reason,
            created_at=override.created_at,
            updated_at=override.updated_at,
        )

    def delete_override(self, project_id: str, target_id: str, db: Session) -> bool:
        override = db.query(PrioritizationOverride).filter_by(
            project_id=project_id, target_id=target_id
        ).first()
        if override:
            db.delete(override)
            db.commit()
            return True
        return False

    def _score_test_case(
        self,
        tc: TestCase,
        override: Optional[PrioritizationOverride],
        db: Session,
    ) -> PrioritizedItemDTO:
        factors: List[PrioritizationFactorDTO] = []
        raw_score = 0.0

        # Factor 1: Safety Criticality from Linked Requirement
        req = tc.requirement
        crit_label = "UNSPECIFIED"
        crit_score = 7.0
        crit_desc = "No linked requirement"

        if req:
            req_type_attr = getattr(req, "req_type", None)
            req_type_str = (req_type_attr.value if hasattr(req_type_attr, "value") else str(req_type_attr or "")).upper()
            desc_upper = (req.description or "").upper()
            if "LEVEL A" in desc_upper or "CATAS" in desc_upper or req_type_str in ("HLR", "HIGH_LEVEL"):
                crit_label = "LEVEL_A"
                crit_score = 35.0
                crit_desc = f"DO-178C Level A safety requirement ({req.identifier})"
            elif "LEVEL B" in desc_upper or "HAZARD" in desc_upper:
                crit_label = "LEVEL_B"
                crit_score = 28.0
                crit_desc = f"DO-178C Level B requirement ({req.identifier})"
            elif "LEVEL C" in desc_upper or "MAJOR" in desc_upper:
                crit_label = "LEVEL_C"
                crit_score = 21.0
                crit_desc = f"DO-178C Level C requirement ({req.identifier})"
            else:
                crit_label = "LEVEL_D"
                crit_score = 14.0
                crit_desc = f"DO-178C Low-Level requirement ({req.identifier})"
        factors.append(PrioritizationFactorDTO(
            factor_name="Safety Criticality",
            weight=0.35,
            contribution=crit_score,
            description=crit_desc,
        ))
        raw_score += crit_score

        # Factor 2: Execution & Regression Failure History
        last_exec = (
            db.query(Execution)
            .filter_by(test_case_id=tc.id)
            .order_by(Execution.created_at.desc())
            .first()
        )
        last_verdict = None
        if last_exec:
            last_verdict = last_exec.status.value if hasattr(last_exec.status, "value") else str(last_exec.status)
            if last_verdict in ("FAIL", "FAILED", "ERROR"):
                fail_score = 20.0
                fail_desc = f"Previous regression run failed ({last_verdict})"
            elif last_verdict == "TIMEOUT":
                fail_score = 16.0
                fail_desc = "Previous run timed out"
            else:
                fail_score = 2.0
                fail_desc = f"Previous run passed ({last_verdict})"
        else:
            fail_score = 12.0
            fail_desc = "No previous execution history (new test case)"
        factors.append(PrioritizationFactorDTO(
            factor_name="Failure & Regression Risk",
            weight=0.20,
            contribution=fail_score,
            description=fail_desc,
        ))
        raw_score += fail_score

        # Factor 3: Missing Coverage / Verification Gap
        cov_score = 0.0
        cov_desc = "Untested execution coverage"
        if last_exec and last_exec.coverage:
            cov = last_exec.coverage
            branch_cov = cov.branch_coverage_pct or 0.0
            stmt_cov = cov.statement_coverage_pct or 0.0
            avg_cov = (branch_cov + stmt_cov) / 2.0
            cov_score = round(25.0 * (1.0 - (avg_cov / 100.0)), 2)
            cov_desc = f"Measured coverage: statement={stmt_cov}%, branch={branch_cov}%"
        else:
            cov_score = 25.0
            cov_desc = "Zero coverage recorded to date"
        factors.append(PrioritizationFactorDTO(
            factor_name="Missing Coverage Gap",
            weight=0.25,
            contribution=cov_score,
            description=cov_desc,
        ))
        raw_score += cov_score

        # Factor 4: Static Decision Complexity of Target Function
        fn = tc.target_function
        fn_name = fn.name if fn else "unknown"
        source_file = fn.source_file.filename if fn and fn.source_file else None
        decisions_count = len(fn.decisions or []) if fn else 0

        if decisions_count >= 3:
            comp_score = 10.0
            comp_desc = f"High decision branching ({decisions_count} decisions)"
        elif decisions_count == 2:
            comp_score = 7.0
            comp_desc = f"Moderate decision branching ({decisions_count} decisions)"
        elif decisions_count == 1:
            comp_score = 4.0
            comp_desc = "Single decision branch"
        else:
            comp_score = 2.0
            comp_desc = "Linear execution path"
        factors.append(PrioritizationFactorDTO(
            factor_name="Static Complexity",
            weight=0.10,
            contribution=comp_score,
            description=comp_desc,
        ))
        raw_score += comp_score

        # Factor 5: Dependency Fan-In / Coupling
        dep_count = len(fn.dependencies) if fn and hasattr(fn, "dependencies") and fn.dependencies else 0
        if dep_count >= 2:
            dep_score = 10.0
            dep_desc = f"Coupled with {dep_count} external dependencies"
        elif dep_count == 1:
            dep_score = 5.0
            dep_desc = "Coupled with 1 external dependency"
        else:
            dep_score = 2.0
            dep_desc = "Independent function"
        factors.append(PrioritizationFactorDTO(
            factor_name="Coupling & Dependencies",
            weight=0.10,
            contribution=dep_score,
            description=dep_desc,
        ))
        raw_score += dep_score

        # Check override
        final_score = min(round(raw_score, 1), 100.0)
        is_overridden = False
        override_reason = None
        if override:
            is_overridden = True
            override_reason = override.override_reason
            if override.manual_score is not None:
                final_score = float(override.manual_score)
            elif override.manual_priority == "HIGH":
                final_score = 95.0
            elif override.manual_priority == "MEDIUM":
                final_score = 50.0
            elif override.manual_priority == "LOW":
                final_score = 15.0

        rationale = (
            f"Prioritized at {final_score}/100. {crit_desc}; {fail_desc}; "
            f"{cov_desc}; {comp_desc}."
        )

        return PrioritizedItemDTO(
            item_id=tc.id,
            target_type="test_case",
            name=tc.name,
            target_function_name=fn_name,
            source_file=source_file,
            safety_criticality=crit_label,
            priority_rank=0,  # assigned after sorting
            priority_score=final_score,
            rationale=rationale,
            factors=factors,
            is_overridden=is_overridden,
            override_reason=override_reason,
            last_verdict=last_verdict,
            uncovered_decisions_count=decisions_count,
        )

    def _score_function(
        self,
        fn: FunctionModel,
        override: Optional[PrioritizationOverride],
        db: Session,
    ) -> PrioritizedItemDTO:
        decisions_count = len(fn.decisions or [])
        comp_score = 10.0 if decisions_count >= 3 else (7.0 if decisions_count >= 1 else 3.0)
        dep_count = len(fn.dependencies) if hasattr(fn, "dependencies") and fn.dependencies else 0
        dep_score = 10.0 if dep_count >= 2 else (5.0 if dep_count == 1 else 2.0)
        crit_score = 30.0 if fn.is_target_under_test else 15.0
        cov_score = 25.0

        raw_score = crit_score + comp_score + dep_score + cov_score + 10.0
        final_score = min(round(raw_score, 1), 100.0)
        is_overridden = False
        override_reason = None
        if override:
            is_overridden = True
            override_reason = override.override_reason
            if override.manual_score is not None:
                final_score = float(override.manual_score)
            elif override.manual_priority == "HIGH":
                final_score = 95.0
            elif override.manual_priority == "MEDIUM":
                final_score = 50.0
            else:
                final_score = 15.0

        factors = [
            PrioritizationFactorDTO(
                factor_name="Target Status",
                weight=0.35,
                contribution=crit_score,
                description="Target function under test" if fn.is_target_under_test else "Secondary module function",
            ),
            PrioritizationFactorDTO(
                factor_name="Missing Coverage Gap",
                weight=0.25,
                contribution=cov_score,
                description="Pending test case authoring and execution",
            ),
            PrioritizationFactorDTO(
                factor_name="Static Complexity",
                weight=0.20,
                contribution=comp_score,
                description=f"{decisions_count} decision branches",
            ),
            PrioritizationFactorDTO(
                factor_name="Coupling",
                weight=0.20,
                contribution=dep_score,
                description=f"{dep_count} dependencies",
            ),
        ]

        return PrioritizedItemDTO(
            item_id=fn.id,
            target_type="function",
            name=fn.name,
            target_function_name=fn.name,
            source_file=fn.source_file.filename if fn.source_file else None,
            safety_criticality="LEVEL_A" if fn.is_target_under_test else "LEVEL_C",
            priority_rank=0,
            priority_score=final_score,
            rationale=f"Function candidate prioritized at {final_score}/100. {decisions_count} decisions, {dep_count} dependencies.",
            factors=factors,
            is_overridden=is_overridden,
            override_reason=override_reason,
            last_verdict=None,
            uncovered_decisions_count=decisions_count,
        )
