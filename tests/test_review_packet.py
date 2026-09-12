import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.review_packet import build_packet


class PacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_root = Path(__file__).resolve().parents[1] / "work" / "test-tmp"
        cls.temp_root.mkdir(parents=True, exist_ok=True)

    def test_evaluator_metadata_never_reaches_packet(self):
        row = dict(article_id="5bf4c943-67d3-46db-b9fa-cba07516166a",
                   title="Example source title", url="https://example.com/article",
                   publisher="Example", published_date="2026-09-01")
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            root = Path(temp)
            row.update(score=99, recommendation="publish", level="A",
                       entity_roles=["lender"], challenge_category="namesake",
                       event_group="SECRET_GROUP", metadata={"gold": "SECRET"})
            build_packet([row], root / "packet")
            rendered = (root / "packet" / "articles.md").read_text(encoding="utf-8")
            payload = json.loads((root / "packet" / "articles.jsonl").read_text())
            self.assertEqual(hashlib.sha256((root / "packet" / "articles.jsonl").read_bytes()).hexdigest(),
                             (root / "packet" / "packet-sha256.txt").read_text().split()[0])
            self.assertEqual(set(payload), {"article_id", "title", "url", "publisher", "published_date"})
            self.assertNotIn("SECRET", rendered)
            self.assertNotIn("namesake", rendered)
            self.assertIn("https://example.com/article", rendered)
            with (root / "packet" / "analyst-labels.csv").open(encoding="utf-8-sig", newline="") as handle:
                labels = list(csv.DictReader(handle))
            self.assertEqual(len(labels), 1)
            self.assertTrue(all(value == "" for key, value in labels[0].items() if key != "article_id"))
            row.update(score=0, event_group="DIFFERENT_SECRET", recommendation="reject")
            build_packet([row], root / "other")
            self.assertEqual((root / "packet" / "articles.jsonl").read_bytes(),
                             (root / "other" / "articles.jsonl").read_bytes())
            with self.assertRaises(FileExistsError):
                build_packet([row], root / "packet")

    def test_duplicate_ids_and_unsafe_urls_rejected(self):
        row = dict(article_id="5bf4c943-67d3-46db-b9fa-cba07516166a",
                   title="Example", url="javascript:alert(1)",
                   publisher="Example", published_date="2026-09-01")
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temp:
            with self.assertRaises(ValueError):
                build_packet([row], Path(temp) / "bad")
            row["url"] = "https://example.com/article"
            with self.assertRaises(ValueError):
                build_packet([row, row], Path(temp) / "duplicate")


if __name__ == "__main__":
    unittest.main()
