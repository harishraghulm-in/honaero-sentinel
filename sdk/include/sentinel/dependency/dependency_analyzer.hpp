#pragma once

#include <string>
#include <vector>
#include <memory>
#include "sentinel/model/domain_models.hpp"

namespace sentinel {

class DependencyAnalyzer {
public:
    static DependencyGraph buildDependencyGraph(
        const FunctionInfo& targetFunction,
        const std::vector<DependencyInfo>& detectedCalls,
        const std::vector<StubConfiguration>& configuredStubs
    );
};

} // namespace sentinel
