"""Bounded retrieval of public source evidence for one article. No model calls.

Fetched text is untrusted evidence, never instructions. Every hop is validated: http(s) only, no
credentials, default ports only, and every resolved address must be public; the connection is
pinned to the validated address so DNS cannot change between check and use. Redirects, bytes and
time are capped. Paywalls, bot checks and aggregator redirect pages are reported, never bypassed.
Excerpts are cached outside public/; cards carry only provenance (status, level, hash, times).
"""
import hashlib
import html.parser
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / 'work' / 'evidence-cache'
MAX_BYTES = 1_000_000
MAX_REDIRECTS = 3
TIMEOUT = 10
MAX_EXCERPT = 2500
MIN_EXCERPT = 200
AGGREGATORS = {'news.google.com'}
TEXT_TYPES = ('text/html', 'application/xhtml+xml', 'text/plain')
USER_AGENT = 'Mozilla/5.0 (compatible; FundCoverageNews/1.0; +https://github.com/Bobksl/Fund-Coverage-News-Dashboard)'
PUBLISHED_META = ('article:published_time', 'datePublished', 'pubdate', 'publish-date', 'date')
# SEC fair-access policy requires a declared contact; the address comes from the environment, never the repo.
SEC_CONTACT_ENV = 'SEC_CONTACT_EMAIL'
# End of the standard SEC form cover page; everything before it is boilerplate.
SEC_COVER_END = re.compile(r'Section 13\(a\) of the Exchange Act\.\s*\S?')


def user_agent(host, environ=os.environ):
    contact = environ.get(SEC_CONTACT_ENV, '').strip()
    if contact and (host == 'sec.gov' or host.endswith('.sec.gov')):
        return f'FundCoverageNews/1.0 {contact}'
    return USER_AGENT


def _resolve(host):
    return sorted({info[4][0] for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})


def _public(address):
    ip = ipaddress.ip_address(address.split('%', 1)[0])
    if getattr(ip, 'ipv4_mapped', None):
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


class _Pinned(http.client.HTTPSConnection):
    """TLS to a pre-validated IP while verifying the certificate for the real host name."""

    def __init__(self, host, ip, port, timeout, tls):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ip, self._tls = ip, tls

    def connect(self):
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host) if self._tls else sock


def _send(scheme, host, ip, port, target, deadline):
    timeout = max(0.5, min(TIMEOUT, deadline - time.monotonic()))
    conn = _Pinned(host, ip, port, timeout, scheme == 'https')
    try:
        conn.request('GET', target, headers={'Host': host, 'User-Agent': user_agent(host),
                                             'Accept': 'text/html,application/xhtml+xml;q=0.9,text/plain;q=0.5'})
        response = conn.getresponse()
        body = b''
        while len(body) <= MAX_BYTES:
            if time.monotonic() > deadline:
                raise TimeoutError('time cap reached')
            chunk = response.read(65536)
            if not chunk:
                break
            body += chunk
        return response.status, {k.lower(): v for k, v in response.getheaders()}, body[:MAX_BYTES + 1]
    finally:
        conn.close()


class _Extract(html.parser.HTMLParser):
    SKIP = frozenset({'script', 'style', 'noscript', 'svg', 'nav', 'header', 'footer', 'form', 'aside', 'template'})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth, self.title, self.meta, self.paragraphs, self._p = 0, '', {}, [], None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in self.SKIP:
            self.depth += 1
        elif tag == 'title':
            self._in_title = True
        elif tag == 'meta':
            key = attrs.get('property') or attrs.get('name') or attrs.get('itemprop')
            if key and attrs.get('content'):
                self.meta.setdefault(key, attrs['content'])
        elif tag in ('p', 'li', 'h1', 'h2') and not self.depth:
            self._p = []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.depth = max(0, self.depth - 1)
        elif tag == 'title':
            self._in_title = False
        elif tag in ('p', 'li', 'h1', 'h2') and self._p is not None:
            text = ' '.join(''.join(self._p).split())
            if len(text) > 30:
                self.paragraphs.append(text)
            self._p = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._p is not None and not self.depth:
            self._p.append(data)


def _published(meta, raw):
    for key in PUBLISHED_META:
        if meta.get(key):
            return meta[key].strip()
    match = re.search(rb'"datePublished"\s*:\s*"([^"]{8,40})"', raw)
    return match.group(1).decode('ascii', 'replace') if match else None


