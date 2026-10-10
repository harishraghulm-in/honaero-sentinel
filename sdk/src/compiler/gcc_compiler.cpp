#include "sentinel/compiler/gcc_compiler.hpp"
#include "sentinel/common/process.hpp"
#include <filesystem>

namespace sentinel {

namespace fs = std::filesystem;

GccCompilerProvider::GccCompilerProvider(std::string compiler_path) {
    config_.compiler_path = std::move(compiler_path);
}

void GccCompilerProvider::configure(const CompilerConfig& config) {
    config_ = config;
}

std::string GccCompilerProvider::getVersion() {
    if (!resolved_version_.empty()) {
        return resolved_version_;
    }
    auto res = ProcessRunner::execute(config_.compiler_path, {"--version"});
    if (res.exit_code == 0) {
        // First line of output
        auto pos = res.stdout_output.find('\n');
        if (pos != std::string::npos) {
            resolved_version_ = res.stdout_output.substr(0, pos);
        } else {
            resolved_version_ = res.stdout_output;
        }
    } else {
        resolved_version_ = "gcc (unreachable: " + res.stderr_output + ")";
    }
    return resolved_version_;
}

std::vector<std::string> GccCompilerProvider::getCapabilities() {
    return {
        "c89", "c99", "c11", "c17",
        "gcov", "profile-arcs", "test-coverage",
        "wall", "wextra", "pedantic",
        "debug-symbols"
    };
}

CompileResult GccCompilerProvider::compileAndLink(
    const std::vector<std::string>& source_files,
    const std::string& output_binary,
    const std::optional<std::string>& working_dir)
{
    CompileResult result;
    std::vector<std::string> args;

    // Standard
    if (!config_.language_standard.empty()) {
        args.push_back("-std=" + config_.language_standard);
    }

    // Default optimization and debugging flags
    args.push_back("-O0");
    args.push_back("-g");

    // Coverage flags
    if (config_.enable_coverage) {
        args.push_back("--coverage");
        args.push_back("-fprofile-arcs");
        args.push_back("-ftest-coverage");
    }

    // Includes
    for (const auto& inc : config_.include_paths) {
        args.push_back("-I" + inc);
    }

    // Defines
    for (const auto& def : config_.defines) {
        args.push_back("-D" + def);
    }

    // Custom flags
    for (const auto& flg : config_.flags) {
        args.push_back(flg);
    }

    // Sources
    for (const auto& src : source_files) {
        args.push_back(src);
    }

    // Output
    args.push_back("-o");
    args.push_back(output_binary);

    result.invoked_command.push_back(config_.compiler_path);
    result.invoked_command.insert(result.invoked_command.end(), args.begin(), args.end());

    auto proc = ProcessRunner::execute(config_.compiler_path, args, working_dir);
    result.exit_code = proc.exit_code;
    result.stdout_output = proc.stdout_output;
    result.stderr_output = proc.stderr_output;
    result.duration_ms = proc.duration_ms;
    result.success = (proc.exit_code == 0 && !proc.timed_out);
    result.output_binary = output_binary;

    return result;
}

} // namespace sentinel
