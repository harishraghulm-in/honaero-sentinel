# HonAero Sentinel — Verification Core Architectural Integration

This document defines the integration boundaries between the Verification Core (C++20), the Backend API (Python FastAPI), and the Frontend (React/TypeScript).

---

## 1. System Responsibility Matrix

| Subsystem | Technology | Primary Responsibilities |
| :--- | :--- | :--- |
| **Frontend** | React, TypeScript, Monaco, Tailwind | Verification studio UX, AST decision inspection, Monaco code editing, test vector authoring, evidence reports. |
| **Backend** | Python, FastAPI, PostgreSQL, SQLAlchemy | REST API, database persistence, job orchestration, project lifecycle, execution management. |
| **Verification Core** | C++20, Clang AST, GCC/gcov, SHA-256 | Clang AST parsing, subprogram/decision extraction, deterministic harness generation, MC/DC engine, coverage parsing, cryptographic evidence sealing. |

---

## 2. Integration Protocol

The Backend interacts with the Verification Core either by:
1. **Direct Process Invocation**: Calling the `sentinel` CLI binary via standard process argument vectors (`subprocess.run(["sentinel", "analyze", ...])`).
2. **Coverage Worker Service**: Invoking `sentinel-coverage-worker` to parse `.gcov` artifacts into `CoverageResult` JSON.
3. **Shared Schemas**: All data exchanges conform strictly to the schemas defined in `packages/schemas/`.
