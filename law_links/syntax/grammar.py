"""Load the shared BNF grammar and adapt Lark trees to syntax models."""

from __future__ import annotations

from collections import defaultdict
from itertools import product
from pathlib import Path
from typing import Mapping, Sequence

from lark import Lark, Token, Tree
from lark.lexer import Lexer

from law_links.syntax.models import AstLeaf, AstNode, LexicalCandidate


GRAMMAR_PATH = Path(__file__).resolve().parents[1] / "resources" / "reference-grammar.bnf"


class CandidateLexer(Lexer):
    """Feed provenance-bearing candidate tokens into Lark's Earley parser."""

    def __init__(self, lexer_conf):
        self.lexer_conf = lexer_conf

    def lex(self, data):
        for item in data:
            yield Token(item.kind, item.value, start_pos=item.start, end_pos=item.end)


def read_grammar(path: Path = GRAMMAR_PATH) -> tuple[dict[str, list[tuple[str, ...]]], set[str]]:
    """Read the shared BNF and collect its productions and terminal names."""
    rules: dict[str, list[tuple[str, ...]]] = defaultdict(list)
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        lhs, alternatives = line.split("::=", 1)
        for alternative in alternatives.split("|"):
            rhs = tuple(alternative.split())
            rules[lhs.strip()].append(() if rhs == ("EPS",) else rhs)
    nonterminals = set(rules)
    terminals = {symbol for alternatives in rules.values() for rhs in alternatives
                 for symbol in rhs if symbol not in nonterminals}
    return rules, terminals


def to_lark_grammar(rules: Mapping[str, Sequence[tuple[str, ...]]],
                    terminals: set[str]) -> str:
    """Translate BNF rules into Lark rules without changing precedence."""
    lines = []
    for lhs, alternatives in rules.items():
        rendered = [" ".join(rhs) for rhs in alternatives]
        lines.append(f"{lhs}: " + "\n    | ".join(rendered))
    lines.append("%declare " + " ".join(sorted(terminals)))
    return "\n".join(lines)


def create_parser() -> Lark:
    """Build the shared Earley parser from the packaged grammar."""
    rules, terminals = read_grammar()
    return Lark(to_lark_grammar(rules, terminals), parser="earley",
                lexer=CandidateLexer, ambiguity="explicit", keep_all_tokens=True,
                propagate_positions=True)


def tree_to_ast(tree: Tree | Token,
                lexical: Mapping[tuple[str, int, int, str], LexicalCandidate]) -> AstNode | AstLeaf:
    """Convert a Lark tree into a grammar-preserving AST with source offsets."""
    if isinstance(tree, Token):
        key = (tree.type, tree.start_pos or 0, tree.end_pos or 0, str(tree))
        candidate = lexical.get(key)
        ids = candidate.law_ids if candidate else ()
        status = None if tree.type != "LAW" else (
            "unknown" if not ids else "known_unique" if len(ids) == 1 else "known_ambiguous")
        evidence = candidate.evidence if candidate else ()
        forms = candidate.matching_forms if candidate else ()
        return AstLeaf(tree.type, str(tree), tree.start_pos or 0, tree.end_pos or 0,
                       ids, status, evidence, forms)
    children = tuple(tree_to_ast(child, lexical) for child in tree.children)
    starts = [child.start for child in children]
    ends = [child.end for child in children]
    return AstNode(str(tree.data), start=min(starts, default=0), end=max(ends, default=0),
                   children=children)


def materialize_shape(shape: tuple, path):
    """Bind a cached grammar shape to the lexical tokens for one occurrence."""
    def materialize(node):
        kind, value, children = node
        if kind == "token":
            item = path[value]
            return Token(item.kind, item.value, start_pos=item.start, end_pos=item.end)
        return Tree(value, [materialize(child) for child in children])

    return materialize(shape)


def expand_trees(tree: Tree | Token):
    """Yield complete trees while retaining each explicit Earley alternative."""
    if isinstance(tree, Token):
        yield tree
        return
    child_options = tuple(tuple(expand_trees(child)) for child in tree.children)
    if str(tree.data) == "_ambig":
        for alternatives in child_options:
            yield from alternatives
        return
    for children in product(*child_options):
        yield Tree(tree.data, list(children), meta=tree.meta)
