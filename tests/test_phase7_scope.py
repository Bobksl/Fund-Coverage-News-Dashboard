"""P7-1: freeze-001's 188/56/30 scope as hashed stage manifests, plus the replay-only linked view.

Synthetic tests always run. RealFreezeScopeTests read the actual private freeze-001 ID lists and
are skipped when the git-ignored work/ data is absent (e.g. a fresh clone).
"""
import contextlib
import hashlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.fixtures import article, temporary_directory
from tests.test_phase7_accounting import CountingProvider
from tools import phase7_scope as scope
from tools import run_model_experiment as rme
from tools.corpus import verify_freeze
from tools.evidence_capture import digest
from tools.records import leakage_scan, loads, read_jsonl, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = ROOT / "work" / "phase2" / "freeze-001"
REGISTRY = ROOT / "work" / "phase2" / "challenge" / "challenge-registry.jsonl"
EVIDENCE_STORE = ROOT / "work" / "phase2" / "evidence-store"
SCOPE_DIR = ROOT / "work" / "phase2" / "phase7-scope"

QUARANTINED = "f6400cea-3e84-5bd7-b063-5a3aa338d076"
UNDATED = "e0f8d0fc-e619-5649-85cb-950a8c028ce9"
CAL, HOLD, CHAL = ["c2", "c1"], ["h1"], ["x1"]
FREEZE = {"frozen_at": "2026-09-12T10:13:04+00:00", "split_manifest_sha256": "s" * 64,
          "evidence_sha256": "e" * 64}
SECRET = "SECRET-SELECTION-REASON"


def synthetic_split(cal=CAL, hold=HOLD, chal=CHAL):
    return {"natural_feed": {"calibration": list(cal), "holdout": list(hold)},
            "challenge": {"article_ids": list(chal)}}


def synthetic_evidence(ids=(*CAL, *HOLD, *CHAL, QUARANTINED, UNDATED)):
    return [article(article_id=article_id, original_url=f"https://example.com/{article_id}",
                    canonical_url=f"https://example.com/{article_id}") for article_id in ids]


def synthetic_registry():
    def row(article_id, linked):
        return {"article_id": article_id, "linked_natural_feed_article_id": linked,
                "categories": ["secret_category"], "selection_reason": SECRET}
    return [row("c1", "c1"), row("h1", "h1"), row(QUARANTINED, QUARANTINED),
            row("x1", None), row(UNDATED, None)]


def build(split=None, registry=synthetic_registry, **kwargs):
    return scope.build_scope(split or synthetic_split(), synthetic_evidence(), FREEZE,
                             "2026-09-13T00:00:00+00:00",
                             registry_rows=registry() if registry else None, **kwargs)


