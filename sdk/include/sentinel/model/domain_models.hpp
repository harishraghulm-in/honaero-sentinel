#pragma once

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <optional>
#include "sentinel/common/source_location.hpp"
#include "sentinel/common/json.hpp"

namespace sentinel {

// ==========================================
// 1. AST & Variable Models
// ==========================================

struct PointerInfo {
    bool is_pointer{false};
    int indirection_level{0};
    std::string pointee_type;

    nlohmann::json toJson() const {
        return {
            {"is_pointer", is_pointer},
            {"indirection_level", indirection_level},
            {"pointee_type", pointee_type}
        };
    }
    static PointerInfo fromJson(const nlohmann::json& j) {
        PointerInfo p;
        if (j.contains("is_pointer")) p.is_pointer = j["is_pointer"].get<bool>();
        if (j.contains("indirection_level")) p.indirection_level = j["indirection_level"].get<int>();
        if (j.contains("pointee_type")) p.pointee_type = j["pointee_type"].get<std::string>();
        return p;
    }
};

struct ArrayInfo {
    bool is_array{false};
    std::vector<int> dimensions;
    std::string element_type;

    nlohmann::json toJson() const {
        return {
            {"is_array", is_array},
            {"dimensions", dimensions},
            {"element_type", element_type}
        };
    }
    static ArrayInfo fromJson(const nlohmann::json& j) {
        ArrayInfo a;
        if (j.contains("is_array")) a.is_array = j["is_array"].get<bool>();
        if (j.contains("dimensions")) a.dimensions = j["dimensions"].get<std::vector<int>>();
        if (j.contains("element_type")) a.element_type = j["element_type"].get<std::string>();
        return a;
    }
};

struct ParameterInfo {
    std::string name;
    std::string type;
    bool is_pointer{false};
    bool is_array{false};
    PointerInfo pointer_details;
    ArrayInfo array_details;
    SourceLocation location;

    nlohmann::json toJson() const {
        return {
            {"name", name},
            {"type", type},
            {"is_pointer", is_pointer},
            {"is_array", is_array},
            {"pointer_details", pointer_details.toJson()},
            {"array_details", array_details.toJson()},
            {"location", location.toJson()}
        };
    }
    static ParameterInfo fromJson(const nlohmann::json& j) {
        ParameterInfo p;
        if (j.contains("name")) p.name = j["name"].get<std::string>();
        if (j.contains("type")) p.type = j["type"].get<std::string>();
        if (j.contains("is_pointer")) p.is_pointer = j["is_pointer"].get<bool>();
        if (j.contains("is_array")) p.is_array = j["is_array"].get<bool>();
        if (j.contains("pointer_details")) p.pointer_details = PointerInfo::fromJson(j["pointer_details"]);
        if (j.contains("array_details")) p.array_details = ArrayInfo::fromJson(j["array_details"]);
        if (j.contains("location")) p.location = SourceLocation::fromJson(j["location"]);
        return p;
    }
};

struct VariableInfo {
    std::string name;
    std::string type;
    bool is_const{false};
    bool is_static{false};
    SourceLocation location;

    nlohmann::json toJson() const {
        return {
            {"name", name},
            {"type", type},
            {"is_const", is_const},
            {"is_static", is_static},
            {"location", location.toJson()}
        };
    }
    static VariableInfo fromJson(const nlohmann::json& j) {
        VariableInfo v;
        if (j.contains("name")) v.name = j["name"].get<std::string>();
        if (j.contains("type")) v.type = j["type"].get<std::string>();
        if (j.contains("is_const")) v.is_const = j["is_const"].get<bool>();
        if (j.contains("is_static")) v.is_static = j["is_static"].get<bool>();
        if (j.contains("location")) v.location = SourceLocation::fromJson(j["location"]);
        return v;
    }
};

struct GlobalVariableInfo {
    VariableInfo variable;
    std::string linkage; // external, internal

    nlohmann::json toJson() const {
        nlohmann::json j = variable.toJson();
        j["linkage"] = linkage;
        return j;
    }
    static GlobalVariableInfo fromJson(const nlohmann::json& j) {
        GlobalVariableInfo g;
        g.variable = VariableInfo::fromJson(j);
        if (j.contains("linkage")) g.linkage = j["linkage"].get<std::string>();
        return g;
    }
};

struct StructMemberInfo {
    std::string name;
    std::string type;
    int offset_bytes{0};

