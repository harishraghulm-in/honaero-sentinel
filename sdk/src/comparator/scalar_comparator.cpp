#include "sentinel/comparator/scalar_comparator.hpp"
#include <cmath>
#include <sstream>

namespace sentinel {

ScalarComparator::ScalarComparator(double abs_tol, double rel_tol)
    : abs_tol_(abs_tol), rel_tol_(rel_tol) {}

ComparisonResult ScalarComparator::compare(const nlohmann::json& actual, const nlohmann::json& expected) const {
    ComparisonResult res;
    res.comparator_type = name();

    if (actual.is_number_float() || expected.is_number_float()) {
        double act = actual.get<double>();
        double exp = expected.get<double>();
        double abs_diff = std::abs(act - exp);
        double max_mag = std::max(std::abs(act), std::abs(exp));
        double rel_diff = (max_mag > 0.0) ? (abs_diff / max_mag) : 0.0;

        res.measured_absolute_error = abs_diff;
        res.measured_relative_error = rel_diff;

        if (abs_diff <= abs_tol_ || rel_diff <= rel_tol_) {
            res.passed = true;
        } else {
            res.passed = false;
            std::ostringstream oss;
            oss << "Floating point mismatch: actual=" << act << ", expected=" << exp
                << ", abs_diff=" << abs_diff << " (tol=" << abs_tol_ << "), rel_diff=" << rel_diff;
            res.difference_description = oss.str();
        }
        return res;
    }

    if (actual.is_number_integer() && expected.is_number_integer()) {
        int64_t act = actual.get<int64_t>();
        int64_t exp = expected.get<int64_t>();
        if (act == exp) {
            res.passed = true;
        } else {
            res.passed = false;
            res.difference_description = "Integer mismatch: actual=" + std::to_string(act) + ", expected=" + std::to_string(exp);
        }
        return res;
    }

    if (actual.is_boolean() && expected.is_boolean()) {
        bool act = actual.get<bool>();
        bool exp = expected.get<bool>();
        if (act == exp) {
            res.passed = true;
        } else {
            res.passed = false;
            res.difference_description = std::string("Boolean mismatch: actual=") + (act ? "true" : "false") + ", expected=" + (exp ? "true" : "false");
        }
        return res;
    }

    if (actual.is_string() && expected.is_string()) {
        std::string act = actual.get<std::string>();
        std::string exp = expected.get<std::string>();
        if (act == exp) {
            res.passed = true;
        } else {
            res.passed = false;
            res.difference_description = "String mismatch: actual=\"" + act + "\", expected=\"" + exp + "\"";
        }
        return res;
    }

    if (actual == expected) {
        res.passed = true;
    } else {
        res.passed = false;
        res.difference_description = "Type or value mismatch: actual=" + actual.dump() + ", expected=" + expected.dump();
    }
    return res;
}

StructuredComparator::StructuredComparator(std::shared_ptr<IComparator> leaf_comparator)
    : leaf_comparator_(leaf_comparator ? leaf_comparator : std::make_shared<ScalarComparator>()) {}

ComparisonResult StructuredComparator::compare(const nlohmann::json& actual, const nlohmann::json& expected) const {
    ComparisonResult res;
    res.comparator_type = name();

    if (actual.is_array() && expected.is_array()) {
        if (actual.size() != expected.size()) {
            res.passed = false;
            res.difference_description = "Array length mismatch: actual size " + std::to_string(actual.size()) + ", expected size " + std::to_string(expected.size());
            return res;
        }
        for (size_t i = 0; i < actual.size(); ++i) {
            auto sub = compare(actual[i], expected[i]);
            if (!sub.passed) {
                res.passed = false;
                res.difference_description = "Array index [" + std::to_string(i) + "] mismatch: " + sub.difference_description;
                return res;
            }
        }
        res.passed = true;
        return res;
    }

    if (actual.is_object() && expected.is_object()) {
        for (auto it = expected.begin(); it != expected.end(); ++it) {
            const std::string& key = it.key();
            if (!actual.contains(key)) {
                res.passed = false;
                res.difference_description = "Missing expected struct/object key: " + key;
                return res;
            }
            auto sub = compare(actual[key], it.value());
            if (!sub.passed) {
                res.passed = false;
                res.difference_description = "Key '" + key + "' mismatch: " + sub.difference_description;
                return res;
            }
        }
        res.passed = true;
        return res;
    }

    return leaf_comparator_->compare(actual, expected);
}

QualifiedComparatorAdapter::QualifiedComparatorAdapter(std::shared_ptr<IComparator> underlying)
    : underlying_(std::move(underlying)) {}

ComparisonResult QualifiedComparatorAdapter::compare(const nlohmann::json& actual, const nlohmann::json& expected) const {
    if (!underlying_) {
        ComparisonResult r;
        r.passed = false;
        r.difference_description = "Underlying comparator not configured";
        return r;
    }
    auto r = underlying_->compare(actual, expected);
    r.comparator_type = name();
    return r;
}

} // namespace sentinel
