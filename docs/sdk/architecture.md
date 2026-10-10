# HonAero Sentinel — Verification Core SDK Architecture

The **Sentinel Verification Core** is the high-assurance C++20 intelligence layer powering the Smart Verification Studio. It performs deterministic static analysis, test harness generation, coverage computation, MC/DC condition independence evaluation, and cryptographic evidence sealing.

---

## 1. Subsystem Decomposition

```text
sdk/
├── include/sentinel/
│   ├── analysis/       --> Clang AST analysis & subprogram extraction
│   ├── model/          --> Canonical domain models (serializable to JSON)
│   ├── dependency/     --> Call graph & stub/real isolation map
│   ├── harness/        --> Deterministic C harness & stub generator
│   ├── comparator/     --> Prototype scalar and structured comparators
│   ├── compiler/       --> Compiler abstraction (GCC, Clang, Cross-toolchains)
│   ├── coverage/       --> GCOV and LLVM coverage artifact parsers
│   ├── mcdc/           --> AST boolean expression tree, truth table, and gap advisor
│   ├── traceability/   --> Requirement -> Function -> Test -> Evidence graph
│   ├── evidence/       --> SHA-256 evidence record and freshness evaluator
│   ├── capsule/        --> Hermetic audit verification capsule packager
│   └── common/         --> ProcessRunner, SourceLocation, Errors, json.hpp
└── src/
    └── cli/            --> sentinel CLI executable
```

---

## 2. Supported Language Scope

Aligned with high-assurance aerospace verification (DO-178C workflow alignment):
- **C Language Standard**: C89, C99, C11, C17.
- **Language Constructs**:
  - Free functions with return types (`int`, `void`, `float`, `double`, `bool`, primitives, pointers).
  - Explicit parameter lists (primitives, pointers `*`, arrays `[]`).
  - Local variable declarations and initializers.
  - Branching control flow: `if`, `else`, compound expressions (`&&`, `||`, `!`).
  - Comparison expressions (`>`, `<`, `==`, `!=`, `>=`, `<=`).
  - Function invocations (`CallExpr`) recorded for dependency stubbing.
  - Return statements with expressions.
- **Explicitly Rejected Constructs**:
  - C++ templates, exception handling, multiple inheritance, goto statements, dynamic runtime eval.
  - Any unsupported syntax raises `UnsupportedConstructError` with exact `SourceLocation` (file, line, column). Silent fallbacks or fake parsing are strictly prohibited.

---

## 3. Toolchain Abstraction

- **Compilers**: `ICompilerProvider` interface implemented by `GccCompilerProvider`. Invokes compiler directly via process argument vectors without shell evaluation (`CreateProcess` on Windows, `posix_spawnp`/`fork`+`execvp` on POSIX).
- **Coverage**: `ICoverageProvider` implemented by `GcovCoverageProvider`. Reads real `.gcno`, `.gcda`, and `.gcov` artifacts.
- **Comparators**: `IComparator` implemented by `ScalarComparator` (absolute tolerance $10^{-6}$, relative tolerance $10^{-5}$) and `StructuredComparator`.
  *Note: Prototype comparators are designed for verification alignment and are not DO-178C qualified.*
