"""Statement identity, novelty and the review lifecycle (IDEA-030 R06/R07, IDEA-031 S2.4-S2.5).

Three questions IDEA-030 found conflated are kept apart:

1. Is this the same *text* as before? `exact_key`: the clause, case/space-normalised.
2. Is it the same *statement*? `semantic_signature`: event, assertion class, actor, temporal frame,
   anchors (numbers, dates, years) and content words with modal verbs and light function words
   normalised, so "could" -> "may" or reordered wording is the same statement, while a changed
   date, amount, actor or event type is a substantive change. A pair in the gray zone is reported
   as UNCERTAIN_MATCH, never silently merged.
3. Was earlier history actually checked? PRIOR_NOT_CHECKED (no lookup), HISTORY_UNAVAILABLE (lookup
   failed or truncated), FIRST_SEEN (complete lookup, no match). None of these means "market news".

The registry kept in the evidence state (gate.py) gives each statement a stable `statement_id`
from its semantic signature, so rereading the same filing, a syndicated copy or a harmless
paraphrase maps to the same entry, and records review status with bounded retries:

PENDING_REVIEW -> ACKNOWLEDGED (seen again by a complete assessment with prior history checked)
PENDING_REVIEW -> PENDING_REVIEW (incomplete reassessment; attempts+1, exponential backoff)
PENDING_REVIEW -> REVIEW_EXHAUSTED (max attempts; stays visible as uncertainty, no further jobs)
any -> SUPERSEDED / CORRECTED / WITHDRAWN (its only supporting record was revised or withdrawn)
any -> EXPIRED (not seen within the retention window; entries are bounded in number)

No transition requires a human. Statuses are evidence bookkeeping, not portfolio permission.
"""

import re

from larp.intelligence.common import digest

STATUSES = ("PENDING_REVIEW", "ACKNOWLEDGED", "REVIEW_EXHAUSTED", "SUPERSEDED", "CORRECTED", "WITHDRAWN",
            "EXPIRED", "RESOLVED")
OPEN_STATUSES = ("PENDING_REVIEW",)
NOVELTY = ("PRIOR_NOT_CHECKED", "HISTORY_UNAVAILABLE", "FIRST_SEEN", "REPEATED", "CHANGED", "UNCERTAIN_MATCH",
           "ALREADY_SEEN")
SAME_THRESHOLD = (4, 5)      # Jaccard >= 0.8 of content words: same statement (with identical anchors)
UNCERTAIN_THRESHOLD = (1, 2)  # 0.5 <= Jaccard < 0.8, or anchors differ above 0.5: not silently merged

_MODAL = re.compile(r"\b(?:may|might|could|can|would|should)\b", re.I)
_STOP = frozenset("a an the of to in on for and or our we us its it this that these those is are be been being "
                  "was were has have had at by with from as any all such which who also other".split())
# Anchors: what makes two statements about the same event different facts. Numbers keep their currency and
# scale ("$1.2 billion" vs "$1.2 million"); dates, years, quarter ordinals, officer titles and third-party roles
# are a closed set (IDEA-031 red team S4-A f03-f06).
_ANCHOR = re.compile(r"\b(?:January|February|March|April|June|July|August|September|October|November|December|May(?=\s+\d))"
                     r"\s+\d{1,2}(?:,\s*\d{4})?|(?:US\$|\$|KRW\s?|\u20a9)?\d[\d,]*(?:\.\d+)?%?"
                     r"(?:\s*(?:thousand|million|billion|trillion))?|\b(?:first|second|third|fourth)\s+(?:fiscal\s+)?quarter\b|"
                     r"\b(?:chief\s+(?:executive|financial|operating|technology)\s+officer|CEO|CFO|COO|CTO|president|"
                     r"chair(?:man|woman|person)?)\b|\b(?:suppliers?|customers?|competitors?|vendors?|partners?)\b|"
                     r"\b(?:thousand|million|billion|trillion)\b", re.I)
_WORD = re.compile(r"[a-z][a-z\-]+")


def normalise(text: str) -> str:
    return " ".join(text.lower().split()).strip(" ,.;:")


def exact_key(text: str) -> str:
    return digest("larp.intel.statement-text.v1", {"t": normalise(text)})


