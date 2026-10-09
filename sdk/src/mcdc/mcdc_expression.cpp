#include "sentinel/mcdc/mcdc_expression.hpp"
#include <sstream>

namespace sentinel {

ConditionLeafNode::ConditionLeafNode(ConditionInfo condition)
    : condition_(std::move(condition)) {}

bool ConditionLeafNode::evaluate(const std::map<std::string, bool>& conditionValues) const {
    auto it = conditionValues.find(condition_.id);
    if (it != conditionValues.end()) {
        return it->second;
    }
    return false;
}

std::string ConditionLeafNode::toString() const {
    return condition_.id + "(" + condition_.expression + ")";
}

std::vector<std::string> ConditionLeafNode::getConditionIds() const {
    return {condition_.id};
}

BinaryOpNode::BinaryOpNode(
    BooleanOp op,
    std::shared_ptr<IExpressionNode> left,
    std::shared_ptr<IExpressionNode> right)
    : op_(op), left_(std::move(left)), right_(std::move(right)) {}

bool BinaryOpNode::evaluate(const std::map<std::string, bool>& conditionValues) const {
    bool l = left_->evaluate(conditionValues);
    bool r = right_->evaluate(conditionValues);
    if (op_ == BooleanOp::AND) {
        return l && r;
    } else if (op_ == BooleanOp::OR) {
        return l || r;
    }
    return false;
}

std::string BinaryOpNode::toString() const {
    std::string opStr = (op_ == BooleanOp::AND) ? " && " : " || ";
    return "(" + left_->toString() + opStr + right_->toString() + ")";
}

std::vector<std::string> BinaryOpNode::getConditionIds() const {
    auto leftIds = left_->getConditionIds();
    auto rightIds = right_->getConditionIds();
    leftIds.insert(leftIds.end(), rightIds.begin(), rightIds.end());
    return leftIds;
}

UnaryOpNode::UnaryOpNode(BooleanOp op, std::shared_ptr<IExpressionNode> child)
    : op_(op), child_(std::move(child)) {}

bool UnaryOpNode::evaluate(const std::map<std::string, bool>& conditionValues) const {
    bool c = child_->evaluate(conditionValues);
    if (op_ == BooleanOp::NOT) {
        return !c;
    }
    return c;
}

std::string UnaryOpNode::toString() const {
    return "!(" + child_->toString() + ")";
}

std::vector<std::string> UnaryOpNode::getConditionIds() const {
    return child_->getConditionIds();
}

std::shared_ptr<IExpressionNode> ExpressionTreeBuilder::buildFromDecision(const DecisionInfo& decision) {
    if (decision.conditions.empty()) {
        return nullptr;
    }
    if (decision.conditions.size() == 1) {
        return std::make_shared<ConditionLeafNode>(decision.conditions[0]);
    }

    // Check if the decision contains '||' or '&&'
    // Default chain is left-associative binary op
    BooleanOp op = BooleanOp::AND;
    if (decision.expression.find("||") != std::string::npos && decision.expression.find("&&") == std::string::npos) {
        op = BooleanOp::OR;
    }

    std::shared_ptr<IExpressionNode> current = std::make_shared<ConditionLeafNode>(decision.conditions[0]);
    for (size_t i = 1; i < decision.conditions.size(); ++i) {
        current = std::make_shared<BinaryOpNode>(
            op,
            current,
            std::make_shared<ConditionLeafNode>(decision.conditions[i])
        );
    }
    return current;
}

} // namespace sentinel
