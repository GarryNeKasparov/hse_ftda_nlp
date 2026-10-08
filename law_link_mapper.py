"""Project supported provision fields into the fixed LawLink response shape."""

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
            links.append(_map_provision(provision))
            if provision.part is not None and provision.point is not None:
                diagnostics.append(SemanticDiagnostic(
                    "unsupported_hierarchy_levels_omitted", reference.start, reference.end))
            if provision.paragraph is not None:
                diagnostics.append(SemanticDiagnostic(
                    "unsupported_hierarchy_levels_omitted", reference.start, reference.end))
            if provision.law_status == "known_ambiguous":
                diagnostics.append(SemanticDiagnostic(
                    "ambiguous_law_identity_resolved_to_minimum", reference.start,
                    reference.end))
    return LawLinkMapping(tuple(links), tuple(diagnostics))


def _map_provision(provision: ProvisionPath) -> LawLinkData:
    """Project each supported field and leave other hierarchy levels internal."""
    law_id = provision.law_id
    if provision.law_status == "known_ambiguous" and provision.law_candidate_ids:
        law_id = min(provision.law_candidate_ids)
    return LawLinkData(
        law_id=law_id,
        article=provision.article,
        point_article=provision.point if provision.point is not None else provision.part,
        subpoint_article=provision.subpoint,
    )
