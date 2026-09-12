"""Build the static browser-demo feed from real baseline decisions.

Demo-only. Reads the run-001 predictions (deterministic baseline, already evaluated in
docs/phase-2-disposition.md) and the frozen evidence, and writes one JSON file per calendar
date plus an index, under work/phase2/demo-feed/ (ignored by git; the demo HTML/JS in site/
reads these at runtime).

No LLM ran, so there are no analyst-approved cards and no Chinese translation. Every card is
labelled `baseline_shortlist_pending_review`, never `approved` or `published` -- the data
contract reserves those statuses for a recorded analyst review, which never happened here.
"""
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from tools.records import read_jsonl
from tools.scoring import SELECTED

ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / "work/phase2/run-001"
EVIDENCE_PATH = ROOT / "work/phase2/freeze-001/evidence.jsonl"
OUT_DIR = ROOT / "work/phase2/demo-feed"
PARTITIONS = ("natural_feed_holdout", "natural_feed_calibration", "challenge")
# The collection window from docs/phase-2-collection-status.md, used only to give the demo's
# date navigator a continuous calendar (most days are legitimately empty -- 22 shortlisted
# events across a month is the real shape of the result, not a display bug).
COLLECTION_WINDOW = (date(2026, 8, 12), date(2026, 9, 10))

EVENT_TYPE_LABELS = {item["canonical_id"]: item["display_name"]
                     for item in json.loads((ROOT / "config/event_types.json")
                                            .read_text(encoding="utf-8"))["event_types"]}


def _card(decision, evidence_by_id, partition):
    articles = [evidence_by_id[aid] for aid in decision["article_ids"] if aid in evidence_by_id]
    dated = sorted((a["published_at"] or "") for a in articles if a["published_at"])
    date = dated[0][:10] if dated else "undated"
    parties = decision["event_identity"].get("parties") or []
    type_label = EVENT_TYPE_LABELS.get(decision["primary_event_type"], decision["primary_event_type"])
    headline = f"{', '.join(parties) or 'Unnamed party'} — {type_label}"
    return {
        "event_id": decision["event_id"],
        "date": date,
        "partition": partition,
        "status": "baseline_shortlist_pending_review",
        "recommendation": decision["recommendation"],
        "relevance_level": decision["relevance_level"],
        "total_score": decision["total_score"],
        "primary_event_type": decision["primary_event_type"],
        "subtype": decision["subtype"],
        "en": {"headline": headline, "summary": decision["eligibility_reason"]},
        "zh": None,
        "zh_status": "not_available: no model provider configured, drafting stage never ran",
        "sources": [{"publisher": a["publisher"], "url": a["canonical_url"], "title": a["title"]}
                    for a in articles],
    }


def build():
    evidence_by_id = {rec["article_id"]: rec for rec in read_jsonl(EVIDENCE_PATH)}
    cards_by_date = defaultdict(list)
    counts = {}
    for partition in PARTITIONS:
        predictions_path = RUN_DIR / partition / "predictions.jsonl"
        decisions = list(read_jsonl(predictions_path))
        counts[partition] = {"decisions": len(decisions),
                             "shortlisted": sum(1 for d in decisions if d["recommendation"] in SELECTED)}
        for decision in decisions:
            if decision["recommendation"] not in SELECTED:
                continue
            card = _card(decision, evidence_by_id, partition)
            cards_by_date[card["date"]].append(card)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    window_start, window_end = COLLECTION_WINDOW
    actual_dates = [date.fromisoformat(d) for d in cards_by_date if d != "undated"]
    # Extend the calendar to cover any shortlisted event outside the natural-feed window too
    # (independent challenge probes can predate it) -- never drop a card by narrowing the range.
    start = min([window_start, *actual_dates]) if actual_dates else window_start
    end = max([window_end, *actual_dates]) if actual_dates else window_end
    full_range = [start + timedelta(days=n) for n in range((end - start).days + 1)]
    for day in full_range:
        key = day.isoformat()
        cards = sorted(cards_by_date.get(key, []), key=lambda c: c["total_score"], reverse=True)
        (OUT_DIR / f"{key}.json").write_text(
            json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")
    if "undated" in cards_by_date:
        (OUT_DIR / "undated.json").write_text(
            json.dumps(cards_by_date["undated"], indent=2, ensure_ascii=False), encoding="utf-8")

    index = {
        "dates": [day.isoformat() for day in full_range],
        "dates_with_cards": sorted(d for d in cards_by_date if d != "undated"),
        "has_undated": "undated" in cards_by_date,
        "generated_from": "work/phase2/run-001 (deterministic baseline, engine=deterministic_baseline)",
        "counts": counts,
        "disclosure": (
            "These are baseline shortlist candidates, not published news. No analyst has "
            "reviewed them and no LLM classifier has run. The measured baseline result is a "
            "FAIL against the agreed bars (natural-feed holdout: 75% precision vs 90% bar, "
            "14.3% recall vs 85% bar, 1 of 2 must-not-miss). See docs/phase-2-disposition.md."
        ),
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return index


if __name__ == "__main__":
    result = build()
    print(json.dumps(result, indent=2, ensure_ascii=False))
