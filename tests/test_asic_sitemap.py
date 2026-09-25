"""ASIC media releases via the official sitemap: lastmod is modification, not publication. Fake HTTP."""
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tests.test_fetch_news import BRIEF, FakePost
from tools import fetch_news, site_data, source_evidence

NOW = datetime(2026, 9, 23, 2, 0, tzinfo=timezone.utc)
RULES = site_data.load_rules()
BASE = 'https://www.asic.gov.au/about-asic/news-centre/find-a-media-release/2026-releases/'
REMARA = BASE + '26-225mr-asic-halts-offers-of-private-credit-products-offered-under-remara-cash-management-fund'
OLD = BASE + '26-022mr-asic-sues-private-credit-fund-manager-over-valuations'
OTHER = BASE + '26-224mr-fundo-loans-pays-infringement-notice'
SITEMAP = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + ''.join(f'<url><loc>{u}</loc><lastmod>{m}</lastmod></url>' for u, m in [
               (REMARA, '2026-09-22T06:34:20Z'), (OLD, '2026-09-22T23:38:50Z'), (OTHER, '2026-09-21T04:17:39Z'),
               ('https://www.asic.gov.au/regulatory-resources/x', '2026-09-22T00:00:00Z')]) + '</urlset>').encode()
TIERS = {'regulator_sitemaps': [{'id': 'asic_media', 'url': 'https://www.asic.gov.au/sitemap.xml', 'publisher': 'ASIC',
                                 'include_prefix': 'https://www.asic.gov.au/about-asic/news-centre/find-a-media-release/',
                                 'domains': ['asic.gov.au']}]}
PAGE = ('ASIC has made interim stop orders against three private credit products offered by Melbourne Securities. ' * 4)


def fetch(url):
    if 'asic.gov.au/sitemap' in url:
        return SITEMAP
    raise OSError('offline')


def retrieve(url):
    created = '2026-02-10' if url == OLD else '2026-09-22'
    return {'status': 'ok', 'level': 'excerpt', 'retrieved_at': 'x', 'final_url': url, 'excerpt': PAGE, 'sha256': 'a',
            'source_published_at': created}


def test_sitemap_entries_keep_only_releases_and_label_lastmod():
    entries = fetch_news.parse_sitemap(SITEMAP, TIERS['regulator_sitemaps'][0])
    assert [e['url'] for e in entries] == [REMARA, OLD, OTHER]
    first = entries[0]
    assert first['title'] == 'ASIC 26-225MR: asic halts offers of private credit products offered under remara cash management fund'
    assert first['published'] == datetime(2026, 9, 22, 6, 34, 20, tzinfo=timezone.utc)
    assert (first['publisher'], first['published_basis']) == ('ASIC', 'sitemap_lastmod')


def test_regulator_release_needs_sector_match_but_not_an_event_keyword():
    with tempfile.TemporaryDirectory() as data:
        _, stats = fetch_news.run(RULES, data, fetch=fetch, post=FakePost(BRIEF), now=NOW, pause=0, tiers=TIERS,
                                  environ={}, dry_run=True)
    titles = [c['title'] for c in stats['candidates']]
    assert any('26-225MR' in t for t in titles) and not any('26-224MR' in t for t in titles)


def test_retouched_old_release_is_skipped_and_fresh_one_is_dated_by_the_page():
    with tempfile.TemporaryDirectory() as data:
        post = FakePost(BRIEF)
        _, stats = fetch_news.run(RULES, data, fetch=fetch, post=post, now=NOW, pause=0, tiers=TIERS, environ={},
                                  retrieve=retrieve)
        cards = [c for f in Path(data).glob('2026-*.json') for c in json.loads(f.read_text(encoding='utf-8'))['items']]
        seen = json.loads((Path(data) / 'seen.json').read_text(encoding='utf-8'))['ids']
    assert [c['source']['url'] for c in cards] == [REMARA]
    assert cards[0]['published_at'] == '2026-09-22' and cards[0]['published_basis'] == 'page_created_date'
    assert cards[0]['source_origin'] == 'regulator'
    assert stats['stale_skipped'] == 1 and post.calls == 1
    assert site_data.card_id(OLD) in seen


def test_created_date_meta_is_read_as_publication():
    page = b'<meta name="dcterms.date.created" content="2026-09-22" /><p>' + PAGE.encode() + b'</p>'
    assert source_evidence.extract(page, 'text/html')['source_published_at'] == '2026-09-22'
