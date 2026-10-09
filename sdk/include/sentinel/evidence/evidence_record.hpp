#pragma once

#include <string>
#include <vector>
#include "sentinel/model/domain_models.hpp"
#include "sentinel/common/sha256.hpp"

namespace sentinel {

struct FreshnessCheckResult {
    EvidenceFreshness freshness{EvidenceFreshness::CURRENT};
    std::string reason;
    std::vector<std::string> affected_test_cases;
    bool source_changed{false};
    bool stubs_changed{false};
    bool vectors_changed{false};
    bool compiler_changed{false};

    nlohmann::json toJson() const {
        return {
            {"freshness", evidenceFreshnessToString(freshness)},
            {"reason", reason},
            {"affected_test_cases", affected_test_cases},
            {"source_changed", source_changed},
            {"stubs_changed", stubs_changed},
            {"vectors_changed", vectors_changed},
            {"compiler_changed", compiler_changed}
        };
    }
};

class FreshnessEvaluator {
public:
    static FreshnessCheckResult evaluateFreshness(
        const EvidenceRecord& record,
        const std::string& currentSourceContent,
        const std::vector<StubConfiguration>& currentStubs = {},
        const std::vector<TestVector>& currentVectors = {},
        const std::string& currentCompilerVersion = ""
    );

    static FreshnessCheckResult evaluateFileFreshness(
        const EvidenceRecord& record,
        const std::string& currentSourceFilePath,
        const std::vector<StubConfiguration>& currentStubs = {},
        const std::vector<TestVector>& currentVectors = {}
    );
};

class EvidenceRecordBuilder {
public:
    static EvidenceRecord create(
        const std::string& projectId,
        const std::string& executionId,
        const std::string& targetFunction,
        const std::string& sourceContent,
        const std::vector<StubConfiguration>& stubs,
        const std::vector<TestVector>& vectors,
        const CoverageResult& coverage,
        const MCDCResult& mcdc,
        const TraceabilityGraph& traceability,
        const std::string& compiler = "gcc",
        const std::string& compilerVersion = "gcc 11.4.0",
        const std::vector<std::string>& compilerFlags = {"-O0", "-g", "--coverage"}
    );
};

} // namespace sentinel
