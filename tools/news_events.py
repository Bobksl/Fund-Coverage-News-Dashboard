"""Lossless event projection over immutable per-day news cards. No model calls."""
import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tools import news_priority, summarize

ROOT = Path(__file__).resolve().parents[1]
GROUPS_PATH = ROOT / 'config' / 'news_event_groups.json'
VERSION = 'events-v2'
# Reviewed member roles: coverage/reaction never advance material time; a reviewed update does.
ROLES = ('coverage', 'reaction', 'update')
NOVELTY_WINDOW_S = 7 * 86400
# An exact repeated headline is evidence of one story only with a discriminating anchor
# (figure, quarter or month); "Apollo announces quarterly results" alone proves nothing.
ANCHOR = re.compile(r'\d|\b(?:first|second|third|fourth) quarter\b|\bq[1-4]\b|\b(?:january|february|march|april|'
                    r'may|june|july|august|september|october|november|december)\b', re.IGNORECASE)


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
    # Informative length ignores "no further details" filler, which otherwise wins on length.
    return min(members, key=lambda c: (c.get('review_status') != 'reviewed',
                                      not (c.get('assessment') or {}).get('assessable', False),
                                      -len(summarize.strip_absence_claims(c['summary']['en'])),
                                      epoch(card_stamp(c)), c['id']))


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


def load_overlay(path=GROUPS_PATH):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _approved(cards, groups):
    """Card ID -> reviewed group, for groups whose present members all still match their hashes."""
    seen = {}
    for group in groups:
        for member in group['members']:
            if member['id'] in seen:
                raise ValueError(f"card {member['id']} is in two reviewed groups: {seen[member['id']]}, {group['event_id']}")
            seen[member['id']] = group['event_id']
    by_id = {c['id']: c for c in cards}
    approved = {}
    for group in groups:
        present = [m for m in group['members'] if m['id'] in by_id]
        # Any changed card invalidates the whole decision, not just one member.
        if all(by_id[m['id']]['headline']['en'] == m['headline'] and
               (not m.get('card_sha256') or card_hash(by_id[m['id']]) == m['card_sha256']) for m in present):
            for member in present:
                approved[member['id']] = group
    return approved


def _corrections(cards, overlay):
    """Hash-checked publication-date corrections; the raw card keeps its original value."""
    by_id = {c['id']: c for c in cards}
    valid = {}
    for fix in overlay.get('corrections', []):
        card = by_id.get(fix.get('card_id'))
        if (card and fix.get('field') == 'published_at' and card.get('published_at') == fix.get('original')
                and card_hash(card) == fix.get('card_sha256')):
            valid[card['id']] = fix
    return valid


def headline_key(card):
    title = card.get('source_headline')
    return normalize_title(title) if title and ANCHOR.search(title) else None


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


