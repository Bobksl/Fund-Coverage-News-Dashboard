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


def test_quotes_tolerate_typography_and_single_item_lists_but_not_paraphrase():
    text = 'The regulator said the fund’s  "stop orders" apply to three products until revoked.'
    item = {'title': 'Regulator halts products', 'text': text}
    base = {'severity': 'substantial', 'linkage': 'sector', 'current_adverse': False, 'resolved': False,
            'deadline_at': None, 'reason_en': 'Orders issued.', 'reason_zh': '已发布命令。'}
    ok = dict(base, quotes={'severity': ["the fund's \"stop orders\" apply to three products"],
                            'linkage': 'The regulator said the fund’s'})
    assert news_priority.validate_assessment(ok, item)['assessable']
    paraphrase = dict(base, quotes={'severity': 'orders apply to three funds', 'linkage': 'The regulator said'})
    assert not news_priority.validate_assessment(paraphrase, item)['assessable']


def test_routine_disclosures_rank_below_non_routine_items_of_the_same_severity():
    text = 'OTF sold unregistered Class I shares to feeder vehicles and restated its monthly distribution. CIFC launched a strategy.'
    item = {'title': 'OTF 8-K', 'text': text}
    base = {'severity': 'bounded', 'linkage': 'direct', 'current_adverse': False, 'resolved': False, 'deadline_at': None,
            'reason_en': 'Routine.', 'reason_zh': '例行披露。',
            'quotes': {'severity': 'restated its monthly distribution', 'linkage': 'OTF sold unregistered Class I shares'}}
    filing = dict(item, verified_primary_source=True)
    routine = news_priority.classify(news_priority.validate_assessment(dict(base, routine=True), filing), as_of=NOW)
    # Only filings and regulator releases can be demoted as routine; press items were misjudged in testing.
    press = news_priority.validate_assessment(dict(base, routine=True), item)
    assert press['routine'] is False
    launch = news_priority.classify(news_priority.validate_assessment(base, item), as_of=NOW)
    assert routine['priority'] == launch['priority'] == 'useful'
    assert routine['routine'] is True and launch['routine'] is False  # missing flag means not routine
    old_primary = dict(routine, evidence_strength='primary')
    events = [{'event_id': 'filing', 'last_material_update_at': '2026-09-23T00:00:00+00:00', 'priority': old_primary},
              {'event_id': 'launch', 'last_material_update_at': '2026-09-17T00:00:00+00:00', 'priority': dict(launch, linkage='sector')}]
    assert [e['event_id'] for e in sorted(events, key=news_priority.rank_key)] == ['launch', 'filing']
    critical = dict(launch, priority='important', severity='substantial')
    assert news_priority.rank_key({'event_id': 'x', 'last_material_update_at': NOW, 'priority': critical}) < \
        news_priority.rank_key({'event_id': 'y', 'last_material_update_at': NOW, 'priority': launch})
    junk = news_priority.validate_assessment(dict(base, routine='yes'), item)
    assert junk['assessable'] and junk['routine'] is False
