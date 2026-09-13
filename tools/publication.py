"""Phase 8 publication: isolated reviewed editions behind an atomically swapped pointer.

The served site directory holds `index.html`, `app.js`, immutable `editions/<publication_id>/`
directories, `publication.json` (which edition is served) and `status.json` (the last source check
and the last publish attempt). Each is a separate fact: a source check never changes the served
edition, and a publish never claims news was checked (docs/phase-8-plan.md, first delivery).

Only tools.reviewed_export writes edition data, so the approval ledger's exact
(event_id, revision, content_hash) gate is the only way a card gets in. An edition is built in a
staging directory and served only after it succeeds; any failure leaves the previous
`publication.json` untouched and records the failure in `status.json` instead.

No collection, model call or credential is involved here, and nothing on the page can trigger one.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from tools import reviewed_export
from tools.records import read_jsonl

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "site"
DEFAULT_SITE = ROOT / "work/phase8/site"
SITE_FILES = ("index.html", "app.js")
EDITION_KINDS = {"historical_sample", "reviewed_update"}
SOURCE_CHECK_STATUSES = {"succeeded", "failed", "budget_stopped"}
PUBLICATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
STALE_AFTER_HOURS = 24
# The repository lives in a OneDrive-synced folder, where a sync or antivirus handle can hold a
# just-written file for a moment and os.replace fails with "Access is denied". Retry briefly; a
# lock that does not clear still raises.
REPLACE_ATTEMPTS = 5
REPLACE_RETRY_SECONDS = 0.2
FOOTER = ("Published by tools/publication.py from approval-ledger-gated cards "
          "(tools/reviewed_export.py). Updates are manual: an operator processes supplied "
          "evidence, a named reviewer approves an exact card revision, and only then is a new "
          "edition published. Reloading reads the published edition; it does not collect news "
          "or run a model.")
PAGE_TEXT = {
    "historical_sample": {
        "subtitle": ("Junson Capital · Alternative Investment team · historical sample edition "
                     "(one human-approved card), not today's news"),
        "footer": FOOTER},
    "reviewed_update": {
        "subtitle": ("Junson Capital · Alternative Investment team · analyst-reviewed edition; "
                     "every card approved at its exact revision"),
        "footer": FOOTER},
}


class PublishError(RuntimeError):
    """The served edition was not replaced."""


def tree_digest(directory):
    """SHA-256 over every file's relative path and bytes, in a stable order."""
    directory = Path(directory)
    digest = hashlib.sha256()
    files = sorted((p.relative_to(directory).as_posix(), p) for p in directory.rglob("*")
                   if p.is_file())
    for relative, path in files:
        digest.update(relative.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def replace_with_retry(source, target):
    """os.replace, retried a bounded number of times while a transient lock holds the target."""
    for attempt in range(1, REPLACE_ATTEMPTS + 1):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS:
                raise
            time.sleep(REPLACE_RETRY_SECONDS * attempt)


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
    replace_with_retry(temporary, path)


def read_status(site_dir):
    status = {"update_mode": "manual", "scheduler": "not_installed",
              "stale_after_hours": STALE_AFTER_HOURS, "last_source_check": None,
              "last_successful_source_check": None, "last_publish_attempt": None}
    path = Path(site_dir) / "status.json"
    if path.exists():
        status.update(json.loads(path.read_text(encoding="utf-8")))
    return status


def _update_status(site_dir, **changes):
    status = dict(read_status(site_dir), **changes)
    write_json_atomic(Path(site_dir) / "status.json", status)
    return status


def record_source_check(site_dir, checked_at, status, detail=None, new_items=None):
    """Record one source check. A failure keeps the last successful check visible beside it."""
    if status not in SOURCE_CHECK_STATUSES:
        raise ValueError(f"Unknown source check status {status!r}; "
                         f"use one of {sorted(SOURCE_CHECK_STATUSES)}")
    check = {"checked_at": checked_at, "status": status, "detail": detail, "new_items": new_items}
    changes = {"last_source_check": check}
    if status == "succeeded":
        changes["last_successful_source_check"] = check
    return _update_status(site_dir, **changes)


def publish(site_dir, publication_id, published_at, edition_kind, decisions_by_event_id,
            drafted_cards, evidence_by_id, ledger_path, dates_by_event_id=None,
            site_source=SITE_DIR):
    """Build one approved-only edition in isolation, then serve it by swapping the pointer.

    Raises PublishError (after recording the failed attempt) whenever the pointer was not swapped.
    """
    if edition_kind not in EDITION_KINDS:
        raise ValueError(f"Unknown edition kind {edition_kind!r}; use one of {sorted(EDITION_KINDS)}")
    if not PUBLICATION_ID.match(publication_id):
        raise ValueError(f"Invalid publication id {publication_id!r}")
    site_dir = Path(site_dir)
    final = site_dir / "editions" / publication_id
    staging = site_dir / "editions" / f".staging-{publication_id}"
    attempt = {"publication_id": publication_id, "attempted_at": published_at}
    moved = False
    try:
        if final.exists():
            raise PublishError(f"Edition {publication_id} already exists; editions are immutable")
        shutil.rmtree(staging, ignore_errors=True)
        index = reviewed_export.write_reviewed_feed(
            staging, decisions_by_event_id, drafted_cards, evidence_by_id, ledger_path,
            dates_by_event_id)
        if index["total_approved_cards"] == 0:
            raise PublishError("There is no approved card at its exact revision and content "
                               "hash; the served edition was not replaced")
        digest = tree_digest(staging)
        os.rename(staging, final)
        moved = True
        for name in SITE_FILES:
            temporary = site_dir / f"{name}.partial"
            shutil.copyfile(Path(site_source) / name, temporary)
            replace_with_retry(temporary, site_dir / name)
        pointer = {"schema": "publication-v1", "publication_id": publication_id,
                   "published_at": published_at, "edition_kind": edition_kind,
                   "update_mode": "manual", "edition_path": f"editions/{publication_id}",
                   "edition_sha256": digest, "total_approved_cards": index["total_approved_cards"],
                   "article_dates": index["dates_with_cards"], "page_text": PAGE_TEXT[edition_kind]}
        write_json_atomic(site_dir / "publication.json", pointer)
    except Exception as error:
        shutil.rmtree(staging, ignore_errors=True)
        if moved:
            shutil.rmtree(final, ignore_errors=True)
        _update_status(site_dir, last_publish_attempt=dict(attempt, status="failed",
                                                           detail=str(error)))
        if isinstance(error, PublishError):
            raise
        raise PublishError(str(error)) from error
    _update_status(site_dir, last_publish_attempt=dict(attempt, status="succeeded", detail=None))
    return pointer


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pub = commands.add_parser("publish", help="Publish approved drafted cards as a new edition")
    pub.add_argument("--site", type=Path, default=DEFAULT_SITE)
    pub.add_argument("--id", required=True, help="New, never reused publication id")
    pub.add_argument("--kind", required=True, choices=sorted(EDITION_KINDS))
    pub.add_argument("--decisions", type=Path, required=True, help="predictions.jsonl")
    pub.add_argument("--draft", type=Path, action="append", required=True,
                     help="A tools.drafting.Drafter.draft() result JSON; repeatable")
    pub.add_argument("--evidence", type=Path, required=True, help="evidence.jsonl")
    pub.add_argument("--ledger", type=Path, required=True, help="approval-ledger.csv")
    pub.add_argument("--date", action="append", default=[], metavar="EVENT_ID=YYYY-MM-DD")
    check = commands.add_parser("record-check", help="Record a manual source check outcome")
    check.add_argument("--site", type=Path, default=DEFAULT_SITE)
    check.add_argument("--status", required=True, choices=sorted(SOURCE_CHECK_STATUSES))
    check.add_argument("--detail", default=None)
    check.add_argument("--new-items", type=int, default=None)
    args = parser.parse_args(argv)

    if args.command == "record-check":
        print(json.dumps(record_source_check(args.site, _now(), args.status, args.detail,
                                             args.new_items), ensure_ascii=False, indent=2))
        return 0
    decisions = {row["event_id"]: row for row in read_jsonl(args.decisions)}
    drafts = [json.loads(path.read_text(encoding="utf-8")) for path in args.draft]
    evidence = {row["article_id"]: row for row in read_jsonl(args.evidence)}
    dates = dict(item.split("=", 1) for item in args.date)
    try:
        pointer = publish(args.site, args.id, _now(), args.kind, decisions, drafts, evidence,
                          args.ledger, dates)
    except PublishError as error:
        print(json.dumps({"status": "failed", "detail": str(error),
                          "served_edition": "unchanged"}, ensure_ascii=False))
        return 2
    print(json.dumps(pointer, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
