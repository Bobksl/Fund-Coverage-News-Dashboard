"""Phase 8 manual update: operator intake, zero-spend queue build and candidate explanations.

Covers the first-delivery acceptance checks that do not need a browser: a manual trigger creates a
traceable pending candidate without approval, identical input creates nothing new and calls
nothing, a missing stored response waits instead of being classified, and a paid-call cap stop is
a distinct status that keeps completed work (docs/phase-8-plan.md).
"""
import json
import unittest

from tests.fixtures import article, decision, temporary_directory
from tests.test_classifier import valid_output
from tests.test_drafting import CLAIMS, card as drafted_card
from tools import (approval_ledger, baseline, classifier, drafting, grouping, manual_update,
                   publication)
from tools.inference_budget import BudgetStop
from tools.records import CREDENTIAL_KEY, leakage_scan, read_jsonl, validate_article

CONFIG = baseline.load_config()
AT = "2026-09-13T01:00:00+00:00"
LATER = "2026-09-13T09:00:00+00:00"
PROFILE = {"provider": "fixture", "model_id": "fixture-model-1", "prompt_version": "p1",
           "inference_settings": {}, "max_attempts": 2}
TEXT = ("Example Manager announced the final close of Example Credit Fund II, a direct lending "
        "vehicle, above its target size. ") * 8


def item(url="https://news.example.com/fund-close?utm_source=mail", text=TEXT, **overrides):
    record = {"url": url, "title": "Example Manager closes Example Credit Fund II",
              "published_at": "2026-09-12", "published_date_precision": "date",
              "source_kind": "independent_reporting", "text": text, "capture_mode": "full"}
    record.update(overrides)
    return record


def batch(*items):
    return {"source_id": "example_wire", "tier": "independent_publication",
            "publisher": "Example Wire", "items": list(items)}


class Provider:
    """Injected stand-in for a paid provider: valid output for the cited article, then a cap stop."""

    def __init__(self, allowed_calls=None):
        self.allowed_calls = allowed_calls
        self.calls = 0

    def __call__(self, prompt, digest, attempt):
        if self.allowed_calls is not None and self.calls >= self.allowed_calls:
            raise BudgetStop("Approved spending cap cannot cover the next request reservation")
        self.calls += 1
        article_id = prompt["evidence"]["article_id"]
        return valid_output(entity_matches=[{"entity_id": "neuberger", "economic_role": "manager",
                                             "involvement": "direct_involvement",
                                             "evidence_refs": [article_id]}])


def only_article_id(workspace):
    records, _ = manual_update.load_evidence(workspace)
    return records[0]["article_id"]


def seed_store(workspace, store_dir):
    """A prior run's stored responses for exactly these inputs, as a reuse source."""
    records, bodies = manual_update.load_evidence(workspace)
    store = classifier.RawOutputStore(store_dir)
    engine = classifier.StructuredClassifier(
        Provider(), store, PROFILE["model_id"], PROFILE["prompt_version"],
        max_attempts=PROFILE["max_attempts"], inference_settings=PROFILE["inference_settings"])
    for record in records:
        engine.propose(record, CONFIG, body=bodies.get(record["article_id"]))


