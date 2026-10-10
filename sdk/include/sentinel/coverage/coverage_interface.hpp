#pragma once

#include <string>
#include <vector>
#include "sentinel/model/domain_models.hpp"
#include "sentinel/common/errors.hpp"

namespace sentinel {

class ICoverageProvider {
public:
    virtual ~ICoverageProvider() = default;
    virtual CoverageResult parseCoverage(const std::string& source_file, const std::string& artifacts_directory) = 0;
    virtual CoverageResult parseGcovFile(const std::string& gcov_file_path) = 0;
    virtual std::string name() const noexcept = 0;
};

} // namespace sentinel