class ScopeManifestTests(unittest.TestCase):
    def test_stage_manifests_are_exact_sorted_and_hashed(self):
        record, manifests = build()
        self.assertEqual(set(manifests), {"stage-a-calibration", "stage-bc-holdout",
                                          "stage-d-challenge", scope.DIAGNOSTIC_STEM})
        expected = {"stage-a-calibration": ("calibration", ["c1", "c2"]),
                    "stage-bc-holdout": ("holdout", ["h1"]),
                    "stage-d-challenge": ("challenge", ["x1"])}
        for stem, (partition, ids) in expected.items():
            manifest = manifests[stem]
            self.assertEqual(manifest["partition"], partition)
            self.assertEqual(manifest["article_ids"], ids)
            self.assertEqual(manifest["article_count"], len(ids))
            self.assertEqual(manifest["article_ids_sha256"], scope.article_ids_sha256(ids))
            scope.check_run_manifest(manifest, partition, replay=False)
        self.assertEqual(record["governing_counts"],
                         {"calibration": 2, "holdout": 1, "challenge": 1,
                          "unique_classifier_inputs": 4})
        self.assertEqual([row["article_id"] for row in record["excluded_articles"]],
                         sorted([QUARANTINED, UNDATED]))

    def test_partitions_must_be_pairwise_disjoint(self):
        for split in (synthetic_split(hold=["c1"]), synthetic_split(chal=["h1"]),
                      synthetic_split(chal=["c2"])):
            with self.assertRaisesRegex(ValueError, "overlap"):
                build(split, registry=None)

    def test_recorded_exclusions_cannot_enter_the_frozen_comparison(self):
        for excluded in (QUARANTINED, UNDATED):
            for split in (synthetic_split(cal=[*CAL, excluded]),
                          synthetic_split(hold=[*HOLD, excluded]),
                          synthetic_split(chal=[*CHAL, excluded])):
                with self.assertRaisesRegex(ValueError, "recorded exclusions"):
                    build(split, registry=None)

    def test_article_ids_hash_is_order_independent_and_changes_on_any_add_or_remove(self):
        base = scope.article_ids_sha256(["a", "b", "c"])
        self.assertEqual(base, scope.article_ids_sha256(["c", "a", "b"]))
        self.assertNotEqual(base, scope.article_ids_sha256(["a", "b"]))
        self.assertNotEqual(base, scope.article_ids_sha256(["a", "b", "c", "d"]))
        self.assertEqual(build()[1]["stage-a-calibration"]["article_ids_sha256"],
                         build()[1]["stage-a-calibration"]["article_ids_sha256"])

    def test_linked_diagnostic_holds_only_frozen_natural_ids_and_is_replay_only(self):
        record, manifests = build()
        diagnostic = manifests[scope.DIAGNOSTIC_STEM]
        self.assertTrue(diagnostic["replay_only"])
        self.assertEqual(diagnostic["article_ids"], ["c1", "h1"])
        self.assertLessEqual(set(diagnostic["article_ids"]), {*CAL, *HOLD})
        self.assertEqual(diagnostic["excluded_linked_article_ids"], [QUARANTINED])
        self.assertNotIn("partition", diagnostic)
        reconciliation = record["registry_reconciliation"]
        self.assertEqual((reconciliation["linked_natural_feed_probes"],
                          reconciliation["linked_in_frozen_natural_feed"],
                          reconciliation["independent_probes"],
                          reconciliation["independent_in_frozen_challenge"],
                          reconciliation["unique_inputs_if_all_registry_probes_were_run"]),
                         (3, 2, 2, 1, 6))

    def test_registry_id_outside_freeze_and_exclusions_is_refused(self):
        for extra in ({"article_id": "zz", "linked_natural_feed_article_id": "zz"},
                      {"article_id": "zz", "linked_natural_feed_article_id": None}):
            with self.assertRaisesRegex(ValueError, "outside freeze-001"):
                build(registry=lambda: [*synthetic_registry(), extra])

    def test_no_evaluator_only_field_or_registry_text_reaches_any_output(self):
        record, manifests = build()
        for payload in (record, *manifests.values()):
            self.assertEqual(leakage_scan(payload), [])
            serialized = json.dumps(payload)
            self.assertNotIn(SECRET, serialized)
            self.assertNotIn("secret_category", serialized)
            self.assertNotIn('"categories"', serialized)

    def test_body_files_must_match_their_frozen_evidence_hash(self):
        with temporary_directory() as workspace:
            evidence = synthetic_evidence()
            for record in evidence:
                (workspace / f"{record['article_id']}.txt").write_text(
                    f"body of {record['article_id']}", encoding="utf-8")
                record["evidence_local_ref"] = f"store/{record['article_id']}.txt"
                record["evidence_hash"] = digest(f"body of {record['article_id']}")
            result = scope.build_scope(synthetic_split(), evidence, FREEZE, "t",
                                       evidence_store=workspace)
            self.assertEqual(result[0]["bodies_verified"], 4)
            (workspace / "h1.txt").write_text("edited after freeze", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "h1: body no longer matches"):
                scope.build_scope(synthetic_split(), evidence, FREEZE, "t",
                                  evidence_store=workspace)

    def test_written_scope_refuses_to_overwrite_and_records_file_hashes(self):
        record, manifests = build()
        with temporary_directory() as workspace:
            written = scope.write_scope(workspace, record, manifests)
            for name, entry in written["manifests"].items():
                self.assertEqual(hashlib.sha256((workspace / name).read_bytes()).hexdigest(),
                                 entry["file_sha256"])
            with self.assertRaises(FileExistsError):
                scope.write_scope(workspace, record, manifests)


