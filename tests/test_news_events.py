import copy
import json
from pathlib import Path

from tools import news_events

FIXTURE = Path(__file__).parent / 'fixtures' / 'news_duplicate_cards.json'


def cards():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def test_eight_reviewed_pairs_retain_all_sources_and_replay_stably():
    source = cards()
    before = copy.deepcopy(source)
    result = news_events.build_events(source, as_of='2026-09-23T14:00:00+00:00')
    assert len(result['events']) == 8
    assert sorted(i for e in result['events'] for i in e['member_card_ids']) == sorted(c['id'] for c in source)
    assert source == before
    replay = news_events.build_events(list(reversed(source)), previous=result,
                                     as_of='2026-09-23T14:00:00+00:00')
    assert replay == result


def test_unapproved_generic_identical_headlines_are_not_merged():
    a, b = copy.deepcopy(cards()[:2])
    a['id'], b['id'] = '000000000001', '000000000002'
    a['headline']['en'] = b['headline']['en'] = 'Apollo announces quarterly results'
    result = news_events.build_events([a, b], groups=[])
    assert len(result['events']) == 2


def test_reviewed_mapping_does_not_apply_after_headline_changes():
    a, b = copy.deepcopy(cards()[:2])
    b['headline']['en'] = 'Apollo private credit fund redemption requests RISE in fourth quarter'
    assert len(news_events.build_events([a, b])['events']) == 2


def test_source_tracking_alias_preserves_query_identity_and_decimal_numbers():
    assert news_events.canonical_url('https://Example.com/a?id=4&utm_source=x#top') == 'https://example.com/a?id=4'
    assert news_events.canonical_url('https://example.com/a?id=4') != news_events.canonical_url('https://example.com/a?id=5')
    assert news_events.normalize_title('6.3% defaults') != news_events.normalize_title('63% defaults')


def test_syndication_does_not_bump_event_recency_and_dates_remain_available():
    source = cards()[6:8]
    result = news_events.build_events(source)
    event = result['events'][0]
    assert event['last_material_update_at'].startswith('2026-09-16')
    assert set(event['date_views']) == {'2026-09-16', '2026-09-18'}
    for day, view in event['date_views'].items():
        assert all(c['date'] <= day for c in source if c['id'] == view['representative_card_id'])


def test_same_url_changed_content_is_not_hidden():
    a, b = copy.deepcopy(cards()[:2])
    a['id'], b['id'] = '000000000003', '000000000004'
    b['source']['url'] = a['source']['url']
    a['source_fingerprint'], b['source_fingerprint'] = 'a', 'b'
    assert len(news_events.build_events([a, b], groups=[])['events']) == 2


def test_verified_identity_groups_paraphrases_but_not_changed_figures_or_period():
    from tools.summarize import validate_event_identity
    a, b = copy.deepcopy(cards()[:2])
    a['id'], b['id'] = '000000000005', '000000000006'
    source = {'title': 'Example launches Alpha', 'text': 'Example launches Alpha in Q3 2026 for $350 million.'}
    raw = {'subject': 'Example', 'action': 'launches', 'object': 'Alpha', 'period': 'Q3 2026'}
    identity = validate_event_identity(raw, source)
    assert identity
    a['event_identity'] = b['event_identity'] = identity
    result = news_events.build_events([a, b], groups=[])
    assert result['event_count'] == 1
    b['event_identity'] = validate_event_identity(raw, dict(source, text=source['text'].replace('350', '500')))
    assert news_events.build_events([a, b], groups=[])['event_count'] == 2
    assert validate_event_identity(dict(raw, period='Q4 2026'), source) is None


def test_legacy_date_only_publication_does_not_break_projection():
    c = copy.deepcopy(cards()[0])
    c['published_at'] = c['date']
    event = news_events.build_events([c])['events'][0]
    assert event['last_material_update_at'] == c['date'] + 'T00:00:00+08:00'
    assert event['timestamp_basis'] == 'date_only'


def test_revision_does_not_rewrite_earlier_day_or_merge_unrelated_reused_url():
    a, b = copy.deepcopy(cards()[:2])
    a['id'], b['id'] = '000000000007', '000000000008'
    a['date'], b['date'] = '2026-09-22', '2026-09-23'
    a['published_at'] = '2026-09-22T12:00:00+00:00'
    b['published_at'] = a['published_at']
    b['observed_at'] = '2026-09-23T12:00:00+00:00'
    b['supersedes_card_id'] = a['id']
    b['source']['url'] = a['source']['url']
    a['source_headline'] = b['source_headline'] = 'Apollo announces Q3 fund redemption limits'
    result = news_events.build_events([a, b], groups=[])
    assert result['event_count'] == 1
    event = result['events'][0]
    assert event['representative_card_id'] == b['id']
    assert event['date_views']['2026-09-22']['representative_card_id'] == a['id']
    b['source_headline'] = 'Apollo announces Q4 new fund launch'
    assert news_events.build_events([a, b], groups=[])['event_count'] == 2


def test_display_tags_fix_vehicle_confusion_without_changing_source_card():
    c = copy.deepcopy(cards()[0])
    c['headline']['en'] = 'Blue Owl Technology Income Corp. extends credit facility'
    c['gps'] = ['otf']
    event = news_events.build_events([c], groups=[])['events'][0]
    assert event['display_gps'] == ['blue_owl']
    assert c['gps'] == ['otf']


def test_corrupt_previous_event_file_is_rebuilt_without_losing_raw_cards(tmp_path):
    c = cards()[0]
    (tmp_path / (c['date'] + '.json')).write_text(json.dumps({'items': [c]}), encoding='utf-8')
    (tmp_path / 'events.json').write_text('broken', encoding='utf-8')
    result = news_events.write_events(tmp_path)
    assert result['article_count'] == result['event_count'] == 1
    assert result['warnings']
