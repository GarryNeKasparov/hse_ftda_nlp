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
  after unfinished candidates. The analyzer already has direct coverage; this
  ticket adds missing end-to-end API coverage and fixes only observed failures.

## Fog

- Grouped selectors, branch coordination, ranges, and API projection when
  point and part coexist remain separate tickets and follow-up decisions.
- The current service API does not expose source spans; boundary scoring stays
  out of this issue.