    nlohmann::json toJson() const {
        return {{"name", name}, {"type", type}, {"offset_bytes", offset_bytes}};
    }
    static StructMemberInfo fromJson(const nlohmann::json& j) {
        StructMemberInfo m;
        if (j.contains("name")) m.name = j["name"].get<std::string>();
        if (j.contains("type")) m.type = j["type"].get<std::string>();
        if (j.contains("offset_bytes")) m.offset_bytes = j["offset_bytes"].get<int>();
        return m;
    }
};

struct StructInfo {
    std::string name;
    std::vector<StructMemberInfo> members;
    int total_size_bytes{0};
    SourceLocation location;

    nlohmann::json toJson() const {
        nlohmann::json members_json = nlohmann::json::array();
        for (const auto& m : members) members_json.push_back(m.toJson());
        return {
            {"name", name},
            {"members", members_json},
            {"total_size_bytes", total_size_bytes},
            {"location", location.toJson()}
        };
    }
};

// ==========================================
// 2. Decision & Condition Models (MC/DC)
// ==========================================

struct ConditionInfo {
    std::string id;              // e.g. "C1", "C2"
    std::string expression;      // e.g. "pressure > 900"
    std::vector<std::string> variable_references; // e.g. ["pressure"]
    std::string relational_operator; // ">", "<", "==", "!=", ">=", "<="
    std::string left_operand;
    std::string right_operand;
    SourceLocation location;

    nlohmann::json toJson() const {
        return {
            {"id", id},
            {"expression", expression},
            {"variable_references", variable_references},
            {"relational_operator", relational_operator},
            {"left_operand", left_operand},
            {"right_operand", right_operand},
            {"location", location.toJson()}
        };
    }
    static ConditionInfo fromJson(const nlohmann::json& j) {
        ConditionInfo c;
        if (j.contains("id")) c.id = j["id"].get<std::string>();
        if (j.contains("expression")) c.expression = j["expression"].get<std::string>();
        if (j.contains("variable_references")) c.variable_references = j["variable_references"].get<std::vector<std::string>>();
        if (j.contains("relational_operator")) c.relational_operator = j["relational_operator"].get<std::string>();
        if (j.contains("left_operand")) c.left_operand = j["left_operand"].get<std::string>();
        if (j.contains("right_operand")) c.right_operand = j["right_operand"].get<std::string>();
        if (j.contains("location")) c.location = SourceLocation::fromJson(j["location"]);
        return c;
    }
};

struct DecisionInfo {
    std::string id;              // e.g. "D1"
    std::string expression;      // e.g. "pressure > 900 && altitude < 10000"
    int line_number{0};
    SourceLocation location;
    std::vector<ConditionInfo> conditions;

    nlohmann::json toJson() const {
        nlohmann::json conds = nlohmann::json::array();
        for (const auto& c : conditions) conds.push_back(c.toJson());
        return {
            {"id", id},
            {"expression", expression},
            {"line_number", line_number},
            {"location", location.toJson()},
            {"conditions", conds}
        };
    }
    static DecisionInfo fromJson(const nlohmann::json& j) {
        DecisionInfo d;
        if (j.contains("id")) d.id = j["id"].get<std::string>();
        if (j.contains("expression")) d.expression = j["expression"].get<std::string>();
        if (j.contains("line_number")) d.line_number = j["line_number"].get<int>();
        if (j.contains("location")) d.location = SourceLocation::fromJson(j["location"]);
        if (j.contains("conditions")) {
            for (const auto& c : j["conditions"]) d.conditions.push_back(ConditionInfo::fromJson(c));
        }
        return d;
    }
};

// ==========================================
// 3. Dependencies & Stubs
// ==========================================

enum class DependencyClassification {
    REAL,
    STUB
};

inline std::string dependencyClassificationToString(DependencyClassification c) {
    return c == DependencyClassification::REAL ? "REAL" : "STUB";
}

inline DependencyClassification dependencyClassificationFromString(const std::string& s) {
    return s == "REAL" ? DependencyClassification::REAL : DependencyClassification::STUB;
}

struct DependencyInfo {
    std::string id;
    std::string name;
    std::string return_type{"void"};
    std::vector<ParameterInfo> parameters;
    SourceLocation location;
    DependencyClassification classification{DependencyClassification::STUB};
    std::string call_site_file;
    int call_site_line{0};

