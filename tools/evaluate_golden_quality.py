"""Measure citation interpretation and full-text extraction against gold JSONL."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from law_links.projection import map_semantic_analysis
from main import app
from law_links.semantic import SemanticAnalysis


DATASETS = {
    "interpretation": ROOT / "data/golden_interpretation.jsonl",
    "extraction": ROOT / "data/golden_extraction.jsonl",
    "real_interpretation": ROOT / "data/golden_real_interpretation.jsonl",
    "real_extraction": ROOT / "data/golden_real_extraction.jsonl",
}
RECOGNITION_PROBES = (
    {
        "name": "one_edit_marker_typo_positive",
        "text": "пунта б статьи 20",
        "expected": [{"law_id": None, "article": "20", "point_article": "б",
                      "subpoint_article": None}],
    },
    {"name": "distant_marker_typo_negative", "text": "статьйа 20", "expected": []},
    {
        "name": "one_edit_full_law_alias_positive",
        "text": "ст. 5 Гражданского процессуального кодекса Российской Федерацци",
        "expected": [{"law_id": 6, "article": "5", "point_article": None,
                      "subpoint_article": None}],
    },
    {
        "name": "distant_code_name_typo_stays_unknown",
        "text": "ст. 5 Гражданского процессуального кодддекса Российской Федерации",
        "expected": [{"law_id": None, "article": "5", "point_article": None,
                      "subpoint_article": None}],
    },
    {
        "name": "short_abbreviation_typo_stays_unmatched",
        "text": "ст. 5 НКФ",
        "expected": [{"law_id": None, "article": "5", "point_article": None,
                      "subpoint_article": None}],
    },
)
LINK_FIELDS = ("law_id", "article", "point_article", "subpoint_article")


def _link_key(link: dict) -> tuple:
    return tuple(link[field] for field in LINK_FIELDS)


def _extraction_sample_exact(predicted_refs: list[dict], gold_refs: list[dict]) -> bool:
    """Compare complete extraction occurrences, including their source spans."""
    normalized_gold_refs = [{
        key: ref[key] for key in ("start", "end", "text", "links")
    } for ref in gold_refs]
    return predicted_refs == normalized_gold_refs


def _pr(tp: int, fp: int, fn: int) -> dict:
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
    }


def _rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    return [row for row in rows if row.get("status") == "gold"]


def evaluate() -> dict:
    """Run all four labeled tracks and retain per-example error details."""
    output = {}
    boundary_probe_results = []
    with TestClient(app) as client:
        for suite, path in DATASETS.items():
            rows = _rows(path)
            exact = 0
            api_tp = api_fp = api_fn = 0
            span_tp = span_fp = span_fn = 0
            grounded_tp = grounded_fp = grounded_fn = 0
            errors = []
            counts = Counter()

            for row in rows:
                text = row["text"]
                gold_refs = row.get("references", [])
                for ref in gold_refs:
                    if text[ref["start"]:ref["end"]] != ref["text"]:
                        raise ValueError(f"Invalid annotated span in {row['id']}: {ref}")
                expected = [link for ref in gold_refs for link in ref["links"]]

                response = client.post("/detect", json={"text": text})
                actual = response.json().get("links", []) if response.is_success else []
                if response.status_code != 200:
                    errors.append({"id": row["id"], "error": "non_200_response",
                                   "status_code": response.status_code})
                gold_link_counts = Counter(_link_key(link) for link in expected)
                actual_link_counts = Counter(_link_key(link) for link in actual)
                overlap = gold_link_counts & actual_link_counts
                api_tp += sum(overlap.values())
                api_fp += sum((actual_link_counts - overlap).values())
                api_fn += sum((gold_link_counts - overlap).values())
                counts["gold_links"] += len(expected)
                counts["api_links"] += len(actual)

                syntax = app.state.reference_analyzer.analyze(text)
                semantic = app.state.semantic_analyzer.analyze(syntax)
                semantic = app.state.contextual_resolver.resolve(semantic)
                predicted_refs = []
                predicted_flat = []
                for reference in semantic.references:
                    mapping = map_semantic_analysis(SemanticAnalysis((reference,), ()))
                    links = [asdict(link) for link in mapping.links]
                    predicted_refs.append({
                        "start": reference.start,
                        "end": reference.end,
                        "text": text[reference.start:reference.end],
                        "links": links,
                    })
                    predicted_flat.extend(links)
                if predicted_flat != actual:
                    raise AssertionError(f"Analyzer/API output diverged for {row['id']}")

                if "extraction" in suite:
                    gold_spans = Counter((ref["start"], ref["end"]) for ref in gold_refs)
                    pred_spans = Counter((ref["start"], ref["end"])
                                         for ref in predicted_refs)
                    span_overlap = gold_spans & pred_spans
                    span_tp += sum(span_overlap.values())
                    span_fp += sum((pred_spans - span_overlap).values())
                    span_fn += sum((gold_spans - span_overlap).values())

                    def occurrence_counts(references):
                        return Counter((ref["start"], ref["end"], _link_key(link))
                                       for ref in references for link in ref["links"])

                    gold_occurrences = occurrence_counts(gold_refs)
                    pred_occurrences = occurrence_counts(predicted_refs)
                    occurrence_overlap = gold_occurrences & pred_occurrences
                    grounded_tp += sum(occurrence_overlap.values())
                    grounded_fp += sum((pred_occurrences - occurrence_overlap).values())
                    grounded_fn += sum((gold_occurrences - occurrence_overlap).values())
                    sample_exact = _extraction_sample_exact(predicted_refs, gold_refs)
                    false_predicted = list((pred_occurrences - gold_occurrences).elements())
                    missed = list((gold_occurrences - pred_occurrences).elements())
                else:
                    sample_exact = actual == expected
                    false_predicted = []
                    missed = []

                if sample_exact:
                    exact += 1
                if not sample_exact:
                    errors.append({
                        "id": row["id"],
                        "source": row.get("source"),
                        "text": text,
                        "expected_links": expected,
                        "predicted_links": actual,
                        "gold_references": gold_refs,
                        "predicted_references": predicted_refs,
                        "false_predicted_occurrences": false_predicted,
                        "missed_occurrences": missed,
                    })

            output[suite] = {
                "dataset": str(path.relative_to(ROOT)),
                "samples": len(rows),
                "gold_references": sum(len(row.get("references", [])) for row in rows),
                "gold_links": counts["gold_links"],
                "predicted_links": counts["api_links"],
                "exact_sample_matches": exact,
                "exact_sample_match_rate": exact / len(rows) if rows else None,
                "api_link_precision_recall": _pr(api_tp, api_fp, api_fn),
                "errors": errors,
            }
            if "extraction" in suite:
                output[suite]["reference_boundary_precision_recall"] = _pr(
                    span_tp, span_fp, span_fn)
                output[suite]["exact_span_and_link_precision_recall"] = _pr(
                    grounded_tp, grounded_fp, grounded_fn)
                output[suite]["false_positive_examples"] = [
                    {"id": error["id"], "occurrences": error["false_predicted_occurrences"]}
                    for error in errors if error.get("false_predicted_occurrences")]
                output[suite]["false_negative_examples"] = [
                    {"id": error["id"], "occurrences": error["missed_occurrences"]}
                    for error in errors if error.get("missed_occurrences")]
        for probe in RECOGNITION_PROBES:
            response = client.post("/detect", json={"text": probe["text"]})
            actual = response.json().get("links", []) if response.is_success else None
            boundary_probe_results.append({
                "name": probe["name"], "text": probe["text"],
                "expected": probe["expected"], "predicted": actual,
                "exact_match": actual == probe["expected"],
            })
    output["recognition_boundary_probes"] = {
        "samples": len(boundary_probe_results),
        "exact_matches": sum(row["exact_match"] for row in boundary_probe_results),
        "cases": boundary_probe_results,
        "interpretation": (
            "Curated probes check one-edit marker/law acceptance, distant typo rejection, "
            "and unknown-name boundaries; they are not a representative corpus."),
    }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    for suite, result in report.items():
        if suite == "recognition_boundary_probes":
            print(f"{suite}: exact={result['exact_matches']}/{result['samples']}")
            continue
        pr = result["api_link_precision_recall"]
        print(f"{suite}: samples={result['samples']} "
              f"exact={result['exact_sample_matches']}/{result['samples']} "
              f"link_precision={pr['precision']} link_recall={pr['recall']}")
        if "extraction" in suite:
            grounded = result["exact_span_and_link_precision_recall"]
            print(f"  span+link precision={grounded['precision']} "
                  f"recall={grounded['recall']}; "
                  f"boundary={result['reference_boundary_precision_recall']}")
    print(f"Quality report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
