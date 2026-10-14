"""Keep the diverse runtime workload fixed while the parser is optimized."""

from pathlib import Path
import unittest

from tools.benchmark_diverse_workload import build_workload, TARGET_CHARS


ROOT = Path(__file__).resolve().parents[1]
FROZEN_WORKLOAD_SHA256 = "70b2b9237500c26b7528fc1d4f5beeeb9b554809364cacf568d899a5ef8cfdaf"


class DiverseWorkloadTests(unittest.TestCase):
    def test_full_workload_keeps_distinct_long_legal_texts(self):
        workload, generation = build_workload()

        self.assertEqual(generation["workload_sha256"], FROZEN_WORKLOAD_SHA256)
        self.assertEqual(generation["total_requests"], 2000)
        self.assertEqual(generation["unique_requests"], 2000)
        for track, texts in workload.items():
            with self.subTest(track=track):
                self.assertEqual(len(texts), 500)
                self.assertTrue(all(len(text) == TARGET_CHARS for text in texts))
                details = generation["details"][track]
                self.assertEqual(len(details["natural"]), 25)
                self.assertEqual(len(details["controlled"]), 475)
                for text, item in zip(texts, details["natural"]):
                    source = (ROOT / "data/sources" / item["source"]).read_text(
                        encoding="utf-8")
                    self.assertEqual(text, source[item["start"]:
                                                   item["start"] + TARGET_CHARS])
                counts = {item["citation_count"] for item in details["controlled"]}
                self.assertEqual(counts, {5, 15, 30})
                self.assertTrue(all(item["natural_characters"] > TARGET_CHARS // 2
                                    for item in details["controlled"]))


if __name__ == "__main__":
    unittest.main()
