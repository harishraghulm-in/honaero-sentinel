#pragma once

#include <string>
#include <string_view>
#include <vector>
#include <cstdint>
#include "sentinel/common/json.hpp"

namespace sentinel {

class Sha256 {
public:
    static std::string hashString(std::string_view input);
    static std::string hashBytes(const uint8_t* data, size_t length);
    static std::string hashJsonCanonical(const nlohmann::json& jsonDoc);
    static std::string hashFile(const std::string& filepath);
};

} // namespace sentinel
