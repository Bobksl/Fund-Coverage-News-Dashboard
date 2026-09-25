"""Primary-source tier: EDGAR registrant feeds and regulator RSS. Fake HTTP only; temp data dirs."""
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tests.test_fetch_news import BRIEF, FakePost, rss
from tools import fetch_news, site_data, source_evidence

NOW = datetime(2026, 9, 23, 2, 0, tzinfo=timezone.utc)
RULES = site_data.load_rules()
SOURCES = {
    'sec_edgar': {'contact_env': 'SEC_CONTACT_EMAIL', 'domains': ['sec.gov'],
                  'feed': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&output=atom',
                  'forms': ['8-K'],
                  'registrants': [{'id': 'ads', 'cik': '0001837532', 'name': 'Apollo Debt Solutions BDC', 'gps': ['apollo']}]},
    'regulator_feeds': [{'id': 'fed_press', 'url': 'https://www.federalreserve.gov/feeds/press_all.xml',
                         'publisher': 'Federal Reserve Board', 'domains': ['federalreserve.gov']}]}
INDEX = 'https://www.sec.gov/Archives/edgar/data/1837532/000119312526398001/0001193125-26-398001-index.htm'


def entry(form, filed, accession):
    dashed = f'{accession[:10]}-{accession[10:12]}-{accession[12:]}'
    return (f'<entry><category label="form type" term="{form}"/><content type="text/xml">'
            f'<filing-href>https://www.sec.gov/Archives/edgar/data/1837532/{accession}/{dashed}-index.htm</filing-href>'
            f'<filing-type>{form}</filing-type><items-desc>item 7.01</items-desc></content>'
            f'<link href="https://www.sec.gov/Archives/edgar/data/1837532/{accession}/{dashed}-index.htm" rel="alternate"/>'
            f'<title>{form}  - Current report</title><updated>{filed}</updated></entry>')


EDGAR = ('<?xml version="1.0" encoding="ISO-8859-1" ?><feed xmlns="http://www.w3.org/2005/Atom">'
         '<company-info><conformed-name>Apollo Debt Solutions BDC</conformed-name></company-info>'
         + entry('8-K', '2026-09-22T16:32:35-04:00', '000119312526398001')
         + entry('4', '2026-09-22T17:00:00-04:00', '000119312526398002')
         + entry('8-K', '2026-08-01T16:00:00-04:00', '000119312526300000') + '</feed>').encode()
FED = rss(("Federal Reserve report finds bank lending to private credit funds reached $300 billion", "https://www.federalreserve.gov/newsevents/pressreleases/a.htm",
           "Tue, 22 Sep 2026 18:00:00 GMT", "Banks' lending to private credit funds rose.", "Federal Reserve Board"),
          ("Federal Reserve announces board meeting", "https://www.federalreserve.gov/newsevents/pressreleases/b.htm",
           "Tue, 22 Sep 2026 18:00:00 GMT", "", "Federal Reserve Board"), channel="Federal Reserve Board")


def feeds(seen=None):
    def fetch(url):
        if seen is not None:
            seen.append(url)
        if 'browse-edgar' in url:
            return EDGAR
        if 'federalreserve' in url:
            return FED
        raise OSError('offline')
    return fetch


INDEX_HTML = ('<table><tr><td>1</td><td>8-K</td><td><a href="/ix?doc=/Archives/edgar/data/1837532/000119312526398001/d142892d8k.htm">'
              'd142892d8k.htm</a></td><td>8-K</td></tr></table>')
LETTER = ('Thank you for your investment in Apollo Debt Solutions BDC. Third-quarter 2026 tender requests were 14.7% of shares, '
          'down from 16.8% in the second quarter; the Fund will repurchase 5% of shares. ') * 3


def fake_retrieve(log):
    def retrieve(url, keep_html=False):
        log.append(url)
        if url == INDEX:
            return {'status': 'ok', 'level': 'headline_only', 'retrieved_at': 'x', 'final_url': url, 'html': INDEX_HTML}
        return {'status': 'ok', 'level': 'excerpt', 'retrieved_at': '2026-09-23T02:00:01+00:00', 'final_url': url,
                'excerpt': LETTER, 'sha256': 'abc'}
    return retrieve


def refresh(data, env, retrieve=None, **kw):
    post = FakePost(BRIEF)
    code, stats = fetch_news.run(RULES, data, fetch=feeds(kw.pop('seen', None)), post=post, now=NOW, pause=0,
                                 retrieve=retrieve, tiers=SOURCES, environ=env, **kw)
    cards = [c for f in Path(data).glob('2026-*.json') for c in json.loads(f.read_text(encoding='utf-8'))['items']]
    return code, stats, post, cards


