import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools import build_site

LABEL_FIELDS = ["article_id", "decision", "event_group_id", "rationale"]


def evidence(article_id, title, published_at="2026-08-20T09:00:00-04:00", access="accessible", url=None):
    return {"article_id": article_id, "title": title, "publisher": "ACI",
            "canonical_url": url or f"https://example.com/{article_id}", "original_url": "None",
            "published_at": published_at, "event_date": "None", "access_status": access,
            "evidence_local_ref": f"store/{article_id}.txt"}


class HistoricalItemsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "store").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, records, labels, texts):
        evidence_path = self.root / "evidence.jsonl"
        evidence_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
        for article_id, text in texts.items():
            (self.root / "store" / f"{article_id}.txt").write_text(text, encoding="utf-8")
        labels_path = self.root / "labels.csv"
        with open(labels_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
            writer.writeheader()
            writer.writerows(labels)
        return build_site.historical_items(evidence_path, labels_path, self.root)

    def test_one_item_per_published_group_preferring_accessible_fuller_text(self):
        records = [
            evidence("a1", "Gated lede", access="partial"),
            evidence("a2", "Full story"),
            evidence("a3", "Short accessible"),
            evidence("b1", "Rejected story"),
            evidence("c1", "Earlier story", published_at="2026-08-13T08:00:00+00:00"),
        ]
        labels = [
            {"article_id": "a1", "decision": "publish", "event_group_id": "E1", "rationale": "gated"},
            {"article_id": "a2", "decision": "publish", "event_group_id": "E1", "rationale": "full"},
            {"article_id": "a3", "decision": "publish", "event_group_id": "E1", "rationale": "short"},
            {"article_id": "b1", "decision": "reject", "event_group_id": "E2", "rationale": "no"},
            {"article_id": "c1", "decision": "publish", "event_group_id": "E3", "rationale": "early"},
        ]
        texts = {"a1": "x" * 900, "a2": "y" * 600, "a3": "z" * 100, "b1": "w", "c1": "v" * 50}
        items, skipped = self.build(records, labels, texts)
        self.assertEqual(skipped, [])
        self.assertEqual([item["title"] for item in items], ["Earlier story", "Full story"])
        self.assertEqual(items[1]["context"], "full")
        self.assertEqual(items[1]["date"], "2026-08-20")
        self.assertEqual(items[1]["url"], "https://example.com/a2")

    def test_items_without_date_are_reported_not_published(self):
        records = [evidence("d1", "Undated", published_at="None")]
        labels = [{"article_id": "d1", "decision": "publish", "event_group_id": "E9", "rationale": "x"}]
        items, skipped = self.build(records, labels, {"d1": "text"})
        self.assertEqual(items, [])
        self.assertEqual(skipped, [{"group_id": "E9", "title": "Undated", "reason": "no date"}])


if __name__ == "__main__":
    unittest.main()