class IntakeTests(unittest.TestCase):
    def test_new_evidence_is_hashed_stored_logged_and_reported_as_a_source_check(self):
        with temporary_directory() as workspace:
            site = workspace / "site"
            report = manual_update.intake(workspace / "ws", batch(item()), AT, site_dir=site)
            self.assertEqual(report["status"], "succeeded")
            self.assertEqual(len(report["new"]), 1)
            records, bodies = manual_update.load_evidence(workspace / "ws")
            self.assertEqual(validate_article(records[0]), [])
            self.assertEqual(records[0]["evidence_scope"], "full_text")
            self.assertEqual(records[0]["discovery_method"], "operator_supplied:example_wire")
            self.assertIn("final close", bodies[records[0]["article_id"]])
            self.assertEqual(len(read_jsonl(workspace / "ws" / "intake-attempts.jsonl")), 1)
            check = publication.read_status(site)["last_source_check"]
            self.assertEqual((check["status"], check["new_items"]), ("succeeded", 1))

    def test_identical_resubmission_creates_nothing_new(self):
        with temporary_directory() as workspace:
            manual_update.intake(workspace, batch(item()), AT)
            report = manual_update.intake(workspace, batch(item()), LATER)
            self.assertEqual((len(report["new"]), len(report["duplicate"])), (0, 1))
            records, _ = manual_update.load_evidence(workspace)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["first_seen_at"], AT)

    def test_changed_text_is_reported_as_changed_not_as_a_second_article(self):
        with temporary_directory() as workspace:
            manual_update.intake(workspace, batch(item()), AT)
            before = only_article_id(workspace)
            previous_hash = manual_update.load_evidence(workspace)[0][0]["evidence_hash"]
            report = manual_update.intake(workspace, batch(item(text=TEXT + " Corrected.")), LATER)
            self.assertEqual(len(report["changed"]), 1)
            self.assertEqual(report["changed"][0]["previous_evidence_hash"], previous_hash)
            records, _ = manual_update.load_evidence(workspace)
            self.assertEqual([r["article_id"] for r in records], [before])
            self.assertNotEqual(records[0]["evidence_hash"], previous_hash)

    def test_invalid_items_are_reported_while_valid_items_are_accepted(self):
        with temporary_directory() as workspace:
            broken = item()
            del broken["url"]
            report = manual_update.intake(workspace, batch(item(), broken), AT)
            self.assertEqual(report["status"], "succeeded")
            self.assertEqual(len(report["new"]), 1)
            self.assertEqual(report["invalid"][0]["index"], 1)

    def test_a_batch_without_any_valid_item_is_a_failed_check_and_writes_no_evidence(self):
        with temporary_directory() as workspace:
            site = workspace / "site"
            report = manual_update.intake(workspace / "ws", {"items": []}, AT, site_dir=site)
            self.assertEqual(report["status"], "failed")
            self.assertFalse((workspace / "ws" / "evidence.jsonl").exists())
            self.assertEqual(publication.read_status(site)["last_source_check"]["status"], "failed")

    def test_a_held_workspace_lock_refuses_a_concurrent_run(self):
        with temporary_directory() as workspace:
            (workspace / ".lock").write_text("held", encoding="utf-8")
            with self.assertRaises(manual_update.WorkspaceLocked):
                manual_update.intake(workspace, batch(item()), AT)
            self.assertFalse((workspace / "evidence.jsonl").exists())