def build_events(cards, *, groups=None, overlay=None, previous=None, as_of=None, backfill=None):
    if overlay is None:
        overlay = load_overlay() if groups is None else {'groups': groups}
    if len({c['id'] for c in cards}) != len(cards):
        raise ValueError('duplicate source card IDs')
    as_of = as_of or datetime.now(timezone.utc).isoformat(timespec='seconds')
    approved = _approved(cards, overlay.get('groups', []))
    fixes = _corrections(cards, overlay)
    raw_cards = cards
    # Evidence backfill (public/data/backfill.json) replaces a card's assessment and summary only while
    # the card still matches the hash it was re-briefed from; day files are never rewritten.
    entries = (backfill or {}).get('cards') or {}
    updates = {c['id']: entries[c['id']] for c in cards
               if isinstance(entries.get(c['id']), dict) and entries[c['id']].get('assessment')
               and entries[c['id']].get('card_sha256') == card_hash(c)}
    cards = [dict(c, assessment=updates[c['id']]['assessment'], summary=updates[c['id']]['summary'])
             if c['id'] in updates else c for c in cards]

    def stamp(card):
        fix = fixes.get(card['id'])
        if fix:
            value = fix['corrected']
            return value if 'T' in value else value + 'T00:00:00+08:00'
        return card_stamp(card)

    def when(card):
        return (epoch(stamp(card)), card['id'])

    prior, prior_aliases = {}, {}
    for event in (previous or {}).get('events', []):
        prior_aliases[event['event_id']] = event.get('aliases', [])
        for cid in event['member_card_ids']:
            prior[cid] = event['event_id']
    buckets, card_keys, heads = {}, {}, {}
    by_id = {c['id']: c for c in cards}
    ordered = sorted(cards, key=when)
    # Reviewed decisions first, so later repeats of a reviewed story can find it archive-wide.
    for card in ordered:
        if card['id'] in approved:
            key = ('reviewed', approved[card['id']]['event_id'])
            card_keys[card['id']] = key
            buckets.setdefault(key, []).append(card)
            if headline_key(card):
                heads.setdefault(headline_key(card), []).append((key, epoch(stamp(card))))
    for card in ordered:
        if card['id'] in approved:
            continue
        head = headline_key(card)
        if head:
            moment = epoch(stamp(card))
            key = next((k for k, start in heads.get(head, []) if abs(moment - start) <= NOVELTY_WINDOW_S), None)
            if key is None:
                key = ('headline', head, card['id'])
                heads.setdefault(head, []).append((key, moment))
        else:
            key = _auto_key(card)
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
    for key, members in sorted(buckets.items(), key=lambda kv: (kv[0][0] != 'reviewed', min(map(when, kv[1])))):
        members.sort(key=when)
        group = approved[members[0]['id']] if key[0] == 'reviewed' else {}
        # Survivor: reviewed ID, else the prior event of the earliest member; never an ID already taken.
        event_id = key[1] if group else next((prior[c['id']] for c in members if c['id'] in prior
                                              and prior[c['id']] not in used_ids), 'evt-' + members[0]['id'])
        if event_id in used_ids:
            event_id = 'evt-' + members[0]['id']
        used_ids.add(event_id)
        roles = {m['id']: m['role'] for m in group.get('members', [])
                 if m['id'] in by_id and m.get('role', 'coverage') != 'coverage'}
        pinned = next((c for c in members if c['id'] == group.get('representative_card_id')), None)
        revisions = [c for c in members if c.get('supersedes_card_id')]
        latest_revision = max(revisions, key=lambda c: (epoch(c.get('observed_at') or stamp(c)), c['id'])) if revisions else None
        chosen = pinned or latest_revision or representative(members)
        first = members[0]
        views = {}
        for day in sorted({c['date'] for c in members}):
            on_day = [c for c in members if c['date'] == day]
            day_revisions = [c for c in on_day if c.get('supersedes_card_id')]
            if pinned in on_day:
                day_chosen = pinned
            elif day_revisions:
                day_chosen = max(day_revisions, key=lambda c: (epoch(c.get('observed_at') or stamp(c)), c['id']))
            else:
                day_chosen = representative(on_day)
            views[day] = {'representative_card_id': day_chosen['id'],
                          'display_gps': display_gps(day_chosen), 'display_sectors': day_chosen['sectors'],
                          'member_card_ids': sorted(c['id'] for c in on_day),
                          'further_coverage': day != first['date']}
            views[day]['priority'] = news_priority.classify(card_assessment(day_chosen),
                                                           as_of=day + 'T23:59:59+08:00')
        priority = news_priority.classify(card_assessment(chosen), as_of=as_of)
        # Novelty: repeats never move material time; reviewed updates and confirmed revisions can.
        material = [stamp(first)] + [stamp(c) for c in members if roles.get(c['id']) == 'update']
        if latest_revision and latest_revision.get('material_update_confirmed') is True:
            material.append(latest_revision.get('observed_at') or stamp(latest_revision))
        sources = []
        for c in members:
            source = dict(c['source'], card_id=c['id'], published_at=stamp(c))
            if c['id'] in fixes:
                source['date_correction'] = {k: fixes[c['id']][k] for k in (
                    'original', 'corrected', 'basis', 'evidence_url', 'event_date', 'decision') if k in fixes[c['id']]}
            sources.append(source)
        rule = key[0] if not (key[0] == 'headline' and len(members) == 1) else _auto_key(first)[0]
        absorbed = {a for c in members if c['id'] in prior for a in [prior[c['id']], *prior_aliases.get(prior[c['id']], [])]}
        events.append({'event_id': event_id, 'member_card_ids': sorted(c['id'] for c in members),
                       'representative_card_id': chosen['id'], 'date_views': views,
                       'display_gps': display_gps(chosen), 'display_sectors': chosen['sectors'],
                       'first_seen_at': stamp(first), 'last_material_update_at': max(material, key=epoch),
                       'timestamp_basis': ('corrected' if first['id'] in fixes else
                                           'published_at' if first.get('published_at') == card_stamp(first) else 'date_only'),
                       'updated': bool(revisions), 'priority': priority,
                       'last_source_revision_at': latest_revision.get('observed_at') if latest_revision else None,
                       'merge_rule': rule, 'member_roles': roles, 'sources': sources,
                       'aliases': set(group.get('aliases', [])) | absorbed})
    resolve = {}
    for event in events:
        event['aliases'] = sorted(event['aliases'] - used_ids)
        for name in [event['event_id'], *event['aliases']]:
            resolve[name] = event['event_id']
    related = {}
    for relation in overlay.get('relations', []):
        linked = {resolve[name] for name in relation['event_ids'] if name in resolve}
        for name in linked:
            related.setdefault(name, set()).update(linked - {name})
    for event in events:
        event['related_event_ids'] = sorted(related.get(event['event_id'], ()))
    ranked = sorted(events, key=news_priority.rank_key)
    for rank, event in enumerate(ranked, 1):
        event['priority_rank'] = rank
    for day in {day for event in events for day in event['date_views']}:
        on_day = [dict(event, priority=event['date_views'][day]['priority']) for event in events if day in event['date_views']]
        for rank, event in enumerate(sorted(on_day, key=news_priority.rank_key), 1):
            event['date_views'][day]['priority_rank'] = rank
    return {'schema_version': 1, 'grouping_version': VERSION, 'ranking_version': news_priority.VERSION, 'as_of': as_of,
            'overlay_version': overlay.get('version'), 'article_count': len(cards), 'event_count': len(events),
            'events': sorted(events, key=lambda e: e['event_id']),
            'card_updates': {cid: {'headline': e['headline'], 'summary': e['summary'],
                                   'evidence_level': (e.get('evidence') or {}).get('level'),
                                   'updated_at': e.get('checked_at'), 'prompt_version': e.get('prompt_version'),
                                   'model': e.get('model')} for cid, e in sorted(updates.items())},
            'cards_sha256': hashlib.sha256(json.dumps(sorted(raw_cards, key=lambda c: c['id']),
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
    backfill = None
    try:
        backfill = json.loads((data_dir / 'backfill.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        pass
    except (ValueError, UnicodeError):
        warnings.append('Evidence backfill file was invalid; original card text used.')
    result = build_events(cards, previous=previous, backfill=backfill if isinstance(backfill, dict) else None,
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
