# 15 — Preserve inserted identifiers and expand plural ASCII ranges

Status: open
Type: task
Blocked by: 14

## What to build

Recognize singular hyphenated provision identifiers as atomic strings, and
expand ascending plain-integer ranges written with ASCII hyphen-minus only
when the selector is explicitly plural. Preserve existing en/em-dash range
behavior, limits, written order, branch context, and law identity.

## Acceptance criteria

- [ ] Extract `статья 6-1 ГПК РФ` as article `6-1` rather than a range.
- [ ] Expand the part list in `частями 1 и 2 статьи 327-2 ГПК РФ`, keeping
  article `327-2` atomic and attaching both parts to it.
- [ ] Expand the explicitly plural range in `главу 6 и статьи 175-189 ГПК РФ`
  inclusively and in written order.
- [ ] Cover a plural range followed by a list item, such as `частей 1-3 и 5`.
- [ ] Preserve current range limits and reject reversed, malformed, or
  unsupported forms with diagnostics instead of inventing targets.
- [ ] Add negative coverage for singular inserted IDs and existing ambiguous
  hyphenated labels; retain focused analyzer and `/detect` assertions.
- [ ] Evaluate focused whole-document examples and save the run evidence in a
  separate experiment directory.
