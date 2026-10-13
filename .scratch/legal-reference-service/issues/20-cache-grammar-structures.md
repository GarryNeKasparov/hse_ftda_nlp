# 20 — Cache repeated legal-reference grammar structures

**What to build:** Repeated legal-reference shapes are parsed once and reused so the analyzer handles long texts faster while returning the same candidate spans and interpretations.

**Blocked by:** None — can start immediately.

Status: resolved

- [x] Cache parse structures by token-kind sequence, including sequences that do not parse, and bind each occurrence to its own source values, law metadata, and offsets.
- [x] Bound the cache and preserve every syntax alternative currently returned by the parser.
- [x] Differentially compare complete analyses and `/detect` outputs before and after caching on the README example, all four gold tracks, and dirty-text regressions.
- [x] Measure warm and cold per-text time and parser cache hit rate on repeated and varied inputs.

## Answer

`ReferenceAnalyzer` now keeps a 4,096-entry LRU cache of parse-tree shapes keyed
by token-kind sequence. Successful entries retain every Earley alternative;
failed sequences are cached too. Each cache hit builds fresh terminals from
the current path, preserving source spelling, offsets, and law metadata.

Complete analyses matched the uncached parser on the exact 4,092-character
README example, all 88 gold samples across the four tracks, and nine dirty-text
regressions covering whitespace, line breaks, backslashes, malformed
separators, and inserted IDs. `/detect` JSON matched for the README, all gold
samples, and all nine dirty-text regressions (98 inputs total).
The analyzer tests, API tests, and full 139-test suite passed; `compileall`
also passed.

On this run, four README analyses averaged 1.28 s with caching and 2.67 s
without; the varied 88-sample pass took 3.01 s with caching and 6.04 s without.
The first cold README analysis took 1.71 s, followed by a 0.98 s mean across
five warm analyses. The varied pass recorded 566 cache hits, 63 misses, and 19
cached failures.
These local timings are directional and do not predict the full 2,000-request
benchmark, which remains ticket 22.
