import csv
import unittest
from pathlib import Path
from uuid import UUID

from tests.fixtures import article, temporary_directory
from tools import corpus, evaluator
from tools.records import leakage_scan

IDS = [str(UUID(int=number)) for number in range(1, 7)]


def record(index, published="2026-09-01", precision="date", **overrides):
    return article(article_id=IDS[index], title=f"Example headline {index}",
                   original_url=f"https://news.example.com/{index}",
                   canonical_url=f"https://news.example.com/{index}",
                   published_at=published, published_date_precision=precision, **overrides)


def gold(article_id, group, decision="publish"):
    return {"article_id": article_id, "event_group_id": group, "decision": decision,
            "must_not_miss": "no"}


class RegistryTests(unittest.TestCase):
    def test_challenge_records_must_declare_a_category(self):
        with self.assertRaises(ValueError):
            corpus.register([record(0)], "challenge", "hand_selected")

    def test_natural_feed_records_carry_no_selection_rationale(self):
        with self.assertRaises(ValueError):
            corpus.register([record(0)], "natural_feed", "roster_v1",
                            selection_reason="looked interesting")

    def test_registry_rows_stay_evaluator_side(self):
        rows = corpus.register([record(0)], "challenge", "probe_v1", "namesake",
                               "OTF versus OTF II")
        self.assertEqual(rows[0]["cohort"], "challenge")
        self.assertEqual(rows[0]["challenge_category"], "namesake")


class PacketTests(unittest.TestCase):
    def test_packet_blinds_cohort_and_orders_by_opaque_id(self):
        records = [record(0), record(1), record(2)]
        with temporary_directory() as workspace:
            result = corpus.build_review_packet(records, workspace / "packet")
            self.assertEqual(result["articles"], 3)
            text = (workspace / "packet" / "articles.md").read_text(encoding="utf-8")
            for word in ("challenge", "natural_feed", "cohort"):
                self.assertNotIn(word, text)
            with (workspace / "packet" / "analyst-labels.csv").open(encoding="utf-8-sig",
                                                                   newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["article_id"] for row in rows], sorted(IDS[:3]))
            self.assertTrue(all(row["decision"] == "" for row in rows))

    def test_undated_record_is_reported_not_given_a_guessed_date(self):
        records = [record(0), record(1, published=None, precision="unknown")]
        with temporary_directory() as workspace:
            result = corpus.build_review_packet(records, workspace / "packet")
            self.assertEqual(result["articles"], 1)
            self.assertEqual(result["excluded"][0]["article_id"], IDS[1])


class SplitTests(unittest.TestCase):
    def test_later_days_go_to_holdout_and_earlier_days_to_calibration(self):
        records = [record(0, "2026-08-20"), record(1, "2026-09-05")]
        split = corpus.temporal_split(records, {}, "2026-09-01")
        self.assertEqual(split["calibration"], [IDS[0]])
        self.assertEqual(split["holdout"], [IDS[1]])

    def test_a_lineage_spanning_the_cutoff_is_quarantined_into_holdout(self):
        records = [record(0, "2026-08-20"), record(1, "2026-09-05")]
        split = corpus.temporal_split(records, {IDS[0]: "G1", IDS[1]: "G1"}, "2026-09-01")
        self.assertEqual(split["calibration"], [])
        self.assertEqual(split["holdout"], sorted(IDS[:2]))
        self.assertEqual(split["quarantined_lineages"][0]["event_group_id"], "G1")

    def test_undated_records_are_unassigned_and_disclosed(self):
        records = [record(0, "2026-08-20"), record(1, published="2026-09", precision="month")]
        split = corpus.temporal_split(records, {}, "2026-09-01")
        self.assertEqual(split["unassigned"], [IDS[1]])
        self.assertEqual(split["date_exceptions"][0]["precision"], "month")
        self.assertNotIn(IDS[1], split["holdout"])


