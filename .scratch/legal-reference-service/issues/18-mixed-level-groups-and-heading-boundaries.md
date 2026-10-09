# 18 — Preserve mixed-level groups and reject heading false positives

Status: resolved
Type: task
Blocked by: 14, 16

## What to build

Extract every supported provision clause in a grouped citation, including
clauses at different hierarchy levels that share a trailing law. Prevent the
abbreviation `т. п.` from consuming a number that begins a later heading.

## Acceptance criteria

- [x] Extract all three clauses from `части 4 статьи 1, абзаца четвертого
  статьи 222 и пункта 4 статьи 328 ГПК РФ` with the shared law ID `6`.
- [x] Project article `1` with part `4`, article `222` from the paragraph
  clause, and article `328` with point `4`.
- [x] Preserve clause order and keep each clause's own hierarchy values; do
  not combine selectors across branches.
- [x] In the measured `т. п.` passage, emit no point `9` from the next heading
  while still extracting the later valid citation to article `225`.
- [x] Keep a genuine standalone `п. 9` citation recognizable.
- [x] Add full-passage analyzer and `/detect` regressions with negative
  coverage; save focused evaluation evidence in a separate experiment
  directory.

## Answer

Semantic analysis now keeps all three clauses in the grouped citation as
separate paths and applies the shared ГПК РФ law target without crossing
hierarchy values between branches. The parser rejects a short `п.` marker when
its next numeric token is a dotted heading at the start of a new line; a
standalone `п. 9` remains recognized.

All 128 tests passed. Four focused analyzer/API cases and the whole-document
comparison are recorded in
[`analysis-report.md`](../../../logs/experiments/issue-18-20261009T134900Z/analysis-report.md).
The comparison improved from Issue 17's 305 TP / 1 FP / 9 FN to 308 / 0 / 6.
Labels are agent-reviewed, not human-adjudicated.