    nlohmann::json toJson() const {
        nlohmann::json params = nlohmann::json::array();
        for (const auto& p : parameters) params.push_back(p.toJson());
        return {
            {"id", id},
            {"name", name},
            {"return_type", return_type},
            {"parameters", params},
            {"location", location.toJson()},
            {"mode", dependencyClassificationToString(classification)},
            {"classification", dependencyClassificationToString(classification)},
            {"call_site_file", call_site_file},
            {"call_site_line", call_site_line}
        };
    }
    static DependencyInfo fromJson(const nlohmann::json& j) {
        DependencyInfo d;
        if (j.contains("id")) d.id = j["id"].get<std::string>();
        if (j.contains("name")) d.name = j["name"].get<std::string>();
        if (j.contains("return_type")) d.return_type = j["return_type"].get<std::string>();
        if (j.contains("parameters")) {
            for (const auto& p : j["parameters"]) d.parameters.push_back(ParameterInfo::fromJson(p));
        }
        if (j.contains("location")) d.location = SourceLocation::fromJson(j["location"]);
        if (j.contains("mode")) d.classification = dependencyClassificationFromString(j["mode"].get<std::string>());
        else if (j.contains("classification")) d.classification = dependencyClassificationFromString(j["classification"].get<std::string>());
        if (j.contains("call_site_file")) d.call_site_file = j["call_site_file"].get<std::string>();
        if (j.contains("call_site_line")) d.call_site_line = j["call_site_line"].get<int>();
        return d;
    }
};

struct DependencyGraph {
    std::string root_function;
    std::vector<DependencyInfo> dependencies;

    nlohmann::json toJson() const {
        nlohmann::json deps = nlohmann::json::array();
        for (const auto& d : dependencies) deps.push_back(d.toJson());
        return {
            {"root_function", root_function},
            {"dependencies", deps}
        };
    }
    static DependencyGraph fromJson(const nlohmann::json& j) {
        DependencyGraph g;
        if (j.contains("root_function")) g.root_function = j["root_function"].get<std::string>();
        if (j.contains("dependencies")) {
            for (const auto& d : j["dependencies"]) g.dependencies.push_back(DependencyInfo::fromJson(d));
        }
        return g;
    }
};

struct StubConfiguration {
    std::string dependency_id;
    std::string function_name;
    std::string mode{"STUB"}; // REAL or STUB
    std::string return_type{"void"};
    nlohmann::json default_return_value;
    std::vector<nlohmann::json> return_values;      // successive return values
    std::map<std::string, nlohmann::json> output_params;
    int expected_call_count{0};
    int call_count{0};
    std::string custom_c_body;

    nlohmann::json toJson() const {
        return {
            {"dependency_id", dependency_id},
            {"function_name", function_name},
            {"mode", mode},
            {"return_type", return_type},
            {"default_return_value", default_return_value},
            {"return_values", return_values},
            {"output_params", output_params},
            {"expected_call_count", expected_call_count},
            {"call_count", call_count},
            {"custom_c_body", custom_c_body}
        };
    }
    static StubConfiguration fromJson(const nlohmann::json& j) {
        StubConfiguration s;
        if (j.contains("dependency_id")) s.dependency_id = j["dependency_id"].get<std::string>();
        if (j.contains("function_name")) s.function_name = j["function_name"].get<std::string>();
        if (j.contains("mode")) s.mode = j["mode"].get<std::string>();
        if (j.contains("return_type")) s.return_type = j["return_type"].get<std::string>();
        if (j.contains("default_return_value")) s.default_return_value = j["default_return_value"];
        if (j.contains("return_values")) s.return_values = j["return_values"].get<std::vector<nlohmann::json>>();
        if (j.contains("output_params")) s.output_params = j["output_params"].get<std::map<std::string, nlohmann::json>>();
        if (j.contains("expected_call_count")) s.expected_call_count = j["expected_call_count"].get<int>();
        if (j.contains("call_count")) s.call_count = j["call_count"].get<int>();
        if (j.contains("custom_c_body")) s.custom_c_body = j["custom_c_body"].get<std::string>();
        return s;
    }
};

// ==========================================
// 4. Function Info & Analysis Result
// ==========================================

struct FunctionInfo {
    std::string id;
    std::string name;
    std::string return_type;
    std::vector<ParameterInfo> parameters;
    std::vector<VariableInfo> local_variables;
    std::vector<DecisionInfo> decisions;
    std::vector<DependencyInfo> external_calls;
    SourceLocation location;
    bool is_target_under_test{false};

