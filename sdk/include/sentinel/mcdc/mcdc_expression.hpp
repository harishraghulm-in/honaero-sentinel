#pragma once

#include <string>
#include <vector>
#include <memory>
#include <map>
#include "sentinel/model/domain_models.hpp"

namespace sentinel {

enum class BooleanOp {
    AND,
    OR,
    NOT
};

class IExpressionNode {
public:
    virtual ~IExpressionNode() = default;
    virtual bool evaluate(const std::map<std::string, bool>& conditionValues) const = 0;
    virtual std::string toString() const = 0;
    virtual std::vector<std::string> getConditionIds() const = 0;
};

class ConditionLeafNode : public IExpressionNode {
public:
    explicit ConditionLeafNode(ConditionInfo condition);
    bool evaluate(const std::map<std::string, bool>& conditionValues) const override;
    std::string toString() const override;
    std::vector<std::string> getConditionIds() const override;

    const ConditionInfo& condition() const noexcept { return condition_; }

private:
    ConditionInfo condition_;
};

class BinaryOpNode : public IExpressionNode {
public:
    BinaryOpNode(BooleanOp op, std::shared_ptr<IExpressionNode> left, std::shared_ptr<IExpressionNode> right);
    bool evaluate(const std::map<std::string, bool>& conditionValues) const override;
    std::string toString() const override;
    std::vector<std::string> getConditionIds() const override;

    BooleanOp op() const noexcept { return op_; }
    const IExpressionNode& left() const noexcept { return *left_; }
    const IExpressionNode& right() const noexcept { return *right_; }

private:
    BooleanOp op_;
    std::shared_ptr<IExpressionNode> left_;
    std::shared_ptr<IExpressionNode> right_;
};

class UnaryOpNode : public IExpressionNode {
public:
    UnaryOpNode(BooleanOp op, std::shared_ptr<IExpressionNode> child);
    bool evaluate(const std::map<std::string, bool>& conditionValues) const override;
    std::string toString() const override;
    std::vector<std::string> getConditionIds() const override;

private:
    BooleanOp op_;
    std::shared_ptr<IExpressionNode> child_;
};

class ExpressionTreeBuilder {
public:
    static std::shared_ptr<IExpressionNode> buildFromDecision(const DecisionInfo& decision);
};

} // namespace sentinel
