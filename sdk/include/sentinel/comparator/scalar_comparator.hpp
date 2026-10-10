#pragma once

#include "sentinel/comparator/comparator_interface.hpp"

namespace sentinel {

class ScalarComparator : public IComparator {
public:
    explicit ScalarComparator(double abs_tol = 1e-6, double rel_tol = 1e-5);
    ~ScalarComparator() override = default;

    ComparisonResult compare(const nlohmann::json& actual, const nlohmann::json& expected) const override;
    std::string name() const noexcept override { return "prototype scalar comparator"; }

private:
    double abs_tol_;
    double rel_tol_;
};

class StructuredComparator : public IComparator {
public:
    explicit StructuredComparator(std::shared_ptr<IComparator> leaf_comparator = nullptr);
    ~StructuredComparator() override = default;

    ComparisonResult compare(const nlohmann::json& actual, const nlohmann::json& expected) const override;
    std::string name() const noexcept override { return "prototype structured comparator"; }

private:
    std::shared_ptr<IComparator> leaf_comparator_;
};

// Design for future DO-178C qualification
class QualifiedComparatorAdapter : public IComparator {
public:
    explicit QualifiedComparatorAdapter(std::shared_ptr<IComparator> underlying);
    ComparisonResult compare(const nlohmann::json& actual, const nlohmann::json& expected) const override;
    std::string name() const noexcept override { return "qualified comparator adapter (prototype stub)"; }

private:
    std::shared_ptr<IComparator> underlying_;
};

} // namespace sentinel
