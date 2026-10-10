# HonAero Sentinel — MC/DC Engine & Gap Advisor

Modified Condition/Decision Coverage (MC/DC) is a structural coverage criterion required for DO-178C Level A avionics software.

---

## 1. Mathematical Definition of Independence

For a boolean decision $D = C_1 \land C_2 \land \dots \land C_n$, a condition $C_k$ is proven to affect the outcome independently if and only if there exist two test cases $T_A$ and $T_B$ such that:
1. $C_k(T_A) \ne C_k(T_B)$ (condition toggles between True and False).
2. $D(T_A) \ne D(T_B)$ (decision outcome changes).
3. For all other conditions $C_j$ ($j \ne k$): $C_j(T_A) = C_j(T_B)$ (all other enabling conditions held constant, or in Masking MC/DC, any difference in $C_j$ is masked by the boolean operator).

---

## 2. Independence Pair Detection

For Decision $D = A \land B$:

| Vector | A | B | Decision Outcome | Proves Independence For |
| :--- | :--- | :--- | :--- | :--- |
| **TC-1** | **True** | **True** | **True** | Benchmark vector |
| **TC-2** | **False** | True | False | Condition A (Pair: TC-1 vs TC-2) |
| **TC-3** | True | **False** | False | Condition B (Pair: TC-1 vs TC-3) |

Total test cases required: $N + 1 = 3$ test cases for $N = 2$ atomic conditions.

---

## 3. MC/DC Gap Advisor

When an atomic condition lacks an independence pair in the current test suite, the Gap Advisor identifies the missing truth transition and synthesizes deterministic candidate input values.

- **Deterministic Value Synthesis**:
  - Relational expression $x > 900$:
    - $\text{True} \to 950$
    - $\text{False} \to 850$
  - Relational expression $y < 10000$:
    - $\text{True} \to 5000$
    - $\text{False} \to 12000$
- **Mandatory Labeling**:
  All suggested test vectors are explicitly marked with the label:
  ```text
  "label": "CANDIDATE VECTOR"
  ```
  The label `CERTIFIED VECTOR` is strictly prohibited, as human verification engineer review and qualification are required.