def _stem(word: str) -> str:
    for suffix in ("ations", "ation", "ments", "ment", "ings", "ing", "ies", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def content_words(text: str) -> frozenset:
    plain = _ANCHOR.sub(" ", _MODAL.sub(" MODAL ", text))
    return frozenset(_stem(w) for w in _WORD.findall(plain.lower()) if w not in _STOP)


def anchors(text: str) -> tuple:
    return tuple(sorted({re.sub(r"s$", "", " ".join(a.lower().replace(",", "").split())) for a in _ANCHOR.findall(text)}))


def signature(event: str, semantics: dict | None, text: str) -> dict:
    sem = semantics or {}
    return {"event": event, "assertion": sem.get("assertion", "LEGACY_UNCLASSIFIED"),
            "actor": sem.get("actor", "UNSPECIFIED"), "temporal": sem.get("temporal", "UNKNOWN"),
            "effective": sem.get("effective"), "anchors": list(anchors(text)), "words": sorted(content_words(text))}


def statement_id(sig: dict) -> str:
    return "stmt:" + digest("larp.intel.statement.v1", sig)


def relation(new: dict, prior: dict) -> str:
    """EXACT | SEMANTIC_SAME | SUBSTANTIVE_CHANGE | UNCERTAIN_MATCH | UNRELATED for two signatures."""
    if new["event"] != prior["event"]:
        return "UNRELATED"
    a, b = set(new["words"]), set(prior["words"])
    union = a | b
    overlap = len(a & b) * SAME_THRESHOLD[1] if union else 0
    same_frame = all(new[k] == prior[k] for k in ("assertion", "actor", "temporal", "effective"))
    if new == prior:
        return "EXACT"
    high = union and overlap >= SAME_THRESHOLD[0] * len(union)
    mid = union and len(a & b) * UNCERTAIN_THRESHOLD[1] >= UNCERTAIN_THRESHOLD[0] * len(union)
    if high and same_frame and new["anchors"] == prior["anchors"]:
        return "SEMANTIC_SAME"
    if mid and (not same_frame or new["anchors"] != prior["anchors"]):
        return "SUBSTANTIVE_CHANGE"
    if mid:
        return "UNCERTAIN_MATCH"
    return "UNRELATED"


def novelty(new: dict, priors: list, *, checked: bool, history_complete: bool, max_comparisons: int) -> dict:
    """Novelty of one statement signature against prior signatures (bounded). Returns label, best match, counts."""
    if not checked:
        return {"label": "PRIOR_NOT_CHECKED", "match": None, "compared": 0, "truncated": False}
    compared, best, truncated = 0, None, False
    order = {"EXACT": 0, "SEMANTIC_SAME": 1, "SUBSTANTIVE_CHANGE": 2, "UNCERTAIN_MATCH": 3}
    for prior in priors:
        if compared >= max_comparisons:
            truncated = True
            break
        compared += 1
        rel = relation(new, prior["fingerprint"])
        if rel in order and (best is None or order[rel] < order[best[0]]):
            best = (rel, prior["id"])
            if rel == "EXACT":
                break
    if best is None:
        label = "FIRST_SEEN" if history_complete and not truncated else "HISTORY_UNAVAILABLE"
    else:
        label = {"EXACT": "REPEATED", "SEMANTIC_SAME": "REPEATED", "SUBSTANTIVE_CHANGE": "CHANGED",
                 "UNCERTAIN_MATCH": "UNCERTAIN_MATCH"}[best[0]]
    return {"label": label, "match": None if best is None else {"relation": best[0], "prior_id": best[1]},
            "compared": compared, "truncated": truncated}


# ------------------------------------------------------------------ registry transitions (pure)
def needs_review(label: str) -> bool:
    return label in ("FIRST_SEEN", "CHANGED", "UNCERTAIN_MATCH", "HISTORY_UNAVAILABLE", "PRIOR_NOT_CHECKED")


def observe(registry: dict, statement: dict, *, result_id: str, now_ms: int, complete: bool, policy: dict) -> dict:
    """Apply one verified statement from an accepted, ASSESSED result. Returns the updated entry.

    `statement`: AssessmentResult event_statements item (statement_id, event, semantics, novelty, source).
    `policy`: {"review_base_delay_ms", "max_review_attempts", "max_backoff_ms"}.
    """
    sid = statement["statement_id"]
    if sid not in registry and statement.get("fingerprint"):
        # A paraphrase or syndicated copy of a registered statement keeps that statement's identity.
        for other in list(registry.values())[: policy.get("max_registry_comparisons", 500)]:
            if other.get("fingerprint") and relation(statement["fingerprint"], other["fingerprint"]) in ("EXACT",
                                                                                                    "SEMANTIC_SAME"):
                sid = other["statement_id"]
                break
    entry = registry.get(sid)
    record = {"accession": statement.get("accession"), "record_id": statement.get("record_id"),
              "content_hash": statement.get("content_hash")}
    if entry is None:
        status = "PENDING_REVIEW" if needs_review(statement["novelty"]) else "ACKNOWLEDGED"
        entry = {"statement_id": sid, "event": statement["event"], "semantics": statement.get("semantics"),
                 "fingerprint": statement.get("fingerprint"),
                 "text": statement.get("statement"), "first_seen_ms": now_ms, "last_seen_ms": now_ms,
                 "first_result_id": result_id, "first_novelty": statement["novelty"], "status": status,
                 "records": [record], "review": {"attempts": 0, "next_due_ms": None, "last_result_id": result_id}}
        if status == "PENDING_REVIEW":
            entry["review"]["next_due_ms"] = now_ms + policy["review_base_delay_ms"]
        registry[sid] = entry
        return entry
    entry = dict(entry, last_seen_ms=now_ms, review=dict(entry["review"]))
    if entry.get("source_resolutions"):
        # A current observation of this support supersedes its earlier correction evidence.
        keys = {r.get("record_id") for r in entry["records"] if r.get("accession") == record["accession"]}
        entry["source_resolutions"] = {k: v for k, v in entry["source_resolutions"].items() if k not in keys}
    if record not in entry["records"]:
        entry["records"] = (entry["records"] + [record])[-8:]
    if entry["status"] == "PENDING_REVIEW" and result_id != entry["review"]["last_result_id"]:
        entry["review"]["last_result_id"] = result_id
        if complete:
            entry["status"] = "ACKNOWLEDGED"
            entry["review"]["next_due_ms"] = None
        else:
            attempts = entry["review"]["attempts"] + 1
            entry["review"]["attempts"] = attempts
            if attempts >= policy["max_review_attempts"]:
                entry["status"] = "REVIEW_EXHAUSTED"
                entry["review"]["next_due_ms"] = None
            else:
                delay = min(policy["max_backoff_ms"], policy["review_base_delay_ms"] * 2 ** attempts)
                entry["review"]["next_due_ms"] = now_ms + delay
    elif entry["status"] in ("SUPERSEDED", "CORRECTED", "WITHDRAWN", "EXPIRED"):
        # Seen again in current evidence: the statement is live again, but it is not news; it is acknowledged.
        entry["status"] = "ACKNOWLEDGED"
        entry["review"]["next_due_ms"] = None
    registry[sid] = entry
    return entry


def revise(registry: dict, *, accession: str, superseding_hash: str, still_present: set, withdrawn: bool,
           now_ms: int) -> list:
    """A later revision (or withdrawal) of `accession`: statements it no longer supports are corrected/withdrawn.

    Entries are kept. Corrections accumulate per supporting record until every support is invalidated.
    """
    changed = []
    for sid, entry in list(registry.items()):
        records = [r for r in entry["records"] if r.get("accession") == accession]
        if not records or sid in still_present:
            continue
        corrections = dict(entry.get("source_resolutions", {}))
        for record in records:
            if record.get("record_id"):
                corrections[record["record_id"]] = {"resolution": "WITHDRAWN" if withdrawn else "CORRECTED",
                                                    "at_ms": now_ms, "superseding_hash": superseding_hash}
        updated = dict(entry, source_resolutions=corrections)
        if all(r.get("record_id") in corrections for r in entry["records"]):
            status = "WITHDRAWN" if all(c["resolution"] == "WITHDRAWN" for c in corrections.values()) else "CORRECTED"
            updated.update(status=status, corrected_ms=now_ms, corrected_by=superseding_hash,
                           review=dict(entry["review"], next_due_ms=None))
            changed.append(sid)
        registry[sid] = updated
    return changed


def expire(registry: dict, *, now_ms: int, retention_ms: int, max_entries: int) -> list:
    """Expire entries not seen within `retention_ms`; keep at most `max_entries` (oldest last_seen dropped first,
    open reviews last). Returns expired/dropped IDs."""
    out = []
    for sid, entry in list(registry.items()):
        if entry["status"] not in ("EXPIRED",) and now_ms - entry["last_seen_ms"] > retention_ms:
            registry[sid] = dict(entry, status="EXPIRED", review=dict(entry["review"], next_due_ms=None))
            out.append(sid)
    if len(registry) > max_entries:
        ranked = sorted(registry.values(), key=lambda e: (e["status"] in OPEN_STATUSES, e["last_seen_ms"]))
        for entry in ranked[: len(registry) - max_entries]:
            del registry[entry["statement_id"]]
            out.append(entry["statement_id"])
    return out


def due_reviews(registry: dict, now_ms: int) -> list:
    return sorted((e for e in registry.values() if e["status"] == "PENDING_REVIEW"
                   and e["review"]["next_due_ms"] is not None and e["review"]["next_due_ms"] <= now_ms),
                  key=lambda e: (e["review"]["next_due_ms"], e["statement_id"]))
