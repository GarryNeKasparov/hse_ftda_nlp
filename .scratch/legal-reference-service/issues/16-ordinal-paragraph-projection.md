# 16 — Preserve supported targets under ordinal paragraphs

Status: resolved
Type: task
Blocked by: 14

## What to build

Allow ordinal paragraph selectors and ranges to identify targets without
making their enclosing supported path unprojectable. Keep paragraph out of
the four-field `LawLink` response and preserve distinct target multiplicity.

## Acceptance criteria

- [x] Extract the supported enclosing path from `абзаца первого части 1
  статьи 284 ГПК РФ` and project article `284`, part `1`, and law ID `6`.
- [x] Cover ordinal paragraph selectors under an article, part, and point.
- [x] Expand agreed ordinal lists and ranges into one target per paragraph
  selector while retaining the enclosing supported values.
- [x] Preserve distinct paragraph occurrences even when omission of paragraph
  produces identical projected `LawLink` values.
- [x] Keep ordinary non-citation ordinal prose from creating a link.
- [x] Add analyzer and `/detect` regressions and save focused evaluation
  evidence in a separate experiment directory.

## Answer

Paragraph ordinals from first through twentieth, plus round tens through
hundredth, are normalized to decimal positions in the semantic analyzer.
Ordinal lists and ranges expand under paragraph markers and retain their full
article/part/point path internally. The mapper omits paragraph as before and
emits one API link per paragraph target, including repeated identical links.
Unmapped ordinal words remain unresolved; ordinary ordinal prose is not a
reference.

All 119 tests passed. Six focused analyzer/API cases and the full-document
comparison are recorded in
[`analysis-report.md`](../../../logs/experiments/issue-16-20261009T132134Z/analysis-report.md).
On the same agent-reviewed document, links improved from Issue 15's 276 TP / 7
FP / 38 FN to 299 / 7 / 15; the labels are not human-adjudicated.
