"""Only readable, matching, date-aligned pages become verified source leads."""
from tests.test_backfill import GN, archive, card
from tools import verify_backfill_sources


def test_source_candidate_verification_requires_page_title_and_date():
    c = card('0000000000v1', GN, source_headline='CIFC launches direct lending strategy on iCapital Marketplace')
    options = [{'url': 'https://example.com/wrong', 'title': c['source_headline'], 'publisher': 'example.com'},
               {'url': 'https://example.com/right', 'title': c['source_headline'], 'publisher': 'example.com'}]

    def retrieve(url):
        return {'status': 'ok', 'level': 'excerpt', 'title': 'Different article' if url.endswith('wrong') else c['source_headline'],
                'source_published_at': '2026-09-17T12:00:00+00:00', 'sha256': 'hash'}

    result = verify_backfill_sources.check(c, options, retrieve)
    assert result['best']['url'].endswith('right') and len(result['attempts']) == 2


def test_source_candidate_verification_rejects_old_article_and_is_resumable(tmp_path):
    c = card('0000000000v2', GN, source_headline='CIFC launches direct lending strategy on iCapital Marketplace')
    data = archive(tmp_path, [c])
    candidates = {'results': {c['id']: [{'url': 'https://example.com/old', 'title': c['source_headline'],
                                         'publisher': 'example.com'}]}}
    calls = []

    def retrieve(url):
        calls.append(url)
        return {'status': 'ok', 'level': 'excerpt', 'title': c['source_headline'],
                'source_published_at': '2025-09-17T12:00:00+00:00', 'sha256': 'hash'}

    report = verify_backfill_sources.run(data, candidates, retrieve=retrieve, max_cards=1)
    assert report['checked'] == 1 and report['verified'] == 0 and len(calls) == 1
    resumed = verify_backfill_sources.run(data, candidates, retrieve=retrieve, max_cards=1, previous=report)
    assert resumed['checked'] == 1 and len(calls) == 1
