import unittest

from tests.fixtures import temporary_directory
from tools import collection

SOURCES = [
    {"source_id": "blue_owl_news", "tier": "manager_newsroom", "publisher": "Blue Owl Capital",
     "entry_point": "https://www.blueowl.com/news", "verification": "readable",
     "scope_note": "Corporate news index, all strategies"},
    {"source_id": "aci_news", "tier": "independent_publication",
     "publisher": "Alternative Credit Investor",
     "entry_point": "https://alternativecreditinvestor.com/category/news/",
     "verification": "readable", "scope_note": "News section listing, all dated entries"},
]


def manifest(**overrides):
    values = {"window_start": "2026-08-12", "window_end": "2026-09-10",
              "holdout_cutoff": "2026-09-04", "sources": SOURCES,
              "recorded_at": "2026-09-11T00:00:00+00:00"}
    values.update(overrides)
    with temporary_directory() as workspace:
        policy = workspace / "policy.md"
        policy.write_text("policy text", encoding="utf-8")
        return collection.build_manifest(values["window_start"], values["window_end"],
                                         values["holdout_cutoff"], values["sources"], policy,
                                         values["recorded_at"])


def observation(**overrides):
    values = {"title": "Manager closes credit fund",
              "url": "https://www.blueowl.com/news/story-1?utm_source=newsletter&id=42",
              "published_at": "2026-08-20", "published_date_precision": "date"}
    values.update(overrides)
    return values


class CanonicalizationTests(unittest.TestCase):
    def test_only_known_tracking_parameters_are_stripped(self):
        canonical = collection.canonicalize(
            "https://example.com/a?utm_source=mail&id=42&gclid=x&page=2")
        self.assertEqual(canonical, "https://example.com/a?id=42&page=2")

    def test_substantive_identifiers_survive(self):
        url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001747777"
        self.assertEqual(collection.canonicalize(url), url)

    def test_article_id_is_stable_and_opaque(self):
        first = collection.article_id_for("https://example.com/a")
        self.assertEqual(first, collection.article_id_for("https://example.com/a"))
        self.assertNotIn("example", first)

    def test_the_same_article_behind_two_tracking_links_collapses_to_one_id(self):
        left = collection.to_evidence(observation(), SOURCES[0], "2026-09-11T09:00:00+00:00")
        right = collection.to_evidence(
            observation(url="https://www.blueowl.com/news/story-1?id=42&utm_campaign=x"),
            SOURCES[0], "2026-09-11T09:05:00+00:00")
        self.assertEqual(left["article_id"], right["article_id"])
        self.assertNotEqual(left["original_url"], right["original_url"])


class ManifestTests(unittest.TestCase):
    def test_a_valid_manifest_records_the_policy_hash(self):
        record = manifest()
        self.assertEqual(len(record["policy_sha256"]), 64)
        self.assertEqual(record["cohort"], "natural_feed")

    def test_cutoff_must_fall_inside_the_window(self):
        with self.assertRaises(ValueError):
            manifest(holdout_cutoff="2026-09-30")

    def test_an_empty_roster_is_refused(self):
        with self.assertRaises(ValueError):
            manifest(sources=[])

    def test_unknown_tier_is_refused(self):
        broken = [dict(SOURCES[0], tier="blog")]
        with self.assertRaises(ValueError):
            manifest(sources=broken)


class IntakeTests(unittest.TestCase):
    def test_an_observed_entry_satisfies_the_evidence_contract(self):
        record = collection.to_evidence(observation(), SOURCES[0], "2026-09-11T09:00:00+00:00")
        self.assertEqual(record["evidence_scope"], "metadata_only")
        self.assertIsNone(record["evidence_hash"])
        self.assertEqual(record["source_kind"], "issuer_release")
        self.assertEqual(record["discovery_method"], "manual_index_enumeration:blue_owl_news")

    def test_an_undated_entry_keeps_a_null_timestamp(self):
        record = collection.to_evidence(
            observation(published_at="unknown", published_date_precision="unknown"),
            SOURCES[0], "2026-09-11T09:00:00+00:00")
        self.assertIsNone(record["published_at"])

    def test_a_malformed_observation_is_refused_not_silently_recorded(self):
        with self.assertRaises(ValueError):
            collection.to_evidence(observation(published_at="20 August 2026"), SOURCES[0],
                                   "2026-09-11T09:00:00+00:00")

    def test_independent_publication_entries_are_not_issuer_releases(self):
        record = collection.to_evidence(
            observation(url="https://alternativecreditinvestor.com/2026/08/20/story/"),
            SOURCES[1], "2026-09-11T09:00:00+00:00")
        self.assertEqual(record["source_kind"], "independent_reporting")
        self.assertEqual(record["publisher"], "Alternative Credit Investor")

    def test_a_gated_article_is_recorded_with_its_access_status(self):
        record = collection.to_evidence(
            observation(access_status="unavailable", evidence_scope="metadata_only"),
            SOURCES[1], "2026-09-11T09:00:00+00:00")
        self.assertEqual(record["access_status"], "unavailable")


