"""Check corpus structure and independently selected law-identity evidence.

Hierarchy labels were reviewed against README.md and the agreed contract.
This audit checks their representation, not legal validity of the provisions.
It does not import the analyzer or use its predictions as evidence.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

# Canonical aliases selected by reading the law names in each gold reference.
# Inflection and quote variants are reconciled manually, independently of the
# service normalizer. Exact whole-alias lookup avoids matching embedded titles
# in acts that amend another law.
CANONICAL_ALIASES = {
    0: "АПК", 5: "Гражданский кодекс Российской Федерации",
    6: "Гражданский процессуальный кодекс Российской Федерации",
    8: "Семейный кодекс Российской Федерации",
    10: "Трудовой кодекс Российской Федерации", 13: "УК РФ",
    15: "НК РФ", 17: "КоАП РФ",
    174: "«О государственной регистрации недвижимости»",
    362: "«О государственной гражданской службе Российской Федерации»",
    984: "«О защите прав потребителей»", 330: "«О персональных данных»",
    224: "«О бухгалтерском учете»",
    412: "«О государственной регистрации юридических лиц и индивидуальных предпринимателей»",
    284: "«О защите прав юридических лиц и индивидуальных предпринимателей при осуществлении государственного контроля (надзора) и муниципального контроля»",
    332: "«О защите конкуренции»", 249: "«О полиции»",
}
UNKNOWN_QUERIES = {
    "unknown-numbered-law": "20-456",
    "unknown-code-name": "рандомного",
    "law-alias-not-listed": "О банках и банковской деятельности",
    "readme-passage-08-reference-1": "20-456",
    "readme-passage-10-reference-1": "рандомного",
}
UNKNOWN_REFERENCE_QUERIES = {
    ("readme-passage-08", "ст. 37 ФЗ №20-456"): "20-456",
    ("readme-passage-08-reference-3",
     'ст. 6 Федерального закона "О банках и банковской деятельности"'):
        "О банках и банковской деятельности",
    ("readme-passage-08", 'ст. 6 Федерального закона "О банках и банковской деятельности"'):
        "О банках и банковской деятельности",
    ("readme-passage-10", "пп. 1 п. 2 ст. 34 рандомного кодекса"): "рандомного",
}


def normalize(value):
    return re.sub(r"\s+", " ", value.casefold().replace("ё", "е"))


def audit(dataset):
    aliases_path = ROOT / "law_aliases.json"
    rows = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    aliases = json.loads(aliases_path.read_text())
    source_manifest = ROOT / "data/sources/manifest.json"
    sources = {entry["id"]: entry for entry in json.loads(source_manifest.read_text())}
    source_paths = set()
    errors, results, ids = [], [], set()
    for row in rows:
        sample_id = row["id"]
        if sample_id in ids:
            errors.append(f"{sample_id}: duplicate ID")
        ids.add(sample_id)
        previous_end = 0
        law_evidence = []
        if row["status"] != "gold":
            errors.append(f"{sample_id}: unexpected status")
        if row.get("origin") == "web" and "source_span" in row:
            source = sources[row["source_id"]]
            snapshot = ROOT / source["normalized_snapshot"]
            source_paths.add(snapshot)
            span = row["source_span"]
            if (hashlib.sha256(snapshot.read_bytes()).hexdigest() != source["normalized_sha256"]
                    or snapshot.read_text()[span["start"]:span["end"]] != row["text"]):
                errors.append(f"{sample_id}: source snapshot or passage differs")
        for ref in row["references"]:
            start, end = ref["start"], ref["end"]
            if not (type(start) is int and type(end) is int
                    and previous_end <= start < end <= len(row["text"])):
                errors.append(f"{sample_id}: invalid or unordered span")
            if row["text"][start:end] != ref["text"]:
                errors.append(f"{sample_id}: span text differs")
            previous_end = end
            if not ref["links"]:
                errors.append(f"{sample_id}: reference has no target links")
            for link in ref["links"]:
                if set(link) != {"law_id", "article", "point_article", "subpoint_article"}:
                    errors.append(f"{sample_id}: unexpected LawLink fields")
                for key in ("article", "point_article", "subpoint_article"):
                    if link[key] is not None and (not isinstance(link[key], str) or not link[key]):
                        errors.append(f"{sample_id}: {key} must be a nonempty string or null")
                law_id = link["law_id"]
                if law_id is not None:
                    alias = CANONICAL_ALIASES[law_id]
                    matches = sorted(int(k) for k, values in aliases.items()
                                     if any(normalize(v) == normalize(alias) for v in values))
                    if type(law_id) is not int or matches != [law_id]:
                        errors.append(f"{sample_id}: canonical alias is not unique for {law_id}")
                    evidence = {"law_id": law_id, "canonical_alias": alias, "matching_ids": matches}
                elif (sample_id in UNKNOWN_QUERIES
                      or (sample_id, ref["text"]) in UNKNOWN_REFERENCE_QUERIES):
                    query = UNKNOWN_REFERENCE_QUERIES.get(
                        (sample_id, ref["text"]), UNKNOWN_QUERIES.get(sample_id))
                    matches = sorted(int(k) for k, values in aliases.items()
                                     if any(normalize(query) in normalize(v) for v in values))
                    if matches:
                        errors.append(f"{sample_id}: unknown-law query found dictionary entries")
                    evidence = {"law_id": None, "absence_query": query, "matching_ids": matches}
                elif "Конституци" in ref["text"]:
                    queries = ("Конституция Российской Федерации", "Конституция РФ")
                    matches = sorted(int(k) for k, values in aliases.items()
                                     if any(normalize(v) in {normalize(q) for q in queries}
                                            for v in values))
                    if matches:
                        errors.append(f"{sample_id}: standalone Constitution alias found")
                    evidence = {"law_id": None, "absent_whole_aliases": queries,
                                "matching_ids": matches}
                elif sample_id == "article-unspecified-law":
                    evidence = {"law_id": None, "reason": "No law mention or antecedent in this input."}
                else:
                    errors.append(f"{sample_id}: unexplained null law")
                    evidence = {"law_id": None, "reason": "Missing audit evidence."}
                if evidence not in law_evidence:
                    law_evidence.append(evidence)
        results.append({"id": sample_id, "references": len(row["references"]),
                        "links": sum(len(ref["links"]) for ref in row["references"]),
                        "law_evidence": law_evidence, "provenance": row["source"]})
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Structural checks and whole canonical-alias uniqueness; manual hierarchy review in docs/golden-label-audit.md.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (dataset, aliases_path, ROOT / "README.md", ROOT / "CONTEXT.md",
                                   source_manifest, *sorted(source_paths))},
        "samples": len(rows), "references": sum(r["references"] for r in results),
        "links": sum(r["links"] for r in results), "errors": errors, "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path,
                        default=ROOT / "data/golden_references.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.dataset.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Audited {report['samples']} samples, {report['references']} spans, {report['links']} links; {len(report['errors'])} errors.")
    for error in report["errors"]:
        print(error)
    raise SystemExit(bool(report["errors"]))
