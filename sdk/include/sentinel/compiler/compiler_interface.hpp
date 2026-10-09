#pragma once

#include <string>
#include <vector>
#include <optional>
#include "sentinel/common/json.hpp"

namespace sentinel {

struct CompilerConfig {
    std::string compiler_path{"gcc"};
    std::string language_standard{"c11"};
    std::vector<std::string> flags;
    std::vector<std::string> include_paths;
    std::vector<std::string> defines;
    bool enable_coverage{true}; // -fprofile-arcs -ftest-coverage --coverage
};

struct CompileResult {
    bool success{false};
    int exit_code{-1};
    std::string output_binary;
    std::string stdout_output;
    std::string stderr_output;
    double duration_ms{0.0};
    std::vector<std::string> invoked_command;

    nlohmann::json toJson() const {
        return {
            {"success", success},
            {"exit_code", exit_code},
            {"output_binary", output_binary},
            {"stdout_output", stdout_output},
            {"stderr_output", stderr_output},
            {"duration_ms", duration_ms},
            {"invoked_command", invoked_command}
        };
    }
};

class ICompilerProvider {
public:
    virtual ~ICompilerProvider() = default;
    virtual void configure(const CompilerConfig& config) = 0;
    virtual CompileResult compileAndLink(
        const std::vector<std::string>& source_files,
        const std::string& output_binary,
        const std::optional<std::string>& working_dir = std::nullopt
    ) = 0;
    virtual std::string getVersion() = 0;
    virtual std::vector<std::string> getCapabilities() = 0;
    virtual std::string name() const noexcept = 0;
};

} // namespace sentinel
