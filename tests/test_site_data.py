import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from tools import site_data

RULES = {
    "gps": {"otf": {"en": "OTF", "zh": "OTF"}, "kkr": {"en": "KKR", "zh": "KKR"}},
    "sectors": {"clo": {"en": "CLO", "zh": "CLO"}},
    "regions": {"US": {"en": "US", "zh": "美国"}},
}
TODAY = date(2026, 9, 13)


def card(url="https://example.com/a", day="2026-09-10", **overrides):
    value = {
        "id": site_data.card_id(url), "date": day, "published_at": f"{day}T09:00:00-04:00",
        "headline": {"en": "OTF closes notes", "zh": "OTF 完成票据发行"},
        "summary": {"en": "OTF closed a notes offering.", "zh": "OTF 完成了票据发行。"},
        "gps": ["otf"], "sectors": [], "region": "US",
        "source": {"publisher": "OTF", "url": url},
        "review_status": "reviewed", "origin": "analyst_labeled",
    }
    value.update(overrides)
    return value


class ValidateCardTest(unittest.TestCase):
    def test_accepts_contract_card(self):
        value = card()
        self.assertIs(site_data.validate_card(value, RULES), value)

    def test_rejects_invalid_fields(self):
        cases = {
            "unknown GP": {"gps": ["blackstone"]},
            "no tags": {"gps": [], "sectors": []},
            "missing zh": {"summary": {"en": "x", "zh": ""}},
            "bad region": {"region": "Mars"},
            "unsafe url": {"source": {"publisher": "x", "url": "javascript:alert(1)"}},
            "bad status": {"review_status": "approved"},
            "bad date": {"date": "20260910"},
        }
        for name, override in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                site_data.validate_card(card(**override), RULES)

    def test_card_id_ignores_fragment_case_and_trailing_slash(self):
        self.assertEqual(site_data.card_id("https://Example.com/a/#x"), site_data.card_id("https://example.com/a"))


class AddCardsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_merges_dedupes_and_indexes(self):
        first = site_data.add_cards([card()], RULES, self.data, today=TODAY)
        again = site_data.add_cards([card(), card("https://example.com/b", published_at="2026-09-10T12:00:00-04:00")],
                                    RULES, self.data, today=TODAY)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(again), 1)
        day = json.loads((self.data / "2026-09-10.json").read_text(encoding="utf-8"))
        self.assertEqual([item["source"]["url"] for item in day["items"]],
                         ["https://example.com/b", "https://example.com/a"])
        index = json.loads((self.data / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["dates"], ["2026-09-10"])
        self.assertEqual(index["counts"], {"2026-09-10": 2})
        self.assertEqual(index["labels"]["gps"]["otf"], {"en": "OTF", "zh": "OTF"})

    def test_rolling_window_skips_and_prunes_old_days(self):
        site_data.add_cards([card(day="2026-06-01")], RULES, self.data, today=date(2026, 6, 2))
        self.assertTrue((self.data / "2026-06-01.json").exists())
        added = site_data.add_cards([card("https://example.com/old", day="2026-05-01")], RULES, self.data, today=TODAY)
        self.assertEqual(added, [])
        self.assertFalse((self.data / "2026-06-01.json").exists())

    def test_invalid_card_writes_nothing(self):
        with self.assertRaises(ValueError):
            site_data.add_cards([card(), card("https://example.com/b", gps=["nope"])], RULES, self.data, today=TODAY)
        self.assertEqual(list(self.data.iterdir()), [])


class StatusTest(unittest.TestCase):
    def test_failed_refresh_keeps_last_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok_at = datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc)
            site_data.write_status(tmp, mode="scheduled", schedule={}, result="succeeded", new_items=3, now=ok_at)
            failed = site_data.write_status(tmp, mode="scheduled", schedule={}, result="failed", new_items=0,
                                            detail="timeout", now=datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc))
            self.assertEqual(failed["last_success_at"], ok_at.isoformat(timespec="seconds"))
            self.assertEqual(failed["last_refresh_result"], "failed")


if __name__ == "__main__":
    unittest.main()