class QueueTests(unittest.TestCase):
    def test_an_article_without_a_stored_response_waits_and_no_model_is_reachable(self):
        with temporary_directory() as workspace:
            manual_update.intake(workspace, batch(item()), AT)
            queue = manual_update.build_queue(workspace, CONFIG, PROFILE, LATER)
            self.assertEqual(queue["events"], [])
            self.assertEqual(queue["counts"]["awaiting_classification"], 1)
            self.assertEqual(queue["awaiting"][0]["article_id"], only_article_id(workspace))
            self.assertIn("no stored model response", queue["awaiting"][0]["reason"])
            self.assertEqual(json.loads((workspace / "queue.json").read_text(encoding="utf-8")), queue)

    def test_a_stored_response_is_reused_at_zero_spend_and_explained(self):
        with temporary_directory() as workspace:
            manual_update.intake(workspace / "ws", batch(item()), AT)
            reuse = workspace / "prior-run-raw-outputs"
            seed_store(workspace / "ws", reuse)
            reuse_files = sorted(p.name for p in reuse.iterdir())
            queue = manual_update.build_queue(workspace / "ws", CONFIG, PROFILE, LATER,
                                              reuse_stores=[reuse])
            self.assertEqual(sorted(p.name for p in reuse.iterdir()), reuse_files)
            self.assertEqual(queue["counts"]["awaiting_classification"], 0)
            event = queue["events"][0]
            self.assertEqual(event["bucket"], "shortlisted")
            self.assertEqual(event["edition_position"], "selected")
            self.assertEqual(event["publication_status"], "pending_review")
            self.assertEqual(event["sources"][0]["url"], "https://news.example.com/fund-close")
            self.assertEqual(event["article_dates"], ["2026-09-12"])
            self.assertEqual({c["name"] for c in event["components"]},
                             set(CONFIG["scoring"]["components"][i]["canonical_id"]
                                 for i in range(len(CONFIG["scoring"]["components"]))))
            self.assertTrue(event["score_band"])
            self.assertTrue(event["provenance"]["replayed_stored_response"])
            self.assertEqual(queue["reused_responses"][0]["source_store"], str(reuse))

    def test_rebuilding_identical_inputs_is_stable_and_reuses_the_run(self):
        with temporary_directory() as workspace:
            manual_update.intake(workspace / "ws", batch(item()), AT)
            seed_store(workspace / "ws", workspace / "reuse")
            first = manual_update.build_queue(workspace / "ws", CONFIG, PROFILE, AT,
                                              reuse_stores=[workspace / "reuse"])
            second = manual_update.build_queue(workspace / "ws", CONFIG, PROFILE, LATER,
                                               reuse_stores=[workspace / "reuse"])
            self.assertEqual(first["events"], second["events"])
            self.assertEqual(first["run_id"], second["run_id"])
            self.assertEqual(len(list((workspace / "ws" / "runs").iterdir())), 1)

    def test_ledger_history_is_labelled_but_never_treated_as_approval(self):
        with temporary_directory() as workspace:
            manual_update.intake(workspace / "ws", batch(item()), AT)
            seed_store(workspace / "ws", workspace / "reuse")
            event_id = grouping.cluster_id([only_article_id(workspace / "ws")])
            ledger = workspace / "ledger.csv"
            approval_ledger.append_review(ledger, event_id, 1, {"headline_en": "old"}, "AN01", AT,
                                          "approved")
            queue = manual_update.build_queue(workspace / "ws", CONFIG, PROFILE, LATER,
                                              reuse_stores=[workspace / "reuse"],
                                              ledgers={"phase6": ledger})
            event = queue["events"][0]
            self.assertEqual(event["ledger_decisions"],
                             [{"ledger": "phase6", "status": "approved", "revision": "1",
                               "reviewer_id": "AN01", "reviewed_at": AT}])
            self.assertEqual(event["publication_status"], "pending_review")

    def test_a_cap_stop_keeps_completed_classification_and_is_a_distinct_status(self):
        with temporary_directory() as workspace:
            site = workspace / "site"
            manual_update.intake(workspace / "ws", batch(
                item(), item(url="https://news.example.com/second-close",
                             title="Example Manager closes Example Credit Fund III")), AT)
            provider = Provider(allowed_calls=1)
            report = manual_update.classify_pending(workspace / "ws", CONFIG, PROFILE, provider,
                                                    LATER, site_dir=site)
            self.assertEqual(report["status"], "budget_stopped")
            self.assertEqual((len(report["classified"]), len(report["remaining"])), (1, 1))
            self.assertEqual(publication.read_status(site)["last_source_check"]["status"],
                             "budget_stopped")
            queue = manual_update.build_queue(workspace / "ws", CONFIG, PROFILE, LATER)
            self.assertEqual((len(queue["events"]), queue["counts"]["awaiting_classification"]),
                             (1, 1))

    def test_classification_never_repeats_a_call_for_an_already_stored_input(self):
        with temporary_directory() as workspace:
            manual_update.intake(workspace, batch(item()), AT)
            provider = Provider()
            manual_update.classify_pending(workspace, CONFIG, PROFILE, provider, AT)
            calls = provider.calls
            report = manual_update.classify_pending(workspace, CONFIG, PROFILE, provider, LATER)
            self.assertEqual(provider.calls, calls)
            self.assertEqual((report["status"], report["classified"]), ("succeeded", []))

    def test_operator_export_is_separate_from_any_published_site_and_carries_no_secrets(self):
        with temporary_directory() as workspace:
            manual_update.intake(workspace / "ws", batch(item()), AT)
            operator = workspace / "operator"
            manual_update.build_queue(workspace / "ws", CONFIG, PROFILE, LATER,
                                      operator_dir=operator)
            self.assertEqual(sorted(p.name for p in operator.iterdir()),
                             ["index.html", "queue.js", "queue.json"])
            payload = json.loads((operator / "queue.json").read_text(encoding="utf-8"))
            self.assertEqual(leakage_scan(payload), [])
            self.assertIsNone(CREDENTIAL_KEY.search((operator / "queue.json").read_text(encoding="utf-8")))


class ExplanationTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {"a1": article()}
        self.scoring = CONFIG["scoring"]

    def test_suppressed_candidate_names_the_failed_gate_reason_and_band(self):
        suppressed = decision(recommendation="suppress", total_score=48,
                              gates=dict(decision()["gates"], materiality="fail"),
                              disposition_reason_codes=["below_materiality"])
        entry = manual_update.explain_decision(suppressed, self.scoring, self.evidence)
        self.assertEqual(entry["bucket"], "suppressed")
        self.assertEqual(entry["failed_gates"], ["materiality"])
        self.assertEqual(entry["reasons"][0]["code"], "below_materiality")
        self.assertTrue(entry["reasons"][0]["explanation"])
        self.assertEqual(entry["score_band"], "48 is in 0–59 (suppress)")

    def test_review_candidate_names_the_gate_that_needs_a_person(self):
        review = decision(recommendation="review_required",
                          gates=dict(decision()["gates"], identity="review_required"),
                          disposition_reason_codes=["ambiguous_identity", "shortlisted"])
        entry = manual_update.explain_decision(review, self.scoring, self.evidence)
        self.assertEqual(entry["bucket"], "review")
        self.assertEqual(entry["review_gates"], ["identity"])
        # The runner keeps the band's "shortlisted" code beside the review verdict; its explanation
        # must not claim every gate passed when one is still waiting for a person.
        band_reason = next(r for r in entry["reasons"] if r["code"] == "shortlisted")
        self.assertNotIn("Every gate passed", band_reason["explanation"])
        self.assertIn("review", band_reason["explanation"])

    def test_shortlisted_candidate_carries_sources_dates_and_component_reasons(self):
        entry = manual_update.explain_decision(decision(), self.scoring, self.evidence,
                                               edition_position="selected")
        self.assertEqual(entry["bucket"], "shortlisted")
        self.assertEqual(entry["score_band"], "88 is in 80–100 (priority_shortlist)")
        self.assertEqual(entry["sources"][0]["publisher"], "Example Manager")
        self.assertEqual(entry["article_dates"], ["2026-09-01"])
        self.assertEqual(len(entry["components"]), 6)
        self.assertTrue(all(c["reason"] for c in entry["components"]))


DRAFT_PROFILE = {"model_id": "fixture-draft-1", "prompt_version": "d1", "inference_settings": {},
                 "max_attempts": 2}


class DraftProvider:
    """Stand-in for an earlier drafting run; a Phase 8 draft step never receives a provider."""

    def __call__(self, prompt, digest, attempt):
        return json.dumps(drafted_card())


def shortlisted_workspace(root):
    workspace = root / "ws"
    manual_update.intake(workspace, batch(item()), AT)
    seed_store(workspace, root / "reuse")
    queue = manual_update.build_queue(workspace, CONFIG, PROFILE, AT, reuse_stores=[root / "reuse"])
    return workspace, queue["events"][0]["event_id"]


def seed_draft_store(workspace, store_dir):
    """A prior drafting run's stored responses for exactly these inputs, as a reuse source."""
    queue, decisions = manual_update.load_decisions(workspace)
    evidence = {record["article_id"]: record for record in manual_update.load_evidence(workspace)[0]}
    store = classifier.RawOutputStore(store_dir)
    drafter = drafting.Drafter(DraftProvider(), store, DRAFT_PROFILE["model_id"],
                               DRAFT_PROFILE["prompt_version"], max_attempts=2, inference_settings={})
    for event in queue["events"]:
        drafter.draft(decisions[event["event_id"]], evidence, CLAIMS)


def stored_draft(workspace, event_id):
    return json.loads((workspace / "drafts" / f"{event_id}.json").read_text(encoding="utf-8"))