def extract(raw, content_type):
    charset = re.search(r'charset=([\w-]+)', content_type or '')
    text = raw.decode(charset.group(1) if charset else 'utf-8', 'replace')
    if content_type.startswith('text/plain'):
        return {'title': '', 'excerpt': ' '.join(text.split())[:MAX_EXCERPT], 'source_published_at': None}
    parser = _Extract()
    parser.feed(text)
    description = parser.meta.get('og:description') or parser.meta.get('description') or ''
    parts = [description] + [p for p in parser.paragraphs if p not in description]
    body = ' '.join(' '.join(parts).split())
    cover = SEC_COVER_END.search(body[:8000])
    if cover:
        body = body[cover.end():].strip()
    return {'title': ' '.join((parser.meta.get('og:title') or parser.title).split()),
            'excerpt': body[:MAX_EXCERPT],
            'source_published_at': _published(parser.meta, raw)}


def _result(url, status, started, **extra):
    record = {'status': status, 'requested_url': url, 'level': 'headline_only',
              'retrieved_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'elapsed_s': round(time.monotonic() - started, 2)}
    record.update(extra)
    return record


def retrieve(url, *, resolve=_resolve, send=_send, cache_dir=None, keep_html=False):
    """Return an evidence record. `excerpt` is present only when text was retrieved.

    keep_html adds the decoded page as `html` (for link discovery such as EDGAR indexes); such
    records are not cached and must never be published.
    """
    cache = Path(cache_dir) / (hashlib.sha256(url.encode()).hexdigest()[:24] + '.json') if cache_dir else None
    if cache and cache.exists() and not keep_html:
        return json.loads(cache.read_text(encoding='utf-8'))
    started = time.monotonic()
    deadline = started + 3 * TIMEOUT
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        parts = urlsplit(current)
        try:
            port = parts.port
        except ValueError:
            return _result(url, 'invalid_url', started)
        if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password
                or port not in (None, 80, 443)):
            return _result(url, 'invalid_url', started)
        host = parts.hostname.lower()
        if host in AGGREGATORS:
            return _result(url, 'unresolved_aggregator', started, final_url=current)
        try:
            addresses = resolve(host)
        except OSError:
            return _result(url, 'error', started, detail='name resolution failed')
        if not addresses or not all(_public(a) for a in addresses):
            return _result(url, 'blocked_address', started, final_url=current)
        target = (parts.path or '/') + ('?' + parts.query if parts.query else '')
        try:
            status, headers, body = send(parts.scheme, host, addresses[0], port or (443 if parts.scheme == 'https' else 80),
                                         target, deadline)
        except (OSError, http.client.HTTPException, TimeoutError) as error:
            return _result(url, 'error', started, final_url=current, detail=type(error).__name__)
        if status in (301, 302, 303, 307, 308) and headers.get('location'):
            current = urljoin(current, headers['location'])
            continue
        if status in (401, 402, 403, 429, 451):
            return _result(url, 'access_denied', started, final_url=current, http_status=status)
        if status != 200:
            return _result(url, 'http_error', started, final_url=current, http_status=status)
        if len(body) > MAX_BYTES:
            return _result(url, 'too_large', started, final_url=current)
        content_type = headers.get('content-type', 'text/html').lower()
        if not content_type.startswith(TEXT_TYPES):
            return _result(url, 'unsupported_content', started, final_url=current, content_type=content_type)
        page = extract(body, content_type)
        record = _result(url, 'ok', started, final_url=current, http_status=status, title=page['title'],
                         source_published_at=page['source_published_at'], excerpt=page['excerpt'],
                         sha256=hashlib.sha256(page['excerpt'].encode()).hexdigest(),
                         level='excerpt' if len(page['excerpt']) >= MIN_EXCERPT else 'headline_only')
        if keep_html:
            record['html'] = body.decode('utf-8', 'replace')
        elif cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        return record
    return _result(url, 'too_many_redirects', started, final_url=current)


def provenance(record):
    """The subset safe to publish on a card: no publisher text."""
    return {key: record[key] for key in ('status', 'level', 'retrieved_at', 'sha256', 'source_published_at',
                                         'final_url') if record.get(key) is not None}


def edgar_document(index_html, index_url):
    """The document to read from an EDGAR filing index: a press-release exhibit, else the main form."""
    rows = []
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', index_html, re.DOTALL | re.IGNORECASE):
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)]
        link = re.search(r'href="([^"]+\.htm)"', row, re.IGNORECASE)
        if link and len(cells) >= 4:
            rows.append((cells[3].upper(), link.group(1).replace('/ix?doc=', '')))
    chosen = next((href for kind, href in rows if kind.startswith('EX-99')), rows[0][1] if rows else None)
    return urljoin(index_url, chosen) if chosen else None
