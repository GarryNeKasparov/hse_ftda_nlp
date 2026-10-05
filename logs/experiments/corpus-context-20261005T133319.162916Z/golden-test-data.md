# Golden test data

## Separate evaluation tasks

| Suite | Input | Expected result | Current size |
| --- | --- | --- | --- |
| `data/golden_interpretation.jsonl` | A supplied citation, isolated from its passage | Correct law identity, hierarchy and list expansion | 31 citations, 36 links |
| `data/golden_extraction.jsonl` | Complete passages with surrounding prose | Every reference extracted in textual order, with no extra links | 12 passages, 29 reference spans, 32 links |

The extraction suite includes 11 verbatim complete passages from README's
`test_text`, including its multiline first paragraph, plus one negative sentence
excerpt. Every passage is exhaustively annotated; passages with several
citations retain all of them. Source offsets and the README hash record the
original passage. The ambiguous passage is excluded as a whole and remains in
the review queue. Interpretation examples are isolated from the annotated
passages, plus the explicit README list example and our unspecified-law case.
`parent_id` connects paired examples so failures can be compared in and out of
context. These paired examples must stay together if later splitting data.

This separates interpretation given a citation from extraction in context.
Interpretation exact match also checks selectors and expansion, so it is not
a pure law-ID metric. Extraction exact match checks the entire ordered API
response. The annotated spans support future boundary evaluation, but `/detect`
does not return spans, so the evaluator explicitly marks boundary scoring as
unavailable. Raw analyzer candidates are not final extracted references.

These passages are original assignment examples, not independently collected
legal documents. A representative extraction corpus still needs sourced real
documents, longer contexts, repeated mentions, distracting numbers, and
negative passages. The legal assertions in README prose are not certified.
For example, the Constitution mention has a null ID because its standalone
name is absent from this supplied dictionary; titles of other acts containing
the word Constitution do not establish that identity.

The experiment runner saves separate `golden-interpretation-evaluation.json`
and `golden-extraction-evaluation.json` reports. Do not combine their scores
into one measure of extraction performance.

## Historical mixed corpus

`data/golden_references.jsonl` is the manually annotated fixture corpus. It
contains 25 examples in total: 23 derived from the assignment's README and two
synthetic examples from our discussion (an unspecified law and independent
citations). Several contexts were adapted rather than copied verbatim; each
record's `source` identifies those changes. The records cover known, unknown,
and unspecified laws; provision levels;
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

The first recorded comparison matched 19 of 25 examples exactly. The six
mismatches expose concrete gaps: mapping a part with an article, expanding two
subpoint lists, resolving АПК when surrounded by prose, and matching two
shortened law names. See the full
[baseline report](../logs/experiments/reference-20261005T130812.494754Z/golden-evaluation.json).
This score is a baseline on these hand-selected examples, not a general
accuracy estimate.

The [label audit](golden-label-audit.md) confirmed the existing expected links
and corrected nine provenance descriptions. It checked 25 spans and 30 links
without using parser predictions. The baseline above used the same input text
and expected links; only source metadata changed during the audit.

To compare the current `/detect` response to every gold example and save each
prediction, run:

```bash
/tmp/legal-grammar-venv/bin/python tools/run_reference_experiment.py
```

Each experiment directory stores the corpus snapshot and a detailed
`golden-evaluation.json` alongside the test logs and environment metadata.
