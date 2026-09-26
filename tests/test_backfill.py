"""Evidence backfill for archived cards: sidecar only, hash-bound, capped, idempotent. Fake HTTP and model."""
import copy
import json

from tests.test_fetch_news import FakePost
from tools import backfill, news_events, site_data

RULES = site_data.load_rules()
EXCERPT = ('CIFC Asset Management, the $47bn alternative credit specialist, has launched its lower-middle-market direct '
           'lending strategy on iCapital Marketplace, giving wealth investors access to senior secured loans. ') * 3
BRIEF = {'relevant': True, 'reason': 'Tracked manager distribution.', 'headline_en': 'CIFC opens direct lending strategy on iCapital',
         'summary_en': 'CIFC, a $47bn credit manager, launched its lower-middle-market direct lending strategy on iCapital.',
         'headline_zh': 'CIFC在iCapital推出直接贷款策略', 'summary_zh': '规模470亿美元的CIFC在iCapital推出其中低端市场直接贷款策略。',
         'gps': ['cifc'], 'sectors': ['private_credit'], 'region': 'US',
         'assessment': {'severity': 'bounded', 'linkage': 'direct', 'current_adverse': False, 'resolved': False,
                        'deadline_at': None, 'reason_en': 'New distribution channel.', 'reason_zh': '新增分销渠道。',
                        'quotes': {'severity': 'giving wealth investors access to senior secured loans',
                                   'linkage': 'CIFC Asset Management, the $47bn alternative credit specialist'}}}


def card(cid, url, **extra):
    c = {'id': cid, 'date': '2026-09-17', 'published_at': '2026-09-17T11:25:06+00:00',
         'headline': {'en': 'CIFC launches direct lending strategy on iCapital', 'zh': '标题'},
         'summary': {'en': 'CIFC launched a strategy. No further details on the strategy or its size were disclosed.', 'zh': '摘要。'},
         'gps': ['cifc'], 'sectors': ['private_credit'], 'region': 'US', 'source': {'publisher': 'ACI', 'url': url},
         'review_status': 'unreviewed', 'origin': 'auto_fetch'}
    c.update(extra)
    return c


def archive(tmp_path, cards):
    tmp_path.joinpath('2026-09-17.json').write_text(json.dumps({'date': '2026-09-17', 'items': cards}), encoding='utf-8')
    return tmp_path


def retriever(log):
    def retrieve(url, keep_html=False):
        log.append(url)
        return {'status': 'ok', 'level': 'excerpt', 'retrieved_at': '2026-09-26T08:00:00+00:00', 'final_url': url,
                'excerpt': EXCERPT, 'sha256': 'abc', 'source_published_at': '2026-09-17T11:25:06+00:00'}
    return retrieve


def test_backfill_writes_sidecar_only_and_is_idempotent(tmp_path):
    direct = card('0000000000a1', 'https://alternativecreditinvestor.com/2026/09/17/cifc/')
    google = card('0000000000a2', 'https://news.google.com/rss/articles/CBMi?oc=5')
    data = archive(tmp_path, [direct, google])
    day_before = (data / '2026-09-17.json').read_bytes()
    log, post = [], FakePost(BRIEF)
    stats = backfill.run(data, RULES, retrieve=retriever(log), post=post, max_cards=10)
    assert (data / '2026-09-17.json').read_bytes() == day_before  # raw cards untouched
    side = json.loads((data / 'backfill.json').read_text(encoding='utf-8'))
    entry = side['cards'][direct['id']]
    assert entry['card_sha256'] == news_events.card_hash(direct) and entry['assessment']['assessable']
    assert entry['summary']['en'].startswith('CIFC, a $47bn') and google['id'] not in side['cards']
    assert log == [direct['source']['url']] and post.calls == 1 and stats['updated'] == 1
    assert EXCERPT[:60] not in json.dumps(side)  # provenance only, no publisher text
    again = backfill.run(data, RULES, retrieve=retriever(log), post=post, max_cards=10)
    assert post.calls == 1 and again['updated'] == 0


