# Preserve occurrences and recover after unfinished references

Status: claimed

Type: task

## Scope

Ensure the public service retains repeated mentions as separate links in source
order and extracts a later complete citation when an earlier citation is left
unfinished. Exercise the agreed analyzer and `POST /detect` seams. Do not infer
missing selectors or emit a partial target from an unfinished citation.

## Acceptance criteria

- Two identical complete citations in one input produce two identical links in
  occurrence order.
- An unfinished citation followed by a complete citation produces only the
  complete citation's link.
- An unfinished citation followed by two complete citations preserves both
  later links in order.
- Existing incomplete-prefix diagnostics remain available through the analyzer.

## Comments

Created from the previously proposed ticket sequence because the local tracker
contained the feature spec but no issue files. The MVP was implemented before
this ticket; its historical acceptance details are recorded in the feature
spec and API tests.
