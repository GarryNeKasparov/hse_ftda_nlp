# 14 — Decide and scope full-document extraction gaps

Status: resolved
Type: task
Blocked by: 10

## Evidence

The complete Supreme Court Plenum Resolution No. 13 of 19 June 2012 was sent
through the current `/detect` pipeline. The measured output has 224 true-positive
links, 7 false positives, and 90 false negatives against the separately saved
whole-document annotations. There are 39 mismatched reference occurrences:
33 have no overlapping prediction, four have the right article selectors
assigned to the wrong law, and two have correct links with truncated spans.

Detailed metrics, all expected and predicted spans, hashes, runtime, and the
annotation policy are in [`docs/full-document-quality.md`](../../../docs/full-document-quality.md),
[`data/golden_document-vsrf-13975.json`](../../../data/golden_document-vsrf-13975.json),
and [`logs/experiments/document-quality-vsrf-13975/quality.json`](../../../logs/experiments/document-quality-vsrf-13975/quality.json).
The labels are agent-reviewed, not human-adjudicated. In particular, their
range policy is broader than the currently agreed parser behavior.

## Repeated patterns

- **Inserted article identifiers:** 15 references containing IDs such as
  `6-1`, `327-1`, and `327-2` were missed (18 expected links). Examples:
  `статья 6-1 ГПК РФ`, `частями 1 и 2 статьи 327-2 ГПК РФ`.
- **Ordinal paragraphs:** 13 references were missed (22 expected links),
  including `абзаца второго части 2 статьи 322 ГПК РФ` and
  `абзацы второй - шестой статьи 222 ГПК РФ`. The current parser drops the
  enclosing article as well as the unsupported paragraph selector.
- **ASCII-hyphen ranges:** 8 references were missed (53 expected links),
  including `частей 1-3 и 5 статьи 322 ГПК РФ` and two occurrences of
  `статей 175-189 ГПК РФ`.
- **Law identity errors:** four references inherit ГПК РФ (ID 6) after an
  explicit law or treaty name is missed. The two Federal Law No. 262-ФЗ
  citations should map to ID 287; the ombudsman law and Convention have no
  alias ID and should remain unresolved.
- **Grouped clauses:** three phrases with several provision clauses in one
  citation were dropped, including `части 4 статьи 1, абзаца четвертого
  статьи 222 и пункта 4 статьи 328 ГПК РФ`.
- **Boundary and false-positive cases:** the span is truncated after
  `статьями 9 и 14` before the full federal constitutional law title, and after
  article 330 before the damaged abbreviation `ГП К РФ`. Ordinary `т. п.`
  followed by heading `9.` produces a spurious point 9.

Counts overlap when a citation has multiple difficult features. The detailed
report has the complete inventory.

## Decisions recorded before implementation tickets

- ASCII hyphen-minus expresses an inclusive range only when plurality is
  explicit through selector morphology or coordination, such as `статей
  175-189`, `главу 6 и статьи 175-189`, or `частей 1-3`. Singular
  inserted identifiers such as `327-1` remain atomic. Existing range limits,
  written order, and en/em-dash behavior remain in force.
- Ordinal paragraph selectors and ranges retain the supported enclosing
  article, part, and point values. Paragraph stays omitted from the API, and
  separate paragraph targets retain occurrence multiplicity even when their
  projected links are identical.
- A known explicit title resolves through its alias, including the dated
  Federal Law No. 262-ФЗ title (ID 287). An explicit title or treaty without
  an alias remains `law_id=null` and prevents inheritance of a preceding law.
- Every supported clause in a mixed-level grouped citation survives and
  shares its explicit trailing law. Ordinary `т. п.` followed by a numbered
  heading does not create a point citation across that boundary.
- Use agent-reviewed labels for focused acceptance cases, reviewing affected
  examples and negative cases individually. They are not a human-adjudicated
  benchmark; revisit a label if a policy dispute appears.

## Exact examples

Each case uses the exact source substring from the saved document. `expected`
and `actual` show the four-field `/detect` links. For boundary cases, they also
show the internal semantic reference text because `/detect` does not return
spans. Reasons are hypotheses from the captured output, not confirmed diagnoses.

### 1. Atomic inserted article identifier

**text**

```text
статья 6-1 ГПК  РФ
```

**expected**

```json
{"links":[{"law_id":6,"article":"6-1","point_article":null,"subpoint_article":null}]}
```

**actual**

```json
{"links":[]}
```

**possible reasons**: `6-1` has both an atomic identifier reading and a
hyphen/range reading. The parser keeps competing syntax alternatives, then
does not select an interpretation for this occurrence.

