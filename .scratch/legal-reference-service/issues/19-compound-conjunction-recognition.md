# 19 — Recognize compound conjunctions without duplicate lexical alternatives

**What to build:** Make grouped legal references containing `и (или)` produce
the same ordered provision paths and `LawLink` response as equivalent lists
joined by `и` or `или`. Recognize the compound conjunction as one `AND_OR`
token spanning the whole phrase, while ordinary `и` and `или` produce `AND`
and `OR` respectively, without redundant `AND_OR` alternatives.

**Blocked by:** None — can start immediately.

Status: resolved

## Context

The conjunction contract and the completed selector-list task include
`и (или)`. However, the current lexer emits two alternatives for each ordinary
conjunction and does not recognize the parenthesized phrase as one token.
Observed behavior:

- `статьи 5 и 6 НК РФ` and `статьи 5 или 6 НК РФ` each produce two syntax
  alternatives for the complete reference solely because of duplicated
  conjunction token types. Both alternatives yield identical provision paths.
- `статьи 5 и (или) 6 НК РФ` produces no links and an
  `unfinished_continuation` diagnostic.

The grammar already accepts `AND_OR` wherever these conjunctions can join
selectors or branches. The existing semantic analyzer enumerates the
referenced provisions for all three conjunction types.

## Acceptance criteria

- [x] `POST /detect` with `статьи 5 и (или) 6 НК РФ` returns exactly two
  `LawLink` records in source order: law ID 15 with article `5`, followed by
  law ID 15 with article `6`; both have null `point_article` and
  `subpoint_article`.
- [x] The complete compound conjunction produces one `AND_OR` lexical
  candidate covering the original `и (или)` phrase. Its source offsets and
  spelling remain tied to the input. The complete reference is extracted
  with its full source span and without `unfinished_continuation`.
- [x] Compound conjunction recognition is case-insensitive and accepts
  whitespace variations, including `и(или)` and spaces inside parentheses.
  The complete compound is consumed as one conjunction rather than competing
  standalone conjunction fragments.
- [x] Ordinary `и` produces `AND`, and ordinary `или` produces `OR`;
  neither additionally produces `AND_OR` for the same source span. For the
  two ordinary article-list examples above, the complete candidate has one
  AST alternative rather than two equivalent alternatives caused by the lexer.
- [x] `п. 1 и (или) п. 2 ст. 5 НК РФ` produces two provision paths and two
  response records retaining point identifiers `1` and `2`, the shared article
  `5`, and law ID 15.
- [x] Existing list expansion, shared parent levels, source order, and repeated
  reference occurrences continue to follow the current semantic contract.
- [x] Unclosed or malformed compound conjunctions do not fabricate a complete
  reference. Arbitrary parenthesized prose is not treated as a conjunction or
  silently skipped.
- [x] Regression coverage checks lexical classification and source spans,
  semantic provision paths, and the `/detect` response for ordinary and
  compound conjunctions, whitespace variants, and malformed inputs.
- [x] Documentation describing conjunction support agrees with the verified
  raw-text behavior.

## Answer

The lexer now emits ordinary `и` only as `AND`, ordinary `или` only as `OR`,
and recognizes case-insensitive `и (или)` with optional whitespace as one
`AND_OR` candidate spanning the original phrase. Compound and ordinary lists
produce one syntax alternative and the expected ordered API links, including
shared article paths for point lists. Malformed parenthesized forms do not
produce a complete citation over the malformed source.

Regression coverage was added for lexical kind and offsets, parse alternatives,
malformed forms, and `/detect` output. The parser and API suites passed (89
tests); full discovery passed (131 tests). The implementation and verification
are recorded in the change commit.
