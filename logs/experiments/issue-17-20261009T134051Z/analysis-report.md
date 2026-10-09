# Issue 17 — explicit law titles and context safety

## Rule implemented

Dated federal-law citations can continue through a bounded date, law number,
and quoted title. An exact title alias supplies its law ID. Unlisted legal
titles and recognized Convention mentions are retained as explicit unknown law
targets, preventing the contextual resolver from assigning a previous law.
The Convention wording in the measured corpus is retained as part of the
reference span. A near title does not fuzzy-resolve to the known law alias.

## Focused results

All seven analyzer/API cases in `inputs.json` passed:

| Case | Result |
| --- | --- |
| Dated Federal Law No. 262-ФЗ following a ГПК reference | Articles 14 and 16 resolve to law ID 287 |
| Same title with a line break after `статьями` | Articles 14 and 16 resolve to law ID 287 |
| Ombudsman law and Convention after ГПК | Both remain `law_id=null`; following article 7 uses НК РФ, ID 15 |
| `пунктом 1 статьи 6 Конвенции о защите прав человека и основных свобод` | Article 6, point 1, null law ID; complete span |
| Federal constitutional law after articles 9 and 14 | Both links keep null law ID and the reference includes the full title |
| Near-matching 262-ФЗ title | No alias is invented; both links keep null law ID |
| Unrelated federal-law prose after a citation | The citation span ends at `ГПК РФ` |

`results.json` records exact API links, semantic paths, identity statuses, and
source spans. `run.json` records source/input hashes and runtime versions. The
full test suite passed: 124 tests; captured output is in `tests.stdout.log` and
`tests.stderr.log`.

## Whole-document check

The unchanged 79,807-character agent-reviewed Supreme Court resolution corpus
was rescored. API links improved from Issue 16's 299 true positives, 7 false
positives, and 15 false negatives to 305 true positives, 1 false positive, and
9 false negatives (precision 99.67%, recall 97.13%, F1 98.39%). Exact reference
boundaries rose from 199/211 to 204/211. The corpus labels are
agent-reviewed, not human-adjudicated, and the document is not an exact match.

One complete-document TestClient request took 22.00 seconds after 5.95 seconds
of startup. Detailed metrics and captured output are in
`full_document_quality.json`, `full_document.stdout.log`, and
`full_document.stderr.log`.

## Reproduction

```sh
.venv/bin/python -B logs/experiments/issue-17-20261009T134051Z/experiment.py \
  > logs/experiments/issue-17-20261009T134051Z/console.stdout.log \
  2> logs/experiments/issue-17-20261009T134051Z/console.stderr.log
.venv/bin/python -B tools/evaluate_document_quality.py \
  --dataset data/golden_document-vsrf-13975.json \
  --output logs/experiments/issue-17-20261009T134051Z/full_document_quality.json \
  > logs/experiments/issue-17-20261009T134051Z/full_document.stdout.log \
  2> logs/experiments/issue-17-20261009T134051Z/full_document.stderr.log
```
