"""Re-brief archived cards from retrievable source text into public/data/backfill.json. Paid; capped.

Day files are never rewritten: each entry is bound to its card's hash, so an edited card falls back to its
original text. A card whose page cannot be read is recorded with its evidence status and not retried until
the card changes. Same prompt, model and validation as the scheduled refresh.

Google News links cannot be decoded. With --gdelt, one such card per still-unassessed event is looked up
in GDELT by its headline's distinctive words (+/- 3 days); a result is used only if its title closely matches
the headline and its site is not a known paywall. Unmatched cards are not recorded, so a later run retries.
Run:

    python -m tools.backfill --data-dir public/data --max-cards 100 [--gdelt]
"""
import argparse
import functools
import json
import re
import time
import urllib.error
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tools import fetch_news, news_events, site_data, source_evidence, summarize

FILE = 'backfill.json'
# Raw model answers stay local (never published) so failed validations can be diagnosed without new calls.
CACHE = source_evidence.CACHE_DIR / 'briefs.json'
GDELT = 'https://api.gdeltproject.org/api/v2/doc/doc'
GDELT_INTERVAL_S, GDELT_RETRY_S = 10, 15
MATCH = 0.6  # share of the headline's distinctive words the found title must contain
# Sites that refused automated reads in testing; a syndicated copy elsewhere is preferred.
BLOCKED = ('bloomberg.com', 'wsj.com', 'ft.com', 'investing.com', 'reuters.com', 'barrons.com', 'connectmoney.com',
           'scanx.trade')
STOP = {'the', 'a', 'an', 'and', 'of', 'to', 'for', 'in', 'on', 'at', 'by', 'with', 'from', 'as', 'its', 'is',
        'are', 'be', 'after', 'over', 'into', 'amid', 'new', 'says', 'said', 'this', 'that', 'than', 'more', 'up',
        'down', 'could', 'may', 'will', 'has', 'have'}


def load(data_dir):
    path = Path(data_dir) / FILE
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'version': 1, 'cards': {}}


def words(title):
    return [w for w in re.findall(r"[a-z][a-z'.-]+", title.lower()) if w not in STOP and len(w) > 2]


def gdelt_query(card):
    day = date.fromisoformat(card['date'])
    keys = sorted(set(words(card.get('source_headline') or card['headline']['en'])), key=len, reverse=True)[:5]
    return GDELT + '?' + urllib.parse.urlencode({
        'query': ' '.join(keys) + ' sourcelang:english', 'mode': 'artlist', 'format': 'json', 'maxrecords': 50,
        'startdatetime': (day - timedelta(days=3)).strftime('%Y%m%d000000'),
        'enddatetime': (day + timedelta(days=3)).strftime('%Y%m%d235959')})


def ask_gdelt(gdelt, card):
    try:
        return fetch_news.parse_gdelt(gdelt(gdelt_query(card)))
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise fetch_news.RateLimited('HTTP 429') from error
        raise


def best_match(card, entries):
    wanted = set(words(card.get('source_headline') or card['headline']['en']))
    scored = [(len(wanted & set(words(e['title']))) / max(1, len(wanted)), e['url']) for e in entries
              if not any(e['publisher'] == b or e['publisher'].endswith('.' + b) for b in BLOCKED)]
    score, url = max(scored, default=(0, None))
    return url if score >= MATCH else None


