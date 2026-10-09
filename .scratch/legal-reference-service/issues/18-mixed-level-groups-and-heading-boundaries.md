# 18 — Preserve mixed-level groups and reject heading false positives

Status: open
Type: task
Blocked by: 14, 16

## What to build

Extract every supported provision clause in a grouped citation, including
clauses at different hierarchy levels that share a trailing law. Prevent the
abbreviation `т. п.` from consuming a number that begins a later heading.

## Acceptance criteria

- [ ] Extract all three clauses from `части 4 статьи 1, абзаца четвертого
  статьи 222 и пункта 4 статьи 328 ГПК РФ` with the shared law ID `6`.
- [ ] Project article `1` with part `4`, article `222` from the paragraph
  clause, and article `328` with point `4`.
- [ ] Preserve clause order and keep each clause's own hierarchy values; do
  not combine selectors across branches.
- [ ] In the measured `т. п.` passage, emit no point `9` from the next heading
  while still extracting the later valid citation to article `225`.
- [ ] Keep a genuine standalone `п. 9` citation recognizable.
- [ ] Add full-passage analyzer and `/detect` regressions with negative
  coverage; save focused evaluation evidence in a separate experiment
  directory.
