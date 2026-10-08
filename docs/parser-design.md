# Legal reference parser: agreed rules

This document records the design and current implementation boundary. The
grammar has an executable raw-text analyzer and an API projection that keeps
all supported fields even when the internal path has extra levels. Contextual
resolution remains deferred.

## Current analyzer

`reference_parser.py` exposes `ReferenceAnalyzer.from_alias_file(path)` and
`analyze(text) -> Analysis`. The analysis contains lexical candidates,
source-positioned candidate spans, grammar-preserving AST alternatives, and
candidate-local diagnostics. It keeps overlapping spans and repeated
occurrences. The service projects interpreted provision paths into `LawLink`
records, expanding coordinated groups and preserving unsupported levels
internally for diagnostic purposes.

The implementation tokenizes the original string and retains Python string
offsets, applies Unicode normalization and case folding for lookup, uses
pymorphy3 to retain morphological alternatives, matches aliases from
`law_aliases.json`, and uses bounded Levenshtein fallback for full law names
and hierarchy-marker words. Law ID collisions remain as multiple IDs.
Recognizable unknown federal-law numbers, quoted titles, and code names are
retained with unknown status. Self and anaphoric targets are structural leaves
without invented IDs. Earley parses available lexical paths and retains
ambiguity.

This is a first extraction milestone, not a claim of complete Russian legal
reference coverage. Unknown-document detection is heuristic; fuzzy thresholds
are implementation defaults; offsets are Python string indices; no context
resolver assigns omitted laws; publication coordinates and workload
benchmarking remain open.

The acceptance suite is run and snapshotted with
`tools/run_reference_experiment.py`. Each invocation stores input hashes,
environment, duration, exit code, and stdout/stderr under
`logs/experiments/reference-*`.

## Recognition

- Normalize before structural parsing, preserving meaningful punctuation and original text positions.
- Build the grammar and assess its properties before choosing a parser algorithm. The proposed order subpoint → point or part → article → law is a hypothesis to assess against more complex examples, not a guaranteed property of the inputs.
- Extract references without an explicit law with `law_id=null`. Contextual law inheritance is a separate responsibility from structural parsing; any inheritance requires an unambiguous antecedent, whose criteria remain undecided.
- Preserve explicitly stated levels: `п. 10 АПК` has point `10` and no article.
- Resolve known laws through normalized aliases in `law_aliases.json`.
- Interpret `пп.` as a subpoint in accordance with the README's examples: `пп. 1 п. 1 ст. 374 НК РФ`.
- Retain recognizable references to unknown laws with `law_id=null`.
- Initially recognize unknown laws by explicit forms: numbered federal laws, quoted law titles, and phrases ending in an inflected form of `кодекс`.

## Normalization and fuzzy matching

- Handle capitalization, whitespace, punctuation variants, inflected markers and law names, and explicit sample typos.
- Try exact matching after normalization first.
- Permit bounded Levenshtein matching for full hierarchy words and full law names when needed.
- Require exact matching after normalization for short abbreviations and provision identifiers.
- Keep ambiguous law matches unresolved internally with all candidate IDs. The API deterministically projects the smallest ID, as agreed in ticket 08.
- The fuzzy thresholds and method for normalizing Russian inflections remain undecided.

## Expansion

- Emit one output per individual provision.
- Expand lists at different levels within one branch into all combinations. Coordinated branches denote alternatives and must remain separate.
- Expand inclusive ranges only when the lexer identifies an en dash (`–`) or
  em dash (`—`) as `RANGE` and both endpoints are plain decimal integer IDs.
  Emit values in ascending written order; reject reversed endpoints. A short
  hyphen-minus (`-`) remains ambiguous with an atomic identifier and is not
  expanded automatically. Reject ranges that would produce more than 1,000
  values to bound one citation's expansion.
- Letter ranges remain deferred. Legal labels may skip letters, so the expansion alphabet and whether to omit absent labels need an explicit policy.
- Dotted and shortened ranges such as `43.2–6` remain unresolved and are not expanded. Legal texts contain atomic dotted identifiers with hyphens, so range expansion must not infer omitted endpoint prefixes.
- Preserve repeated reference occurrences in textual order. Any future deduplication is a separate post-processing step.

## Cases to assess before settling the grammar

- `статьи 5 и 6 НК РФ`
- `статья 5 НК РФ и пункт 2 статьи 6 ГК РФ`
- `пункты 2 и 3 части 1 статьи 15`
- `пункт 2 части 1 и часть 3 статьи 15`
- `абзацы второй и третий пункта 4 части 2 статьи 10`

