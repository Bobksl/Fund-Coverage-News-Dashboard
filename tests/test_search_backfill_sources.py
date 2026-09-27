"""Brave candidate discovery is capped and never promotes search snippets into evidence."""
from tests.test_backfill import GN, archive, card
from tools import search_backfill_sources


def test_search_candidates_require_strong_title_overlap_and_public_web_urls():
    c = card('0000000000n1', GN, source_headline='CIFC launches direct lending strategy on iCapital Marketplace')
    results = [
        {'url': 'https://example.com/cifc', 'title': c['source_headline']},
        {'url': 'https://news.google.com/a', 'title': c['source_headline']},
        {'url': 'https://example.com/other', 'title': 'Apollo raises a third private credit fund'},
        {'url': 'https://example.com@127.0.0.1/a', 'title': c['source_headline']},
        {'url': 'https://127.0.0.1/a', 'title': c['source_headline']},
    ]
    assert [item['url'] for item in search_backfill_sources.candidates(c, results)] == ['https://example.com/cifc']


def test_search_run_obeys_call_cap_and_writes_no_public_file(tmp_path):
    cards = [card(f'0000000000n{i}', GN + str(i), source_headline=f'CIFC launches direct lending strategy number {i}')
             for i in range(3)]
    data = archive(tmp_path, cards)
    before = (data / '2026-09-17.json').read_bytes()
    calls = []

    def fake(title, key):
        calls.append((title, key))
        return [{'url': 'https://example.com/cifc', 'title': title}]

    report = search_backfill_sources.run(data, key='private-test-key', max_searches=2, search_fn=fake)
    assert len(calls) == 2 and report['searched'] == 2 and report['remaining'] == 1
    assert report['matches'] == 2 and (data / '2026-09-17.json').read_bytes() == before
    assert not (data / 'backfill.json').exists()
    resumed = search_backfill_sources.run(data, key='private-test-key', max_searches=2, search_fn=fake,
                                          previous=report)
    assert resumed['attempted_this_run'] == 1 and resumed['searched'] == 3
