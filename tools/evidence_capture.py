"""Capture permitted article text, hash it and attach it to the evidence records.

Text is what a reader sees on the public page. Nothing here purchases a subscription, creates an
account or works around an access control: where a page does not show the article, the record
keeps `metadata_only` and says so. Captured text is stored privately under ignored `work/` and
never enters Git.

A changed capture never overwrites the previous one silently. The earlier hash is preserved and a
correction is recorded, because the contract treats evidence revision as an appended fact.
"""
import hashlib
import json
import re
from pathlib import Path

from tools.records import validate_article, write_jsonl

# A page that renders only a teaser plus a subscribe prompt is not readable evidence.
GATE_MARKERS = re.compile(
    r"already have an account|subscribe to (?:continue|read)|sign in to (?:continue|read)|"
    r"to continue reading|members only|this article is for subscribers|already a subscriber|"
    r"subscribe now for unlimited", re.I)
MINIMUM_ARTICLE_CHARS = 400
# A gated lede still states the core fact and is worth keeping as an excerpt. Below this it is
# only a headline restatement and carries nothing the metadata does not already hold.
MINIMUM_EXCERPT_CHARS = 150
# Captures are bounded excerpts: enough for the classifier to judge, and a smaller footprint of
# third-party text than retaining whole articles.
EXCERPT_CHARS = 800


def normalize(text):
    """Collapse whitespace so a hash tracks the words, not the page's line wrapping."""
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+\n", "\n", (text or "").strip()))


def digest(text):
    return "sha256:" + hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def classify(text, reported_status=None, mode="full", gated=None):
    """Decide access status and evidence scope from what the publisher actually served.

    `mode="excerpt"` means the capture was deliberately truncated, so the scope is an excerpt
    however much text came back; claiming full_text for a bounded capture would misstate what the
    classifier saw. `gated` records that the publisher served a lede plus a registration or
    subscription prompt: that is a real excerpt, not a failure, and never a full text.
    """
    body = normalize(text)
    if reported_status == "unavailable" or not body:
        return "unavailable", "metadata_only"
    if gated is None:
        gated = bool(GATE_MARKERS.search(body))
    if gated:
        return ("partial",
                "primary_excerpt" if len(body) >= MINIMUM_EXCERPT_CHARS else "metadata_only")
    if len(body) < MINIMUM_EXCERPT_CHARS:
        return "partial", "metadata_only"
    if len(body) < MINIMUM_ARTICLE_CHARS:
        return "partial", "primary_excerpt"
    return "accessible", "primary_excerpt" if mode == "excerpt" else "full_text"


def flag_boilerplate(captures, min_repeats=3):
    """Reject captures that are site chrome rather than article text.

    A JS-rendered page served as raw HTML yields the navigation menu for every article, identical
    each time. Storing that as an excerpt would manufacture evidence that was never read, so any
    text repeated verbatim across several different articles is marked as a capture failure.
    """
    counts = {}
    for capture in captures:
        body = normalize(capture.get("text"))
        if body:
            counts[body] = counts.get(body, 0) + 1
    flagged = 0
    for capture in captures:
        body = normalize(capture.get("text"))
        if body and counts.get(body, 0) >= min_repeats:
            capture["text"] = ""
            capture["access_status"] = "unavailable"
            capture["capture_failure"] = (
                "boilerplate: identical text returned for "
                f"{counts[body]} different articles, so the page body was not captured")
            flagged += 1
    return flagged


def store_capture(store_dir, article_id, text):
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    path = store_dir / f"{article_id}.txt"
    path.write_bytes(normalize(text).encode("utf-8"))
    return path


def apply_captures(records, captures, store_dir, store_prefix="work/phase2/evidence-store"):
    """Attach hashes and local references. Returns (updated records, report)."""
    by_id = {record["article_id"]: dict(record) for record in records}
    applied, corrections, skipped, invalid = [], [], [], []
    for capture in captures:
        article_id = capture["article_id"]
        record = by_id.get(article_id)
        if record is None:
            skipped.append({"article_id": article_id, "reason": "not in this cohort"})
            continue
        status, scope = classify(capture.get("text"), capture.get("access_status"),
                                 capture.get("mode", "full"), capture.get("gated"))
        if scope == "metadata_only":
            record["access_status"] = status
            record["evidence_scope"] = "metadata_only"
            record["evidence_hash"] = None
            record["evidence_local_ref"] = None
        else:
            new_hash = digest(capture["text"])
            previous = record.get("evidence_hash")
            if previous and previous != new_hash:
                # Source content changed since the last capture: append, never overwrite.
                corrections.append({"article_id": article_id, "previous_evidence_hash": previous,
                                    "new_evidence_hash": new_hash,
                                    "captured_at": capture.get("captured_at"),
                                    "note": "Source text changed between captures."})
            store_capture(store_dir, article_id, capture["text"])
            record["access_status"] = status
            record["evidence_scope"] = scope
            record["evidence_hash"] = new_hash
            record["evidence_local_ref"] = f"{store_prefix}/{article_id}.txt"
        errors = validate_article(record)
        if errors:
            invalid.append({"article_id": article_id, "errors": errors})
            continue
        by_id[article_id] = record
        applied.append(article_id)

    updated = [by_id[record["article_id"]] for record in records]
    scopes, statuses = {}, {}
    for record in updated:
        scopes[record["evidence_scope"]] = scopes.get(record["evidence_scope"], 0) + 1
        statuses[record["access_status"]] = statuses.get(record["access_status"], 0) + 1
    report = {
        "records": len(updated), "captures_applied": len(applied),
        "corrections": corrections, "skipped": skipped, "invalid": invalid,
        "by_evidence_scope": dict(sorted(scopes.items())),
        "by_access_status": dict(sorted(statuses.items())),
        "uncaptured": sorted(record["article_id"] for record in updated
                             if record["evidence_scope"] == "metadata_only"),
        "limits": ("Hashes cover the text captured on the date shown, not the publisher's page "
                   "forever. A record left metadata_only carries no text and is not labelable "
                   "evidence; it is reported, never treated as an editorial rejection."),
    }
    return updated, report


def write_updated(path, records, allow_overwrite=True):
    return write_jsonl(path, records, allow_overwrite=allow_overwrite)


def load_batches(directory):
    """Read capture batches produced by the browser session."""
    captures = []
    for path in sorted(Path(directory).glob("*.json")):
        captures.extend(json.loads(path.read_text(encoding="utf-8")))
    return captures
