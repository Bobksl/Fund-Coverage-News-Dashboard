"""Synthetic fixtures for Phase 2 engineering tests. No real article text, labels or model output."""
import shutil
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

# Sandbox temporary directories proved unreliable on this workspace; stay under ignored work/.
WORK_ROOT = Path(__file__).resolve().parents[1] / "work" / "test-workspace"


@contextmanager
def temporary_directory():
    workspace = WORK_ROOT / uuid4().hex
    workspace.mkdir(parents=True)
    try:
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def article(**overrides):
    record = {
        "article_id": "a1",
        "title": "Example Manager closes private credit fund",
        "original_url": "https://example.com/news/a1?utm_source=newsletter",
        "canonical_url": "https://example.com/news/a1",
        "publisher": "Example Manager",
        "originating_publisher": None,
        "discovery_method": "manual_curation",
        "source_kind": "issuer_release",
        "published_at": "2026-09-01T13:00:00+00:00",
        "published_date_precision": "datetime",
        "event_date": "2026-09-01",
        "first_seen_at": "2026-09-02T08:00:00+00:00",
        "retrieved_at": "2026-09-02T08:00:05+00:00",
        "access_status": "accessible",
        "evidence_scope": "full_text",
        "evidence_hash": "sha256:9f2c1a",
        "evidence_local_ref": "work/phase2/evidence/a1.txt",
        "claims": [],
        "supersedes_article_id": None,
    }
    record.update(overrides)
    return record


def component(points, reason="synthetic fixture anchor"):
    return {"points": points, "reason": reason, "evidence_refs": []}


def decision(**overrides):
    record = {
        "event_id": "p-event-1",
        "revision": 1,
        "decision_id": "d1",
        "run_id": "run-test",
        "attempt": 1,
        "article_ids": ["a1"],
        "claim_ids": [],
        "event_identity": {"parties": ["Example Manager"], "action": "fund_close",
                           "vehicle": "Example Credit Fund II", "period": None,
                           "event_date": "2026-09-01"},
        "direct_entity_ids": ["example_manager"],
        "propagated_entity_ids": [],
        "entity_matches": [],
        "held_status": "monitored",
        "asset_classes": ["private_credit"],
        "sector_ids": ["private_credit"],
        "theme_ids": [],
        "primary_event_type": "capital_formation",
        "subtype": "final_close",
        "secondary_event_types": [],
        "countries": ["US"],
        "primary_region": "US",
        "region_basis": "stated borrower and fund domicile",
        "relevance_level": "A",
        "eligibility_reason": "Tracked manager's own credit vehicle",
        "transmission": {"trigger": "final close", "mechanism": "deployable capital",
                         "outcome": "origination capacity", "uncertainty": "deployment pace"},
        "gates": {"evidence": "pass", "identity": "pass", "relevance": "pass",
                  "materiality": "pass", "transmission": "pass", "novelty": "pass"},
        "components": {"portfolio_fit": component(30), "materiality": component(20),
                       "investment_transmission": component(15), "actionability": component(8),
                       "source_credibility": component(10), "novelty": component(5)},
        "total_score": 88,
        "recommendation": "priority_shortlist",
        "disposition_reason_codes": ["shortlisted"],
        "duplicate_of": None,
        "update_of": None,
        "model_metadata": {"provider": "fixture", "model": "none", "prompt_version": "t1"},
        "spec_metadata": {"scoring_version": "0.1.0"},
        "analyst_review": None,
        "publication": {"status": "pending_review", "selection_reason": None},
    }
    record.update(overrides)
    return record
