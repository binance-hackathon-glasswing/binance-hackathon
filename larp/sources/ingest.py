"""Point-in-time ingestion of free official sources into SourceDocument.v1 records (IDEA-031 S2.6).

`SourceIngestor.poll(source_id)` reads at most `max_pages` listing pages and commits each page (records + cursor)
in one durable transaction, so a crash between pages resumes from the saved page URL without duplicating or
skipping items. The first page is requested conditionally (ETag / Last-Modified). A failure marks only that
source's health (other sources and their consumers are unaffected) and is retried on a later poll; the
client's own retries are bounded with backoff.

Each record stores: source, publisher and original publisher, canonical URL, item version (n+1 when the
permitted content changes; WITHDRAWN when the source says so), content hash and the artifact hashes of the
permitted raw item and its saved text (artifacts live outside Git), licence/attribution and the register
hash, exclusions applied, publication time with precision, source event/effective times, retrieval and
first-seen time, `available_ms` = this version's first retrieval (never earlier), a conservative
replay bound for date-only publication times, untrusted-instruction flags, a common-origin fingerprint,
and the source statement (what the authority said or did, with issuer mentions; effect UNKNOWN).
Earlier versions are never rewritten. No record carries trading authority.
"""

from larp.contracts import Document
from larp.intelligence.common import digest
from larp.intelligence.semantics import classify_source_statement
from larp.intelligence.text import document_text
from larp.intelligence.tools import suspicious_instructions
from larp.sources.parse import parse
from larp.sources.rights import filter_item
from larp.sources.store import canonical
from larp.sources.transport import SourceError, allowed

MAX_RESUME_FAILURES = 3  # a continuation that keeps failing is abandoned and the listing restarts at page 1

DAY_MS = 86_400_000
# A date-only publication time could mean any instant of that day in the publisher's zone; for historical replay
# the earliest instant the text may be treated as public is the end of that day at UTC-12 (36 h after 00:00 UTC).
DATE_ONLY_REPLAY_BOUND_MS = DAY_MS + 12 * 3_600_000


def initial_cursor(source_id: str) -> dict:
    return {"schema": "SourceCursor.v1", "source_id": source_id, "version": 0, "seen": {}, "rejected": {},
            "in_progress": None, "etag": None, "last_modified": None, "watermark_ms": None, "last_truncated": False,
            "health": {"status": "NEVER_POLLED", "last_success_ms": None, "last_attempt_ms": None,
                       "consecutive_failures": 0, "last_error": None}}


