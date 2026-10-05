"""Project simple, unambiguous AST references into the LawLink response shape."""

from __future__ import annotations

from dataclasses import dataclass

from semantic_analyzer import (ProvisionPath, SemanticAnalysis,
                               SemanticDiagnostic)


@dataclass(frozen=True)
class LawLinkData:
    """Serializable values for one legal provision."""

    law_id: int | None
    article: str | None
    point_article: str | None
    subpoint_article: str | None


@dataclass(frozen=True)
class LawLinkMapping:
    """API records plus paths that do not fit the public LawLink schema."""

    links: tuple[LawLinkData, ...]
    diagnostics: tuple[SemanticDiagnostic, ...]


def map_semantic_analysis(analysis: SemanticAnalysis) -> LawLinkMapping:
    """Project representable paths and diagnose paths the API cannot express."""
    links = []
    diagnostics = []
    for reference in analysis.references:
        for provision in reference.provisions:
            link = _map_provision(provision)
            if link is not None:
                links.append(link)
            else:
                diagnostics.append(SemanticDiagnostic(
                    "provision_not_representable_in_law_link", reference.start, reference.end))
    return LawLinkMapping(tuple(links), tuple(diagnostics))


def _map_provision(provision: ProvisionPath) -> LawLinkData | None:
    """Map one path when its levels fit the four-field output contract."""
    if provision.paragraph is not None or (provision.part is not None and provision.point is not None):
        return None
    return LawLinkData(
        law_id=provision.law_id,
        article=provision.article,
        point_article=provision.point if provision.point is not None else provision.part,
        subpoint_article=provision.subpoint,
    )
