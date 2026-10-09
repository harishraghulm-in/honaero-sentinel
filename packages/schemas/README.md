# HonAero Sentinel — Shared Verification Schemas

This directory defines the stable machine-readable contracts between the **Verification Core (C++20)**, **Backend API (Python FastAPI)**, **Execution Worker**, and **Frontend (React/TypeScript)**.

All schemas adhere to Draft 2020-12 of JSON Schema.

---

## 1. Schema Catalog

| Schema | File | Producer | Consumer | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `AnalysisResult` | `AnalysisResult.schema.json` | C++ Verification Core | Backend API, Frontend | AST subprogram, parameter, and decision extraction |
| `DependencyGraph` | `DependencyGraph.schema.json` | C++ Verification Core | Backend API, Frontend | Call graph with real/stub classification |
| `HarnessRequest` | `HarnessRequest.schema.json` | Backend API / User | C++ Verification Core | Specifications for harness, stubs, and vectors |
| `HarnessResult` | `HarnessResult.schema.json` | C++ Verification Core | Backend API, Execution Worker | Generated C/C++ files manifest and SHA-256 |
| `CoverageResult` | `CoverageResult.schema.json` | Coverage Worker | Backend API, Frontend | GCOV statement, line, and branch coverage |
| `MCDCResult` | `MCDCResult.schema.json` | C++ Verification Core | Backend API, Frontend | MC/DC condition independence & Gap Advisor |
| `TraceabilityGraph` | `TraceabilityGraph.schema.json` | C++ Verification Core | Backend API, Frontend | Full trace from Requirement to Evidence |
| `EvidenceRecord` | `EvidenceRecord.schema.json` | C++ Verification Core | Backend API, Regulatory Audit | Cryptographically locked verification record |
| `VerificationCapsule`| `VerificationCapsule.schema.json`| C++ Verification Core | External Auditors / Archive | Hermetic audit bundle with tamper-evident hash |

---

## 2. Specification & Example Payloads

### `AnalysisResult`
- **Purpose**: Output of the Clang/AST analysis engine. Exposes free functions, signatures, parameters, decisions, and external calls without leaking Clang internal memory models.
- **Key Fields**:
  - `functions[]`: List of parsed functions.
    - `id`: Unique identifier (`fn_cabin_pressure_control`).
    - `name`: Subprogram identifier.
    - `return_type`: Return type string.
    - `parameters[]`: Typed parameter list.
    - `decisions[]`: Logical expressions (`pressure > 900 && altitude < 10000`) and decomposed atomic conditions (`C1`, `C2`).
  - `dependencies[]`: Directly called functions classified as `REAL` or `STUB`.
- **Example JSON**:
```json
{
  "project_id": "proj_001",
  "source_file": "cabin_pressure.c",
  "total_sources": 1,
  "functions": [
    {
      "id": "fn_cabin_pressure_control",
      "name": "cabin_pressure_control",
      "return_type": "int",
      "is_target_under_test": true,
      "parameters": [
        {"name": "pressure", "type": "int", "is_pointer": false, "is_array": false},
        {"name": "altitude", "type": "int", "is_pointer": false, "is_array": false}
      ],
      "decisions": [
        {
          "id": "D1",
          "expression": "pressure > 900 && altitude < 10000 && sensor_val > 900",
          "line_number": 8,
          "conditions": [
            {"id": "C1", "expression": "pressure > 900", "variable_references": ["pressure"]},
            {"id": "C2", "expression": "altitude < 10000", "variable_references": ["altitude"]},
            {"id": "C3", "expression": "sensor_val > 900", "variable_references": ["sensor_val"]}
          ]
        }
      ]
    }
  ],
  "dependencies": [
    {"id": "dep_sensor_read", "name": "sensor_read", "classification": "STUB"},
    {"id": "dep_valve_actuate", "name": "valve_actuate", "classification": "STUB"}
  ]
}
```

---

### `CoverageResult`
- **Purpose**: Canonical structure containing metrics parsed from GCOV/LLVM coverage outputs.
- **Key Fields**:
  - `statement_coverage_pct`: Percentage of executed statements [0.0 - 100.0].
  - `branch_coverage_pct`: Percentage of evaluated branches [0.0 - 100.0].
  - `total_lines` / `covered_lines`: Raw line counts.
  - `total_branches` / `covered_branches`: Raw branch counts.
  - `uncovered_lines[]`: Line numbers that were never hit.
- **Example JSON**:
```json
{
  "execution_id": "exec_001",
  "source_file": "cabin_pressure.c",
  "statement_coverage_pct": 100.0,
  "branch_coverage_pct": 83.33,
  "function_coverage_pct": 100.0,
  "line_coverage_pct": 100.0,
  "total_lines": 8,
  "covered_lines": 8,
  "total_branches": 6,
  "covered_branches": 5,
  "uncovered_lines": []
}
```

---

### `MCDCResult`
- **Purpose**: Output of the deterministic MC/DC evaluator, demonstrating condition independence pairs and synthesising deterministic candidate vectors for coverage gaps.
- **Key Fields**:
  - `coverage_percentage`: MC/DC coverage [0.0 - 100.0].
  - `full_mcdc_achieved`: Boolean indicating 100% independence compliance.
  - `decisions[]`: Decision breakdown with proven pairs.
  - `gap_recommendations[]`: Gap advisor candidate vectors labeled explicitly as `CANDIDATE VECTOR`.
- **Example JSON**:
```json
{
  "execution_id": "exec_001",
  "coverage_percentage": 100.0,
  "full_mcdc_achieved": true,
  "decisions": [
    {
      "decision_id": "D1",
      "expression": "pressure > 900 && altitude < 10000 && sensor_val > 900",
      "mcdc_achieved": true,
      "coverage_pct": 100.0,
      "total_conditions": 3,
      "covered_conditions": 3,
      "independence_pairs": [
        {
          "condition_id": "C1",
          "true_vector_index": 1,
          "false_vector_index": 2,
          "explanation": "Independence proven: C1 toggles TRUE (TC-1) to FALSE (TC-2) altering decision outcome."
        }
      ],
      "conditions": [
        {"id": "C1", "independence_proven": true, "independence_pair": "TC-1 vs TC-2"}
      ]
    }
  ],
  "gap_recommendations": []
}
```

---

### `EvidenceRecord`
- **Purpose**: Cryptographically sealed verification evidence. Contains hashes of source, stubs, and vectors without timestamps to guarantee reproducible checksums.
- **Freshness States**:
  - `CURRENT`: Source and test vectors match cryptographic hashes.
  - `STALE`: Source code, stubs, or test vectors modified after verification run.
  - `INVALIDATED`: Underlying files removed or corrupted.
- **Example JSON**:
```json
{
  "evidence_id": "evid_exec_001",
  "project_id": "proj_001",
  "execution_id": "exec_001",
  "target_function": "cabin_pressure_control",
  "timestamp": "2026-10-09T06:00:00Z",
  "tool_version": "1.0.0",
  "source_checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "stub_checksum": "a79c3d...",
  "vector_checksum": "8b1a4f...",
  "freshness": "CURRENT",
  "freshness_reason": "Evidence is fresh and cryptographically verified against current source.",
  "compiler": "gcc",
  "compiler_version": "11.4.0",
  "build_status": "PASSED",
  "execution_status": "PASSED"
}
```
