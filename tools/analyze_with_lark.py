"""Cross-check the candidate BNF with Lark using annotated token kinds.

This experiment does not recognize Russian text or choose an interpretation.
The BNF remains the sole grammar specification; Lark syntax is generated.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from functools import cache
from importlib.metadata import version
import json
from math import prod
from pathlib import Path
from time import perf_counter

from lark import Lark, Token, Tree
from lark.exceptions import GrammarError, UnexpectedInput

from analyze_grammar import count_derivations, grammar_properties, read_grammar


def lark_grammar(productions, terminals: set[str]) -> str:
    """Translate productions without adding priorities or removing alternatives."""
    rules = defaultdict(list)
    for production in productions:
        rules[production.lhs].append(' '.join(production.rhs))
    lines = [f"{lhs}: " + '\n    | '.join(alternatives)
             for lhs, alternatives in rules.items()]
    # Token kinds, not raw labels, are the artificial input alphabet. The
    # boundary prevents AND from matching the beginning of AND_OR.
    lines.extend(f'{terminal}: /{terminal}(?![A-Z_])/'
                 for terminal in sorted(terminals))
    lines.extend(['%import common.WS', '%ignore WS'])
    return '\n'.join(lines) + '\n'


def derivation_count(tree: Tree | Token) -> int:
    """Sum alternatives and multiply independent child ambiguities."""
    @cache
    def count(node):
        if isinstance(node, Token):
            return 1
        counts = [count(child) for child in node.children]
        return sum(counts) if node.data == '_ambig' else prod(counts)

    return count(tree)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--grammar', type=Path, default=root / 'docs/reference-grammar.bnf')
    cli.add_argument('--examples', type=Path, default=root / 'docs/grammar-examples.json')
    cli.add_argument('--output', type=Path, default=root / 'docs/lark-grammar-analysis.md')
    args = cli.parse_args()
    productions = read_grammar(args.grammar)
    properties = grammar_properties(productions)
    grammar = lark_grammar(productions, properties['terminals'])
    earley = Lark(grammar, parser='earley', lexer='basic', ambiguity='explicit',
                  keep_all_tokens=True)
    results = []
    for example in json.loads(args.examples.read_text()):
        tokens = tuple((token.split(':', 1)[0], token.split(':', 1)[-1])
                       for token in example['tokens'].split())
        unknown = {kind for kind, _ in tokens} - properties['terminals']
        if unknown:
            raise ValueError(f"Unknown tokens in {example['name']}: {sorted(unknown)}")
        text = ' '.join(kind for kind, _ in tokens)
        if [token.type for token in earley.lex(text)] != [kind for kind, _ in tokens]:
            raise ValueError(f"Surrogate lexer changed tokens in {example['name']}")
        expected_count, _ = count_derivations(productions, properties['minimum'], tokens)
        started = perf_counter()
        try:
            tree = earley.parse(text)
        except UnexpectedInput:
            tree = None
        elapsed_ms = (perf_counter() - started) * 1000
        actual_count = derivation_count(tree) if tree is not None else 0
        matches = (actual_count == expected_count
                   and bool(actual_count) == (example['expect'] == 'accept')
                   and actual_count >= example.get('minimum_derivations', 0))
        results.append((example, expected_count, actual_count, elapsed_ms, matches))

    try:
        Lark(grammar, parser='lalr', lexer='basic', strict=True)
    except GrammarError as error:
        lalr_error = str(error)
    else:
        lalr_error = None

    passed = sum(row[-1] for row in results)
    ambiguous = sum(row[2] > 1 for row in results)
    lines = ['# Lark grammar experiment', '',
             f"Environment: Lark {version('lark')}, interegular {version('interegular')}.", '',
             '## Method', '',
             'The tool translates [reference-grammar.bnf](reference-grammar.bnf) directly '
             'to Lark syntax. It introduces no rule priorities or attachment preferences. '
             'Earley uses `lexer="basic"`, `ambiguity="explicit"` and retained terminals. '
             'Inputs are the manually annotated token kinds from '
             '[grammar-examples.json](grammar-examples.json); identifier and law values '
             'are intentionally outside this structural experiment. The artificial lexer '
             'is checked against every input token sequence.', '',
             'Derivation counts sum `_ambig` alternatives and multiply independent '
             'child counts. They are compared with the separate span-based CFG analyzer. '
             'Acceptance and any minimum-count fixture expectations are also checked.', '',
             '## Results', '',
             f'- {passed}/{len(results)} examples agree with both the CFG analyzer and fixture expectations.',
             f'- {ambiguous} examples have multiple derivations.',
             f"- Strict LALR construction {'fails with a grammar conflict' if lalr_error else 'succeeds'}.", '',
             '| Case | CFG derivations | Earley derivations | Parse time (ms) | Result |',
             '|---|---:|---:|---:|---|']
    for example, expected_count, actual_count, elapsed_ms, matches in results:
        lines.append(f"| {example['name']} | {expected_count} | {actual_count} | "
                     f"{elapsed_ms:.3f} | {'pass' if matches else 'FAIL'} |")
    lines.extend(['', '## Strict LALR diagnostic', ''])
    if lalr_error:
        lines.extend(['```text', lalr_error, '```', '',
                      'This is the conflict reported during construction, not an exhaustive '
                      'inventory of LR conflicts. Diagnostic order may vary between runs.', ''])
    else:
        lines.extend(['No construction conflict was reported.', ''])
    lines.extend(['## Interpretation and limits', '',
                  'Earley reproduces the candidate grammar without silently selecting '
                  'one interpretation. It is suitable for the next grammar experiment. '
                  'These findings do not select the production parser or prove that '
                  'the intended language has no deterministic grammar.', '',
                  'The existing ambiguity witnesses remain in [grammar-analysis.md](grammar-analysis.md). '
                  'Shared article/law scope and comma attachment still '
                  'require explicit interpretation policies. Reorganizing lawless references '
                  'can also produce distinct trees with the same eventual provision output.', '',
                  'Parse times are single observations on short annotated candidates, '
                  'excluding parser construction. They are not a benchmark for full Russian '
                  'texts, memory use or the instructor’s five-minute limit. No Russian lexer, '
                  'normalizer, law resolver, range expander or API projection is checked.', '',
                  '## Reproduce', '', '```bash',
                  'python3 -m venv /tmp/legal-grammar-venv',
                  '/tmp/legal-grammar-venv/bin/python -m pip install -r requirements-grammar.txt',
                  '/tmp/legal-grammar-venv/bin/python tools/analyze_with_lark.py', '```', '',
                  'Official documentation: [Earley and LALR](https://lark-parser.readthedocs.io/en/latest/parsers.html), '
                  '[strict mode](https://lark-parser.readthedocs.io/en/latest/how_to_use.html#strict-mode).', ''])
    args.output.write_text('\n'.join(lines))
    print(f'{passed}/{len(results)} examples agree; {ambiguous} ambiguous cases; '
          f"strict LALR {'rejected' if lalr_error else 'accepted'} the grammar.")
    print(f'Report: {args.output}')
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
