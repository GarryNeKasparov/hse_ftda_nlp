"""Interpret syntax candidates as provision paths and expand simple lists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from reference_parser import Analysis, AstLeaf, AstNode, CandidateSpan


@dataclass(frozen=True)
class ProvisionPath:
    """One provision in an occurrence, retaining every internal level."""

    law_id: int | None
    law_status: str
    law_candidate_ids: tuple[int, ...]
    article: str | None = None
    part: str | None = None
    point: str | None = None
    subpoint: str | None = None
    paragraph: str | None = None


@dataclass(frozen=True)
class SemanticReference:
    """Expanded provision paths tied to one source occurrence."""

    start: int
    end: int
    provisions: tuple[ProvisionPath, ...]

    @property
    def span(self) -> tuple[int, int]:
        """Return the original half-open source span."""
        return self.start, self.end


@dataclass(frozen=True)
class SemanticDiagnostic:
    """A source-local interpretation that this semantic stage declined."""

    code: str
    start: int
    end: int


@dataclass(frozen=True)
class SemanticAnalysis:
    """Semantic references and unresolved candidate diagnostics for one text."""

    references: tuple[SemanticReference, ...]
    diagnostics: tuple[SemanticDiagnostic, ...]


_GROUP_FIELDS = {
    "article_group": ("article_level", "article"),
    "part_group": ("part_level", "part"),
    "point_group": ("point_level", "point"),
    "subpoint_group": ("subpoint_level", "subpoint"),
    "paragraph_group": ("paragraph_level", "paragraph"),
}
_LIST_CONNECTORS = {"COMMA", "AND", "OR", "AND_OR"}


class _UnsupportedSemantics(ValueError):
    """The current semantic policy does not define this valid syntax form."""


class SemanticAnalyzer:
    """Convert parsed references into provision paths and expand selector lists.

    This is the shared semantic stage for future work on parse alternatives,
    coordinated branches, and contextual targets. This version interprets
    complete references with scalar or coordinated scalar selectors; divergent
    branch structures remain unresolved.
    """

    def analyze(self, syntax: Analysis) -> SemanticAnalysis:
        """Interpret syntax candidates and retain unresolved cases as diagnostics."""
        diagnostics = [SemanticDiagnostic(item.code, item.start, item.end)
                       for item in syntax.diagnostics]
        by_start: dict[int, list[CandidateSpan]] = {}
        for candidate in syntax.candidates:
            if candidate.complete:
                by_start.setdefault(candidate.start, []).append(candidate)

        interpreted: list[SemanticReference] = []
        rejected_spans: list[tuple[int, int]] = []
        for candidates in by_start.values():
            candidate = max(candidates, key=lambda item: (item.end, -len(item.alternatives)))
            try:
                interpreted.extend(self._interpret(candidate))
            except _UnsupportedSemantics as error:
                diagnostics.append(SemanticDiagnostic(str(error), candidate.start, candidate.end))
                rejected_spans.append((candidate.start, candidate.end))

        # Candidate discovery exposes prefixes. Keep only the longest supported
        # interpretation at each overlapping occurrence, in source order.
        selected: list[SemanticReference] = []
        consumed_until = -1
        for reference in sorted(interpreted, key=lambda item: (item.start, -item.end)):
            overlaps_rejected = any(reference.start < end and start < reference.end
                                    for start, end in rejected_spans)
            if reference.start < consumed_until or overlaps_rejected:
                continue
            selected.append(reference)
            consumed_until = reference.end

        diagnostics = [item for item in diagnostics
                       if not (item.code == "unfinished_continuation"
                               and any(reference.start <= item.start
                                       and item.end <= reference.end
                                       for reference in selected))]
        unique_diagnostics = {(item.code, item.start, item.end): item for item in diagnostics}
        return SemanticAnalysis(tuple(selected), tuple(sorted(
            unique_diagnostics.values(), key=lambda item: (item.start, item.end, item.code))))

    def _interpret(self, candidate: CandidateSpan) -> tuple[SemanticReference, ...]:
        alternatives = []
        failures = []
        for tree in candidate.alternatives:
            try:
                reference_nodes = [node for node in self._walk_nodes(tree)
                                   if node.kind == "reference"]
                if not reference_nodes:
                    raise _UnsupportedSemantics("expected_reference")
                occurrences = []
                for reference in reference_nodes:
                    leaves = tuple(self._walk_leaves(reference))
                    if not leaves:
                        raise _UnsupportedSemantics("reference_without_source_tokens")
                    start = min(leaf.start for leaf in leaves)
                    end = max(leaf.end for leaf in leaves)
                    occurrences.append(SemanticReference(
                        start, end, self._interpret_tree(reference)))
                alternatives.append(tuple(sorted(occurrences,
                                                 key=lambda item: (item.start, item.end))))
            except _UnsupportedSemantics as error:
                failures.append(str(error))
        if failures:
            code = ("competing_syntax_alternatives" if len(candidate.alternatives) > 1
                    else failures[0])
            raise _UnsupportedSemantics(code)
        if not alternatives or any(result != alternatives[0] for result in alternatives[1:]):
            raise _UnsupportedSemantics("competing_syntax_alternatives")
        return alternatives[0]

    def _interpret_tree(self, tree: AstNode) -> tuple[ProvisionPath, ...]:
        provision_groups = [node for node in self._walk_nodes(tree)
                            if node.kind in _GROUP_FIELDS]
        root_groups = [node for node in provision_groups
                       if not self._has_ancestor_group(tree, node)]
        if not root_groups:
            raise _UnsupportedSemantics("expected_provision_branch")
        if any(node.kind and node.kind.endswith("_children_tail") and node.children
               for node in self._walk_nodes(tree)):
            raise _UnsupportedSemantics("coordinated_child_groups_not_yet_resolved")
        paths = [path for group in root_groups for path in self._expand_group(group)]
        if len(root_groups) > 1:
            path_shapes = {tuple(sorted(key for key, value in path.items() if value is not None))
                           for path in paths}
            if len(path_shapes) != 1:
                raise _UnsupportedSemantics("coordinated_branches_not_yet_resolved")
        law_leaves = [leaf for leaf in self._walk_leaves(tree)
                      if leaf.kind in {"LAW", "SELF_LAW", "ANAPHORIC_LAW"}]
        if len(law_leaves) > 1:
            raise _UnsupportedSemantics("multiple_law_mentions")
        law = law_leaves[0] if law_leaves else None
        law_status = ("unspecified" if law is None else
                      law.law_status if law.kind == "LAW" else
                      "self" if law.kind == "SELF_LAW" else "anaphoric")
        candidate_ids = law.law_ids if law is not None else ()
        law_id = candidate_ids[0] if law_status == "known_unique" and len(candidate_ids) == 1 else None
        provisions = tuple(ProvisionPath(law_id=law_id, law_status=law_status,
                                         law_candidate_ids=candidate_ids, **path)
                           for path in paths)
        if not provisions:
            raise _UnsupportedSemantics("empty_provision_expansion")
        return provisions

    def _expand_group(self, group: AstNode) -> list[dict[str, str | None]]:
        level_kind, field = _GROUP_FIELDS[group.kind]
        level_nodes = [node for node in self._descendants_before_group(group)
                       if node.kind == level_kind]
        if len(level_nodes) != 1:
            raise _UnsupportedSemantics("missing_or_repeated_hierarchy_level")
        values = self._selector_values(level_nodes[0])
        children = self._child_groups(group)
        if len(children) > 1:
            raise _UnsupportedSemantics("coordinated_child_groups_not_yet_resolved")
        if children:
            lower_paths = self._expand_group(children[0])
        else:
            lower_paths = [{}]
        return [{**lower, field: value} for lower in lower_paths for value in values]

    def _selector_values(self, level: AstNode) -> list[str]:
        selectors = [node for node in self._walk_nodes(level) if node.kind == "selector"]
        if len(selectors) != 1:
            raise _UnsupportedSemantics("missing_or_repeated_selector")
        selector = selectors[0]
        items = [node for node in self._walk_nodes(selector) if node.kind == "item"]
        if not items:
            raise _UnsupportedSemantics("empty_selector")
        values = []
        for item in items:
            leaves = tuple(self._walk_leaves(item))
            identifiers = [leaf for leaf in leaves if leaf.kind in {"ID", "ORDINAL"}]
            if len(identifiers) != 1 or identifiers[0].kind != "ID":
                raise _UnsupportedSemantics("non_scalar_or_ordinal_selector")
            if any(leaf.kind == "RANGE" for leaf in leaves):
                raise _UnsupportedSemantics("range_expansion_not_yet_resolved")
            values.append(identifiers[0].value)
        connectors = [leaf.kind for leaf in self._walk_leaves(selector)
                      if leaf.kind in {"COMMA", "AND", "OR", "AND_OR"}]
        if any(connector not in _LIST_CONNECTORS for connector in connectors):
            raise _UnsupportedSemantics("disjunctive_selector_policy_not_yet_resolved")
        if len(connectors) != len(items) - 1:
            raise _UnsupportedSemantics("unsupported_selector_separator")
        return values

    @classmethod
    def _child_groups(cls, group: AstNode) -> list[AstNode]:
        found = []

        def visit(node):
            for child in node.children:
                if isinstance(child, AstNode) and child.kind in _GROUP_FIELDS:
                    found.append(child)
                elif isinstance(child, AstNode):
                    visit(child)

        visit(group)
        return found

    @classmethod
    def _descendants_before_group(cls, group: AstNode) -> Iterable[AstNode]:
        def visit(node):
            for child in node.children:
                if not isinstance(child, AstNode):
                    continue
                if child.kind in _GROUP_FIELDS:
                    continue
                yield child
                yield from visit(child)

        return visit(group)

    @classmethod
    def _has_ancestor_group(cls, root: AstNode, target: AstNode) -> bool:
        def visit(node, seen_group=False):
            if node is target:
                return seen_group
            next_seen = seen_group or (node is not root and node.kind in _GROUP_FIELDS)
            return any(visit(child, next_seen) for child in node.children
                       if isinstance(child, AstNode))

        return visit(root)

    @staticmethod
    def _walk_nodes(node: AstNode):
        yield node
        for child in node.children:
            if isinstance(child, AstNode):
                yield from SemanticAnalyzer._walk_nodes(child)

    @staticmethod
    def _walk_leaves(node: AstNode):
        for child in node.children:
            if isinstance(child, AstLeaf):
                yield child
            else:
                yield from SemanticAnalyzer._walk_leaves(child)