**can affect on already implemented**: choosing the atomic reading for every
hyphen would break numeric range interpretation. Keep existing en/em-dash
expansion, preserve dotted and superscript identifiers, and retain diagnostics
when ASCII hyphen evidence is genuinely ambiguous.

### 2. Selector list attached to an inserted article ID

**text**

```text
частями  1  и  2  статьи  327-2 ГПК  РФ
```

**expected**

```json
{"links":[{"law_id":6,"article":"327-2","point_article":"1","subpoint_article":null},{"law_id":6,"article":"327-2","point_article":"2","subpoint_article":null}]}
```

**actual**

```json
{"links":[]}
```

**possible reasons**: the article identifier ambiguity prevents the enclosing
reference from being selected; the list itself may be parsed correctly in
other contexts.

**can affect on already implemented**: preserve selector-list expansion and
keep both part values attached to article `327-2`. Do not flatten the list into
separate references or alter the existing part-to-`point_article` projection.

### 3. ASCII-hyphen article range

**text**

```text
статьи 175-189 ГПК  РФ
```

**expected**

```json
{"links":[{"law_id":6,"article":"175","point_article":null,"subpoint_article":null},{"law_id":6,"article":"176","point_article":null,"subpoint_article":null},{"law_id":6,"article":"177","point_article":null,"subpoint_article":null},{"law_id":6,"article":"178","point_article":null,"subpoint_article":null},{"law_id":6,"article":"179","point_article":null,"subpoint_article":null},{"law_id":6,"article":"180","point_article":null,"subpoint_article":null},{"law_id":6,"article":"181","point_article":null,"subpoint_article":null},{"law_id":6,"article":"182","point_article":null,"subpoint_article":null},{"law_id":6,"article":"183","point_article":null,"subpoint_article":null},{"law_id":6,"article":"184","point_article":null,"subpoint_article":null},{"law_id":6,"article":"185","point_article":null,"subpoint_article":null},{"law_id":6,"article":"186","point_article":null,"subpoint_article":null},{"law_id":6,"article":"187","point_article":null,"subpoint_article":null},{"law_id":6,"article":"188","point_article":null,"subpoint_article":null},{"law_id":6,"article":"189","point_article":null,"subpoint_article":null}]}
```

**actual**

```json
{"links":[]}
```

**possible reasons**: issue 07 only accepts en/em dash as range markers; ASCII
hyphen-minus is retained as ambiguous with an atomic identifier.

**can affect on already implemented**: expanding all ASCII hyphens could turn
article IDs such as `327-1` into ranges. Preserve the existing range size cap,
written order, and atomic-identifier handling. This expected expansion also
needs policy approval because the gold labels go beyond issue 07's current
contract.

### 4. Ordinal paragraph before a supported part and article

**text**

```text
абзаца первого части  1  статьи  284  ГПК  РФ
```

**expected**

```json
{"links":[{"law_id":6,"article":"284","point_article":"1","subpoint_article":null}]}
```

**actual**

```json
{"links":[]}
```

**possible reasons**: the selector parser recognizes the ordinal paragraph,
but semantic expansion rejects a non-scalar/ordinal selector and drops the
whole reference.

**can affect on already implemented**: retain paragraph distinctions
internally while projecting the existing article and part values. Preserve
normal numeric paragraph handling, nested selector correlations, and the API's
current omission of paragraph. Gold scoring counts one target per paragraph,
including duplicates after projection; confirm that policy before adopting it.

### 5. Explicit unrecognized law after a previous known law

**text**

```text
подпункта  1  пункта  1  статьи  29
Федерального  конституционного  закона  от  26  февраля   1997 года
N 1-ФКЗ  "Об Уполномоченном  по  правам   человека   в   Российской
Федерации"
```

**expected**

```json
{"links":[{"law_id":null,"article":"29","point_article":"1","subpoint_article":"1"}]}
```

**actual**

```json
{"links":[{"law_id":6,"article":"29","point_article":"1","subpoint_article":"1"}]}
```

The predicted semantic span is only `подпункта  1  пункта  1  статьи  29`;
it stops before the named law.

**possible reasons**: the multiline dated federal constitutional law title is
not recognized as part of this candidate. The resolver then treats the law as
omitted and inherits the preceding ГПК РФ identity.

**can affect on already implemented**: preserve issue 11's protection against
stale context for explicit unknown laws. Do not clear context for genuinely
omitted law references or change exact known alias resolution.

### 6. Dated known law title is skipped and gets the prior law ID

**text**

