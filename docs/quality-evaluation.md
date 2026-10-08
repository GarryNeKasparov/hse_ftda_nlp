# Quality and runtime evaluation

This is a local measurement of the current milestone, not an estimate of
hidden-benchmark accuracy. The four evaluation tracks stay separate: isolated
citation interpretation and full-passage extraction, each for README examples
and published judicial text. The published texts are provenance-backed and
their labels were audited against source snapshots and the alias database.

## Results

| Track | Samples | Gold links | Exact samples | Link precision | Link recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| README citation interpretation | 31 | 36 | 28/31 | 0.943 | 0.917 |
| README full-passage extraction | 12 | 32 | 8/12 | 0.903 | 0.875 |
| Published citation interpretation | 26 | 27 | 26/26 | 1.000 | 1.000 |
| Published full-passage extraction | 19 | 27 | 18/19 | 1.000 | 0.963 |

For passage extraction, exact link scores do not require the correct source
span. Boundary-only precision/recall was 0.786/0.759 on README passages and
0.960/0.923 on published passages. Requiring both the exact span and its
provision links gives 0.806/0.781 and 0.962/0.926, respectively. The service
response itself has no span field; boundary scores use the analyzer's
source-positioned semantic references.

Errors in the README passage set include an omitted first citation in
`readme-passage-12`, incorrect or absent matches for long and unknown law
names in passages 05, 06, and 08, and citation boundaries that end before `РФ`
or before an unlisted law title in passages 01 and 02. The published passage
set misses `статьей 11 ТК РФ` in `web-vsrf-12452-paragraph-037`. Detailed
expected and predicted spans and links are in the experiment report.

Five separate recognition probes passed: a one-edit marker typo and a one-edit
long law-name typo were accepted; a distant marker typo was rejected; a
distant code-name typo and a short misspelled abbreviation retained no law ID.
These curated probes are useful boundary checks, not a representative corpus.
The README data also shows a stale-context failure when an explicit law tail
is not recognized: a previous law can be inherited for a later reference.

All four label audits pass after extending the audit evidence for the newer
README corpora. The initial audit-tool failures and their output are retained
in the experiment directory. They were missing audit mappings for the known
unlisted-law labels, not corrections to those labels.

## Runtime

The measured proxy cycles each gold track to 500 inputs, for 2,000 `/detect`
requests in total. It reuses the existing labeled texts and therefore has a
narrow, repeated distribution.

- Analyzer, semantic analyzer, and resolver construction: **3.65 s**.
- FastAPI lifespan startup: **4.10 s**.
- Direct analyzer pipeline for 2,000 texts: **141.44 s**.
- HTTP `/detect` for 2,000 texts: **156.05 s** (about **78 ms** per request on
  average; estimated HTTP/request overhead **14.61 s** across the run).
- The local 2,000-request proxy is below the assignment's 300-second limit.

This does not establish hidden-benchmark success. Repeated samples, warm
normalization caches, the local TestClient transport, and the small three-source
published corpus may differ from the grader's workload and environment.

## Docker

The Dockerfile now copies `contextual_resolver.py`; a static contract check
confirms all eight copied inputs exist, the image exposes port 8978, and the
command starts the service on that port. Docker Desktop's CLI is present on the
Windows side but its WSL command reports that Docker is unavailable in this
distro. The image could not be built or exercised here and remains an open
environment limitation.

## Reproduction

The complete snapshots, hashes, versions, commands, test output, label audits,
evaluation JSON, runtime report, and Docker checks are in
[`issue-10-20261008T131105Z`](../logs/experiments/issue-10-20261008T131105Z/).
The core commands are:

```bash
.venv/bin/python -m pytest -p no:cacheprovider tests
.venv/bin/python -B tools/evaluate_golden_quality.py --output /tmp/quality.json
.venv/bin/python -B tools/benchmark_golden_workload.py --repetitions 500 --output /tmp/runtime.json
.venv/bin/python -B tools/check_docker_contract.py
```

## Follow-up tickets

- [Issue 11: law-name tails and stale contextual IDs](../.scratch/legal-reference-service/issues/11-law-name-boundaries-and-context-safety.md)
- [Issue 12: part-to-article citation form](../.scratch/legal-reference-service/issues/12-part-before-article-citations.md)
- [Issue 13: abbreviated-law citation coverage](../.scratch/legal-reference-service/issues/13-abbreviated-law-citation-coverage.md)
