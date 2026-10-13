# 22 — Meet the length-matched instructor benchmark runtime

**What to build:** The complete service processes a deterministic 2,000-request workload within the instructor's five-minute execution limit while preserving current extraction behavior.

**Blocked by:** 20 — Cache repeated legal-reference grammar structures; 21 — Index fuzzy law-alias matching.

Status: resolved

- [x] Build four deterministic batches of 500 texts each, with every text exactly 4,092 characters, the README example's length. Cycle through complete samples in each gold track so every sample appears; separate each sample from neutral prose with a blank line and do not cut citations.
- [x] Run the workload through `/detect`, include service startup in the total, and finish within 240 seconds to preserve a one-minute margin against the 300-second limit.
- [x] Report total and per-request median, p95, maximum, startup time, cache hit rates, and the workload-generation seed and command.
- [x] Confirm the full test suite, current README and golden evaluations, and output differential checks pass. Do not claim hidden-benchmark accuracy from this local timing result.
- [x] Profile and tune the initial workload when it exceeded 240 seconds; verify the tuned workload meets the runtime criterion.

## Answer

Added `tools/benchmark_length_matched.py` to generate deterministic, unique
4,092-character inputs and measure real `/detect` requests including service
startup. Each request contains one whole gold sample, cycled so all samples in
each of the four tracks are exercised, followed by neutral prose. Joining many
different gold samples into every request created synthetic cross-citation
paths and took 271.1 seconds for 2,000 requests. Profiling identified repeated
dirty-alias fragment scans in `_recognize_edges`; precomputing joined forms
once per source position brought the final run to 229.5 seconds.

The final workload used seed `20261013`, 500 requests per track, and SHA-256
`186508b39008d518c34c6c553ffa9a02e1cb4fead0a6d4efb0df061d143a9aed`.
Command:

```text
.venv/bin/python tools/benchmark_length_matched.py --seed 20261013 --requests-per-track 500 --target-chars 4092 --output logs/experiments/issue-22-length-matched-20261013/report.json
```

All 2,000 requests completed in **229.53 s including 7.68 s startup**. Per
request aggregate median/p95/maximum was **105.8/158.5/723.2 ms**. By track,
median/p95/maximum was 126.6/175.8/723.2 ms (README interpretation),
112.3/177.4/321.3 ms (README extraction), 86.6/113.9/467.4 ms (real
interpretation), and 94.9/140.5/483.0 ms (real extraction). Parse-shape cache
hit rate was **99.61%** and fuzzy-lookup cache hit rate was **98.35%**.

The full suite passed (142 tests) and `compileall` succeeded. Golden quality
evaluation matched README interpretation 31/31 and extraction 12/12, real
interpretation 26/26 and extraction 19/19, plus all five recognition probes;
link and span precision/recall were 1.0. The optimized alias scan produced
identical complete analyses and mapped links to its pre-optimization version
for all 88 gold samples and seven dirty-separator cases. The quality report is
in `logs/experiments/issue-22-length-matched-20261013/golden-quality-report.json`.

This local proxy meets the 240-second target. It is not a claim about hidden
benchmark accuracy or runtime under a different environment.
