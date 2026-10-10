#pragma once

#include <string>
#include <vector>
#include <filesystem>
#include "sentinel/model/domain_models.hpp"

namespace sentinel {

class VerificationCapsulePackager {
public:
    static VerificationCapsule createCapsule(
        const std::string& projectId,
        const std::map<std::string, std::string>& sourceFilesWithContent,
        const HarnessRequest& harnessConfig,
        const std::vector<StubConfiguration>& stubs,
        const std::vector<TestVector>& testVectors,
        const EvidenceRecord& evidence,
        const std::string& compilerPath = "gcc",
        const std::string& compilerVersion = "gcc 11.4.0",
        const std::vector<std::string>& compilerFlags = {"-O0", "-g", "--coverage"}
    );

    static bool exportCapsule(const VerificationCapsule& capsule, const std::string& outputPath);
    static VerificationCapsule importCapsule(const std::string& inputPath);
    static bool verifyCapsuleIntegrity(const VerificationCapsule& capsule);
};

} // namespace sentinel