    nlohmann::json toJson() const {
        nlohmann::json params = nlohmann::json::array();
        for (const auto& p : parameters) params.push_back(p.toJson());
        nlohmann::json locals = nlohmann::json::array();
        for (const auto& l : local_variables) locals.push_back(l.toJson());
        nlohmann::json decs = nlohmann::json::array();
        for (const auto& d : decisions) decs.push_back(d.toJson());
        nlohmann::json calls = nlohmann::json::array();
        for (const auto& c : external_calls) calls.push_back(c.toJson());

        return {
            {"id", id},
            {"name", name},
            {"return_type", return_type},
            {"parameters", params},
            {"local_variables", locals},
            {"decisions", decs},
            {"external_calls", calls},
            {"location", location.toJson()},
            {"is_target_under_test", is_target_under_test}
        };
    }
    static FunctionInfo fromJson(const nlohmann::json& j) {
        FunctionInfo f;
        if (j.contains("id")) f.id = j["id"].get<std::string>();
        if (j.contains("name")) f.name = j["name"].get<std::string>();
        if (j.contains("return_type")) f.return_type = j["return_type"].get<std::string>();
        if (j.contains("parameters")) {
            for (const auto& p : j["parameters"]) f.parameters.push_back(ParameterInfo::fromJson(p));
        }
        if (j.contains("local_variables")) {
            for (const auto& l : j["local_variables"]) f.local_variables.push_back(VariableInfo::fromJson(l));
        }
        if (j.contains("decisions")) {
            for (const auto& d : j["decisions"]) f.decisions.push_back(DecisionInfo::fromJson(d));
        }
        if (j.contains("external_calls")) {
            for (const auto& c : j["external_calls"]) f.external_calls.push_back(DependencyInfo::fromJson(c));
        }
        if (j.contains("location")) f.location = SourceLocation::fromJson(j["location"]);
        if (j.contains("is_target_under_test")) f.is_target_under_test = j["is_target_under_test"].get<bool>();
        return f;
    }
};

struct AnalysisResult {
    std::string project_id;
    std::string source_file;
    int total_sources{1};
    std::vector<FunctionInfo> functions;
    std::vector<DependencyInfo> dependencies;
    std::vector<GlobalVariableInfo> globals;

    nlohmann::json toJson() const {
        nlohmann::json funcs = nlohmann::json::array();
        for (const auto& f : functions) funcs.push_back(f.toJson());
        nlohmann::json deps = nlohmann::json::array();
        for (const auto& d : dependencies) deps.push_back(d.toJson());
        nlohmann::json globs = nlohmann::json::array();
        for (const auto& g : globals) globs.push_back(g.toJson());

        return {
            {"project_id", project_id},
            {"source_file", source_file},
            {"total_sources", total_sources},
            {"functions", funcs},
            {"dependencies", deps},
            {"globals", globs}
        };
    }
    static AnalysisResult fromJson(const nlohmann::json& j) {
        AnalysisResult res;
        if (j.contains("project_id")) res.project_id = j["project_id"].get<std::string>();
        if (j.contains("source_file")) res.source_file = j["source_file"].get<std::string>();
        if (j.contains("total_sources")) res.total_sources = j["total_sources"].get<int>();
        if (j.contains("functions")) {
            for (const auto& f : j["functions"]) res.functions.push_back(FunctionInfo::fromJson(f));
        }
        if (j.contains("dependencies")) {
            for (const auto& d : j["dependencies"]) res.dependencies.push_back(DependencyInfo::fromJson(d));
        }
        return res;
    }
};

// ==========================================
// 5. Test Vectors & Harness
// ==========================================

struct TestVector {
    int vector_index{1};
    std::string id;
    std::string description;
    std::map<std::string, nlohmann::json> inputs;
    std::map<std::string, nlohmann::json> expected_outputs;
    std::map<std::string, std::string> metadata;

    nlohmann::json toJson() const {
        return {
            {"vector_index", vector_index},
            {"id", id},
            {"description", description},
            {"inputs", inputs},
            {"expected_outputs", expected_outputs},
            {"metadata", metadata}
        };
    }
    static TestVector fromJson(const nlohmann::json& j) {
        TestVector v;
        if (j.contains("vector_index")) v.vector_index = j["vector_index"].get<int>();
        if (j.contains("id")) v.id = j["id"].get<std::string>();
        if (j.contains("description")) v.description = j["description"].get<std::string>();
        if (j.contains("inputs") && j["inputs"].is_object()) {
            for (auto it = j["inputs"].begin(); it != j["inputs"].end(); ++it) {
                v.inputs[it.key()] = it.value();
            }
        }
        if (j.contains("expected_outputs") && j["expected_outputs"].is_object()) {
            for (auto it = j["expected_outputs"].begin(); it != j["expected_outputs"].end(); ++it) {
                v.expected_outputs[it.key()] = it.value();
            }
        }
        if (j.contains("metadata") && j["metadata"].is_object()) {
            for (auto it = j["metadata"].begin(); it != j["metadata"].end(); ++it) {
                v.metadata[it.key()] = it.value().get<std::string>();
            }
        }
        return v;
    }
};

struct UserHooks {
    std::string setup_code;
    std::string before_test_code;
    std::string after_test_code;
    std::string teardown_code;

