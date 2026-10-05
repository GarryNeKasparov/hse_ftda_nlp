"""Run the reference-analyzer acceptance suite and snapshot its exact inputs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from time import perf_counter


def main() -> int:
    """Record one reproducible test run under logs/experiments."""
    root = Path(__file__).resolve().parents[1]
    run_name = datetime.now(timezone.utc).strftime("reference-%Y%m%dT%H%M%S.%fZ")
    run_dir = root / "logs" / "experiments" / run_name
    run_dir.mkdir(parents=True, exist_ok=False)
    paths = (
        "reference_parser.py", "docs/reference-grammar.bnf", "law_aliases.json",
        "requirements.txt", "tests/test_reference_parser.py",
        "tools/run_reference_experiment.py",
    )
    files = {}
    for relative in paths:
        source = root / relative
        destination = run_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        files[relative] = hashlib.sha256(destination.read_bytes()).hexdigest()

    stdout_path = run_dir / "unittest.stdout.log"
    stderr_path = run_dir / "unittest.stderr.log"
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
    started_at = datetime.now(timezone.utc).isoformat()
    timer = perf_counter()
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    duration = perf_counter() - timer
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    metadata = {
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "workspace": str(root),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "duration_seconds": duration,
        "exit_code": result.returncode,
        "files_sha256": files,
        "stdout": stdout_path.name,
        "stderr": stderr_path.name,
        "status": "passed" if result.returncode == 0 else "failed",
    }
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n",
                                      encoding="utf-8")
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    print(f"Run log: {run_dir}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
