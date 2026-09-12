"""Build the static browser-demo feed from real baseline decisions.

Demo-only. Reads the run-001 predictions (deterministic baseline, already evaluated in
docs/phase-2-disposition.md) and the frozen evidence, and writes one JSON file per calendar
date plus an index, under work/phase2/demo-feed/ (ignored by git; the demo HTML/JS in site/
reads these at runtime).

The ordinary calendar is built only from natural-feed decisions, with the daily capacity target
applied per Asia/Hong_Kong calendar day (tools.scoring.select_editions_by_day), not once across
the whole partition -- a busy day can no longer use up the capacity a later quiet day never gets
a chance at. The independent challenge partition never appears in this calendar (finding 4: "No
challenge records in the ordinary news feed"); its shortlisted candidates are written to a
separate diagnostic file instead.

No LLM ran, so there are no analyst-approved cards and no Chinese translation. Every card is
labelled `baseline_shortlist_pending_review`, never `approved` or `published` -- the data
contract reserves those statuses for a recorded analyst review, which never happened here.
"""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tools.baseline import load_config
from tools.records import read_jsonl
from tools.scoring import SELECTED, select_editions_by_day

ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / "work/phase2/run-001"
EVIDENCE_PATH = ROOT / "work/phase2/freeze-001/evidence.jsonl"
OUT_DIR = ROOT / "work/phase2/demo-feed"
NATURAL_PARTITIONS = ("natural_feed_holdout", "natural_feed_calibration")
DIAGNOSTIC_PARTITIONS = ("challenge",)
HK_OFFSET = timezone(timedelta(hours=8))
# The collection window from docs/phase-2-collection-status.md, used only to give the demo's
# date navigator a continuous calendar (most days are legitimately empty -- 22 shortlisted
# events across a month is the real shape of the result, not a display bug).
COLLECTION_WINDOW = (date(2026, 8, 12), date(2026, 9, 10))

EVENT_TYPE_LABELS = {item["canonical_id"]: item["display_name"]
                     for item in json.loads((ROOT / "config/event_types.json")
                                            .read_text(encoding="utf-8"))["event_types"]}


def _hk_date(article):
    """Return the Asia/Hong_Kong editorial calendar date, or None if none is established.

    A datetime-precision timestamp is converted to HK local time before taking the date, so an
    article published just after UTC midnight lands on the correct HK calendar day. A date-only
    record has no time to convert and keeps its published date as-is, per decision-record.md
    ("date-only evidence must not acquire an invented publication time").
    """
    published_at = article.get("published_at")
    if not published_at:
        return None
    if article.get("published_date_precision") == "datetime":
        return datetime.fromisoformat(str(published_at)).astimezone(HK_OFFSET).date().isoformat()
    return str(published_at)[:10]


def _earliest_date(decision, evidence_by_id):
    articles = [evidence_by_id[aid] for aid in decision["article_ids"] if aid in evidence_by_id]
    dated = sorted(d for d in (_hk_date(a) for a in articles) if d)
    return dated[0] if dated else None


def _card(decision, evidence_by_id, partition, edition_date):
    articles = [evidence_by_id[aid] for aid in decision["article_ids"] if aid in evidence_by_id]
    parties = decision["event_identity"].get("parties") or []
    type_label = EVENT_TYPE_LABELS.get(decision["primary_event_type"], decision["primary_event_type"])
    headline = f"{', '.join(parties) or 'Unnamed party'} — {type_label}"
    return {
        "event_id": decision["event_id"],
        "date": edition_date or "undated",
        "partition": partition,
        "status": "baseline_shortlist_pending_review",
        "recommendation": decision["recommendation"],
        "relevance_level": decision["relevance_level"],
        "total_score": decision["total_score"],
        "primary_event_type": decision["primary_event_type"],
        "subtype": decision["subtype"],
        "en": {"headline": headline, "summary": decision["eligibility_reason"],
              "why_it_matters": None},
        "zh": None,
        "zh_status": "not_available: no model provider configured, drafting stage never ran",
        "tags": {"entities": sorted(set(decision["direct_entity_ids"]) |
                                    set(decision["propagated_entity_ids"])),
                "sectors": decision["sector_ids"], "geography": decision["countries"],
                "primary_region": decision["primary_region"],
                "event_type": decision["primary_event_type"]},
        "sources": [{"publisher": a["publisher"], "url": a["canonical_url"], "title": a["title"]}
                    for a in articles],
    }