    nlohmann::json toJson() const {
        return {
            {"setup_code", setup_code},
            {"before_test_code", before_test_code},
            {"after_test_code", after_test_code},
            {"teardown_code", teardown_code}
        };
    }
    static UserHooks fromJson(const nlohmann::json& j) {
        UserHooks h;
        if (j.contains("setup_code")) h.setup_code = j["setup_code"].get<std::string>();
        if (j.contains("before_test_code")) h.before_test_code = j["before_test_code"].get<std::string>();
        if (j.contains("after_test_code")) h.after_test_code = j["after_test_code"].get<std::string>();
        if (j.contains("teardown_code")) h.teardown_code = j["teardown_code"].get<std::string>();
        return h;
    }
};

struct HarnessRequest {
    std::string project_id;
    std::string target_source_file;
    std::string target_header_file;
    FunctionInfo target_function;
    std::vector<StubConfiguration> stubs;
    std::vector<TestVector> test_vectors;
    UserHooks hooks;
    std::string output_directory;

    nlohmann::json toJson() const {
        nlohmann::json stubs_json = nlohmann::json::array();
        for (const auto& s : stubs) stubs_json.push_back(s.toJson());
        nlohmann::json vectors_json = nlohmann::json::array();
        for (const auto& v : test_vectors) vectors_json.push_back(v.toJson());

        return {
            {"project_id", project_id},
            {"target_source_file", target_source_file},
            {"target_header_file", target_header_file},
            {"target_function", target_function.toJson()},
            {"stubs", stubs_json},
            {"test_vectors", vectors_json},
            {"hooks", hooks.toJson()},
            {"output_directory", output_directory}
        };
    }
    static HarnessRequest fromJson(const nlohmann::json& j) {
        HarnessRequest req;
        if (j.contains("project_id")) req.project_id = j["project_id"].get<std::string>();
        if (j.contains("target_source_file")) req.target_source_file = j["target_source_file"].get<std::string>();
        if (j.contains("target_header_file")) req.target_header_file = j["target_header_file"].get<std::string>();
        if (j.contains("target_function")) req.target_function = FunctionInfo::fromJson(j["target_function"]);
        if (j.contains("stubs")) {
            for (const auto& s : j["stubs"]) req.stubs.push_back(StubConfiguration::fromJson(s));
        }
        if (j.contains("test_vectors")) {
            for (const auto& v : j["test_vectors"]) req.test_vectors.push_back(TestVector::fromJson(v));
        }
        if (j.contains("hooks")) req.hooks = UserHooks::fromJson(j["hooks"]);
        if (j.contains("output_directory")) req.output_directory = j["output_directory"].get<std::string>();
        return req;
    }
};

struct HarnessResult {
    bool success{false};
    std::string harness_source_file;
    std::string stubs_header_file;
    std::string stubs_source_file;
    std::string test_vectors_source_file;
    std::string build_script_file;
    std::string generated_code_hash;
    std::string error_message;

    nlohmann::json toJson() const {
        return {
            {"success", success},
            {"harness_source_file", harness_source_file},
            {"stubs_header_file", stubs_header_file},
            {"stubs_source_file", stubs_source_file},
            {"test_vectors_source_file", test_vectors_source_file},
            {"build_script_file", build_script_file},
            {"generated_code_hash", generated_code_hash},
            {"error_message", error_message}
        };
    }
};

// ==========================================
// 6. Coverage Models
// ==========================================

struct LineCoverageDetail {
    int line{0};
    int execution_count{0};
    bool covered{false};
    std::string source_text;

    nlohmann::json toJson() const {
        return {
            {"line", line},
            {"execution_count", execution_count},
            {"covered", covered},
            {"source_text", source_text}
        };
    }
};

struct BranchCoverageDetail {
    int line{0};
    int branch_number{0};
    int taken_count{0};
    bool covered{false};

    nlohmann::json toJson() const {
        return {
            {"line", line},
            {"branch_number", branch_number},
            {"taken_count", taken_count},
            {"covered", covered}
        };
    }
};

struct CoverageResult {
    std::string execution_id;
    std::string source_file;
    double statement_coverage_pct{0.0};
    double branch_coverage_pct{0.0};
    double function_coverage_pct{0.0};
    double line_coverage_pct{0.0};
    int total_lines{0};
    int covered_lines{0};
    int total_branches{0};
    int covered_branches{0};
    std::vector<int> uncovered_lines;
    std::vector<LineCoverageDetail> line_details;
    std::vector<BranchCoverageDetail> branch_details;
    std::string raw_artifact;

