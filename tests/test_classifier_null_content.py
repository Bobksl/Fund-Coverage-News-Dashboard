"""Synthetic P7-4 regressions: malformed content must not abort a cohort."""
import json
import unittest
from pathlib import Path

from tests.fixtures import article, temporary_directory
from tests.test_classifier import CONFIG, valid_output
from tools.classifier import RawOutputStore, StructuredClassifier


class InvalidContentTests(unittest.TestCase):
    def assert_contained_failure(self, raw):
        calls = []

        def provider(prompt, digest, attempt):
            calls.append((digest, attempt))
            if len(calls) <= 2:
                return {"raw": raw}
            return {"raw": valid_output(entity_matches=[{
                "entity_id": "neuberger", "economic_role": "manager",
                "involvement": "direct_involvement", "evidence_refs": ["a2"],
            }])}

        with temporary_directory() as workspace:
            engine = StructuredClassifier(provider, RawOutputStore(workspace / "raw"),
                                          "fixture-model", "p2", max_attempts=2)
            failed = engine.propose(article(), CONFIG)
            self.assertEqual(len(calls), 2)
            self.assertEqual([item[1] for item in calls], [1, 2])
            self.assertIn("classifier_failure", failed["flags"])
            self.assertEqual(failed["gates"]["identity"], "review_required")
            self.assertEqual(failed["gates"]["relevance"], "review_required")
            self.assertTrue(all(component["points"] is None
                                for component in failed["components"].values()))
            self.assertEqual(len(failed["attempts"]), 2)
            for attempt in failed["attempts"]:
                self.assertIn(attempt["outcome"], ("unparsable", "schema_invalid"))
                self.assertTrue(attempt["detail"])
                saved = json.loads(Path(attempt["raw_ref"]).read_text(encoding="utf-8"))
                self.assertEqual(saved["raw"], raw)
                self.assertEqual(saved["attempt"], attempt["attempt"])

            following = engine.propose(article(article_id="a2"), CONFIG)
            self.assertEqual(len(calls), 3)
            self.assertEqual(following["article_id"], "a2")
            self.assertEqual(following["attempts"][0]["outcome"], "valid")
            self.assertNotIn("classifier_failure", following["flags"])
            self.assertEqual(following["gates"]["relevance"], "pass")

    def test_null_content_is_preserved_and_contained(self):
        self.assert_contained_failure(None)

    def test_numeric_content_is_preserved_and_contained(self):
        self.assert_contained_failure(42)

    def test_empty_content_is_preserved_and_contained(self):
        self.assert_contained_failure("")

    def test_truncated_json_is_preserved_and_contained(self):
        self.assert_contained_failure('{"relevance_level": "A",')


if __name__ == "__main__":
    unittest.main()
