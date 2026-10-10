#pragma once

#include "sentinel/compiler/compiler_interface.hpp"

namespace sentinel {

class GccCompilerProvider : public ICompilerProvider {
public:
    explicit GccCompilerProvider(std::string compiler_path = "gcc");
    ~GccCompilerProvider() override = default;

    void configure(const CompilerConfig& config) override;
    CompileResult compileAndLink(
        const std::vector<std::string>& source_files,
        const std::string& output_binary,
        const std::optional<std::string>& working_dir = std::nullopt
    ) override;

    std::string getVersion() override;
    std::vector<std::string> getCapabilities() override;
    std::string name() const noexcept override { return "GccCompilerProvider"; }

private:
    CompilerConfig config_;
    std::string resolved_version_;
};

} // namespace sentinel
