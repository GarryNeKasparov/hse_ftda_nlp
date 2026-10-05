"""Project simple, unambiguous AST references into the LawLink response shape."""

from __future__ import annotations

from dataclasses import dataclass

from reference_parser import Analysis, AstLeaf, AstNode, CandidateSpan


@dataclass(frozen=True)
class LawLinkData:
    """Serializable values for one legal provision."""

    law_id: int | None
    article: str | None
    point_article: str | None
    subpoint_article: str | None


_LEVELS = {
    "article_level": "article",
    "part_level": "point_article",
    "point_level": "point_article",
    "subpoint_level": "subpoint_article",
}
_MARKER_KINDS = {"ARTICLE", "PART", "POINT", "SUBPOINT", "PP"}
_UNSUPPORTED_TOKENS = {
    "ORDINAL", "RANGE", "AND", "OR", "AND_OR", "COMMA", "IN",
    "PARAGRAPH", "SELF_ARTICLE", "SELF_PART", "SELF_POINT", "SELF_SUBPOINT",
    "SELF_PARAGRAPH", "SELF_LAW", "ANAPHORIC_LAW",
}


def project_simple_references(analysis: Analysis) -> list[LawLinkData]:
    """Return longest non-overlapping, single-chain references from an analysis."""
    projectable = []
    for candidate in analysis.candidates:
        if not candidate.complete or len(candidate.alternatives) != 1:
            continue
        projected = _project_candidate(candidate)
        if projected is not None:
            projectable.append((candidate, projected))

    selected = []
    consumed_until = -1
    for candidate, projected in sorted(
        projectable, key=lambda item: (item[0].start, -item[0].end)
    ):
        if candidate.start < consumed_until:
            continue
        selected.append(projected)
        consumed_until = candidate.end
    return selected


def _project_candidate(candidate: CandidateSpan) -> LawLinkData | None:
    """Map a single complete AST chain, declining grouped or unsupported forms."""
    tree = candidate.alternatives[0]
    leaves = tuple(_leaves(tree))
    if any(leaf.kind in _UNSUPPORTED_TOKENS for leaf in leaves):
        return None

    level_nodes = [node for node in _nodes(tree) if node.kind in _LEVELS]
    values: dict[str, str] = {}
    for level in level_nodes:
        field = _LEVELS[level.kind]
        if field in values:
            return None
        identifiers = [leaf.value for leaf in _leaves(level) if leaf.kind == "ID"]
        if len(identifiers) != 1:
            return None
        values[field] = identifiers[0]

    markers = [leaf for leaf in leaves if leaf.kind in _MARKER_KINDS]
    if len(markers) != len(level_nodes):
        return None
    law_mentions = [leaf for leaf in leaves if leaf.kind == "LAW"]
    if len(law_mentions) > 1:
        return None
    law_ids = law_mentions[0].law_ids if law_mentions else ()
    law_id = law_ids[0] if len(law_ids) == 1 else None

    return LawLinkData(
        law_id=law_id,
        article=values.get("article"),
        point_article=values.get("point_article"),
        subpoint_article=values.get("subpoint_article"),
    )


def _nodes(node: AstNode):
    """Yield AST nodes in source order."""
    yield node
    for child in node.children:
        if isinstance(child, AstNode):
            yield from _nodes(child)


def _leaves(node: AstNode):
    """Yield terminal leaves in source order."""
    for child in node.children:
        if isinstance(child, AstLeaf):
            yield child
        else:
            yield from _leaves(child)
