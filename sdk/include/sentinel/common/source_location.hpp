#pragma once

#include <string>
#include "sentinel/common/json.hpp"

namespace sentinel {

struct SourceLocation {
    std::string file;
    int line{0};
    int column{0};

    bool isValid() const noexcept {
        return !file.empty() && line > 0;
    }

    bool operator==(const SourceLocation& other) const noexcept {
        return file == other.file && line == other.line && column == other.column;
    }

    nlohmann::json toJson() const {
        return {
            {"file", file},
            {"line", line},
            {"column", column}
        };
    }

    static SourceLocation fromJson(const nlohmann::json& j) {
        SourceLocation loc;
        if (j.contains("file") && j["file"].is_string()) loc.file = j["file"].get<std::string>();
        if (j.contains("line") && j["line"].is_number()) loc.line = j["line"].get<int>();
        if (j.contains("column") && j["column"].is_number()) loc.column = j["column"].get<int>();
        return loc;
    }
};

inline void to_json(nlohmann::json& j, const SourceLocation& loc) {
    j = loc.toJson();
}

inline void from_json(const nlohmann::json& j, SourceLocation& loc) {
    loc = SourceLocation::fromJson(j);
}

} // namespace sentinel
