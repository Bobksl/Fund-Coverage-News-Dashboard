"""Check Brave URL candidates against the bounded source retriever; keep results local."""
import argparse
import functools
import json
from datetime import date
from pathlib import Path

from tools import backfill, news_events, site_data, source_evidence

INPUT = site_data.ROOT / 'work' / 'brave-candidates.json'
OUTPUT = site_data.ROOT / 'work' / 'source-verification.json'


def overlap(wanted, found):
    wanted_words = set(backfill.words(wanted))
    return len(wanted_words & set(backfill.words(found))) / max(1, len(wanted_words))


def check(card, options, retrieve):
    headline = card.get('source_headline') or card['headline']['en']
    attempts = []
    for option in options[:3]:
        record = retrieve(option['url'])
        page_title = record.get('title') or ''
        title_score = overlap(headline, page_title)
        published = record.get('source_published_at')
        date_ok = None
        if published:
            try:
                date_ok = abs((date.fromisoformat(published[:10]) - date.fromisoformat(card['date'])).days) <= 7
            except ValueError:
                date_ok = False
        status = ('verified' if record.get('level') == 'excerpt' and title_score >= 0.8 and date_ok is True
                  else 'review_date' if record.get('level') == 'excerpt' and title_score >= 0.8 and date_ok is None
                  else 'mismatch' if record.get('level') == 'excerpt' else record.get('status', 'error'))
        attempt = {'url': option['url'], 'title': option['title'], 'publisher': option['publisher'],
                   'status': status, 'page_title_score': round(title_score, 3),
                   'source_published_at': published, 'source_sha256': record.get('sha256')}
        attempts.append(attempt)
        if status == 'verified':
            return {'card_sha256': news_events.card_hash(card), 'best': attempt, 'attempts': attempts}
    return {'card_sha256': news_events.card_hash(card), 'best': None, 'attempts': attempts}


def run(data_dir, candidates, *, retrieve, max_cards=20, previous=None, output=None):
    if not 0 <= max_cards <= 160:
        raise ValueError('max_cards must be between 0 and 160')
    data_dir = Path(data_dir)
    cards = {c['id']: c for day in site_data._day_files(data_dir) for c in site_data.load_day(data_dir, day)}
    results = dict((previous or {}).get('results') or {})
    queue = [(cid, options) for cid, options in candidates['results'].items()
             if options and cid in cards and cid not in results]
    for cid, options in queue[:max_cards]:
        results[cid] = check(cards[cid], options, retrieve)
        if output:
            site_data._write_json(output, {'results': results})
    return {'checked': len(results), 'remaining': max(0, len(queue) - max_cards),
            'verified': sum(bool(item['best']) for item in results.values()), 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data-dir', type=Path, default=site_data.DATA_DIR)
    parser.add_argument('--max-cards', type=int, default=20)
    parser.add_argument('--input', type=Path, default=INPUT)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    candidates = json.loads(args.input.read_text(encoding='utf-8'))
    previous = json.loads(args.output.read_text(encoding='utf-8')) if args.output.exists() else None
    report = run(args.data_dir, candidates,
                 retrieve=functools.partial(source_evidence.retrieve, cache_dir=source_evidence.CACHE_DIR),
                 max_cards=args.max_cards, previous=previous, output=args.output)
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}))


if __name__ == '__main__':
    main()
