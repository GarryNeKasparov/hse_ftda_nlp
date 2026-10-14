"""Behavioral tests for the public reference-analysis interface."""

from pathlib import Path
import re
import unittest

from law_links.syntax.analyzer import ReferenceAnalyzer
from law_links.syntax.models import AstLeaf


ROOT = Path(__file__).resolve().parents[1]


class ReferenceAnalyzerTests(unittest.TestCase):
    """Check legal-reference extraction through its public interface."""

    @classmethod
    def setUpClass(cls):
        cls.analyzer = ReferenceAnalyzer.from_alias_file(ROOT / "data/law_aliases.json")

    def test_finds_reference_span_and_zero_valued_law_id(self):
        text = "См. статью 5 АПК."

        result = self.analyzer.analyze(text)

        matches = [candidate for candidate in result.candidates
                   if text[candidate.start:candidate.end] == "статью 5 АПК"]
        self.assertEqual(len(matches), 1)
        candidate = matches[0]
        self.assertTrue(candidate.complete)
        self.assertIn("0", law_ids(candidate))
        self.assertEqual(node_values(candidate, "ID"), ["5"])

    def test_reuses_parse_shape_but_binds_each_occurrence_to_its_source(self):
        analyzer = ReferenceAnalyzer({"15": ["НК РФ"], "0": ["АПК"]})
        text = "статью 5 НК РФ; статью 8 АПК"

        result = analyzer.analyze(text)

        first = find_candidate(result, text, "статью 5 НК РФ")
        second = find_candidate(result, text, "статью 8 АПК")
        self.assertEqual(node_values(first, "ID"), ["5"])
        self.assertEqual(law_ids(first), ["15"])
        self.assertEqual(node_values(second, "ID"), ["8"])
        self.assertEqual(law_ids(second), ["0"])
        self.assertGreater(analyzer.parse_cache_info["hits"], 0)

    def test_caches_unparseable_token_shapes(self):
        analyzer = ReferenceAnalyzer({})

        analyzer.analyze("статья 5 статья 6; статья 7 статья 8")

        self.assertGreater(analyzer.parse_cache_info["hits"], 0)
        self.assertGreater(analyzer.parse_cache_info["failures"], 0)
        self.assertLessEqual(analyzer.parse_cache_info["size"],
                             analyzer.parse_cache_info["maxsize"])

    def test_keeps_full_law_alias_when_sentence_comma_follows(self):
        text = "Согласно пункту 2 статьи 5 НК РФ, применяется правило."
        expected_span = "пункту 2 статьи 5 НК РФ"

        result = self.analyzer.analyze(text)

        matches = [candidate for candidate in result.candidates
                   if text[candidate.start:candidate.end] == expected_span]
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0].complete)
        law_names = [leaf.value for leaf in leaves(matches[0]) if leaf.kind == "LAW"]
        self.assertIn("НК РФ", law_names)

    def test_keeps_explicit_law_complete_before_prose_starting_with_in(self):
        for law, expected_id in (("АПК", "0"), ("НК РФ", "15")):
            with self.subTest(law=law):
                citation = f"ст. 5 {law}"
                text = f"Согласно {citation} в рассматриваемом деле действует правило."

                result = self.analyzer.analyze(text)
                candidate = find_candidate(result, text, citation)

                self.assertTrue(candidate.complete)
                self.assertEqual(law_ids(candidate), [expected_id])
                self.assertEqual(node_values(candidate, "ID"), ["5"])

    def test_interprets_pp_as_subpoint_under_point(self):
        text = "пп. 1 п. 1 ст. 374 НК РФ"

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, text)

        alternative_kinds = {node.kind for alternative in candidate.alternatives
                             for node in walk_nodes(alternative)}
        self.assertIn("subpoint_level", alternative_kinds)
        self.assertEqual(len(candidate.alternatives), 1)
        leaves_by_kind = [(leaf.kind, leaf.value) for leaf in leaves(candidate)]
        self.assertIn(("PP", "пп."), leaves_by_kind)
        self.assertIn(("POINT", "п."), leaves_by_kind)

    def test_keeps_quoted_lettered_subpoint_in_full_reference_span(self):
        for opening, closing in (("«", "»"), ('"', '"')):
            with self.subTest(quote=opening + closing):
                text = f"подпункт {opening}а{closing} пункта 2 статьи 10 НК РФ"

                result = self.analyzer.analyze(text)
                candidate = find_candidate(result, text, text)

                self.assertTrue(candidate.complete)
                self.assertEqual((candidate.start, candidate.end), (0, len(text)))
                self.assertEqual(node_values(candidate, "ID"), ["а", "2", "10"])

    def test_recognizes_quoted_subpoint_after_abbreviation_and_in_list(self):
        examples = (
            ("пп. «а» п. 1 ст. 5 НК РФ", ["а", "1", "5"]),
            ("подпункты «а», «б» пункта 1 статьи 5 НК РФ",
             ["а", "б", "1", "5"]),
        )
        for text, expected_ids in examples:
            with self.subTest(text=text):
                candidate = find_candidate(self.analyzer.analyze(text), text, text)

                self.assertTrue(candidate.complete)
                self.assertEqual(node_values(candidate, "ID"), expected_ids)

    def test_extracts_article_without_law_for_later_context_resolution(self):
        text = "согласно ст. 6"

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, "ст. 6")

        self.assertTrue(candidate.complete)
        self.assertEqual(node_values(candidate, "ID"), ["6"])
        self.assertFalse(any(leaf.kind == "LAW" for leaf in leaves(candidate)))
        self.assertEqual(law_ids(candidate), [])

    def test_retains_incomplete_prefix_and_extracts_reference_after_it(self):
        text = "статьи 5 и; затем ст. 6 НК РФ"

        result = self.analyzer.analyze(text)

        prefix = find_candidate(result, text, "статьи 5")
        later = find_candidate(result, text, "ст. 6 НК РФ")
        self.assertFalse(prefix.complete)
        self.assertEqual(prefix.diagnostics[0].code, "unfinished_continuation")
        self.assertTrue(later.complete)
        self.assertEqual(node_values(later, "ID"), ["6"])

    def test_keeps_unknown_federal_law_mention_without_an_id(self):
        text = "ст. 37 ФЗ №20-456"

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, text)

        law_mentions = [leaf for leaf in leaves(candidate) if leaf.kind == "LAW"]
        self.assertEqual(len(law_mentions), 1)
        self.assertEqual(law_mentions[0].value, "ФЗ №20-456")
        self.assertEqual(law_mentions[0].law_ids, ())
        self.assertEqual(law_mentions[0].law_status, "unknown")

    def test_keeps_all_ids_for_a_colliding_law_alias(self):
        text = "ст. 7 ФЗ №7-ФЗ"

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, text)

        ids = {law_id for leaf in leaves(candidate) if leaf.kind == "LAW"
               for law_id in leaf.law_ids}
        self.assertEqual(ids, {247, 401, 446, 471, 501, 533})

    def test_extracts_unknown_inflected_code_name(self):
        text = "ст. 6 рандомного кодекса"

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, text)

        law_mentions = [leaf for leaf in leaves(candidate) if leaf.kind == "LAW"]
        self.assertEqual([(leaf.value, leaf.law_status) for leaf in law_mentions],
                         [("рандомного кодекса", "unknown")])

    def test_preserves_atomic_hyphen_label_and_competing_range(self):
        text = "ст. 28-1"

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, text)
        token_paths = [{(leaf.kind, leaf.value) for leaf in walk(alternative)}
                       for alternative in candidate.alternatives]

        self.assertTrue(any(("ID", "28-1") in path for path in token_paths))
        self.assertTrue(any(("ID", "28") in path and ("RANGE", "-") in path
                            and ("ID", "1") in path for path in token_paths))

    def test_classifies_yo_e_instrumental_article_marker_for_inserted_id(self):
        text = "статьей 327-2 ГПК РФ"

        result = self.analyzer.analyze(text)

        article_marker = next(token for token in result.lexical_candidates
                              if token.start == 0 and token.kind == "ARTICLE")
        inserted_id = next(token for token in result.lexical_candidates
                            if token.kind == "ID" and token.value == "327-2")
        self.assertIn("exact_marker", article_marker.evidence)
        self.assertIn("atomic_hyphen_identifier", inserted_id.evidence)
        self.assertFalse(any(token.kind == "RANGE" for token in result.lexical_candidates))

    def test_matches_known_short_alias_tokens_split_by_dirty_separators(self):
        examples = (
            ("ст. 5 Н-К РФ", "Н-К РФ", (15,)),
            ("статья 5 А\tПК РФ", "А\tПК РФ", (0,)),
            ("ст. 5 ГП\nК РФ", "ГП\nК РФ", (6,)),
            (r"ст. 5 ГП\К РФ", r"ГП\К РФ", (6,)),
        )
        for text, law_spelling, expected_ids in examples:
            with self.subTest(text=text):
                result = self.analyzer.analyze(text)
                matches = [token for token in result.lexical_candidates
                           if token.kind == "LAW"
                           and text[token.start:token.end] == law_spelling]

                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].law_ids, expected_ids)

    def test_does_not_join_alias_fragments_across_letters_or_digits(self):
        for text in ("ст. 5 ГП2К РФ", "ст. 5 ГП-Х РФ",
                     "ст. 5 ГП, повреждено, К РФ"):
            with self.subTest(text=text):
                result = self.analyzer.analyze(text)
                law_ids = {law_id for token in result.lexical_candidates
                           if token.kind == "LAW" for law_id in token.law_ids}

                self.assertNotIn(6, law_ids)

    def test_offsets_refer_to_original_decomposed_unicode_text(self):
        text = "е\u0308 статья 5 АПК"

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, "статья 5 АПК")

        self.assertEqual(candidate.start, 3)
        self.assertEqual(text[candidate.start:candidate.end], "статья 5 АПК")

    def test_extracts_decomposed_unicode_marker_with_original_source_offsets(self):
        citation = "статье\u0308и\u0306 5 НК РФ"
        text = f"Согласно {citation}, применяется правило."

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, citation)

        self.assertTrue(candidate.complete)
        self.assertEqual((candidate.start, candidate.end),
                         (len("Согласно "), len("Согласно ") + len(citation)))
        self.assertEqual(node_values(candidate, "ID"), ["5"])
        self.assertEqual(law_ids(candidate), ["15"])

    def test_recognizes_self_and_anaphoric_targets_without_inventing_ids(self):
        self_target = "пункт 2 настоящей статьи настоящего закона"
        anaphoric_target = "статья 8 указанного закона"

        self_result = self.analyzer.analyze(self_target)
        anaphoric_result = self.analyzer.analyze(anaphoric_target)
        self_candidate = find_candidate(self_result, self_target, self_target)
        anaphoric_candidate = find_candidate(anaphoric_result, anaphoric_target,
                                            anaphoric_target)

        self_kinds = {leaf.kind for leaf in leaves(self_candidate)}
        anaphoric_kinds = {leaf.kind for leaf in leaves(anaphoric_candidate)}
        self.assertTrue({"SELF_ARTICLE", "SELF_LAW"}.issubset(self_kinds))
        self.assertIn("ANAPHORIC_LAW", anaphoric_kinds)

    def test_recognizes_an_unknown_quoted_title(self):
        text = 'ст. 4 «Совершенно неизвестный закон»'

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, text)

        law_mentions = [leaf for leaf in leaves(candidate) if leaf.kind == "LAW"]
        self.assertEqual(len(law_mentions), 1)
        self.assertEqual(law_mentions[0].value, '«Совершенно неизвестный закон»')
        self.assertEqual(law_mentions[0].law_status, "unknown")

    def test_keeps_repeated_reference_occurrences_in_text_order(self):
        text = "статья 5 НК РФ и статья 5 НК РФ"

        result = self.analyzer.analyze(text)
        spans = sorted((candidate.start, candidate.end) for candidate in result.candidates
                       if candidate.complete and text[candidate.start:candidate.end]
                       == "статья 5 НК РФ")

        self.assertEqual(len(spans), 2)
        self.assertLess(spans[0][0], spans[1][0])

    def test_classifies_conjunctions_once_and_preserves_compound_span(self):
        for text, spelling, kind in (
                ("статьи 5 и 6 НК РФ", "и", "AND"),
                ("статьи 5 или 6 НК РФ", "или", "OR"),
                ("статьи 5 и (или) 6 НК РФ", "и (или)", "AND_OR"),
                ("статьи 5 И( ИЛИ ) 6 НК РФ", "И( ИЛИ )", "AND_OR")):
            with self.subTest(text=text):
                result = self.analyzer.analyze(text)
                conjunctions = [token for token in result.lexical_candidates
                                if token.kind in {"AND", "OR", "AND_OR"}]
                expected = text.index(f" {spelling}") + 1
                self.assertEqual(len(conjunctions), 1)
                self.assertEqual(conjunctions[0].kind, kind)
                self.assertEqual((conjunctions[0].start, conjunctions[0].end),
                                 (expected, expected + len(spelling)))
                self.assertEqual(text[conjunctions[0].start:conjunctions[0].end], spelling)
                candidate = find_candidate(result, text, text)
                self.assertTrue(candidate.complete)
                self.assertEqual(len(candidate.alternatives), 1)
                self.assertFalse(candidate.diagnostics)

    def test_malformed_compound_does_not_become_a_valid_full_reference(self):
        for text in ("статьи 5 и (или 6 НК РФ", "статьи 5 и (либо) 6 НК РФ"):
            with self.subTest(text=text):
                result = self.analyzer.analyze(text)
                self.assertFalse(any(candidate.complete and text[candidate.start:candidate.end]
                                     == text for candidate in result.candidates))

    def test_matches_a_misspelled_full_law_name_with_bounded_fuzzy_fallback(self):
        analyzer = ReferenceAnalyzer({
            "42": ["Большой необычный закон Российской Федерации"],
        })
        text = "ст. 2 Большой необычный закоон Российской Федерации"

        result = analyzer.analyze(text)
        candidate = find_candidate(result, text, text)

        law_mentions = [leaf for leaf in leaves(candidate) if leaf.kind == "LAW"]
        self.assertEqual(len(law_mentions), 1)
        self.assertEqual(law_mentions[0].law_ids, (42,))
        self.assertEqual(law_mentions[0].law_status, "known_unique")

    def test_fuzzy_matches_a_misspelled_explicit_federal_law_title(self):
        text = 'ст. 5 Федерального закона "О персональных данныз"'

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, text)

        law_mentions = [leaf for leaf in leaves(candidate) if leaf.kind == "LAW"]
        self.assertEqual(len(law_mentions), 1)
        self.assertEqual(law_mentions[0].law_ids, (330,))
        self.assertEqual(law_mentions[0].law_status, "known_unique")

    def test_recognizes_typos_created_from_exact_full_law_aliases(self):
        examples = (
            ("ст. 5 Налогового кодекса Российской Федерации",
             "ст. 5 Налоговго кодекса Российской Федерации", 15),
            ('ст. 5 Федерального закона "О персональных данных"',
             'ст. 5 Федерального закона "О персональных данныз"', 330),
        )

        for exact_text, typo_text, expected_law_id in examples:
            with self.subTest(text=exact_text):
                exact_result = self.analyzer.analyze(exact_text)
                typo_result = self.analyzer.analyze(typo_text)

                self.assertTrue(any(
                    token.kind == "LAW"
                    and token.start == len("ст. 5 ")
                    and token.end == len(typo_text)
                    and token.law_ids == (expected_law_id,)
                    for token in typo_result.lexical_candidates
                ))
                self.assertTrue(any(
                    token.kind == "LAW" and token.end == len(exact_text)
                    and token.law_ids == (expected_law_id,)
                    for token in exact_result.lexical_candidates
                ))

    def test_recognizes_single_letter_deletions_across_full_law_names(self):
        known_citations = (
            ("ст. 5 ", "Налоговый кодекс Российской Федерации", "", 15),
            ("ст. 5 ", 'Федерального закона "О персональных данных', '"', 330),
        )
        checked = 0
        seen_typos = set()

        for prefix, alias, suffix, expected_law_id in known_citations:
            exact_text = prefix + alias + suffix
            exact_result = self.analyzer.analyze(exact_text)
            self.assertTrue(any(
                token.kind == "LAW" and token.start == len(prefix)
                and token.end == len(exact_text)
                and token.law_ids == (expected_law_id,)
                for token in exact_result.lexical_candidates
            ))

            for match in re.finditer(r"[А-Яа-яЁё]+", alias):
                word = match.group()
                if len(word) < 5:
                    continue
                for position in range(len(word)):
                    typo_alias = (alias[:match.start()] + word[:position]
                                  + word[position + 1:] + alias[match.end():])
                    typo_text = prefix + typo_alias + suffix
                    if typo_text in seen_typos:
                        continue
                    seen_typos.add(typo_text)
                    with self.subTest(text=typo_text):
                        result = self.analyzer.analyze(typo_text)
                        self.assertTrue(any(
                            token.kind == "LAW" and token.start == len(prefix)
                            and token.end == len(typo_text)
                            and token.law_ids == (expected_law_id,)
                            for token in result.lexical_candidates
                        ))
                    checked += 1

        self.assertGreaterEqual(checked, 30)

    def test_fuzzy_full_alias_can_extend_a_known_short_alias(self):
        text = "ст. 5 Налоговый кодекс Российскцй Федерации"

        result = self.analyzer.analyze(text)

        self.assertTrue(any(
            token.kind == "LAW" and token.start == len("ст. 5 ")
            and token.end == len(text) and token.law_ids == (15,)
            and "fuzzy_law_alias" in token.evidence
            for token in result.lexical_candidates
        ))

    def test_fuzzy_index_preserves_ambiguous_ids_and_reuses_form_lookups(self):
        alias = "Большой необычный закон Российской Федерации"
        analyzer = ReferenceAnalyzer({
            "42": [alias],
            "43": [alias],
            "99": ["Иной редкий федеральный норматив Федерации"],
        })
        text = ("ст. 2 Большой необычный закоон Российской Федерации; "
                "ст. 3 Большой необычный закоон Российской Федерации")

        result = analyzer.analyze(text)

        fuzzy_laws = [token for token in result.lexical_candidates
                      if token.kind == "LAW" and "fuzzy_law_alias" in token.evidence]
        self.assertEqual(len(fuzzy_laws), 2)
        self.assertTrue(all(token.law_ids == (42, 43) for token in fuzzy_laws))
        self.assertGreater(analyzer.fuzzy_cache_info["hits"], 0)
        self.assertLessEqual(analyzer.fuzzy_cache_info["size"],
                             analyzer.fuzzy_cache_info["maxsize"])
        alias_count = sum(map(len, analyzer._fuzzy_aliases.values()))
        self.assertLess(analyzer.fuzzy_cache_info["aliases_checked"],
                        alias_count * analyzer.fuzzy_cache_info["misses"])

    def test_fuzzy_index_preserves_the_two_edit_cumulative_boundary(self):
        analyzer = ReferenceAnalyzer({
            "42": ["Большой необычный закон Российской Федерации"],
        })
        accepted = "Большой необычный закоон Российской Федераци"
        rejected = "Большой необычнный закоон Российской Федераци"

        accepted_edges = analyzer._fuzzy_law_edges(analyzer._tokenize(accepted), 0, accepted)
        rejected_edges = analyzer._fuzzy_law_edges(analyzer._tokenize(rejected), 0, rejected)

        self.assertEqual([edge.token.law_ids for edge in accepted_edges], [(42,)])
        self.assertEqual(rejected_edges, ())

    def test_keeps_malformed_range_continuation_incomplete(self):
        text = "ст. 5 - неизвестно. Ст. 7 УК РФ"

        result = self.analyzer.analyze(text)
        prefix = find_candidate(result, text, "ст. 5")
        later = find_candidate(result, text, "Ст. 7 УК РФ")

        self.assertFalse(prefix.complete)
        self.assertEqual(prefix.diagnostics[0].code, "unfinished_continuation")
        self.assertTrue(later.complete)

    def test_malformed_ascii_range_is_diagnosed_as_incomplete(self):
        text = "частей 1- статьи 322"

        result = self.analyzer.analyze(text)
        prefixes = [candidate for candidate in result.candidates
                    if candidate.start == 0 and not candidate.complete]

        self.assertTrue(any(any(item.code == "unfinished_continuation"
                                for item in candidate.diagnostics)
                            for candidate in prefixes))

    def test_finds_the_five_structural_challenge_references_in_raw_text(self):
        references = (
            "статьи 5 и 6 НК РФ",
            "статья 5 НК РФ и пункт 2 статьи 6 ГК РФ",
            "пункты 2 и 3 части 1 статьи 15",
            "пункт 2 части 1 и часть 3 статьи 15",
            "абзацы второй и третий пункта 4 части 2 статьи 10",
        )

        for text in references:
            with self.subTest(text=text):
                result = self.analyzer.analyze(text)
                candidate = find_candidate(result, text, text)
                self.assertTrue(candidate.complete)
                self.assertTrue(candidate.alternatives)

    def test_recognizes_one_letter_marker_typo_but_not_identifier_typos(self):
        text = "пунта б статьи 20"

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, text)

        point_markers = [item for item in result.lexical_candidates
                         if item.start == 0 and item.end == len("пунта")]
        self.assertTrue(any(item.kind == "POINT" and "fuzzy_marker" in item.evidence
                            for item in point_markers))
        self.assertEqual(node_values(candidate, "ID"), ["б", "20"])

    def test_fuzzy_marker_index_matches_brute_force_edit_rule(self):
        from rapidfuzz.distance import Levenshtein

        forms = self.analyzer._fuzzy_marker_forms
        samples = set()
        for form, _ in forms:
            samples.add(form)
            samples.update(form[:index] + form[index + 1:]
                           for index in range(len(form)))
            samples.update(form[:index] + "я" + form[index + 1:]
                           for index in range(len(form)) if form[index] != "я")
            samples.add("я" + form)
            samples.add(form + "я")

        for word in samples:
            if len(word) < 4:
                continue
            expected = frozenset(
                kind for form, kind in forms
                if not (len(word) > len(form) and word.endswith(form))
                and Levenshtein.distance(word, form, score_cutoff=1) <= 1
            )
            with self.subTest(word=word):
                self.assertEqual(self.analyzer._fuzzy_marker_kinds(word), expected)

    def test_matches_a_controlled_latin_cyrillic_alias_variant(self):
        text = "статья 5 СК РФ"

        result = self.analyzer.analyze(text)
        candidate = find_candidate(result, text, text)

        self.assertIn("8", law_ids(candidate))


