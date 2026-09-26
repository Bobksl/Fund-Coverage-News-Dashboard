"""Evidence-linked ordinal news priority; never a weighted composite score."""
import hashlib
import re
import unicodedata
from datetime import datetime, timezone

VERSION = 'priority-v1'
ORDERS = {
    'priority': ['urgent', 'important', 'useful', 'needs_review'],
    'severity': ['critical', 'substantial', 'bounded', 'unknown'],
    # User decision 26 Sep 2026: scheduled/administrative disclosures rank below non-routine items of the
    # same class and severity (e.g. a BDC's monthly share sale below a strategy launch).
    'routine': [False, True],
    'time_sensitivity': ['48h', '7d', 'monitor'],
    'linkage': ['direct', 'sector', 'indirect', 'unknown'],
    'evidence_strength': ['primary', 'reported', 'unknown'],
}
RISK = re.compile(r'\b(payment default|defaulted|suspend(?:s|ed)? withdrawals|withdrawal suspension|'
                  r'redemption (?:gate|suspension)|bankruptcy|material impairment)\b', re.IGNORECASE)


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone required')
    return parsed


TYPOGRAPHY = str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"', '–': '-', '—': '-'})


def _plain(value):
    # Quote matching ignores typography and spacing only; wording must still be the source's own.
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', value).translate(TYPOGRAPHY)).strip()


def source_text(item):
    return str(item.get('text') or '').strip()


def validate_assessment(raw, item):
    """Require source spans for each decisive claim. Semantics remain model judgements.

    Source refs store offsets/hash, not whole publisher articles in the public archive.
    Headlines alone cannot substantiate a confirmed priority. Invalid assessment metadata
    does not discard an otherwise valid bilingual news card.
    """
    text = source_text(item)
    result = {'version': VERSION, 'assessable': False, 'potential_urgent': bool(RISK.search(
        str(item.get('title', '')) + ' ' + text)), 'evidence_refs': {},
        'source_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'failure': 'Missing or insufficient source evidence'}
    if not isinstance(raw, dict) or text == str(item.get('title', '')).strip() or not text:
        return result
    for name in ('severity', 'linkage'):
        if not isinstance(raw.get(name), str) or raw[name] not in ORDERS[name][:-1]:
            return result
    if type(raw.get('current_adverse')) is not bool or type(raw.get('resolved')) is not bool:
        return result
    quotes = raw.get('quotes')
    if not isinstance(quotes, dict):
        return result
    needed = ['severity', 'linkage']
    needed += [name for name in ('current_adverse', 'resolved') if raw[name]]
    deadline = raw.get('deadline_at')
    if deadline is not None:
        try:
            instant(deadline)
        except (TypeError, ValueError, AttributeError):
            return result
        needed.append('deadline_at')
    plain = _plain(text)
    for name in needed:
        quote = quotes.get(name)
        if isinstance(quote, list) and len(quote) == 1:
            quote = quote[0]  # a one-item list is a formatting slip, not a different claim
        if not isinstance(quote, str) or len(quote.strip()) < 8 or _plain(quote) not in plain:
            result['failure'] = 'Unsupported assessment claim: ' + name
            return result
        # Absolute deadline must be present literally; do not let the model invent date math.
        if name == 'deadline_at' and deadline not in quote:
            return result
        start = plain.index(_plain(quote))  # offsets refer to the whitespace/typography-normalised text
        result['evidence_refs'][name] = {'start': start, 'end': start + len(_plain(quote))}
    if not all(isinstance(raw.get('reason_' + lang), str) and raw['reason_' + lang].strip()
               for lang in ('en', 'zh')) or not re.search(r'[\u4e00-\u9fff]', raw['reason_zh']):
        return result
    result.update({key: raw[key] for key in ('severity', 'linkage', 'current_adverse', 'resolved')})
    # Routine only demotes, so it needs no quote; anything but a real boolean counts as not routine. It is honoured
    # only for verified primary sources (filings, regulator releases): on press items the flag was mostly wrong.
    result.update(assessable=True, deadline_at=deadline, evidence_strength='reported',
                  routine=raw.get('routine') is True and item.get('verified_primary_source') is True,
                  reason={'en': raw['reason_en'], 'zh': raw['reason_zh']}, failure=None)
    # Primary strength requires a separately verified source classification; model cannot grant it.
    if item.get('verified_primary_source') is True:
        result['evidence_strength'] = 'primary'
    return result


def classify(assessment, *, as_of=None):
    as_of = as_of or datetime.now(timezone.utc).isoformat(timespec='seconds')
    now = instant(as_of)
    a = assessment if isinstance(assessment, dict) else {}
    p = {'version': VERSION, 'as_of': as_of, 'priority': 'needs_review', 'severity': 'unknown',
         'time_sensitivity': 'monitor', 'linkage': 'unknown', 'evidence_strength': 'unknown', 'routine': False,
         'potential_urgent': a.get('potential_urgent') is True,
         'reason': {'en': a.get('failure') or 'Evidence has not been assessed.',
                    'zh': '证据尚未充分核实，需人工复核。'}}
    if a.get('assessable') is not True or a.get('version') != VERSION:
        return p
    for name in ('severity', 'linkage', 'evidence_strength'):
        if not isinstance(a.get(name), str) or a[name] not in ORDERS[name][:-1]:
            return p
    if type(a.get('current_adverse')) is not bool or type(a.get('resolved')) is not bool:
        return p
    if not isinstance(a.get('reason'), dict) or not all(isinstance(a['reason'].get(lang), str)
                                                      for lang in ('en', 'zh')):
        return p
    deadline = a.get('deadline_at')
    bucket = 'monitor'
    if deadline:
        try:
            hours = (instant(deadline) - now).total_seconds() / 3600
        except (ValueError, TypeError, AttributeError):
            return p
        if 0 <= hours <= 48:
            bucket = '48h'
        elif 48 < hours <= 168:
            bucket = '7d'
    critical = a['severity'] == 'critical' and a['current_adverse'] and not a['resolved']
    material_deadline = a['severity'] in ('critical', 'substantial') and bucket != 'monitor' and not a['resolved']
    tier = 'urgent' if critical or material_deadline else (
        'important' if a['severity'] in ('critical', 'substantial') else 'useful')
    p.update(priority=tier, severity=a['severity'], time_sensitivity=bucket,
             linkage=a['linkage'], evidence_strength=a['evidence_strength'],
             routine=a.get('routine') is True and a['evidence_strength'] == 'primary',
             potential_urgent=False, reason=a['reason'])
    return p


def rank_key(event):
    p = event['priority']
    order = tuple(values.index(p.get(name)) if p.get(name) in values else len(values)
                  for name, values in ORDERS.items())
    return (*order, -instant(event['last_material_update_at']).timestamp(), event['event_id'])
