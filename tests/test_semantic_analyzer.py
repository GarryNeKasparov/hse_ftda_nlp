"""Behavioral checks for syntax-to-provision semantic analysis."""

from pathlib import Path
import unittest

from reference_parser import ReferenceAnalyzer
from semantic_analyzer import SemanticAnalyzer

ROOT = Path(__file__).resolve().parents[1]


class SemanticAnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.syntax = ReferenceAnalyzer.from_alias_file(ROOT / "law_aliases.json")
        cls.semantic = SemanticAnalyzer()

    def analyze(self, text):
        return self.semantic.analyze(self.syntax.analyze(text))

    def test_expands_subpoint_list_and_carries_shared_parents_and_law(self):
        text = "пп. 1, 2, 3 п. 2 ст. 3 НК РФ"

        result = self.analyze(text)

        self.assertEqual(len(result.references), 1)
        self.assertEqual(result.references[0].span, (0, len(text)))
        self.assertEqual(result.references[0].provisions, (
            self.path(law_id=15, article="3", point="2", subpoint="1"),
            self.path(law_id=15, article="3", point="2", subpoint="2"),
            self.path(law_id=15, article="3", point="2", subpoint="3"),
        ))
        self.assertEqual(result.diagnostics, ())

    def test_expands_conjoined_subpoint_list_in_source_order(self):
        text = ('пп. 4, 5, 6 и 8 п. 1 ст. 14 Федерального закона '
                '"О государственной регистрации недвижимости"')

        result = self.analyze(text)

        self.assertEqual([item.subpoint for item in result.references[0].provisions],
                         ["4", "5", "6", "8"])
        self.assertTrue(all(item.law_id == 174
                            and item.article == "14" and item.point == "1"
                            for item in result.references[0].provisions))

    def test_expands_parent_selector_list(self):
        text = "пункты 1 и 2 статьи 299 ГК РФ"

        result = self.analyze(text)

        self.assertEqual([item.point for item in result.references[0].provisions],
                         ["1", "2"])
        self.assertTrue(all(item.article == "299" and item.law_id == 5
                            for item in result.references[0].provisions))

    def test_shared_law_applies_to_each_coordinated_article_branch(self):
        result = self.analyze("пункт 2 статьи 5 и пункт 3 статьи 6 НК РФ")

        self.assertEqual(result.references[0].provisions, (
            self.path(law_id=15, article="5", point="2"),
            self.path(law_id=15, article="6", point="3"),
        ))
        self.assertEqual(result.diagnostics, ())

    def test_mixed_depth_branches_inherit_article_without_crossing(self):
        result = self.analyze("пункт 2 части 1 и часть 3 статьи 15")

        self.assertEqual(result.references[0].provisions, (
            self.path(law_id=None, law_status="unspecified", article="15",
                      part="1", point="2"),
            self.path(law_id=None, law_status="unspecified", article="15",
                      part="3"),
        ))
        self.assertEqual(result.diagnostics, ())

    def test_expands_mixed_depth_branches_under_shared_article_and_law(self):
        text = ("пунктами 2, 4, 6, подпунктами 1 и 2 пункта 9 "
                "статьи 1483 ГК РФ")

        result = self.analyze(text)

        self.assertEqual(result.references[0].provisions, (
            self.path(law_id=5, article="1483", point="2"),
            self.path(law_id=5, article="1483", point="4"),
            self.path(law_id=5, article="1483", point="6"),
            self.path(law_id=5, article="1483", point="9", subpoint="1"),
            self.path(law_id=5, article="1483", point="9", subpoint="2"),
        ))
        self.assertEqual(result.diagnostics, ())

    def test_expands_lists_at_two_levels_within_their_shared_branch(self):
        text = "пп. 1, 2 п. 3, 4 ст. 5 НК РФ"

        result = self.analyze(text)

        self.assertEqual([(item.point, item.subpoint)
                          for item in result.references[0].provisions],
                         [("3", "1"), ("4", "1"), ("3", "2"), ("4", "2")])

    def test_retains_unknown_and_unspecified_law_statuses(self):
        unknown = self.analyze("ст. 6 рандомного кодекса").references[0].provisions[0]
        unspecified = self.analyze("ст. 6").references[0].provisions[0]

        self.assertEqual((unknown.law_id, unknown.law_status, unknown.law_candidate_ids),
                         (None, "unknown", ()))
        self.assertEqual((unspecified.law_id, unspecified.law_status,
                          unspecified.law_candidate_ids), (None, "unspecified", ()))

    def test_keeps_two_explicit_law_citations_as_separate_occurrences(self):
        result = self.analyze("ст. 5 НК РФ и п. 2 ст. 6 ГК РФ")

        self.assertEqual([item.span for item in result.references], [(0, 11), (14, 30)])
        self.assertEqual(result.references[0].provisions[0].law_id, 15)
        self.assertEqual(result.references[1].provisions[0].law_id, 5)
        self.assertEqual(result.references[1].provisions[0].point, "2")

    def test_one_citation_in_prose_has_one_final_occurrence_span(self):
        text = "Согласно пункту 2 статьи 5 НК РФ, применяется правило."

        result = self.analyze(text)

        self.assertEqual(len(result.references), 1)
        self.assertEqual(result.references[0].span,
                         (text.index("пункт"), text.index(",")))
        self.assertEqual(result.references[0].provisions, (
            self.path(law_id=15, article="5", point="2"),
        ))

    def test_prose_conjunction_after_citation_does_not_shorten_its_span(self):
        text = "В тексте указана статья 5 НК РФ, и она применяется на практике."

        result = self.analyze(text)

        self.assertEqual(len(result.references), 1)
        self.assertEqual(result.references[0].span,
                         (text.index("статья"), text.index(",")))
        self.assertEqual(result.references[0].provisions,
                         (self.path(law_id=15, article="5"),))

    def test_two_prose_citations_keep_source_order_and_duplicates(self):
        result = self.analyze(
            "Согласно ст. 5 НК РФ, действует правило. "
            "Ст. 5 НК РФ также упоминается ниже.")

        self.assertEqual([item.provisions for item in result.references], [
            (self.path(law_id=15, article="5"),),
            (self.path(law_id=15, article="5"),),
        ])
        self.assertLess(result.references[0].start, result.references[1].start)

    def test_unsupported_longer_range_does_not_leak_its_first_number(self):
        result = self.analyze("пункты 2-4 статьи 10 НК РФ")

        self.assertEqual(result.references, ())
        self.assertTrue(any(item.code == "competing_syntax_alternatives"
                            for item in result.diagnostics))

    def test_expands_explicit_integer_range_in_written_order(self):
        for dash in ("–", "—"):
            with self.subTest(dash=dash):
                text = (f"Согласно пунктам 2{dash}4 статьи 10 НК РФ, "
                        "действует правило.")
                result = self.analyze(text)

                self.assertEqual(result.references[0].provisions, (
                    self.path(law_id=15, article="10", point="2"),
                    self.path(law_id=15, article="10", point="3"),
                    self.path(law_id=15, article="10", point="4"),
                ))
                self.assertEqual(result.references[0].span,
                                 (text.index("пункт"), text.index(",")))
                self.assertEqual(result.diagnostics, ())

    def test_expands_ranges_inside_a_selector_list_and_keeps_parent_values(self):
        result = self.analyze("пункты 2, 4–5 и 8 статьи 10 НК РФ")

        self.assertEqual(result.references[0].provisions, (
            self.path(law_id=15, article="10", point="2"),
            self.path(law_id=15, article="10", point="4"),
            self.path(law_id=15, article="10", point="5"),
            self.path(law_id=15, article="10", point="8"),
        ))

    def test_leaves_dotted_ranges_unresolved(self):
        result = self.analyze("пункты 2.3–2.5 статьи 10 НК РФ")

        self.assertEqual(result.references, ())
        self.assertTrue(any(item.code == "unsupported_range_endpoints"
                            for item in result.diagnostics))

    def test_keeps_ascii_hyphen_identifier_range_ambiguity_unresolved(self):
        result = self.analyze("пункт 2-1 статьи 10 НК РФ")

        self.assertEqual(result.references, ())
        self.assertTrue(any(item.code == "competing_syntax_alternatives"
                            for item in result.diagnostics))

    def test_rejects_reversed_explicit_integer_range(self):
        result = self.analyze("пункты 4–2 статьи 10 НК РФ")

        self.assertEqual(result.references, ())
        self.assertTrue(any(item.code == "reversed_range"
                            for item in result.diagnostics))

    def test_rejects_ranges_that_expand_to_too_many_provisions(self):
        result = self.analyze("пункты 1–1001 статьи 10 НК РФ")

        self.assertEqual(result.references, ())
        self.assertTrue(any(item.code == "range_too_large"
                            for item in result.diagnostics))

    @staticmethod
    def path(*, law_id, article=None, part=None, point=None, subpoint=None,
             paragraph=None, law_status="known_unique", law_candidate_ids=()):
        """Construct one independently specified provision path."""
        from semantic_analyzer import ProvisionPath
        if law_id is not None and not law_candidate_ids:
            law_candidate_ids = (law_id,)
        return ProvisionPath(law_id=law_id, law_status=law_status,
                             law_candidate_ids=law_candidate_ids,
                             law_target_status=("unspecified" if law_status == "unspecified"
                                                else "self" if law_status == "self"
                                                else "anaphoric" if law_status == "anaphoric"
                                                else "explicit"),
                             article=article,
                             article_status="explicit" if article is not None else "unspecified",
                             part=part, point=point, subpoint=subpoint,
                             paragraph=paragraph)


if __name__ == "__main__":
    unittest.main()
