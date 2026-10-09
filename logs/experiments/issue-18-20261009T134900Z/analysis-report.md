# Issue 18 — mixed-level groups and heading boundaries

## Rule implemented

Mixed-level branches remain separate provision paths, retaining each branch's
article, part, point, and paragraph values while sharing a trailing law. A
short `п.` marker no longer attaches to a dotted number at the start of a new
line, so it cannot consume the number of a following section heading. A
standalone point citation remains supported.

## Focused results

All four analyzer/API cases in `inputs.json` passed:

| Case | Result |
| --- | --- |
| `части 4 статьи 1, абзаца четвертого статьи 222 и пункта 4 статьи 328 ГПК РФ` | Three ordered paths: part 4/article 1; paragraph 4/article 222; point 4/article 328; all law ID 6 |
| Full measured `т. п.` passage followed by heading `9.` and a citation | No heading point 9; article 225, point 5 is extracted |
| `п. 9 ГПК РФ` | Standalone point 9 remains recognized |
| Ordinary `т. п.` prose | No links |

The API omits paragraph, so the middle branch projects as article 222 while the
internal semantic path retains paragraph 4. `results.json` records exact
outputs, paths, and source spans. All 128 tests passed; captured output is in
`tests.stdout.log` and `tests.stderr.log`.

## Whole-document check

The unchanged 79,807-character agent-reviewed Supreme Court resolution corpus
was rescored. API links improved from Issue 17's 305 true positives, 1 false
positive, and 9 false negatives to 308 true positives, 0 false positives, and
6 false negatives (precision 100%, recall 98.09%, F1 99.04%). Exact reference
boundaries rose from 204/211 to 205/211. The corpus labels are agent-reviewed,
not human-adjudicated; the document is not an exact match.

One complete-document TestClient request took 22.46 seconds after 4.67 seconds
of startup. Metrics and captured output are in `full_document_quality.json`,
`full_document.stdout.log`, and `full_document.stderr.log`.

## Reproduction

```sh
.venv/bin/python -B logs/experiments/issue-18-20261009T134900Z/experiment.py \
  > logs/experiments/issue-18-20261009T134900Z/console.stdout.log \
  2> logs/experiments/issue-18-20261009T134900Z/console.stderr.log
.venv/bin/python -B tools/evaluate_document_quality.py \
  --dataset data/golden_document-vsrf-13975.json \
  --output logs/experiments/issue-18-20261009T134900Z/full_document_quality.json \
  > logs/experiments/issue-18-20261009T134900Z/full_document.stdout.log \
  2> logs/experiments/issue-18-20261009T134900Z/full_document.stderr.log
```
