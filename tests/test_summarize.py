import json
import tempfile
import unittest
from pathlib import Path

from tools import summarize

RULES = {
    "gps": {"otf": {"en": "OTF", "zh": "OTF", "scope": "BDC"}},
    "sectors": {"private_credit": {"en": "Private Credit", "zh": "私募信贷"}},
    "regions": {"US": {"en": "US", "zh": "美国"}},
}
ITEM = {"title": "OTF closes notes", "publisher": "OTF", "url": "https://example.com/otf",
        "date": "2026-09-04", "published_at": "2026-09-04T16:00:00-04:00",
        "text": "Blue Owl Technology Finance closed ��$150 million notes."}
GOOD = {"relevant": True, "reason": "Tracked BDC financing.", "headline_en": "OTF closes $150m notes",
        "summary_en": "OTF closed a $150 million private placement.", "headline_zh": "OTF 完成1.5亿美元票据发行",
        "summary_zh": "OTF 完成了1.5亿美元私募配售。", "gps": ["otf", "blackstone"],
        "sectors": ["private_credit"], "region": "US"}


def response(payload):
    content = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 100, "completion_tokens": 50}}


class FakePost:
    def __init__(self, *payloads):
        self.payloads = list(payloads)
        self.bodies = []

    def __call__(self, body):
        self.bodies.append(body)
        return response(self.payloads.pop(0))


class SummarizerTest(unittest.TestCase):
    def test_source_fingerprint_and_review_assessment_are_retained(self):
        brief = summarize.parse_brief(json.dumps(GOOD, ensure_ascii=False), RULES)
        card = summarize.make_card(ITEM, brief, 'unreviewed', 'auto_fetch')
        self.assertEqual(len(card['source_fingerprint']), 64)
        self.assertFalse(card['assessment']['assessable'])
        self.assertEqual(card['relevance_reason'], GOOD['reason'])

    def test_otic_is_not_tagged_otf_and_otf_propagates_parent(self):
        rules = dict(RULES, gps=dict(RULES['gps'], blue_owl={'en': 'Blue Owl'}))
        brief = summarize.parse_brief(json.dumps(GOOD, ensure_ascii=False), rules)
        item = dict(ITEM, title='Blue Owl Technology Income Corp. closes notes',
                    text='Blue Owl Technology Income Corp. closes $150 million notes.')
        card = summarize.make_card(item, brief, 'unreviewed', 'auto_fetch')
        self.assertNotIn('otf', card['gps'])
        self.assertIn('blue_owl', card['gps'])

    def test_valid_brief_drops_unknown_tags_and_counts_usage(self):
        post = FakePost(GOOD)
        summarizer = summarize.Summarizer(RULES, post=post)
        brief = summarizer(ITEM)
        self.assertEqual(brief["gps"], ["otf"])
        self.assertTrue(brief["relevant"])
        self.assertEqual(summarizer.usage, {"input_tokens": 100, "output_tokens": 50})
        self.assertEqual(post.bodies[0]["model"], summarize.MODEL_ID)

    def test_retries_invalid_output_once(self):
        post = FakePost("not json", GOOD)
        brief = summarize.Summarizer(RULES, post=post)(ITEM)
        self.assertEqual(brief["region"], "US")
        self.assertEqual(len(post.bodies), 2)

    def test_rejects_english_only_chinese_fields(self):
        with self.assertRaises(summarize.SummaryError):
            summarize.Summarizer(RULES, post=FakePost(dict(GOOD, summary_zh="OTF closed"), dict(GOOD, summary_zh="x")))(ITEM)

    def test_call_cap_stops_spending(self):
        summarizer = summarize.Summarizer(RULES, post=FakePost("bad", "bad"), max_calls=1)
        with self.assertRaisesRegex(summarize.SummaryError, "cap"):
            summarizer(ITEM)
        self.assertEqual(summarizer.calls, 1)

    def test_cache_avoids_repeat_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "briefs.json"
            summarize.Summarizer(RULES, post=FakePost(GOOD), cache_path=cache)(ITEM)
            post = FakePost()
            brief = summarize.Summarizer(RULES, post=post, cache_path=cache)(ITEM)
            self.assertEqual(post.bodies, [])
            self.assertEqual(brief["headline"]["en"], GOOD["headline_en"])

    def test_prompt_uses_cleaned_text_and_make_card_matches_contract(self):
        content = json.loads(summarize.build_messages(ITEM, RULES)[1]["content"])
        self.assertNotIn("�", content["article"]["text"])
        brief = summarize.parse_brief(json.dumps(GOOD, ensure_ascii=False), RULES)
        card = summarize.make_card(ITEM, brief, "unreviewed", "auto_fetch")
        self.assertEqual(card["source"], {"publisher": "OTF", "url": "https://example.com/otf"})
        self.assertEqual(len(card["id"]), 12)

    def test_load_api_key_reads_env_file_without_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("OTHER=1\nTEST_SUMMARIZE_KEY='abc'\n", encoding="utf-8")
            self.assertEqual(summarize.load_api_key("TEST_SUMMARIZE_KEY", env_file), "abc")
            with self.assertRaises(summarize.SummaryError):
                summarize.load_api_key("MISSING_SUMMARIZE_KEY", env_file)


if __name__ == "__main__":
    unittest.main()
