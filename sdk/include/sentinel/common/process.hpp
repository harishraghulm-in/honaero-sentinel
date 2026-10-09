#pragma once

#include <string>
#include <vector>
#include <optional>
#include <chrono>

namespace sentinel {

struct ProcessResult {
    int exit_code{-1};
    std::string stdout_output;
    std::string stderr_output;
    bool timed_out{false};
    double duration_ms{0.0};

    bool success() const noexcept {
        return exit_code == 0 && !timed_out;
    }
};

class ProcessRunner {
public:
    static ProcessResult execute(
        const std::string& executable,
        const std::vector<std::string>& arguments,
        const std::optional<std::string>& working_dir = std::nullopt,
        std::chrono::milliseconds timeout = std::chrono::milliseconds(10000)
    );
};

} // namespace sentinel
