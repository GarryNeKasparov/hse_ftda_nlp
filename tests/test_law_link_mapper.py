"""Behavioral checks for projecting provision paths into LawLink."""

from pathlib import Path
import unittest

from law_link_mapper import map_semantic_analysis
from reference_parser import ReferenceAnalyzer
from semantic_analyzer import SemanticAnalyzer

ROOT = Path(__file__).resolve().parents[1]


class LawLinkMapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.syntax = ReferenceAnalyzer.from_alias_file(ROOT / "law_aliases.json")
        cls.semantic = SemanticAnalyzer()

    def map_text(self, text):
        analysis = self.semantic.analyze(self.syntax.analyze(text))
        return analysis, map_semantic_analysis(analysis)

    def test_projects_point_and_ignores_part_while_recording_internal_diagnostic(self):
        _, result = self.map_text("пункт 2 части 1 статьи 15 НК РФ")

        self.assertEqual([(link.law_id, link.article, link.point_article,
                           link.subpoint_article) for link in result.links],
                         [(15, "15", "2", None)])
        self.assertEqual([item.code for item in result.diagnostics],
                         ["unsupported_hierarchy_levels_omitted"])

    def test_projects_supported_levels_when_path_also_has_paragraph(self):
        _, result = self.map_text(
            "абзац 2 подпункта 3 пункта 4 статьи 10 НК РФ")

        self.assertEqual([(link.law_id, link.article, link.point_article,
                           link.subpoint_article) for link in result.links],
                         [(15, "10", "4", "3")])
        self.assertEqual([item.code for item in result.diagnostics],
                         ["unsupported_hierarchy_levels_omitted"])

    def test_projects_minimum_ambiguous_law_id_and_keeps_candidates_internally(self):
        analysis, result = self.map_text("статья 2 ФЗ №3-ФЗ")
        path = analysis.references[0].provisions[0]

        self.assertEqual(result.links[0].law_id, 249)
        self.assertEqual((path.law_status, path.law_candidate_ids),
                         ("known_ambiguous", (249, 472, 504, 542)))
        self.assertEqual([item.code for item in result.diagnostics],
                         ["ambiguous_law_identity_resolved_to_minimum"])


if __name__ == "__main__":
    unittest.main()