def test_edgar_feed_parses_forms_times_and_links():
    [a, b, _] = fetch_news.parse_edgar(EDGAR, SOURCES['sec_edgar']['registrants'][0])
    assert (a['form'], a['url'], a['publisher']) == ('8-K', INDEX, 'Apollo Debt Solutions BDC')
    assert a['published'] == datetime(2026, 9, 22, 20, 32, 35, tzinfo=timezone.utc)
    assert a['title'] == 'Apollo Debt Solutions BDC files 8-K: item 7.01' and b['form'] == '4'


def test_sec_feeds_are_skipped_without_a_declared_contact():
    seen = []
    with tempfile.TemporaryDirectory() as data:
        _, stats, _, _ = refresh(data, {}, seen=seen)
    assert not any('sec.gov' in url for url in seen)
    assert 'sec_edgar: SEC_CONTACT_EMAIL not set' in stats['feeds_skipped']


def test_filing_is_primary_direct_and_uses_filing_text():
    log = []
    with tempfile.TemporaryDirectory() as data:
        _, _, _, cards = refresh(data, {'SEC_CONTACT_EMAIL': 'x@example.com'}, fake_retrieve(log))
    filing = next(c for c in cards if c['source']['url'] == INDEX)
    assert filing['source_origin'] == 'issuer_filing' and 'apollo' in filing['gps']
    assert filing['source']['publisher'] == 'Apollo Debt Solutions BDC'
    assert filing['published_at'] == '2026-09-22T20:32:35+00:00'
    assert log[:2] == [INDEX, 'https://www.sec.gov/Archives/edgar/data/1837532/000119312526398001/d142892d8k.htm']
    assert filing['evidence']['level'] == 'excerpt'
    # Form 4 and the month-old 8-K are outside scope or the lookback window.
    assert sum(c['source']['url'].startswith('https://www.sec.gov/Archives') for c in cards) == 1


def test_regulator_items_still_need_the_keyword_rule_and_are_marked_primary():
    with tempfile.TemporaryDirectory() as data:
        _, _, _, cards = refresh(data, {})
    fed = [c for c in cards if 'federalreserve' in c['source']['url']]
    assert [c['source']['url'][-5:] for c in fed] == ['a.htm']  # the board-meeting notice fails the rule
    assert fed[0]['source_origin'] == 'regulator'


def test_primary_flag_requires_the_listed_domain():
    item = fetch_news.to_item(dict(fetch_news.parse_edgar(EDGAR, SOURCES['sec_edgar']['registrants'][0])[0],
                                   origin='issuer_filing', domains=['sec.gov']))
    assert item['verified_primary_source'] is True
    spoof = dict(item, url='https://sec.gov.evil.example/x')
    assert fetch_news.primary_host(spoof['url'], ['sec.gov']) is False
    assert fetch_news.primary_host('https://www.sec.gov/a', ['sec.gov']) is True


def test_sec_requests_declare_the_contact_and_others_do_not():
    env = {'SEC_CONTACT_EMAIL': 'x@example.com'}
    assert source_evidence.user_agent('www.sec.gov', env).endswith('x@example.com')
    assert 'example.com' not in source_evidence.user_agent('www.federalreserve.gov', env)
    assert 'x@example.com' not in source_evidence.user_agent('www.sec.gov', {})


def test_sec_cover_page_boilerplate_is_trimmed():
    page = ('<p>Date of Report (Date of earliest event reported): September 22, 2026</p>'
            '<p>If an emerging growth company, indicate by check mark if the registrant has elected not to use the extended '
            'transition period for complying with any new or revised financial accounting standards provided pursuant to '
            'Section 13(a) of the Exchange Act. ☐</p><p>' + LETTER + '</p>').encode()
    assert source_evidence.extract(page, 'text/html')['excerpt'].startswith('Thank you for your investment')


def test_edgar_document_prefers_press_release_exhibit():
    html = INDEX_HTML.replace('</table>', '<tr><td>2</td><td>Press release</td><td><a href="/Archives/edgar/data/1/2/ex99-1.htm">'
                              'ex99-1.htm</a></td><td>EX-99.1</td></tr></table>')
    assert source_evidence.edgar_document(html, INDEX) == 'https://www.sec.gov/Archives/edgar/data/1/2/ex99-1.htm'
    assert source_evidence.edgar_document(INDEX_HTML, INDEX).endswith('/d142892d8k.htm')
    assert source_evidence.edgar_document('<table></table>', INDEX) is None