def test_backfill_respects_the_cap_and_records_missing_evidence(tmp_path):
    cards = [card(f'0000000000b{i}', f'https://alternativecreditinvestor.com/{i}/') for i in range(3)]
    data = archive(tmp_path, cards)

    def blocked(url, keep_html=False):
        return {'status': 'access_denied', 'level': 'headline_only', 'retrieved_at': 'x'}
    post = FakePost(BRIEF)
    stats = backfill.run(data, RULES, retrieve=blocked, post=post, max_cards=2)
    side = json.loads((data / 'backfill.json').read_text(encoding='utf-8'))
    assert post.calls == 0 and stats['no_evidence'] == 2 and len(side['cards']) == 2
    assert all(entry['status'] == 'access_denied' and 'assessment' not in entry for entry in side['cards'].values())


def test_events_use_backfilled_assessment_and_expose_updates_but_ignore_stale_hashes(tmp_path):
    c = card('0000000000c1', 'https://alternativecreditinvestor.com/c/')
    data = archive(tmp_path, [c])
    backfill.run(data, RULES, retrieve=retriever([]), post=FakePost(BRIEF), max_cards=5)
    side = json.loads((data / 'backfill.json').read_text(encoding='utf-8'))
    result = news_events.build_events([c], groups=[], backfill=side, as_of='2026-09-26T00:00:00+00:00')
    event = result['events'][0]
    assert event['priority']['priority'] == 'useful' and event['priority']['linkage'] == 'direct'
    update = result['card_updates'][c['id']]
    assert update['summary']['en'].startswith('CIFC, a $47bn') and update['headline']['en'] == BRIEF['headline_en']
    assert update['evidence_level'] == 'excerpt'
    changed = copy.deepcopy(c)
    changed['summary']['en'] = 'Edited.'
    stale = news_events.build_events([changed], groups=[], backfill=side, as_of='2026-09-26T00:00:00+00:00')
    assert stale['events'][0]['priority']['priority'] == 'needs_review' and stale['card_updates'] == {}


def test_write_events_reads_the_sidecar(tmp_path):
    c = card('0000000000d1', 'https://alternativecreditinvestor.com/d/')
    data = archive(tmp_path, [c])
    backfill.run(data, RULES, retrieve=retriever([]), post=FakePost(BRIEF), max_cards=5)
    result = json.loads((data / 'events.json').read_text(encoding='utf-8'))
    assert c['id'] in result['card_updates']


def test_retry_unassessed_rebriefs_only_failed_entries_and_caches_raw_answers(tmp_path):
    good = card('0000000000e1', 'https://alternativecreditinvestor.com/e1/')
    bad = card('0000000000e2', 'https://alternativecreditinvestor.com/e2/',
               headline={'en': 'CIFC adds iCapital access for its direct lending strategy', 'zh': '标题二'})
    data = archive(tmp_path, [good, bad])
    weak = dict(BRIEF, assessment=dict(BRIEF['assessment'], quotes={'severity': 'not in the source at all'}))
    backfill.run(data, RULES, retrieve=retriever([]), post=FakePost(weak), max_cards=5)
    side = json.loads((data / 'backfill.json').read_text(encoding='utf-8'))
    assert not side['cards'][bad['id']]['assessment']['assessable']
    post = FakePost(BRIEF)
    stats = backfill.run(data, RULES, retrieve=retriever([]), post=post, max_cards=5, retry_unassessed=True,
                         cache_path=tmp_path / 'cache.json')
    side = json.loads((data / 'backfill.json').read_text(encoding='utf-8'))
    assert post.calls == 2 and stats['updated'] == 2  # both failed first time; both retried
    assert all(v['assessment']['assessable'] for v in side['cards'].values())
    assert json.loads((tmp_path / 'cache.json').read_text(encoding='utf-8'))
    again = backfill.run(data, RULES, retrieve=retriever([]), post=post, max_cards=5, retry_unassessed=True)
    assert post.calls == 2 and again['updated'] == 0  # assessed entries are settled
