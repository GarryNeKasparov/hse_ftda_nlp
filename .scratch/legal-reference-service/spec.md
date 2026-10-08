# Legal reference extraction service specification

Status: ready-for-agent

Synthesized from the assignment and agreed conversation decisions. The user
confirmed the test seams. Unresolved interpretation policies are identified
below; implementation of their affected cases requires explicit decisions.

## Problem Statement

A caller needs to identify legal provisions mentioned in Russian text and
receive one structured legal reference per provision. References contain
inflected names, abbreviations, omitted hierarchy levels, lists, ranges, and
coordinated branches. A mentioned law may be known, unknown, unspecified, or
ambiguous. Misinterpreting the structure can attach a point to the wrong
article or resolve a law to the wrong identity.

The service connects syntax analysis, an explicit shared semantic analyzer,
and a `/detect` mapper. Coordinated branches, supported integer ranges, and
projection into the fixed LawLink fields are implemented. Contextual
resolution and workload evaluation remain future work.

## Solution

Provide a Dockerized FastAPI service accepting text through POST /detect and
returning a links collection of LawLink records. Each record describes one
legal provision through the stated law, article, point or part, and subpoint.
Unspecified and unknown laws must not prevent extraction.

Use a grammar-based pipeline that preserves original source spans and
competing interpretations until the stage responsible for resolving them.
Separate structural parsing, law identity, contextual resolution, and API
mapping so that uncertainty at one stage does not silently invent information
at another. Preserve repeated textual occurrences and expand grouped legal
references within their own branches.

The remaining implementation work includes contextual interpretation,
representative workload evaluation, and quality measurement. The explicit shared `SemanticAnalyzer`
stage now consumes `Analysis` and returns `SemanticAnalysis` containing
`SemanticReference` occurrences and expanded `ProvisionPath` values. Further
semantic tickets extend this same stage and representation. Policies listed
as open below need an explicit decision before their affected output cases
can serve as definitive acceptance criteria.

## User Stories

1. As a service caller, I want to submit Russian text, so that I can obtain its legal references automatically.
2. As a service caller, I want a links collection of LawLink records, so that I can consume the result through the assignment's API contract.
3. As a service caller, I want one record per individual legal provision, so that a grouped reference has explicit targets.
4. As a service caller, I want full and abbreviated hierarchy markers recognized, so that normal citation styles are supported.
5. As a service caller, I want inflected hierarchy words recognized, so that grammatical case does not hide a reference.
6. As a service caller, I want пп. interpreted as subpoint under the README convention, so that the worked examples retain their intended hierarchy.
7. As a service caller, I want inflected law aliases matched, so that names absent from the dictionary in their exact surface form can still identify known laws.
8. As a service caller, I want capitalization and supported punctuation variants normalized, so that superficial spelling differences do not hide references.
9. As a service caller, I want supported marker and full-law-name typos handled conservatively, so that damaged text remains extractable.
10. As a service caller, I want provision identifiers preserved as strings, so that dotted, lettered, superscript, and hyphenated labels retain their identity.
11. As a service caller, I want omitted hierarchy levels left absent, so that a point-only reference does not acquire an invented article.
12. As a service caller, I want known law aliases resolved to their supplied IDs, so that extracted provisions can be connected to the law database.
13. As a service caller, I want references to recognizable unknown laws retained, so that dictionary coverage does not limit extraction to known acts.
14. As a service caller, I want references without an explicit law retained, so that an article mention such as ст. 6 is not discarded.
15. As an analyst, I want unknown laws distinguished from unspecified laws internally, so that absence of a name is distinguishable from an unrecognized name.
16. As an analyst, I want every candidate ID retained for an ambiguous law alias, so that matching does not silently choose an identity.
17. As an analyst, I want original source spans and spelling retained, so that I can inspect the evidence behind an extracted candidate.
18. As an analyst, I want competing structural interpretations retained, so that unresolved attachment can be examined before API projection.
19. As an analyst, I want self and anaphoric targets represented explicitly, so that a future context resolver can operate on them without invented IDs or provision numbers.
20. As a service caller, I want selector lists expanded within a branch, so that each listed provision receives a record.
21. As a service caller, I want lists at multiple levels combined within their branch, so that subpoints а and б under points 1 and 2 identify four provisions.
22. As a service caller, I want coordinated branches kept separate, so that the expansion does not combine unrelated articles or laws.
23. As a service caller, I want a supported shared article or law attached to the appropriate branches, so that compact legal references remain meaningful.
24. As a service caller, I want unambiguous integer ranges expanded inclusively, so that each referenced integer provision is returned.
25. As an analyst, I want hyphenated identifiers distinguished from possible ranges, so that expansion does not invent provisions.
26. As a service caller, I want repeated occurrences preserved in textual order, so that the result reflects the source's mentions.
27. As an analyst, I want an incomplete candidate accompanied by a diagnostic, so that malformed input remains reviewable.
28. As a service caller, I want valid citations following malformed material extracted, so that one damaged passage does not stop the analysis.
29. As a developer, I want analyzer behavior tested through its public interface, so that tests remain useful when internal stages change.
30. As a developer, I want the final response tested through POST /detect, so that extraction and serialization satisfy the actual caller contract.
31. As a developer, I want grammar analysis and an independent parser cross-check recorded, so that parser choices and ambiguities have reproducible evidence.
32. As a developer, I want experiment inputs, versions, timings, results, and console logs saved together, so that another developer can assess each run.
33. As an operator, I want the service available in Docker on port 8978, so that it runs in the assignment's evaluation environment.
34. As a submitting team, I want representative quality and runtime measurements, so that we can assess progress toward the hidden benchmarks without mistaking small test coverage for benchmark success.

