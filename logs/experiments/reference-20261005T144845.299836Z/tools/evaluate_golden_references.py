"""Compare the current HTTP response with manually annotated gold examples."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import app


def main() -> int:
    """Run the golden corpus through POST /detect and save every prediction."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    examples = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    examples = [example for example in examples if example.get("status") == "gold"]
    results = []
    with TestClient(app) as client:
        for example in examples:
            references = example["references"]
            for reference in references:
                start, end = reference["start"], reference["end"]
                if example["text"][start:end] != reference["text"]:
                    raise ValueError(f"Gold span text does not match sample {example['id']}")
            started = perf_counter()
            response = client.post("/detect", json={"text": example["text"]})
            elapsed = perf_counter() - started
            predicted = response.json().get("links") if response.is_success else None
            expected = [link for reference in references for link in reference["links"]]
            results.append({
                "id": example["id"],
                "test_type": example.get("test_type", "legacy_mixed"),
                "source": example["source"],
                "references": references,
                "status_code": response.status_code,
                "expected": expected,
                "predicted": predicted,
                "exact_match": predicted == expected,
                "elapsed_seconds": elapsed,
            })

    exact = sum(result["exact_match"] for result in results)
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(args.dataset),
        "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "evaluated": len(results),
        "exact_matches": exact,
        "accuracy_on_this_fixture_only": exact / len(results) if results else None,
        "elapsed_seconds": sum(result["elapsed_seconds"] for result in results),
        "results": results,
        "by_test_type": {
            kind: {
                "evaluated": sum(r["test_type"] == kind for r in results),
                "exact_matches": sum(r["test_type"] == kind and r["exact_match"]
                                     for r in results),
            }
            for kind in sorted({r["test_type"] for r in results})
        },
        "boundary_scoring": "Not measured: POST /detect returns links without spans.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    mismatches = [result["id"] for result in results if not result["exact_match"]]
    print(f"Exact responses: {exact}/{len(results)}")
    if mismatches:
        print("Mismatches: " + ", ".join(mismatches))
    print(f"Evaluation report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
