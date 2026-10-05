# Preserve occurrences and recover after unfinished references

Status: resolved

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

## Answer

Added two public API cases for repeated identical citations and recovery after
an unfinished citation followed by two valid ones. Both passed on the first
run, confirming the current pipeline already meets this ticket's behavior.
The analyzer's existing tests also cover repeated spans and its
`unfinished_continuation` diagnostic. No production-code change was needed.

Verification: `/tmp/legal-grammar-venv/bin/python -B -m unittest discover -s
tests -v` passed all 25 tests. The first full-suite attempt used system Python
without project dependencies and failed at import; the successful run used the
project virtualenv. Logs are in
`logs/experiments/issue-02-20261005T140019.622344Z/` (failed invocation) and
`logs/experiments/issue-02-20261005T140043.283893Z/` (passed run).
