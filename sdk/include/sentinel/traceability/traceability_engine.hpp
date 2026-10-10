#pragma once

#include <string>
#include <vector>
#include "sentinel/model/domain_models.hpp"

namespace sentinel {

class TraceabilityEngine {
public:
    static TraceabilityGraph buildGraph(
        const std::string& projectId,
        const std::vector<Requirement>& requirements,
        const std::vector<FunctionInfo>& functions,
        const std::vector<TestVector>& testVectors,
        const std::string& targetFunctionId = "",
        const std::string& primaryRequirementId = ""
    );

    static void linkExecutionAndEvidence(
        TraceabilityGraph& graph,
        const std::string& executionId,
        const std::string& evidenceId
    );
};

} // namespace sentinel
