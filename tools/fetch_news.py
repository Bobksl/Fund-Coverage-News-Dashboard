"""Scheduled news refresh: fetch feeds, apply the keyword rule, brief with DeepSeek, publish cards.

Runs twice each weekday from .github/workflows/refresh.yml, or by hand:

    python -m tools.fetch_news --dry-run    # fetch and filter only: no model calls, no writes
    python -m tools.fetch_news              # add new unreviewed cards to public/data

Feeds and the rule live in config/filter_rules.json. Google News is used for discovery only; each
card links to the article it points at. New cards are marked unreviewed. A failed refresh records
its status and never removes published cards. Items the model rejects are remembered for two weeks
in public/data/seen.json so later runs do not pay to brief them again.
"""
import argparse
import email.utils
import functools
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree

from tools import news_events, site_data, source_evidence, summarize

USER_AGENT = "Mozilla/5.0 (compatible; FundCoverageNews/1.0; +https://github.com/Bobksl/Fund-Coverage-News-Dashboard)"
SEEN_FILE = "seen.json"
TIERS_PATH = site_data.ROOT / "config" / "source_tiers.json"
PRIMARY_ORIGINS = ("issuer_filing", "regulator")
ATOM = "{http://www.w3.org/2005/Atom}"
SEEN_DAYS = 14
HTML_TAG = re.compile(r"<[^>]+>")
STOPWORDS = frozenset(["a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "is", "its", "of",
                       "on", "or", "the", "to", "with", "after", "amid", "over", "s"])
SIMILAR_TITLES = 0.5


