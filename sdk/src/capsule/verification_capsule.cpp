#include "sentinel/capsule/verification_capsule.hpp"
#include "sentinel/common/sha256.hpp"
#include "sentinel/common/errors.hpp"
#include <fstream>
#include <chrono>
#include <iomanip>
#include <sstream>

namespace sentinel {

static std::string getCurrentUtcTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto in_time_t = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&in_time_t), "%Y-%m-%dT%H:%M:%SZ");
    return ss.str();
}

VerificationCapsule VerificationCapsulePackager::createCapsule(
    const std::string& projectId,
    const std::map<std::string, std::string>& sourceFilesWithContent,
    const HarnessRequest& harnessConfig,
    const std::vector<StubConfiguration>& stubs,
    const std::vector<TestVector>& testVectors,
    const EvidenceRecord& evidence,
    const std::string& compilerPath,
    const std::string& compilerVersion,
    const std::vector<std::string>& compilerFlags)
{
    VerificationCapsule cap;
    cap.capsule_id = "capsule_" + projectId + "_" + evidence.execution_id;
    cap.schema_version = "1.0.0";
    cap.project_id = projectId;
    cap.created_at = getCurrentUtcTimestamp();

    // Source manifest and contents
    for (const auto& [path, content] : sourceFilesWithContent) {
        cap.source_manifest[path] = Sha256::hashString(content);
        cap.source_contents[path] = content;
    }

    cap.harness_config = harnessConfig;
    cap.stubs = stubs;
    cap.test_vectors = testVectors;
    cap.compiler_path = compilerPath;
    cap.compiler_version = compilerVersion;
    cap.compiler_flags = compilerFlags;
    cap.evidence = evidence;

    // Calculate deterministic capsule content hash (excluding timestamp)
    nlohmann::json contentForHashing = {
        {"project_id", cap.project_id},
        {"source_manifest", cap.source_manifest},
        {"harness_config", cap.harness_config.toJson()},
        {"compiler_version", cap.compiler_version},
        {"compiler_flags", cap.compiler_flags},
        {"evidence_source_checksum", cap.evidence.source_checksum},
        {"evidence_vector_checksum", cap.evidence.vector_checksum}
    };
    cap.capsule_hash = Sha256::hashJsonCanonical(contentForHashing);

    return cap;
}

bool VerificationCapsulePackager::exportCapsule(const VerificationCapsule& capsule, const std::string& outputPath) {
    std::ofstream out(outputPath);
    if (!out.is_open()) return false;
    out << capsule.toJson().dump(2);
    return true;
}

VerificationCapsule VerificationCapsulePackager::importCapsule(const std::string& inputPath) {
    std::ifstream in(inputPath);
    if (!in.is_open()) {
        throw EvidenceError("Failed to open capsule file for import", inputPath);
    }
    nlohmann::json j;
    in >> j;

    VerificationCapsule cap;
    if (j.contains("capsule_id")) cap.capsule_id = j["capsule_id"].get<std::string>();
    if (j.contains("schema_version")) cap.schema_version = j["schema_version"].get<std::string>();
    if (j.contains("project_id")) cap.project_id = j["project_id"].get<std::string>();
    if (j.contains("created_at")) cap.created_at = j["created_at"].get<std::string>();
    if (j.contains("source_manifest")) cap.source_manifest = j["source_manifest"].get<std::map<std::string, std::string>>();
    if (j.contains("source_contents")) cap.source_contents = j["source_contents"].get<std::map<std::string, std::string>>();
    if (j.contains("harness_config")) cap.harness_config = HarnessRequest::fromJson(j["harness_config"]);
    if (j.contains("stubs")) {
        for (const auto& s : j["stubs"]) cap.stubs.push_back(StubConfiguration::fromJson(s));
    }
    if (j.contains("test_vectors")) {
        for (const auto& v : j["test_vectors"]) cap.test_vectors.push_back(TestVector::fromJson(v));
    }
    if (j.contains("compiler_path")) cap.compiler_path = j["compiler_path"].get<std::string>();
    if (j.contains("compiler_version")) cap.compiler_version = j["compiler_version"].get<std::string>();
    if (j.contains("compiler_flags")) cap.compiler_flags = j["compiler_flags"].get<std::vector<std::string>>();
    if (j.contains("capsule_hash")) cap.capsule_hash = j["capsule_hash"].get<std::string>();

    return cap;
}

bool VerificationCapsulePackager::verifyCapsuleIntegrity(const VerificationCapsule& capsule) {
    // 1. Verify every source file content matches its declared SHA-256
    for (const auto& [path, content] : capsule.source_contents) {
        auto it = capsule.source_manifest.find(path);
        if (it == capsule.source_manifest.end()) return false;
        if (Sha256::hashString(content) != it->second) return false;
    }

    // 2. Verify capsule hash
    nlohmann::json contentForHashing = {
        {"project_id", capsule.project_id},
        {"source_manifest", capsule.source_manifest},
        {"harness_config", capsule.harness_config.toJson()},
        {"compiler_version", capsule.compiler_version},
        {"compiler_flags", capsule.compiler_flags},
        {"evidence_source_checksum", capsule.evidence.source_checksum},
        {"evidence_vector_checksum", capsule.evidence.vector_checksum}
    };
    std::string expectedHash = Sha256::hashJsonCanonical(contentForHashing);
    return expectedHash == capsule.capsule_hash;
}

} // namespace sentinel
