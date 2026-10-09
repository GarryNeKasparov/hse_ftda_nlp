"""Score a complete document against separately reviewed LawLink annotations."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from law_link_mapper import map_semantic_analysis
from main import app
from semantic_analyzer import SemanticAnalysis

FIELDS = ("law_id", "article", "point_article", "subpoint_article")


def link_key(link):
    return tuple(link[field] for field in FIELDS)


def score_counts(gold, predicted):
    """Count matching occurrences without dropping repeated targets."""
    gold, predicted = Counter(gold), Counter(predicted)
    matched = gold & predicted
    return score_totals(sum(matched.values()), sum((predicted - gold).values()),
                        sum((gold - predicted).values()))


def score_totals(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"true_positive": tp, "false_positive": fp, "false_negative": fn,
            "precision": precision, "recall": recall,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0}


def ordered_matches(gold, predicted):
    """Count the longest matching subsequence, respecting document order."""
    previous = [0] * (len(predicted) + 1)
    for expected in gold:
        current = [0]
        for index, actual in enumerate(predicted, 1):
            current.append(previous[index - 1] + 1 if expected == actual
                           else max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.dataset.read_text(encoding="utf-8"))
    text = document["text"]
    gold_refs = document["references"]
    if document.get("status") != "gold":
        raise ValueError("Expected reviewed gold annotations, not saved predictions")
    for ref in gold_refs:
        if text[ref["start"]:ref["end"]] != ref["text"]:
            raise ValueError(f"Invalid annotated source span: {ref['start']}:{ref['end']}")
    expected = [link for ref in gold_refs for link in ref["links"]]
    if document["result"] != {"links": expected}:
        raise ValueError("Gold text2result output disagrees with annotated references")

    startup = perf_counter()
    with TestClient(app) as client:
        startup_seconds = perf_counter() - startup
        started = perf_counter()
        response = client.post("/detect", json={"text": text})
        request_seconds = perf_counter() - started
        response.raise_for_status()
        result = response.json()

        stage_times = {}
        started = perf_counter()
        syntax = app.state.reference_analyzer.analyze(text)
        stage_times["syntax_seconds"] = perf_counter() - started
        started = perf_counter()
        semantic = app.state.semantic_analyzer.analyze(syntax)
        stage_times["semantic_seconds"] = perf_counter() - started
        started = perf_counter()
        semantic = app.state.contextual_resolver.resolve(semantic)
        stage_times["context_seconds"] = perf_counter() - started
        predicted_refs = []
        for ref in semantic.references:
            mapped = map_semantic_analysis(SemanticAnalysis((ref,), ()))
            predicted_refs.append({"start": ref.start, "end": ref.end,
                                   "text": text[ref.start:ref.end],
                                   "links": [asdict(link) for link in mapped.links]})

    predicted = result["links"]
    if [link for ref in predicted_refs for link in ref["links"]] != predicted:
        raise AssertionError("HTTP response and source-positioned pipeline diverged")
    gold_keys, pred_keys = list(map(link_key, expected)), list(map(link_key, predicted))
    ordered_tp = ordered_matches(gold_keys, pred_keys)

    def grounded_keys(refs):
        return [(ref["start"], ref["end"], link_key(link))
                for ref in refs for link in ref["links"]]

    errors = []
    exact_refs = 0
    for ref in gold_refs:
        exact = next((p for p in predicted_refs
                      if (p["start"], p["end"]) == (ref["start"], ref["end"])
                      and p["links"] == ref["links"]), None)
        if exact is not None:
            exact_refs += 1
        else:
            overlaps = [p for p in predicted_refs
                        if p["start"] < ref["end"] and ref["start"] < p["end"]]
            errors.append({"gold": ref, "overlapping_predictions": overlaps})
    extra_refs = [p for p in predicted_refs
                  if not any(p["start"] < g["end"] and g["start"] < p["end"]
                             for g in gold_refs)]
    code_paths = ("reference_parser.py", "semantic_analyzer.py", "contextual_resolver.py",
                  "law_link_mapper.py", "main.py", "law_aliases.json", "docs/reference-grammar.bnf")
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": document["source"], "dataset": str(args.dataset),
        "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "source_sha256": document["source_sha256"],
        "code_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                        for path in code_paths},
        "annotation_status": document["annotation_status"],
        "annotation_policy": document["annotation_policy"],
        "document_characters": len(text), "gold_references": len(gold_refs),
        "predicted_references": len(predicted_refs), "gold_links": len(expected),
        "predicted_links": len(predicted), "document_exact_match": predicted == expected,
        "api_link_metrics": score_counts(gold_keys, pred_keys),
        "ordered_link_metrics": score_totals(ordered_tp, len(predicted) - ordered_tp,
                                             len(expected) - ordered_tp),
        "reference_boundary_metrics": score_counts(
            [(ref["start"], ref["end"]) for ref in gold_refs],
            [(ref["start"], ref["end"]) for ref in predicted_refs]),
        "exact_span_and_link_metrics": score_counts(grounded_keys(gold_refs),
                                                     grounded_keys(predicted_refs)),
        "exact_reference_matches": exact_refs,
        "exact_reference_match_rate": exact_refs / len(gold_refs),
        "runtime": {"startup_seconds": startup_seconds,
                    "http_request_seconds": request_seconds,
                    "characters_per_second": len(text) / request_seconds,
                    "warm_pipeline_stage_times": stage_times,
                    "measurement": "One complete-document TestClient request; warm direct pipeline measured separately."},
        "diagnostic_counts": dict(Counter(d.code for d in semantic.diagnostics)),
        "result": result, "predicted_references_with_spans": predicted_refs,
        "reference_errors": errors, "predictions_without_gold_overlap": extra_refs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {key: report[key] for key in (
        "gold_references", "predicted_references", "gold_links", "predicted_links",
        "document_exact_match", "api_link_metrics", "ordered_link_metrics",
        "reference_boundary_metrics", "exact_span_and_link_metrics",
        "exact_reference_matches", "runtime")}
    print(json.dumps(summary, indent=2))
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