These five cases are now included in the annotated grammar experiment. The
executable version-1 grammar is [reference-grammar.bnf](reference-grammar.bnf);
its token assumptions and scope are in [grammar-contract.md](grammar-contract.md).
The earlier EBNF file points to that specification.

The reproducible [analysis](grammar-analysis.md) covers 35 manually annotated
acceptance/rejection cases. All match the stated expectations. Four have
multiple derivations; the grammar has 35 LL(1) table conflicts. Explicit
ambiguity witnesses rule out LL(k)/LR(k) for this grammar as written, not for
every equivalent grammar of the intended language. Actual Russian lexing,
normalization, scope selection, and production parser performance are not
validated by this experiment.

The [Lark cross-check](lark-grammar-analysis.md) independently reproduces the
exact derivation counts of all 35 cases using Earley with explicit ambiguity.
Strict LALR construction rejects the unchanged grammar with a shift/reduce
conflict. Lark syntax is generated from the BNF, so there is no second manually
maintained grammar. Experiment dependencies are in `requirements-grammar.txt`.

Lark Earley is suitable for continuing the grammar investigation. Production
selection remains open: no full-text extraction or workload measurement has
been performed. Before adding attachment preferences, the proposed next step
is to project alternative trees into distinct internal provision paths and
compare their meanings. This should separate regroupings with identical
outputs from alternatives that change article/law scope or point/subpoint
type. Such comparison must preserve occurrence order and repeated mentions;
it must not deduplicate the reference output. Selection policies still need
evidence or explicit agreement.

## Output and context decisions

- When both point and part occur, project the point into `point_article` and omit the part from the API response. A part without a point maps to `point_article`.
- Omit paragraphs from the API response but continue projecting article, point/part, and subpoint values. Retain paragraph values internally.
- For an ambiguous law alias, project the smallest candidate ID to `law_id`. Retain the ambiguous status and all candidate IDs internally and record a mapping diagnostic.
- Initially return `law_id=null` for references without an explicit law. Contextual inheritance is deferred.
- Preserve distinct hierarchy levels internally even when the API projection omits one.

## Open decisions

- Exact extraction strategy, grammar, and parser algorithm.
- Where to retain supporting information about unresolved laws.
- Exact unknown-name boundaries and lexical rules.
- What counts as an unambiguous antecedent if contextual resolution is added later.
- Whether to support alternate meanings of abbreviations such as `пп.` in legal texts beyond this assignment's README convention.
- The ordering used for letter ranges and treatment of inserted identifiers within ranges.
- Distinguishing hyphenated atomic identifiers from ranges and preserving superscripts in output.

## Research implications for the next grammar draft

See [legal-reference-research.md](legal-reference-research.md) for primary evidence, inferred rules, and retrieval limitations.

- Keep paragraph, subpoint, point, article part, and article distinct internally; the API projects only fields it supports.
- Preserve atomic identifiers, including multiple dots, letter-plus-number labels, superscript suffixes, and hyphens. Marker type determines the stated level; identifier shape alone does not.
- Distinguish single selectors, lists, and ranges before expansion.
- Represent coordination and shared tails explicitly. A shared tail may be an article or a law; Cartesian expansion is scoped to one branch.
- Permit omitted, self-referential, and anaphoric law targets in the internal model without assuming contextual identity has been resolved.
- Separate document matching from unique ID resolution. Some exact dictionary aliases already have multiple candidate IDs.
- Include known aliases for decrees, orders, and other supplied document kinds, not only federal statutes and codes.
- Preserve publication coordinates as a distinct context so an official-publication item marked `ст.` is not confused with a law article.
- Preserve source spans and superscript boundaries during normalization. Fuzzy matching does not settle structural or identity ambiguity.

These are evidence-driven requirements to consider while refining the grammar, not a claim that the current draft implements them or belongs to an LL/LR class.

## Evidence from legal texts

A Supreme Court review approved on 28 September 2016, page 3, uses
`пунктом 1 части 1 и частью 2 статьи 31`. This is a direct example of
coordinated branches of different depths sharing a trailing article.
The corresponding interpretation is point 1 of part 1 of article 31,
and part 2 of article 31. This supports interpreting
`пункт 2 части 1 и часть 3 статьи 15` with article 15 shared by both branches.
It does not establish a universal attachment rule for all coordination.

Source: https://vsrf.ru/Show_pdf.php?Id=11033

A Constitutional Court notice also refers to the single
`частью 1.3-3 статьи 32.2`. Thus dotted identifiers containing a hyphen
can identify one provision; they are not necessarily shortened ranges.
The previously agreed expansion of `43.2–6` remains provisional and needs
reconsideration in light of this counterexample.

Source: https://www.ksrf.ru/news/19406/
