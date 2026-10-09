"""End-to-end behavior tests for the MVP HTTP service contract."""

import unittest

from fastapi.testclient import TestClient

from main import app


class ServiceApiTests(unittest.TestCase):
    """Exercise legal-reference projection through POST /detect."""

    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def test_returns_all_levels_for_a_known_law(self):
        response = self.client.post("/detect", json={
            "text": "пп. 1 п. 1 ст. 374 НК РФ",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"links": [{
            "law_id": 15,
            "article": "374",
            "point_article": "1",
            "subpoint_article": "1",
        }]})

    def test_returns_quoted_lettered_subpoint_for_each_quote_style(self):
        for opening, closing in (("«", "»"), ('"', '"')):
            with self.subTest(quote=opening + closing):
                text = f"подпункт {opening}а{closing} пункта 2 статьи 10 НК РФ"

                response = self.client.post("/detect", json={"text": text})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"links": [{
                    "law_id": 15,
                    "article": "10",
                    "point_article": "2",
                    "subpoint_article": "а",
                }]})

    def test_returns_quoted_subpoint_after_abbreviated_marker(self):
        response = self.client.post("/detect", json={
            "text": "пп. «а» п. 1 ст. 5 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": 15, "article": "5", "point_article": "1",
            "subpoint_article": "а",
        }]})

    def test_expands_quoted_subpoint_list_with_its_parent_path(self):
        response = self.client.post("/detect", json={
            "text": "подпункты «а», «б» пункта 1 статьи 5 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": "1",
             "subpoint_article": "а"},
            {"law_id": 15, "article": "5", "point_article": "1",
             "subpoint_article": "б"},
        ]})

    def test_expands_quoted_subpoint_list_ending_in_conjunction(self):
        response = self.client.post("/detect", json={
            "text": "подпункты «а», «б» и «в» пункта 1 статьи 5 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": "1",
             "subpoint_article": letter}
            for letter in ("а", "б", "в")
        ]})

    def test_expands_numeric_list_with_comma_and_final_conjunction(self):
        response = self.client.post("/detect", json={
            "text": "статьи 5, 6 и 7 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": article, "point_article": None,
             "subpoint_article": None}
            for article in ("5", "6", "7")
        ]})

    def test_comma_between_point_and_article_nests_the_hierarchy(self):
        response = self.client.post("/detect", json={
            "text": "п. 1, ст. 5 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": 15, "article": "5", "point_article": "1",
            "subpoint_article": None,
        }]})

    def test_commas_can_bridge_multiple_reverse_hierarchy_levels(self):
        response = self.client.post("/detect", json={
            "text": "пп. а, п. 1, ст. 5 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": 15, "article": "5", "point_article": "1",
            "subpoint_article": "а",
        }]})

    def test_comma_followed_by_conjunction_expands_selector_list(self):
        response = self.client.post("/detect", json={
            "text": "статьи 5, и 6 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": None,
             "subpoint_article": None},
            {"law_id": 15, "article": "6", "point_article": None,
             "subpoint_article": None},
        ]})

    def test_unknown_law_article_does_not_override_known_law_anaphora(self):
        response = self.client.post("/detect", json={
            "text": ("ст. 5 ГК РФ. ст. 6 неизвестного кодекса. "
                     "п. 2 указанной статьи ГК РФ"),
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 5, "article": "5", "point_article": None,
             "subpoint_article": None},
            {"law_id": None, "article": "6", "point_article": None,
             "subpoint_article": None},
            {"law_id": 5, "article": "5", "point_article": "2",
             "subpoint_article": None},
        ]})

    def test_unknown_article_is_not_anaphoric_context_for_known_law(self):
        response = self.client.post("/detect", json={
            "text": "ст. 6 неизвестного кодекса. п. 2 указанной статьи НК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": None, "article": "6", "point_article": None,
             "subpoint_article": None},
            {"law_id": 15, "article": None, "point_article": "2",
             "subpoint_article": None},
        ]})

    def test_keeps_explicit_law_before_prose_instead_of_inheriting_context(self):
        citation = "Согласно ст. 5 АПК в рассматриваемом деле действует правило."
        for prefix in ("", "Ст. 8 НК РФ. "):
            with self.subTest(prefix=prefix):
                expected = []
                if prefix:
                    expected.append({
                        "law_id": 15, "article": "8", "point_article": None,
                        "subpoint_article": None,
                    })
                expected.append({
                    "law_id": 0, "article": "5", "point_article": None,
                    "subpoint_article": None,
                })

                response = self.client.post("/detect", json={"text": prefix + citation})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"links": expected})

    def test_recognizes_composed_and_decomposed_unicode_article_markers(self):
        for marker in ("статьёй", "статье\u0308и\u0306"):
            with self.subTest(marker=marker):
                response = self.client.post("/detect", json={
                    "text": f"Согласно {marker} 5 НК РФ, применяется правило.",
                })

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"links": [{
                    "law_id": 15, "article": "5", "point_article": None,
                    "subpoint_article": None,
                }]})

    def test_returns_unknown_law_with_null_id(self):
        response = self.client.post("/detect", json={"text": "ст. 37 ФЗ №20-456"})

        self.assertEqual(response.json(), {"links": [{
            "law_id": None,
            "article": "37",
            "point_article": None,
            "subpoint_article": None,
        }]})

    def test_returns_unspecified_law_with_null_id(self):
        response = self.client.post("/detect", json={"text": "согласно ст. 6"})

        self.assertEqual(response.json(), {"links": [{
            "law_id": None,
            "article": "6",
            "point_article": None,
            "subpoint_article": None,
        }]})

    def test_inherits_last_explicit_law_for_a_later_reference(self):
        response = self.client.post("/detect", json={
            "text": "Статья 5 НК РФ. Статья 6",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": None,
             "subpoint_article": None},
            {"law_id": 15, "article": "6", "point_article": None,
             "subpoint_article": None},
        ]})

    def test_resolves_anaphoric_article_and_law_from_previous_reference(self):
        response = self.client.post("/detect", json={
            "text": ("Пункт 2 статьи 5 НК РФ. "
                     "Пункт 3 указанной статьи указанного закона"),
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": "2",
             "subpoint_article": None},
            {"law_id": 15, "article": "5", "point_article": "3",
             "subpoint_article": None},
        ]})

    def test_uses_recent_article_as_fallback_for_present_article(self):
        response = self.client.post("/detect", json={
            "text": "Статья 5 НК РФ. Пункт 2 настоящей статьи",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": None,
             "subpoint_article": None},
            {"law_id": 15, "article": "5", "point_article": "2",
             "subpoint_article": None},
        ]})

    def test_keeps_present_article_unresolved_without_prior_context(self):
        response = self.client.post("/detect", json={
            "text": "Пункт 2 настоящей статьи",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": None, "article": None, "point_article": "2",
            "subpoint_article": None,
        }]})

    def test_anaphoric_article_uses_most_recent_compatible_law_context(self):
        response = self.client.post("/detect", json={
            "text": ("Статья 5 НК РФ. Статья 6 ГК РФ. "
                     "Пункт 3 указанной статьи НК РФ"),
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": None,
             "subpoint_article": None},
            {"law_id": 5, "article": "6", "point_article": None,
             "subpoint_article": None},
            {"law_id": 15, "article": "5", "point_article": "3",
             "subpoint_article": None},
        ]})

    def test_new_explicit_law_replaces_context_for_later_omitted_laws(self):
        response = self.client.post("/detect", json={
            "text": "Статья 5 НК РФ. Статья 6 ГК РФ. Статья 7",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": None,
             "subpoint_article": None},
            {"law_id": 5, "article": "6", "point_article": None,
             "subpoint_article": None},
            {"law_id": 5, "article": "7", "point_article": None,
             "subpoint_article": None},
        ]})

    def test_explicit_law_tails_keep_identity_and_full_source_spans(self):
        text = (
            'ст. 16 Закона "О защите прав потребителей". '
            'п. 2 ст. 14 Закона "О персональных данных". '
            'статье 17 Конституции Российской Федерации. Статья 5 ГК РФ. '
            'ст. 6 Федерального закона "О банках и банковской деятельности"'
        )
        response = self.client.post("/detect", json={"text": text})

        self.assertEqual(response.json(), {"links": [
            {"law_id": 984, "article": "16", "point_article": None,
             "subpoint_article": None},
            {"law_id": 330, "article": "14", "point_article": "2",
             "subpoint_article": None},
            {"law_id": None, "article": "17", "point_article": None,
             "subpoint_article": None},
            {"law_id": 5, "article": "5", "point_article": None,
             "subpoint_article": None},
            {"law_id": None, "article": "6", "point_article": None,
             "subpoint_article": None},
        ]})

        syntax = self.client_context.app.state.reference_analyzer.analyze(text)
        semantic = self.client_context.app.state.semantic_analyzer.analyze(syntax)
        excerpts = [text[item.start:item.end] for item in semantic.references]
        self.assertEqual(excerpts, [
            'ст. 16 Закона "О защите прав потребителей"',
            'п. 2 ст. 14 Закона "О персональных данных"',
            "статье 17 Конституции Российской Федерации",
            "Статья 5 ГК РФ",
            'ст. 6 Федерального закона "О банках и банковской деятельности"',
        ])

    def test_part_comma_article_citation_and_neighboring_reference(self):
        text = (
            "Дополнительно применяются общие правила часть 3, ст. 30.1 КоАП РФ "
            "(обжалование), при дальнейшем споре — нормы ст. 211 АПК РФ и далее."
        )
        response = self.client.post("/detect", json={"text": text})

        self.assertEqual(response.json(), {"links": [
            {"law_id": 17, "article": "30.1", "point_article": "3",
             "subpoint_article": None},
            {"law_id": 0, "article": "211", "point_article": None,
             "subpoint_article": None},
        ]})

        syntax = self.client_context.app.state.reference_analyzer.analyze(text)
        semantic = self.client_context.app.state.semantic_analyzer.analyze(syntax)
        citation = next(item for item in semantic.references
                        if text[item.start:item.end] == "часть 3, ст. 30.1 КоАП РФ")
        self.assertEqual(len(citation.provisions), 1)
        path = citation.provisions[0]
        self.assertEqual((path.part, path.article, path.law_id), ("3", "30.1", 17))

    def test_ordinary_part_and_article_prose_does_not_form_a_citation(self):
        text = (
            "В первой части доклада обсуждается новая статья; "
            "обозначение 30.1 указано отдельно."
        )

        self.assertEqual(self.client.post("/detect", json={"text": text}).json(),
                         {"links": []})

    def test_abbreviated_law_citations_keep_boundaries_in_running_text(self):
        text = (
            "Ведение учета регулируют ст. 105 УК РФ и ведения бухгалтерского учета. "
            "Далее применяются ст. 211 АПК РФ (см. пояснение). "
            "В соответствии со статьей 11 ТК РФ нормы этого Кодекса обязательны."
        )
        response = self.client.post("/detect", json={"text": text})

        self.assertEqual(response.json(), {"links": [
            {"law_id": 13, "article": "105", "point_article": None,
             "subpoint_article": None},
            {"law_id": 0, "article": "211", "point_article": None,
             "subpoint_article": None},
            {"law_id": 10, "article": "11", "point_article": None,
             "subpoint_article": None},
        ]})

        syntax = self.client_context.app.state.reference_analyzer.analyze(text)
        semantic = self.client_context.app.state.semantic_analyzer.analyze(syntax)
        self.assertEqual([text[item.start:item.end] for item in semantic.references], [
            "ст. 105 УК РФ",
            "ст. 211 АПК РФ",
            "статьей 11 ТК РФ",
        ])

    def test_preserves_point_without_inventing_an_article(self):
        response = self.client.post("/detect", json={"text": "п. 10 АПК"})

        self.assertEqual(response.json(), {"links": [{
            "law_id": 0,
            "article": None,
            "point_article": "10",
            "subpoint_article": None,
        }]})

    def test_returns_an_empty_list_when_no_reference_is_present(self):
        response = self.client.post("/detect", json={"text": "Обычный текст."})

        self.assertEqual(response.json(), {"links": []})

    def test_returns_multiple_simple_references_in_text_order(self):
        response = self.client.post("/detect", json={
            "text": "ст. 5 НК РФ. п. 10 АПК",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": None,
             "subpoint_article": None},
            {"law_id": 0, "article": None, "point_article": "10",
             "subpoint_article": None},
        ]})

    def test_does_not_emit_a_partial_provision_from_a_grouped_reference(self):
        response = self.client.post("/detect", json={"text": "статьи 5 и 6 НК РФ"})

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": None,
             "subpoint_article": None},
            {"law_id": 15, "article": "6", "point_article": None,
             "subpoint_article": None},
        ]})

    def test_shared_law_applies_to_coordinated_article_branches(self):
        response = self.client.post("/detect", json={
            "text": ("Согласно пункту 2 статьи 5 и пункту 3 статьи 6 НК РФ, "
                     "применяется правило."),
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": "2",
             "subpoint_article": None},
            {"law_id": 15, "article": "6", "point_article": "3",
             "subpoint_article": None},
        ]})

    def test_preserves_repeated_occurrences_as_separate_links(self):
        response = self.client.post("/detect", json={
            "text": "статья 5 НК РФ и статья 5 НК РФ",
        })

        expected = {"law_id": 15, "article": "5", "point_article": None,
                    "subpoint_article": None}
        self.assertEqual(response.json(), {"links": [expected, expected]})

    def test_prose_with_one_nested_citation_returns_one_link(self):
        response = self.client.post("/detect", json={
            "text": "Согласно пункту 2 статьи 5 НК РФ, применяется правило.",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": 15,
            "article": "5",
            "point_article": "2",
            "subpoint_article": None,
        }]})

    def test_comma_before_prose_conjunction_keeps_citation_complete(self):
        response = self.client.post("/detect", json={
            "text": "В тексте указана статья 5 НК РФ, и она применяется на практике.",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": 15,
            "article": "5",
            "point_article": None,
            "subpoint_article": None,
        }]})

    def test_incomplete_longer_citation_does_not_emit_its_prefix(self):
        response = self.client.post("/detect", json={"text": "статьи 5 и"})

        self.assertEqual(response.json(), {"links": []})

    def test_expands_ascii_range_for_plural_points(self):
        response = self.client.post("/detect", json={
            "text": "пункты 2-4 статьи 10 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "10", "point_article": point,
             "subpoint_article": None}
            for point in ("2", "3", "4")
        ]})

    def test_expands_an_explicit_integer_range_through_the_api(self):
        response = self.client.post("/detect", json={
            "text": "Согласно пунктам 2–4 статьи 10 НК РФ, действует правило.",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "10", "point_article": point,
             "subpoint_article": None}
            for point in ("2", "3", "4")
        ]})

    def test_preserves_singular_inserted_article_identifier(self):
        response = self.client.post("/detect", json={
            "text": "статья 6-1 ГПК РФ",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": 6,
            "article": "6-1",
            "point_article": None,
            "subpoint_article": None,
        }]})

    def test_keeps_abbreviated_hyphen_label_unresolved(self):
        response = self.client.post("/detect", json={
            "text": "ст. 28-1 ГПК РФ",
        })

        self.assertEqual(response.json(), {"links": []})

    def test_expands_parts_under_an_inserted_article_identifier(self):
        response = self.client.post("/detect", json={
            "text": "частями 1 и 2 статьи 327-2 ГПК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 6, "article": "327-2", "point_article": "1",
             "subpoint_article": None},
            {"law_id": 6, "article": "327-2", "point_article": "2",
             "subpoint_article": None},
        ]})

    def test_expands_ascii_range_in_explicit_plural_article_context(self):
        response = self.client.post("/detect", json={
            "text": "главу 6 и статьи 175-189 ГПК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 6, "article": str(article), "point_article": None,
             "subpoint_article": None}
            for article in range(175, 190)
        ]})

    def test_expands_ascii_range_before_a_list_item(self):
        response = self.client.post("/detect", json={
            "text": "частей 1-3 и 5 статьи 322 ГПК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 6, "article": "322", "point_article": part,
             "subpoint_article": None}
            for part in ("1", "2", "3", "5")
        ]})

    def test_does_not_apply_plural_range_context_across_prose(self):
        response = self.client.post("/detect", json={
            "text": "частей 1, перечисленных ранее, 5-7 статьи 322 ГПК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": None, "article": None, "point_article": "1",
             "subpoint_article": None},
            {"law_id": 6, "article": "322", "point_article": None,
             "subpoint_article": None},
        ]})

    def test_malformed_ascii_range_does_not_emit_its_first_selector(self):
        response = self.client.post("/detect", json={
            "text": "частей 1- статьи 322",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": None,
            "article": "322",
            "point_article": None,
            "subpoint_article": None,
        }]})

    def test_projects_point_when_part_is_also_present(self):
        response = self.client.post("/detect", json={
            "text": "пункт 2 части 1 статьи 15",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": None,
            "article": "15",
            "point_article": "2",
            "subpoint_article": None,
        }]})

    def test_projects_supported_levels_and_ignores_paragraph(self):
        response = self.client.post("/detect", json={
            "text": "абзац 2 подпункта 3 пункта 4 статьи 10 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": 15,
            "article": "10",
            "point_article": "4",
            "subpoint_article": "3",
        }]})

    def test_projects_ordinal_paragraph_under_article_and_part(self):
        response = self.client.post("/detect", json={
            "text": "абзаца первого части 1 статьи 284 ГПК РФ",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": 6,
            "article": "284",
            "point_article": "1",
            "subpoint_article": None,
        }]})

    def test_projects_each_ordinal_paragraph_without_collapsing_duplicates(self):
        response = self.client.post("/detect", json={
            "text": "абзацев первого и второго пункта 2 статьи 284 ГПК РФ",
        })

        expected = {"law_id": 6, "article": "284", "point_article": "2",
                    "subpoint_article": None}
        self.assertEqual(response.json(), {"links": [expected, expected]})

    def test_expands_ordinal_paragraph_range_and_list_without_deduplication(self):
        response = self.client.post("/detect", json={
            "text": "абзацев первого-третьего и пятого статьи 284 ГПК РФ",
        })

        expected = {"law_id": 6, "article": "284", "point_article": None,
                    "subpoint_article": None}
        self.assertEqual(response.json(), {"links": [expected] * 4})

    def test_ordinary_ordinal_prose_does_not_create_a_link(self):
        response = self.client.post("/detect", json={
            "text": "Это первый абзац обычного текста.",
        })

        self.assertEqual(response.json(), {"links": []})

    def test_uses_minimum_law_id_for_an_ambiguous_alias(self):
        response = self.client.post("/detect", json={
            "text": "статья 2 ФЗ №3-ФЗ",
        })

        self.assertEqual(response.json(), {"links": [{
            "law_id": 249,
            "article": "2",
            "point_article": None,
            "subpoint_article": None,
        }]})

    def test_recovers_after_an_unfinished_reference_without_emitting_it(self):
        response = self.client.post("/detect", json={
            "text": "статьи 5 и; затем ст. 6 НК РФ и ст. 7 ГК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "6", "point_article": None,
             "subpoint_article": None},
            {"law_id": 5, "article": "7", "point_article": None,
             "subpoint_article": None},
        ]})

    def test_expands_the_assignment_subpoint_list(self):
        response = self.client.post("/detect", json={
            "text": "пп. 1, 2, 3 п. 2 ст. 3 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "3", "point_article": "2",
             "subpoint_article": subpoint}
            for subpoint in ("1", "2", "3")
        ]})

    def test_expands_two_selector_lists_without_crossing_the_branch(self):
        response = self.client.post("/detect", json={
            "text": "пп. 1, 2 п. 3, 4 ст. 5 НК РФ",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "5", "point_article": point,
             "subpoint_article": subpoint}
            for subpoint in ("1", "2") for point in ("3", "4")
        ]})

    def test_does_not_treat_a_word_ending_in_a_marker_as_a_marker(self):
        text = ("Если унитарное предприятие или учреждение обратилось в суд с иском о "
                "признании права хозяйственного ведения, оперативного управления или "
                "об истребовании имущества из чужого незаконного владения, суду "
                "необходимо установить, находится ли спорное имущество в государственной "
                "или муниципальной собственности, и привлечь к участию в деле собственника "
                "унитарного предприятия или учреждения.")

        response = self.client.post("/detect", json={"text": text})

        self.assertEqual(response.json(), {"links": []})


if __name__ == "__main__":
    unittest.main()
