"""Ensure the service's selected candidates preserve full semantic output."""

import unittest

from fastapi.testclient import TestClient

from main import app
from tools.benchmark_diverse_workload import build_workload
from tools.benchmark_length_matched import load_gold_tracks


class ServiceSelectionEquivalenceTests(unittest.TestCase):
    def test_selected_analysis_matches_full_semantics(self):
        tracks = load_gold_tracks()
        diverse, _ = build_workload(requests_per_track=4)
        texts = [
            "пп. 1, 2 п. 1 ст. 374 НК РФ; статьи 5 и 6 ГПК РФ.",
            "часть 3, ст. 30.1 КоАП РФ, а также настоящей статьи.",
        ]
        texts.extend(text for samples in tracks.values() for text in samples)
        texts.extend(text for samples in diverse.values() for text in samples)

        with TestClient(app):
            syntax = app.state.reference_analyzer
            semantic = app.state.semantic_analyzer
            resolver = app.state.contextual_resolver
            for index, text in enumerate(texts):
                with self.subTest(index=index):
                    full = resolver.resolve(semantic.analyze(syntax.analyze(text)))
                    selected = resolver.resolve(
                        semantic.analyze(syntax.analyze_for_service(text)))
                    self.assertEqual(selected, full)


if __name__ == "__main__":
    unittest.main()