class PartitionTests(unittest.TestCase):
    def test_dates_split_at_the_frozen_cutoff(self):
        record = manifest()
        self.assertEqual(collection.partition_for("2026-08-20", record), "calibration")
        self.assertEqual(collection.partition_for("2026-09-04", record), "holdout")
        self.assertEqual(collection.partition_for("2026-09-07", record), "holdout")

    def test_entries_outside_the_window_belong_to_neither_partition(self):
        record = manifest()
        self.assertIsNone(collection.partition_for("2026-08-01", record))
        self.assertIsNone(collection.partition_for(None, record))


class GapTests(unittest.TestCase):
    def test_a_gap_is_recorded_as_a_fact_not_as_zero_news(self):
        gap = collection.gap_record("bayview_news", "no_index_published",
                                    "2026-09-11T09:00:00+00:00", "No newsroom in public navigation")
        self.assertIn("not evidence that the source published nothing", gap["note"])

    def test_unknown_gap_reasons_are_refused(self):
        with self.assertRaises(ValueError):
            collection.gap_record("x", "did_not_feel_like_it", "2026-09-11T09:00:00+00:00", "d")


class ReportTests(unittest.TestCase):
    def test_report_counts_sources_partitions_and_pending_gaps(self):
        record = manifest()
        records = [collection.to_evidence(observation(), SOURCES[0], "2026-09-11T09:00:00+00:00"),
                   collection.to_evidence(
                       observation(url="https://www.blueowl.com/news/story-2",
                                   published_at="2026-09-08"),
                       SOURCES[0], "2026-09-11T09:00:00+00:00")]
        gaps = [collection.gap_record("aci_news", "roster_pending", "2026-09-11T09:00:00+00:00",
                                      "not yet enumerated")]
        report = collection.intake_report(record, records, gaps)
        self.assertEqual(report["records"], 2)
        self.assertEqual(report["partition_counts"], {"calibration": 1, "holdout": 1})
        self.assertEqual(report["sources_gapped_or_pending"], ["aci_news"])
        self.assertEqual(report["sources_observed_zero_in_window"], [])
        self.assertEqual(report["duplicate_article_ids"], 0)

    def test_frozen_manifest_is_not_overwritten(self):
        with temporary_directory() as workspace:
            record = manifest()
            collection.write_collection(workspace / "nf", record, [], [])
            with self.assertRaises(FileExistsError):
                collection.write_collection(workspace / "nf", record, [], [])


if __name__ == "__main__":
    unittest.main()


class MergeTests(unittest.TestCase):
    def test_one_article_on_two_indexes_becomes_one_record_keeping_both_paths(self):
        first = collection.to_evidence(observation(), SOURCES[0], "2026-09-11T09:00:00+00:00")
        second_source = dict(SOURCES[0], source_id="blue_owl_ir")
        second = collection.to_evidence(observation(), second_source, "2026-09-11T10:00:00+00:00")
        merged = collection.merge_records([first, second])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["discovery_method"],
                         "manual_index_enumeration:blue_owl_ir+blue_owl_news")
        self.assertEqual(merged[0]["first_seen_at"], "2026-09-11T09:00:00+00:00")

    def test_a_merged_record_counts_for_both_sources_in_the_report(self):
        first = collection.to_evidence(observation(), SOURCES[0], "2026-09-11T09:00:00+00:00")
        second = collection.to_evidence(observation(), dict(SOURCES[0], source_id="blue_owl_ir"),
                                        "2026-09-11T10:00:00+00:00")
        report = collection.intake_report(manifest(), collection.merge_records([first, second]), [])
        self.assertEqual(report["records"], 1)
        self.assertEqual(report["records_by_source"], {"blue_owl_ir": 1, "blue_owl_news": 1})

    def test_accessible_evidence_supersedes_an_unavailable_sighting(self):
        gated = collection.to_evidence(observation(access_status="unavailable"), SOURCES[1],
                                       "2026-09-11T09:00:00+00:00")
        open_copy = collection.to_evidence(observation(), dict(SOURCES[1], source_id="other"),
                                           "2026-09-11T09:30:00+00:00")
        merged = collection.merge_records([gated, open_copy])
        self.assertEqual(merged[0]["access_status"], "accessible")

    def test_enumerable_titles_without_article_links_are_their_own_gap(self):
        gap = collection.gap_record("neuberger_newsroom", "article_links_unavailable",
                                    "2026-09-11T13:05:00+00:00",
                                    "Index lists titles and dates but exposes no per-article href")
        self.assertEqual(gap["reason"], "article_links_unavailable")
        self.assertIn("not evidence that the source published nothing", gap["note"])

    def test_an_enumerated_source_with_nothing_in_window_is_not_a_gap(self):
        record = manifest()
        records = [collection.to_evidence(observation(), SOURCES[0], "2026-09-11T09:00:00+00:00")]
        report = collection.intake_report(record, records, [])
        self.assertEqual(report["sources_observed_zero_in_window"], ["aci_news"])
        self.assertEqual(report["sources_gapped_or_pending"], [])


