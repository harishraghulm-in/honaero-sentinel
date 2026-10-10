import pytest
from apps.api.app.application.services.mcdc_analyzer import MCDCAnalyzerService
from apps.api.app.domain.interfaces.source_parser import (
    NormalizedDecision,
    NormalizedCondition,
)
from apps.api.app.domain.enums import MCDCConditionStatus


def test_mcdc_incomplete_and_gap_recommendation():
    analyzer = MCDCAnalyzerService()
    decision = NormalizedDecision(
        id="D1",
        expression="pressure > 900 and altitude < 10000",
        conditions=[
            NormalizedCondition(id="C1", expression="pressure > 900", variable_references=["pressure"]),
            NormalizedCondition(id="C2", expression="altitude < 10000", variable_references=["altitude"]),
        ],
    )

    # Vector 1: C1=True, C2=True -> Decision=True
    # Vector 2: C1=False, C2=True -> Decision=False
    # Here C1 independence is proven via pair (1, 2).
    # But C2 is NOT proven because there's no pair where C1=True and C2 flips to False.
    vectors = [
        {"pressure": 950, "altitude": 8000},
        {"pressure": 850, "altitude": 8000},
    ]

    report = analyzer.analyze([decision], vectors)

    assert report.total_conditions == 2
    assert report.proven_conditions == 1
    assert report.coverage_percentage == 50.0

    dec_rep = report.decisions[0]
    assert dec_rep.conditions[0].id == "C1"
    assert dec_rep.conditions[0].independence_proven is True
    assert dec_rep.conditions[0].independence_pair == (1, 2)

    assert dec_rep.conditions[1].id == "C2"
    assert dec_rep.conditions[1].independence_proven is False
    assert dec_rep.conditions[1].status == MCDCConditionStatus.NOT_PROVEN

    # Gap Advisor verification
    assert len(report.gap_recommendations) == 1
    rec = report.gap_recommendations[0]
    assert rec.condition_id == "C2"
    assert "candidate" in rec.disclaimer.lower()
    assert rec.recommended_truth_assignment["C1"] is True
    assert rec.recommended_truth_assignment["C2"] is False


def test_mcdc_full_coverage():
    analyzer = MCDCAnalyzerService()
    decision = NormalizedDecision(
        id="D1",
        expression="pressure > 900 and altitude < 10000",
        conditions=[
            NormalizedCondition(id="C1", expression="pressure > 900", variable_references=["pressure"]),
            NormalizedCondition(id="C2", expression="altitude < 10000", variable_references=["altitude"]),
        ],
    )

    # 3 vectors for N=2 conditions (N+1 rule for MC/DC):
    # Vector 1: C1=T, C2=T -> D=T
    # Vector 2: C1=F, C2=T -> D=F  (Pair 1,2 proves C1)
    # Vector 3: C1=T, C2=F -> D=F  (Pair 1,3 proves C2)
    vectors = [
        {"pressure": 950, "altitude": 8000},
        {"pressure": 850, "altitude": 8000},
        {"pressure": 950, "altitude": 12000},
    ]

    report = analyzer.analyze([decision], vectors)

    assert report.total_conditions == 2
    assert report.proven_conditions == 2
    assert report.coverage_percentage == 100.0
    assert len(report.gap_recommendations) == 0

    dec_rep = report.decisions[0]
    assert dec_rep.conditions[0].independence_proven is True
    assert dec_rep.conditions[1].independence_proven is True

