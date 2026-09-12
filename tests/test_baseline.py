import unittest

from tools import baseline

CONFIG = baseline.load_config()
ENTITIES = CONFIG["entities"]["entities"]


def proposal(title, body=None, url="https://news.example.com/story", source_kind="independent_reporting",
             access_status="accessible", evidence_scope="full_text"):
    article_input = {"article_id": "a1", "title": title, "canonical_url": url, "publisher": "Example Wire",
                     "source_kind": source_kind, "access_status": access_status,
                     "evidence_scope": evidence_scope, "event_date": "2026-09-01"}
    return baseline.propose(article_input, CONFIG, body=body)


def status_of(matches, canonical_id):
    return next((m["status"] for m in matches if m["canonical_id"] == canonical_id), None)


class EntityResolutionTests(unittest.TestCase):
    def test_bare_conditional_name_stays_ambiguous(self):
        result = proposal("NB reports a strong quarter")
        self.assertEqual(result["direct_entity_ids"], [])
        self.assertIn("neuberger", result["flags"])
        self.assertEqual(result["gates"]["identity"], "review_required")

    def test_qualified_name_resolves(self):
        result = proposal("Neuberger Berman closes Private Debt V",
                          body="The direct lending fund held its final close.")
        self.assertIn("neuberger", result["direct_entity_ids"])
        self.assertEqual(result["gates"]["identity"], "pass")

    def test_bare_ticker_never_resolves_an_issuer(self):
        bare = proposal("OTF declares a dividend")
        self.assertEqual(bare["direct_entity_ids"], [])
        self.assertEqual(status_of(bare["entity_matches"], "otf"), "ambiguous")
        qualified = proposal("Shares of OTF rise", body="NYSE: OTF gained after the report.")
        self.assertIn("otf", qualified["direct_entity_ids"])

    def test_longest_vehicle_name_wins_and_parent_stays_propagated(self):
        result = proposal("Blue Owl Technology Finance Corp. reports fourth quarter results")
        self.assertEqual(result["direct_entity_ids"], ["otf"])
        self.assertIn("blue_owl", result["propagated_entity_ids"])
        self.assertEqual(status_of(result["entity_matches"], "blue_owl"), "suppressed_by_longer_name")

    def test_deceptive_host_suffix_does_not_corroborate(self):
        matches = baseline.match_entities("NB said little.", "https://nb.com.evil.example/story", ENTITIES)
        self.assertEqual(status_of(matches, "neuberger"), "ambiguous")

    def test_official_host_corroborates_a_bare_namesake(self):
        matches = baseline.match_entities("Bayview announced a transaction.",
                                          "https://bayview.com/news/1", ENTITIES)
        self.assertEqual(status_of(matches, "bayview"), "resolved")

    def test_excluded_context_suppresses_a_name_match(self):
        matches = baseline.match_entities("Blue Owl collected awards this year.",
                                          "https://news.example.com/x", ENTITIES)
        self.assertEqual(status_of(matches, "blue_owl"), "excluded")


class RuleTests(unittest.TestCase):
    def test_event_phrases_match_whole_tokens_only(self):
        result = proposal("Example Manager closes its flagship fund",
                          body="The manager closes the vehicle after commitments arrived.")
        self.assertEqual(result["primary_event_type"], "capital_formation")

    def test_stress_language_classifies_as_credit_stress(self):
        result = proposal("Borrower misses payment as covenant breach is reported")
        self.assertEqual(result["primary_event_type"], "credit_stress")

    def test_unconnected_article_is_preserved_not_dropped(self):
        result = proposal("Local bakery opens a second branch")
        self.assertIsNone(result["relevance_level"])
        self.assertEqual(result["gates"]["relevance"], "fail")
        self.assertEqual(result["components"]["portfolio_fit"]["points"], 0)
        self.assertEqual(result["article_id"], "a1")

    def test_routine_activity_scores_low_materiality(self):
        result = proposal("CIFC recognized as a best places to work honoree")
        self.assertEqual(result["components"]["materiality"]["points"], 5)

    def test_source_kind_drives_credibility_and_inaccessible_evidence_caps_it(self):
        filing = proposal("CIFC prices a CLO", source_kind="filing")
        self.assertEqual(filing["components"]["source_credibility"]["points"], 10)
        snippet = proposal("CIFC prices a CLO", source_kind="filing",
                           access_status="unavailable", evidence_scope="metadata_only")
        self.assertEqual(snippet["components"]["source_credibility"]["points"], 4)

    def test_generic_macro_keeps_a_low_transmission_anchor(self):
        result = proposal("Federal Reserve signals a rate cut")
        self.assertEqual(result["relevance_level"], "C")
        self.assertEqual(result["components"]["investment_transmission"]["points"], 5)

    def test_baseline_never_infers_a_region(self):
        result = proposal("CIFC prices a CLO")
        self.assertEqual(result["primary_region"], "Unknown")


if __name__ == "__main__":
    unittest.main()
