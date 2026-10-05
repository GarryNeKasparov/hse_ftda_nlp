# Golden label audit

Reviewed all 25 gold records against README.md, law_aliases.json, CONTEXT.md,
and the decisions made in our discussion. No expected LawLink values, input
texts, or spans needed changing. Nine source descriptions were corrected:
five contexts were adapted, one inflected marker was changed, and two examples
were synthetic. The negative sentence's capitalization as a standalone excerpt
was also recorded explicitly.

The audit is a review by the coding agent, not a second human annotation.
The automated portion checks bounds, exact span text, reference order,
nonoverlap, unique sample IDs, field names and selector types, and law identity
evidence. It imports neither the service nor its normalizer. Expected selector
values and list expansion were checked manually in the table below.

## Reviewed targets

Values use `law / article / point or part / subpoint`; `—` means null.

| Sample | Expected target(s) | Basis |
| --- | --- | --- |
| nested-subpoint | 15 / 374 / 1 / 1 | README explicitly explains this hierarchy. |
| article-known-law | 13 / 105 / — / — | Explicit article and УК РФ. Adapted prose does not add selectors. |
| point-without-article | 0 / — / 10 / — | Explicit point and АПК; no article. Zero is a valid ID. |
| part-and-article | 17 / 30.1 / 3 / — | README puts both part and point in point_article; the comma does not sever this supplied citation. |
| article-unspecified-law | — / 6 / — / — | Synthetic isolated mention; no law or antecedent in the input. Agreed policy, not an explicit README expected output. |
| unknown-numbered-law | — / 37 / — / — | №20-456 is absent from the dictionary. |
| unknown-code-name | — / 34 / 2 / 1 | Explicit hierarchy; рандомного кодекса has no dictionary entry. |
| independent-citations | 15 / 5 / — / —; 0 / — / 10 / — | Synthetic two mentions retained in textual order. |
| subpoint-list | 15 / 3 / 2 / {1, 2, 3} | README explicitly requires three links. |
| subpoint-list-under-point | 174 / 14 / 1 / {4, 5, 6, 8} | Same list rule; four links, shared point/article/law. |
| lettered-point | 0 / 20 / а / — | Marker is пункта, so а belongs to point_article. Preserve Cyrillic а. |
| misspelled-point-marker | 362 / 22 / б / 2 | пунта is a point-marker typo; подпункту identifies level 2. Preserve Cyrillic б. |
| civil-code | 5 / 30 / — / — | Inflected name maps to Гражданский кодекс Российской Федерации. |
| family-code | 8 / 90 / — / — | Inflected full code name. |
| labour-code | 10 / 70 / — / — | Inflected full code name. |
| civil-procedure-code | 6 / 213 / 1 / — | Explicit point, article and full code name. |
| consumer-protection-law | 984 / 16 / — / — | Standalone title О защите прав потребителей. Marker adapted from статье to статья. |
| personal-data-law | 330 / 14 / 2 / — | Standalone title О персональных данных. |
| accounting-law-yo-variant | 224 / 19 / — / — | Title matches after ё→е normalization. |
| registration-of-entities-law | 412 / 9 / р / — | Explicit п. р; preserve Cyrillic р, not Latin p. |
| inspection-law | 284 / 16 / 1 / — | Exact standalone title identifies this act. |
| competition-law | 332 / 12 / — / — | Exact standalone title. |
| police-law | 249 / 20 / 3 / — | Explicit point/article and standalone title. |
| law-alias-not-listed | — / 6 / — / — | О банках и банковской деятельности absent from supplied aliases. Unknown identity here does not assert that the law does not exist. |
| ordinary-prose-negative | No links | No hierarchy selector or law mention. |

## Law evidence and limits

All 17 distinct nonnull IDs have a unique matching whole canonical alias in
the supplied dictionary. Quotation and inflection differences were reconciled
manually when choosing canonical evidence. The machine-readable log records
the chosen alias and all matching IDs. For null unknown-law labels, it records
the absence queries over every alias.

A substring search alone is insufficient: the personal-data title also
occurs inside other acts' longer titles. Number-only aliases such as №218-ФЗ,
№79-ФЗ and №3-ФЗ have collisions. These gold inputs give the full titles, which
uniquely support their IDs; this audit does not validate number-only resolution.

Labels concern extracting the references as written. They do not certify the
truth of the surrounding legal statements or the existence of every mentioned
article, point, or lettered provision. Unknown-law labels are relative to the
supplied dictionary. Context inheritance and unclear coordination require
separate cases; this corpus does not cover those policies comprehensively.

`ambiguous-hierarchy-needs-review` remains outside gold in
`data/review_queue.jsonl`: attachment of `3.345, 23` needs adjudication.

## Reproduce and inspect

```bash
python3 tools/audit_golden_labels.py --output logs/experiments/golden-audit/audit.json
```

The initial [audit log](../logs/experiments/golden-audit-20261005T132231.567329Z/audit.json)
includes input hashes and evidence for every sample. Its directory also stores
the before/after corpus snapshots and the command. The existing 19/25 service
baseline remains a historical evaluation of unchanged inputs and targets;
provenance changes alter the corpus file hash but not its expected outputs.