## Implementation Decisions

- Preserve the existing API: a text string in the request and a links collection in the response. Each LawLink contains nullable law_id, article, point_article, and subpoint_article. A known law ID is an integer; provision identifiers are strings.
- Keep the existing analyzer interface, ReferenceAnalyzer.analyze(text), as the public extraction boundary. Its Analysis contains lexical candidates, candidate spans, AST alternatives, and diagnostics.
- Use the revised pipeline: original text, tokenization, normalization alternatives, lexical recognition, candidate discovery and parsing, AST, contextual resolution when defined, and output mapping. Unknown-law recognition and law-alias matching belong to lexical recognition; boundary discovery may be integrated with parsing.
- Retain original Python string offsets and source spelling. Lookup normalization must not change the coordinate system of the input text.
- Preserve morphological alternatives and all ambiguous law IDs internally. For public projection, use the smallest candidate ID when a law alias remains ambiguous and record an internal diagnostic.
- Use the supplied law alias database for known documents. The database has no established guarantee of covering every law mentioned in input.
- Recognize unknown laws initially through explicit numbered federal-law mentions, quoted titles, and names ending in an inflected form of кодекс. Exact unknown-name boundaries remain heuristic and need evaluation.
- Interpret пп. as a subpoint for this assignment. The raw abbreviation may remain represented by a dedicated terminal, but its grammar production must be a subpoint production.
- Keep paragraph, subpoint, point, article part, article, and law distinct internally. Omitted levels remain absent.
- Use one explicit `SemanticAnalyzer` between syntax analysis and output mapping. It consumes `Analysis` and returns `SemanticAnalysis` containing `SemanticReference` occurrences with expanded `ProvisionPath` values. A separate `ContextualResolver` pass consumes these references before mapping; later semantic tickets extend the same representation.
- Expand comma and conjunction selector lists along a provision path, combining nested selector values only within that path. Preserve separate occurrences and law identities. Compare competing AST alternatives by their provision paths before accepting an interpretation.
- Build and assess the CFG before choosing deterministic parsing rules. The current implementation uses Lark Earley and retains explicit alternatives; evidence does not support treating the current grammar as LL or LR.
- Use normalization and exact matching first. Bounded Levenshtein fallback applies to supported full hierarchy words and sufficiently long law names. Short abbreviations and provision identifiers require exact matching after normalization. Existing edit thresholds are prototype defaults pending corpus evaluation.
- Preserve individual selectors, lists, ranges, coordination, and shared-tail structure in the AST until semantic interpretation and expansion.
- Compare AST alternatives by the provision paths they describe before adopting attachment preferences. Different tree groupings can describe the same provisions. Equality of interpretation must not deduplicate repeated source occurrences.
- Expand selector lists across levels within one branch. Keep separate coordinated branches separate. Expand unambiguous integer ranges inclusively.
- Preserve competing atomic-identifier and range readings where hyphens are ambiguous. Letter-range and shortened dotted-range policies are still open.
- Extract an unspecified-law reference with unresolved identity before contextual resolution. A separate left-to-right resolver fills an omitted law from the most recent law context and retains unresolved identity if no context exists.
- Preserve recognizable unknown-law references with unresolved identity and internal supporting evidence; their eventual law_id is null. An ambiguous law retains all candidate IDs and status internally; its projected law_id is the smallest candidate ID.
- Retain self and anaphoric structural targets for contextual resolution. The parser does not supply a numeric identifier for настоящей статьи or a law ID for указанного закона. The resolver uses the most recent compatible context as a fallback because enclosing-document context is unavailable in text-only input.
- Retain incomplete candidate prefixes with local diagnostics and continue searching for later legal references. A connector joining a valid later reference is not automatically a dangling continuation.
- Preserve repeated occurrences in textual order. Final occurrence selection must handle overlapping prefixes from candidate discovery without treating each prefix as a separate final mention; the selection policy remains open.
- Project article to article, point to point_article, and subpoint to subpoint_article. A part alone maps to point_article; when both part and point occur, project the point and omit the part. Omit paragraph from the response while retaining other supported values. Record internal diagnostics when hierarchy levels are omitted.
- Integrate the analyzer and subsequent output stages into the service after the relevant interpretation and projection policies are defined. Reuse initialized recognition resources across requests rather than constructing the full analyzer for every request.
- Package the grammar, recognition dependencies, law aliases, and service code in the Docker image. Keep port 8978 and the /detect route required by the assignment.
- Save each experiment in a separate log directory with input/source snapshots, hashes, interpreter and dependency versions, command, duration, exit status, and captured output. Historical runs retain their original results.
- Use grammar-based extraction as the current approach. The assignment does not require an ML model, and no ML training stage has been agreed.

