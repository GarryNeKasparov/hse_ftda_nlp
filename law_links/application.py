"""Compose the extraction stages behind one text-to-links interface."""

from __future__ import annotations

from pathlib import Path

from law_links.context import ContextualResolver
from law_links.projection import LawLinkData, map_semantic_analysis
from law_links.semantic import SemanticAnalyzer
from law_links.syntax.analyzer import ReferenceAnalyzer


class LegalReferenceDetector:
    """Run the reusable syntax, semantic, context, and projection stages."""

    def __init__(self, reference_analyzer: ReferenceAnalyzer,
                 semantic_analyzer: SemanticAnalyzer,
                 contextual_resolver: ContextualResolver):
        self.reference_analyzer = reference_analyzer
        self.semantic_analyzer = semantic_analyzer
        self.contextual_resolver = contextual_resolver

    def detect(self, text: str) -> tuple[LawLinkData, ...]:
        """Extract ordered LawLink values from one source text."""
        syntax = self.reference_analyzer.analyze_for_service(text)
        semantic = self.semantic_analyzer.analyze(syntax)
        resolved = self.contextual_resolver.resolve(semantic)
        return map_semantic_analysis(resolved).links


def build_detector(aliases_path: str | Path | None = None) -> LegalReferenceDetector:
    """Build the reusable detector and load its law dictionary once."""
    if aliases_path is None:
        aliases_path = Path(__file__).resolve().parents[1] / "data" / "law_aliases.json"
    analyzer = ReferenceAnalyzer.from_alias_file(aliases_path)
    return LegalReferenceDetector(analyzer, SemanticAnalyzer(), ContextualResolver())
