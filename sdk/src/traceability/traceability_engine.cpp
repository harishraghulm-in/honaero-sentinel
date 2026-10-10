#include "sentinel/traceability/traceability_engine.hpp"

namespace sentinel {

TraceabilityGraph TraceabilityEngine::buildGraph(
    const std::string& projectId,
    const std::vector<Requirement>& requirements,
    const std::vector<FunctionInfo>& functions,
    const std::vector<TestVector>& testVectors,
    const std::string& targetFunctionId,
    const std::string& primaryRequirementId)
{
    TraceabilityGraph graph;
    graph.project_id = projectId;
    graph.requirements = requirements;
    graph.functions = functions;

    std::string targetFn = targetFunctionId;
    if (targetFn.empty() && !functions.empty()) {
        targetFn = functions[0].id;
    }

    std::string primaryReq = primaryRequirementId;
    if (primaryReq.empty() && !requirements.empty()) {
        primaryReq = requirements[0].identifier;
    }

    // 1. Link Requirement -> Function (IMPLEMENTS)
    if (!primaryReq.empty() && !targetFn.empty()) {
        TraceabilityLink link;
        link.source_id = primaryReq;
        link.source_type = "Requirement";
        link.target_id = targetFn;
        link.target_type = "Function";
        link.relationship = "IMPLEMENTED_BY";
        graph.links.push_back(link);
    }

    // 2. Create TestCase and Link Function -> TestCase (VERIFIED_BY)
    TestCaseTrace tcTrace;
    tcTrace.id = "TC-001";
    tcTrace.name = "Safety Critical Test Suite";
    tcTrace.target_function_id = targetFn;
    tcTrace.requirement_id = primaryReq;
    tcTrace.vector_count = static_cast<int>(testVectors.size());
    graph.test_cases.push_back(tcTrace);

    if (!targetFn.empty()) {
        TraceabilityLink link;
        link.source_id = targetFn;
        link.source_type = "Function";
        link.target_id = tcTrace.id;
        link.target_type = "TestCase";
        link.relationship = "VERIFIED_BY";
        graph.links.push_back(link);
    }

    // 3. Link Requirement -> TestCase (VALIDATED_BY)
    if (!primaryReq.empty()) {
        TraceabilityLink link;
        link.source_id = primaryReq;
        link.source_type = "Requirement";
        link.target_id = tcTrace.id;
        link.target_type = "TestCase";
        link.relationship = "VALIDATED_BY";
        graph.links.push_back(link);
    }

    return graph;
}

void TraceabilityEngine::linkExecutionAndEvidence(
    TraceabilityGraph& graph,
    const std::string& executionId,
    const std::string& evidenceId)
{
    // TestCase -> Execution
    if (!graph.test_cases.empty()) {
        TraceabilityLink link1;
        link1.source_id = graph.test_cases[0].id;
        link1.source_type = "TestCase";
        link1.target_id = executionId;
        link1.target_type = "Execution";
        link1.relationship = "EXECUTED_IN";
        graph.links.push_back(link1);
    }

    // Execution -> Coverage
    TraceabilityLink link2;
    link2.source_id = executionId;
    link2.source_type = "Execution";
    link2.target_id = "cov_" + executionId;
    link2.target_type = "Coverage";
    link2.relationship = "MEASURED_COVERAGE";
    graph.links.push_back(link2);

    // Execution -> MC/DC
    TraceabilityLink link3;
    link3.source_id = executionId;
    link3.source_type = "Execution";
    link3.target_id = "mcdc_" + executionId;
    link3.target_type = "MCDC";
    link3.relationship = "EVALUATED_MCDC";
    graph.links.push_back(link3);

    // Execution -> Evidence
    TraceabilityLink link4;
    link4.source_id = executionId;
    link4.source_type = "Execution";
    link4.target_id = evidenceId;
    link4.target_type = "Evidence";
    link4.relationship = "PRODUCED_EVIDENCE";
    graph.links.push_back(link4);
}

} // namespace sentinel
