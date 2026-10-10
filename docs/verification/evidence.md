# HonAero Sentinel — Evidence Records & Freshness Tracking

## 1. Immutable Evidence Records
Verification evidence in aerospace engineering must be repeatable and auditable. Every execution in HonAero Sentinel generates an immutable `EvidenceRecord` containing:
- Project ID & execution UUID
- Source files list & SHA-256 cryptographic hashes
- Compiler name, version, and exact compiler flags
- Stub configurations and return values
- Test vectors (inputs, expected outputs, actual outputs)
- Statement, branch, and line coverage percentages
- MC/DC independence analysis matrix
- Execution stdout, stderr, exit code, and timestamps
- Toolchain version ("HonAero Sentinel Verification Studio v1.0.0")

## 2. Dynamic Evidence Freshness (CURRENT vs STALE)
A core capability of Sentinel is cryptographic freshness tracking:
1. When an execution completes, the exact SHA-256 hash of all source files and stub configurations is recorded into the evidence record.
2. If an engineer later modifies the source code, updates a stub return value, or re-scopes the project:
   - The system re-hashes the current source tree.
   - Sentinel compares the current hash against the evidence record's stored hash.
   - If they differ, the evidence record is marked **`STALE`**.
   - If they match, the evidence record remains **`CURRENT`**.
3. Previous evidence records are **never deleted**, preserving the historical audit trail required by certification authorities.

## 3. Evidence Export
Evidence can be exported via:
- Machine-readable JSON: `POST /api/v1/projects/{project_id}/executions/{execution_id}/evidence/export?format=json`
- Human-reviewable Markdown/Report: `POST /api/v1/projects/{project_id}/executions/{execution_id}/evidence/export?format=md`

