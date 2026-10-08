# HonAero Sentinel — API Contract Specification

**Version:** 1.0.0  
**Base Path:** `/api/v1`  
**Protocol:** REST / JSON  
**Target Consumers:** React + TypeScript Frontend, Automated CI/CD Pipelines

---

## 1. Health & Readiness Probes

### `GET /health`
Liveness probe.
- **Response `200 OK`**:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-10-08T14:00:00Z"
}
```

### `GET /ready`
Readiness probe checking database connectivity and compiler toolchains.
- **Response `200 OK`**:
```json
{
  "status": "ready",
  "database": true,
  "toolchains": {
    "gcc": {
      "name": "gcc",
      "available": true,
      "path": "C:\\msys64\\ucrt64\\bin\\gcc.exe",
      "version": "gcc.exe 16.1.0"
    },
    "gcov": {
      "name": "gcov",
      "available": true,
      "path": "C:\\msys64\\ucrt64\\bin\\gcov.exe",
      "version": "gcov 16.1.0"
    }
  },
  "details": {
    "execution_engine": "local_process",
    "workspace_base": "workspaces",
    "artifact_storage": "storage/artifacts"
  }
}
```

---

## 2. Project Management

### `POST /api/v1/projects`
Create a new verification studio project.
- **Request Body**:
```json
{
  "name": "Cabin Pressure Controller",
  "description": "DO-178C Verification Target"
}
```
- **Response `201 Created`**:
```json
{
  "id": "uuid-v4",
  "name": "Cabin Pressure Controller",
  "description": "DO-178C Verification Target",
  "created_at": "2026-10-08T14:00:00Z",
  "updated_at": "2026-10-08T14:00:00Z"
}
```

### `GET /api/v1/projects`
List all projects.

### `GET /api/v1/projects/{project_id}`
Retrieve a project by ID.

### `DELETE /api/v1/projects/{project_id}`
Delete a project and all associated verification artifacts.

---

## 3. Source Code Management

### `POST /api/v1/projects/{project_id}/sources`
Upload/import a C or C++ source file.
- **Request Body**:
```json
{
  "filename": "cabin_pressure.c",
  "filepath": "src/cabin_pressure.c",
  "content": "int cabin_pressure_control(...) { ... }",
  "is_target": true,
  "is_environment": false
}
```
- **Response `201 Created`**:
```json
{
  "id": "source-uuid",
  "project_id": "project-uuid",
  "filename": "cabin_pressure.c",
  "filepath": "src/cabin_pressure.c",
  "checksum_sha256": "64-char-sha256",
  "is_target": true,
  "is_environment": false,
  "created_at": "2026-10-08T14:00:00Z"
}
```

### `GET /api/v1/projects/{project_id}/sources`
List all source files in a project.

---

## 4. AST Source Analysis

### `POST /api/v1/projects/{project_id}/analyze`
Triggers the normalized Clang/AST analysis engine across all uploaded sources.
- **Response `200 OK`**:
```json
{
  "project_id": "uuid",
  "total_sources": 2,
  "functions": [
    {
      "id": "func-uuid",
      "name": "cabin_pressure_control",
      "return_type": "int",
      "parameters": [
        {"name": "pressure", "type": "int", "is_pointer": false, "is_array": false},
        {"name": "altitude", "type": "int", "is_pointer": false, "is_array": false}
      ],
      "decisions": [
        {
          "id": "D1",
          "expression": "pressure > 900 && altitude < 10000",
          "line_number": 8,
          "conditions": [
            {"id": "C1", "expression": "pressure > 900", "variable_references": ["pressure"]},
            {"id": "C2", "expression": "altitude < 10000", "variable_references": ["altitude"]}
          ]
        }
      ],
      "is_target_under_test": true
    }
  ],
  "dependencies": [
    {
      "id": "dep-uuid",
      "name": "sensor_read",
      "type": "external_function",
      "return_type": "int",
      "mode": "REAL"
    }
  ]
}
```

---

## 5. Scope Selection

### `POST /api/v1/projects/{project_id}/scope`
Set the target subprogram and environment files.
- **Request Body**:
```json
{
  "target_function_id": "func-uuid",
  "target_source_id": "source-uuid",
  "environment_source_ids": ["env-source-uuid"]
}
```

---

## 6. Stubs & Dependency Isolation

### `GET /api/v1/projects/{project_id}/dependencies`
List detected dependencies with their current `REAL` or `STUB` modes.

### `POST /api/v1/projects/{project_id}/stubs`
Configure deterministic stub behavior for an external dependency.
- **Request Body**:
```json
{
  "dependency_id": "dep-uuid",
  "function_name": "sensor_read",
  "mode": "STUB",
  "return_values": [950, 945, 960],
  "output_params": {},
  "expected_call_count": 3
}
```

---

## 7. Test Authoring

### `POST /api/v1/projects/{project_id}/test-cases`
Create test case with test vectors.
- **Request Body**:
```json
{
  "name": "TC-001 Overpressure Vector",
  "target_function_id": "func-uuid",
  "requirement_id": "req-uuid",
  "vectors": [
    {
      "vector_index": 1,
      "inputs": {"pressure": 950, "altitude": 8000},
      "expected_outputs": {"return": 1}
    }
  ]
}
```

---

## 8. Build & Execution

### `POST /api/v1/projects/{project_id}/executions`
Generates test harness, links stubs, compiles with GCC, and executes in isolated process.
- **Request Body**:
```json
{
  "test_case_id": "tc-uuid",
  "timeout_seconds": 10
}
```
- **Response `201 Created`**:
```json
{
  "execution_id": "exec-uuid",
  "project_id": "project-uuid",
  "test_case_id": "tc-uuid",
  "status": "PASSED",
  "exit_code": 0,
  "duration_ms": 716.31,
  "results_summary": {
    "status": "PASSED",
    "passed_count": 4,
    "failed_count": 0
  },
  "created_at": "2026-10-08T14:00:00Z"
}
```

---

## 9. Coverage & MC/DC

### `GET /api/v1/projects/{project_id}/executions/{execution_id}/coverage`
Returns statement, branch, and line coverage metrics parsed from GCOV.

### `GET /api/v1/projects/{project_id}/executions/{execution_id}/mcdc`
Returns condition independence results and Gap Advisor recommendations.

---

## 10. Traceability & Evidence

### `GET /api/v1/projects/{project_id}/traceability`
Returns the complete `Requirement -> Function -> TestCase -> Execution -> Coverage -> Evidence` graph.

### `GET /api/v1/projects/{project_id}/executions/{execution_id}/evidence`
Retrieves the immutable evidence record with fresh cryptographic checksum evaluation (`CURRENT` vs `STALE`).

### `POST /api/v1/projects/{project_id}/executions/{execution_id}/evidence/export`
Exports evidence in `json` or `md` format.

