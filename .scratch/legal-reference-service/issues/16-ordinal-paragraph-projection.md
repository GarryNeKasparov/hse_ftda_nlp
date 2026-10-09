# 16 — Preserve supported targets under ordinal paragraphs

Status: open
Type: task
Blocked by: 14

## What to build

Allow ordinal paragraph selectors and ranges to identify targets without
making their enclosing supported path unprojectable. Keep paragraph out of
the four-field `LawLink` response and preserve distinct target multiplicity.

## Acceptance criteria

- [ ] Extract the supported enclosing path from `абзаца первого части 1
  статьи 284 ГПК РФ` and project article `284`, part `1`, and law ID `6`.
- [ ] Cover ordinal paragraph selectors under an article, part, and point.
- [ ] Expand agreed ordinal lists and ranges into one target per paragraph
  selector while retaining the enclosing supported values.
- [ ] Preserve distinct paragraph occurrences even when omission of paragraph
  produces identical projected `LawLink` values.
- [ ] Keep ordinary non-citation ordinal prose from creating a link.
- [ ] Add analyzer and `/detect` regressions and save focused evaluation
  evidence in a separate experiment directory.
