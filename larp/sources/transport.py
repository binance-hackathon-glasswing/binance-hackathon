"""Allowlisted, bounded HTTP retrieval for free sources (IDEA-031 S2.6, AC-D04/AC-D06).

`AllowlistedClient.get(source, url, ...)` enforces: https only; host and path prefix in the source's allowlist;
redirects followed only to allowlisted URLs (at most 3); response bytes capped; bounded retries with
exponential backoff on network errors, HTTP 429 and 5xx; conditional requests (If-None-Match /
If-Modified-Since) from the cursor. The network itself is an injected `fetch(url, headers, timeout_s)
-> (status, headers, body)` that never follows redirects, so tests use fakes and only the read-only
connectivity probe uses `urllib_fetch`. Retrieved bytes are untrusted data.
"""

from dataclasses import dataclass
from urllib.parse import unquote, urljoin, urlsplit
import http.client
import hashlib
import json
import re
import time

_DOT_SEGMENT = re.compile(r"(?:^|/)\.{1,2}(?:/|$)")

USER_AGENT_DEFAULT = "LARP-free-source-ingest/1 (IDEA-031; no contact configured)"
DOJ_WIRE_CAP = 32_000_000  # bounded exception for excluded inline image bytes, not permitted text


class SourceError(Exception):
    """Retrieval refused or failed; the code is recorded in the source's health."""


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    headers: dict
    body: bytes | None
    url: str
    attempts: int
    truncated: bool
    wire_sha256: str | None = None
    wire_bytes: int | None = None
    media_removed: dict | None = None


def _doj_api(url):
    p = urlsplit(url)
    return p.scheme == 'https' and p.hostname == 'www.justice.gov' and p.path.startswith('/api/v1/press_releases')


def _doj_without_inline_images(body):
    """Remove only already-excluded img elements; never discard records or permitted body text.

    The hard wire bound is checked before JSON decoding. Retain original wire identity,
    and carry per-item exclusion counts to the permitted artifact's provenance.
    """
    if len(body) > DOJ_WIRE_CAP:
        raise SourceError('RESPONSE_TOO_LARGE')
    try:
        data = json.loads(body)
        rows = data['results']
        if type(rows) is not list or any(type(r) is not dict for r in rows):
            raise ValueError()
        removed = {}
        # A quoted '>' is part of an attribute, not the end of the image tag.
        image = re.compile(r'''<img\b(?:[^>"']|"[^"]*"|'[^']*')*>''', re.I)
        for row in rows:
            value = row.get('body')
            html = value.get('value') if type(value) is dict else value
            if type(html) is not str:
                continue
            from larp.sources.rights import NOT_COVERED
            if NOT_COVERED.search(html):
                # Do not remove an image attribute which could carry an item-level rights restriction.
                raise ValueError()
            cleaned, count = image.subn(' ', html)
            if count:
                if type(row.get('uuid')) is not str or row['uuid'] in removed:
                    raise ValueError()
                removed[row['uuid']] = count
                row['body'] = dict(value, value=cleaned) if type(value) is dict else cleaned
        if not removed:
            raise ValueError()
        return json.dumps(data, ensure_ascii=True, separators=(',', ':')).encode(), removed
    except (ValueError, KeyError, TypeError, RecursionError):
        raise SourceError('RESPONSE_TOO_LARGE') from None


def allowed(source, url: str) -> bool:
    """https, no credentials or odd port, an allowlisted host, and a path inside an allowlisted prefix after
    rejecting dot segments, encoded separators/dots and empty segments (S4-B d01)."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme != "https" or parts.username or parts.password or port not in (None, 443):
        return False
    path, decoded = parts.path, unquote(parts.path)
    if _DOT_SEGMENT.search(decoded) or "//" in path or "\\" in decoded or re.search(r"%2[ef]|%5c", path, re.I):
        return False
    for a in source.allow:
        prefix = a["path_prefix"]
        if parts.hostname == a["host"] and path.startswith(prefix) and (
                prefix.endswith("/") or len(path) == len(prefix) or path[len(prefix)] in "/.?"):
            return True
    return False


class AllowlistedClient:
    def __init__(self, fetch, *, sleep=time.sleep, user_agents: dict | None = None):
        self.fetch, self.sleep, self.user_agents = fetch, sleep, user_agents or {}

    def get(self, source, url: str, *, etag: str | None = None, last_modified: str | None = None) -> Response:
        limits = source.limits
        if not source.enabled:
            raise SourceError("SOURCE_DISABLED")
        if not allowed(source, url):
            raise SourceError("URL_NOT_ALLOWLISTED")
        headers = {"Accept": "application/json, application/rss+xml, application/xml;q=0.9, */*;q=0.1"}
        if source.requires_user_agent:
            agent = self.user_agents.get(source.requires_user_agent)
            if not agent:
                raise SourceError("USER_AGENT_NOT_CONFIGURED")
            headers["User-Agent"] = agent
        else:
            headers["User-Agent"] = USER_AGENT_DEFAULT
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        attempts, delay, current, redirects = 0, limits.get("backoff_ms", 1000), url, 0
        while True:
            attempts += 1
            try:
                status, reply_headers, body = self.fetch(current, headers, 30)
            except (OSError, TimeoutError, http.client.HTTPException) as exc:
                if attempts >= limits.get("max_attempts", 3):
                    raise SourceError(f"NETWORK_ERROR:{type(exc).__name__}:EXHAUSTED") from None
                self.sleep(delay / 1000)
                delay *= 2
                continue
            reply_headers = {k.lower(): v for k, v in (reply_headers or {}).items()}
            if status in (301, 302, 303, 307, 308):
                target = urljoin(current, reply_headers.get("location", ""))
                redirects += 1
                if redirects > 3 or not allowed(source, target):
                    raise SourceError("REDIRECT_NOT_ALLOWLISTED")
                current = target
                attempts -= 1  # a redirect is not a failed attempt
                continue
            if status == 429 or status >= 500:
                if attempts >= limits.get("max_attempts", 3):
                    raise SourceError(f"HTTP_{status}:EXHAUSTED")
                self.sleep(delay / 1000)
                delay *= 2
                continue
            if status == 304:
                return Response(304, reply_headers, None, current, attempts, False)
            if status != 200:
                raise SourceError(f"HTTP_{status}")
            cap = limits.get("max_response_bytes", 2_000_000)
            wire_sha, wire_bytes, removed = None, None, None
            if body is not None and len(body) > cap and source.format == 'DOJ_PRESS_JSON' and _doj_api(current):
                wire_sha, wire_bytes = hashlib.sha256(body).hexdigest(), len(body)
                body, removed = _doj_without_inline_images(body)
            truncated = body is not None and len(body) > cap
            if truncated:
                raise SourceError("RESPONSE_TOO_LARGE")
            return Response(200, reply_headers, body, current, attempts, truncated,
                            wire_sha, wire_bytes, removed)


class _NoRedirect:
    """urllib redirect handler that returns 3xx responses instead of following them."""

    def __new__(cls):
        import urllib.request

        class Handler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        return Handler()


def urllib_fetch(url: str, headers: dict, timeout_s: float) -> tuple:
    """Real network for the read-only connectivity probe only (no redirects followed, bounded read)."""
    import urllib.error
    import urllib.request
    opener = urllib.request.build_opener(_NoRedirect())
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with opener.open(request, timeout=timeout_s) as reply:  # noqa: S310 - allowlisted by the caller
            limit = DOJ_WIRE_CAP if _doj_api(url) else 8_000_000
            return reply.status, dict(reply.headers), reply.read(limit + 1)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), None
