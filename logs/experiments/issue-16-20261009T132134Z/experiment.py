"""Evaluate ordinal paragraph projection at the analyzer and API seams."""

from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from main import app

RUN_DIR = Path(__file__).resolve().parent
INPUTS_PATH = RUN_DIR / "inputs.json"
RESULTS_PATH = RUN_DIR / "results.json"
INPUTS = json.loads(INPUTS_PATH.read_text(encoding="utf-8"))


def main():
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    results = []
    with TestClient(app) as client:
        for item in INPUTS:
            syntax = app.state.reference_analyzer.analyze(item["text"])
            semantic = app.state.semantic_analyzer.analyze(syntax)
            response = client.post("/detect", json={"text": item["text"]})
            links = response.json()["links"]
            results.append({
                **item,
                "actual_links": links,
                "semantic_paths": [asdict(path) for reference in semantic.references
                                   for path in reference.provisions],
                "diagnostics": [diagnostic.code for diagnostic in semantic.diagnostics],
                "passed": response.status_code == 200 and links == item["expected_links"],
            })

    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    sources = ("reference_parser.py", "semantic_analyzer.py", "law_link_mapper.py",
               "main.py", "docs/reference-grammar.bnf", "law_aliases.json")
    metadata = {
        "ticket": "16",
        "exit_status": 0 if all(result["passed"] for result in results) else 1,
        "started_at_utc": started_at,
        "duration_seconds": time.monotonic() - started,
        "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))],
        "stdout": "console.stdout.log",
        "stderr": "console.stderr.log",
        "python": sys.version,
        "dependencies": {name: version(name) for name in ("fastapi", "lark", "pydantic")},
        "inputs_sha256": hashlib.sha256(INPUTS_PATH.read_bytes()).hexdigest(),
        "source_sha256": {
            relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in sources
        },
        "results": "results.json",
        "case_count": len(results),
    }
    (RUN_DIR / "run.json").write_text(json.dumps(metadata, indent=2) + "\n",
                                      encoding="utf-8")
    for result in results:
        print(f"{result['id']}: passed={result['passed']} "
              f"links={len(result['actual_links'])} diagnostics={result['diagnostics']}")
    print(f"saved {RESULTS_PATH.relative_to(ROOT)}")
    raise SystemExit(metadata["exit_status"])


if __name__ == "__main__":
    main()