class RunEntryGuardTests(unittest.TestCase):
    def write_manifests(self, workspace):
        _, manifests = build()
        paths = {}
        for stem, payload in manifests.items():
            paths[stem] = workspace / f"{stem}.json"
            paths[stem].write_text(json.dumps(payload), encoding="utf-8")
        write_jsonl(workspace / "evidence.jsonl", synthetic_evidence())
        return manifests, paths

    def cli(self, workspace, run_id, partition, manifest_path, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            return rme.main([run_id, partition, str(manifest_path),
                             str(workspace / "evidence.jsonl"), str(workspace / run_id),
                             "--raw-store", str(workspace / "raw"), "--provider", "fixture",
                             "--model", "fixture-model", *extra])

    def test_live_cli_refuses_the_replay_only_manifest_before_any_provider_exists(self):
        with temporary_directory() as workspace, \
                patch.object(rme, "build_provider") as build_provider, \
                patch.object(rme, "run_experiment") as run_experiment:
            _, paths = self.write_manifests(workspace)
            with self.assertRaisesRegex(ValueError, "Replay-only"):
                self.cli(workspace, "diag", "linked", paths[scope.DIAGNOSTIC_STEM])
            build_provider.assert_not_called()
            run_experiment.assert_not_called()

    def test_tampered_mislabelled_or_excluded_stage_manifest_is_refused_before_any_run(self):
        _, manifests = build()
        stage_d = manifests["stage-d-challenge"]
        tampered = dict(stage_d, article_ids=[*stage_d["article_ids"], "x9"])
        rehashed_exclusion = dict(stage_d, article_ids=["x1", UNDATED],
                                  article_ids_sha256=scope.article_ids_sha256(["x1", UNDATED]))
        cases = ((tampered, "challenge", "no longer match"),
                 (stage_d, "holdout", "partition 'challenge'"),
                 (rehashed_exclusion, "challenge", "Recorded exclusions"))
        run_experiment = Mock()
        with temporary_directory() as workspace, patch.object(rme, "run_experiment",
                                                              run_experiment):
            write_jsonl(workspace / "evidence.jsonl", synthetic_evidence())
            for number, (manifest, partition, message) in enumerate(cases):
                path = workspace / f"case-{number}.json"
                path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    self.cli(workspace, f"case-{number}", partition, path)
        run_experiment.assert_not_called()

    def test_overlapping_linked_ids_replay_once_with_no_new_provider_call(self):
        provider = CountingProvider()
        with temporary_directory() as workspace, patch.object(rme, "build_provider",
                                                             return_value=provider):
            _, paths = self.write_manifests(workspace)
            self.cli(workspace, "stage-a", "calibration", paths["stage-a-calibration"])
            self.cli(workspace, "stage-bc", "holdout", paths["stage-bc-holdout"])
            self.assertEqual(sorted(call[0] for call in provider.calls), ["c1", "c2", "h1"])
            provider.calls.clear()

            self.cli(workspace, "diag", "linked", paths[scope.DIAGNOSTIC_STEM], "--replay")
            self.assertEqual(provider.calls, [])
            run_manifest = loads((workspace / "diag" / "run-manifest.json").read_text(
                encoding="utf-8"))
            self.assertEqual(run_manifest["mode"], "replay")
            self.assertEqual(run_manifest["replayed_articles"], 2)
            self.assertEqual(run_manifest["incremental_usage_totals"],
                             {"input_tokens": 0, "output_tokens": 0})
            rows = read_jsonl(workspace / "diag" / "article-attempts.jsonl")
            self.assertEqual(sorted(row["article_id"] for row in rows), ["c1", "h1"])


@unittest.skipUnless((FREEZE_DIR / "split-manifest.json").exists(),
                     "private freeze-001 data not present")
class RealFreezeScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freeze = loads((FREEZE_DIR / "freeze-record.json").read_text(encoding="utf-8"))
        verify_freeze(cls.freeze, FREEZE_DIR / "evidence.jsonl",
                      split_manifest_path=FREEZE_DIR / "split-manifest.json")
        cls.split = loads((FREEZE_DIR / "split-manifest.json").read_text(encoding="utf-8"))
        cls.evidence = read_jsonl(FREEZE_DIR / "evidence.jsonl")

    def real_registry(self):
        if not REGISTRY.exists():
            self.skipTest("private challenge registry not present")
        return [{"article_id": row["article_id"],
                 "linked_natural_feed_article_id": row.get("linked_natural_feed_article_id")}
                for row in read_jsonl(REGISTRY)]

    def test_freeze_001_governs_disjoint_188_56_30_with_no_recorded_exclusion(self):
        calibration = set(self.split["natural_feed"]["calibration"])
        holdout = set(self.split["natural_feed"]["holdout"])
        challenge = set(self.split["challenge"]["article_ids"])
        self.assertEqual((len(calibration), len(holdout), len(challenge)), (188, 56, 30))
        self.assertEqual((len(self.split["natural_feed"]["calibration"]),
                          len(self.split["natural_feed"]["holdout"]),
                          len(self.split["challenge"]["article_ids"])), (188, 56, 30))
        self.assertFalse(calibration & holdout)
        self.assertFalse(calibration & challenge)
        self.assertFalse(holdout & challenge)
        self.assertEqual(len(calibration | holdout | challenge), 274)
        self.assertFalse((calibration | holdout | challenge) & scope.EXCLUDED_ARTICLES.keys())

    def test_real_scope_reconciles_the_91_registry_to_59_linked_and_30_challenge(self):
        record, manifests = scope.build_scope(self.split, self.evidence, self.freeze, "t",
                                              registry_rows=self.real_registry())
        self.assertEqual(record["governing_counts"],
                         dict(scope.FREEZE_001_COUNTS, unique_classifier_inputs=274))
        reconciliation = record["registry_reconciliation"]
        self.assertEqual(reconciliation["registry_rows"], 91)
        self.assertEqual((reconciliation["linked_natural_feed_probes"],
                          reconciliation["linked_in_frozen_natural_feed"],
                          reconciliation["linked_excluded"]), (60, 59, [QUARANTINED]))
        self.assertEqual((reconciliation["independent_probes"],
                          reconciliation["independent_in_frozen_challenge"],
                          reconciliation["independent_excluded"]), (31, 30, [UNDATED]))
        self.assertEqual(reconciliation["unique_inputs_if_all_registry_probes_were_run"], 276)
        diagnostic = manifests[scope.DIAGNOSTIC_STEM]
        self.assertEqual(diagnostic["article_count"], 59)
        self.assertLessEqual(set(diagnostic["article_ids"]),
                             set(manifests["stage-a-calibration"]["article_ids"])
                             | set(manifests["stage-bc-holdout"]["article_ids"]))

    @unittest.skipUnless((SCOPE_DIR / "scope-record.json").exists(),
                         "frozen Phase 7 scope artifacts not written")
    def test_written_scope_artifacts_match_a_fresh_rebuild_of_freeze_001(self):
        written = loads((SCOPE_DIR / "scope-record.json").read_text(encoding="utf-8"))
        store = EVIDENCE_STORE if EVIDENCE_STORE.exists() else None
        record, manifests = scope.build_scope(self.split, self.evidence, self.freeze,
                                              written["generated_at"],
                                              registry_rows=self.real_registry(),
                                              evidence_store=store)
        self.assertEqual(written["governing_counts"], record["governing_counts"])
        self.assertEqual(set(written["manifests"]), {f"{stem}.json" for stem in manifests})
        for stem, rebuilt in manifests.items():
            data = (SCOPE_DIR / f"{stem}.json").read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),
                             written["manifests"][f"{stem}.json"]["file_sha256"])
            self.assertEqual(loads(data.decode("utf-8")), rebuilt)
        if store:
            self.assertEqual(record["bodies_verified"], 273)


if __name__ == "__main__":
    unittest.main()
