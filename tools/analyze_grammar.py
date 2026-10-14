"""Compute CFG properties and count derivations of annotated examples.

This is a grammar experiment, independent of service parsing and lexing.
Run with Python 3; no additional packages are required.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import cache
from itertools import product
import json
from pathlib import Path

SAMPLE_LIMIT = 3


@dataclass(frozen=True)
class Production:
    lhs: str
    rhs: tuple[str, ...]

    def display(self) -> str:
        return f"{self.lhs} → {' '.join(self.rhs) or 'ε'}"


@dataclass(frozen=True)
class Tree:
    symbol: str
    children: tuple[Tree, ...] = ()
    value: str | None = None


def read_grammar(path: Path) -> tuple[Production, ...]:
    productions = []
    for line in path.read_text().splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        lhs, alternatives = line.split('::=', 1)
        for alternative in alternatives.split('|'):
            rhs = tuple(alternative.split())
            productions.append(Production(lhs.strip(), () if rhs == ('EPS',) else rhs))
    if not productions or len(set(productions)) != len(productions):
        raise ValueError('The grammar must contain distinct productions.')
    defined = {p.lhs for p in productions}
    undefined = {s for p in productions for s in p.rhs if not s.isupper() and s not in defined}
    if undefined:
        raise ValueError(f'Undefined nonterminals: {sorted(undefined)}')
    return tuple(productions)


def grammar_properties(productions: tuple[Production, ...]) -> dict:
    """Find nullable symbols, FIRST/FOLLOW sets and predictive conflicts."""
    nonterminals = {p.lhs for p in productions}
    terminals = {s for p in productions for s in p.rhs} - nonterminals
    nullable: set[str] = set()
    while True:
        updated = nullable | {p.lhs for p in productions if all(s in nullable for s in p.rhs)}
        if updated == nullable:
            break
        nullable = updated

    first = {s: {s} for s in terminals}
    first.update({s: set() for s in nonterminals})

    def first_sequence(symbols: tuple[str, ...]) -> set[str]:
        result = set()
        for symbol in symbols:
            result |= first[symbol]
            if symbol not in nullable:
                break
        return result

    while True:
        changed = False
        for p in productions:
            updated = first[p.lhs] | first_sequence(p.rhs)
            changed |= updated != first[p.lhs]
            first[p.lhs] = updated
        if not changed:
            break

    follow = {s: set() for s in nonterminals}
    follow[productions[0].lhs].add('$')
    while True:
        changed = False
        for p in productions:
            for i, symbol in enumerate(p.rhs):
                if symbol not in nonterminals:
                    continue
                suffix = p.rhs[i + 1:]
                updated = follow[symbol] | first_sequence(suffix)
                if all(s in nullable for s in suffix):
                    updated |= follow[p.lhs]
                changed |= updated != follow[symbol]
                follow[symbol] = updated
        if not changed:
            break

    predictive: dict[tuple[str, str], list[Production]] = {}
    for p in productions:
        lookahead = first_sequence(p.rhs)
        if all(s in nullable for s in p.rhs):
            lookahead |= follow[p.lhs]
        for token in lookahead:
            predictive.setdefault((p.lhs, token), []).append(p)
    conflicts = {key: ps for key, ps in predictive.items() if len(ps) > 1}

    minimum = {s: 1 for s in terminals}
    minimum.update({s: float('inf') for s in nonterminals})
    while True:
        changed = False
        for p in productions:
            width = sum(minimum[s] for s in p.rhs)
            if width < minimum[p.lhs]:
                minimum[p.lhs] = width
                changed = True
        if not changed:
            break

    reachable = {productions[0].lhs}
    while True:
        updated = reachable | {s for p in productions if p.lhs in reachable for s in p.rhs}
        if updated == reachable:
            break
        reachable = updated
    return dict(nonterminals=nonterminals, terminals=terminals, nullable=nullable,
                first=first, follow=follow, conflicts=conflicts, minimum=minimum,
                unreachable=nonterminals - reachable)


def count_derivations(productions: tuple[Production, ...], minimum: dict,
                      tokens: tuple[tuple[str, str], ...]) -> tuple[int, tuple[Tree, ...]]:
    """Count all derivations by spans, retaining a few example trees.

    Recursive calls must reduce the span or follow an acyclic same-span
    dependency. A future grammar containing nullable/unit cycles is
    rejected explicitly rather than producing misleading counts.
    """
    by_lhs: dict[str, list[Production]] = {}
    for p in productions:
        by_lhs.setdefault(p.lhs, []).append(p)
    active = set()

    @cache
    def parse(symbol: str, start: int, end: int) -> tuple[int, tuple[Tree, ...]]:
        if symbol not in by_lhs:
            if end == start + 1 and tokens[start][0] == symbol:
                return 1, (Tree(symbol, value=tokens[start][1]),)
            return 0, ()
        if end - start < minimum[symbol]:
            return 0, ()
        key = (symbol, start, end)
        if key in active:
            raise ValueError(f'Same-span recursive cycle encountered: {key}')
        active.add(key)
        count, trees = 0, []
        for p in by_lhs[symbol]:
            n, children = sequence(p.rhs, start, end)
            count += n
            trees.extend(Tree(symbol, child) for child in children[:SAMPLE_LIMIT - len(trees)])
        active.remove(key)
        return count, tuple(trees)

    @cache
    def sequence(symbols: tuple[str, ...], start: int, end: int):
        if not symbols:
            return (1, ((),)) if start == end else (0, ())
        head, tail = symbols[0], symbols[1:]
        tail_width = sum(minimum[s] for s in tail)
        if minimum[head] == float('inf') or tail_width == float('inf'):
            return 0, ()
        count, samples = 0, []
        for split in range(start + int(minimum[head]), end - int(tail_width) + 1):
            left_count, left_trees = parse(head, start, split)
            if not left_count:
                continue
            right_count, right_trees = sequence(tail, split, end)
            count += left_count * right_count
            for left, right in product(left_trees, right_trees):
                if len(samples) < SAMPLE_LIMIT:
                    samples.append((left,) + right)
        return count, tuple(samples)

    return parse(productions[0].lhs, 0, len(tokens))


def compact_tree(tree: Tree) -> str:
    """Show meaningful group/level boundaries while hiding grammar plumbing."""
    if tree.value is not None:
        return f'{tree.symbol}({tree.value})' if tree.value != tree.symbol else tree.symbol
    children = ' '.join(filter(None, (compact_tree(child) for child in tree.children)))
    meaningful = (tree.symbol == 'reference' or tree.symbol.endswith('_group')
                  or tree.symbol.endswith('_level') or tree.symbol == 'item')
    return f'{tree.symbol}[{children}]' if meaningful else children


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grammar', type=Path,
                        default=root / 'law_links/resources/reference-grammar.bnf')
    parser.add_argument('--examples', type=Path, default=root / 'docs/grammar-examples.json')
    parser.add_argument('--output', type=Path, default=root / 'docs/grammar-analysis.md')
    args = parser.parse_args()
    productions = read_grammar(args.grammar)
    properties = grammar_properties(productions)
    examples = json.loads(args.examples.read_text())
    results = []
    for example in examples:
        tokens = tuple((token.split(':', 1)[0], token.split(':', 1)[-1])
                       for token in example['tokens'].split())
        unknown = {kind for kind, _ in tokens} - properties['terminals']
        if unknown:
            raise ValueError(f"Unknown fixture tokens in {example['name']}: {sorted(unknown)}")
        count, trees = count_derivations(productions, properties['minimum'], tokens)
        matches = bool(count) == (example['expect'] == 'accept')
        if 'minimum_derivations' in example:
            matches &= count >= example['minimum_derivations']
        results.append((example, count, trees, matches))

    lines = ['# Reference grammar analysis', '',
             'Generated by `python3 tools/analyze_grammar.py`.', '',
             '## Scope', '',
             'This checks the CFG in [reference-grammar.bnf](reference-grammar.bnf) '
             'over manually annotated tokens in [grammar-examples.json](grammar-examples.json). '
             'It does not check Russian normalization, text scanning, law-name resolution, '
             'range expansion, API serialization, or benchmark runtime.', '',
             'The grammar describes the conventional reverse hierarchy with omitted levels. '
             'Other surface orders are outside this version; rejecting one is not evidence '
             'that it never occurs in legal text.', '',
             '## Computed properties', '',
             f"- Nonterminals: {len(properties['nonterminals'])}.",
             f"- Terminals: {len(properties['terminals'])}.",
             f'- Productions: {len(productions)}.',
             f"- Nullable nonterminals: {', '.join(sorted(properties['nullable']))}.",
             f"- Unreachable nonterminals: {', '.join(sorted(properties['unreachable'])) or 'none'}.",
             f"- Nonproductive nonterminals: {', '.join(sorted(s for s in properties['nonterminals'] if properties['minimum'][s] == float('inf'))) or 'none'}.",
             f"- LL(1) conflicting table cells: {len(properties['conflicts'])}.", '',
             '## Annotated examples', '',
             '| Case | Source text | Expected | Derivations | Result |',
             '|---|---|---|---:|---|']
    for example, count, _, matches in results:
        lines.append(f"| {example['name']} | {example['text']} | {example['expect']} | {count} | {'pass' if matches else 'FAIL'} |")

    ambiguous = [(e, n, ts) for e, n, ts, _ in results if n > 1]
    lines.extend(['', '## Ambiguity witnesses', ''])
    for example, count, trees in ambiguous:
        lines.extend([f"### {example['name']}", '', example['text'], '',
                      f'{count} derivations; up to {SAMPLE_LIMIT} example trees are shown below.', '', '```text'])
        lines.extend(compact_tree(tree) for tree in trees)
        lines.extend(['```', ''])
    if ambiguous:
        lines.extend(['These multiple parse trees prove that **this grammar is ambiguous**, '
                      'so it is not LL(k) or LR(k) for any finite k. '
                      'That does not prove the intended language lacks an equivalent deterministic grammar. '
                      'Some differences only regroup lawless references; others change the scope '
                      'of a shared article or law.', '',
                      'A generalized parser can preserve the alternatives, but cannot choose their '
                      'intended meaning by itself. Attachment and abbreviation policies remain necessary. '
                      'Earley/GLR behavior and performance have not been evaluated.', ''])
    else:
        lines.extend(['No ambiguous example was found. This is not a proof of unambiguity.', ''])
    lines.extend(['## LL(1) conflict details', '',
                  '| Nonterminal | Lookahead | Competing productions |',
                  '|---|---|---|'])
    for (symbol, token), candidates in sorted(properties['conflicts'].items()):
        lines.append(f"| `{symbol}` | `{token}` | {'; '.join(p.display() for p in candidates)} |")
    lines.extend(['', '## FIRST and FOLLOW', '',
                  '| Nonterminal | FIRST (ε listed separately above) | FOLLOW |',
                  '|---|---|---|'])
    for symbol in sorted(properties['nonterminals']):
        lines.append(f"| `{symbol}` | {', '.join(sorted(properties['first'][symbol]))} | {', '.join(sorted(properties['follow'][symbol]))} |")
    args.output.write_text('\n'.join(lines) + '\n')
    passed = sum(matches for _, _, _, matches in results)
    print(f'{passed}/{len(results)} annotated cases match expectations; '
          f'{len(ambiguous)} cases have multiple derivations; '
          f"{len(properties['conflicts'])} LL(1) conflict cells.")
    print(f'Report: {args.output}')
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
