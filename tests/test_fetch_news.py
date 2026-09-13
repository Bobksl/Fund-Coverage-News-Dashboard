import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools import fetch_news, site_data

NOW = datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc)
RULES = site_data.load_rules()


def rss(*items, channel="Google News"):
    body = "".join(
        f"<item><title>{title}</title><link>{link}</link><pubDate>{date}</pubDate>"
        f"<description>{description}</description><source url=\"https://pub.example\">{publisher}</source></item>"
        for title, link, date, description, publisher in items)
    return f"<?xml version=\"1.0\"?><rss version=\"2.0\"><channel><title>{channel}</title>{body}</channel></rss>".encode()


KKR_FUND = ("KKR raises $2bn for asset-based finance fund - Private Debt Investor", "https://news.example/kkr",
            "Sun, 13 Sep 2026 03:00:00 GMT",
            "&lt;a href=&quot;https://news.example/kkr&quot;&gt;KKR raises $2bn for asset-based finance fund&lt;/a&gt;",
            "Private Debt Investor")
OLD_ITEM = ("Apollo closes credit fund at $5bn - Reuters", "https://news.example/old",
            "Mon, 01 Sep 2026 03:00:00 GMT", "", "Reuters")
PAGE_ITEM = ("Page Industries names new CEO - Mint", "https://news.example/page",
             "Sun, 13 Sep 2026 02:00:00 GMT", "", "Mint")
BRIEF = {"relevant": True, "reason": "Tracked manager ABF fundraising.", "headline_en": "KKR raises $2bn ABF fund",
         "summary_en": "KKR raised $2 billion for an asset-based finance fund.", "headline_zh": "KKR 募集20亿美元资产支持融资基金",
         "summary_zh": "KKR 为一只资产支持融资基金募集了20亿美元。", "gps": ["kkr"],
         "sectors": ["asset_based_finance"], "region": "US"}


class FakePost:
    def __init__(self, brief):
        self.brief = brief
        self.calls = 0

    def __call__(self, body):
        self.calls += 1
        return {"choices": [{"message": {"content": json.dumps(self.brief, ensure_ascii=False)}}], "usage": {}}


def google_only(payload):
    def fetch(url):
        if "news.google.com" not in url:
            raise OSError("feed offline")
        return payload
    return fetch


class ParseAndRuleTest(unittest.TestCase):
    def test_parse_google_news_item(self):
        [entry] = fetch_news.parse_feed(rss(KKR_FUND))
        self.assertEqual(entry["title"], "KKR raises $2bn for asset-based finance fund")
        self.assertEqual(entry["publisher"], "Private Debt Investor")
        self.assertEqual(entry["description"], "")
        self.assertEqual(entry["published"], datetime(2026, 9, 13, 3, 0, tzinfo=timezone.utc))
        self.assertEqual(fetch_news.to_item(dict(entry))["date"], "2026-09-13")

    def test_rule_match(self):
        cases = {
            "KKR raises $2bn for asset-based finance fund": (True, ["kkr"], ["asset_based_finance"]),
            "KKR completes buyout of a retailer for $1bn": (False, [], []),
            "Page Industries names new CEO": (False, [], []),
            "CLO managers price record deals as issuance hits $20bn": (True, [], ["clo"]),
            "Shoppers close stores early": (False, [], []),
            "Blue Owl wins private credit award": (False, ["blue_owl"], ["private_credit"]),
            "Private credit outlook remains positive": (False, [], ["private_credit"]),
        }
        for text, (keep, gps, sectors) in cases.items():
            with self.subTest(text):
                match = fetch_news.rule_match(text, RULES)
                self.assertEqual((match["keep"], match["gps"], match["sectors"]), (keep, gps, sectors))

    def test_select_merges_syndicated_headlines_but_not_different_managers(self):
        def entry(title, hour):
            return {"title": title, "url": f"https://news.example/{hour}", "publisher": "X",
                    "published": datetime(2026, 9, 13, hour, tzinfo=timezone.utc), "description": ""}
        entries = [
            entry("BlackRock private credit fund redemption requests ease in third quarter", 5),
            entry("BlackRock private credit fund redemptions fall in third quarter", 4),
            entry("KKR raises $2bn for private credit fund", 3),
            entry("Apollo raises $2bn for private credit fund", 2),
        ]
        candidates, unique = fetch_news.select(entries, RULES, set())
        self.assertEqual(unique, 3)
        self.assertEqual([item["title"] for item in candidates],
                         ["BlackRock private credit fund redemption requests ease in third quarter",
                          "KKR raises $2bn for private credit fund",
                          "Apollo raises $2bn for private credit fund"])


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def status(self):
        return json.loads((self.data / "status.json").read_text(encoding="utf-8"))

    def test_adds_unreviewed_card_once(self):
        fetch = google_only(rss(KKR_FUND, OLD_ITEM, PAGE_ITEM))
        post = FakePost(BRIEF)
        code, stats = fetch_news.run(RULES, self.data, fetch=fetch, post=post, now=NOW, pause=0)
        self.assertEqual(code, 0)
        self.assertEqual((stats["fresh"] > 0, stats["rule_passed"], stats["added"], post.calls), (True, 1, 1, 1))
        [card] = json.loads((self.data / "2026-09-13.json").read_text(encoding="utf-8"))["items"]
        self.assertEqual((card["review_status"], card["origin"]), ("unreviewed", "auto_fetch"))
        self.assertEqual(self.status()["last_refresh_result"], "succeeded")

        code, stats = fetch_news.run(RULES, self.data, fetch=fetch, post=post, now=NOW, pause=0)
        self.assertEqual((code, stats["added"], post.calls), (0, 0, 1))
        self.assertEqual(self.status()["last_refresh_result"], "no_new_items")

    def test_model_rejection_is_remembered(self):
        post = FakePost(dict(BRIEF, relevant=False))
        fetch = google_only(rss(KKR_FUND))
        fetch_news.run(RULES, self.data, fetch=fetch, post=post, now=NOW, pause=0)
        fetch_news.run(RULES, self.data, fetch=fetch, post=post, now=NOW, pause=0)
        self.assertEqual(post.calls, 1)
        self.assertFalse((self.data / "2026-09-13.json").exists())

    def test_all_feeds_failing_records_failure(self):
        def offline(url):
            raise OSError("offline")
        code, stats = fetch_news.run(RULES, self.data, fetch=offline, post=FakePost(BRIEF), now=NOW, pause=0)
        self.assertEqual(code, 1)
        self.assertEqual(stats["feeds_ok"], 0)
        self.assertEqual(self.status()["last_refresh_result"], "failed")

    def test_dry_run_writes_nothing_and_calls_no_model(self):
        post = FakePost(BRIEF)
        code, stats = fetch_news.run(RULES, self.data, fetch=google_only(rss(KKR_FUND)), post=post,
                                     now=NOW, dry_run=True, pause=0)
        self.assertEqual((code, post.calls, len(stats["candidates"])), (0, 0, 1))
        self.assertEqual(list(self.data.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
