# What the grammar experiments check

The experiments ask whether the candidate grammar accepts our annotated
reference structures, whether it admits multiple parse trees, and whether
Lark reproduces the independent analyzer's results. They do not yet check
extraction from Russian prose.

## Inputs

[reference-grammar.bnf](reference-grammar.bnf) contains 79 productions,
37 nonterminals and 22 terminal types. It describes the conventional reverse
hierarchy, with omitted levels, lists, ranges, coordinated branches and optional
law targets.

[grammar-examples.json](grammar-examples.json) contains 35 manually annotated
cases. For example:

```text
Text:   статьи 5 и 6 НК РФ
Tokens: ARTICLE ID:5 AND ID:6 LAW:НК_РФ
Expect: accept
```

The annotations are supplied by us. Neither experiment derives those tokens
from the Russian sentence. Expectations specify acceptance or rejection;
some cases also require at least two derivations. They do not specify a full
expected API response or select the correct interpretation of every ambiguity.

## Experiment 1: independent CFG analysis

`tools/analyze_grammar.py` reads the BNF and computes:

- Nullable symbols: rules that can produce an empty sequence.
- FIRST sets: token types that can begin a rule's derivation.
- FOLLOW sets: token types that can occur immediately after a rule.
- LL(1) conflicts: table cells where one lookahead token leaves multiple
  productions available.
- Reachability and productivity: whether a rule is reachable from the start
  and can produce a finite terminal sequence.

For each fixture, a separate span-based algorithm tries each production and
possible split of the input into child spans. It caches intermediate results,
counts all derivations, and retains up to three example trees. Terminal matching
uses token types; values are retained for displaying trees. A count of zero
means rejection, one means a unique derivation for that input, and more than
one supplies an ambiguity witness. Same-span recursive cycles cause an explicit
error; the current grammar has no such problem on these cases.

Observed result: all 35 fixture expectations passed; four inputs were ambiguous;
35 LL(1) table cells had conflicts; all nonterminals were reachable and productive.

## Experiment 2: Lark cross-check

`tools/analyze_with_lark.py` converts the same BNF into Lark syntax without
introducing priorities or attachment rules. It uses an artificial input alphabet:

```text
ARTICLE ID AND ID LAW
```

Identifier and law values are omitted because this experiment checks structure.
It verifies that the basic lexer returns exactly the supplied token kinds.
Earley runs with `ambiguity="explicit"` and `keep_all_tokens=True`.

The tool counts the returned alternatives by summing children of `_ambig`
nodes and multiplying independent child choices. It compares each count with
the independent span analyzer, then checks acceptance and any minimum-count
expectation.

Observed result: all 35 derivation counts agreed exactly. The ambiguous cases were:

| Case | Derivations | Structural question |
|---|---:|---|
| `shared_article` | 3 | Does the trailing article apply to both branches? |
| `readme_comma_gap` | 3 | Does the comma connect nested levels or separate references? |
| `mixed_branches` | 3 | How do mixed branches attach to the common tail? |
| `shared_law` | 2 | Does the trailing law apply to both article mentions? |

Some trees differ only in grouping lawless references; distinct trees are not
automatically distinct eventual API outputs.

Finally, the tool attempts to construct a LALR parser with `strict=True` and
the same basic lexer. Construction fails with a shift/reduce grammar conflict.
The report retains the actual diagnostic. The first reported conflict may vary
between runs; it is not a complete inventory of LR conflicts.

## What we can conclude

The current grammar has proven ambiguity witnesses. Lark Earley preserves its
alternatives and matches the independent analyzer on the chosen cases. Strict
LALR cannot construct this unchanged grammar. This supports continuing grammar
investigation with Earley; it does not rule out an equivalent deterministic
grammar after interpretation policies are defined.

Finite examples do not establish coverage of all legal references. The experiments
do not check normalization, candidate boundaries, law IDs, contextual inheritance,
range expansion or API serialization. Single parse timings exclude parser
construction and do not establish benchmark performance.

## Execution records

[Experiment logs](../logs/experiments/README.md) stores separate runs and snapshots for
each new run. Earlier reports are preserved there with their logging limitation
stated explicitly. Use `tools/run_grammar_experiments.py` for future recorded runs.