def build():
    evidence_by_id = {rec["article_id"]: rec for rec in read_jsonl(EVIDENCE_PATH)}
    counts = {}

    natural_decisions = []
    for partition in NATURAL_PARTITIONS:
        decisions = list(read_jsonl(RUN_DIR / partition / "predictions.jsonl"))
        counts[partition] = {"decisions": len(decisions),
                             "shortlisted": sum(1 for d in decisions if d["recommendation"] in SELECTED)}
        for decision in decisions:
            decision = dict(decision, _demo_partition=partition)
            natural_decisions.append(decision)

    dates_by_event_id = {d["event_id"]: _earliest_date(d, evidence_by_id) for d in natural_decisions}
    editions, undated = select_editions_by_day(natural_decisions, dates_by_event_id,
                                               load_config()["scoring"])

    cards_by_date = {}
    for day, edition in editions.items():
        cards = [_card(d, evidence_by_id, d["_demo_partition"], day) for d in edition["selected"]]
        cards_by_date[day] = sorted(cards, key=lambda c: c["total_score"], reverse=True)
    undated_cards = [_card(d, evidence_by_id, d["_demo_partition"], None) for d in undated
                     if d["recommendation"] in SELECTED]

    diagnostic_cards = []
    for partition in DIAGNOSTIC_PARTITIONS:
        decisions = list(read_jsonl(RUN_DIR / partition / "predictions.jsonl"))
        counts[partition] = {"decisions": len(decisions),
                             "shortlisted": sum(1 for d in decisions if d["recommendation"] in SELECTED)}
        for decision in decisions:
            if decision["recommendation"] not in SELECTED:
                continue
            diagnostic_cards.append(
                _card(decision, evidence_by_id, partition, _earliest_date(decision, evidence_by_id)))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    window_start, window_end = COLLECTION_WINDOW
    actual_dates = [date.fromisoformat(d) for d in cards_by_date]
    start = min([window_start, *actual_dates]) if actual_dates else window_start
    end = max([window_end, *actual_dates]) if actual_dates else window_end
    full_range = [start + timedelta(days=n) for n in range((end - start).days + 1)]
    for day in full_range:
        key = day.isoformat()
        (OUT_DIR / f"{key}.json").write_text(
            json.dumps(cards_by_date.get(key, []), indent=2, ensure_ascii=False), encoding="utf-8")
    if undated_cards:
        (OUT_DIR / "undated.json").write_text(
            json.dumps(undated_cards, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "challenge-diagnostic.json").write_text(
        json.dumps(diagnostic_cards, indent=2, ensure_ascii=False), encoding="utf-8")

    index = {
        "dates": [day.isoformat() for day in full_range],
        "dates_with_cards": sorted(d for d in cards_by_date if cards_by_date[d]),
        "has_undated": bool(undated_cards),
        "has_challenge_diagnostic": bool(diagnostic_cards),
        "generated_from": "work/phase2/run-001 (deterministic baseline, engine=deterministic_baseline)",
        "counts": counts,
        "disclosure": (
            "These are baseline shortlist candidates, not published news. No analyst has "
            "reviewed them and no LLM classifier has run. The measured baseline result is a "
            "FAIL against the agreed bars (natural-feed holdout: 75% precision vs 90% bar, "
            "14.3% recall vs 85% bar, 1 of 2 must-not-miss). See docs/phase-2-disposition.md. "
            "The daily capacity target is applied per Asia/Hong_Kong calendar day. The "
            "independent challenge partition is excluded from this calendar; see "
            "challenge-diagnostic.json for those probe-only candidates."
        ),
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return index


if __name__ == "__main__":
    result = build()
    print(json.dumps(result, indent=2, ensure_ascii=False))
