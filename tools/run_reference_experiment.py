"""Run the reference-analyzer acceptance suite and snapshot its exact inputs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
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
        "main.py", "law_links/__init__.py", "law_links/application.py", "law_links/http.py",
        "law_links/syntax/__init__.py", "law_links/syntax/analyzer.py",
        "law_links/syntax/models.py", "law_links/syntax/grammar.py",
        "law_links/syntax/numbers.py", "law_links/semantic.py", "law_links/context.py",
        "law_links/projection.py", "Dockerfile",
        "law_links/resources/reference-grammar.bnf", "data/law_aliases.json", "requirements.txt",
        "requirements-test.txt", "tests/test_reference_parser.py",
        "tests/test_service_api.py",
        "tests/test_semantic_analyzer.py",
        "tests/test_law_link_mapper.py",
        "data/golden_references.jsonl", "data/review_queue.jsonl",
        "data/golden_interpretation.jsonl", "data/golden_extraction.jsonl",
        "data/golden_real_interpretation.jsonl", "data/golden_real_extraction.jsonl",
        "data/real_review_queue.jsonl", "data/sources/manifest.json",
        "data/sources/vsrf-14913.txt", "data/sources/vsrf-13345.txt",
        "data/sources/vsrf-12452.txt", "docs/real-reference-data.md",
        "docs/golden-test-data.md", "tools/evaluate_golden_references.py",
        "tools/run_reference_experiment.py",
        "CONTEXT.md",
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
    test_duration = perf_counter() - timer
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    evaluation_command = [
        sys.executable, "-B", "tools/evaluate_golden_references.py",
        "--dataset", str(run_dir / "data/golden_references.jsonl"),
        "--output", str(run_dir / "golden-evaluation.json"),
    ]
    evaluation_started = perf_counter()
    evaluation = subprocess.run(evaluation_command, cwd=root, capture_output=True, text=True)
    evaluation_duration = perf_counter() - evaluation_started
    evaluation_stdout_path = run_dir / "golden-evaluation.stdout.log"
    evaluation_stderr_path = run_dir / "golden-evaluation.stderr.log"
    evaluation_stdout_path.write_text(evaluation.stdout, encoding="utf-8")
    evaluation_stderr_path.write_text(evaluation.stderr, encoding="utf-8")
    additional_evaluations = []
    for suite in ("interpretation", "extraction", "real_interpretation", "real_extraction"):
        argv = [sys.executable, "-B", "tools/evaluate_golden_references.py",
                "--dataset", str(run_dir / f"data/golden_{suite}.jsonl"),
                "--output", str(run_dir / f"golden-{suite}-evaluation.json")]
        started = perf_counter()
        completed = subprocess.run(argv, cwd=root, capture_output=True, text=True)
        elapsed = perf_counter() - started
        out = run_dir / f"golden-{suite}.stdout.log"
        err = run_dir / f"golden-{suite}.stderr.log"
        out.write_text(completed.stdout, encoding="utf-8")
        err.write_text(completed.stderr, encoding="utf-8")
        additional_evaluations.append({"argv": argv, "exit_code": completed.returncode,
                                       "duration_seconds": elapsed,
                                       "stdout": out.name, "stderr": err.name,
                                       "report": f"golden-{suite}-evaluation.json"})
    duration = test_duration + evaluation_duration + sum(
        r["duration_seconds"] for r in additional_evaluations)
    metadata = {
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "commands": [
            {"argv": command, "exit_code": result.returncode,
             "duration_seconds": test_duration,
             "stdout": stdout_path.name, "stderr": stderr_path.name},
            {"argv": evaluation_command, "exit_code": evaluation.returncode,
             "duration_seconds": evaluation_duration,
             "stdout": evaluation_stdout_path.name, "stderr": evaluation_stderr_path.name,
             "report": "golden-evaluation.json"},
        ] + additional_evaluations,
        "workspace": str(root),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {name: version(name) for name in
                         ("fastapi", "httpx", "lark", "pymorphy3",
                          "pymorphy3-dicts-ru", "rapidfuzz", "uvicorn")},
        "duration_seconds": duration,
        "exit_code": result.returncode or evaluation.returncode or next(
            (r["exit_code"] for r in additional_evaluations if r["exit_code"]), 0),
        "files_sha256": files,
        "stdout": stdout_path.name,
        "stderr": stderr_path.name,
        "status": "passed" if result.returncode == 0 and evaluation.returncode == 0
                  and all(r["exit_code"] == 0 for r in additional_evaluations) else "failed",
    }
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n",
                                      encoding="utf-8")
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    print(evaluation.stdout, end="")
    print(evaluation.stderr, end="", file=sys.stderr)
    print(f"Run log: {run_dir}")
    return metadata["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
