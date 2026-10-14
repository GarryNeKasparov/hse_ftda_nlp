"""Benchmark varied README-length texts through the complete /detect service."""

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
from tools.benchmark_length_matched import DATASETS, _distribution


SOURCE_PATHS = tuple(sorted((ROOT / "data/sources").glob("vsrf-*.txt")))
TRACKS = tuple(DATASETS)
TARGET_CHARS = 4092
SEED = 20261013
REQUESTS_PER_TRACK = 500
NATURAL_PER_TRACK = 25
TARGET_SECONDS = 240


def load_citations() -> dict[str, list[str]]:
    citations = {}
    for track, path in DATASETS.items():
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        passages = [reference["text"] for row in rows if row.get("status") == "gold"
                    for reference in row["references"]]
        # Each citation stays complete. Long passages are supplied by the
        # natural windows; compact ones allow dense controlled inputs.
        citations[track] = sorted(set(text for text in passages if len(text) <= 100))
        if not citations[track]:
            raise ValueError(f"No compact citations for {track}")
    return citations


def build_workload(requests_per_track: int = REQUESTS_PER_TRACK,
                   seed: int = SEED) -> tuple[dict[str, list[str]], dict]:
    """Freeze distinct natural and controlled requests with complete citations."""
    if requests_per_track < 1 or requests_per_track > REQUESTS_PER_TRACK:
        raise ValueError("requests_per_track must be between 1 and 500")
    sources = [(path.name, path.read_text(encoding="utf-8")) for path in SOURCE_PATHS]
    if len(sources) != 4:
        raise ValueError("Expected four checked-in legal documents")
    citations = load_citations()
    rng = random.Random(seed)
    natural_count = max(1, round(requests_per_track * NATURAL_PER_TRACK /
                                 REQUESTS_PER_TRACK))
    workload = {}
    details = {}
    global_seen = set()
    for track_index, track in enumerate(TRACKS):
        texts = []
        natural = []
        controlled = []
        for index in range(natural_count):
            source_name, source = sources[(index + track_index) % len(sources)]
            # Across all tracks, each source window starts 2,200 characters
            # after the previous one: adjacent 4,092-character windows share
            # less than half of their source text.
            offset = (index // 4 * 4 + track_index) * 2200
            if offset + TARGET_CHARS > len(source):
                raise ValueError(f"Insufficient distinct text in {source_name}")
            text = source[offset:offset + TARGET_CHARS]
            if text in global_seen:
                raise ValueError("Duplicate natural window")
            global_seen.add(text)
            texts.append(text)
            natural.append({"source": source_name, "start": offset})

        pool = citations[track]
        for index in range(natural_count, requests_per_track):
            count = (5, 15, 30)[index % 3]
            frames = [rng.choice(pool) for _ in range(count)]
            inserted = "\n\n".join(frames)
            available = TARGET_CHARS - len(inserted) - 4
            if available < TARGET_CHARS // 3:
                raise ValueError("Citation frames leave too little natural prose")
            source_name, source = sources[(index + track_index) % len(sources)]
            offset = rng.randrange(len(source) - available + 1)
            background = source[offset:offset + available]
            split = available // 2
            text = background[:split] + "\n\n" + inserted + "\n\n" + background[split:]
            if len(text) != TARGET_CHARS or text in global_seen:
                raise ValueError("Generated request is not distinct or length matched")
            global_seen.add(text)
            texts.append(text)
            controlled.append({"source": source_name, "start": offset,
                               "citation_count": count,
                               "natural_characters": available})
        workload[track] = texts
        details[track] = {"natural": natural, "controlled": controlled}

    flat = [text for texts in workload.values() for text in texts]
    return workload, {
        "seed": seed,
        "requests_per_track": requests_per_track,
        "target_characters": TARGET_CHARS,
        "total_requests": len(flat),
        "unique_requests": len(global_seen),
        "workload_sha256": hashlib.sha256("\n".join(flat).encode()).hexdigest(),
        "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in SOURCE_PATHS},
        "details": details,
    }


def run_benchmark(workload: dict[str, list[str]], generation: dict) -> dict:
    times = defaultdict(list)
    response_hash = hashlib.sha256()
    started = perf_counter()
    with TestClient(app) as client:
        startup = perf_counter() - started
        for track, texts in workload.items():
            for text in texts:
                request_started = perf_counter()
                response = client.post("/detect", json={"text": text})
                times[track].append(perf_counter() - request_started)
                if response.status_code != 200:
                    raise RuntimeError(f"/detect returned {response.status_code}")
                response_hash.update(response.content)
                response_hash.update(b"\n")
    total = perf_counter() - started
    samples = [sample for track_times in times.values() for sample in track_times]
    analyzer = app.state.reference_analyzer
    projected = startup + sum(samples) * 2000 / len(samples)
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "generation": generation,
        "startup_seconds": startup,
        "elapsed_including_startup_seconds": total,
        "requests": {"per_track": {track: _distribution(track_times)
                                    for track, track_times in times.items()},
                     "aggregate": _distribution(samples),
                     "per_request_ms": {track: [round(sample * 1000, 3)
                                                for sample in track_times]
                                        for track, track_times in times.items()}},
        "projected_2000_seconds": projected,
        "response_sha256": response_hash.hexdigest(),
        "caches": {"parse": analyzer.parse_cache_info,
                   "fuzzy_lookup": analyzer.fuzzy_cache_info},
        "target_seconds": TARGET_SECONDS,
        "within_target": total <= TARGET_SECONDS if len(samples) == 2000 else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests-per-track", type=int, default=REQUESTS_PER_TRACK)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    workload, generation = build_workload(args.requests_per_track, args.seed)
    result = run_benchmark(workload, generation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Requests: {generation['total_requests']}; unique: {generation['unique_requests']}")
    print(f"Startup: {result['startup_seconds']:.3f}s")
    print(f"Elapsed: {result['elapsed_including_startup_seconds']:.3f}s")
    print(f"Projected 2,000-request time: {result['projected_2000_seconds']:.1f}s")
    print(f"Within {TARGET_SECONDS}s target: {result['within_target']}")
    print(f"Workload SHA-256: {generation['workload_sha256']}")
    return 1 if result["within_target"] is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
