#pragma once

#include <string>
#include <vector>
#include <map>
#include "sentinel/model/domain_models.hpp"
#include "sentinel/mcdc/mcdc_expression.hpp"

namespace sentinel {

class MCDCEvaluator {
public:
    static MCDCResult evaluate(
        const std::vector<DecisionInfo>& decisions,
        const std::vector<TestVector>& testVectors,
        const std::vector<StubConfiguration>& stubs = {}
    );

    static bool evaluateConditionOnVector(
        const ConditionInfo& condition,
        const TestVector& vector,
        const std::vector<StubConfiguration>& stubs = {}
    );

    static std::vector<TestVectorEvaluation> evaluateDecisionVectors(
        const DecisionInfo& decision,
        const std::shared_ptr<IExpressionNode>& tree,
        const std::vector<TestVector>& testVectors,
        const std::vector<StubConfiguration>& stubs = {}
    );

    static std::optional<MCDCIndependencePair> findIndependencePair(
        const std::string& conditionId,
        const std::vector<TestVectorEvaluation>& evaluations
    );
};

} // namespace sentinel
