"""Checks for deterministic whole-sample benchmark workload generation."""

import unittest

from tools.benchmark_length_matched import build_workload


class LengthMatchedWorkloadTests(unittest.TestCase):
    def test_builds_unique_exact_length_batches_from_whole_samples(self):
        tracks = {
            "readme_interpretation": ["Статья 5 НК РФ.", "Пункт 2 статьи 8 КоАП РФ."],
            "readme_extraction": ["ст. 3 ГК РФ", "часть 4 статьи 12 ТК РФ"],
            "real_interpretation": ["Статьи 9 и 10 закона."],
            "real_extraction": ["Согласно пункту 6 статьи 22 закона."],
        }

        first = build_workload(tracks, requests_per_track=5, target_chars=1024, seed=31)
        second = build_workload(tracks, requests_per_track=5, target_chars=1024, seed=31)

        self.assertEqual(first, second)
        for name, texts in first.items():
            self.assertEqual(len(texts), 5)
            self.assertEqual(len(set(texts)), 5)
            self.assertEqual({sample for sample in tracks[name]
                              if any(text.startswith(sample + "\n\n") for text in texts)},
                             set(tracks[name]))
            for text in texts:
                self.assertEqual(len(text), 1024)
                self.assertTrue(any(sample in text for sample in tracks[name]))


if __name__ == "__main__":
    unittest.main()
