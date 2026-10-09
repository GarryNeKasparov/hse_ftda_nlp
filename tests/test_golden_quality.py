import unittest

from tools.evaluate_golden_quality import _extraction_sample_exact


class GoldenQualityTests(unittest.TestCase):
    def test_extraction_exact_match_requires_matching_boundaries(self):
        predicted = [{
            "start": 0, "end": 10, "text": "ст. 5 НК РФ",
            "links": [{"law_id": 15, "article": "5",
                       "point_article": None, "subpoint_article": None}],
        }]
        gold = [{
            "start": 0, "end": 9, "text": "ст. 5 НК",
            "links": [{"law_id": 15, "article": "5",
                       "point_article": None, "subpoint_article": None}],
        }]

        self.assertFalse(_extraction_sample_exact(predicted, gold))


if __name__ == "__main__":
    unittest.main()
