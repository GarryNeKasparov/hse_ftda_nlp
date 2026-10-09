# Issue 16 — ordinal paragraph projection

## Rule implemented

Paragraph selectors support Russian ordinal values from first through twentieth
and round tens through hundredth. Ordinal lists and ranges expand in written
order with the existing 1,000-value limit. Each paragraph remains a separate
internal provision path; the four-field API omits its paragraph value while
preserving article, part, point, subpoint, and law identity. Unsupported ordinal
words remain unresolved.

## Focused results

All six analyzer/API cases in `inputs.json` passed:

| Case | Result |
| --- | --- |
| `абзаца второго статьи 284 ГПК РФ` | Article 284 link, law ID 6 |
| `абзаца первого части 1 статьи 284 ГПК РФ` | Article 284, part 1, law ID 6 |
| `абзаца второго пункта 2 статьи 284 ГПК РФ` | Article 284, point 2, law ID 6 |
| `абзацев первого и второго пункта 2 статьи 284 ГПК РФ` | Two identical links retained for two paragraph targets |
| `абзацев первого-третьего и пятого статьи 284 ГПК РФ` | Four identical links retained for the expanded list/range |
| `Это первый абзац обычного текста.` | No link |

`results.json` records semantic paths and exact API outputs. `run.json` records
the input and source hashes, runtime environment, and command. Test output is
saved in `tests.stdout.log` and `tests.stderr.log`; all 119 tests passed.

## Whole-document check

The unchanged 79,807-character agent-reviewed Supreme Court resolution corpus
was rescored. API link counts improved from Issue 15's 276 true positives, 7
false positives, and 38 false negatives to 299 true positives, 7 false
positives, and 15 false negatives (precision 97.71%, recall 95.22%, F1 96.45%).
Exact reference boundaries rose from 185/211 to 199/211. The document is not an
exact match; labels are agent-reviewed, not human-adjudicated.

One complete-document TestClient request took 12.70 seconds after 4.57 seconds
of startup. Captured output and detailed metrics are in
`full_document_quality.json`, `full_document.stdout.log`, and
`full_document.stderr.log`.

## Reproduction

```sh
.venv/bin/python -B logs/experiments/issue-16-20261009T132134Z/experiment.py \
  > logs/experiments/issue-16-20261009T132134Z/console.stdout.log \
  2> logs/experiments/issue-16-20261009T132134Z/console.stderr.log
.venv/bin/python -B tools/evaluate_document_quality.py \
  --dataset data/golden_document-vsrf-13975.json \
  --output logs/experiments/issue-16-20261009T132134Z/full_document_quality.json \
  > logs/experiments/issue-16-20261009T132134Z/full_document.stdout.log \
  2> logs/experiments/issue-16-20261009T132134Z/full_document.stderr.log
```
