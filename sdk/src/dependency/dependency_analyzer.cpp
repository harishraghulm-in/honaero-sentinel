#include "sentinel/dependency/dependency_analyzer.hpp"
#include <map>

namespace sentinel {

DependencyGraph DependencyAnalyzer::buildDependencyGraph(
    const FunctionInfo& targetFunction,
    const std::vector<DependencyInfo>& detectedCalls,
    const std::vector<StubConfiguration>& configuredStubs)
{
    DependencyGraph graph;
    graph.root_function = targetFunction.name;

    std::map<std::string, StubConfiguration> stubMap;
    for (const auto& s : configuredStubs) {
        stubMap[s.function_name] = s;
    }

    // Merge external calls from function definition and detected calls
    std::map<std::string, DependencyInfo> uniqueDeps;
    for (const auto& call : targetFunction.external_calls) {
        uniqueDeps[call.name] = call;
    }
    for (const auto& call : detectedCalls) {
        if (uniqueDeps.find(call.name) == uniqueDeps.end()) {
            uniqueDeps[call.name] = call;
        } else {
            // Merge parameters or return type if available
            if (uniqueDeps[call.name].return_type == "void" && call.return_type != "void") {
                uniqueDeps[call.name].return_type = call.return_type;
            }
            if (uniqueDeps[call.name].parameters.empty() && !call.parameters.empty()) {
                uniqueDeps[call.name].parameters = call.parameters;
            }
        }
    }

    for (auto& [name, dep] : uniqueDeps) {
        auto it = stubMap.find(name);
        if (it != stubMap.end()) {
            dep.classification = dependencyClassificationFromString(it->second.mode);
        } else {
            dep.classification = DependencyClassification::STUB;
        }
        graph.dependencies.push_back(dep);
    }

    return graph;
}

} // namespace sentinel
