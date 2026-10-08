# HonAero Sentinel — System Architecture

## 1. Architectural Principles
HonAero Sentinel is built to serve safety-critical aerospace software verification inspired by DO-178C Level A/B guidelines.
It operates as a layered verification platform:

```
[ Frontend: React + TypeScript UI ]
                 ↓ REST API (OpenAPI v3)
[ Presentation & Router Layer: FastAPI ]
                 ↓ Domain Interfaces & Dependency Injection
[ Application Services: Harness, Stubs, MCDC, Traceability, Evidence ]
                 ↓ Domain Models & Repositories
[ Persistence: PostgreSQL 16+ & SQLAlchemy 2.0 ]
                 ↓ Infrastructure Isolation
[ Verification Core: Clang/AST Parser, GCC/Clang Toolchains, GCOV, Process Worker ]
```

## 2. Layered Structure
- **`apps/api/app/api/`**: Thin REST endpoints validating requests and returning strongly typed Pydantic DTOs.
- **`apps/api/app/application/services/`**: Pure verification logic:
  - `StubGeneratorService`: Generates deterministic C stubs with call-counting and successive returns.
  - `HarnessGeneratorService`: Generates self-contained C test harnesses with setup/teardown and hooks.
  - `MCDCAnalyzerService`: Evaluates condition independence and synthesizes gap advisor recommendations.
  - `EvidenceService`: Creates immutable cryptographic evidence records with freshness detection.
  - `TraceabilityService`: Builds requirement-to-evidence graphs.
- **`apps/api/app/domain/`**: SQLAlchemy 2.x models, status enums, and parser/compiler interfaces.
- **`apps/api/app/infrastructure/`**: Isolated execution runners, GccCompilerProvider, GcovCoverageProvider, and database engine.

## 3. Database Schema
Managed via Alembic revisions. Entities supported:
- `projects`, `source_files`, `build_configurations`, `requirements`
- `functions`, `dependencies`, `stub_configurations`, `user_hooks`
- `test_suites`, `test_cases`, `test_vectors`
- `executions`, `execution_artifacts`, `coverage_results`, `mcdc_results`
- `traceability_links`, `evidence_records`

