#pragma once

#include <string>
#include <optional>
#include "sentinel/common/json.hpp"

namespace sentinel {

struct ComparisonResult {
    bool passed{false};
    std::string difference_description;
    double measured_relative_error{0.0};
    double measured_absolute_error{0.0};
    std::string comparator_type{"prototype comparator"};

    nlohmann::json toJson() const {
        return {
            {"passed", passed},
            {"difference_description", difference_description},
            {"measured_relative_error", measured_relative_error},
            {"measured_absolute_error", measured_absolute_error},
            {"comparator_type", comparator_type}
        };
    }
};

class IComparator {
public:
    virtual ~IComparator() = default;
    virtual ComparisonResult compare(const nlohmann::json& actual, const nlohmann::json& expected) const = 0;
    virtual std::string name() const noexcept = 0;
};

} // namespace sentinel
