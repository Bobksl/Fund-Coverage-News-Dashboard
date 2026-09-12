"""Claim construction is grounded and deterministic: no figure is invented, none is dropped."""
import unittest

from tests.fixtures import decision
from tools import claims
from tools.records import validate_article


class ExtractAmountClaimsTests(unittest.TestCase):
    def test_extracts_a_dollar_amount_with_scale_unit(self):
        body = "Example Manager closed the fund at $7.3 billion, above target."
        result = claims.extract_amount_claims("a1", body, "final close size", "2026-09-01")
        self.assertEqual(len(result), 1)
        claim = result[0]
        self.assertEqual(claim["amount"], 7.3)
        self.assertEqual(claim["currency"], "USD")
        self.assertEqual(claim["unit"], "billion")
        self.assertIn("$7.3 billion", claim["evidence_span"])
        self.assertEqual(claim["article_id"], "a1")
        self.assertEqual(claim["basis"], "final close size")
        self.assertEqual(claim["period"], "2026-09-01")

    def test_evidence_span_is_a_verbatim_substring_of_the_body(self):
        body = "Nationwide Life Insurance provided EUR 50.75 million in permanent financing."
        result = claims.extract_amount_claims("a1", body, "loan amount", "2026-08")
        self.assertEqual(len(result), 1)
        self.assertIn(result[0]["evidence_span"], body)

    def test_no_amount_in_body_yields_no_claims(self):
        result = claims.extract_amount_claims("a1", "A routine marketing note with no figures.",
                                              "basis", "2026-09")
        self.assertEqual(result, [])

    def test_multiple_amounts_get_distinct_sequential_claim_ids(self):
        body = "The vehicle raised $100 million in the first close and $250 million at final close."
        result = claims.extract_amount_claims("a1", body, "close size", "2026-09")
        self.assertEqual([c["claim_id"] for c in result], ["a1-amt1", "a1-amt2"])

    def test_every_extracted_claim_satisfies_the_article_claim_contract(self):
        body = "Example Manager secured GBP 12 million of financing."
        record = dict(
            article_id="a1", title="x", original_url="https://example.com/a1",
            canonical_url="https://example.com/a1", publisher="Example", originating_publisher=None,
            discovery_method="manual_curation", source_kind="issuer_release",
            published_at="2026-09-01T00:00:00+00:00", published_date_precision="datetime",
            event_date="2026-09-01", first_seen_at="2026-09-02T00:00:00+00:00",
            retrieved_at="2026-09-02T00:00:05+00:00", access_status="accessible",
            evidence_scope="full_text", evidence_hash="sha256:x", evidence_local_ref="x.txt",
            claims=claims.extract_amount_claims("a1", body, "loan amount", "2026-09"),
            supersedes_article_id=None)
        self.assertEqual(validate_article(record), [])


class ManualClaimTests(unittest.TestCase):
    def test_qualitative_claim_needs_no_numeric_fields(self):
        claim = claims.manual_claim("a1-c1", "a1", "The manager described the deal as oversubscribed.",
                                    "described the deal as oversubscribed")
        self.assertIsNone(claim["amount"])

    def test_numeric_claim_without_currency_unit_basis_or_period_is_refused(self):
        with self.assertRaises(ValueError):
            claims.manual_claim("a1-c1", "a1", "raised $5 million", "$5 million", amount=5.0)


class ClaimsForDecisionTests(unittest.TestCase):
    def test_builds_claims_only_for_articles_with_a_supplied_body(self):
        record = decision(article_ids=["a1", "a2"])
        bodies = {"a1": "Example Manager closed at $7.3 billion."}
        result = claims.claims_for_decision(record, bodies)
        self.assertEqual({c["article_id"] for c in result}, {"a1"})

    def test_no_bodies_yields_no_fabricated_claims(self):
        record = decision(article_ids=["a1"])
        self.assertEqual(claims.claims_for_decision(record, {}), [])


if __name__ == "__main__":
    unittest.main()
