#include <iostream>
#include <fstream>
#include <cassert>
#include <string>
#include <vector>
#include <filesystem>
#include "sentinel/analysis/ast_analyzer.hpp"
#include "sentinel/dependency/dependency_analyzer.hpp"
#include "sentinel/harness/harness_generator.hpp"
#include "sentinel/comparator/scalar_comparator.hpp"
#include "sentinel/coverage/gcov_provider.hpp"
#include "sentinel/mcdc/mcdc_expression.hpp"
#include "sentinel/mcdc/mcdc_evaluator.hpp"
#include "sentinel/mcdc/mcdc_gap_advisor.hpp"
#include "sentinel/traceability/traceability_engine.hpp"
#include "sentinel/common/sha256.hpp"
#include "sentinel/evidence/evidence_record.hpp"
#include "sentinel/capsule/verification_capsule.hpp"

using namespace sentinel;
namespace fs = std::filesystem;

#define ASSERT_TRUE(cond) do { \
    if (!(cond)) { \
        std::cerr << "Assertion FAILED: " #cond " at line " << __LINE__ << std::endl; \
        std::exit(1); \
    } \
} while(0)

#define ASSERT_FALSE(cond) ASSERT_TRUE(!(cond))

#define ASSERT_EQ(a, b) do { \
    if (!((a) == (b))) { \
        std::cerr << "Assertion FAILED: " #a " == " #b << " (" << (a) << " vs " << (b) << ") at line " << __LINE__ << std::endl; \
        std::exit(1); \
    } \
} while(0)

void test_ast_analysis() {
    std::cout << "[Test 1/10] Testing AST Function, Parameter, and Decision Extraction..." << std::endl;
    std::string source = 
        "int cabin_pressure_control(int pressure, int altitude) {\n"
        "    int sensor_val = sensor_read();\n"
        "    if (pressure > 900 && altitude < 10000 && sensor_val > 900) {\n"
        "        valve_actuate(100);\n"
        "        return 1;\n"
        "    }\n"
        "    valve_actuate(0);\n"
        "    return 0;\n"
        "}\n";

    ClangAstAnalyzer analyzer;
    auto res = analyzer.analyzeSource(source, "cabin_pressure.c");

    ASSERT_EQ(res.functions.size(), 1);
    const auto& fn = res.functions[0];
    ASSERT_EQ(fn.name, "cabin_pressure_control");
    ASSERT_EQ(fn.return_type, "int");
    ASSERT_EQ(fn.parameters.size(), 2);
    ASSERT_EQ(fn.parameters[0].name, "pressure");
    ASSERT_EQ(fn.parameters[0].type, "int");
    ASSERT_EQ(fn.parameters[1].name, "altitude");
    ASSERT_EQ(fn.parameters[1].type, "int");

    // Decision and Conditions
    ASSERT_EQ(fn.decisions.size(), 1);
    const auto& dec = fn.decisions[0];
    ASSERT_EQ(dec.id, "D1");
    ASSERT_EQ(dec.conditions.size(), 3);
    ASSERT_EQ(dec.conditions[0].id, "C1");
    ASSERT_EQ(dec.conditions[0].relational_operator, ">");
    ASSERT_EQ(dec.conditions[0].left_operand, "pressure");
    ASSERT_EQ(dec.conditions[0].right_operand, "900");

    ASSERT_EQ(dec.conditions[1].id, "C2");
    ASSERT_EQ(dec.conditions[1].relational_operator, "<");
    ASSERT_EQ(dec.conditions[1].left_operand, "altitude");
    ASSERT_EQ(dec.conditions[1].right_operand, "10000");

    // Dependency calls detected
    ASSERT_TRUE(!fn.external_calls.empty());
    bool foundSensorRead = false;
    for (const auto& c : fn.external_calls) {
        if (c.name == "sensor_read") foundSensorRead = true;
    }
    ASSERT_TRUE(foundSensorRead);

    std::cout << "  -> PASSED: Function, Parameters, Decision, and Dependencies correctly extracted." << std::endl;
}

void test_dependency_and_stubs() {
    std::cout << "[Test 2/10] Testing Dependency Graph and Stub Reconciliation..." << std::endl;
    FunctionInfo fn;
    fn.name = "cabin_pressure_control";

    DependencyInfo d1;
    d1.name = "sensor_read";
    d1.return_type = "int";
    fn.external_calls.push_back(d1);

    StubConfiguration s1;
    s1.function_name = "sensor_read";
    s1.mode = "STUB";
    s1.return_type = "int";
    s1.return_values = {950, 950, 950};

    auto graph = DependencyAnalyzer::buildDependencyGraph(fn, {d1}, {s1});
    ASSERT_EQ(graph.dependencies.size(), 1);
    ASSERT_EQ(graph.dependencies[0].name, "sensor_read");
    ASSERT_TRUE(graph.dependencies[0].classification == DependencyClassification::STUB);

    std::cout << "  -> PASSED: Dependency graph and stub configurations reconciled." << std::endl;
}

