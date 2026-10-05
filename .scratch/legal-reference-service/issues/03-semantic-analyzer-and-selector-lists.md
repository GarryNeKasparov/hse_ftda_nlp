# Add the semantic analyzer and expand selector lists

Status: resolved

Type: task

## Shared stage contract

Create one explicit `SemanticAnalyzer` that consumes `Analysis` from
`ReferenceAnalyzer.analyze(text)` and returns semantic references made of
`ProvisionPath` values. This is the shared provision representation for later
semantic work: alternative selection, branch coordination, shared-tail
attachment, and additional expansion rules extend this module and its output
types rather than introducing independent semantic stages or parallel IRs.

Each provision path retains law identity status and candidate IDs separately
from article, part, point, subpoint, and paragraph identifiers. Source
occurrence spans stay attached to the semantic reference. The API mapper
converts supported paths into `LawLink` after semantic analysis.

## This ticket's behavior

- Expand comma and `и`, `или`, or `и (или)` selector lists within one
  syntactic branch.
- Carry shared parent selectors and law identity to every expanded provision.
- Preserve selector order and source occurrence identity.
- Leave a complete, single-selector citation as one provision path.
- Merge competing syntax parses only when they yield identical provision
  paths. Decline divergent attachment, ranges, and unsupported coordination
  with semantic diagnostics.
- Split repeated citations in a syntax `reference_tail` into separate semantic
  occurrences, preserving each citation's source span and law identity.
- Keep part and point as separate fields internally. If the final API cannot
  represent a path, the mapper reports it as unprojectable rather than
  collapsing levels.

## Acceptance criteria

- `пп. 1, 2, 3 п. 2 ст. 3 НК РФ` becomes three paths retaining point 2,
  article 3, and law ID 15.
- `пп. 4, 5, 6 и 8 п. 1 ст. 14 ...` becomes four paths, in source order.
- `пункты 1 и 2 статьи 299 ГК РФ` becomes two point paths under article 299.
- `ст. 5 НК РФ и п. 2 ст. 6 ГК РФ` remains two occurrences with their own
  spans and law identities.
- Existing simple citation output remains unchanged through `/detect`.
- Semantic analysis is a named module in the main service pipeline, between
  syntax analysis and `LawLink` mapping.
- An unsupported or incomplete candidate does not leak a misleading partial
  path into the API response.

## Dependencies and extension points

- Depends on the MVP syntax analyzer and mapper (complete).
- Issue 04 and later semantic tickets must extend the `SemanticAnalyzer`,
  `SemanticAnalysis`, `SemanticReference`, and `ProvisionPath` contract.
- Broader coordination and shared-tail policies remain separate decisions.

## Comments

The user explicitly confirmed that semantic analysis must be one visible,
shared stage so multiple tickets build on the same provision object.

## Answer

Implemented `SemanticAnalyzer` in `semantic_analyzer.py`, between syntax
analysis and API mapping. Its shared IR consists of `SemanticAnalysis`,
`SemanticReference`, `ProvisionPath`, and semantic diagnostics. It preserves
separate article, part, point, subpoint, paragraph, law status, candidate IDs,
and source spans. Later semantic work can extend these same objects.

The analyzer expands comma, `и`, `или`, and `и (или)` selector lists, takes
cross products between selector lists nested along the same provision path,
and retains distinct source occurrences. Competing syntax alternatives are
merged only when they produce identical paths. The API mapper projects
representable paths and retains a diagnostic when its four fields cannot
express a path. The service and Docker image now include this stage.

The real document corpus caught a false positive: `участию` was fuzzy-matched
as the marker `частию`. The lexer now rejects a fuzzy marker match when a longer
word merely ends in that marker form. A full passage from the Supreme Court
source checks this behavior.

Verification: all 34 tests passed. The complete experiment run is saved in
`logs/experiments/reference-20261005T144845.299836Z/`. It reports exact API
matches of 21/25 on the historical mixed corpus, 28/31 on interpretation,
7/12 on README passage extraction, and 26/26 plus 19/19 on real-document
interpretation and extraction. Those small selected fixture scores are
regression measurements, not general accuracy estimates. The preceding run
without the false-positive fix scored 18/19 on real extraction.

Docker image construction could not be verified because Docker is unavailable
in this environment.
