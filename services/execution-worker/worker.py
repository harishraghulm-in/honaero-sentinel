"""
HonAero Sentinel — Isolated Execution Worker Service
Responsible for sandboxed compilation and execution of C/C++ harnesses.
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from apps.api.app.infrastructure.execution.process_engine import LocalProcessExecutionEngine
from apps.api.app.infrastructure.execution.interface import ExecutionRequest


def run_worker_task(payload_path: Path) -> int:
    """Reads execution payload JSON, executes in isolation, and outputs result JSON."""
    if not payload_path.exists():
        sys.stderr.write(f"Task payload not found at {payload_path}\n")
        return 1

    data = json.loads(payload_path.read_text(encoding="utf-8"))
    req = ExecutionRequest(**data)

    engine = LocalProcessExecutionEngine()
    result = engine.execute(req)

    out_file = Path(result.workspace_dir) / "worker_output.json"
    out_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"[Worker] Execution {result.execution_id} completed with status: {result.status.value}")
    return 0 if result.status.value == "PASSED" else 1


def main():
    parser = argparse.ArgumentParser(description="Sentinel Isolated Execution Worker")
    parser.add_argument("--payload", type=Path, required=True, help="Path to execution payload JSON file")
    args = parser.parse_args()
    code = run_worker_task(args.payload)
    sys.exit(code)


if __name__ == "__main__":
    main()