void test_harness_generation() {
    std::cout << "[Test 3/10] Testing Deterministic Test Harness Generation..." << std::endl;
    HarnessRequest req;
    req.project_id = "test_proj";
    req.target_source_file = "cabin_pressure.c";
    req.target_function.name = "cabin_pressure_control";
    req.target_function.return_type = "int";
    
    ParameterInfo p1; p1.name = "pressure"; p1.type = "int";
    ParameterInfo p2; p2.name = "altitude"; p2.type = "int";
    req.target_function.parameters = {p1, p2};

    StubConfiguration stub;
    stub.function_name = "sensor_read";
    stub.mode = "STUB";
    stub.return_type = "int";
    stub.return_values = {950, 950, 950};
    req.stubs.push_back(stub);

    TestVector v1;
    v1.vector_index = 1;
    v1.inputs["pressure"] = 950;
    v1.inputs["altitude"] = 8000;
    v1.expected_outputs["return"] = 1;

    TestVector v2;
    v2.vector_index = 2;
    v2.inputs["pressure"] = 850;
    v2.inputs["altitude"] = 8000;
    v2.expected_outputs["return"] = 0;

    req.test_vectors = {v1, v2};
    req.output_directory = "test_generated_harness";

    auto hResult = HarnessGenerator::generate(req);
    ASSERT_TRUE(hResult.success);
    ASSERT_TRUE(fs::exists(hResult.harness_source_file));
    ASSERT_TRUE(fs::exists(hResult.stubs_header_file));
    ASSERT_TRUE(fs::exists(hResult.stubs_source_file));
    ASSERT_TRUE(fs::exists(hResult.test_vectors_source_file));
    ASSERT_FALSE(hResult.generated_code_hash.empty());

    // Deterministic repeatability check
    auto hResult2 = HarnessGenerator::generate(req);
    ASSERT_EQ(hResult.generated_code_hash, hResult2.generated_code_hash);

    std::cout << "  -> PASSED: Test harness generated deterministically with SHA: " << hResult.generated_code_hash.substr(0, 8) << std::endl;
}

void test_comparator() {
    std::cout << "[Test 4/10] Testing Prototype Scalar & Structured Comparators..." << std::endl;
    ScalarComparator scalarComp(1e-4, 1e-4);

    // Float comparison
    auto r1 = scalarComp.compare(10.00001, 10.00002);
    ASSERT_TRUE(r1.passed);

    auto r2 = scalarComp.compare(10.0, 11.0);
    ASSERT_FALSE(r2.passed);

    // Integer comparison
    auto r3 = scalarComp.compare(1, 1);
    ASSERT_TRUE(r3.passed);
    auto r4 = scalarComp.compare(1, 0);
    ASSERT_FALSE(r4.passed);

    // Structured comparison
    StructuredComparator structComp;
    nlohmann::json objA = {{"return", 1}, {"pressure", 950}};
    nlohmann::json objB = {{"return", 1}, {"pressure", 950}};
    nlohmann::json objC = {{"return", 0}, {"pressure", 950}};

    ASSERT_TRUE(structComp.compare(objA, objB).passed);
    ASSERT_FALSE(structComp.compare(objA, objC).passed);

    std::cout << "  -> PASSED: Scalar and structured comparisons match specifications." << std::endl;
}