    nlohmann::json toJson() const {
        nlohmann::json lines = nlohmann::json::array();
        for (const auto& l : line_details) lines.push_back(l.toJson());
        nlohmann::json branches = nlohmann::json::array();
        for (const auto& b : branch_details) branches.push_back(b.toJson());

        return {
            {"execution_id", execution_id},
            {"source_file", source_file},
            {"statement_coverage_pct", statement_coverage_pct},
            {"branch_coverage_pct", branch_coverage_pct},
            {"function_coverage_pct", function_coverage_pct},
            {"line_coverage_pct", line_coverage_pct},
            {"total_lines", total_lines},
            {"covered_lines", covered_lines},
            {"total_branches", total_branches},
            {"covered_branches", covered_branches},
            {"uncovered_lines", uncovered_lines},
            {"line_details", lines},
            {"branch_details", branches},
            {"raw_artifact", raw_artifact}
        };
    }
    static CoverageResult fromJson(const nlohmann::json& j) {
        CoverageResult c;
        if (j.contains("execution_id")) c.execution_id = j["execution_id"].get<std::string>();
        if (j.contains("source_file")) c.source_file = j["source_file"].get<std::string>();
        if (j.contains("statement_coverage_pct")) c.statement_coverage_pct = j["statement_coverage_pct"].get<double>();
        if (j.contains("branch_coverage_pct")) c.branch_coverage_pct = j["branch_coverage_pct"].get<double>();
        if (j.contains("function_coverage_pct")) c.function_coverage_pct = j["function_coverage_pct"].get<double>();
        if (j.contains("line_coverage_pct")) c.line_coverage_pct = j["line_coverage_pct"].get<double>();
        if (j.contains("total_lines")) c.total_lines = j["total_lines"].get<int>();
        if (j.contains("covered_lines")) c.covered_lines = j["covered_lines"].get<int>();
        if (j.contains("total_branches")) c.total_branches = j["total_branches"].get<int>();
        if (j.contains("covered_branches")) c.covered_branches = j["covered_branches"].get<int>();
        if (j.contains("uncovered_lines")) c.uncovered_lines = j["uncovered_lines"].get<std::vector<int>>();
        if (j.contains("raw_artifact") && !j["raw_artifact"].is_null()) c.raw_artifact = j["raw_artifact"].get<std::string>();
        return c;
    }
};

// ==========================================
// 7. MC/DC Models
// ==========================================

struct ConditionEvaluation {
    std::string condition_id;
    bool evaluated_value{false};

    nlohmann::json toJson() const {
        return {
            {"condition_id", condition_id},
            {"evaluated_value", evaluated_value}
        };
    }
};

struct TestVectorEvaluation {
    int vector_index{0};
    std::map<std::string, bool> condition_values; // condition_id -> bool
    bool decision_outcome{false};

    nlohmann::json toJson() const {
        return {
            {"vector_index", vector_index},
            {"condition_values", condition_values},
            {"decision_outcome", decision_outcome}
        };
    }
};

struct MCDCIndependencePair {
    std::string condition_id;
    int true_vector_index{0};
    int false_vector_index{0};
    std::string explanation;

    nlohmann::json toJson() const {
        return {
            {"condition_id", condition_id},
            {"true_vector_index", true_vector_index},
            {"false_vector_index", false_vector_index},
            {"explanation", explanation}
        };
    }
};

struct MCDCGap {
    std::string condition_id;
    std::string condition_expression;
    std::string missing_independence_reason;
    std::map<std::string, bool> required_condition_values;
    std::map<std::string, nlohmann::json> candidate_inputs;
    std::string guidance;

    nlohmann::json toJson() const {
        return {
            {"condition_id", condition_id},
            {"condition_expression", condition_expression},
            {"missing_independence_reason", missing_independence_reason},
            {"required_condition_values", required_condition_values},
            {"candidate_inputs", candidate_inputs},
            {"guidance", guidance}
        };
    }
};

struct DecisionMCDCStatus {
    std::string decision_id;
    std::string expression;
    int line_number{0};
    bool mcdc_achieved{false};
    double coverage_pct{0.0};
    int total_conditions{0};
    int covered_conditions{0};
    std::vector<MCDCIndependencePair> independence_pairs;
    std::vector<MCDCGap> gaps;

