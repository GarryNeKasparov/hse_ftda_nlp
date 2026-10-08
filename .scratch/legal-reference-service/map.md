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

## Fog

- Selector expansion and basic same-shape coordinated branches are implemented
  in issue 03. Divergent branch shapes, ranges, and API projection when point
  and part coexist remain separate tickets and follow-up decisions.
- The current service API does not expose source spans; boundary scoring stays
  out of this issue.

- [Issue 02: repeated occurrences and recovery](issues/02-repeated-occurrences-and-recovery.md) is resolved.
- [Issue 03: semantic analyzer and selector lists](issues/03-semantic-analyzer-and-selector-lists.md) owns the shared semantic IR and is resolved.

## Ticket navigation

The following ten-ticket roadmap is reconstructed from the current spec and
conversation. It is not an exact recovery of the missing historical list.
Tickets 02 and 03 retain their original bodies and answers; ticket 01 records
the previously completed MVP. Dependency numbers refer to this table.

| Ticket | Status | Blocked by | Purpose |
| --- | --- | --- | --- |
| [01 — MVP service](issues/01-mvp-service.md) | resolved | None | Simple raw-text extraction through the service API |
| [02 — Occurrences and recovery](issues/02-repeated-occurrences-and-recovery.md) | resolved | None | Preserve repeated mentions and recover after unfinished candidates |
| [03 — Semantic analyzer and lists](issues/03-semantic-analyzer-and-selector-lists.md) | resolved | MVP | Shared provision paths and selector-list expansion |
| [04 — Final citation boundaries](issues/04-final-occurrence-boundaries.md) | resolved | 03 | Validate and fix overlapping-candidate selection |
| [05 — Concrete grammar ambiguities](issues/05-concrete-grammar-ambiguities.md) | ready-for-agent | 03 | Investigate actual alternatives and settle attachment rules |
| [06 — Coordination and shared tails](issues/06-coordination-and-shared-tails.md) | ready-for-agent | 03, 05 | Grammar-supported branches through semantic expansion and API output |
| [07 — Safe range expansion](issues/07-safe-range-expansion.md) | ready-for-agent | 03 | Expand agreed integer ranges while preserving uncertain identifiers |
| [08 — LawLink projection policy](issues/08-lawlink-projection-policy.md) | ready-for-agent | 03 | Decide outputs for paths the API cannot fully represent |
| [09 — Context resolution](issues/09-contextual-reference-resolution.md) | ready-for-agent | 04, 08 | Resolve context-dependent targets under explicitly agreed rules |
| [10 — Quality, runtime, packaging](issues/10-quality-runtime-and-packaging.md) | ready-for-agent | 04–09 | Assess real-text quality, workload runtime, and Docker execution |

## Frontier

Ticket 05 is the first numbered open, unclaimed ticket. Tickets 07 and 08 are
also unblocked. Their recorded policy questions remain questions until
settled; ready-for-agent allows that work to begin and does not imply that
the answers have already been chosen.

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