void test_mcdc_engine() {
    std::cout << "[Test 5/10] Testing MC/DC Engine & Independence Pair Detection..." << std::endl;
    DecisionInfo dec;
    dec.id = "D1";
    dec.expression = "pressure > 900 && altitude < 10000";

    ConditionInfo c1;
    c1.id = "C1";
    c1.expression = "pressure > 900";
    c1.relational_operator = ">";
    c1.variable_references = {"pressure"};
    c1.left_operand = "pressure";
    c1.right_operand = "900";

    ConditionInfo c2;
    c2.id = "C2";
    c2.expression = "altitude < 10000";
    c2.relational_operator = "<";
    c2.variable_references = {"altitude"};
    c2.left_operand = "altitude";
    c2.right_operand = "10000";

    dec.conditions = {c1, c2};

    // TC-001: C1=T, C2=T -> Decision=T
    TestVector tv1;
    tv1.vector_index = 1;
    tv1.inputs["pressure"] = 950;
    tv1.inputs["altitude"] = 5000;
    tv1.expected_outputs["return"] = 1;

    // TC-002: C1=F, C2=T -> Decision=F (Proves C1 independence with TC-001)
    TestVector tv2;
    tv2.vector_index = 2;
    tv2.inputs["pressure"] = 850;
    tv2.inputs["altitude"] = 5000;
    tv2.expected_outputs["return"] = 0;

    // TC-003: C1=T, C2=F -> Decision=F (Proves C2 independence with TC-001)
    TestVector tv3;
    tv3.vector_index = 3;
    tv3.inputs["pressure"] = 950;
    tv3.inputs["altitude"] = 12000;
    tv3.expected_outputs["return"] = 0;

    std::vector<TestVector> vectors = {tv1, tv2, tv3};

    auto mcdcRes = MCDCEvaluator::evaluate({dec}, vectors);
    ASSERT_TRUE(mcdcRes.full_mcdc_achieved);
    ASSERT_EQ(mcdcRes.coverage_percentage, 100.0);
    ASSERT_EQ(mcdcRes.decisions[0].independence_pairs.size(), 2);

    // C1 pair
    bool c1Found = false;
    for (const auto& p : mcdcRes.decisions[0].independence_pairs) {
        if (p.condition_id == "C1") {
            c1Found = true;
            ASSERT_EQ(p.true_vector_index, 1);
            ASSERT_EQ(p.false_vector_index, 2);
        }
    }
    ASSERT_TRUE(c1Found);

    std::cout << "  -> PASSED: Full MC/DC achieved with correct independence pairs." << std::endl;
}

void test_mcdc_gap_advisor() {
    std::cout << "[Test 6/10] Testing MC/DC Gap Advisor Candidate Vector Synthesis..." << std::endl;
    DecisionInfo dec;
    dec.id = "D1";
    dec.expression = "pressure > 900 && altitude < 10000";

    ConditionInfo c1;
    c1.id = "C1";
    c1.expression = "pressure > 900";
    c1.relational_operator = ">";
    c1.variable_references = {"pressure"};
    c1.right_operand = "900";

    ConditionInfo c2;
    c2.id = "C2";
    c2.expression = "altitude < 10000";
    c2.relational_operator = "<";
    c2.variable_references = {"altitude"};
    c2.right_operand = "10000";

    dec.conditions = {c1, c2};

    // Provide only TC-1 (T, T) and TC-2 (F, T) -> C2 is MISSING independence!
    TestVector tv1; tv1.vector_index = 1; tv1.inputs["pressure"] = 950; tv1.inputs["altitude"] = 5000;
    TestVector tv2; tv2.vector_index = 2; tv2.inputs["pressure"] = 850; tv2.inputs["altitude"] = 5000;

    auto recs = MCDCGapAdvisor::adviseGaps(dec, {tv1, tv2});
    ASSERT_EQ(recs.size(), 1);
    ASSERT_EQ(recs[0].condition_id, "C2");
    ASSERT_EQ(recs[0].label, "CANDIDATE VECTOR"); // Strictly labeled CANDIDATE VECTOR
    ASSERT_TRUE(recs[0].recommended_inputs.find("altitude") != recs[0].recommended_inputs.end());

    std::cout << "  -> PASSED: Gap Advisor recommended candidate vector: " << nlohmann::json(recs[0].recommended_inputs).dump() << std::endl;
}

void test_coverage_parser() {
    std::cout << "[Test 7/10] Testing GCOV Coverage Parser..." << std::endl;
    // Create a mock .gcov file
    std::string mockGcov =
        "        -:    0:Source:cabin_pressure.c\n"
        "        -:    0:Graph:cabin_pressure.gcno\n"
        "        -:    0:Data:cabin_pressure.gcda\n"
        "        -:    0:Runs:1\n"
        "        -:    1:#include \"cabin_pressure.h\"\n"
        "        4:    3:int cabin_pressure_control(int pressure, int altitude) {\n"
        "        4:    4:    int sensor_val = sensor_read();\n"
        "        4:    5:    if (pressure > 900 && altitude < 10000) {\n"
        "branch  0 taken 2 (fallthrough)\n"
        "branch  1 taken 2\n"
        "        1:    6:        return 1;\n"
        "        -:    7:    }\n"
        "        3:    8:    return 0;\n"
        "        -:    9:}\n";

    fs::path tempGcov = "test_mock.gcov";
    std::ofstream(tempGcov) << mockGcov;

    GcovCoverageProvider provider;
    auto cov = provider.parseGcovFile(tempGcov.string());

    ASSERT_EQ(cov.total_lines, 5);
    ASSERT_EQ(cov.covered_lines, 5);
    ASSERT_EQ(cov.statement_coverage_pct, 100.0);
    ASSERT_EQ(cov.total_branches, 2);
    ASSERT_EQ(cov.covered_branches, 2);

    fs::remove(tempGcov);
    std::cout << "  -> PASSED: Statement (100%) and Branch (100%) coverage parsed from gcov." << std::endl;
}

