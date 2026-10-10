# HonAero Sentinel — Isolated Execution Architecture

## 1. Security Isolation Policy
Executing untrusted, user-provided C/C++ code inside the API process is strictly prohibited. Sentinel executes all builds and tests inside isolated runner environments:

1. **LocalProcessExecutionEngine**:
   - Creates a dedicated, non-shared workspace directory per execution (`workspaces/<execution_id>`).
   - Compiles code with GCC with `--coverage -fprofile-arcs -ftest-coverage`.
   - Executes via an isolated worker process with:
     - Configurable execution timeout (default 10s).
     - Standard input closed, standard output and error redirected to disk logs.
     - Strict exit code verification.
   - On Windows, compiles native machine code as dynamic library and runs through an isolated Python runner worker to operate seamlessly within Windows App Control / WDAC policies.

2. **LocalDockerExecutionEngine (Production Mode)**:
   - Mounts the isolated workspace into a locked container `honaero-sentinel/execution-worker`.
   - Runs with `--cap-drop=ALL --network none --read-only`.
   - Memory capped at 512MB, CPU capped at 1.0 cores.

## 2. Execution Lifecyle
```
QUEUED → BUILDING → RUNNING → [PASSED | FAILED | TIMEOUT | BUILD_FAILED | ERROR]
```

## 3. Artifact Capture
All generated artifacts are hashed (SHA-256) and tracked in `execution_artifacts`:
- Executable/Library binary
- Compiler `.gcno` and runtime `.gcda` files
- `stdout.log` and `stderr.log`
- Machine-readable `sentinel_result.json`

