#pragma once

#include "sentinel/coverage/coverage_interface.hpp"

namespace sentinel {

class GcovCoverageProvider : public ICoverageProvider {
public:
    explicit GcovCoverageProvider(std::string gcov_binary = "gcov");
    ~GcovCoverageProvider() override = default;

    CoverageResult parseCoverage(const std::string& source_file, const std::string& artifacts_directory) override;
    CoverageResult parseGcovFile(const std::string& gcov_file_path) override;
    std::string name() const noexcept override { return "GcovCoverageProvider"; }

private:
    std::string gcov_binary_;
};

} // namespace sentinel