void test_traceability_graph() {
    std::cout << "[Test 8/10] Testing Traceability Graph Generation..." << std::endl;
    Requirement req;
    req.identifier = "HLR-001";
    req.title = "Cabin Pressure Control";
    req.req_type = "HLR";

    FunctionInfo fn;
    fn.id = "fn_cabin_pressure";
    fn.name = "cabin_pressure_control";

    TestVector v;
    v.vector_index = 1;

    auto graph = TraceabilityEngine::buildGraph("proj_001", {req}, {fn}, {v});
    ASSERT_EQ(graph.requirements.size(), 1);
    ASSERT_EQ(graph.functions.size(), 1);
    ASSERT_EQ(graph.test_cases.size(), 1);
    ASSERT_TRUE(!graph.links.empty());

    TraceabilityEngine::linkExecutionAndEvidence(graph, "exec_001", "evid_001");
    ASSERT_EQ(graph.links.size(), 7); // Full chain: Req -> Fn -> TC -> Exec -> Cov -> MCDC -> Evid

    std::cout << "  -> PASSED: End-to-end traceability graph successfully linked." << std::endl;
}

void test_evidence_freshness_lifecycle() {
    std::cout << "[Test 9/10] Testing Cryptographic Evidence and Freshness Lifecycle (CURRENT -> STALE)..." << std::endl;
    std::string originalSource = "int cabin_pressure_control(...) { return 1; }";
    std::vector<StubConfiguration> stubs;
    std::vector<TestVector> vectors;
    CoverageResult cov;
    MCDCResult mcdc;
    TraceabilityGraph trace;

    auto evid = EvidenceRecordBuilder::create(
        "proj_1", "exec_1", "cabin_pressure_control",
        originalSource, stubs, vectors, cov, mcdc, trace
    );

    // Initial check against identical source: must be CURRENT
    auto check1 = FreshnessEvaluator::evaluateFreshness(evid, originalSource, stubs, vectors);
    ASSERT_TRUE(check1.freshness == EvidenceFreshness::CURRENT);
    ASSERT_FALSE(check1.source_changed);

    // Source modification: MUST BECOME STALE WITH REASON
    std::string modifiedSource = "int cabin_pressure_control(...) { return 0; }";
    auto check2 = FreshnessEvaluator::evaluateFreshness(evid, modifiedSource, stubs, vectors);
    ASSERT_TRUE(check2.freshness == EvidenceFreshness::STALE);
    ASSERT_TRUE(check2.source_changed);
    ASSERT_FALSE(check2.reason.empty());

    std::cout << "  -> PASSED: Evidence freshness validated: CURRENT -> STALE with reason: " << check2.reason << std::endl;
}

void test_verification_capsule() {
    std::cout << "[Test 10/10] Testing Verification Capsule Packaging & Integrity Audit..." << std::endl;
    std::map<std::string, std::string> sources = {
        {"cabin_pressure.c", "int main() { return 0; }"},
        {"cabin_pressure.h", "#pragma once"}
    };
    HarnessRequest hReq;
    hReq.target_source_file = "cabin_pressure.c";
    EvidenceRecord evid;
    evid.execution_id = "exec_100";

    auto capsule = VerificationCapsulePackager::createCapsule(
        "proj_capsule", sources, hReq, {}, {}, evid
    );

    ASSERT_TRUE(VerificationCapsulePackager::verifyCapsuleIntegrity(capsule));

    // Export and Re-import
    std::string capPath = "test_capsule.json";
    ASSERT_TRUE(VerificationCapsulePackager::exportCapsule(capsule, capPath));
    auto imported = VerificationCapsulePackager::importCapsule(capPath);
    ASSERT_EQ(imported.capsule_hash, capsule.capsule_hash);
    ASSERT_TRUE(VerificationCapsulePackager::verifyCapsuleIntegrity(imported));

    fs::remove(capPath);
    std::cout << "  -> PASSED: Verification capsule hermetic integrity verified." << std::endl;
}

int main() {
    std::cout << "============================================================" << std::endl;
    std::cout << "HONAERO SENTINEL — VERIFICATION CORE UNIT & ACCEPTANCE TESTS" << std::endl;
    std::cout << "============================================================" << std::endl;

    try {
        test_ast_analysis();
        test_dependency_and_stubs();
        test_harness_generation();
        test_comparator();
        test_mcdc_engine();
        test_mcdc_gap_advisor();
        test_coverage_parser();
        test_traceability_graph();
        test_evidence_freshness_lifecycle();
        test_verification_capsule();

        std::cout << "============================================================" << std::endl;
        std::cout << "ALL 10 VERIFICATION CORE TEST SUITES PASSED SUCCESSFULLY!" << std::endl;
        std::cout << "============================================================" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Test exception: " << e.what() << std::endl;
        return 1;
    }
}
