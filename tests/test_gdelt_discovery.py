"""GDELT discovery: real publisher URLs, paced requests, honest seen-time, Google News de-duplication.
Fake HTTP only; temporary data directories."""
import json
import tempfile
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from tests.test_fetch_news import BRIEF, FakePost, rss
from tools import fetch_news, site_data

NOW = datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc)
RULES = site_data.load_rules()
TIERS = {'gdelt': {'endpoint': 'https://api.gdeltproject.org/api/v2/doc/doc', 'min_interval_s': 10, 'retry_after_s': 15,
                   'maxrecords': 250, 'queries': [{'id': 'managers', 'q': '("KKR") sourcelang:english'},
                                                  {'id': 'sector', 'q': '("private credit") sourcelang:english'}]}}
ARTICLE = {'url': 'https://www.afr.com/markets/private-credit-kkr-20260924-p6100o', 'url_mobile': '',
           'title': 'KKR raises $2 . 5 billion for private credit fund , sources say', 'seendate': '20260924T013000Z',
           'domain': 'afr.com', 'language': 'English', 'sourcecountry': 'Australia'}
GDELT = json.dumps({'articles': [ARTICLE]}).encode()
GOOGLE = rss(('KKR raises $2.5 billion for private credit fund, sources say', 'https://news.google.com/rss/articles/CBMiX?oc=5',
              'Thu, 24 Sep 2026 01:20:00 GMT', '', 'AFR'),
             ('KKR closes $1bn asset-based finance fund', 'https://news.google.com/rss/articles/CBMiY?oc=5',
              'Thu, 24 Sep 2026 02:00:00 GMT', '', 'PDI'))


def fetcher(gdelt_replies, log):
    replies = list(gdelt_replies)

    def fetch(url):
        log.append(url)
        if 'gdeltproject' in url:
            reply = replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply
        if 'news.google.com' in url and 'q=KKR' in url.replace('%22', ''):
            return GOOGLE
        raise OSError('offline')
    return fetch


def run(data, replies, sleeps=None, **kw):
    log = []
    _, stats = fetch_news.run(RULES, data, fetch=fetcher(replies, log), post=FakePost(BRIEF), now=NOW,
                                 pause=0 if sleeps is None else 1, tiers=TIERS, environ={},
                                 sleep=(sleeps.append if sleeps is not None else None), **kw)
    cards = [c for f in Path(data).glob('2026-*.json') for c in json.loads(f.read_text(encoding='utf-8'))['items']]
    return stats, cards, log


def test_gdelt_titles_are_cleaned_and_seen_time_is_labelled():
    [entry] = fetch_news.parse_gdelt(GDELT)
    assert entry['title'] == 'KKR raises $2.5 billion for private credit fund, sources say'
    assert entry['published'] == datetime(2026, 9, 24, 1, 30, tzinfo=timezone.utc)
    assert (entry['publisher'], entry['discovery']) == ('afr.com', 'gdelt')


def test_gdelt_result_replaces_its_opaque_google_news_copy():
    with tempfile.TemporaryDirectory() as data:
        _, cards, _ = run(data, [GDELT, GDELT])
    urls = sorted(c['source']['url'] for c in cards)
    assert ARTICLE['url'] in urls and 'https://news.google.com/rss/articles/CBMiX?oc=5' not in urls
    assert 'https://news.google.com/rss/articles/CBMiY?oc=5' in urls  # different story stays
    gdelt = next(c for c in cards if c['source']['url'] == ARTICLE['url'])
    assert gdelt['published_basis'] == 'gdelt_seen' and gdelt['published_at'] == '2026-09-24T01:30:00+00:00'


def test_gdelt_calls_are_paced_and_a_rate_limit_is_retried_once_then_recorded():
    sleeps = []
    limited = b'Please limit requests to one every 5 seconds'
    with tempfile.TemporaryDirectory() as data:
        stats, _, log = run(data, [limited, GDELT, limited, limited], sleeps=sleeps)
    calls = [u for u in log if 'gdeltproject' in u]
    assert len(calls) == 4  # each query: first try + one retry
    assert 15 in sleeps and all(s >= 9.9 for s in sleeps if s != 1)
    assert any(f.startswith('gdelt_sector') for f in stats['feeds_failed'])
    assert not any(f.startswith('gdelt_managers') for f in stats['feeds_failed'])


def test_gdelt_http_errors_do_not_fail_the_refresh():
    error = urllib.error.HTTPError('https://api.gdeltproject.org', 429, 'Too Many Requests', {}, None)
    with tempfile.TemporaryDirectory() as data:
        stats, cards, _ = run(data, [error, error, error, error])
    assert stats['feeds_ok'] >= 1 and len([f for f in stats['feeds_failed'] if f.startswith('gdelt')]) == 2
    assert cards  # Google News items still processed


def test_gdelt_text_errors_are_reported_in_its_own_words():
    try:
        fetch_news.parse_gdelt(b'Your search contained a keyword that was too short.')
    except ValueError as error:
        assert 'too short' in str(error)
    else:
        raise AssertionError('plain-text error accepted')
    assert fetch_news.parse_gdelt(b'{}') == []


def test_gdelt_query_url_encodes_parameters():
    url = fetch_news.gdelt_url(TIERS['gdelt'], TIERS['gdelt']['queries'][0], lookback_days=3)
    assert url.startswith('https://api.gdeltproject.org/api/v2/doc/doc?query=')
    assert 'mode=artlist' in url and 'format=json' in url and 'timespan=3d' in url and 'maxrecords=250' in url
