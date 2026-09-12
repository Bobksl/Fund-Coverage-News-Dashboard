"""Approved-only bilingual export: the mandatory link between tools/approval_ledger.py and a
real (non-mechanics) demo feed (Phase 5 handover section 5F).

tools/build_demo_feed.py exports baseline shortlist candidates and is deliberately never
"approved" -- every card there is `baseline_shortlist_pending_review` by construction, per
docs/demo-readme.md. This module is the separate path for actual drafted bilingual cards
(tools.drafting.Drafter output): it keeps only cards a named human reviewer approved at the exact
current revision and content hash (tools.approval_ledger.filter_approved_cards) and renders them
into the same site card JSON shape the UI already reads. A pending, rejected, or since-edited card
is simply absent from the output -- absence from this feed *is* the pending/rejected state; there
is no separate "not yet approved" card ever written here.

Never call this with baseline mechanics cards. It only accepts tools.drafting.Drafter.draft()
output (`status == "ready_for_analyst_review"`), so a baseline card (which never reaches that
status) cannot be relabelled as analyst-approved model output by construction.
"""
import json
from pathlib import Path

from tools.approval_ledger import filter_approved_cards

REVIEWABLE_STATUS = "ready_for_analyst_review"


def _rendered_card(decision, drafted_card, evidence_by_id, edition_date):
    content = drafted_card["content"]
    articles = [evidence_by_id[a] for a in decision["article_ids"] if a in evidence_by_id]
    return {
        "event_id": decision["event_id"],
        "date": edition_date or "undated",
        "partition": "reviewed",
        "status": "analyst_approved",
        "recommendation": decision["recommendation"],
        "relevance_level": decision["relevance_level"],
        "total_score": decision["total_score"],
        "primary_event_type": decision["primary_event_type"],
        "subtype": decision["subtype"],
        "en": {"headline": content["headline_en"], "summary": content["summary_en"],
              "why_it_matters": content["interpretation_en"]},
        "zh": {"headline": content["headline_zh"], "summary": content["summary_zh"],
              "why_it_matters": content["interpretation_zh"]},
        "zh_status": "approved",
        "tags": {"entities": sorted(set(decision["direct_entity_ids"]) |
                                    set(decision["propagated_entity_ids"])),
                "sectors": decision["sector_ids"], "geography": decision["countries"],
                "primary_region": decision["primary_region"],
                "event_type": decision["primary_event_type"]},
        "sources": [{"publisher": a["publisher"], "url": a["canonical_url"], "title": a["title"]}
                    for a in articles],
    }


def build_reviewed_cards(decisions_by_event_id, drafted_cards, evidence_by_id, ledger_path,
                         dates_by_event_id=None):
    """Return the rendered cards that are actually approved right now, keyed by event_id.

    `decisions_by_event_id` supplies the contract decision (tags, sources, scores) for each
    candidate event; `drafted_cards` are tools.drafting.Drafter.draft() outputs. A card whose
    status is not ready_for_analyst_review is never eligible for approval, matching the ledger's
    own binding on (event_id, revision, content_hash) -- there is nothing to approve without a
    drafted revision to hash.
    """
    dates_by_event_id = dates_by_event_id or {}
    reviewable = [
        {"event_id": card["event_id"], "revision": decisions_by_event_id[card["event_id"]]["revision"],
         "content": card["content"]}
        for card in drafted_cards
        if card.get("status") == REVIEWABLE_STATUS and card["event_id"] in decisions_by_event_id]
    approved_ids = {row["event_id"] for row in filter_approved_cards(reviewable, ledger_path)}
    cards = {}
    for card in drafted_cards:
        if card["event_id"] not in approved_ids:
            continue
        decision = decisions_by_event_id[card["event_id"]]
        cards[card["event_id"]] = _rendered_card(
            decision, card, evidence_by_id, dates_by_event_id.get(card["event_id"]))
    return cards


def write_reviewed_feed(out_dir, decisions_by_event_id, drafted_cards, evidence_by_id, ledger_path,
                        dates_by_event_id=None):
    """Write one JSON file per calendar date containing only currently approved cards.

    Mirrors tools.build_demo_feed's per-date file layout so the existing site/app.js can read
    either feed unmodified. Writes nothing for a date with zero approved cards rather than an
    empty placeholder file, so a reviewer can tell "no approved edition yet" from "checked, empty".
    """
    cards = build_reviewed_cards(decisions_by_event_id, drafted_cards, evidence_by_id, ledger_path,
                                 dates_by_event_id)
    by_date = {}
    for card in cards.values():
        by_date.setdefault(card["date"], []).append(card)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for date, day_cards in by_date.items():
        ordered = sorted(day_cards, key=lambda c: c["total_score"] or 0, reverse=True)
        (out_dir / f"{date}.json").write_text(
            json.dumps(ordered, indent=2, ensure_ascii=False), encoding="utf-8")
    index = {
        "dates_with_cards": sorted(by_date),
        "total_approved_cards": len(cards),
        "generated_from": "tools.reviewed_export (approval-ledger-gated, real drafted cards only)",
        "disclosure": ("Every card here was approved by a named human reviewer at its exact "
                       "current revision and content hash. A pending, rejected, or "
                       "since-edited card is absent, not shown as pending."),
    }
    (out_dir / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return index


__all__ = ["build_reviewed_cards", "write_reviewed_feed"]