```text
статьями  14  и  16
Федерального   закона   от   22    декабря    2008 года    N 262-ФЗ
"Об обеспечении  доступа  к  информации  о  деятельности  судов   в
Российской Федерации"
```

**expected**

```json
{"links":[{"law_id":287,"article":"14","point_article":null,"subpoint_article":null},{"law_id":287,"article":"16","point_article":null,"subpoint_article":null}]}
```

**actual**

```json
{"links":[{"law_id":6,"article":"14","point_article":null,"subpoint_article":null},{"law_id":6,"article":"16","point_article":null,"subpoint_article":null}]}
```

The predicted semantic span ends at `статьями  14  и  16`.

**possible reasons**: the long dated law descriptor and quoted title are not
joined to the article-list candidate, so the resolver inherits law ID 6.

**can affect on already implemented**: preserve short abbreviation matching,
full law-title boundary handling, and compact coordinated law tails from
issues 11 and 13. Recognition of this title must resolve to ID 287 rather than
being treated as an unknown law.

### 7. Several provision clauses in one citation

**text**

```text
части 4 статьи 1, абзаца  четвертого  статьи
222 и пункта 4 статьи 328 ГПК РФ
```

**expected**

```json
{"links":[{"law_id":6,"article":"1","point_article":"4","subpoint_article":null},{"law_id":6,"article":"222","point_article":null,"subpoint_article":null},{"law_id":6,"article":"328","point_article":"4","subpoint_article":null}]}
```

**actual**

```json
{"links":[]}
```

**possible reasons**: mixed-depth clauses (part/article, ordinal paragraph,
point/article) connected by comma and conjunction are not represented as three
coordinated provision branches accepted by semantic selection.

**can affect on already implemented**: preserve issue 06 shared-tail and
branch-local expansion, issue 12 part-before-article commas, and ordinary
article lists. A fix must not attach part 4 or point 4 to every article.

### 8. Citation span stops before full unknown-law title

**text**

```text
статьями 9 и  14  Федерального  конституционного  закона
"О судах общей юрисдикции  в  Российской  Федерации"
```

**expected**

```json
{"text":"статьями 9 и  14  Федерального  конституционного  закона\n\"О судах общей юрисдикции  в  Российской  Федерации\"","links":[{"law_id":null,"article":"9","point_article":null,"subpoint_article":null},{"law_id":null,"article":"14","point_article":null,"subpoint_article":null}]}
```

**actual**

```json
{"text":"статьями 9 и  14","links":[{"law_id":null,"article":"9","point_article":null,"subpoint_article":null},{"law_id":null,"article":"14","point_article":null,"subpoint_article":null}]}
```

**possible reasons**: this federal constitutional law descriptor/title form is
not recognized as a law tail for the candidate.

**can affect on already implemented**: preserve issue 11's full spans for
explicit law names and issue 13's rule that spans include complete short law
abbreviations without absorbing following prose.

### 9. Ordinary abbreviation followed by a numbered heading

**text** (local source context)

```text
нахождение  в  командировке  или  отпуске,   отсутствие   в   штате
организации юриста и т. п.
     9. Исходя из положений пункта 5 части  1  статьи  225  ГПК  РФ
```

**expected**

```json
{"links":[]}
```

This expected value applies to the `т. п.` plus heading occurrence only; the
later article 225 citation is a separate valid reference.

**actual**

```json
{"links":[{"law_id":6,"article":null,"point_article":"9","subpoint_article":null}]}
```

The false-positive predicted text is `п.\n     9`.

**possible reasons**: the abbreviation `п.` from `т. п.` is allowed to take the
next number as a point selector across a paragraph break and heading boundary.

**can affect on already implemented**: do not reject valid point-only
references such as `п. 9`, or valid numbered citations later in the same text.
Treat the abbreviation's sentence/heading boundary as evidence that the `9.`
starts a new section.

## Follow-up implementation tickets

- [15 — Inserted identifiers and plural ASCII ranges](15-inserted-identifiers-and-ascii-ranges.md)
- [16 — Ordinal paragraph projection](16-ordinal-paragraph-projection.md)
- [17 — Explicit law titles and context safety](17-explicit-law-titles-and-context-safety.md)
- [18 — Mixed-level groups and heading boundaries](18-mixed-level-groups-and-heading-boundaries.md)

## Answer

The feature spec now records the behavior decisions and evidence limits above.
Four implementation tickets split the measured gaps into focused slices. The
agent-reviewed document labels can seed targeted cases, with negative coverage
and individual review of affected examples; no claim of human adjudication is
made.
