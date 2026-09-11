"""Offline article-only packet builder. Does not label, group, rank or call a model."""
import argparse
import csv
import hashlib
import html
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

FIELDS = ("article_id", "title", "url", "publisher", "published_date")
LABEL_FIELDS = ("article_id", "analyst_id", "decision", "relevance_level",
                "materiality_tier", "event_group_id", "entity_roles",
                "must_not_miss", "rationale", "evidence_access", "reviewed_on")


def build_packet(records, destination):
    articles, seen = [], set()
    for record in records:
        row = {key: record[key] for key in FIELDS}
        if any(not isinstance(value, str) or not value.strip() for value in row.values()):
            raise ValueError("Article fields must be nonempty strings")
        UUID(row["article_id"])
        date.fromisoformat(row["published_date"])
        url = urlsplit(row["url"])
        if url.scheme != "https" or not url.hostname or any(c in row["url"] for c in '\r\n<>"'):
            raise ValueError("Expected a public HTTPS source URL")
        if row["article_id"] in seen:
            raise ValueError("Duplicate article ID")
        seen.add(row["article_id"])
        articles.append(row)
    if not articles:
        raise ValueError("Empty packet")
    # Opaque IDs determine order; no ranking, category or suggested grouping.
    articles.sort(key=lambda row: row["article_id"])
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in articles)
    (destination / "articles.jsonl").write_bytes(payload.encode("utf-8"))
    lines = ["# Article review packet", "", "Read each original source before completing the blank labels file.",
             "All watchlist entities are monitoring-only. Article order carries no recommendation.",
             "Record insufficient evidence if the source cannot support a decision; do not infer from the title alone.",
             "This link packet is not a frozen full-text evidence corpus.", ""]
    for row in articles:
        lines.extend([f'## {row["article_id"]}', "", html.escape(row["title"]), "",
                      f'{html.escape(row["publisher"])} | {row["published_date"]}', "",
                      f'Original source: <{row["url"]}>', ""])
    (destination / "articles.md").write_text("\n".join(lines), encoding="utf-8")
    with (destination / "analyst-labels.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows({"article_id": row["article_id"]} for row in articles)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    (destination / "packet-sha256.txt").write_text(digest + "  articles.jsonl\n", encoding="utf-8")
    return len(articles)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.source.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Created {build_packet(records, args.destination)} article records; no inference performed.")
