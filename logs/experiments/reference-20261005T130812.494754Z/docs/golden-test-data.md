# Golden test data

`data/golden_references.jsonl` is the manually annotated fixture corpus. It
contains 25 legal-reference and negative examples drawn from the assignment's
README, plus one clearly marked combination of two supplied examples. Several
citations retain surrounding prose so the corpus also checks extraction from
text. The records cover known, unknown, and unspecified laws; provision levels;
lists; typos; separate mentions; and ordinary prose.

Each JSONL record has an `id`, `status`, `source`, `text`, and ordered
`references`. Every reference records its exact half-open source span, the
surface text at that span, and expected links using the four-field LawLink
schema. Grouped selectors have one expected link per provision, as required by
the README. Law IDs are taken from `law_aliases.json`; `null` means no explicit
law or no matching entry in that supplied dictionary. The ambiguous hierarchy
example is kept separately in `data/review_queue.jsonl` and is not scored until
its intended structure is adjudicated.

The examples are hand-annotated task fixtures, not a statistically
representative sample of legal writing. Their exact-match score is useful as a
stable regression baseline only. Add examples with both source provenance and
reviewed expected outputs; keep disputed interpretations in the review queue
instead of guessing.

To compare the current `/detect` response to every gold example and save each
prediction, run:

```bash
/tmp/legal-grammar-venv/bin/python tools/run_reference_experiment.py
```

Each experiment directory stores the corpus snapshot and a detailed
`golden-evaluation.json` alongside the test logs and environment metadata.
