# HonAero Sentinel — Smart Verification Studio

HonAero Sentinel is a mission-critical DO-178C smart verification studio integrating a deterministic C++20 verification core, an isolated compilation and execution engine with real GCC and GCOV coverage, a FastAPI backend with full run history and regression tracking, and a modern React/TypeScript/Vite IDE interface.

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Smart Verification Studio                   │
│             (React 18 + TypeScript + Vite)                  │
│       Panes: Explorer, Analysis, Tests, Runs, Coverage      │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON REST
┌──────────────────────────────▼──────────────────────────────┐
│                  FastAPI Backend Server                     │
│  - SQLite Database Persistence & Historical Test Run Audit  │
│  - Real-time Traceability, MC/DC, and Evidence Services     │
│  - Optional NVIDIA NIM Advisory Assistant (DO-178C Guard)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Subprocess Execution
┌──────────────────────────────▼──────────────────────────────┐
│             C++20 Verification Engine & Worker              │
│  - sentinel-core (AST Analysis, Stubs, Deterministic Harness)│
│  - Real GCC/G++ Compiler & GCOV Coverage Collector           │
│  - MC/DC Independence Pairs & Gap Advisor Recommendations    │
│  - Hermetic SHA-256 Source Hash & Freshness Lifecycle Audit  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Integrated Git Branches

The integrated solution consolidates all active development workstreams onto `integration-dev`:
- `origin/backend-dev`: Complete FastAPI endpoints, database durability models, requirements-to-test promotion, and execution engine abstractions.
- `origin/frontend-dev`: Modern desktop-grade IDE interface under `apps/web/`, featuring sidebar panels, test authoring, Monaco-style editor, live terminal output, and coverage dashboards.
- `origin/verification-dev`: C++20 verification SDK (`sdk/`), GCOV coverage worker (`services/coverage-worker/`), and CLI tool (`sdk/bin/`).

---

## 3. Prerequisites

- **C/C++ Compiler**: GCC 11+ with `gcov` (MinGW-W64 on Windows or native GCC on Linux).
- **Build System**: CMake 3.20+ and Ninja.
- **Python**: Python 3.11+ (with `uv` recommended for virtual environment management).
- **Node.js**: Node.js 18+ and `npm`.

---

## 4. Quick Startup Guide

### A. Build the C++ Verification Engine

```bash
# Configure with Ninja and GCC
cmake -B build -G "Ninja" -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DCMAKE_BUILD_TYPE=Release

# Build sentinel library, CLI, and worker
cmake --build build

# Verify by running core verification test suite
./build/tests/verification/sentinel_tests.exe
```

### B. Start the Backend API

```bash
# Set up Python virtual environment
uv venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
uv pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy alembic pycparser httpx pytest pytest-asyncio python-docx pypdf

# Launch the FastAPI server on port 8000
python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at: `http://localhost:8000/docs`.

### C. Start the Web Frontend

```bash
cd apps/web

# Install dependencies
npm install

# Run Vitest test suite
npm test

# Start the Vite development server
npm run dev
```

The Smart Verification Studio interface will be available at: `http://localhost:5173`.

---

## 5. Key Verification Capabilities

### Explicit Deterministic Verdicts
- `PASS`: Test executed successfully, all assertions matched, exit code 0.
- `FAIL`: Execution completed but assertions did not match expected outputs.
- `ERROR`: Build failed, process crashed, or execution timed out.
- `NOT RUN`: Test vector queued or pending compilation.
- `INCONCLUSIVE`: Execution finished with indeterminate status.

### Real Toolchain Execution
- No mock results: Test harnesses are compiled with real GCC, executed in isolated workspaces, and measured with GCOV for actual Statement and Branch coverage.

### MC/DC Analysis & Gap Advisor
- Truth-table condition evaluation detecting independence pairs.
- Built-in Gap Advisor suggesting specific candidate input vectors to achieve full MC/DC.

### Source Integrity & Evidence Freshness
- Cryptographic SHA-256 hashing across all project source files.
- Real-time audit of evidence freshness: `CURRENT`, `STALE` (when source modified after test execution), or `INVALIDATED`.

### Run History & Regression Comparison
- Every verification execution is persisted with a unique execution ID, timestamps, compiler output, stdout, stderr, and exit codes.
- Historical rerun creates a new traceable execution rather than overwriting history.
- Run comparison detects verdict flips (`PASS` $\leftrightarrow$ `FAIL`) and regressions between any two historical runs.

### Optional AI Assistant (DO-178C Guarded)
- Integration with NVIDIA NIM (Llama 3.3, Nemotron) for requirement extraction, fault injection, and failure explanations.
- **Strict DO-178C Separation**: All AI responses are classified as advisory proposals and include an explicit disclaimer. AI failure does not affect the deterministic verification core.

---

## 6. Test Suite Results

All unit and integration tests across every component pass 100%:

| Component | Test Runner | Status |
|---|---|---|
| **Verification Core (C++20)** | `sentinel_tests.exe` | 10/10 test suites PASSED |
| **Backend API & Workflows** | `pytest` (Python 3.11) | 39/39 tests PASSED |
| **Frontend Web IDE** | `vitest` & `tsc` | 1/1 tests PASSED, Build clean |
| **End-to-End Workflow** | Integration Pipeline | Full DO-178C cycle verified |
