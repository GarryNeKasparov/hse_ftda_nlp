"""Focused tests for defensive paths that ordinary citations rarely reach."""

from pathlib import Path
import runpy
from unittest import TestCase
from unittest.mock import patch

from law_links.context import ContextualResolver
from law_links.syntax.analyzer import ReferenceAnalyzer, _Edge, _RawToken
from law_links.syntax.models import (AstLeaf, AstNode, CandidateSpan,
                                     LexicalCandidate)
from law_links.semantic import (ProvisionPath, SemanticAnalysis,
                               SemanticAnalyzer, SemanticReference,
                               _UnsupportedSemantics)

ROOT = Path(__file__).resolve().parents[1]


class CoverageEdgeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = ReferenceAnalyzer.from_alias_file(ROOT / "data/law_aliases.json")
        cls.semantic = SemanticAnalyzer()

    def test_incompatible_law_article_context_and_empty_antecedent(self):
        self.assertTrue(ContextualResolver._compatible_laws((None, "unknown", ()), None))

    def test_health_endpoint_and_module_entry_point(self):
        from fastapi.testclient import TestClient
        import main

        with TestClient(main.app) as client:
            self.assertEqual(client.get("/health").json(), {"status": "healthy"})
        with patch("uvicorn.run") as run:
            runpy.run_path(str(ROOT / "main.py"), run_name="__main__")
        run.assert_called_once()

    def test_semantic_rejects_malformed_trees(self):
        empty = AstNode("root")
        no_reference = CandidateSpan(0, 0, (empty,))
        with self.assertRaisesRegex(_UnsupportedSemantics, "expected_reference"):
            self.semantic._interpret(no_reference)

        empty_reference = AstNode("reference")
        with self.assertRaisesRegex(_UnsupportedSemantics, "reference_without_source_tokens"):
            self.semantic._interpret(CandidateSpan(0, 0, (AstNode("root", children=(empty_reference,)),)))

        group_without_level = AstNode("article_group")
        reference = AstNode("reference", children=(group_without_level,))
        with self.assertRaisesRegex(_UnsupportedSemantics, "missing_or_repeated_hierarchy_level"):
            self.semantic._interpret_tree(reference)
        with self.assertRaisesRegex(_UnsupportedSemantics, "expected_provision_branch"):
            self.semantic._interpret_tree(AstNode("reference"))

        with self.assertRaisesRegex(_UnsupportedSemantics, "competing_syntax_alternatives"):
            self.semantic._interpret(CandidateSpan(0, 0, ()))

        selector = AstNode("selector", children=(AstNode("item", children=(
            AstLeaf("ID", "1", 0, 1),)),))
        group = AstNode("article_group", children=(AstNode(
            "article_level", children=(selector,)),))
        multi_law = AstNode("reference", children=(
            group, AstLeaf("LAW", "law one", 0, 1, (1,), "known_unique"),
            AstLeaf("LAW", "law two", 2, 3, (2,), "known_unique")))
        with self.assertRaisesRegex(_UnsupportedSemantics, "multiple_law_mentions"):
            self.semantic._interpret_tree(multi_law)

    def test_semantic_rejects_empty_selector_expansion_and_bad_separator(self):
        with self.assertRaisesRegex(_UnsupportedSemantics, "missing_or_repeated_selector"):
            self.semantic._selector_values(AstNode("article_level"))
        empty = AstNode("article_level", children=(AstNode("selector"),))
        with self.assertRaisesRegex(_UnsupportedSemantics, "empty_selector"):
            self.semantic._selector_values(empty)

        selector = AstNode("selector", children=(
            AstNode("item", children=(AstLeaf("ID", "1", 0, 1),)),
            AstNode("item", children=(AstLeaf("ID", "2", 2, 3),))))
        with self.assertRaisesRegex(_UnsupportedSemantics, "unsupported_selector_separator"):
            self.semantic._selector_values(selector)

        valid_group = AstNode("article_group", children=(AstNode("article_level"),))
        reference = AstNode("reference", children=(valid_group,))
        with patch.object(self.semantic, "_expand_group", return_value=[]):
            with self.assertRaisesRegex(_UnsupportedSemantics, "empty_provision_expansion"):
                self.semantic._interpret_tree(reference)

    def test_semantic_refinement_rejects_equal_rank_or_conflicting_paths(self):
        def reading(path):
            return (SemanticReference(0, 2, (path,)),)

        base = ProvisionPath(None, "unspecified", ())
        with self.assertRaisesRegex(_UnsupportedSemantics, "competing_syntax_alternatives"):
            self.semantic._select_refined_alternative(
                [reading(ProvisionPath(None, "unspecified", (), article="5")),
                 reading(ProvisionPath(None, "unspecified", (), point="2"))])

        with self.assertRaisesRegex(_UnsupportedSemantics, "competing_syntax_alternatives"):
            self.semantic._select_refined_alternative(
                [reading(ProvisionPath(None, "unspecified", (), article="5")),
                 reading(ProvisionPath(None, "unspecified", (), article="6", point="2"))])

        more = ProvisionPath(1, "unknown", (), article="5", point="2")
        less = ProvisionPath(2, "known_unique", (2,), article="5")
        with self.assertRaisesRegex(_UnsupportedSemantics, "competing_syntax_alternatives"):
            self.semantic._select_refined_alternative([reading(more), reading(less)])

        more = ProvisionPath(1, "known_unique", (1,), article="5", point="2")
        less = ProvisionPath(2, "known_unique", (2,), article="5")
        with self.assertRaisesRegex(_UnsupportedSemantics, "competing_syntax_alternatives"):
            self.semantic._select_refined_alternative([reading(more), reading(less)])

        unspecified = ProvisionPath(None, "unspecified", (), article="5")
        known = ProvisionPath(1, "known_unique", (1,), article="5")
        self.assertEqual(self.semantic._select_refined_alternative(
            [reading(unspecified), reading(known)]), (reading(known)[0],))

    def test_semantic_range_conversion_rejects_non_ascii_numeric_values(self):
        selector = AstNode("selector", children=(AstNode("item", children=(
            AstLeaf("ID", "١", 0, 1), AstLeaf("RANGE", "–", 1, 2),
            AstLeaf("ID", "٢", 2, 3))),))
        with self.assertRaisesRegex(_UnsupportedSemantics, "unsupported_range_endpoints"):
            self.semantic._selector_values(selector)

    def test_semantic_rejects_bad_selector_shapes(self):
        leaf = AstLeaf("ID", "2", 0, 1)
        malformed_range = AstNode("selector", children=(AstNode("item", children=(
            AstLeaf("RANGE", "–", 0, 1), leaf)),))
        with self.assertRaisesRegex(_UnsupportedSemantics, "unsupported_range_endpoints"):
            self.semantic._selector_values(malformed_range)

        ordinal = AstNode("selector", children=(AstNode("item", children=(
            AstLeaf("ORDINAL", "второй", 0, 1),)),))
        with self.assertRaisesRegex(_UnsupportedSemantics, "non_scalar_or_ordinal_selector"):
            self.semantic._selector_values(ordinal)

    def test_parser_unknown_federal_law_forms_and_fuzzy_stops(self):
        for text in ("ст. 5 неизвестный ФЗ № 123-ФЗ",
                     "ст. 5 Федеральный закон № 123-ФЗ",
                     "ст. 5 Федеральный закон № 123"):
            self.parser.analyze(text)
        raw = self.parser._tokenize("Гражданского процессуального кодекса Российской Федерации\nстатья")
        self.parser._fuzzy_law_edges(raw, 0, "Гражданского процессуального кодекса Российской Федерации\nстатья")

    def test_parser_rejects_spaced_alias_continuation_and_short_fuzzy_surface(self):
        self.parser.analyze("статья 5 Гражданского   процессуального кодекса Российской Федерации")
        raw = self.parser._tokenize("ГК РФ")
        self.parser._fuzzy_law_edges(raw, 0, "ГК РФ")

    def test_parser_marker_and_alias_index_defensive_paths(self):
        with patch.object(self.parser._morphology, "parse", return_value=[
                type("Parse", (), {"normal_form": "different", "lexeme": ()})()]):
            self.parser._build_marker_index()
        self.parser._build_alias_index({"5": ["some test alias", "some test alias"]})
        self.parser._recognize_edges(self.parser._tokenize("статья 5"), "статья 5")
        self.parser._recognize_edges(self.parser._tokenize("ст 5"), "ст 5")
        for text in ("ст. 5 Федеральный закон № 12–15",
                     "ст. 5 Федеральный закон № 12–ФЗ"):
            self.parser.analyze(text)
        self.parser.analyze(
            "статья 5 Гражданского  процессуального кодекса Российской Федерации")

        longest_alias = max(alias.surface for aliases in self.parser._fuzzy_aliases.values()
                            for alias in aliases)
        too_long = longest_alias + " лишнее"
        raw = self.parser._tokenize(too_long)
        self.parser._fuzzy_law_edges(raw, 0, too_long)

        short_alias_parser = ReferenceAnalyzer({"1": ["примерного кодекса"]})
        spaced_text = "примерного, кодекса"
        spaced_raw = (_RawToken("примерного", 0, 10), _RawToken("кодекса", 12, 19))
        short_alias_parser._alias_trie = {
            frozenset({"примерного"}): {
                frozenset({"кодекса"}): {None: {1}},
            },
        }
        short_alias_parser._word_forms = lambda value: frozenset({value})
        short_alias_parser._recognize_edges(spaced_raw, spaced_text)

        self.parser._max_fuzzy_alias_chars = 2
        raw = self.parser._tokenize("alpha beta")
        self.parser._fuzzy_law_edges(raw, 0, "alpha beta")
        newline_text = "alpha\nbeta"
        raw = self.parser._tokenize(newline_text)
        self.parser._fuzzy_law_edges(raw, 0, newline_text)

    def test_parser_skips_duplicate_pending_lexical_paths(self):
        text = "ст 5"
        raw = self.parser._tokenize(text)
        marker = self.parser._tokenize("ст")[0]
        number = self.parser._tokenize("5")[0]
        marker_edge = _Edge(LexicalCandidate("ARTICLE", marker.value, marker.start,
                                            marker.end), 0, 1)
        number_edge = _Edge(LexicalCandidate("ID", number.value, number.start,
                                            number.end), 1, 2)
        self.parser._parse_candidates(raw, {0: [marker_edge], 1: [number_edge, number_edge]}, text)

