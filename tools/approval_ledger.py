"""Minimal local approval ledger: analyst sign-off tied to an exact card revision hash.

Append-only CSV, one row per review decision (never overwritten -- a correction appends a new
row). A row references the event_id, revision, a content hash of the exact drafted card fields
being reviewed, reviewer, timestamp, status and notes. Approval is checked by hash equality, not
by event_id alone, so an event whose drafted content later changes (a redraft, a corrected
figure) is never silently treated as still approved -- the old hash simply has no match among
the new content's hash, and the card falls out of the exported/approved set until re-reviewed.

This is deliberately a file, not a service: "a simple file-based review step is sufficient; no
approval UI/backend is necessary" (docs/phase-4-plan.md, slice 4C). Publication benchmark labels
(e.g. a scoring band) are never treated as approval here -- only a row an analyst actually wrote.
"""
import csv
import hashlib
import json
from pathlib import Path

FIELDS = ("event_id", "revision", "content_hash", "reviewer_id", "reviewed_at", "status", "notes")
STATUSES = {"approved", "rejected"}


def content_hash(card_content):
    """Hash the exact fields under review (headline/summary/interpretation, EN and ZH, sources)."""
    canonical = json.dumps(card_content, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_review(path, event_id, revision, card_content, reviewer_id, reviewed_at, status,
                  notes=""):
    """Append one review decision. Never edits or removes a prior row."""
    if status not in STATUSES:
        raise ValueError(f"Unknown review status {status!r}; use one of {sorted(STATUSES)}")
    if not reviewer_id:
        raise ValueError("A review must record a reviewer_id; no anonymous approval")
    path = Path(path)
    is_new = not path.exists()
    row = {"event_id": event_id, "revision": revision, "content_hash": content_hash(card_content),
          "reviewer_id": reviewer_id, "reviewed_at": reviewed_at, "status": status, "notes": notes}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
    return row


def load_reviews(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def latest_decisions(path):
    """One row per (event_id, revision): the last-written row wins (corrections append)."""
    latest = {}
    for row in load_reviews(path):
        latest[(row["event_id"], row["revision"])] = row
    return latest


def approved_keys(path):
    """(event_id, revision, content_hash) triples whose most recent decision is approved.

    Binding on all three, not the hash alone, is deliberate: two unrelated events could in
    principle draft to identical text, and a hash-only check would then credit one event's
    approval to the other. Revision is compared as text since the CSV round-trip stores it that
    way; callers pass their revision as whatever type they have and it is normalized here.
    """
    return {(row["event_id"], row["revision"], row["content_hash"])
           for row in latest_decisions(path).values() if row["status"] == "approved"}


def filter_approved_cards(cards, path, content_field="content"):
    """Return only cards whose exact current (event_id, revision, content hash) was approved.

    A card is a dict with at least event_id, revision and the field named by content_field
    (defaults to the shape tools.drafting.Drafter.draft() returns). Never treats an event_id
    match alone as approval, never lets a revision bump silently inherit an old approval, and
    never credits a benchmark/recommendation label as review.
    """
    approved = approved_keys(path)
    kept = []
    for card in cards:
        current_hash = content_hash(card.get(content_field))
        key = (str(card["event_id"]), str(card["revision"]), current_hash)
        if key in approved:
            kept.append(dict(card, content_hash=current_hash))
    return kept
