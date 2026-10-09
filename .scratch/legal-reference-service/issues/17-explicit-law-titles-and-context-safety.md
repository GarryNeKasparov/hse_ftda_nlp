# 17 — Recognize explicit law titles without stale context inheritance

Status: resolved
Type: task
Blocked by: 14

## What to build

Recognize the measured long law and treaty title forms as explicit citation
evidence. Resolve titles present in the alias data; retain unresolved identity
for titles without an alias and prevent a previous law ID from filling that
identity.

## Acceptance criteria

- [x] Resolve the dated Federal Law No. 262-ФЗ title to law ID `287` in both
  measured occurrences.
- [x] Keep the ombudsman law and Convention references at `law_id=null` when
  the alias data has no matching identity, even after a ГПК РФ citation.
- [x] Include `пунктом 1 статьи 6 Конвенции о защите прав человека и основных
  свобод` as the focused Convention regression and leave its law unresolved.
- [x] Preserve complete explicit law-title spans, including the federal
  constitutional law title after `статьями 9 и 14`.
- [x] Preserve a valid following reference and its own law identity after an
  unresolved explicit title.
- [x] Add negative cases for unrelated prose and near-matching titles so
  recognition does not absorb text or invent an alias.
- [x] Cover analyzer identity status, source spans, and final `/detect` links;
  save focused evaluation evidence in a separate experiment directory.

## Answer

The parser now recognizes dated federal-law descriptors through their date,
number, and quoted title. Exact quoted aliases resolve to their supplied law
IDs; unlisted law and convention titles remain explicit unknown targets, so
they do not inherit an earlier law ID. The Convention's measured wording and
unrelated-prose/near-title boundaries have focused coverage.

All 124 tests passed. Seven focused analyzer/API cases and the whole-document
comparison are in
[`analysis-report.md`](../../../logs/experiments/issue-17-20261009T134051Z/analysis-report.md).
The comparison improved from Issue 16's 299 TP / 7 FP / 15 FN to 305 / 1 / 9.
The labels are agent-reviewed, not human-adjudicated.
