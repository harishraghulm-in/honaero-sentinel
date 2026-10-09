#pragma once

#include <string>
#include <vector>
#include "sentinel/model/domain_models.hpp"

namespace sentinel {

struct CandidateVectorRecommendation {
    std::string condition_id;
    std::string condition_expression;
    std::string label{"CANDIDATE VECTOR"}; // NEVER "CERTIFIED VECTOR"
    std::string reason;
    std::map<std::string, nlohmann::json> recommended_inputs;
    nlohmann::json expected_outcome;

    nlohmann::json toJson() const {
        return {
            {"condition_id", condition_id},
            {"condition_expression", condition_expression},
            {"label", label},
            {"reason", reason},
            {"recommended_inputs", recommended_inputs},
            {"expected_outcome", expected_outcome}
        };
    }
};

class MCDCGapAdvisor {
public:
    static std::vector<CandidateVectorRecommendation> adviseGaps(
        const DecisionInfo& decision,
        const std::vector<TestVector>& existingVectors,
        const std::vector<StubConfiguration>& stubs = {}
    );

    static nlohmann::json deriveDeterministicValue(
        const ConditionInfo& condition,
        bool desiredEvaluation
    );
};

} // namespace sentinel
