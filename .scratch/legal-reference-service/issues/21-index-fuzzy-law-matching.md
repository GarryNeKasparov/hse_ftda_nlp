# 21 — Index fuzzy law-alias matching

**What to build:** Fuzzy law names are matched against the supplied aliases without rescanning the full alias collection for each possible source span, while retaining the current two-edit matching behavior and law identities.

**Blocked by:** None — can start immediately.

Status: resolved

- [x] Retrieve candidate aliases through indexed token-form lookups, then apply the current length, morphology, and cumulative edit-distance rules to confirm matches.
- [x] Keep all aliases and law IDs that satisfy current matching rules; do not cap candidate matches or silently discard ambiguous identities.
- [x] Differentially compare recognized law spans, IDs, complete analyses, and `/detect` outputs against the current matcher on all four gold tracks and fuzzy-match boundary cases.
- [x] Measure cold and warm matching time, including alias-index construction and lookup-cache behavior.

## Answer

Full law aliases are indexed by token count and token position in BK-trees over
their morphological forms. Source token forms query those trees within the
existing two-edit ceiling; the original length and cumulative distance checks
then confirm each candidate. A bounded 32,768-entry lookup cache reuses these
candidate sets, while the confirmation step retains every matching alias and
law ID.

The indexed matcher and a full-scan baseline produced identical recognized
LAW source spans and IDs across all 88 gold samples and four fuzzy boundary
inputs. Complete analyses and `/detect` outputs also matched for the README
example, all 88 gold samples, and those four boundaries (93 inputs total).
Tests cover the two-edit cumulative boundary, rejection at three edits, repeated typo
forms, and ambiguous IDs. All 141 tests passed and `compileall` succeeded.

Index construction took 6.04 s, compared with 4.81 s without the BK-tree
build. Warm recognition took 0.42 s versus 2.80 s for the README, and 0.75 s
versus 6.93 s across the varied 88-sample set. The gold pass recorded 65,003
lookup-cache hits and 6,259 misses. A repeated custom fuzzy citation recorded
25 hits, 11 misses, and four alias confirmations. The added index build time is
startup cost; these local measurements do not predict the full benchmark.
