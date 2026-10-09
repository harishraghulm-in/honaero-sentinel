#pragma once

#include <exception>
#include <string>
#include <optional>
#include "sentinel/common/source_location.hpp"
#include "sentinel/common/json.hpp"

namespace sentinel {

class SentinelError : public std::exception {
protected:
    std::string code_;
    std::string message_;
    std::string details_;
    std::optional<SourceLocation> location_;
    mutable std::string what_buffer_;

public:
    SentinelError(std::string code, std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : code_(std::move(code)), message_(std::move(message)), details_(std::move(details)), location_(std::move(loc)) {}

    const char* what() const noexcept override {
        if (what_buffer_.empty()) {
            what_buffer_ = "[" + code_ + "] " + message_;
            if (!details_.empty()) {
                what_buffer_ += " - " + details_;
            }
            if (location_.has_value() && location_->isValid()) {
                what_buffer_ += " at " + location_->file + ":" + std::to_string(location_->line) + ":" + std::to_string(location_->column);
            }
        }
        return what_buffer_.c_str();
    }

    const std::string& code() const noexcept { return code_; }
    const std::string& message() const noexcept { return message_; }
    const std::string& details() const noexcept { return details_; }
    const std::optional<SourceLocation>& location() const noexcept { return location_; }

    nlohmann::json toJson() const {
        nlohmann::json j = {
            {"code", code_},
            {"message", message_},
            {"details", details_}
        };
        if (location_.has_value() && location_->isValid()) {
            j["location"] = location_->toJson();
        } else {
            j["location"] = nullptr;
        }
        return j;
    }
};

class ParseError : public SentinelError {
public:
    explicit ParseError(std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : SentinelError("PARSE_ERROR", std::move(message), std::move(details), std::move(loc)) {}
};

class UnsupportedConstructError : public SentinelError {
public:
    explicit UnsupportedConstructError(std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : SentinelError("UNSUPPORTED_CONSTRUCT_ERROR", std::move(message), std::move(details), std::move(loc)) {}
};

class HarnessGenerationError : public SentinelError {
public:
    explicit HarnessGenerationError(std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : SentinelError("HARNESS_GENERATION_ERROR", std::move(message), std::move(details), std::move(loc)) {}
};

class CompilerError : public SentinelError {
public:
    explicit CompilerError(std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : SentinelError("COMPILER_ERROR", std::move(message), std::move(details), std::move(loc)) {}
};

class CoverageError : public SentinelError {
public:
    explicit CoverageError(std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : SentinelError("COVERAGE_ERROR", std::move(message), std::move(details), std::move(loc)) {}
};

class MCDCAnalysisError : public SentinelError {
public:
    explicit MCDCAnalysisError(std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : SentinelError("MCDC_ANALYSIS_ERROR", std::move(message), std::move(details), std::move(loc)) {}
};

class InvalidTestVectorError : public SentinelError {
public:
    explicit InvalidTestVectorError(std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : SentinelError("INVALID_TEST_VECTOR_ERROR", std::move(message), std::move(details), std::move(loc)) {}
};

class ComparatorError : public SentinelError {
public:
    explicit ComparatorError(std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : SentinelError("COMPARATOR_ERROR", std::move(message), std::move(details), std::move(loc)) {}
};

class EvidenceError : public SentinelError {
public:
    explicit EvidenceError(std::string message, std::string details = "", std::optional<SourceLocation> loc = std::nullopt)
        : SentinelError("EVIDENCE_ERROR", std::move(message), std::move(details), std::move(loc)) {}
};

} // namespace sentinel
