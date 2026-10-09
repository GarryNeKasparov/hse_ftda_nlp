# Reference grammar version 1

The executable specification is [reference-grammar.bnf](reference-grammar.bnf).
Its properties and example derivations are recorded in [grammar-analysis.md](grammar-analysis.md).
The grammar is an experiment over normalized reference candidates; it is not a whole-text extractor.

## Token contract

Terminals represent already recognized lexical items. The examples in
[grammar-examples.json](grammar-examples.json) are manually annotated; their
acceptance does not demonstrate that Russian normalization or law matching works.
Each whitespace-separated fixture token has the form `TYPE` or `TYPE:value`.
Underscores in a fixture's law label stand for spaces for display purposes.

| Terminal | Meaning | Example |
|---|---|---|
| `PARAGRAPH` | Explicit paragraph marker | абзацы |
| `SUBPOINT` | Unambiguous subpoint marker | подпункту |
| `POINT` | Unambiguous point marker | пункта |
| `PART` | Article-part marker | частью |
| `ARTICLE` | Article marker | статьи |
| `PP` | Subpoint abbreviation under this assignment's examples | пп. |
| `ID` | An opaque provision identifier | 3.345, а, а.1, 1.3-3, 159¹ |
| `ORDINAL` | An ordinal expression whose spelling remains available | второй |
| `RANGE` | A separator already classified as a range operator | – in an annotated 5–7 range |
| `AND`, `OR`, `AND_OR` | Coordinating conjunctions | и, или, и (или) |
| `COMMA` | A comma retained for structural interpretation | , |
| `IN` | A permitted bridge before a parent level | в |
| `LAW` | An explicit act-name span | НК РФ, an unknown quoted law title |
| `SELF_LAW` | A mention of the enclosing act | настоящего закона |
| `ANAPHORIC_LAW` | A mention requiring a contextual antecedent | указанного закона |
| `SELF_ARTICLE`, `SELF_PART`, `SELF_POINT`, `SELF_SUBPOINT`, `SELF_PARAGRAPH` | An enclosing structural unit with no invented numeric identifier | настоящей статьи |

A future lexer must retain original offsets, raw spelling, normalization
alternatives, and candidate law IDs. `LAW` recognition does not assert a unique
ID; `ORDINAL` recognition does not assert a final numeric serialization.

A hyphen-minus may belong to an `ID` or denote a `RANGE`. Treat it as a range
separator when selector plurality is explicit through morphology or
coordination; singular inserted article identifiers remain atomic. Keep other
ambiguous readings unresolved. En dash and em dash are lexed as explicit
`RANGE` separators. Semantic expansion accepts only ascending ranges whose
two endpoints are plain decimal integer IDs. Dotted, shortened, letter,
reversed, and oversized ranges are not expanded. Ordinal ranges are supported
only for paragraph selectors: Russian ordinals from first through twentieth
and the round tens through hundredth are normalized to decimal positions;
ordinal lists and ranges use the same inclusive size limit. Other ordinal
forms remain unresolved.
Under the assignment's README convention, `PP` maps to subpoint. Broader legal
texts may use the same abbreviation differently; those readings are outside
this homework-specific token contract.

## Structural scope

The working order is paragraph → subpoint → point → article part → article → act.
This is a hypothesis for the conventional reverse-order subset, with omitted
levels allowed. It is not a claim about all Russian legal references.

Each `*_group` ends with its highest stated level. Its preceding children are
lower groups, possibly coordinated. This can represent a shared parent:

```text
article 15
├── part 1
│   └── point 2
└── part 3
```

Adjacent levels form a path; `IN` and a comma may bridge them. Conjunctions join
selectors or branches rather than nesting levels automatically. Lists/ranges
remain syntax nodes for later expansion. A hyphenated label remains a string,
not a floating-point number or an implicitly expanded sequence.

An explicit act can follow a group of branches. Several references can also
be coordinated. An omitted act is allowed. For one compact coordinated
citation, a single explicit final law scopes each branch; separately named
laws stay attached to their branches. This bounded rule does not define
inheritance across unrelated prose.

The confirmed reading for `пункт 2 части 1 и часть 3 статьи 15` is article 15
containing point 2 of part 1 and part 3. The grammar retains the competing
local reading; semantic analysis selects the uniquely more complete path
interpretation when alternatives preserve the same branch identifiers.
Additional parse trees can differ only in how lawless references are grouped;
those are not necessarily different output provisions.

## Outside this version

- Finding candidate boundaries in arbitrary prose or handling recovery after malformed input.
- Lexical recognition of inflections, typos, quoted titles, dates, and act numbers.
- Arbitrary intervening prose, parenthetical interruptions, exceptions, and references inside quoted amendments.
- Forward-order references, code-volume qualifiers, chapters, sections, and appendices.
- Selecting a law ID, inheriting a law from context, and resolving self references.
- Enumerating inserted/repealed identifiers or skipped letters inside ranges.
- Mapping simultaneous points/parts or paragraphs into the four-field API schema.

The research basis and unresolved assignment questions are in
[legal-reference-research.md](legal-reference-research.md). The specification
can be refined as new assignment examples are assessed; the raw-text analyzer
uses Earley to retain structural alternatives.

## Reproducing the analysis

```bash
python3 tools/analyze_grammar.py
```

The standard-library tool computes nullable, FIRST, FOLLOW, productive and
reachable symbols, and LL(1) table conflicts. It counts derivations of the
annotated cases using memoized spans and retains example trees. Grammars with
same-span recursive cycles are rejected explicitly by the derivation counter.
Multiple derivations provide an ambiguity witness; absence of such a witness
on a finite collection would not prove unambiguity.

## Independent Lark experiment

The [Lark report](lark-grammar-analysis.md) compares Earley derivation counts
with the span analyzer and tries strict LALR construction. Lark syntax is
generated directly from the BNF; the original grammar is unchanged.

```bash
python3 -m venv /tmp/legal-grammar-venv
/tmp/legal-grammar-venv/bin/python -m pip install -r requirements-grammar.txt
/tmp/legal-grammar-venv/bin/python tools/analyze_with_lark.py
```

The experiment uses a surrogate alphabet consisting of token kinds. It does
not implement a lexer for Russian text. Its structural ambiguity cases and
failed strict LALR construction support using Earley for further grammar analysis;
they do not settle production performance or interpretation policies.
