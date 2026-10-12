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
    directives = [{"predicate_id": f["predicate_id"], "accession": f["finding_id"],
                   "finding_ids": [f["finding_id"]], "class": records[f["predicate_id"]]["class"],
                   "kind": "EXIT" if records[f["predicate_id"]]["class"] == 1 else
                           "BLOCK_NEW_BUYS" if records[f["predicate_id"]]["class"] == 2 else "SHADOW",
                   "block_sessions": records[f["predicate_id"]]["block_sessions"],
                   "restarts_block": True} for f in findings]
    update_directive_blocks(blocks, history, symbol, directives, session=session, run_id=run_id,
                            allow_resolution=allow_resolution)


def update_directive_blocks(blocks, history, symbol, directives, *, session, run_id, allow_resolution=False):
    """Published I8 directives; overlapping timed blocks survive a critical latch and its clearance."""
    current = blocks.get(symbol, {})
    timed = current.get("timed_block") if current.get("reason") == "CLASS_1_EXIT" else current
    if timed and timed.get("reason") == "CLASS_2_ENTRY_BLOCK":
        if session < timed["started_session"]:
            raise ContractError("Session clock moved backward")
        if session >= timed["expires_session"]:
            timed = None
    else:
        timed = None
    for directive in directives:
        if directive["kind"] != "BLOCK_NEW_BUYS":
            continue
        key = symbol + ":" + directive["predicate_id"] + ":" + directive["accession"]
        if not directive.get("restarts_block", True):
            # An amendment does not begin a second five-session clock for an existing predicate.
            starts = [v for k, v in history.items() if k.startswith(symbol + ":" + directive["predicate_id"] + ":")]
            first = min(starts) if starts else session
            history.setdefault(key, first)
        else:
            first = history.setdefault(key, session)
        if session < first:
            raise ContractError("Session clock moved backward")
        if session < first + directive["block_sessions"]:
            timed = {"reason": "CLASS_2_ENTRY_BLOCK", "run_id": run_id,
                     "started_session": min(first, (timed or {}).get("started_session", first)),
                     "expires_session": max((timed or {}).get("expires_session", 0),
                                            first + directive["block_sessions"])}
    critical = [d for d in directives if d["kind"] == "EXIT"]
    if critical or current.get("reason") == "CLASS_1_EXIT" and not allow_resolution:
        blocks[symbol] = {"reason": "CLASS_1_EXIT", "run_id": run_id,
                          "finding_ids": sorted({i for d in critical for i in d["finding_ids"]})
                          if critical else current.get("finding_ids", []), "timed_block": timed}
    elif timed:
        blocks[symbol] = timed
    else:
        blocks.pop(symbol, None)
