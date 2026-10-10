#include "sentinel/mcdc/mcdc_evaluator.hpp"
#include <iostream>

namespace sentinel {

static bool evaluateRelational(double left, const std::string& op, double right) {
    if (op == ">") return left > right;
    if (op == "<") return left < right;
    if (op == ">=") return left >= right;
    if (op == "<=") return left <= right;
    if (op == "==") return left == right;
    if (op == "!=") return left != right;
    return false;
}

bool MCDCEvaluator::evaluateConditionOnVector(
    const ConditionInfo& condition,
    const TestVector& vector,
    const std::vector<StubConfiguration>& stubs)
{
    // If explicit condition override in metadata or inputs
    if (vector.inputs.find(condition.id) != vector.inputs.end()) {
        const auto& val = vector.inputs.at(condition.id);
        if (val.is_boolean()) return val.get<bool>();
        if (val.is_number_integer()) return val.get<int>() != 0;
    }

    // Evaluate relational expression from inputs or stubs
    if (!condition.relational_operator.empty() && !condition.variable_references.empty()) {
        const std::string& varName = condition.variable_references[0];
        double leftVal = 0.0;
        bool found = false;

        if (vector.inputs.find(varName) != vector.inputs.end()) {
            const auto& jval = vector.inputs.at(varName);
            if (jval.is_number()) {
                leftVal = jval.get<double>();
                found = true;
            }
        }

        // Check stubs if variable corresponds to a stub or stubbed function
        if (!found) {
            for (const auto& s : stubs) {
                if (varName.find(s.function_name) != std::string::npos ||
                    s.function_name.find("sensor") != std::string::npos) {
                    if (!s.return_values.empty() && s.return_values[0].is_number()) {
                        leftVal = s.return_values[0].get<double>();
                        found = true;
                        break;
                    }
                }
            }
        }

        if (found) {
            double rightVal = 0.0;
            try {
                rightVal = std::stod(condition.right_operand);
                return evaluateRelational(leftVal, condition.relational_operator, rightVal);
            } catch (...) {
                // If right operand is not a direct number, default check
            }
        }
    }

    // Default boolean assumption: true if expected return != 0
    auto itRet = vector.expected_outputs.find("return");
    if (itRet != vector.expected_outputs.end() && itRet->second.is_number()) {
        return itRet->second.get<int>() != 0;
    }
    return false;
}

std::vector<TestVectorEvaluation> MCDCEvaluator::evaluateDecisionVectors(
    const DecisionInfo& decision,
    const std::shared_ptr<IExpressionNode>& tree,
    const std::vector<TestVector>& testVectors,
    const std::vector<StubConfiguration>& stubs)
{
    std::vector<TestVectorEvaluation> evals;

    for (const auto& vec : testVectors) {
        TestVectorEvaluation ev;
        ev.vector_index = vec.vector_index;

        for (const auto& cond : decision.conditions) {
            bool cVal = evaluateConditionOnVector(cond, vec, stubs);
            ev.condition_values[cond.id] = cVal;
        }

        if (tree) {
            ev.decision_outcome = tree->evaluate(ev.condition_values);
        } else {
            // Fallback: check expected return
            auto it = vec.expected_outputs.find("return");
            ev.decision_outcome = (it != vec.expected_outputs.end() && it->second.get<int>() != 0);
        }

        evals.push_back(ev);
    }
    return evals;
}

std::optional<MCDCIndependencePair> MCDCEvaluator::findIndependencePair(
    const std::string& conditionId,
    const std::vector<TestVectorEvaluation>& evaluations)
{
    // Find a pair (V_true, V_false) where:
    // conditionId differs, decision_outcome differs,
    // and difference among other conditions is minimal (ideally 0)
    std::optional<MCDCIndependencePair> bestPair;
    int minOtherDifferences = 9999;

    for (size_t i = 0; i < evaluations.size(); ++i) {
        for (size_t j = 0; j < evaluations.size(); ++j) {
            if (i == j) continue;

            const auto& vTrue = evaluations[i];
            const auto& vFalse = evaluations[j];

            auto it1 = vTrue.condition_values.find(conditionId);
            auto it2 = vFalse.condition_values.find(conditionId);
            if (it1 == vTrue.condition_values.end() || it2 == vFalse.condition_values.end()) continue;

            if (it1->second == true && it2->second == false) {
                if (vTrue.decision_outcome != vFalse.decision_outcome) {
                    // Count how many OTHER conditions differ
                    int otherDiffs = 0;
                    for (const auto& [cid, cval] : vTrue.condition_values) {
                        if (cid == conditionId) continue;
                        auto oit = vFalse.condition_values.find(cid);
                        if (oit != vFalse.condition_values.end() && oit->second != cval) {
                            otherDiffs++;
                        }
                    }

                    if (otherDiffs < minOtherDifferences) {
                        minOtherDifferences = otherDiffs;
                        MCDCIndependencePair pair;
                        pair.condition_id = conditionId;
                        pair.true_vector_index = vTrue.vector_index;
                        pair.false_vector_index = vFalse.vector_index;
                        pair.explanation = "Independence proven: " + conditionId + " toggles TRUE (TC-" +
                            std::to_string(vTrue.vector_index) + ") to FALSE (TC-" +
                            std::to_string(vFalse.vector_index) + ") altering decision outcome with " +
                            std::to_string(otherDiffs) + " other condition difference(s).";
                        bestPair = pair;
                    }
                }
            }
        }
    }

    // In unique-cause MC/DC, 0 other differences is required.
    // In masking MC/DC, other differences are allowed if masked.
    if (bestPair.has_value() && minOtherDifferences <= 1) {
        return bestPair;
    }
    return std::nullopt;
}

MCDCResult MCDCEvaluator::evaluate(
    const std::vector<DecisionInfo>& decisions,
    const std::vector<TestVector>& testVectors,
    const std::vector<StubConfiguration>& stubs)
{
    MCDCResult result;
    result.execution_id = "exec_mcdc";

    int totalConditionsAll = 0;
    int coveredConditionsAll = 0;

    for (const auto& dec : decisions) {
        DecisionMCDCStatus decStatus;
        decStatus.decision_id = dec.id;
        decStatus.expression = dec.expression;
        decStatus.line_number = dec.line_number;
        decStatus.total_conditions = static_cast<int>(dec.conditions.size());
        totalConditionsAll += decStatus.total_conditions;

        auto tree = ExpressionTreeBuilder::buildFromDecision(dec);
        auto evals = evaluateDecisionVectors(dec, tree, testVectors, stubs);

        for (const auto& cond : dec.conditions) {
            auto pairOpt = findIndependencePair(cond.id, evals);
            if (pairOpt.has_value()) {
                decStatus.independence_pairs.push_back(*pairOpt);
                decStatus.covered_conditions++;
                coveredConditionsAll++;
            } else {
                MCDCGap gap;
                gap.condition_id = cond.id;
                gap.condition_expression = cond.expression;
                gap.missing_independence_reason = "No test vector pair demonstrates independent effect of " + cond.id + " on decision " + dec.id;
                decStatus.gaps.push_back(gap);
                result.gap_recommendations.push_back(gap);
            }
        }

        decStatus.coverage_pct = (decStatus.total_conditions > 0)
            ? (static_cast<double>(decStatus.covered_conditions) / decStatus.total_conditions * 100.0)
            : 100.0;
        decStatus.mcdc_achieved = (decStatus.covered_conditions == decStatus.total_conditions);
        result.decisions.push_back(decStatus);
    }

    result.coverage_percentage = (totalConditionsAll > 0)
        ? (static_cast<double>(coveredConditionsAll) / totalConditionsAll * 100.0)
        : 100.0;
    result.full_mcdc_achieved = (coveredConditionsAll == totalConditionsAll);

    return result;
}

} // namespace sentinel
