# Legal reference service work map

## Notes

The MVP analyzer and `/detect` route are implemented. Full passage corpora now
exist for README examples and a separately sourced official-document batch.
The initial ticket list was proposed in conversation but had not been saved as
local issue files.

## Decisions-so-far

- The MVP ticket preceded issue 02 and is complete; no original issue file was
  present to recover.
- Issue 02 is the next planned slice: repeated final occurrences and recovery
  after unfinished candidates. Resolved after adding end-to-end API coverage;
  all 25 tests passed and no implementation change was required.
- Issue 04 is resolved. Its boundary audit found that an ordinary sentence
  comma could truncate a citation span before the final law token; the parser
  now distinguishes that punctuation from a dangling list connector. All 43
  tests passed; the experiment log is in `logs/experiments/issue-04-20261008T093122Z/`.
- Issue 05 is resolved. The experiment found genuine shared-law alternatives
  and equivalent tree alternatives, and records a bounded rule: one explicit
  law closing a compact coordinated citation scopes all its branches. The
  user confirmed the mixed-depth grouping for issue 06. Its annotated
  experiment is in `logs/experiments/issue-05-20261008T095039Z/`.
- Issue 06 is resolved. The shared semantic analyzer expands coordinated
  branches and common tails, including the confirmed mixed-depth example. The
  LawLink limitation for paths containing both a part and point remains with
  issue 08. Verification is in `logs/experiments/issue-06-20261008T101500Z/`.
- Issue 07 is resolved. Explicit en/em dash ranges with ascending plain
  integer endpoints expand inclusively; ASCII hyphen ambiguities and deferred
  range forms remain unresolved with diagnostics. Verification is in
  `logs/experiments/issue-07-20261008T111053Z/`.
- Issue 08 is resolved. LawLink projects supported fields while retaining
  complete paths internally; ambiguous law aliases project their smallest
  candidate ID with a diagnostic. Verification is in
  `logs/experiments/issue-08-20261008T114056Z/`.
- Issue 09 is resolved. A separate left-to-right resolver carries law and
  article context, uses the latest compatible entity for anaphoric/self
  targets, and retains unresolved values when context is absent. Verification
  is in `logs/experiments/issue-09-20261008T124607Z/`.
- Issue 10 is resolved. The four gold tracks, audited labels, recognition
  probes, 2,000-request local workload, and Docker contract are recorded in
  `docs/quality-evaluation.md` and
  `logs/experiments/issue-10-20261008T131105Z/`. Docker could not run in WSL.
- Issue 11 is resolved. Explicit law-name tails now retain their full spans;
  exact quoted aliases keep their IDs and unlisted titles clear stale law
  context. The five-case passage regression and updated quality metrics are in
  `logs/experiments/issue-11-20261008T133215Z/`.
- Issue 12 is resolved. A comma between a part selector and an article marker
  is represented as a hierarchy gap, so `часть 3, ст. 30.1 КоАП РФ` produces
  one complete provision path. The README extraction track is now 12/12 exact;
  details are in `logs/experiments/issue-12-20261008T134000Z/`.
- Issue 13 is resolved. Short law aliases now retain complete spans through
  `РФ`, trailing prose does not invalidate citations, and `статьей 11 ТК РФ`
  extracts correctly. Both README and published passage suites have perfect
  boundary and link precision/recall; logs are in
  `logs/experiments/issue-13-20261008T135311Z/`.
- Issues 11–13 are focused follow-ups from measured failures: law-name boundary
  and stale-context errors, one part/article citation form, and abbreviated-law
  citation boundaries/recall.

## Fog

- Selector expansion is implemented in issue 03; divergent branch shapes and
  shared tails in issue 06; safe integer ranges and LawLink projection in
  issues 07 and 08.
- `/detect` does not expose source spans. Issue 10 scores boundaries from
  internal semantic references for evaluation; span output is still outside
  the API contract.

- [Issue 02: repeated occurrences and recovery](issues/02-repeated-occurrences-and-recovery.md) is resolved.
- [Issue 03: semantic analyzer and selector lists](issues/03-semantic-analyzer-and-selector-lists.md) owns the shared semantic IR and is resolved.

## Ticket navigation

The original ten-ticket roadmap is reconstructed from the current spec and
conversation, not recovered exactly. Tickets 02 and 03 retain their original
bodies and answers; ticket 01 records the previously completed MVP. Tickets
11–13 were added from measured gaps in issue 10. Dependency numbers refer to
this table.

| Ticket | Status | Blocked by | Purpose |
| --- | --- | --- | --- |
| [01 — MVP service](issues/01-mvp-service.md) | resolved | None | Simple raw-text extraction through the service API |
| [02 — Occurrences and recovery](issues/02-repeated-occurrences-and-recovery.md) | resolved | None | Preserve repeated mentions and recover after unfinished candidates |
| [03 — Semantic analyzer and lists](issues/03-semantic-analyzer-and-selector-lists.md) | resolved | MVP | Shared provision paths and selector-list expansion |
| [04 — Final citation boundaries](issues/04-final-occurrence-boundaries.md) | resolved | 03 | Validate and fix overlapping-candidate selection |
| [05 — Concrete grammar ambiguities](issues/05-concrete-grammar-ambiguities.md) | resolved | 03 | Investigate actual alternatives and settle attachment rules |
| [06 — Coordination and shared tails](issues/06-coordination-and-shared-tails.md) | resolved | 03, 05 | Grammar-supported branches through semantic expansion and API output |
| [07 — Safe range expansion](issues/07-safe-range-expansion.md) | resolved | 03 | Expand agreed integer ranges while preserving uncertain identifiers |
| [08 — LawLink projection policy](issues/08-lawlink-projection-policy.md) | resolved | 03 | Decide outputs for paths the API cannot fully represent |
| [09 — Context resolution](issues/09-contextual-reference-resolution.md) | resolved | 04, 08 | Resolve context-dependent targets under explicitly agreed rules |
| [10 — Quality, runtime, packaging](issues/10-quality-runtime-and-packaging.md) | resolved | 04–09 | Assess real-text quality, workload runtime, and Docker execution |
| [11 — Law-name boundaries and context safety](issues/11-law-name-boundaries-and-context-safety.md) | resolved | 10 | Prevent missed explicit law tails from inheriting stale IDs |
| [12 — Part-before-article citation](issues/12-part-before-article-citations.md) | resolved | 10 | Extract the measured `часть 3, ст. 30.1 КоАП РФ` form |
| [13 — Abbreviated-law citations](issues/13-abbreviated-law-citation-coverage.md) | resolved | 10 | Improve spans and recall for short law abbreviations |

## Frontier

All saved tickets are resolved. Add a new ticket if later evaluation or
annotation identifies another concrete gap.

## Comments

The user authorized saving all tickets for navigation only. No implementation
or new verification run was performed during reconstruction. After discussion,
ticket 04 became an audit of existing behavior, ticket 05 became a concrete
grammar investigation, and ticket 06 explicitly assigns branch structure to
the grammar. All later semantic behavior extends the stage from ticket 03.
Dependency edges were narrowed to genuine prerequisites so that independent
range and projection work can start without waiting for branch coordination.

Ticket 04 was later authorized and completed. Its parser fix and interface
coverage are described in the ticket answer and experiment report.