class SourceIngestor:
    def __init__(self, *, register: dict, register_sha256: str, aliases: dict, client, store, artifacts, clock_ms,
                 max_seen: int = 20_000):
        self.register, self.register_sha256, self.aliases = register, register_sha256, aliases
        self.client, self.store, self.artifacts, self.clock, self.max_seen = client, store, artifacts, clock_ms, max_seen

    def poll(self, source_id: str) -> dict:
        source = self.register[source_id]
        if not source.enabled:
            return {"source_id": source_id, "status": "DISABLED", "reason": source.status_reason}
        stored = self.store.cursor(source_id)
        cursor = stored or initial_cursor(source_id)
        expected = cursor["version"] if stored else -1
        outcome = {"source_id": source_id, "status": "OK", "pages": 0, "new": [], "versions": [], "withdrawn": [],
                   "duplicates": 0, "rejected": [], "resumed": cursor["in_progress"] is not None, "truncated": False}
        progress = cursor["in_progress"] or {}
        if progress and (progress.get("failures", 0) >= MAX_RESUME_FAILURES or not allowed(source, progress["next_url"])):
            outcome["abandoned_continuation"] = progress.get("next_url")  # wedged or poisoned (S4-B d07)
            cursor = dict(cursor, in_progress=None)
        url = (cursor["in_progress"] or {}).get("next_url") or source.listing_url
        first = cursor["in_progress"] is None
        pages_done = (cursor["in_progress"] or {}).get("pages_done", 0)
        while url and pages_done < source.limits.get("max_pages", 1):
            now = self.clock()
            health = dict(cursor["health"], last_attempt_ms=now)
            try:
                response = self.client.get(source, url, etag=cursor["etag"] if first else None,
                                           last_modified=cursor["last_modified"] if first else None)
                if response.status == 304:
                    items, next_url = [], None
                    outcome["status"] = "NOT_MODIFIED"
                else:
                    items, next_url = parse(source, response.body, response.url)
            except SourceError as exc:
                health.update(status="UNAVAILABLE", consecutive_failures=health["consecutive_failures"] + 1,
                              last_error=str(exc))
                progress = cursor["in_progress"]
                if progress:
                    progress = dict(progress, failures=progress.get("failures", 0) + 1)
                cursor = dict(cursor, version=cursor["version"] + 1, health=health, in_progress=progress)
                self.store.commit({"cursor": cursor, "records": [], "expected_cursor_version": expected})
                return dict(outcome, status="SOURCE_UNAVAILABLE", error=str(exc))
            records = []
            seen, rejected = dict(cursor["seen"]), dict(cursor["rejected"])
            for item in items:
                previous = seen.get(item["item_id"])
                if previous is None:  # the cursor cache is bounded; the store is the durable item index (S4-B d06)
                    stored_record = self.store.latest(source.source_id, item["item_id"])
                    if stored_record is not None:
                        previous = {"version": stored_record["version"], "content_hash": stored_record["content_hash"],
                                    "record_id": stored_record["record_id"], "status": stored_record["status"],
                                    "first_seen_ms": stored_record["first_seen_ms"],
                                    "published_ms": stored_record["published"]["ms"]}
                record, why = self._record(source, item, previous, now, response)
                if why == "DUPLICATE":
                    outcome["duplicates"] += 1
                    continue
                if why:
                    rejected[item["item_id"]] = {"reason": why, "at_ms": now}
                    outcome["rejected"].append([item["item_id"], why])
                    continue
                records.append(record)
                seen[item["item_id"]] = {"version": record["version"], "content_hash": record["content_hash"],
                                         "record_id": record["record_id"], "status": record["status"],
                                         "first_seen_ms": record["first_seen_ms"],
                                         "published_ms": record["published"]["ms"]}
                key = "withdrawn" if record["status"] == "WITHDRAWN" else "versions" if record["version"] else "new"
                outcome[key].append(record["record_id"])
            pages_done += 1
            if next_url and not allowed(source, next_url):
                outcome["rejected_next_page"] = next_url  # never saved as a continuation (S4-B d07)
                next_url = None
            more = next_url and pages_done < source.limits.get("max_pages", 1)
            if next_url and not more:
                outcome["truncated"] = True  # page limit reached with pages left: coverage is incomplete
            published = [r["published"]["ms"] for r in records if r["published"]["ms"] is not None]
            cursor = dict(cursor, version=cursor["version"] + 1, seen=self._bounded(seen), rejected=rejected,
                          in_progress={"next_url": next_url, "pages_done": pages_done} if more else None,
                          watermark_ms=max([cursor["watermark_ms"] or 0] + published) or None,
                          last_truncated=bool(outcome["truncated"]),
                          health=dict(health, status="OK", last_success_ms=now, consecutive_failures=0,
                                      last_error=None))
            if first and response.status == 200:
                cursor.update(etag=response.headers.get("etag"), last_modified=response.headers.get("last-modified"))
            self.store.commit({"cursor": cursor, "records": records, "expected_cursor_version": expected})
            expected = cursor["version"]
            outcome["pages"] += 1
            first = False
            url = next_url if more else None
        return outcome

    def _bounded(self, seen: dict) -> dict:
        if len(seen) <= self.max_seen:
            return seen
        keep = sorted(seen.items(), key=lambda kv: (kv[1].get("first_seen_ms") or 0, kv[0]))[-self.max_seen:]
        return dict(keep)

    def _record(self, source, item: dict, previous: dict | None, now: int, response) -> tuple:
        if item.get("published_precision") == "UNPARSEABLE":
            return None, "UNPARSEABLE_TIMESTAMP"
        body, exclusions, rejection = filter_item(item.get("title"), item.get("body_html"))
        if rejection:
            return None, rejection
        exclusions = exclusions + [f"FIELD_NOT_RETRIEVED:{f}" for f in item.get("excluded_fields", [])]
        permitted = {"title": item.get("title"), "body": body, "url": item.get("url"),
                     "published_raw": item.get("published_raw"), "doc_type": item.get("doc_type"),
                     "event_times": item.get("event_times"), "withdrawn": bool(item.get("withdrawn")),
                     "announces_withdrawal": bool(item.get("announces_withdrawal"))}
        content_hash = digest("larp.source.content.v1", permitted)
        # WITHDRAWN only when an item we already hold is withdrawn (or turns into a withdrawal notice); a new document
        # announcing the withdrawal of something else is an ACTIVE document about a withdrawal (S4-B d08).
        status = ("WITHDRAWN" if previous and (item.get("withdrawn") or item.get("announces_withdrawal"))
                  else "ACTIVE")
        if previous and previous["content_hash"] == content_hash and previous["status"] == status:
            return None, "DUPLICATE"
        raw = canonical(permitted)
        html = "".join(f"<p>{x}</p>" for x in (item.get("title"),) if x) + (body or "")
        saved = document_text(html.encode("utf-8"), "item.html", "text/html")
        if self.artifacts.put(raw) != digest_bytes(raw) or self.artifacts.put(saved.saved_bytes) != saved.text_sha256:
            raise RuntimeError("Artifact store returned a different content address")
        precision = item.get("published_precision")
        published_ms = item.get("published_ms")
        record = {
            "schema": "SourceDocument.v1", "source_id": source.source_id, "publisher": source.publisher,
            "original_publisher": source.original_publisher, "actor": source.actor, "kind": source.kind,
            "item_id": item["item_id"], "canonical_url": item.get("url"), "doc_type": item.get("doc_type"),
            "version": previous["version"] + 1 if previous else 0,
            "supersedes": previous["content_hash"] if previous else None, "status": status,
            "content_hash": content_hash, "raw_sha256": digest_bytes(raw), "text_sha256": saved.text_sha256,
            "text_chars": len(saved.text), "title": item.get("title"),
            "licence": {k: source.rights[k] for k in ("basis", "licence_id", "terms_url", "terms_checked",
                                                       "terms_evidence_sha256", "attribution")}
            | {"register_sha256": self.register_sha256},
            "exclusions": exclusions,
            "published": {"raw": item.get("published_raw"), "ms": published_ms, "precision": precision,
                          "replay_available_bound_ms": (None if published_ms is None else
                                                        published_ms + DATE_ONLY_REPLAY_BOUND_MS
                                                        if precision == "DAY" else published_ms)},
            "event_times": item.get("event_times") or {}, "changed_raw": item.get("changed_raw"),
            "retrieved_ms": now, "available_ms": now,
            "first_seen_ms": previous["first_seen_ms"] if previous else now,
            "listing": {"url": response.url, "attempts": response.attempts},
            "untrusted_instructions": sorted(suspicious_instructions(saved.text)),
            "statement": classify_source_statement(saved.text, source_kind=source.kind, actor=source.actor,
                                                   aliases=self.aliases),
            "authority": "SHADOW_ONLY",
        }
        record["record_id"] = "src:" + Document.from_dict(record).digest("larp.source.record.v1")
        return record, None


def digest_bytes(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def coverage(register: dict, store, dependencies: dict, now_ms: int, max_age_ms: int) -> dict:
    """Per consumer: which of its declared sources are unhealthy or stale. A source failure affects only the
    consumers that declare it; enabled sources nobody depends on are still reported."""
    health = {}
    for source_id, source in register.items():
        if not source.enabled:
            continue
        cursor = store.cursor(source_id)
        h = (cursor or initial_cursor(source_id))["health"]
        fresh = h["last_success_ms"] is not None and now_ms - h["last_success_ms"] <= max_age_ms
        health[source_id] = {"status": h["status"] if fresh or h["status"] != "OK" else "STALE",
                             "last_success_ms": h["last_success_ms"], "last_error": h["last_error"]}
    consumers = {name: {"impaired": sorted(s for s in deps if health.get(s, {}).get("status") != "OK"),
                        "complete": all(health.get(s, {}).get("status") == "OK" for s in deps)}
                 for name, deps in dependencies.items()}
    return {"schema": "SourceCoverage.v1", "as_of_ms": now_ms, "sources": health, "consumers": consumers}
