# Lark grammar experiment

Environment: Lark 1.3.1, interegular 0.3.3.

## Method

The tool translates [reference-grammar.bnf](reference-grammar.bnf) directly to Lark syntax. It introduces no rule priorities or attachment preferences. Earley uses `lexer="basic"`, `ambiguity="explicit"` and retained terminals. Inputs are the manually annotated token kinds from [grammar-examples.json](grammar-examples.json); identifier and law values are intentionally outside this structural experiment. The artificial lexer is checked against every input token sequence.

Derivation counts sum `_ambig` alternatives and multiply independent child counts. They are compared with the separate span-based CFG analyzer. Acceptance and any minimum-count fixture expectations are also checked.

## Results

- 35/35 examples agree with both the CFG analyzer and fixture expectations.
- 4 examples have multiple derivations.
- Strict LALR construction fails with a grammar conflict.

| Case | CFG derivations | Earley derivations | Parse time (ms) | Result |
|---|---:|---:|---:|---|
| article_list | 1 | 1 | 6.445 | pass |
| two_explicit_laws | 1 | 1 | 6.493 | pass |
| point_list_under_part | 1 | 1 | 8.100 | pass |
| shared_article | 3 | 3 | 9.128 | pass |
| paragraph_ordinals | 1 | 1 | 8.507 | pass |
| readme_nested | 1 | 1 | 4.125 | pass |
| readme_subpoint_list | 1 | 1 | 9.116 | pass |
| readme_missing_article | 1 | 1 | 2.261 | pass |
| readme_lettered_point | 1 | 1 | 3.148 | pass |
| readme_typo_annotation | 1 | 1 | 5.599 | pass |
| readme_multi_level_lists | 1 | 1 | 12.411 | pass |
| readme_comma_gap | 3 | 3 | 5.122 | pass |
| unknown_act | 1 | 1 | 2.488 | pass |
| no_act | 1 | 1 | 2.933 | pass |
| dotted_letter | 1 | 1 | 3.986 | pass |
| atomic_hyphen | 1 | 1 | 3.930 | pass |
| atomic_integer_hyphen | 1 | 1 | 1.907 | pass |
| superscript_id | 1 | 1 | 1.777 | pass |
| integer_range | 1 | 1 | 4.078 | pass |
| ordinal_range_list | 1 | 1 | 6.085 | pass |
| mixed_branches | 3 | 3 | 22.980 | pass |
| shared_law | 2 | 2 | 4.524 | pass |
| pp_means_subpoint | 1 | 1 | 7.299 | pass |
| self_target | 1 | 1 | 4.958 | pass |
| anaphoric_act | 1 | 1 | 2.572 | pass |
| repeated_occurrences | 1 | 1 | 6.343 | pass |
| bare_act | 0 | 0 | 1.150 | pass |
| bare_identifier | 0 | 0 | 1.206 | pass |
| marker_without_value | 0 | 0 | 1.355 | pass |
| unfinished_range | 0 | 0 | 1.478 | pass |
| unfinished_list | 0 | 0 | 2.392 | pass |
| reversed_order_outside_v1 | 0 | 0 | 1.830 | pass |
| repeated_level_without_join | 0 | 0 | 2.015 | pass |
| two_acts_without_join | 0 | 0 | 2.357 | pass |
| empty_candidate | 0 | 0 | 3.273 | pass |

## Strict LALR diagnostic

```text
Shift/Reduce conflict for terminal COMMA. [strict-mode]
 * <article_children_tail : >

```

This is the conflict reported during construction, not an exhaustive inventory of LR conflicts. Diagnostic order may vary between runs.

## Interpretation and limits

Earley reproduces the candidate grammar without silently selecting one interpretation. It is suitable for the next grammar experiment. These findings do not select the production parser or prove that the intended language has no deterministic grammar.

The existing ambiguity witnesses remain in [grammar-analysis.md](grammar-analysis.md). Shared article/law scope and comma attachment still require explicit interpretation policies. Reorganizing lawless references can also produce distinct trees with the same eventual provision output.

Parse times are single observations on short annotated candidates, excluding parser construction. They are not a benchmark for full Russian texts, memory use or the instructor’s five-minute limit. No Russian lexer, normalizer, law resolver, range expander or API projection is checked.

## Reproduce

```bash
python3 -m venv /tmp/legal-grammar-venv
/tmp/legal-grammar-venv/bin/python -m pip install -r requirements-grammar.txt
/tmp/legal-grammar-venv/bin/python tools/analyze_with_lark.py
```

Official documentation: [Earley and LALR](https://lark-parser.readthedocs.io/en/latest/parsers.html), [strict mode](https://lark-parser.readthedocs.io/en/latest/how_to_use.html#strict-mode).
