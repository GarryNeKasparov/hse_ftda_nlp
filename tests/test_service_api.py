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

    def test_unsupported_range_does_not_emit_its_first_number(self):
        response = self.client.post("/detect", json={
            "text": "пункты 2-4 статьи 10 НК РФ",
        })

        self.assertEqual(response.json(), {"links": []})

    def test_expands_an_explicit_integer_range_through_the_api(self):
        response = self.client.post("/detect", json={
            "text": "Согласно пунктам 2–4 статьи 10 НК РФ, действует правило.",
        })

        self.assertEqual(response.json(), {"links": [
            {"law_id": 15, "article": "10", "point_article": point,
             "subpoint_article": None}
            for point in ("2", "3", "4")
        ]})

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
