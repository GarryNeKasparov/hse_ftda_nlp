# 15 — Preserve inserted identifiers and expand plural ASCII ranges

Status: resolved
Type: task
Blocked by: 14

## What to build

Recognize singular inserted article identifiers as atomic strings, and expand
ascending plain-integer ranges written with ASCII hyphen-minus only when the
selector is explicitly plural. Preserve existing en/em-dash range behavior,
limits, written order, branch context, and law identity.

## Acceptance criteria

- [x] Extract `статья 6-1 ГПК РФ` as article `6-1` rather than a range.
- [x] Expand the part list in `частями 1 и 2 статьи 327-2 ГПК РФ`, keeping
  article `327-2` atomic and attaching both parts to it.
- [x] Expand the explicitly plural range in `главу 6 и статьи 175-189 ГПК РФ`
  inclusively and in written order.
- [x] Cover a plural range followed by a list item, such as `частей 1-3 и 5`.
- [x] Preserve current range limits and reject reversed, malformed, or
  unsupported forms with diagnostics instead of inventing targets.
- [x] Add negative coverage for singular inserted IDs and existing ambiguous
  hyphenated labels; retain focused analyzer and `/detect` assertions.
- [x] Evaluate focused whole-document examples and save the run evidence in a
  separate experiment directory.

## Answer

The parser now uses selector morphology and coordination to classify ASCII
hyphens. Explicitly plural ascending integer ranges expand through the shared
semantic analyzer; singular inserted article identifiers remain atomic, while
other ambiguous hyphenated labels stay unresolved. Malformed range continuations
no longer emit their first selector as a complete reference.

The full suite passes (110 tests). The ten-case analyzer/API experiment and
whole-document comparison are recorded in
[`analysis-report.md`](../../../logs/experiments/issue-15-20261009T125655Z/analysis-report.md).
On the fixed document, API link metrics improved from 224 TP / 7 FP / 90 FN to
276 TP / 7 FP / 38 FN; remaining gaps are outside this ticket's scope.