def http_get(url, timeout=20):
    agent = source_evidence.user_agent(urllib.parse.urlsplit(url).hostname or "")
    request = urllib.request.Request(url, headers={
        "User-Agent": agent, "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def feed_urls(rules):
    """Yield (feed_id, url) for every Google News query and plain RSS feed in the rules."""
    google = rules["feeds"]["google_news"]
    for number, query in enumerate(google["queries"], 1):
        params = {"q": f"{query['q']} {google['lookback']}", **google["editions"][query["edition"]]}
        yield f"google_news_{number}", f"{google['endpoint']}?{urllib.parse.urlencode(params)}"
    for feed in rules["feeds"].get("rss", []):
        yield feed["id"], feed["url"]


def clean_html(value):
    text = HTML_TAG.sub(" ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_feed(data):
    """Parse RSS 2.0 bytes into entries with title, url, publisher, published and description."""
    channel = ElementTree.fromstring(data).find("channel")
    if channel is None:
        raise ValueError("not an RSS 2.0 feed")
    channel_title = clean_html(channel.findtext("title"))
    entries = []
    for node in channel.findall("item"):
        title = clean_html(node.findtext("title"))
        url = (node.findtext("link") or "").strip()
        source = node.find("source")
        publisher = clean_html(source.text) if source is not None and source.text else channel_title
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(f" - {publisher}")].strip()
        try:
            published = email.utils.parsedate_to_datetime(node.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        description = clean_html(node.findtext("description"))
        if title and description.startswith(title):
            description = ""  # Google News descriptions only repeat the headline and publisher.
        if title and url:
            entries.append({"title": title, "url": url, "publisher": publisher or "Unknown source",
                            "published": published, "description": description})
    return entries


def parse_edgar(data, registrant):
    """Parse one registrant's EDGAR company Atom feed into filing entries (index page as the URL)."""
    root = ElementTree.fromstring(data)
    entries = []
    for node in root.iter(ATOM + "entry"):
        category = node.find(ATOM + "category")
        link = node.find(ATOM + "link")
        content = node.find(ATOM + "content")
        form = category.get("term") if category is not None else ""
        items = (content.findtext(ATOM + "items-desc") if content is not None else "") or ""
        try:
            published = datetime.fromisoformat(node.findtext(ATOM + "updated") or "").astimezone(timezone.utc)
        except ValueError:
            continue
        if form and link is not None and link.get("href"):
            title = f"{registrant['name']} files {form}" + (f": {items}" if items else "")
            entries.append({"title": title, "url": link.get("href"), "publisher": registrant["name"],
                            "published": published, "description": "", "form": form})
    return entries


def parse_sitemap(data, feed):
    """Official sitemap -> release entries under include_prefix. lastmod is a modification time, so
    entries are labelled sitemap_lastmod until the page's own created date replaces it."""
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    entries = []
    for node in ElementTree.fromstring(data).iter(ns + "url"):
        url, lastmod = (node.findtext(ns + "loc") or "").strip(), (node.findtext(ns + "lastmod") or "").strip()
        if not url.startswith(feed["include_prefix"]) or not lastmod:
            continue
        try:
            published = datetime.fromisoformat(lastmod.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            continue
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        release = re.match(r"(\d+-\d+mr)-(.+)", slug)  # e.g. 26-225mr-asic-halts-offers-...
        number, words = (release.group(1).upper() + ":", release.group(2)) if release else (":", slug)
        title = f"{feed['publisher']} {number} {words.replace('-', ' ')}".replace(" :", ":")
        entries.append({"title": title, "url": url, "publisher": feed["publisher"], "published": published,
                        "description": "", "published_basis": "sitemap_lastmod"})
    return entries


def primary_feeds(primary, environ):
    """Yield (feed_id, url, parse, extra fields) for the primary tier; SEC needs a declared contact."""
    skipped = []
    for feed in primary.get("regulator_feeds", []):
        yield feed["id"], feed["url"], parse_feed, {"origin": "regulator", "domains": feed["domains"]}
    for feed in primary.get("regulator_sitemaps", []):
        yield (feed["id"], feed["url"], functools.partial(parse_sitemap, feed=feed),
               {"origin": "regulator", "domains": feed["domains"]})
    # Wire releases are issuer-origin: what the company said, not independent or primary confirmation.
    for feed in primary.get("wire_feeds", []):
        yield feed["id"], feed["url"], parse_feed, {"origin": "wire", "domains": feed["domains"]}
    sec = primary.get("sec_edgar")
    if sec and not environ.get(sec["contact_env"], "").strip():
        skipped.append(f"sec_edgar: {sec['contact_env']} not set")
    elif sec:
        for registrant in sec["registrants"]:
            yield (f"sec_{registrant['id']}", sec["feed"].format(cik=registrant["cik"]),
                   functools.partial(parse_edgar, registrant=registrant),
                   {"origin": "issuer_filing", "domains": sec["domains"], "gps": registrant["gps"],
                    "forms": sec["forms"]})
    gdelt = primary.get("gdelt")
    for query in gdelt["queries"] if gdelt else []:
        yield (f"gdelt_{query['id']}", gdelt_url(gdelt, query, primary.get("_lookback_days", 3)), parse_gdelt,
               {"pace": gdelt["min_interval_s"], "retry": gdelt["retry_after_s"]})
    yield from (("skipped", reason, None, None) for reason in skipped)


class RateLimited(RuntimeError):
    """A discovery API asked us to slow down; retried once, then recorded as a feed failure."""


def gdelt_url(gdelt, query, lookback_days):
    params = {"query": query["q"], "mode": "artlist", "format": "json", "maxrecords": gdelt["maxrecords"],
              "timespan": f"{lookback_days}d"}
    return f"{gdelt['endpoint']}?{urllib.parse.urlencode(params)}"


def clean_gdelt_title(title):
    # GDELT tokenises titles ("$2 . 5 billion , says"); undo only that spacing.
    title = re.sub(r"(\d) \. (\d)", r"\1.\2", title)
    title = re.sub(r"\s+([.,%:;!?)\]])", r"\1", title)
    return " ".join(re.sub(r"([(\[$])\s+", r"\1", title).split())


def parse_gdelt(data):
    """GDELT DOC artlist JSON -> entries with real publisher URLs. seendate is GDELT's first sighting."""
    body = data.lstrip()
    if body.startswith(b"Please limit requests"):
        raise RateLimited("GDELT rate limit")
    if not body.startswith(b"{"):
        # GDELT reports query problems as plain text; keep its words in the failure log.
        raise ValueError("GDELT: " + body[:120].decode("utf-8", "replace"))
    entries = []
    for article in json.loads(data).get("articles", []):
        try:
            seen = datetime.strptime(article["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            continue
        if article.get("url", "").startswith(("https://", "http://")) and article.get("title"):
            entries.append({"title": clean_gdelt_title(article["title"]), "url": article["url"],
                            "publisher": article.get("domain") or "Unknown source", "published": seen,
                            "description": "", "discovery": "gdelt", "published_basis": "gdelt_seen"})
    return entries


def title_key(title):
    """Headline identity across aggregators: normalised, without a trailing ' - Publisher' / ' | Publisher'."""
    return news_events.normalize_title(re.sub(r"\s[-|\u2013]\s[^-|\u2013]{1,40}$", "", title))


def primary_host(url, domains):
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in domains)


@functools.cache
def _pattern(term):
    # All-caps terms (KKR, PAG, CLO) match case-sensitively so "page" or "close" never count.
    flags = 0 if re.fullmatch(r"[A-Z0-9]+", term) else re.IGNORECASE
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", flags)


def _matches(text, terms):
    return [term for term in terms if _pattern(term).search(text)]


def rule_match(text, rules):
    """Apply the rule in config/filter_rules.json to one item's title and description."""
    credit = bool(_matches(text, rules["credit_context_keywords"]))

    def tagged(group):
        return [key for key, spec in rules[group].items()
                if _matches(text, spec["match"]) and (credit or not spec.get("credit_context_required"))]

    gps, sectors = tagged("gps"), tagged("sectors")
    excluded = _matches(text, rules["exclude_keywords"])
    if excluded:
        reason = f"excluded: {excluded[0]}"
    elif not (gps or sectors):
        reason = "no tracked manager or sub-sector"
    elif not _matches(text, rules["material_event_keywords"]):
        reason = "no material event"
    else:
        reason = "matched"
    return {"keep": reason == "matched", "gps": gps, "sectors": sectors, "reason": reason}


def title_words(title):
    words = [word for word in re.findall(r"[a-z0-9]+", title.lower()) if word not in STOPWORDS]
    return (words[0] if words else ""), frozenset(words)


def same_story(first, second):
    """Headlines from different outlets about one story: same lead word and half the words shared.

    Requiring the same lead word keeps "KKR raises $2bn credit fund" and "Apollo raises $2bn credit
    fund" apart even though most of their words match.
    """
    (lead_a, words_a), (lead_b, words_b) = first, second
    return bool(lead_a) and lead_a == lead_b and len(words_a & words_b) / len(words_a | words_b) >= SIMILAR_TITLES


def collect(rules, fetch, now, lookback_days, pause, primary=None, environ=None, sleep=time.sleep):
    """Fetch every feed; one failing feed is recorded and skipped. Paced feeds (GDELT) keep their own
    minimum interval and get one retry after a rate limit; pause=0 (tests) disables all sleeping."""
    oldest, newest = now - timedelta(days=lookback_days), now + timedelta(hours=1)
    stats = {"feeds_ok": 0, "feeds_failed": [], "feeds_skipped": [], "fetched": 0, "fresh": 0}
    entries = []
    feeds = [(feed_id, url, parse_feed, {}) for feed_id, url in feed_urls(rules)]
    feeds += list(primary_feeds(dict(primary or {}, _lookback_days=lookback_days),
                                os.environ if environ is None else environ))
    last_paced = None
    for number, (feed_id, url, parse, extra) in enumerate(feeds):
        if feed_id == "skipped":
            stats["feeds_skipped"].append(url)
            continue
        extra = dict(extra)
        interval, retry = extra.pop("pace", None), extra.pop("retry", None)
        if number and pause:
            sleep(max(interval - (time.monotonic() - last_paced), 0) if interval and last_paced else pause)
        try:
            for attempt in (1, 2):
                try:
                    parsed = parse(fetch(url))
                    break
                except (RateLimited, urllib.error.HTTPError) as error:
                    limited = isinstance(error, RateLimited) or error.code == 429
                    if not (interval and limited and attempt == 1):
                        raise
                    if pause:
                        sleep(retry)
                finally:
                    if interval:
                        last_paced = time.monotonic()
        except Exception as error:  # noqa: BLE001 -- any network or parse failure is per-feed
            stats["feeds_failed"].append(f"{feed_id}: {type(error).__name__}: {str(error)[:120]}")
            continue
        stats["feeds_ok"] += 1
        stats["fetched"] += len(parsed)
        forms = extra.pop("forms", None) if extra else None
        entries.extend(dict(entry, feed=feed_id, **extra) for entry in parsed
                       if oldest <= entry["published"] <= newest and (forms is None or entry.get("form") in forms))
    stats["fresh"] = len(entries)
    return entries, stats


def select(entries, rules, known_ids, known_sources=None, rejected=None):
    """Retain different-source coverage; event grouping happens after validated card creation.

    Fingerprinted same-URL changes may pass as revisions. Legacy cards without fingerprints
    retain the original skip behavior because no prior source bytes exist for comparison.
    Items failing the keyword rule are appended to `rejected` when a list is given.
    """
    known_sources = known_sources or {}
    seen_versions, candidates, unique = set(), [], 0
    # An opaque Google News link loses to the same headline found with its real URL by GDELT.
    real_urls = {title_key(entry["title"]) for entry in entries if entry.get("discovery") == "gdelt"}
    entries = [entry for entry in entries
               if not (entry.get("feed", "").startswith("google_news") and title_key(entry["title"]) in real_urls)]
    for entry in sorted(entries, key=lambda item: item["published"], reverse=True):
        entry_id = site_data.card_id(entry["url"])
        fingerprint = summarize.source_fingerprint(to_item(entry))
        versions = known_sources.get(entry_id, {})
        if (entry_id, fingerprint) in seen_versions or fingerprint in versions:
            continue
        if entry_id in known_ids and not versions:
            continue
        seen_versions.add((entry_id, fingerprint))
        unique += 1
        if entry.get("origin") == "issuer_filing":
            # The registrant is a tracked vehicle and the form is in scope; the brief judges materiality.
            match = {"keep": True, "gps": entry["gps"], "sectors": [], "reason": "primary filing"}
        else:
            match = rule_match(f"{entry['title']} {entry['description']}", rules)
            if entry.get("origin") == "regulator" and match["reason"] == "no material event":
                # A regulator's own release is itself a regulatory action or statement; the sector
                # or manager match is still required.
                match = dict(match, keep=True, reason="regulator release")
        if match["keep"]:
            candidates.append(dict(entry, match=match, revision_of=next(reversed(versions.values()), None)))
        elif rejected is not None:
            rejected.append({"published": entry["published"].isoformat(), "publisher": entry["publisher"],
                             "title": entry["title"], "url": entry["url"], "reason": match["reason"]})
    return candidates, unique


def load_seen(data_dir, now):
    path = Path(data_dir) / SEEN_FILE
    seen = json.loads(path.read_text(encoding="utf-8")).get("ids", {}) if path.exists() else {}
    cutoff = (now - timedelta(days=SEEN_DAYS)).date().isoformat()
    return {key: day for key, day in seen.items() if day >= cutoff}


def to_item(candidate):
    published = candidate["published"]
    return {"title": candidate["title"], "publisher": candidate["publisher"], "url": candidate["url"],
            "date": published.astimezone(site_data.HKT).date().isoformat(),
            "published_at": published.isoformat(timespec="seconds"),
            "text": candidate["description"] or candidate["title"],
            **({"origin": candidate["origin"],
                "verified_primary_source": candidate["origin"] in PRIMARY_ORIGINS
                and primary_host(candidate["url"], candidate.get("domains", []))}
               if candidate.get("origin") else {}),
            **({"context": f"Primary source: SEC {candidate['form']} filed by {candidate['publisher']}."}
               if candidate.get("origin") == "issuer_filing" else {}),
            **({"published_basis": candidate["published_basis"]} if candidate.get("published_basis") else {})}


def gather_evidence(item, retrieve):
    """Swap the feed line for a retrieved excerpt when one exists; always record provenance.

    Any retrieval failure leaves the feed text in place: the brief then stays headline-level
    and its priority unassessed, rather than the refresh failing.
    """
    try:
        if item.get("origin") == "issuer_filing":
            # The feed links the filing index; read the press-release exhibit or the form itself.
            index = retrieve(item["url"], keep_html=True)
            document = source_evidence.edgar_document(index.get("html", ""), index.get("final_url") or item["url"])
            record = retrieve(document) if document else index
        else:
            record = retrieve(item["url"])
    except Exception as error:  # noqa: BLE001 -- evidence is optional; never fail a refresh on it
        record = {"status": "error", "level": "headline_only", "detail": type(error).__name__,
                  "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    item["feed_text"] = item["text"]
    if record.get("level") == "excerpt" and len(record.get("excerpt") or "") > len(item["text"]):
        item["text"] = record["excerpt"]
    item["evidence_level"] = "excerpt" if item["text"] != item["feed_text"] else "headline_only"
    if record.get("source_published_at"):
        item["source_published_at"] = record["source_published_at"]
    item["evidence"] = dict(source_evidence.provenance(record), level=item["evidence_level"])
    return record["status"]


def run(rules, data_dir=site_data.DATA_DIR, fetch=http_get, post=None, now=None, max_items=30,
        max_calls=60, lookback_days=3, dry_run=False, pause=1.0, scheduled=False, retrieve=None,
        max_fetches=30, tiers=None, environ=None, sleep=None):
    """One refresh. Returns (exit_code, stats).

    `retrieve` (url -> evidence record) is off unless given; main() passes the bounded
    source_evidence retriever. At most `max_fetches` pages are requested per run. `tiers` is
    config/source_tiers.json (primary filings, regulators, GDELT; off unless given); SEC feeds need
    SEC_CONTACT_EMAIL.
    """
    now = now or datetime.now(timezone.utc)
    entries, stats = collect(rules, fetch, now, lookback_days, pause, tiers, environ, sleep or time.sleep)
    seen = load_seen(data_dir, now)
    existing = [card for day in site_data._day_files(data_dir) for card in site_data.load_day(data_dir, day)]
    known_sources = {}
    for card in sorted(existing, key=lambda c: c.get('observed_at') or c.get('published_at') or c['date']):
        if card.get('source_fingerprint'):
            known_sources.setdefault(site_data.card_id(card['source']['url']), {})[card['source_fingerprint']] = card['id']
    rule_rejected = [] if dry_run else None
    candidates, stats["after_dedupe"] = select(entries, rules, site_data.existing_ids(data_dir) | set(seen),
                                               known_sources, rule_rejected)
    stats["rule_passed"] = len(candidates)
    # Primary records first: the item cap must never drop a filing in favour of its syndicated copies.
    candidates.sort(key=lambda item: item.get("origin") not in PRIMARY_ORIGINS)
    candidates = candidates[:max_items]
    if dry_run:
        stats["candidates"] = [{"published": item["published"].isoformat(), "publisher": item["publisher"],
                                "title": item["title"], "gps": item["match"]["gps"],
                                "sectors": item["match"]["sectors"], "origin": item.get("origin", "news")}
                               for item in candidates]
        # Rule rejections for prospective recall audits; model rejections need paid calls and are not here.
        stats["rule_rejected"] = rule_rejected
        return 0, stats

    errors, failure = [], None
    if stats["feeds_ok"] == 0:
        failure = "every feed failed"
    elif candidates and post is None:
        try:
            summarize.load_api_key()
        except summarize.SummaryError as error:
            failure = str(error)
    summarizer = summarize.Summarizer(rules, post=post, max_calls=max_calls)
    cards, rejected, evidence, stale = [], 0, {}, 0
    for candidate in [] if failure else candidates:
        item = to_item(candidate)
        if retrieve is not None:
            if sum(evidence.values()) < max_fetches:
                status = gather_evidence(item, retrieve)
            else:
                status = "skipped_cap"
                item["feed_text"], item["evidence_level"] = item["text"], "headline_only"
                item["evidence"] = {"status": status, "level": "headline_only"}
            evidence[status] = evidence.get(status, 0) + 1
        if item.get("published_basis") == "sitemap_lastmod" and item.get("source_published_at"):
            created = item["source_published_at"][:10]
            if created < (now - timedelta(days=lookback_days)).date().isoformat():
                # An old release that was merely edited: not news, and not worth a brief.
                stale += 1
                seen[site_data.card_id(item["url"])] = now.date().isoformat()
                continue
            item.update(published_at=created, date=created, published_basis="page_created_date")
        try:
            brief = summarizer(item)
            card = summarize.make_card(item, brief, "unreviewed", "auto_fetch")
            card['observed_at'] = now.isoformat(timespec='seconds')
            if candidate.get('origin') == 'issuer_filing':
                card['gps'] = list(dict.fromkeys(card['gps'] + candidate['gps']))
            if candidate.get('revision_of'):
                card['supersedes_card_id'] = candidate['revision_of']
                card['id'] = hashlib.sha256((card['id'] + card['source_fingerprint']).encode()).hexdigest()[:12]
                # A correction discovered later belongs to the observation day, never a past edition.
                card['date'] = now.astimezone(site_data.HKT).date().isoformat()
            if not brief["relevant"] or not (card["gps"] or card["sectors"]):
                rejected += 1
                seen[card["id"]] = now.date().isoformat()
                continue
            site_data.validate_card(card, rules)
        except (summarize.SummaryError, ValueError) as error:
            errors.append(f"{item['title'][:60]}: {str(error)[:120]}")
            if summarizer.calls >= summarizer.max_calls:
                break
            continue
        cards.append(card)

    added = site_data.add_cards(cards, rules, data_dir, now=now)
    site_data._write_json(Path(data_dir) / SEEN_FILE, {"ids": seen})
    result = "failed" if failure else ("succeeded" if added else "no_new_items")
    detail = (f"{stats['feeds_ok']} feeds ok, {len(stats['feeds_failed'])} failed; {len(candidates)} matched "
              f"the rule; {len(added)} added; {rejected} rejected by the model")
    site_data.write_status(data_dir, mode="scheduled" if scheduled else "manual", schedule=rules["schedule"],
                           result=result, new_items=len(added),
                           detail=f"{failure}; {detail}" if failure else detail, now=now)
    added_cards = [card for card in cards if card["id"] in set(added)]
    stats.update(briefed=0 if failure else len(candidates), model_rejected=rejected, added=len(added),
                 europe_share=(round(sum(card["region"] == "Europe" for card in added_cards) / len(added_cards), 2)
                               if added_cards else None),
                 calls=summarizer.calls, usage=summarizer.usage, errors=errors[:5], failure=failure,
                 evidence=evidence, stale_skipped=stale)
    return (1 if failure else 0), stats


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="fetch and filter only; no model calls or writes")
    parser.add_argument("--data-dir", type=Path, default=site_data.DATA_DIR)
    parser.add_argument("--max-items", type=int, default=30)
    parser.add_argument("--max-calls", type=int, default=60)
    parser.add_argument("--lookback-days", type=int, default=3)
    args = parser.parse_args(argv)
    code, stats = run(site_data.load_rules(), data_dir=args.data_dir, max_items=args.max_items,
                      max_calls=args.max_calls, lookback_days=args.lookback_days, dry_run=args.dry_run,
                      scheduled=os.environ.get("GITHUB_ACTIONS") == "true",
                      retrieve=functools.partial(source_evidence.retrieve, cache_dir=source_evidence.CACHE_DIR),
                      tiers=json.loads(TIERS_PATH.read_text(encoding="utf-8")))
    print(json.dumps(stats, ensure_ascii=False, indent=2, default=str))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
