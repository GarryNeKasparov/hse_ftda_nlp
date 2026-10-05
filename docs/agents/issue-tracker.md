# Issue tracker: Local Markdown

Issues and specs for this project live as Markdown files under `.scratch/`.
Resolve all paths relative to the homework project directory containing this
configuration, even when the enclosing Git repository has a different root.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`.
- The feature spec is `.scratch/<feature-slug>/spec.md`.
- Implementation tickets are individual files at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`.
- Record workflow state as a `Status:` line near the top. Use the state required by the originating skill; for a spec published through to-spec, use `ready-for-agent`.
- Append comments and conversation history under a `## Comments` heading.

## Publishing and reading

When a skill says to publish to the issue tracker, create the appropriate
local file. Read a relevant ticket at its referenced path. Preserve existing
issue content and append subsequent discussion rather than overwriting it.

## Wayfinding operations

- Map: `.scratch/<effort>/map.md`, containing Notes, Decisions-so-far, and Fog.
- Child ticket: `.scratch/<effort>/issues/NN-<slug>.md`, with the question in its body and a `Type:` line of `research`, `prototype`, `grilling`, or `task`.
- Blocking: a `Blocked by: NN, NN` line identifies dependencies. A ticket is unblocked when all listed tickets are resolved.
- Frontier: choose the first numbered open ticket that is unblocked and unclaimed.
- Claim: save `Status: claimed` before beginning work.
- Resolve: append an `## Answer`, save `Status: resolved`, and add a brief answer and ticket link to the map's Decisions-so-far.
