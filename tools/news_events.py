"""Lossless event projection over immutable per-day news cards. No model calls."""
import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tools import news_priority

ROOT = Path(__file__).resolve().parents[1]
GROUPS_PATH = ROOT / 'config' / 'news_event_groups.json'
VERSION = 'events-v1'


def normalize_title(value):
    value = unicodedata.normalize('NFKC', value).casefold()
    value = value.translate(str.maketrans({'’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '—': '-'}))
    return re.sub(r'\s+', ' ', value).strip()


def canonical_url(value):
    url = urlsplit(value)
    query = [(k, v) for k, v in parse_qsl(url.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in {'fbclid', 'gclid'}]
    return urlunsplit((url.scheme.lower(), url.netloc.lower(), url.path, urlencode(query), ''))


def card_stamp(card):
    value = card.get('published_at')
    if value:
        try:
            epoch(value)
            return value
        except (ValueError, TypeError, AttributeError):
            pass
    return card['date'] + 'T00:00:00+08:00'


def epoch(stamp):
    parsed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    return parsed.timestamp()


def representative(members):
    # Human approval is attached to this exact card, not transferred to other summaries.
    return min(members, key=lambda c: (c.get('review_status') != 'reviewed',
                                      not (c.get('assessment') or {}).get('assessable', False),
                                      -len(c['summary']['en']), epoch(card_stamp(c)), c['id']))


def card_assessment(card):
    if isinstance(card.get('assessment'), dict):
        return card['assessment']
    title = card.get('source_headline') or card['headline']['en']
    return news_priority.validate_assessment(None, {'title': title, 'text': title})


def display_gps(card):
    gps = list(card['gps'])
    title = card.get('source_headline') or card['headline']['en']
    if re.search(r'Blue Owl Technology Income', title, re.IGNORECASE) and not re.search(r'Technology Finance', title, re.IGNORECASE):
        gps = [gp for gp in gps if gp != 'otf']
        if 'blue_owl' not in gps:
            gps.append('blue_owl')
    if 'otf' in gps and 'blue_owl' not in gps:
        gps.append('blue_owl')
    return gps


def _approved_keys(cards, groups):
    by_id = {c['id']: c for c in cards}
    keys = {}
    for group in groups:
        present = [m for m in group['members'] if m['id'] in by_id]
        # Any changed headline invalidates the whole decision, not just one member.
        if all(by_id[m['id']]['headline']['en'] == m['headline'] and
               (not m.get('card_sha256') or card_hash(by_id[m['id']]) == m['card_sha256']) for m in present):
            for member in present:
                keys[member['id']] = group['event_id']
    return keys


def card_hash(card):
    return hashlib.sha256(json.dumps(card, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _auto_key(card):
    identity = card.get('event_identity')
    if isinstance(identity, dict) and identity.get('version') == 'identity-v1':
        fields = ('subject', 'action', 'object', 'period')
        if all(isinstance(identity.get(f), str) and identity[f] for f in fields):
            return ('identity', *(identity[f] for f in fields), tuple(identity.get('numbers', [])))
    fingerprint = card.get('source_fingerprint')
    if fingerprint:
        return ('source', canonical_url(card['source']['url']), fingerprint)
    # Legacy generated headlines alone are deliberately insufficient.
    return ('single', card['id'])


def same_revision_event(card, parent):
    if canonical_url(parent['source']['url']) != canonical_url(card['source']['url']):
        return False
    a, b = parent.get('event_identity'), card.get('event_identity')
    if isinstance(a, dict) and isinstance(b, dict):
        return all(a.get(f) == b.get(f) for f in ('subject', 'action', 'object', 'period'))
    return bool(card.get('source_headline')) and normalize_title(card['source_headline']) == normalize_title(parent.get('source_headline', ''))


def build_events(cards, *, groups=None, previous=None, as_of=None):
    if groups is None:
        groups = json.loads(GROUPS_PATH.read_text(encoding='utf-8'))['groups']
    if len({c['id'] for c in cards}) != len(cards):
        raise ValueError('duplicate source card IDs')
    as_of = as_of or datetime.now(timezone.utc).isoformat(timespec='seconds')
    approved = _approved_keys(cards, groups)
    prior = {cid: event['event_id'] for event in (previous or {}).get('events', [])
             for cid in event['member_card_ids']}
    buckets = {}
    card_keys = {}
    by_id = {c['id']: c for c in cards}
    for card in sorted(cards, key=lambda c: (epoch(card_stamp(c)), c['id'])):
        key = ('reviewed', approved[card['id']]) if card['id'] in approved else _auto_key(card)
        card_keys[card['id']] = key
        buckets.setdefault(key, []).append(card)
    # Same-source revisions are explicitly linked by the ingestion code, not headline similarity.
    for card in sorted(cards, key=lambda c: (c.get('observed_at', ''), c['id'])):
        parent = by_id.get(card.get('supersedes_card_id'))
        if parent and parent['id'] != card['id'] and same_revision_event(card, parent):
            old, target = card_keys[card['id']], card_keys[parent['id']]
            if old != target:
                moving = buckets.pop(old)
                buckets[target].extend(moving)
                for member in moving:
                    card_keys[member['id']] = target
    events, used_ids = [], set()
    for key, members in buckets.items():
        candidate_ids = sorted({prior[c['id']] for c in members if c['id'] in prior})
        event_id = key[1] if key[0] == 'reviewed' else next(
            (value for value in candidate_ids if value not in used_ids), 'evt-' + members[0]['id'])
        if event_id in used_ids:
            event_id = 'evt-' + members[0]['id']
        used_ids.add(event_id)
        members.sort(key=lambda c: (epoch(card_stamp(c)), c['id']))
        revisions = [c for c in members if c.get('supersedes_card_id')]
        latest_revision = max(revisions, key=lambda c: (epoch(c.get('observed_at') or card_stamp(c)), c['id'])) if revisions else None
        chosen = latest_revision or representative(members)
        first = min(members, key=lambda c: (epoch(card_stamp(c)), c['id']))
        views = {}
        for day in sorted({c['date'] for c in members}):
            on_day = [c for c in members if c['date'] == day]
            day_revisions = [c for c in on_day if c.get('supersedes_card_id')]
            day_chosen = max(day_revisions, key=lambda c: (epoch(c.get('observed_at') or card_stamp(c)), c['id'])) if day_revisions else representative(on_day)
            views[day] = {'representative_card_id': day_chosen['id'],
                          'display_gps': display_gps(day_chosen), 'display_sectors': day_chosen['sectors'],
                          'member_card_ids': sorted(c['id'] for c in on_day),
                          'further_coverage': day != first['date']}
            views[day]['priority'] = news_priority.classify(card_assessment(day_chosen),
                                                           as_of=day + 'T23:59:59+08:00')
        priority = news_priority.classify(card_assessment(chosen), as_of=as_of)
        if latest_revision and latest_revision.get('material_update_confirmed') is True:
            material_stamp = latest_revision.get('observed_at') or card_stamp(latest_revision)
        else:
            material_stamp = card_stamp(first)
        events.append({'event_id': event_id, 'member_card_ids': sorted(c['id'] for c in members),
                       'representative_card_id': chosen['id'], 'date_views': views,
                       'display_gps': display_gps(chosen), 'display_sectors': chosen['sectors'],
                       'first_seen_at': card_stamp(first), 'last_material_update_at': material_stamp,
                       'timestamp_basis': 'published_at' if first.get('published_at') == card_stamp(first) else 'date_only',
                       'updated': bool(revisions), 'priority': priority,
                       'last_source_revision_at': latest_revision.get('observed_at') if latest_revision else None,
                       'merge_rule': key[0], 'sources': [dict(c['source'], card_id=c['id'],
                                                           published_at=card_stamp(c)) for c in members]})
    ranked = sorted(events, key=news_priority.rank_key)
    for rank, event in enumerate(ranked, 1):
        event['priority_rank'] = rank
    for day in {day for event in events for day in event['date_views']}:
        on_day = [dict(event, priority=event['date_views'][day]['priority']) for event in events if day in event['date_views']]
        for rank, event in enumerate(sorted(on_day, key=news_priority.rank_key), 1):
            event['date_views'][day]['priority_rank'] = rank
    return {'schema_version': 1, 'grouping_version': VERSION, 'ranking_version': news_priority.VERSION, 'as_of': as_of,
            'article_count': len(cards), 'event_count': len(events),
            'events': sorted(events, key=lambda e: e['event_id']),
            'cards_sha256': hashlib.sha256(json.dumps(sorted(cards, key=lambda c: c['id']),
                                                     sort_keys=True, ensure_ascii=False).encode()).hexdigest()}


def write_events(data_dir, *, now=None):
    from tools import site_data

    data_dir = Path(data_dir)
    cards = [c for day in site_data._day_files(data_dir) for c in site_data.load_day(data_dir, day)]
    path = data_dir / 'events.json'
    previous, warnings = None, []
    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(previous, dict) or not isinstance(previous.get('events'), list):
                raise TypeError('invalid previous event index')
            for event in previous['events']:
                if (not isinstance(event, dict) or not isinstance(event.get('event_id'), str)
                        or not isinstance(event.get('member_card_ids'), list)
                        or not all(isinstance(cid, str) for cid in event['member_card_ids'])):
                    raise ValueError('invalid previous event membership')
        except (ValueError, TypeError, UnicodeError):
            previous = None
            warnings.append('Previous event index was invalid; rebuilt from preserved source cards.')
    result = build_events(cards, previous=previous,
                          as_of=(now or datetime.now(timezone.utc)).isoformat(timespec='seconds'))
    if warnings:
        result['warnings'] = warnings
    site_data._write_json(path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    args = parser.parse_args()
    result = write_events(args.data_dir)
    print(json.dumps({key: result[key] for key in ('article_count', 'event_count', 'cards_sha256')}))


if __name__ == '__main__':
    main()