    nlohmann::json toJson() const {
        nlohmann::json pairs = nlohmann::json::array();
        for (const auto& p : independence_pairs) pairs.push_back(p.toJson());
        nlohmann::json gaps_json = nlohmann::json::array();
        for (const auto& g : gaps) gaps_json.push_back(g.toJson());

        nlohmann::json conds_status = nlohmann::json::array();
        for (const auto& p : independence_pairs) {
            conds_status.push_back({
                {"id", p.condition_id},
                {"independence_proven", true},
                {"independence_pair", "TC-" + std::to_string(p.true_vector_index) + " vs TC-" + std::to_string(p.false_vector_index)}
            });
        }
        for (const auto& g : gaps) {
            conds_status.push_back({
                {"id", g.condition_id},
                {"expression", g.condition_expression},
                {"independence_proven", false},
                {"reason", g.missing_independence_reason}
            });
        }

        return {
            {"decision_id", decision_id},
            {"expression", expression},
            {"line_number", line_number},
            {"mcdc_achieved", mcdc_achieved},
            {"coverage_pct", coverage_pct},
            {"total_conditions", total_conditions},
            {"covered_conditions", covered_conditions},
            {"independence_pairs", pairs},
            {"gaps", gaps_json},
            {"conditions", conds_status}
        };
    }
};

struct MCDCResult {
    std::string execution_id;
    double coverage_percentage{0.0};
    bool full_mcdc_achieved{false};
    std::vector<DecisionMCDCStatus> decisions;
    std::vector<MCDCGap> gap_recommendations;

    nlohmann::json toJson() const {
        nlohmann::json decs = nlohmann::json::array();
        for (const auto& d : decisions) decs.push_back(d.toJson());
        nlohmann::json gaps = nlohmann::json::array();
        for (const auto& g : gap_recommendations) gaps.push_back(g.toJson());

        return {
            {"execution_id", execution_id},
            {"coverage_percentage", coverage_percentage},
            {"full_mcdc_achieved", full_mcdc_achieved},
            {"decisions", decs},
            {"gap_recommendations", gaps}
        };
    }
};

// ==========================================
// 8. Traceability Models
// ==========================================

struct Requirement {
    std::string identifier; // e.g. "HLR-001"
    std::string title;
    std::string description;
    std::string req_type;   // "HLR" or "LLR"

    nlohmann::json toJson() const {
        return {
            {"identifier", identifier},
            {"title", title},
            {"description", description},
            {"req_type", req_type}
        };
    }
    static Requirement fromJson(const nlohmann::json& j) {
        Requirement r;
        if (j.contains("identifier")) r.identifier = j["identifier"].get<std::string>();
        if (j.contains("title")) r.title = j["title"].get<std::string>();
        if (j.contains("description")) r.description = j["description"].get<std::string>();
        if (j.contains("req_type")) r.req_type = j["req_type"].get<std::string>();
        return r;
    }
};

struct TestCaseTrace {
    std::string id;
    std::string name;
    std::string target_function_id;
    std::string requirement_id;
    int vector_count{0};

    nlohmann::json toJson() const {
        return {
            {"id", id},
            {"name", name},
            {"target_function_id", target_function_id},
            {"requirement_id", requirement_id},
            {"vector_count", vector_count}
        };
    }
};

struct TraceabilityLink {
    std::string source_id;
    std::string source_type; // "Requirement", "Function", "TestCase", "Execution", "Coverage", "MCDC", "Evidence"
    std::string target_id;
    std::string target_type;
    std::string relationship; // "IMPLEMENTS", "VERIFIES", "EXECUTES", "MEASURES", "PROVES"

    nlohmann::json toJson() const {
        return {
            {"source_id", source_id},
            {"source_type", source_type},
            {"target_id", target_id},
            {"target_type", target_type},
            {"relationship", relationship}
        };
    }
};

struct TraceabilityGraph {
    std::string project_id;
    std::vector<Requirement> requirements;
    std::vector<FunctionInfo> functions;
    std::vector<TestCaseTrace> test_cases;
    std::vector<TraceabilityLink> links;

