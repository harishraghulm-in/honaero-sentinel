#pragma once

#include <string>
#include <vector>
#include <memory>
#include "sentinel/model/domain_models.hpp"
#include "sentinel/common/errors.hpp"

namespace sentinel {

class IAstAnalyzer {
public:
    virtual ~IAstAnalyzer() = default;
    virtual AnalysisResult analyzeFile(const std::string& filepath, const std::vector<std::string>& compiler_args = {}) = 0;
    virtual AnalysisResult analyzeSource(const std::string& source_code, const std::string& virtual_filename = "source.c", const std::vector<std::string>& compiler_args = {}) = 0;
};

class ClangAstAnalyzer : public IAstAnalyzer {
public:
    ClangAstAnalyzer();
    ~ClangAstAnalyzer() override;

    AnalysisResult analyzeFile(const std::string& filepath, const std::vector<std::string>& compiler_args = {}) override;
    AnalysisResult analyzeSource(const std::string& source_code, const std::string& virtual_filename = "source.c", const std::vector<std::string>& compiler_args = {}) override;

    static bool isClangLibToolingAvailable() noexcept;
    static std::string getToolchainStatus();

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace sentinel
