# Lark grammar experiment

Environment: Lark 1.3.1, interegular 0.3.3.

## Method

The tool translates [reference-grammar.bnf](reference-grammar.bnf) directly to Lark syntax. It introduces no rule priorities or attachment preferences. Earley uses `lexer="basic"`, `ambiguity="explicit"` and retained terminals. Inputs are the manually annotated token kinds from [grammar-examples.json](grammar-examples.json); identifier and law values are intentionally outside this structural experiment. The artificial lexer is checked against every input token sequence.

Derivation counts sum `_ambig` alternatives and multiply independent child counts. They are compared with the separate span-based CFG analyzer. Acceptance and any minimum-count fixture expectations are also checked.

## Results

- 35/35 examples agree with both the CFG analyzer and fixture expectations.
- 5 examples have multiple derivations.
- Strict LALR construction fails with a grammar conflict.

| Case | CFG derivations | Earley derivations | Parse time (ms) | Result |
|---|---:|---:|---:|---|
| article_list | 1 | 1 | 10.536 | pass |
| two_explicit_laws | 1 | 1 | 8.644 | pass |
| point_list_under_part | 1 | 1 | 10.739 | pass |
| shared_article | 3 | 3 | 20.812 | pass |
| paragraph_ordinals | 1 | 1 | 10.416 | pass |
| readme_nested | 1 | 1 | 8.796 | pass |
| readme_subpoint_list | 1 | 1 | 18.636 | pass |
| readme_missing_article | 1 | 1 | 4.940 | pass |
| readme_lettered_point | 1 | 1 | 4.806 | pass |
| readme_typo_annotation | 1 | 1 | 6.103 | pass |
| readme_multi_level_lists | 1 | 1 | 20.831 | pass |
| readme_comma_gap | 3 | 3 | 9.406 | pass |
| unknown_act | 1 | 1 | 4.277 | pass |
| no_act | 1 | 1 | 2.853 | pass |
| dotted_letter | 1 | 1 | 6.428 | pass |
| atomic_hyphen | 1 | 1 | 7.746 | pass |
| atomic_integer_hyphen | 1 | 1 | 4.664 | pass |
| superscript_id | 1 | 1 | 4.605 | pass |
| integer_range | 1 | 1 | 4.526 | pass |
| ordinal_range_list | 1 | 1 | 7.438 | pass |
| mixed_branches | 3 | 3 | 26.421 | pass |
| shared_law | 2 | 2 | 10.088 | pass |
| ambiguous_pp | 2 | 2 | 12.324 | pass |
| self_target | 1 | 1 | 6.116 | pass |
| anaphoric_act | 1 | 1 | 3.925 | pass |
| repeated_occurrences | 1 | 1 | 5.666 | pass |
| bare_act | 0 | 0 | 1.865 | pass |
| bare_identifier | 0 | 0 | 1.653 | pass |
| marker_without_value | 0 | 0 | 1.387 | pass |
| unfinished_range | 0 | 0 | 3.209 | pass |
| unfinished_list | 0 | 0 | 2.803 | pass |
| reversed_order_outside_v1 | 0 | 0 | 3.049 | pass |
| repeated_level_without_join | 0 | 0 | 1.647 | pass |
| two_acts_without_join | 0 | 0 | 7.353 | pass |
| empty_candidate | 0 | 0 | 1.546 | pass |

## Strict LALR diagnostic

```text
Shift/Reduce conflict for terminal COMMA. [strict-mode]
 * <part_children_tail : >

```

This is the conflict reported during construction, not an exhaustive inventory of LR conflicts. Diagnostic order may vary between runs.

## Interpretation and limits

Earley reproduces the candidate grammar without silently selecting one interpretation. It is suitable for the next grammar experiment. These findings do not select the production parser or prove that the intended language has no deterministic grammar.

The existing ambiguity witnesses remain in [grammar-analysis.md](grammar-analysis.md). Shared article/law scope, comma attachment and the type of `PP` still require explicit interpretation policies. Reorganizing lawless references can also produce distinct trees with the same eventual provision output.

Parse times are single observations on short annotated candidates, excluding parser construction. They are not a benchmark for full Russian texts, memory use or the instructor’s five-minute limit. No Russian lexer, normalizer, law resolver, range expander or API projection is checked.

## Reproduce

```bash
python3 -m venv /tmp/legal-grammar-venv
/tmp/legal-grammar-venv/bin/python -m pip install -r requirements-grammar.txt
/tmp/legal-grammar-venv/bin/python tools/analyze_with_lark.py
```

Official documentation: [Earley and LALR](https://lark-parser.readthedocs.io/en/latest/parsers.html), [strict mode](https://lark-parser.readthedocs.io/en/latest/how_to_use.html#strict-mode).
