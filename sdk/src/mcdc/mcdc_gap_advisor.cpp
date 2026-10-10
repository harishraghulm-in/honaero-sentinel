#include "sentinel/mcdc/mcdc_gap_advisor.hpp"
#include "sentinel/mcdc/mcdc_evaluator.hpp"
#include <cmath>

namespace sentinel {

nlohmann::json MCDCGapAdvisor::deriveDeterministicValue(
    const ConditionInfo& condition,
    bool desiredEvaluation)
{
    double threshold = 0.0;
    bool hasThreshold = false;
    try {
        if (!condition.right_operand.empty()) {
            threshold = std::stod(condition.right_operand);
            hasThreshold = true;
        }
    } catch (...) {
        hasThreshold = false;
    }

    const std::string& op = condition.relational_operator;

    if (hasThreshold) {
        if (op == ">") {
            // e.g. pressure > 900: True -> 950, False -> 850
            double delta = (threshold >= 1000.0) ? 1000.0 : (threshold > 10.0 ? 50.0 : 1.0);
            return desiredEvaluation ? (threshold + delta) : (threshold - delta);
        } else if (op == "<") {
            // e.g. altitude < 10000: True -> 5000 or 8000, False -> 12000
            double delta = (threshold >= 1000.0) ? 2000.0 : (threshold > 10.0 ? 50.0 : 1.0);
            return desiredEvaluation ? (threshold - delta) : (threshold + delta);
        } else if (op == ">=") {
            return desiredEvaluation ? threshold : (threshold - 1.0);
        } else if (op == "<=") {
            return desiredEvaluation ? threshold : (threshold + 1.0);
        } else if (op == "==") {
            return desiredEvaluation ? threshold : (threshold + 1.0);
        } else if (op == "!=") {
            return desiredEvaluation ? (threshold + 1.0) : threshold;
        }
    }

    // Default boolean
    return desiredEvaluation ? 1 : 0;
}

std::vector<CandidateVectorRecommendation> MCDCGapAdvisor::adviseGaps(
    const DecisionInfo& decision,
    const std::vector<TestVector>& existingVectors,
    const std::vector<StubConfiguration>& stubs)
{
    std::vector<CandidateVectorRecommendation> recommendations;

    auto tree = ExpressionTreeBuilder::buildFromDecision(decision);
    auto evals = MCDCEvaluator::evaluateDecisionVectors(decision, tree, existingVectors, stubs);

    for (const auto& cond : decision.conditions) {
        auto pairOpt = MCDCEvaluator::findIndependencePair(cond.id, evals);
        if (!pairOpt.has_value()) {
            // Condition has an MC/DC gap
            CandidateVectorRecommendation rec;
            rec.condition_id = cond.id;
            rec.condition_expression = cond.expression;
            rec.label = "CANDIDATE VECTOR";

            // Find if there is an existing vector where this condition is TRUE or FALSE
            bool foundTrueVector = false;
            int existingTrueIndex = -1;
            bool foundFalseVector = false;
            int existingFalseIndex = -1;

            for (const auto& ev : evals) {
                auto it = ev.condition_values.find(cond.id);
                if (it != ev.condition_values.end()) {
                    if (it->second == true && !foundTrueVector) {
                        foundTrueVector = true;
                        existingTrueIndex = ev.vector_index;
                    } else if (it->second == false && !foundFalseVector) {
                        foundFalseVector = true;
                        existingFalseIndex = ev.vector_index;
                    }
                }
            }

            bool targetConditionValue = true;
            if (foundTrueVector && !foundFalseVector) {
                targetConditionValue = false;
                rec.reason = "Hold other conditions TRUE while changing " + cond.id + " (" + cond.expression + ") TRUE -> FALSE to demonstrate independent negative outcome.";
            } else if (foundFalseVector && !foundTrueVector) {
                targetConditionValue = true;
                rec.reason = "Hold other conditions TRUE while satisfying " + cond.id + " (" + cond.expression + ") to demonstrate independent positive outcome.";
            } else {
                targetConditionValue = false;
                rec.reason = "Construct independence pair for " + cond.id + ": toggle " + cond.expression + " while holding other decision conditions constant.";
            }

            // Derive deterministic candidate inputs
            for (const auto& otherCond : decision.conditions) {
                bool desiredVal = (otherCond.id == cond.id) ? targetConditionValue : true;
                nlohmann::json inputVal = deriveDeterministicValue(otherCond, desiredVal);
                if (!otherCond.variable_references.empty()) {
                    rec.recommended_inputs[otherCond.variable_references[0]] = inputVal;
                }
            }

            rec.expected_outcome = targetConditionValue ? 1 : 0;
            recommendations.push_back(rec);
        }
    }

    return recommendations;
}

} // namespace sentinel
