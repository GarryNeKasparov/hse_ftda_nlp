# Issue 15 — inserted identifiers and plural ASCII ranges

## Rule implemented

Expand an ASCII hyphen-minus range when the selector context explicitly
indicates plurality through marker morphology or coordination. Singular
inserted article identifiers remain atomic. A shorthand marker without enough
number evidence, such as `ст. 28-1`, retains its competing identifier/range
readings. A singular point label such as `пункт 2-1` also remains unresolved.
Ascending integer expansion remains inclusive, ordered, and capped at 1,000
values; reversed, oversized, and malformed ranges produce diagnostics without
emitting the partial selector.

## Focused results

All ten analyzer/API cases in `inputs.json` passed:

| Case | Result |
| --- | --- |
| `статья 6-1 ГПК РФ` | One link with atomic article `6-1`, law ID 6 |
| `частями 1 и 2 статьи 327-2 ГПК РФ` | Parts 1 and 2 under atomic article `327-2`, law ID 6 |
| `главу 6 и статьи 175-189 ГПК РФ` | Articles 175–189 in written order, law ID 6 |
| `частей 1-3 и 5 статьи 322 ГПК РФ` | Parts 1, 2, 3, 5 under article 322 |
| `пункты 2-4 статьи 10 НК РФ` | Points 2, 3, 4 under article 10, law ID 15 |
| `ст. 28-1 ГПК РФ`; `пункт 2-1 статьи 10 НК РФ` | No links; ambiguity retained |
| Reversed, oversized, and malformed plural ranges | No partial range target; `reversed_range`, `range_too_large`, or `unfinished_continuation` diagnostic |

`results.json` records exact API outputs, semantic paths, and diagnostics.
`run.json` records source hashes, Python/dependency versions, command,
duration, and input hash. Standard output and error are saved separately.
The full test suite passed: 110 tests.

## Whole-document check

The unchanged 79,807-character agent-reviewed Supreme Court resolution corpus
was rescored. API link counts improved from Issue 14's 224 true positives, 7
false positives, and 90 false negatives to 276 true positives, 7 false
positives, and 38 false negatives (precision 97.53%, recall 87.90%, F1 92.46%).
Exact reference boundaries rose from 172/211 to 185/211. The full document is
still not an exact match; remaining errors include gaps outside this ticket's
range and inserted-identifier scope. The labels are not human-adjudicated.

One complete-document TestClient request took 22.66 seconds after 4.14 seconds
of startup. The detailed report and captured console output are
`full_document_quality.json`, `full_document.stdout.log`, and
`full_document.stderr.log`.

## Reproduction

```sh
.venv/bin/python -B logs/experiments/issue-15-20261009T125655Z/experiment.py \
  > logs/experiments/issue-15-20261009T125655Z/console.stdout.log \
  2> logs/experiments/issue-15-20261009T125655Z/console.stderr.log
.venv/bin/python -B tools/evaluate_document_quality.py \
  --dataset data/golden_document-vsrf-13975.json \
  --output logs/experiments/issue-15-20261009T125655Z/full_document_quality.json \
  > logs/experiments/issue-15-20261009T125655Z/full_document.stdout.log \
  2> logs/experiments/issue-15-20261009T125655Z/full_document.stderr.log
```
