"""Run a deterministic, length-matched 2,000-request /detect workload."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from main import app


DATASETS = {
    "readme_interpretation": ROOT / "data/golden_interpretation.jsonl",
    "readme_extraction": ROOT / "data/golden_extraction.jsonl",
    "real_interpretation": ROOT / "data/golden_real_interpretation.jsonl",
    "real_extraction": ROOT / "data/golden_real_extraction.jsonl",
}
DEFAULT_TARGET_CHARS = 4092
DEFAULT_REQUESTS_PER_TRACK = 500
DEFAULT_SEED = 20261013
_PADDING_SENTENCES_BY_COST = {
    15: ("Текст понятен.", "Смысл изложен."),
    16: ("Общие сведения.", "Данные указаны.", "Материал готов.",
         "Ответ приведен."),
    17: ("Факт установлен.", "Общие материалы.", "Нужные сведения.",
         "Текст описывает."),
}


def load_gold_tracks() -> dict[str, list[str]]:
    """Load complete source samples from the four checked-in gold tracks."""
    tracks = {}
    for name, path in DATASETS.items():
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        tracks[name] = [row["text"] for row in rows if row.get("status") == "gold"]
        if not tracks[name]:
            raise ValueError(f"Gold track {name} is empty")
    return tracks


def _padding_costs(length: int) -> list[int]:
    """Find complete neutral sentences whose lengths plus separators fit."""
    previous: list[int | None] = [None] * (length + 1)
    previous[0] = 0
    for total in range(1, length + 1):
        for cost in _PADDING_SENTENCES_BY_COST:
            if total >= cost and previous[total - cost] is not None:
                previous[total] = cost
                break
    if previous[length] is None:
        raise ValueError(f"Cannot make neutral prose of exactly {length} characters")
    costs = []
    while length:
        cost = previous[length]
        assert cost is not None
        costs.append(cost)
        length -= cost
    return costs


def _neutral_prose(length: int, rng: random.Random) -> str:
    """Make exact-length neutral text from complete sentences."""
    costs = _padding_costs(length + 1)
    sentences = [rng.choice(_PADDING_SENTENCES_BY_COST[cost]) for cost in costs]
    rng.shuffle(sentences)
    return "\n".join(sentences)


def _compose_text(sample: str, target_chars: int,
                  rng: random.Random, minimum_padding: int = 512) -> str:
    """Keep one complete sample intact, then add exact neutral padding."""
    if target_chars <= minimum_padding + 16:
        raise ValueError("Target must leave room for neutral padding")
    if len(sample) + 2 + minimum_padding > target_chars:
        raise ValueError("A complete gold sample does not fit in the requested text length")
    text = sample + "\n\n" + _neutral_prose(target_chars - len(sample) - 2, rng)
    if len(text) != target_chars:
        raise AssertionError(f"Generated {len(text)} chars; expected {target_chars}")
    return text


def build_workload(tracks: dict[str, list[str]], requests_per_track: int =
                   DEFAULT_REQUESTS_PER_TRACK, target_chars: int = DEFAULT_TARGET_CHARS,
                   seed: int = DEFAULT_SEED) -> dict[str, list[str]]:
    """Build deterministic track batches from whole samples and neutral padding."""
    if requests_per_track < 1:
        raise ValueError("requests_per_track must be positive")
    rng = random.Random(seed)
    workload = {}
    for name, samples in tracks.items():
        if not samples:
            raise ValueError(f"Gold track {name} is empty")
        sample_order = list(samples)
        rng.shuffle(sample_order)
        texts = []
        seen = set()
        for index in range(requests_per_track):
            sample = sample_order[index % len(sample_order)]
            for _ in range(100):
                text = _compose_text(sample, target_chars, rng)
                if text not in seen:
                    break
            else:
                raise ValueError(f"Could not generate unique texts for track {name}")
            texts.append(text)
            seen.add(text)
        workload[name] = texts
    return workload


def _distribution(samples: list[float]) -> dict[str, float | int | None]:
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, int(0.95 * len(ordered)))
    return {
        "count": len(samples),
        "total_seconds": sum(samples),
        "mean_ms": statistics.mean(samples) * 1000 if samples else None,
        "median_ms": statistics.median(samples) * 1000 if samples else None,
        "p95_ms": ordered[p95_index] * 1000 if ordered else None,
        "max_ms": max(samples, default=0) * 1000,
    }


def run_benchmark(workload: dict[str, list[str]], seed: int,
                  target_chars: int) -> dict:
    """Measure real TestClient requests, including FastAPI lifespan startup."""
    all_texts = [text for texts in workload.values() for text in texts]
    if any(len(text) != target_chars for text in all_texts):
        raise ValueError("Every workload text must match target_chars exactly")

    request_times: dict[str, list[float]] = defaultdict(list)
    startup_started = perf_counter()
    run_started = startup_started
    with TestClient(app) as client:
        startup_seconds = perf_counter() - startup_started
        for track, texts in workload.items():
            for text in texts:
                request_started = perf_counter()
                response = client.post("/detect", json={"text": text})
                request_times[track].append(perf_counter() - request_started)
                if response.status_code != 200:
                    raise RuntimeError(f"/detect returned {response.status_code}")
    elapsed_including_startup = perf_counter() - run_started
    analyzer = app.state.reference_analyzer
    fuzzy_cache = analyzer.fuzzy_cache_info
    parse_cache = analyzer.parse_cache_info
    fuzzy_lookups = fuzzy_cache["hits"] + fuzzy_cache["misses"]
    parse_lookups = parse_cache["hits"] + parse_cache["misses"]
    flat_times = [elapsed for values in request_times.values() for elapsed in values]
    workload_hash = hashlib.sha256(
        "\n".join(all_texts).encode("utf-8")).hexdigest()
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "generation": {
            "seed": seed,
            "command": (".venv/bin/python tools/benchmark_length_matched.py "
                        f"--seed {seed} --requests-per-track {len(next(iter(workload.values())))} "
                        f"--target-chars {target_chars} --output <report.json>"),
            "target_chars": target_chars,
            "requests_per_track": {name: len(texts) for name, texts in workload.items()},
            "total_requests": len(all_texts),
            "workload_sha256": workload_hash,
            "construction": ("Shuffle complete gold samples within each track and cycle them "
                            "across requests; put one whole sample at the start, followed by "
                            "neutral prose separated by a blank line."),
        },
        "startup_seconds": startup_seconds,
        "elapsed_including_startup_seconds": elapsed_including_startup,
        "requests": {
            "per_track": {name: _distribution(values)
                          for name, values in request_times.items()},
            "aggregate": _distribution(flat_times),
        },
        "caches": {
            "parse": {**parse_cache,
                      "hit_rate": parse_cache["hits"] / parse_lookups if parse_lookups else 0.0},
            "fuzzy_lookup": {**fuzzy_cache,
                             "hit_rate": fuzzy_cache["hits"] / fuzzy_lookups
                             if fuzzy_lookups else 0.0},
        },
        "target_seconds": 240,
        "within_target": elapsed_including_startup <= 240,
        "hidden_benchmark_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--requests-per-track", type=int, default=DEFAULT_REQUESTS_PER_TRACK)
    parser.add_argument("--target-chars", type=int, default=DEFAULT_TARGET_CHARS)
    args = parser.parse_args()
    workload = build_workload(load_gold_tracks(), args.requests_per_track,
                              args.target_chars, args.seed)
    report = run_benchmark(workload, args.seed, args.target_chars)
    report["generation"]["command"] = (
        f".venv/bin/python tools/benchmark_length_matched.py --seed {args.seed} "
        f"--requests-per-track {args.requests_per_track} --target-chars {args.target_chars} "
        f"--output {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Requests: {report['generation']['total_requests']} of {args.target_chars} chars")
    print(f"Startup: {report['startup_seconds']:.3f}s")
    print(f"Elapsed including startup: {report['elapsed_including_startup_seconds']:.3f}s")
    print(f"Median/p95/max: {report['requests']['aggregate']['median_ms']:.1f}/"
          f"{report['requests']['aggregate']['p95_ms']:.1f}/"
          f"{report['requests']['aggregate']['max_ms']:.1f} ms")
    print(f"Within 240s target: {report['within_target']}")
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
