# 17 — Recognize explicit law titles without stale context inheritance

Status: open
Type: task
Blocked by: 14

## What to build

Recognize the measured long law and treaty title forms as explicit citation
evidence. Resolve titles present in the alias data; retain unresolved identity
for titles without an alias and prevent a previous law ID from filling that
identity.

## Acceptance criteria

- [ ] Resolve the dated Federal Law No. 262-ФЗ title to law ID `287` in both
  measured occurrences.
- [ ] Keep the ombudsman law and Convention references at `law_id=null` when
  the alias data has no matching identity, even after a ГПК РФ citation.
- [ ] Include `пунктом 1 статьи 6 Конвенции о защите прав человека и основных
  свобод` as the focused Convention regression and leave its law unresolved.
- [ ] Preserve complete explicit law-title spans, including the federal
  constitutional law title after `статьями 9 и 14`.
- [ ] Preserve a valid following reference and its own law identity after an
  unresolved explicit title.
- [ ] Add negative cases for unrelated prose and near-matching titles so
  recognition does not absorb text or invent an alias.
- [ ] Cover analyzer identity status, source spans, and final `/detect` links;
  save focused evaluation evidence in a separate experiment directory.
