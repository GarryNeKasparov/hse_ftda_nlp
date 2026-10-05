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


if __name__ == "__main__":
    unittest.main()
