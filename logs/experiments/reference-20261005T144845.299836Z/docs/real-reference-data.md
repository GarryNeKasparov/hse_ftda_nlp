# References from published legal documents

Collected on 2026-10-05 from the Supreme Court's official website. This first
batch contains 19 complete paragraphs, including three negative paragraphs,
with 26 reference occurrences and 27 expected LawLink targets. A paired
interpretation suite contains the 26 isolated reference occurrences. Seven
additional complete paragraphs remain unscored pending annotation decisions.

## Sources

| Snapshot ID | Published document | Gold paragraphs | Review paragraphs |
| --- | --- | --- | --- |
| vsrf-14913 | [Plenum resolution №25, 23 June 2015](https://www.vsrf.ru/files/14913/) | 7 | 1 |
| vsrf-13345 | [Joint Plenum resolution №10/22, 29 April 2010](https://www.vsrf.ru/files/13345/) | 8 | 2 |
| vsrf-12452 | [Plenum resolution №63, 28 December 2006](https://www.vsrf.ru/files/12452/) | 4 | 4 |

The third page begins with a meeting report, then publishes resolution №63
and the new text of resolution №2 of 17 March 2004. All selected paragraphs
come from that resolution text, not the introductory meeting report. These
are historical publications; the dataset tests extraction of their wording,
not whether the cited provisions are currently in force.

## Files and provenance

- `data/golden_real_extraction.jsonl`: complete source paragraphs and exhaustive
  reference annotations for the chosen task scope.
- `data/golden_real_interpretation.jsonl`: isolated citations paired through
  `parent_id` and `parent_reference_span`.
- `data/real_review_queue.jsonl`: whole passages requiring policy decisions;
  no invented expected outputs and no partial scoring.
- `data/sources/manifest.json`: URLs, titles, publication dates, retrieval times,
  raw and normalized snapshot paths, hashes, and text conversion rules.
- `data/sources/vsrf-*.txt`: normalized source text. Each extraction record's
  `source_span` points into this snapshot; reference offsets point into the
  record's `text`. All offsets are half-open Python string indices.

Downloaded HTML is retained under
`logs/experiments/real-corpus-20261005T134149.958158Z/`. HTML PRE text is decoded,
entities are resolved, and whitespace is collapsed. Published spelling,
punctuation, word order, and identifiers are preserved. Superscript formatting
is not reconstructed; passages where that affects the identifier are queued
for review. The log also stores the annotation construction script and corpus
snapshots. The source IDs and `document_group` must stay together when splitting
training, development, and evaluation data, including paired citations.

## Annotation rules and review

Annotations were written by reading each full paragraph, independently of the
service's predictions. They are agent-reviewed labels, not independently
adjudicated human gold. References require a provision selector: naming a code
without identifying a provision is not an additional reference. Section
numbers heading the ruling's paragraphs are not references either.

Spans begin at the hierarchy marker and end at the explicit law name, excluding
outer parentheses, trailing punctuation, and parenthetical abbreviation
definitions such as `(далее - ГК РФ)`. Each selected positive paragraph has all
its references annotated, including occurrences linked by `и` or `или`.
Separate occurrences remain in textual order. `пунктами 1, 2 статьи 299 ГК РФ`
is one reference span with two ordered targets; parts map to `point_article`.

The four known identities are uniquely supported by whole aliases in the
supplied dictionary: ГК РФ→5, ГПК РФ→6, АПК РФ→0, ТК РФ→10. Their full code
names support the same IDs. The standalone Constitution name is absent, so
the reference to its article 55 has `law_id=null`, with absence evidence.
Other acts whose titles mention the Constitution are not that act.

The review queue preserves these cases:

| Source paragraph | Unresolved decision |
| --- | --- |
| 14913 / 10 | Printed article `8-1`: preserve typography or normalize it; do not silently treat it as a range. |
| 13345 / 10 | Point 3 and part 4 both occur within article 170; the API has one field for these two levels. |
| 13345 / 13 | Paragraph fifth is a level absent from LawLink. |
| 12452 / 18 | Point 1 and part 1 both occur within article 22. |
| 12452 / 22 | Decide serialization of `часть первая`. |
| 12452 / 28 | Superscript article typography and `части второй` referring to the code volume. |
| 12452 / 40 | Shared law tail across article 15 with listed parts and article 120. |

This is a small, deliberately selected development corpus from one publisher,
covering civil law, civil procedure, arbitration procedure, and labour law.
It adds published prose, multi-reference paragraphs, list expansion, valid
zero IDs, an unknown identity, and genuine negative paragraphs. It is not a
random sample or a comprehensive benchmark. Difficult queued cases are
reported separately; their exclusion makes the gold subset easier.

## Validation and evaluation

`tools/audit_golden_labels.py --dataset <path> --output <path>` checks annotation
structure, exact spans, source snapshot hashes, source excerpts, and canonical
alias uniqueness without importing the service. Hierarchy values and paragraph
completeness are a manual annotation responsibility, not something these
mechanical checks prove.

The recorded audits passed with zero errors: [extraction labels](../logs/experiments/real-corpus-20261005T134149.958158Z/extraction-label-audit.json)
and [interpretation labels](../logs/experiments/real-corpus-20261005T134149.958158Z/interpretation-label-audit.json).
Raw snapshot hashes, all seven review excerpts, and consistency of paired
labels were also checked. The collection log records these checks separately
from service evaluations.

`tools/run_reference_experiment.py` now snapshots these files and produces
separate `golden-real_extraction-evaluation.json` and
`golden-real_interpretation-evaluation.json` reports alongside the assignment
corpora. No new service performance claim is made by collecting this batch.
The API response comparison does not measure boundaries because `/detect`
does not expose reference spans.