## Testing Decisions

- The user confirmed two existing seams: ReferenceAnalyzer.analyze(text) for extraction behavior and POST /detect for final LawLink behavior. Prefer these to tests of each internal stage in isolation.
- A good test asserts observable meaning: the reference span, stated hierarchy, identifier values, candidate law IDs and identity status, alternatives, diagnostic, occurrence order, or final API response. Avoid assertions about private helper calls, grammar-node counts, or incidental traversal order unless that structure encodes a domain decision.
- Use the existing analyzer acceptance suite as prior art. It covers known and unknown laws, alias collisions, normalization, bounded typos, original offsets, contextual targets, hyphen ambiguity, malformed continuation recovery, and repeated mentions.
- Verify the README's nested example as subpoint 1, point 1, article 374 of the explicitly named law. Include a simple пп. reference without a following point to ensure it does not acquire a point reading.
- Verify ст. 6 without an explicit law as a complete article candidate with no law ID. Context inheritance receives separate acceptance cases only after its rules are decided.
- Preserve the five structural challenge inputs in the analyzer suite: article lists, coordinated references naming different laws, point lists under a part and article, mixed-depth branches sharing an article, and ordinal paragraphs under higher levels.
- For expansion, assert complete provision records and correlations, including the three-record README subpoint list and combinations restricted to a single branch. Add definitive expectations only for agreed interpretation policies.
- For the API, assert request and response shape, nullable absent values, string provision identifiers, integer known law IDs, one output per provision, and preservation of repeated occurrences.
- Include negative examples and ordinary prose in evaluation, so that precision is measured alongside extraction successes. Candidate retention alone is not a precision measurement for the final service.
- Continue the independent CFG derivation-count and Earley cross-check over manually annotated tokens. These tests establish structural agreement on their fixtures; they do not validate Russian lexing or final API interpretation.
- Use TDD for behavioral implementation: record a meaningful failing interface test, implement the behavior, and run the checks appropriate to the changed behavior.
- Record analyzer construction and per-text processing costs separately in workload evaluation. Also measure service request overhead and document the workload and environment. The assignment limits the aggregate four hidden benchmarks, each containing 500 texts, to five minutes.
- Keep exact benchmark results distinct from small-suite pass rates. No local run can establish hidden-baseline success without access to that evaluation.

## Out of Scope

- Retrieving the full text of laws, verifying that a provision exists, or determining whether it is current or repealed.
- Legal advice or verification of the factual legal statements surrounding a reference.
- Expanding the supplied law database or assuming that it is exhaustive.
- ML training as a prerequisite for the current solution.
- Deduplicating repeated textual occurrences in the extraction response.
- Adding response fields to express the entire internal AST without an explicit API-contract decision.
- Applying alternate meanings of пп. from broader legal writing to this assignment's default interpretation.
- Inferring enclosing-document identity that is absent from the input text.
- Treating letter ranges, shortened dotted ranges, or atomic hyphenated identifiers as settled expansion cases.
- Committing to arbitrary intervening prose, parenthetical interruptions, forward-order references, chapters, appendices, or publication-coordinate parsing in the initial conventional-reference milestone. These remain potential coverage extensions to assess against task examples.
- Automatic deployment, public repository publication, or submission to the instructor as part of specification drafting.

## Further Notes

The current milestone is a raw-text reference service backed by the analyzer
and AST alternatives. The latest recorded analyzer and API acceptance run
passes 66 tests. The structural
experiment passes all 35 annotated cases, with four cases admitting multiple
derivations and 35 LL(1) conflict cells. Strict LALR rejects the current
grammar. These measures describe the selected fixtures; they are not
extraction precision, recall, or hidden-benchmark performance. The Docker image
has not yet been built in this environment.

The following decisions remain necessary for the affected implementation stages:

- **Occurrence selection:** how to choose final mentions from overlapping candidate prefixes while preserving separate repeated occurrences.
- **Structural interpretation:** how to select article/law attachment when alternatives describe different provisions, and how to recognize alternatives with equal meaning.
- **Range interpretation:** how to distinguish atomic hyphenated labels from ranges, and whether letter or shortened dotted ranges can be expanded safely.
- **Coverage and thresholds:** how unknown-law boundaries, fuzzy thresholds, false positives, and runtime behave on a representative annotated corpus.

The existing research records evidence of broader legal conventions, including
alternate uses of пп. The user's latest assignment-specific decision governs
the implementation described here.

This specification is published in the project's local Markdown issue tracker.
Its ready-for-agent status permits work on agreed requirements. Resolve any
remaining interpretation policies explicitly before implementing their
affected output cases.
