"""Static data for the public dashboard: one JSON file per day, plus index.json and status.json.

Shapes are defined in docs/site-data-contract.md. Every write goes to a temporary file first and
then replaces the target, so an interrupted refresh leaves the previous files intact.
"""
import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"
RULES_PATH = ROOT / "config" / "filter_rules.json"
WINDOW_DAYS = 90
HKT = timezone(timedelta(hours=8))
REGIONS = ("US", "Europe", "APAC", "Global")
REVIEW_STATUSES = ("reviewed", "unreviewed")
ORIGINS = ("analyst_labeled", "auto_fetch")
MODES = ("scheduled", "manual")
REFRESH_RESULTS = ("succeeded", "no_new_items", "failed")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DAY_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


def load_rules(path=RULES_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def today_hkt(now=None):
    return (now or datetime.now(timezone.utc)).astimezone(HKT).date()


def card_id(url):
    """Stable 12-hex id from the source URL, so the same article is never added twice."""
    normalized = url.strip().split("#", 1)[0].rstrip("/").lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_card(card, rules):
    """Raise ValueError unless the card matches the contract; returns the card unchanged."""
    _require(isinstance(card, dict), "card must be an object")
    _require(re.fullmatch(r"[0-9a-f]{12}", str(card.get("id"))) is not None,
             "id must be 12 lowercase hex characters")
    _require(ISO_DATE.match(str(card.get("date"))) is not None, "date must be YYYY-MM-DD")
    date.fromisoformat(card["date"])
    for field in ("headline", "summary"):
        value = card.get(field)
        _require(isinstance(value, dict) and all(isinstance(value.get(lang), str) and value[lang].strip()
                                                 for lang in ("en", "zh")),
                 f"{field} needs non-empty en and zh text")
    gps, sectors = card.get("gps"), card.get("sectors")
    _require(isinstance(gps, list) and set(gps) <= set(rules["gps"]), f"unknown GP tag in {gps}")
    _require(isinstance(sectors, list) and set(sectors) <= set(rules["sectors"]),
             f"unknown sector tag in {sectors}")
    _require(bool(gps or sectors), "a card needs at least one GP or sector tag")
    _require(card.get("region") in REGIONS, f"region must be one of {REGIONS}")
    source = card.get("source") or {}
    _require(isinstance(source.get("publisher"), str) and source["publisher"].strip(),
             "source.publisher is required")
    _require(str(source.get("url", "")).startswith(("https://", "http://")), "source.url must be http(s)")
    _require(card.get("review_status") in REVIEW_STATUSES, "invalid review_status")
    _require(card.get("origin") in ORIGINS, "invalid origin")
    return card


def _day_files(data_dir):
    data_dir = Path(data_dir)
    if not data_dir.exists():
        return {}
    return {match.group(1): path for path in data_dir.iterdir() if (match := DAY_FILE.match(path.name))}


def load_day(data_dir, day):
    path = Path(data_dir) / f"{day}.json"
    return json.loads(path.read_text(encoding="utf-8"))["items"] if path.exists() else []


def existing_ids(data_dir=DATA_DIR):
    return {card["id"] for day in _day_files(data_dir) for card in load_day(data_dir, day)}


def add_cards(cards, rules, data_dir=DATA_DIR, today=None, window_days=WINDOW_DAYS, now=None):
    """Validate and merge cards into day files, skipping known ids and days outside the window.

    Returns the ids actually added. Day files older than the rolling window are deleted and
    index.json is rebuilt on every call, even when nothing new was added.
    """
    for card in cards:
        validate_card(card, rules)
    today = today or today_hkt(now)
    cutoff = today - timedelta(days=window_days)
    known = existing_ids(data_dir)
    by_day, added = {}, []
    for card in cards:
        if card["id"] in known or date.fromisoformat(card["date"]) < cutoff:
            continue
        known.add(card["id"])
        by_day.setdefault(card["date"], []).append(card)
        added.append(card["id"])
    for day, new_cards in by_day.items():
        items = load_day(data_dir, day) + new_cards
        items.sort(key=lambda card: card.get("published_at") or "", reverse=True)
        _write_json(Path(data_dir) / f"{day}.json", {"date": day, "items": items})
    for day, path in _day_files(data_dir).items():
        if date.fromisoformat(day) < cutoff:
            path.unlink()
    write_index(rules, data_dir, window_days, now)
    return added


def write_index(rules, data_dir=DATA_DIR, window_days=WINDOW_DAYS, now=None):
    from tools import news_events

    counts = {day: len(load_day(data_dir, day)) for day in _day_files(data_dir)}
    dates = sorted((day for day, count in counts.items() if count), reverse=True)
    index = {
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "window_days": window_days,
        "dates": dates,
        "counts": {day: counts[day] for day in dates},
        "labels": {
            "gps": {key: {"en": value["en"], "zh": value["zh"]} for key, value in rules["gps"].items()},
            "sectors": {key: {"en": value["en"], "zh": value["zh"]} for key, value in rules["sectors"].items()},
            "regions": rules["regions"],
        },
    }
    _write_json(Path(data_dir) / "index.json", index)
    news_events.write_events(data_dir, now=now)
    return index


def write_status(data_dir=DATA_DIR, *, mode, schedule, result, new_items, detail=None, now=None):
    """Record one refresh attempt. A failed attempt keeps the previous last_success_at."""
    _require(mode in MODES, f"mode must be one of {MODES}")
    _require(result in REFRESH_RESULTS, f"result must be one of {REFRESH_RESULTS}")
    path = Path(data_dir) / "status.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    stamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    status = {
        "mode": mode,
        "schedule": schedule,
        "last_refresh_at": stamp,
        "last_refresh_result": result,
        "last_success_at": previous.get("last_success_at") if result == "failed" else stamp,
        "new_items": new_items,
        "detail": detail,
    }
    _write_json(path, status)
    return status
