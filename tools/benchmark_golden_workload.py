"""Measure initialization, analyzer processing, and API time on a 2,000-text proxy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from law_links.projection import map_semantic_analysis
from main import app
from law_links.syntax.analyzer import ReferenceAnalyzer
from law_links.semantic import SemanticAnalysis, SemanticAnalyzer
from law_links.context import ContextualResolver


DATASETS = {
    "readme_interpretation": ROOT / "data/golden_interpretation.jsonl",
    "readme_extraction": ROOT / "data/golden_extraction.jsonl",
    "real_interpretation": ROOT / "data/golden_real_interpretation.jsonl",
    "real_extraction": ROOT / "data/golden_real_extraction.jsonl",
}


def load_texts():
    suites = {}
    for name, path in DATASETS.items():
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        suites[name] = [row["text"] for row in rows if row.get("status") == "gold"]
    return suites


def distribution(times: list[float]) -> dict:
    ordered = sorted(times)
    p95_index = min(len(ordered) - 1, int(0.95 * len(ordered)))
    return {
        "count": len(times),
        "total_seconds": sum(times),
        "mean_ms": statistics.mean(times) * 1000 if times else None,
        "median_ms": statistics.median(times) * 1000 if times else None,
        "p95_ms": ordered[p95_index] * 1000 if ordered else None,
        "max_ms": max(times, default=0) * 1000,
    }


def pipeline(analyzer, semantic_analyzer, resolver, text):
    syntax = analyzer.analyze(text)
    semantic = semantic_analyzer.analyze(syntax)
    resolved = resolver.resolve(semantic)
    return map_semantic_analysis(resolved)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=500)
    args = parser.parse_args()
    suites = load_texts()
    if not all(suites.values()):
        raise ValueError("Every gold suite must contain at least one example")

    init_started = perf_counter()
    analyzer = ReferenceAnalyzer.from_alias_file(ROOT / "data/law_aliases.json")
    semantic_analyzer = SemanticAnalyzer()
    resolver = ContextualResolver()
    resource_init_seconds = perf_counter() - init_started

    for texts in suites.values():
        for text in texts[:5]:
            pipeline(analyzer, semantic_analyzer, resolver, text)

    workload = {name: [texts[index % len(texts)] for index in range(args.repetitions)]
                for name, texts in suites.items()}
    direct_times = {}
    for name, texts in workload.items():
        samples = []
        for text in texts:
            started = perf_counter()
            pipeline(analyzer, semantic_analyzer, resolver, text)
            samples.append(perf_counter() - started)
        direct_times[name] = samples

    api_times = {}
    startup_started = perf_counter()
    with TestClient(app) as client:
        service_startup_seconds = perf_counter() - startup_started
        for name, texts in workload.items():
            samples = []
            for text in texts:
                started = perf_counter()
                response = client.post("/detect", json={"text": text})
                samples.append(perf_counter() - started)
                if response.status_code != 200:
                    raise RuntimeError(f"/detect returned {response.status_code}")
            api_times[name] = samples

    direct_total = sum(sum(samples) for samples in direct_times.values())
    api_total = sum(sum(samples) for samples in api_times.values())
    total_texts = sum(len(texts) for texts in workload.values())
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "datasets_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in DATASETS.values()},
        "workload": {
            "suite_text_counts": {name: len(texts) for name, texts in suites.items()},
            "texts_per_suite": args.repetitions,
            "total_texts": total_texts,
            "construction": "Cycle each gold sample in its track until 500 inputs; no generated legal text.",
            "warmup": "Five original samples per track for direct pipeline only; excluded from measured totals.",
        },
        "initialization": {
            "resources": "ReferenceAnalyzer.from_alias_file + SemanticAnalyzer + ContextualResolver",
            "resource_initialization_seconds": resource_init_seconds,
            "fastapi_lifespan_startup_seconds": service_startup_seconds,
        },
        "analyzer_pipeline": {
            "per_suite": {name: distribution(values) for name, values in direct_times.items()},
            "aggregate": distribution([value for values in direct_times.values()
                                        for value in values]),
            "total_seconds": direct_total,
        },
        "http_service": {
            "per_suite": {name: distribution(values) for name, values in api_times.items()},
            "aggregate": distribution([value for values in api_times.values()
                                        for value in values]),
            "total_seconds": api_total,
            "estimated_request_overhead_seconds": max(0.0, api_total - direct_total),
        },
        "assignment_limit": {
            "texts": 2000,
            "seconds": 300,
            "measured_http_seconds": api_total,
            "local_proxy_within_limit": api_total <= 300,
            "hidden_benchmark_claim": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Initialization: analyzer={resource_init_seconds:.3f}s "
          f"service_startup={service_startup_seconds:.3f}s")
    print(f"Direct pipeline {total_texts} texts: {direct_total:.3f}s")
    print(f"HTTP /detect {total_texts} texts: {api_total:.3f}s "
          f"(estimated request overhead {max(0.0, api_total - direct_total):.3f}s)")
    print(f"Local proxy within 300s: {api_total <= 300}")
    print(f"Benchmark report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
