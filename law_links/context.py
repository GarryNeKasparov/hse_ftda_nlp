"""Resolve context-dependent law identities across semantic references."""

from __future__ import annotations

from dataclasses import replace

from law_links.semantic import (ProvisionPath, SemanticAnalysis,
                                SemanticDiagnostic, SemanticReference)


class ContextualResolver:
    """Resolve omitted and anaphoric law targets in source order."""

    def resolve(self, analysis: SemanticAnalysis) -> SemanticAnalysis:
        """Carry the last explicit law through later compatible references."""
        last_law: tuple[int | None, str, tuple[int, ...]] | None = None
        last_article: str | None = None
        last_article_law: tuple[int | None, str, tuple[int, ...]] | None = None
        article_contexts: list[tuple[str, tuple[int | None, str, tuple[int, ...]]]] = []
        references = []
        diagnostics = list(analysis.diagnostics)

        for reference in sorted(analysis.references, key=lambda item: (item.start, item.end)):
            provisions = []
            for provision in reference.provisions:
                target_status = provision.law_target_status
                law_is_explicit = target_status == "explicit"
                if law_is_explicit:
                    last_law = (provision.law_id, provision.law_status,
                                provision.law_candidate_ids)
                elif last_law is not None:
                    provision = replace(provision, law_id=last_law[0],
                                        law_status=last_law[1],
                                        law_candidate_ids=last_law[2],
                                        law_target_status=(
                                            "inherited" if target_status == "unspecified"
                                            else f"resolved_{target_status}"))
                    diagnostics.append(SemanticDiagnostic(
                        "contextual_law_inherited", reference.start, reference.end))

                if provision.article is not None:
                    last_article = provision.article
                    last_article_law = (provision.law_id, provision.law_status,
                                        provision.law_candidate_ids)
                    article_contexts.append((last_article, last_article_law))
                elif provision.article_status in {"self", "anaphoric"}:
                    current_law = (provision.law_id, provision.law_status,
                                  provision.law_candidate_ids)
                    antecedent = next((item for item in reversed(article_contexts)
                                       if self._compatible_laws(current_law, item[1])), None)
                    if antecedent is not None:
                        provision = replace(provision, article=antecedent[0],
                                            article_status=f"resolved_{provision.article_status}")
                        last_article = provision.article
                        last_article_law = current_law
                        article_contexts.append((last_article, last_article_law))
                        diagnostics.append(SemanticDiagnostic(
                            "contextual_article_inherited", reference.start, reference.end))
                provisions.append(provision)
            references.append(SemanticReference(
                reference.start, reference.end, tuple(provisions)))

        unique = {(item.code, item.start, item.end): item for item in diagnostics}
        return SemanticAnalysis(tuple(references), tuple(sorted(
            unique.values(), key=lambda item: (item.start, item.end, item.code))))

    @staticmethod
    def _compatible_laws(current, antecedent) -> bool:
        """Reject article antecedents whose known law identity conflicts."""
        if antecedent is None:
            return True
        current_ids = set(current[2])
        antecedent_ids = set(antecedent[2])
        if current_ids and not antecedent_ids:
            return False
        return not current_ids or not antecedent_ids or bool(current_ids & antecedent_ids)
