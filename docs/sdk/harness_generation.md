# HonAero Sentinel — Deterministic Test Harness Generator

The Test Harness Generator synthesizes inspectable and editable C/C++ code for unit verification.

---

## 1. Generated Artifacts

Executing `HarnessGenerator::generate()` creates four distinct files in the output directory:

```text
generated/
├── stubs.h           --> Function prototypes and sentinel stub reset declarations
├── stubs.cpp         --> Deterministic stub state variables and implementations
├── test_vectors.cpp  --> Test vector data structures and input tables
└── harness.cpp       --> Main execution runner with 10-step lifecycle
```

All generated files are strictly plain C/C++ source code, fully inspectable by verification engineers and regulatory auditors.

---

## 2. The 10-Step Harness Lifecycle

Every test harness adheres to this execution sequence:

1. **Setup Hook**: Executes global initialization logic (`UserHooks::setup_code`).
2. **Configure Stubs**: Resets invocation counters via `sentinel_reset_stubs()`.
3. **Before-Test Hook**: Runs setup specific to the impending vector.
4. **Call Target**: Invokes the unit under test (`actual = target_fn(...)`).
5. **Capture Output**: Captures return values and out-parameters.
6. **Compare Output**: Evaluates `actual == expected`.
7. **Record Result**: Emits structured JSON result block for vector.
8. **After-Test Hook**: Runs vector cleanup logic.
9. **Teardown Hook**: Executes global test suite teardown.
10. **Emit Summary**: Emits machine-readable JSON summary and exits with non-zero if failures occurred.
