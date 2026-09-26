"""Re-brief archived cards from retrievable source text into public/data/backfill.json. Paid; capped.

Day files are never rewritten: each entry is bound to its card's hash, so an edited card falls back to its
original text. Google News links are skipped (not decodable). A card whose page cannot be read is recorded
with its evidence status and not retried until the card changes. Same prompt, model and validation as the
scheduled refresh. Run:

    python -m tools.backfill --data-dir public/data --max-cards 100
"""
import argparse
import functools
import json
from datetime import datetime, timezone
from pathlib import Path

from tools import fetch_news, news_events, site_data, source_evidence, summarize

FILE = 'backfill.json'
# Raw model answers stay local (never published) so failed validations can be diagnosed without new calls.
CACHE = source_evidence.CACHE_DIR / 'briefs.json'


def load(data_dir):
    path = Path(data_dir) / FILE
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'version': 1, 'cards': {}}


def run(data_dir, rules, *, retrieve, post=None, max_cards=100, now=None, retry_unassessed=False, cache_path=None,
        rebrief_older_prompt=False):
    now = now or datetime.now(timezone.utc)
    data_dir = Path(data_dir)
    side = load(data_dir)
    cards = [c for day in site_data._day_files(data_dir) for c in site_data.load_day(data_dir, day)]

    def settled(card):
        entry = side['cards'].get(card['id'])
        if entry is None or entry.get('card_sha256') != news_events.card_hash(card):
            return False
        failed = 'assessment' in entry and not entry['assessment'].get('assessable')
        older = 'assessment' in entry and entry.get('prompt_version') != summarize.PROMPT_VERSION
        return not ((retry_unassessed and failed) or (rebrief_older_prompt and older))

    todo = [c for c in cards if not (c.get('assessment') or {}).get('assessable')
            and 'news.google.com' not in c['source']['url'] and not settled(c)]
    summarizer = summarize.Summarizer(rules, post=post, max_calls=2 * max_cards, cache_path=cache_path)
    stats = {'candidates': len(todo), 'updated': 0, 'no_evidence': 0, 'errors': []}
    for card in todo[:max_cards]:
        url = card['source']['url']
        title = card.get('source_headline') or card['headline']['en']
        item = {'title': title, 'publisher': card['source']['publisher'], 'url': url, 'date': card['date'],
                'published_at': card.get('published_at'), 'text': title}
        if url.endswith('-index.htm') and fetch_news.primary_host(url, ['sec.gov']):
            # An EDGAR filing index: read the press-release exhibit or the form; the filing is primary evidence.
            item.update(origin='issuer_filing', verified_primary_source=True)
        status = fetch_news.gather_evidence(item, retrieve)
        entry = {'card_sha256': news_events.card_hash(card), 'status': status,
                 'checked_at': now.isoformat(timespec='seconds'), 'evidence': item['evidence']}
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
            entry.update(headline=new['headline'], summary=new['summary'], assessment=new['assessment'],
                         relevant=brief['relevant'], relevance_reason=brief['reason'],
                         prompt_version=summarize.PROMPT_VERSION, model=summarize.MODEL_ID)
            stats['updated'] += 1
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
    args = parser.parse_args()
    stats = run(args.data_dir, site_data.load_rules(), max_cards=args.max_cards,
                retry_unassessed=args.retry_unassessed, rebrief_older_prompt=args.rebrief_older_prompt, cache_path=CACHE,
                retrieve=functools.partial(source_evidence.retrieve, cache_dir=source_evidence.CACHE_DIR))
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
