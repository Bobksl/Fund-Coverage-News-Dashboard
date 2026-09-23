import copy

from tools import news_priority

NOW = '2026-09-23T08:00:00+00:00'
TEXT = 'OTF suspended withdrawals after a material liquidity failure. The decision deadline is 2026-09-24T08:00:00+00:00.'
ITEM = {'title': 'OTF suspends withdrawals', 'text': TEXT, 'url': 'https://example.com/news'}


def assessment(**changes):
    result = {'severity': 'critical', 'linkage': 'direct', 'current_adverse': True,
              'deadline_at': '2026-09-24T08:00:00+00:00', 'resolved': False,
              'reason_en': 'Withdrawals suspended.', 'reason_zh': '暂停赎回。',
              'quotes': {'severity': 'material liquidity failure', 'linkage': 'OTF suspended withdrawals',
                         'current_adverse': 'OTF suspended withdrawals',
                         'deadline_at': '2026-09-24T08:00:00+00:00'}}
    result.update(changes)
    return news_priority.validate_assessment(result, ITEM)


def test_urgent_is_derived_and_deadline_bucket_expires_without_new_news():
    a = assessment()
    p = news_priority.classify(a, as_of=NOW)
    assert p['priority'] == 'urgent'
    assert p['time_sensitivity'] == '48h'
    late = news_priority.classify(a, as_of='2026-09-26T08:00:00+00:00')
    assert late['time_sensitivity'] == 'monitor'


def test_missing_fabricated_malformed_or_headline_only_evidence_requires_review():
    for raw in [None, [], {'severity': []}, {'severity': 'critical', 'quotes': {'severity': 'invented'}}]:
        assert news_priority.classify(news_priority.validate_assessment(raw, ITEM), as_of=NOW)['priority'] == 'needs_review'
    raw = {'severity': 'critical', 'quotes': {'severity': 'OTF suspends withdrawals'}}
    assert not news_priority.validate_assessment(raw, dict(ITEM, text=ITEM['title']))['assessable']


def test_ranking_uses_timing_then_linkage_then_recency_not_source_count():
    p = news_priority.classify(assessment(), as_of=NOW)
    def event(event_id, **change):
        return {'event_id': event_id, 'last_material_update_at': NOW, 'priority': dict(p, **change)}
    near = event('near')
    far = event('far', time_sensitivity='7d')
    sector = event('sector', linkage='sector')
    assert sorted([far, sector, near], key=news_priority.rank_key) == [near, sector, far]
    duplicate = copy.deepcopy(near)
    duplicate['sources'] = [{}] * 100
    assert news_priority.rank_key(duplicate) == news_priority.rank_key(near)


def test_noncritical_material_event_and_resolved_critical_event_are_important():
    p = news_priority.classify(assessment(severity='substantial', current_adverse=False, deadline_at=None), as_of=NOW)
    assert p['priority'] == 'important'
    raw = assessment(resolved=True)
    # resolved=True needs its own support; absent evidence must not silently clear a risk.
    assert not raw['assessable']


def test_known_headline_risk_is_visible_but_not_confirmed_urgent():
    a = news_priority.validate_assessment(None, dict(ITEM, text=ITEM['title']))
    p = news_priority.classify(a, as_of=NOW)
    assert p['priority'] == 'needs_review'
    assert p['potential_urgent']