def law_ids(candidate):
    """Collect law ID values retained in an AST candidate."""
    return [str(law_id) for leaf in leaves(candidate) for law_id in leaf.law_ids]


def node_values(candidate, kind):
    """Collect lexical values of one kind from every parse alternative."""
    return [leaf.value for leaf in leaves(candidate) if leaf.kind == kind]


def leaves(candidate):
    """Yield terminal AST leaves from every complete candidate alternative."""
    for alternative in candidate.alternatives:
        yield from walk(alternative)


def walk(node):
    """Visit terminal values in a grammar-preserving AST alternative."""
    if isinstance(node, AstLeaf):
        yield node
        return
    if node.kind is not None:
        yield node
    for child in node.children:
        yield from walk(child)


def walk_nodes(node):
    """Yield internal nodes from one parsed AST alternative."""
    if isinstance(node, AstLeaf):
        return
    yield node
    for child in node.children:
        yield from walk_nodes(child)


def find_candidate(result, text, candidate_text):
    """Find one complete span whose original source matches the supplied text."""
    matches = [candidate for candidate in result.candidates
               if text[candidate.start:candidate.end] == candidate_text]
    if not matches:
        raise AssertionError(f"No candidate span found for {candidate_text!r}")
    return next((candidate for candidate in matches if candidate.complete), matches[0])


if __name__ == "__main__":
    unittest.main()
