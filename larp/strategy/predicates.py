"""I8 consumer contract. Predicate records belong to the evidence producer.

No local production registry: validate Yao's versioned records against the team
decision; finding identity comes from verified EvidenceContext.v1, not model text.
"""

from larp.contracts import ContractError, Document

DECIDED = {"4.02": (1, "DISCRETIONARY_EXIT", 0),
           "1.05": (2, "ENTRY_BLOCK", 5), "2.06": (2, "ENTRY_BLOCK", 5)}


def predicate_records(registry):
    if (type(registry) is not dict or registry.get("schema") != "RedFlagPredicates.v1"
            or not registry.get("version") or not registry.get("producer_commit")
            or not registry.get("records")):
        raise ContractError("Versioned producer red-flag registry required")
    commit = registry["producer_commit"]
    if type(commit) is not str or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ContractError("Predicate producer commit must be pinned")
    body = {k: v for k, v in registry.items() if k != "content_hash"}
    if registry.get("content_hash") != Document.from_dict(body).digest("RedFlagPredicates.v1"):
        raise ContractError("Predicate registry hash mismatch")
    result, items = {}, set()
    for record in registry["records"]:
        pid = record.get("predicate_id")
        item = record.get("item")
        expected = DECIDED.get(item, (3, "SHADOW", 0))
        if (not pid or pid in result or item in items
                or (record.get("class"), record.get("action"), record.get("block_sessions")) != expected
                or (item not in DECIDED and record.get("kind") != "STATEMENT")
                or not record.get("verification_fixture_hashes")):
            raise ContractError("Predicate conflicts with IDEA-035 B1 or lacks verification fixtures")
        for h in record["verification_fixture_hashes"]:
            if type(h) is not str or len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
                raise ContractError("Invalid predicate verification hash")
        result[pid] = record
        items.add(item)
    if not set(DECIDED).issubset(items):
        raise ContractError("Incomplete decided red-flag classes")
    return result


def update_blocks(blocks, history, symbol, findings, *, session, run_id, registry, allow_resolution=False):
    """Expiry uses stable first-observed session per finding; repeated reads cannot renew it."""
    records = predicate_records(registry)
    current = blocks.get(symbol)
    if current and current.get("reason") == "CLASS_2_ENTRY_BLOCK":
        if session < current["started_session"]:
            raise ContractError("Session clock moved backward")
        if session >= current["expires_session"]:
            blocks.pop(symbol)
    critical = [f for f in findings if records[f["predicate_id"]]["class"] == 1]
    if critical:
        blocks[symbol] = {"reason": "CLASS_1_EXIT", "run_id": run_id,
                          "finding_ids": sorted(f["finding_id"] for f in critical)}
        return
    if blocks.get(symbol, {}).get("reason") == "CLASS_1_EXIT":
        # Caller only supplies a validated, current context. No context never clears a latch.
        if not allow_resolution:
            return
        blocks.pop(symbol)
    for finding in findings:
        record = records[finding["predicate_id"]]
        if record["class"] != 2:
            continue
        key = symbol + ":" + finding["finding_id"]
        first = history.setdefault(key, session)
        if session < first:
            raise ContractError("Session clock moved backward")
        if session < first + record["block_sessions"]:
            old_expiry = blocks.get(symbol, {}).get("expires_session", 0)
            blocks[symbol] = {"reason": "CLASS_2_ENTRY_BLOCK", "run_id": run_id,
                "started_session": first, "expires_session": max(old_expiry, first + record["block_sessions"])}
