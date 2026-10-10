# HonAero Sentinel — Isolated Execution Worker

The execution worker runs C/C++ compilation and verification test execution in an isolated sandbox or container.

## Security Constraints
- Never executes code in the primary API process.
- Strictly bounds execution timeout (configurable).
- Redirects and captures stdout/stderr and exit codes.
- Hashes and indexes generated artifacts (binaries, .gcno, .gcda, logs).