class SufficiencyTests(unittest.TestCase):
    def test_undersized_positive_supply_is_inconclusive(self):
        rows = [gold(IDS[0], "G1"), gold(IDS[1], "G2", "reject")]
        result = corpus.sufficiency(IDS[:2], rows, "natural_feed", "holdout")
        self.assertEqual(result["publish_worthy_events"], 1)
        self.assertEqual(result["non_publish_worthy_events"], 1)
        self.assertFalse(result["sufficient"])
        self.assertEqual(result["disposition"], "inconclusive_insufficient_positive_events")

    def test_eligible_but_reserved_events_are_not_positives(self):
        rows = [gold(IDS[0], "G1", "reserve"), gold(IDS[1], "G2", "reserve")]
        result = corpus.sufficiency(IDS[:2], rows, "challenge", "holdout", min_positive_events=1)
        self.assertEqual(result["publish_worthy_events"], 0)
        self.assertFalse(result["sufficient"])

    def test_sufficient_supply_is_marked_evaluable(self):
        rows = [gold(IDS[0], "G1"), gold(IDS[1], "G2")]
        result = corpus.sufficiency(IDS[:2], rows, "natural_feed", "holdout", min_positive_events=2)
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["disposition"], "evaluable")


class ManifestTests(unittest.TestCase):
    def test_manifest_exports_ids_and_partition_only(self):
        manifest = corpus.runner_manifest("run-1", "natural_feed_holdout", [IDS[1], IDS[0], IDS[0]])
        self.assertEqual(sorted(manifest), ["article_ids", "partition", "run_id"])
        self.assertEqual(manifest["article_ids"], sorted(IDS[:2]))

    def test_freeze_record_hashes_every_frozen_input(self):
        with temporary_directory() as workspace:
            paths = {}
            for name in ("labels.csv", "evidence.jsonl", "split.json", "predictions.jsonl"):
                path = workspace / name
                path.write_bytes(name.encode("utf-8"))
                paths[name] = path
            freeze = corpus.freeze_record(paths["labels.csv"], paths["evidence.jsonl"],
                                          paths["split.json"], paths["predictions.jsonl"],
                                          "2026-09-11T00:00:00+00:00")
            self.assertEqual(len(freeze["labels_sha256"]), 64)
            self.assertNotEqual(freeze["labels_sha256"], freeze["evidence_sha256"])


class VerifyFreezeTests(unittest.TestCase):
    def test_matching_files_pass_the_preflight(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            labels_path = workspace / "labels.csv"
            evidence_path.write_bytes(b"evidence")
            labels_path.write_bytes(b"labels")
            freeze = corpus.freeze_record(labels_path, evidence_path, evidence_path, None,
                                          "2026-09-11T00:00:00+00:00")
            self.assertTrue(corpus.verify_freeze(freeze, evidence_path, labels_path))

    def test_a_silently_edited_evidence_file_fails_the_preflight(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            labels_path = workspace / "labels.csv"
            evidence_path.write_bytes(b"evidence")
            labels_path.write_bytes(b"labels")
            freeze = corpus.freeze_record(labels_path, evidence_path, evidence_path, None,
                                          "2026-09-11T00:00:00+00:00")
            evidence_path.write_bytes(b"evidence-mutated-after-freeze")
            with self.assertRaises(evaluator.FreezeError):
                corpus.verify_freeze(freeze, evidence_path, labels_path)

    def test_a_silently_edited_labels_file_fails_the_preflight(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            labels_path = workspace / "labels.csv"
            evidence_path.write_bytes(b"evidence")
            labels_path.write_bytes(b"labels")
            freeze = corpus.freeze_record(labels_path, evidence_path, evidence_path, None,
                                          "2026-09-11T00:00:00+00:00")
            labels_path.write_bytes(b"labels-mutated-after-freeze")
            with self.assertRaises(evaluator.FreezeError):
                corpus.verify_freeze(freeze, evidence_path, labels_path)

    def test_inference_manifest_carries_provenance_and_no_gold(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            evidence_path.write_bytes(b"evidence")
            freeze = corpus.freeze_record(evidence_path, evidence_path, evidence_path, None,
                                          "2026-09-11T00:00:00+00:00")
            manifest = corpus.inference_manifest(
                freeze, "run-live-1", "natural_feed_calibration", [IDS[0]],
                config_root=Path(__file__).resolve().parents[1] / "config",
                prompt_version="p1", model_id="fixture-model-1", evidence_path=evidence_path)
            self.assertTrue(manifest["inference_preflight"]["freeze_verified"])
            self.assertEqual(manifest["inference_preflight"]["model_id"], "fixture-model-1")
            self.assertIn("scoring.json", manifest["inference_preflight"]["config_hashes"])
            self.assertEqual(leakage_scan(manifest), [])


if __name__ == "__main__":
    unittest.main()