class PrecisionWindowTests(unittest.TestCase):
    def test_a_full_timestamp_is_windowed_by_its_calendar_date(self):
        record = manifest()
        self.assertTrue(collection.in_window("2026-09-10T16:49:58-04:00", record))
        self.assertEqual(collection.partition_for("2026-09-10T16:49:58-04:00", record), "holdout")
        self.assertEqual(collection.partition_for("2026-08-20T09:00:00-04:00", record), "calibration")

    def test_a_timestamp_outside_the_window_is_still_excluded(self):
        record = manifest()
        self.assertFalse(collection.in_window("2026-09-11T11:00:46-04:00", record))
        self.assertIsNone(collection.calendar_date("not a date"))


def issuer(**overrides):
    values = {"entity_id": "otf", "legal_name": "Blue Owl Technology Finance Corp.",
              "cik": "0001747777", "verification_basis": "SEC ticker file",
              "evidence": "ticker OTF", "scope_note": "Tracked vehicle"}
    values.update(overrides)
    return values


SCOPE = {"include": ["8-K", "10-Q"],
         "exclude": [{"form": "13F-HR", "reason": "holdings, not an event"}]}
QUERY = {"endpoint": "browse-edgar", "date_filter": "filing date in window"}


def roster(issuers=None, unresolved=None, scope=None):
    with temporary_directory() as workspace:
        policy = workspace / "policy.md"
        policy.write_text("policy", encoding="utf-8")
        return collection.build_sec_roster(
            issuers if issuers is not None else [issuer()],
            unresolved if unresolved is not None else [],
            scope or SCOPE, QUERY, manifest(), policy, "2026-09-12T00:00:00+00:00")


class CikTests(unittest.TestCase):
    def test_ciks_are_padded_to_ten_digits(self):
        self.assertEqual(collection.normalize_cik("1747777"), "0001747777")
        self.assertEqual(collection.normalize_cik("CIK#: 0001465109"), "0001465109")

    def test_a_name_is_not_a_cik(self):
        with self.assertRaises(ValueError):
            collection.normalize_cik("Pacific Alliance Group Ltd")


class SecRosterTests(unittest.TestCase):
    def test_a_valid_roster_records_the_policy_hash_and_window(self):
        record = roster()
        self.assertEqual(record["source_id"], "sec_edgar")
        self.assertEqual(record["window_start"], "2026-08-12")
        self.assertEqual(len(record["policy_sha256"]), 64)

    def test_every_issuer_needs_a_verification_basis(self):
        with self.assertRaises(ValueError):
            roster([issuer(verification_basis="")])

    def test_a_malformed_cik_is_refused(self):
        with self.assertRaises(ValueError):
            roster([issuer(cik="1747777")])

    def test_duplicate_ciks_are_refused(self):
        with self.assertRaises(ValueError):
            roster([issuer(), issuer(entity_id="duplicate")])

    def test_an_unresolved_entity_may_not_carry_a_cik(self):
        with self.assertRaises(ValueError):
            roster(unresolved=[{"entity_id": "pag", "detail": "historical name only",
                                "cik": "0001684210"}])

    def test_an_unresolved_entity_needs_a_detail(self):
        with self.assertRaises(ValueError):
            roster(unresolved=[{"entity_id": "pag"}])

    def test_an_excluded_form_needs_a_reason(self):
        with self.assertRaises(ValueError):
            roster(scope={"include": ["8-K"], "exclude": [{"form": "4"}]})

    def test_a_form_cannot_be_included_and_excluded(self):
        with self.assertRaises(ValueError):
            roster(scope={"include": ["8-K"],
                          "exclude": [{"form": "8-K", "reason": "contradiction"}]})

    def test_an_empty_include_scope_is_refused(self):
        with self.assertRaises(ValueError):
            roster(scope={"include": [], "exclude": []})