    nlohmann::json toJson() const {
        nlohmann::json reqs = nlohmann::json::array();
        for (const auto& r : requirements) reqs.push_back(r.toJson());
        nlohmann::json funcs = nlohmann::json::array();
        for (const auto& f : functions) funcs.push_back(f.toJson());
        nlohmann::json tests = nlohmann::json::array();
        for (const auto& t : test_cases) tests.push_back(t.toJson());
        nlohmann::json lks = nlohmann::json::array();
        for (const auto& l : links) lks.push_back(l.toJson());

        return {
            {"project_id", project_id},
            {"requirements", reqs},
            {"functions", funcs},
            {"test_cases", tests},
            {"links", lks}
        };
    }
};

// ==========================================
// 9. Evidence & Freshness Models
// ==========================================

enum class EvidenceFreshness {
    CURRENT,
    STALE,
    INVALIDATED
};

inline std::string evidenceFreshnessToString(EvidenceFreshness f) {
    switch (f) {
        case EvidenceFreshness::CURRENT: return "CURRENT";
        case EvidenceFreshness::STALE: return "STALE";
        case EvidenceFreshness::INVALIDATED: return "INVALIDATED";
    }
    return "INVALIDATED";
}

inline EvidenceFreshness evidenceFreshnessFromString(const std::string& s) {
    if (s == "CURRENT") return EvidenceFreshness::CURRENT;
    if (s == "STALE") return EvidenceFreshness::STALE;
    return EvidenceFreshness::INVALIDATED;
}

struct EvidenceRecord {
    std::string evidence_id;
    std::string project_id;
    std::string execution_id;
    std::string target_function;
    std::string timestamp; // recorded execution timestamp
    std::string tool_version{"1.0.0"};
    
    // Checksums (Content hashes without timestamps)
    std::string source_checksum;
    std::string stub_checksum;
    std::string vector_checksum;
    std::string configuration_checksum;

    // Freshness & State
    EvidenceFreshness freshness{EvidenceFreshness::CURRENT};
    std::string freshness_reason;
    std::vector<std::string> affected_test_cases;

    // Toolchain & Configuration
    std::string compiler;
    std::string compiler_version;
    std::vector<std::string> compiler_flags;

    // Results
    std::string build_status{"PASSED"};
    std::string execution_status{"PASSED"};
    int exit_code{0};
    double duration_ms{0.0};
    CoverageResult coverage;
    MCDCResult mcdc;
    TraceabilityGraph traceability;
    nlohmann::json evidence_data;

    nlohmann::json toJson() const {
        return {
            {"evidence_id", evidence_id},
            {"project_id", project_id},
            {"execution_id", execution_id},
            {"target_function", target_function},
            {"timestamp", timestamp},
            {"tool_version", tool_version},
            {"source_checksum", source_checksum},
            {"stub_checksum", stub_checksum},
            {"vector_checksum", vector_checksum},
            {"configuration_checksum", configuration_checksum},
            {"freshness", evidenceFreshnessToString(freshness)},
            {"freshness_reason", freshness_reason},
            {"affected_test_cases", affected_test_cases},
            {"compiler", compiler},
            {"compiler_version", compiler_version},
            {"compiler_flags", compiler_flags},
            {"build_status", build_status},
            {"execution_status", execution_status},
            {"exit_code", exit_code},
            {"duration_ms", duration_ms},
            {"coverage", coverage.toJson()},
            {"mcdc", mcdc.toJson()},
            {"traceability", traceability.toJson()},
            {"evidence_data", evidence_data}
        };
    }
};

// ==========================================
// 10. Verification Capsule
// ==========================================

struct VerificationCapsule {
    std::string capsule_id;
    std::string schema_version{"1.0.0"};
    std::string project_id;
    std::string created_at;
    
    // Manifest of files and content hashes
    std::map<std::string, std::string> source_manifest; // path -> sha256
    std::map<std::string, std::string> source_contents; // path -> raw content
    
    // Exact configurations
    HarnessRequest harness_config;
    std::vector<StubConfiguration> stubs;
    std::vector<TestVector> test_vectors;
    
    // Environment & Toolchain
    std::string compiler_path;
    std::string compiler_version;
    std::vector<std::string> compiler_flags;
    
    // Evidence & Verification outputs
    EvidenceRecord evidence;
    std::string capsule_hash; // SHA-256 over canonicalized package contents

    nlohmann::json toJson() const {
        nlohmann::json stubs_json = nlohmann::json::array();
        for (const auto& s : stubs) stubs_json.push_back(s.toJson());
        nlohmann::json vecs_json = nlohmann::json::array();
        for (const auto& v : test_vectors) vecs_json.push_back(v.toJson());

        return {
            {"capsule_id", capsule_id},
            {"schema_version", schema_version},
            {"project_id", project_id},
            {"created_at", created_at},
            {"source_manifest", source_manifest},
            {"source_contents", source_contents},
            {"harness_config", harness_config.toJson()},
            {"stubs", stubs_json},
            {"test_vectors", vecs_json},
            {"compiler_path", compiler_path},
            {"compiler_version", compiler_version},
            {"compiler_flags", compiler_flags},
            {"evidence", evidence.toJson()},
            {"capsule_hash", capsule_hash}
        };
    }
};

} // namespace sentinel
