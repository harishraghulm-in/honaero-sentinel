# HonAero Sentinel — MC/DC Analysis & Gap Advisor

## 1. Background: DO-178C MC/DC Requirements
In DO-178C Level A software verification, Modified Condition / Decision Coverage (MC/DC) requires demonstrating that:
1. Every decision has taken all possible outcomes (True and False).
2. Every condition in a decision has taken all possible outcomes (True and False).
3. Each condition has been shown to independently affect the decision's outcome.

To prove independence for condition $C_i$, Sentinel identifies an **Independence Pair** $(T_a, T_b)$ such that:
- Condition $C_i$ flips truth value between $T_a$ and $T_b$.
- All other conditions in the decision either remain unchanged (Unique Cause) or are masked.
- The overall decision outcome flips.

## 2. Deterministic Analysis Engine
The `MCDCAnalyzerService` evaluates conditions against the executed test vector matrix without guessing or stochastic sampling.
Outputs:
- Condition status: `PROVEN`, `NOT_PROVEN`, or `UNTESTED`.
- Independence pair indices: e.g. `[1, 2]`.
- Decision-level and overall project MC/DC coverage percentages.

## 3. MC/DC Gap Advisor (Candidate Vector Generator)
When a condition's independence is `NOT_PROVEN`, the Gap Advisor analyzes the condition truth table to discover missing independence effects.

Example:
For decision `pressure > 900 && altitude < 10000 && sensor_val > 900`:
If existing tests lack an independence effect for `sensor_val`, the Gap Advisor computes the missing truth assignment:
```json
{
  "condition_id": "C3",
  "status": "NOT_PROVEN",
  "rationale": "Condition C3 (sensor_val > 900) requires an independent condition effect pair...",
  "recommended_truth_assignment": {
    "C1": true,
    "C2": true,
    "C3": false
  },
  "candidate_test_vector_inputs": {
    "pressure": 950,
    "altitude": 8000,
    "sensor_val": 850
  },
  "disclaimer": "Candidate vector advisory only. DO-178C verification requires engineering review and qualification."
}
```
> **Notice:** Gap recommendations are explicitly designated as candidate test vectors for engineering review, never claimed as pre-certified evidence.