class DraftReviewPublishTests(unittest.TestCase):
    def draft(self, root):
        workspace, event_id = shortlisted_workspace(root)
        seed_draft_store(workspace, root / "drafts-reuse")
        report = manual_update.draft_shortlisted(workspace, CONFIG, DRAFT_PROFILE, LATER,
                                                 claims_by_event={event_id: CLAIMS},
                                                 reuse_stores=[root / "drafts-reuse"])
        return workspace, event_id, report

    def test_a_stored_draft_replays_at_zero_spend_and_waits_for_a_person(self):
        with temporary_directory() as root:
            workspace, event_id = shortlisted_workspace(root)
            seed_draft_store(workspace, root / "drafts-reuse")
            before = sorted(p.name for p in (root / "drafts-reuse").iterdir())
            report = manual_update.draft_shortlisted(workspace, CONFIG, DRAFT_PROFILE, LATER,
                                                     claims_by_event={event_id: CLAIMS},
                                                     reuse_stores=[root / "drafts-reuse"])
            self.assertEqual(sorted(p.name for p in (root / "drafts-reuse").iterdir()), before)
            self.assertEqual(report["awaiting_drafting"], [])
            drafted = report["drafted"][0]
            self.assertEqual((drafted["event_id"], drafted["status"]),
                             (event_id, "ready_for_analyst_review"))
            self.assertEqual(drafted["content_hash"],
                             approval_ledger.content_hash(stored_draft(workspace, event_id)["content"]))
            queue = manual_update.build_queue(workspace, CONFIG, PROFILE, LATER)
            self.assertEqual(queue["events"][0]["draft"],
                             {"status": "ready_for_analyst_review",
                              "content_hash": drafted["content_hash"], "approved_exact_in": []})

    def test_without_a_stored_draft_the_event_waits_and_nothing_is_drafted(self):
        with temporary_directory() as root:
            workspace, event_id = shortlisted_workspace(root)
            report = manual_update.draft_shortlisted(workspace, CONFIG, DRAFT_PROFILE, LATER,
                                                     claims_by_event={event_id: CLAIMS})
            self.assertEqual(report["drafted"], [])
            self.assertEqual(report["awaiting_drafting"][0]["event_id"], event_id)
            self.assertFalse((workspace / "drafts" / f"{event_id}.json").exists())
            queue = manual_update.build_queue(workspace, CONFIG, PROFILE, LATER)
            self.assertIsNone(queue["events"][0]["draft"])

    def test_review_binds_the_exact_draft_and_only_that_draft_publishes(self):
        with temporary_directory() as root:
            workspace, event_id, _ = self.draft(root)
            ledger = root / "ledger.csv"
            row = manual_update.record_review(workspace, event_id, "AN01", "approved", LATER, ledger)
            self.assertEqual(row["content_hash"],
                             approval_ledger.content_hash(stored_draft(workspace, event_id)["content"]))
            queue = manual_update.build_queue(workspace, CONFIG, PROFILE, LATER,
                                              ledgers={"phase8": ledger})
            self.assertEqual(queue["events"][0]["draft"]["approved_exact_in"], ["phase8"])
            pointer = manual_update.publish_workspace(workspace, root / "site", "ed-001",
                                                      "reviewed_update", ledger, LATER)
            self.assertEqual(pointer["total_approved_cards"], 1)
            self.assertEqual(pointer["article_dates"], ["2026-09-12"])

    def test_edited_or_rejected_drafts_cannot_publish_and_the_last_edition_stays(self):
        with temporary_directory() as root:
            workspace, event_id, _ = self.draft(root)
            ledger = root / "ledger.csv"
            manual_update.record_review(workspace, event_id, "AN01", "approved", LATER, ledger)
            manual_update.publish_workspace(workspace, root / "site", "ed-001", "reviewed_update",
                                            ledger, LATER)
            before = (root / "site" / "publication.json").read_bytes()
            path = workspace / "drafts" / f"{event_id}.json"
            original = path.read_bytes()
            edited = stored_draft(workspace, event_id)
            edited["content"]["headline_en"] += " (edited after approval)"
            path.write_text(json.dumps(edited, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(publication.PublishError):
                manual_update.publish_workspace(workspace, root / "site", "ed-002",
                                                "reviewed_update", ledger, LATER)
            path.write_bytes(original)
            manual_update.record_review(workspace, event_id, "AN01", "rejected", LATER, ledger,
                                        notes="figure needs checking")
            with self.assertRaises(publication.PublishError):
                manual_update.publish_workspace(workspace, root / "site", "ed-003",
                                                "reviewed_update", ledger, LATER)
            self.assertEqual((root / "site" / "publication.json").read_bytes(), before)

    def test_an_event_without_a_ready_draft_cannot_be_reviewed(self):
        with temporary_directory() as root:
            workspace, event_id = shortlisted_workspace(root)
            with self.assertRaises(ValueError):
                manual_update.record_review(workspace, event_id, "AN01", "approved", LATER,
                                            root / "ledger.csv")
            self.assertFalse((root / "ledger.csv").exists())


if __name__ == "__main__":
    unittest.main()