def run(data_dir, rules, *, retrieve, post=None, max_cards=100, now=None, retry_unassessed=False, cache_path=None,
        rebrief_older_prompt=False, gdelt=None, sleep=time.sleep):
    now = now or datetime.now(timezone.utc)
    data_dir = Path(data_dir)
    side = load(data_dir)
    cards = [c for day in site_data._day_files(data_dir) for c in site_data.load_day(data_dir, day)]

    def verified(card):
        entry = side['cards'].get(card['id']) or {}
        return (card.get('assessment') or {}).get('assessable') or (
            (entry.get('assessment') or {}).get('assessable') and entry.get('card_sha256') == news_events.card_hash(card))

    def settled(card):
        entry = side['cards'].get(card['id'])
        if entry is None or entry.get('card_sha256') != news_events.card_hash(card):
            return False
        failed = 'assessment' in entry and not entry['assessment'].get('assessable')
        older = 'assessment' in entry and entry.get('prompt_version') != summarize.PROMPT_VERSION
        return not ((retry_unassessed and failed) or (rebrief_older_prompt and older))

    todo = [c for c in cards if not (c.get('assessment') or {}).get('assessable')
            and 'news.google.com' not in c['source']['url'] and not settled(c)]
    if gdelt is not None:
        # One Google-News card per event that has no verified assessment yet.
        events = news_events.build_events(cards, backfill=side)['events']
        by_id = {c['id']: c for c in cards}
        for event in sorted(events, key=lambda e: e['event_id']):
            members = [by_id[i] for i in event['member_card_ids']]
            if any(verified(m) for m in members):
                continue
            pick = next((m for m in sorted(members, key=lambda m: m['id'])
                         if 'news.google.com' in m['source']['url'] and not settled(m)), None)
            if pick:
                todo.append(pick)
    summarizer = summarize.Summarizer(rules, post=post, max_calls=2 * max_cards, cache_path=cache_path)
    stats = {'candidates': len(todo), 'updated': 0, 'no_evidence': 0, 'kept_previous': 0, 'resolved': 0,
             'unresolved': 0, 'gdelt_stopped': False, 'errors': []}
    asked = False
    for card in todo[:max_cards]:
        url = card['source']['url']
        resolved = None
        if 'news.google.com' in url:
            if stats['gdelt_stopped']:
                continue
            if asked:
                sleep(GDELT_INTERVAL_S)
            asked, found = True, None
            for attempt in (1, 2):
                try:
                    found = ask_gdelt(gdelt, card)
                    break
                except fetch_news.RateLimited:
                    if attempt == 2:
                        stats['gdelt_stopped'] = True  # GDELT is refusing us: stop, do not hammer it
                    else:
                        sleep(GDELT_RETRY_S)
                except (OSError, ValueError) as error:
                    stats['errors'].append(f"{card['id']}: GDELT {type(error).__name__}")
                    break
            resolved = best_match(card, found or [])
            if not resolved:
                if not stats['gdelt_stopped']:
                    stats['unresolved'] += 1
                continue
            stats['resolved'] += 1
        title = card.get('source_headline') or card['headline']['en']
        item = {'title': title, 'publisher': card['source']['publisher'], 'url': resolved or url, 'date': card['date'],
                'published_at': card.get('published_at'), 'text': title}
        if url.endswith('-index.htm') and fetch_news.primary_host(url, ['sec.gov']):
            # An EDGAR filing index: read the press-release exhibit or the form; the filing is primary evidence.
            item.update(origin='issuer_filing', verified_primary_source=True)
        status = fetch_news.gather_evidence(item, retrieve)
        entry = {'card_sha256': news_events.card_hash(card), 'status': status,
                 'checked_at': now.isoformat(timespec='seconds'), 'evidence': item['evidence']}
        if resolved:
            entry['resolved_url'] = resolved
        if item['evidence_level'] != 'excerpt':
            stats['no_evidence'] += 1
        else:
            try:
                brief = summarizer(item)
            except summarize.SummaryError as error:
                stats['errors'].append(f"{card['id']}: {str(error)[:120]}")  # not recorded: retried next run
                if summarizer.calls >= summarizer.max_calls:
                    break
                continue
            new = summarize.make_card(item, brief, card['review_status'], card['origin'])
            if not new['assessment'].get('assessable'):
                summarizer.forget(item)  # an unverified answer is not reused by a later retry
            entry.update(headline=new['headline'], summary=new['summary'], assessment=new['assessment'],
                         relevant=brief['relevant'], relevance_reason=brief['reason'],
                         prompt_version=summarize.PROMPT_VERSION, model=summarize.MODEL_ID)
            stats['updated'] += 1
        previous = side['cards'].get(card['id']) or {}
        if verified(card) and previous and not (entry.get('assessment') or {}).get('assessable'):
            # Answers vary between runs; a new answer that fails the evidence check never replaces a verified one.
            stats['kept_previous'] += 1
            if 'assessment' in entry:
                stats['updated'] -= 1
            continue
        side['cards'][card['id']] = entry
    side.update(version=1, generated_at=now.isoformat(timespec='seconds'))
    site_data._write_json(data_dir / FILE, side)
    news_events.write_events(data_dir, now=now)
    stats.update(calls=summarizer.calls, usage=summarizer.usage, remaining=max(0, len(todo) - max_cards))
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data-dir', type=Path, default=site_data.DATA_DIR)
    parser.add_argument('--max-cards', type=int, default=100)
    parser.add_argument('--retry-unassessed', action='store_true', help='re-brief entries whose assessment failed')
    parser.add_argument('--rebrief-older-prompt', action='store_true', help='re-brief entries from an older prompt version')
    parser.add_argument('--gdelt', action='store_true', help='look up Google News cards in GDELT (paced, best effort)')
    args = parser.parse_args()
    stats = run(args.data_dir, site_data.load_rules(), max_cards=args.max_cards,
                retry_unassessed=args.retry_unassessed, rebrief_older_prompt=args.rebrief_older_prompt, cache_path=CACHE,
                retrieve=functools.partial(source_evidence.retrieve, cache_dir=source_evidence.CACHE_DIR),
                gdelt=fetch_news.http_get if args.gdelt else None)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
