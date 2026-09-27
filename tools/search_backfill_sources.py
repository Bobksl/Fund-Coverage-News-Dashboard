"""Find candidate publisher URLs for archived Google News cards with capped Brave searches.

Results stay in work/ for review. Search snippets are never published, and no URL is
accepted as article evidence until the bounded retriever reads its page.
"""
import argparse
import ipaddress
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from tools import backfill, news_events, site_data, summarize

ENDPOINT = 'https://api.search.brave.com/res/v1/web/search'
OUTPUT = site_data.ROOT / 'work' / 'brave-candidates.json'
MAX_RESPONSE_BYTES = 1_000_000


def search(title, key, *, open_url=urllib.request.urlopen):
    query = urllib.parse.urlencode({'q': f'"{title[:350]}"', 'count': 5})
    request = urllib.request.Request(ENDPOINT + '?' + query,
                                     headers={'X-Subscription-Token': key, 'Accept': 'application/json'})
    with open_url(request, timeout=15) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('Search response exceeded size cap')
    return json.loads(raw).get('web', {}).get('results', [])


def candidates(card, results):
    wanted = set(backfill.words(card.get('source_headline') or card['headline']['en']))
    found = []
    for result in results:
        url, title = result.get('url'), result.get('title')
        if not isinstance(url, str) or not isinstance(title, str):
            continue
        parts = urlsplit(url)
        host = (parts.hostname or '').lower()
        try:
            literal_ip = ipaddress.ip_address(host)
        except ValueError:
            literal_ip = None
        if (parts.scheme not in ('http', 'https') or parts.username or parts.password or
                host in ('localhost', 'news.google.com') or
                (literal_ip is not None and not literal_ip.is_global) or
                any(host == b or host.endswith('.' + b) for b in backfill.BLOCKED)):
            continue
        score = len(wanted & set(backfill.words(title))) / max(1, len(wanted))
        if score >= 0.8:
            found.append({'url': url, 'title': title, 'publisher': host, 'score': round(score, 3)})
    return sorted(found, key=lambda result: result['score'], reverse=True)[:3]


def cards_to_search(data_dir):
    data_dir = Path(data_dir)
    side = backfill.load(data_dir)['cards']
    cards = [c for day in site_data._day_files(data_dir) for c in site_data.load_day(data_dir, day)]
    reviewed = json.loads((site_data.ROOT / 'config' / 'reviewed_source_links.json').read_text(encoding='utf-8'))
    return [c for c in cards if 'news.google.com' in c['source']['url']
            and not (c.get('assessment') or {}).get('assessable')
            and not ((side.get(c['id']) or {}).get('card_sha256') == news_events.card_hash(c)
                     and ((side.get(c['id']) or {}).get('assessment') or {}).get('assessable'))
            and not (c['id'] in reviewed and reviewed[c['id']].get('card_sha256') == news_events.card_hash(c))]


def run(data_dir, *, key, max_searches=10, search_fn=search, previous=None):
    if not 0 <= max_searches <= 160:
        raise ValueError('max_searches must be between 0 and 160')
    results = dict((previous or {}).get('results') or {})
    errors = []
    queue = [card for card in cards_to_search(data_dir) if card['id'] not in results]
    attempted = 0
    consecutive_errors = 0
    for card in queue[:max_searches]:
        attempted += 1
        title = card.get('source_headline') or card['headline']['en']
        try:
            results[card['id']] = candidates(card, search_fn(title, key))
            consecutive_errors = 0
        except urllib.error.HTTPError as error:
            errors.append({'card_id': card['id'], 'error': f'HTTP {error.code}'})
            if error.code == 429:
                break
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append({'card_id': card['id'], 'error': type(error).__name__})
            consecutive_errors += 1
            if consecutive_errors >= 3:
                break
    new_results = len(results) - len((previous or {}).get('results') or {})
    return {'searched': len(results), 'attempted_this_run': attempted,
            'remaining': max(0, len(queue) - new_results),
            'matches': sum(bool(v) for v in results.values()), 'results': results, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data-dir', type=Path, default=site_data.DATA_DIR)
    parser.add_argument('--max-searches', type=int, default=10)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    key = summarize.load_api_key('BRAVE_SEARCH_API_KEY')
    previous = json.loads(args.output.read_text(encoding='utf-8')) if args.output.exists() else None
    report = run(args.data_dir, key=key, max_searches=args.max_searches, previous=previous)
    site_data._write_json(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
