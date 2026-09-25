"""Reviewed overlay v2 and archive-wide novelty: survivor IDs, aliases, member roles, date
corrections, related events, anchored exact-headline repeats. Synthetic cards; no public writes."""
import json

import pytest

from tools import news_events

AS_OF = '2026-09-25T00:00:00+00:00'
HEADLINE = 'Apollo fund redemption requests ease in third quarter'


def make(cid, date, published, headline, **extra):
    c = {'id': cid, 'date': date, 'published_at': published, 'headline': {'en': headline, 'zh': '标题'},
         'summary': {'en': headline + '.', 'zh': '摘要。'}, 'gps': ['apollo'], 'sectors': ['private_credit'],
         'region': 'US', 'source': {'publisher': 'P' + cid[-2:], 'url': 'https://example.com/' + cid},
         'review_status': 'unreviewed', 'origin': 'auto_fetch'}
    c.update(extra)
    return c


def group(event_id, members, **extra):
    return dict({'event_id': event_id, 'reason': 'test', 'members': [
        dict({'id': c['id'], 'headline': c['headline']['en'], 'card_sha256': news_events.card_hash(c)}, **role)
        for c, role in members]}, **extra)


def apollo_family():
    return [make('a00000000001', '2026-09-23', '2026-09-22T20:44:00+00:00', HEADLINE),
            make('a00000000002', '2026-09-23', '2026-09-22T22:04:00+00:00', 'Apollo BDC requests ease to 14.7% in Q3'),
            make('a00000000003', '2026-09-23', '2026-09-23T12:19:00+00:00', 'Apollo stock falls as redemptions stay capped'),
            make('a00000000004', '2026-09-24', '2026-09-24T12:17:00+00:00', 'Apollo limits withdrawals for third consecutive quarter')]


def test_reviewed_merge_keeps_survivor_aliases_all_sources_and_no_recency_bump():
    family = apollo_family()
    before = news_events.build_events(family, groups=[], as_of=AS_OF)
    assert before['event_count'] == 4
    members = [(c, {}) for c in family[:2]] + [(family[2], {'role': 'reaction'}), (family[3], {})]
    overlay = {'groups': [group('evt-reviewed-001', members, aliases=['evt-legacy-old'])]}
    after = news_events.build_events(family, overlay=overlay, previous=before, as_of=AS_OF)
    assert after['event_count'] == 1
    event = after['events'][0]
    assert event['event_id'] == 'evt-reviewed-001'
    assert sorted(event['member_card_ids']) == sorted(c['id'] for c in family)
    assert event['aliases'] == sorted(['evt-legacy-old'] + ['evt-' + c['id'] for c in family])
    # Repeats, a stock reaction and a day-later rewrite never advance the material timestamp.
    assert event['last_material_update_at'] == family[0]['published_at']
    assert event['member_roles'] == {family[2]['id']: 'reaction'}
    replay = news_events.build_events(list(reversed(family)), overlay=overlay, previous=after, as_of=AS_OF)
    assert replay == after


def test_aliases_survive_a_rebuild_without_previous_index():
    family = apollo_family()
    before = news_events.build_events(family, groups=[], as_of=AS_OF)
    overlay = {'groups': [group('evt-reviewed-001', [(c, {}) for c in family])]}
    migrated = news_events.build_events(family, overlay=overlay, previous=before, as_of=AS_OF)
    later = news_events.build_events(family, overlay=overlay, previous=migrated, as_of=AS_OF)
    assert later['events'][0]['aliases'] == migrated['events'][0]['aliases']


def test_update_role_uses_corrected_publication_date_not_observation():
    issue = make('b00000000001', '2026-08-17', '2026-08-17', 'OTF files prospectus supplement for 6.500% notes due 2029')
    rating = make('b00000000002', '2026-09-17', '2026-09-17T08:00:59+00:00', 'KBRA assigns BBB to OTF $400m notes')
    correction = {'card_id': rating['id'], 'card_sha256': news_events.card_hash(rating), 'field': 'published_at',
                  'original': rating['published_at'], 'corrected': '2026-08-18', 'basis': 'publisher dateline',
                  'evidence_url': 'https://example.com/kbra', 'event_date': '2026-08-17'}
    overlay = {'groups': [group('evt-b00000000001', [(issue, {}), (rating, {'role': 'update'})])],
               'corrections': [correction]}
    event = news_events.build_events([issue, rating], overlay=overlay, as_of=AS_OF)['events'][0]
    assert event['last_material_update_at'] == '2026-08-18T00:00:00+08:00'
    source = next(s for s in event['sources'] if s['card_id'] == rating['id'])
    assert source['published_at'] == '2026-08-18T00:00:00+08:00'
    assert source['date_correction']['original'] == '2026-09-17T08:00:59+00:00'
    assert source['date_correction']['event_date'] == '2026-08-17'
    # Raw card and its September date view are untouched: observation is not rewritten.
    assert rating['published_at'] == '2026-09-17T08:00:59+00:00'
    assert event['date_views']['2026-09-17']['further_coverage'] is True
    assert set(event['date_views']) == {'2026-08-17', '2026-09-17'}


def test_correction_is_ignored_when_card_content_changed():
    rating = make('b00000000002', '2026-09-17', '2026-09-17T08:00:59+00:00', 'KBRA assigns BBB to OTF $400m notes')
    correction = {'card_id': rating['id'], 'card_sha256': news_events.card_hash(rating), 'field': 'published_at',
                  'original': rating['published_at'], 'corrected': '2026-08-18', 'basis': 'x', 'evidence_url': 'https://e.x'}
    rating['summary']['en'] = 'Changed.'
    event = news_events.build_events([rating], overlay={'groups': [], 'corrections': [correction]}, as_of=AS_OF)['events'][0]
    assert 'date_correction' not in event['sources'][0]
    assert event['last_material_update_at'] == rating['published_at']


