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
    law_target_status: str = "unspecified"
    article: str | None = None
    article_status: str = "unspecified"
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
_MAX_RANGE_VALUES = 1000


class _UnsupportedSemantics(ValueError):
    """The current semantic policy does not define this valid syntax form."""


class SemanticAnalyzer:
    """Convert parsed references into provision paths and expand selector lists.

    This is the shared semantic stage for parse alternatives, coordinated
    branches, and contextual targets. It expands branch-local selectors and
    carries common parent levels and a single final law tail to each branch.
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
                law_leaves = [leaf for leaf in self._walk_leaves(tree)
                              if leaf.kind in {"LAW", "SELF_LAW", "ANAPHORIC_LAW"}]
                if (len(reference_nodes) > 1 and len(law_leaves) == 1
                        and law_leaves[0].kind == "LAW"
                        and any(leaf is law_leaves[0]
                                for leaf in self._walk_leaves(reference_nodes[-1]))):
                    law = law_leaves[0]
                    law_id = (law.law_ids[0] if law.law_status == "known_unique"
                              and len(law.law_ids) == 1 else None)
                    propagated = []
                    for occurrence in occurrences:
                        provisions = tuple(ProvisionPath(
                            law_id=law_id,
                            law_status=law.law_status or "unknown",
                            law_candidate_ids=law.law_ids,
                            law_target_status="explicit",
                            article=path.article, article_status=path.article_status,
                            part=path.part, point=path.point,
                            subpoint=path.subpoint, paragraph=path.paragraph)
                            for path in occurrence.provisions)
                        propagated.extend(provisions)
                    occurrences = [SemanticReference(
                        min(item.start for item in occurrences),
                        max(item.end for item in occurrences), tuple(propagated))]
                alternatives.append(tuple(sorted(occurrences,
                                                 key=lambda item: (item.start, item.end))))
            except _UnsupportedSemantics as error:
                failures.append(str(error))
        if failures:
            code = ("competing_syntax_alternatives" if len(candidate.alternatives) > 1
                    else failures[0])
            raise _UnsupportedSemantics(code)
        if not alternatives:
            raise _UnsupportedSemantics("competing_syntax_alternatives")
        if all(result == alternatives[0] for result in alternatives[1:]):
            return alternatives[0]
        return self._select_refined_alternative(alternatives)

    @staticmethod
    def _select_refined_alternative(
            alternatives: list[tuple[SemanticReference, ...]]) -> tuple[SemanticReference, ...]:
        """Choose a uniquely more complete reading when paths otherwise agree."""
        flattened = [tuple(path for reference in result for path in reference.provisions)
                     for result in alternatives]
        if not flattened or any(len(paths) != len(flattened[0]) for paths in flattened[1:]):
            raise _UnsupportedSemantics("competing_syntax_alternatives")

        def refines(more, less):
            fields = ("article", "part", "point", "subpoint", "paragraph")
            for field in fields:
                less_value = getattr(less, field)
                more_value = getattr(more, field)
                if less_value is not None and more_value != less_value:
                    return False
            if less.law_status not in {"unspecified", more.law_status}:
                return False
            if (less.law_status != "unspecified"
                    and (less.law_id, less.law_candidate_ids)
                    != (more.law_id, more.law_candidate_ids)):
                return False
            return True

        ranks = [sum(sum(getattr(path, field) is not None for field in
                         ("article", "part", "point", "subpoint", "paragraph"))
                     + (path.law_status != "unspecified") for path in paths)
                 for paths in flattened]
        best_rank = max(ranks)
        best = [index for index, rank in enumerate(ranks) if rank == best_rank]
        if any(flattened[index] != flattened[best[0]] for index in best[1:]):
            raise _UnsupportedSemantics("competing_syntax_alternatives")
        selected = best[0]
        if any(not all(refines(preferred, alternative)
                       for preferred, alternative in zip(flattened[selected], paths))
               for paths in flattened):
            raise _UnsupportedSemantics("competing_syntax_alternatives")
        return alternatives[selected]

    def _interpret_tree(self, tree: AstNode) -> tuple[ProvisionPath, ...]:
        provision_groups = [node for node in self._walk_nodes(tree)
                            if node.kind in _GROUP_FIELDS]
        root_groups = [node for node in provision_groups
                       if not self._has_ancestor_group(tree, node)]
        if not root_groups:
            raise _UnsupportedSemantics("expected_provision_branch")
        paths = [path for group in root_groups for path in self._expand_group(group)]
        law_leaves = [leaf for leaf in self._walk_leaves(tree)
                      if leaf.kind in {"LAW", "SELF_LAW", "ANAPHORIC_LAW"}]
        if len(law_leaves) > 1:
            raise _UnsupportedSemantics("multiple_law_mentions")
        law = law_leaves[0] if law_leaves else None
        article_target = next((leaf for leaf in self._walk_leaves(tree)
                               if leaf.kind in {"SELF_ARTICLE", "ANAPHORIC_ARTICLE"}), None)
        article_status = ("self" if article_target.kind == "SELF_ARTICLE" else "anaphoric") \
            if article_target is not None else "unspecified"
        law_status = ("unspecified" if law is None else
                      law.law_status if law.kind == "LAW" else
                      "self" if law.kind == "SELF_LAW" else "anaphoric")
        law_target_status = ("unspecified" if law is None else
                             "explicit" if law.kind == "LAW" else
                             "self" if law.kind == "SELF_LAW" else "anaphoric")
        candidate_ids = law.law_ids if law is not None else ()
        law_id = candidate_ids[0] if law_status == "known_unique" and len(candidate_ids) == 1 else None
        provisions = tuple(ProvisionPath(
            law_id=law_id, law_status=law_status, law_candidate_ids=candidate_ids,
            law_target_status=law_target_status,
            article_status=("explicit" if path.get("article") is not None else article_status),
            **path) for path in paths)
        if not provisions:
            raise _UnsupportedSemantics("empty_provision_expansion")
        return provisions

    def _expand_group(self, group: AstNode) -> list[dict[str, str | None]]:
        level_kind, field = _GROUP_FIELDS[group.kind]
        level_nodes = [node for node in self._descendants_before_group(group)
                       if node.kind == level_kind]
        if len(level_nodes) != 1:
            raise _UnsupportedSemantics("missing_or_repeated_hierarchy_level")
        structural_self = (field == "article" and any(
            leaf.kind in {"SELF_ARTICLE", "ANAPHORIC_ARTICLE"}
            for leaf in self._walk_leaves(level_nodes[0])))
        values = ([None] if structural_self else
                  self._selector_values(level_nodes[0], allow_ordinals=field == "paragraph"))
        children = self._child_groups(group)
        if children:
            lower_paths = [path for child in children
                           for path in self._expand_group(child)]
        else:
            lower_paths = [{}]
        return [{**lower, field: value} for lower in lower_paths for value in values]

    def _selector_values(self, level: AstNode, *,
                         allow_ordinals: bool = False) -> list[str]:
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
            ranges = [leaf for leaf in leaves if leaf.kind == "RANGE"]
            if ranges:
                if (len(ranges) != 1 or len(identifiers) != 2
                        or any(identifier.kind != "ID"
                               and not (allow_ordinals and identifier.kind == "ORDINAL")
                               for identifier in identifiers)):
                    raise _UnsupportedSemantics("unsupported_range_endpoints")
                first, last = (self._selector_number(identifier, allow_ordinals)
                               for identifier in identifiers)
                if first is None or last is None:
                    raise _UnsupportedSemantics("unsupported_range_endpoints")
                if any(not endpoint.isascii() or not endpoint.isdigit()
                       for endpoint in (first, last)):
                    raise _UnsupportedSemantics("unsupported_range_endpoints")
                first_number, last_number = int(first), int(last)
                if first_number > last_number:
                    raise _UnsupportedSemantics("reversed_range")
                if last_number - first_number + 1 > _MAX_RANGE_VALUES:
                    raise _UnsupportedSemantics("range_too_large")
                values.extend(str(number) for number in range(first_number, last_number + 1))
                continue
            if (len(identifiers) != 1
                    or (identifiers[0].kind != "ID"
                        and not (allow_ordinals and identifiers[0].kind == "ORDINAL"))):
                raise _UnsupportedSemantics("non_scalar_or_ordinal_selector")
            value = self._selector_number(identifiers[0], allow_ordinals)
            if value is None:
                raise _UnsupportedSemantics("unsupported_ordinal_selector")
            values.append(value)
        connectors = [leaf for leaf in self._walk_leaves(selector)
                      if leaf.kind in {"COMMA", "AND", "OR", "AND_OR"}]
        item_spans = []
        for item in items:
            item_leaves = tuple(self._walk_leaves(item))
            item_spans.append((min(leaf.start for leaf in item_leaves),
                               max(leaf.end for leaf in item_leaves)))
        joins = [sum(left_end <= leaf.start and leaf.end <= right_start
                     for leaf in connectors)
                 for (_, left_end), (right_start, _) in zip(item_spans, item_spans[1:])]
        if (len(joins) != len(items) - 1 or any(count == 0 for count in joins)
                or sum(joins) != len(connectors)):
            raise _UnsupportedSemantics("unsupported_selector_separator")
        return values

    @staticmethod
    def _selector_number(leaf: AstLeaf, allow_ordinals: bool) -> str | None:
        """Return a scalar selector or a supported paragraph ordinal value."""
        if leaf.kind == "ID":
            return leaf.value
        if not allow_ordinals or leaf.kind != "ORDINAL":
            return None
        prefix = "ordinal_value:"
        value = next((item[len(prefix):] for item in leaf.evidence
                      if item.startswith(prefix)), None)
        return value if value is not None and value.isascii() and value.isdigit() else None

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
