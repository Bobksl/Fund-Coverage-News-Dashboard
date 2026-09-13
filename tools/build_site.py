"""Backfill public/data with the analyst-reviewed history (articles published 2026-08-12 to 2026-09-11).

Joins the frozen evidence with the analyst's publish decisions from git-ignored work/phase2, keeps
one article per analyst event group, asks tools.summarize for the bilingual brief and tags, and
writes reviewed cards through tools.site_data. It needs the local work/ folder, so it runs on the
operator's machine; the scheduled refresh (tools/fetch_news.py) adds new days on top.

    python -m tools.build_site --dry-run
    python -m tools.build_site --limit 3
    python -m tools.build_site
"""
import argparse
import csv
import json
import sys
from pathlib import Path

from tools import site_data, summarize

ROOT = site_data.ROOT
EVIDENCE = ROOT / "work/phase2/freeze-001/evidence.jsonl"
LABELS = ROOT / "work/phase2/evaluator/label-review-003/normalized.csv"
CACHE = ROOT / "work/site-cache/briefs.json"
HISTORY_START = "2026-08-12"  # first day of the natural-feed collection window


def _value(value):
    return None if value in (None, "", "None", "null") else value


def _excerpt(record, root):
    ref = _value(record.get("evidence_local_ref"))
    path = Path(root) / ref if ref else None
    return path.read_text(encoding="utf-8", errors="replace") if path and path.exists() else ""


def historical_items(evidence_path=EVIDENCE, labels_path=LABELS, root=ROOT):
    """Return (items, skipped): one item per analyst-published event group, oldest first."""
    evidence = {}
    for line in Path(evidence_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            evidence[record["article_id"]] = record
    groups = {}
    with open(labels_path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["decision"] == "publish" and row["article_id"] in evidence:
                record = evidence[row["article_id"]]
                groups.setdefault(row["event_group_id"], []).append((row, record, _excerpt(record, root)))
    items, skipped = [], []
    for group_id, members in groups.items():
        # Prefer a fully accessible article, then the one with the most captured text.
        row, record, text = max(members, key=lambda m: (m[1].get("access_status") == "accessible", len(m[2])))
        published = _value(record.get("published_at")) or _value(record.get("event_date"))
        url = _value(record.get("canonical_url")) or _value(record.get("original_url"))
        if not published or not url:
            skipped.append({"group_id": group_id, "title": record.get("title"),
                            "reason": "no date" if not published else "no url"})
            continue
        items.append({"group_id": group_id, "title": record["title"], "publisher": record["publisher"],
                      "url": url, "date": published[:10], "published_at": _value(record.get("published_at")),
                      "text": text, "context": row.get("rationale", "")})
    items.sort(key=lambda item: (item["date"], item["group_id"]))
    return items, skipped


def main(argv=None):
    # Windows consoles default to a legacy code page; titles contain characters such as "€".
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="list events without calling the model")
    parser.add_argument("--since", default=HISTORY_START,
                        help="skip events dated before this day (default: collection window start)")
    parser.add_argument("--limit", type=int, default=0, help="brief only the first N events")
    parser.add_argument("--max-calls", type=int, default=150, help="hard cap on DeepSeek requests")
    parser.add_argument("--data-dir", type=Path, default=site_data.DATA_DIR)
    parser.add_argument("--cache", type=Path, default=CACHE)
    args = parser.parse_args(argv)

    rules = site_data.load_rules()
    items, skipped = historical_items()
    # Earlier-dated labels are curated challenge probes, not part of the daily feed history.
    items = [item for item in items if item["date"] >= args.since]
    if args.limit:
        items = items[:args.limit]
    print(f"{len(items)} event(s) to brief; {len(skipped)} skipped without a date or URL", file=sys.stderr)
    if args.dry_run:
        for item in items:
            print(f"{item['date']}  {item['publisher']}: {item['title']}")
        return 0

    summarizer = summarize.Summarizer(rules, max_calls=args.max_calls, cache_path=args.cache)
    cards, failures = [], []
    for number, item in enumerate(items, 1):
        try:
            brief = summarizer(item)
            card = summarize.make_card(item, brief, "reviewed", "analyst_labeled")
            site_data.validate_card(card, rules)
        except (summarize.SummaryError, ValueError) as error:
            failures.append({"group_id": item["group_id"], "title": item["title"], "error": str(error)})
            print(f"[{number}/{len(items)}] FAILED {item['title']}: {error}", file=sys.stderr)
            if summarizer.calls >= summarizer.max_calls:
                break
            continue
        cards.append(card)
        print(f"[{number}/{len(items)}] ok {item['date']} {card['gps'] + card['sectors']}", file=sys.stderr)

    added = site_data.add_cards(cards, rules, data_dir=args.data_dir)
    if not (Path(args.data_dir) / "status.json").exists():
        site_data.write_status(args.data_dir, mode="manual", schedule=rules["schedule"], result="succeeded",
                               new_items=len(added), detail="historical backfill of analyst-reviewed items")
    print(json.dumps({"added": len(added), "failures": failures, "skipped": skipped,
                      "calls": summarizer.calls, "usage": summarizer.usage}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