def test_related_events_stay_separate_and_resolve_aliases():
    orders = make('c00000000001', '2026-09-22', '2026-09-22T09:36:30+00:00', 'ASIC stop orders on three Remara products')
    copy_ = make('c00000000003', '2026-09-22', '2026-09-22T09:42:12+00:00', 'Regulator cracks down on three products')
    speech = make('c00000000002', '2026-09-22', '2026-09-22T03:24:30+00:00', 'ASIC says sector should prepare for enforcement')
    overlay = {'groups': [group('evt-c00000000001', [(orders, {}), (copy_, {})], aliases=['evt-c00000000003'])],
               'relations': [{'event_ids': ['evt-c00000000003', 'evt-c00000000002'], 'reason': 'distinct actions'}]}
    result = news_events.build_events([orders, copy_, speech], overlay=overlay, as_of=AS_OF)
    assert result['event_count'] == 2
    by_id = {e['event_id']: e for e in result['events']}
    assert by_id['evt-c00000000001']['related_event_ids'] == ['evt-c00000000002']
    assert by_id['evt-c00000000002']['related_event_ids'] == ['evt-c00000000001']


def test_card_cannot_belong_to_two_reviewed_groups():
    family = apollo_family()
    overlay = {'groups': [group('evt-x', [(family[0], {})]), group('evt-y', [(family[0], {})])]}
    with pytest.raises(ValueError, match='two reviewed groups'):
        news_events.build_events(family, overlay=overlay)


def test_anchored_identical_source_headlines_join_within_seven_days_only():
    first = make('d00000000001', '2026-09-22', '2026-09-22T20:44:00+00:00', 'x', source_headline=HEADLINE)
    copy_ = make('d00000000002', '2026-09-24', '2026-09-24T09:00:00+00:00', 'y', observed_at='2026-09-25T04:00:00+00:00',
                 source_headline='Apollo Fund Redemption Requests Ease in Third Quarter')
    stale = make('d00000000003', '2026-10-10', '2026-10-10T09:00:00+00:00', 'z', source_headline=HEADLINE)
    generic_a = make('d00000000004', '2026-09-22', '2026-09-22T09:00:00+00:00', 'g', source_headline='Apollo announces quarterly results')
    generic_b = make('d00000000005', '2026-09-23', '2026-09-23T09:00:00+00:00', 'h', source_headline='Apollo announces quarterly results')
    result = news_events.build_events([first, copy_, stale, generic_a, generic_b], groups=[], as_of=AS_OF)
    members = sorted(sorted(e['member_card_ids']) for e in result['events'])
    assert members == sorted([[first['id'], copy_['id']], [stale['id']], [generic_a['id']], [generic_b['id']]])
    joined = next(e for e in result['events'] if copy_['id'] in e['member_card_ids'])
    assert joined['merge_rule'] == 'headline' and joined['event_id'] == 'evt-' + first['id']
    assert joined['last_material_update_at'] == first['published_at']


def test_late_repeat_joins_reviewed_event_without_leaking_into_earlier_days():
    family = apollo_family()
    family[0]['source_headline'] = HEADLINE
    late = make('a00000000009', '2026-09-26', '2026-09-26T01:00:00+00:00', 'l', source_headline=HEADLINE,
                observed_at='2026-09-26T02:00:00+00:00')
    overlay = {'groups': [group('evt-reviewed-001', [(c, {}) for c in family])]}
    cards = family + [late]
    event = news_events.build_events(cards, overlay=overlay, as_of=AS_OF)['events'][0]
    assert late['id'] in event['member_card_ids'] and event['merge_rule'] == 'reviewed'
    assert event['last_material_update_at'] == family[0]['published_at']
    by_id = {c['id']: c for c in cards}
    for day, view in event['date_views'].items():
        assert all(by_id[cid]['date'] == day for cid in view['member_card_ids'])
    assert event['date_views']['2026-09-26']['further_coverage'] is True


def test_reviewed_representative_choice_and_informative_summary_preference():
    family = apollo_family()
    family[0]['summary']['en'] = 'Apollo requests eased. No further details were provided in the article beyond the headline.'
    family[1]['summary']['en'] = 'Apollo BDC redemption requests eased to 14.7% in Q3.'
    assert news_events.representative(family[:2])['id'] == family[1]['id']
    overlay = {'groups': [group('evt-r', [(c, {}) for c in family], representative_card_id=family[3]['id'])]}
    event = news_events.build_events(family, overlay=overlay, as_of=AS_OF)['events'][0]
    assert event['representative_card_id'] == family[3]['id']
    assert event['date_views']['2026-09-23']['representative_card_id'] == family[1]['id']


def test_repository_overlay_is_internally_consistent():
    overlay = json.loads(news_events.GROUPS_PATH.read_text(encoding='utf-8'))
    ids = [m['id'] for g in overlay['groups'] for m in g['members']]
    assert len(ids) == len(set(ids))
    survivors = {g['event_id'] for g in overlay['groups']}
    aliases = [a for g in overlay['groups'] for a in g.get('aliases', [])]
    assert len(aliases) == len(set(aliases)) and not survivors & set(aliases)
    for g in overlay['groups']:
        assert g.get('representative_card_id') in (None, *[m['id'] for m in g['members']])
        assert all(m.get('role', 'coverage') in news_events.ROLES for m in g['members'])
    for c in overlay.get('corrections', []):
        assert c['field'] == 'published_at' and c['original'] != c['corrected'] and c['evidence_url'].startswith('https://')
