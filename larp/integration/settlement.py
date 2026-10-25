"""Execution observations -> journaled projection (interface I4; IDEA-042 item 1, ported from PR #10).

Two boundaries (docs/build/DEPLOYMENT_BUILD.md I4):

- BROADCAST_ATTEMPTED changes execution state and the round record only: the swap's tx hash on its order and one
  `swap_mappings` row, so the round's audit event carries it. Balances, the portfolio and store reservations are
  untouched.
- Final facts (APPROVAL, FILL, REVERT with `settlement: FINAL`) change balances and gas through Keith's
  `advance_accounting`; `projection.balances` is rewritten from the resulting ledger so `ledger_from` accepts the
  next round. A terminal fact releases every remaining store reservation of its intent (USDT, BNB and
  `INCOMING:<token>`, A9); an approval releases the BNB it spent. NOT_SUBMITTED ends an intent that never reached
  the chain: reservations are released and nothing is accounted.

Store reservations are the authority for what is still reserved; the projection keeps `portfolio.reservations`
empty and `ledger_from` rebuilds them each round. Repeating an observation is a no-op twice over: the coordinator
refuses a reused event ID with changed bytes and returns the old receipt otherwise, and the accounting reducer keeps
`applied_events`.
"""

from copy import deepcopy

from larp.contracts import ContractError, Document
from larp.integration.runtime import INCOMING, iso_ms
from larp.ports import validate_execution_observation
from larp.risk.accounting import advance_accounting
from larp.execution import REVOKE_TOKENS

SCHEMA = "ExecutionState.v1"


def _observation(observation):
    return validate_execution_observation(observation.read())


class ExecutionBridge:
    """ports.Execution: per-intent execution state and the execution owner's terminal-round attestation.

    The attestation is the observation's `round_terminal` flag, set by the execution service that owns every command
    of the round. The coordinator checks it against the round record before sealing the round.
    """

    def advance(self, state, observation):
        s, o = state.read(), _observation(observation)
        if s.get("schema") != SCHEMA:
            raise ContractError("Unexpected execution state")
        intents = dict(s.get("intents", {}))
        entry = dict(intents.get(o["intent_id"], {"round_id": o["round_id"], "status": "PLANNED", "tx_hashes": []}))
        if entry["round_id"] != o["round_id"]:
            raise ContractError("Observation names another round for this intent")
        kind = o["kind"]
        cleanup = o.get('maintenance') == 'ALLOWANCE_REVOKE'
        if kind == "BROADCAST_ATTEMPTED":
            entry["status"] = ('ALLOWANCE_REVOKE_SUBMITTED' if cleanup else
                               'APPROVE_SUBMITTED' if o['step'] == 'approve' else 'SWAP_SUBMITTED')
            entry["tx_hashes"] = sorted(set(entry["tx_hashes"]) | {o["tx_hash"].lower()})
        elif kind == "APPROVAL":
            entry["status"] = 'ALLOWANCE_REVOKE_CONFIRMED' if cleanup else 'APPROVED'
        else:
            entry["status"] = kind if o["intent_terminal"] else entry["status"]
        if kind != "BROADCAST_ATTEMPTED" and o["intent_terminal"]:
            intents.pop(o["intent_id"], None)  # terminal intents leave the live state
        else:
            intents[o["intent_id"]] = entry
        terminal = [o["round_id"]] if kind != "BROADCAST_ATTEMPTED" and o["round_terminal"] else []
        return Document.from_dict({"schema": "ExecutionTransition.v1",
                                   "next_state": {"schema": SCHEMA, "intents": intents},
                                   "commands": [], "observation_ids": [o["event_id"]], "terminal_rounds": terminal})


def _accounting_reservation(intent: dict, held: dict, round_id: str) -> dict:
    """Keith's per-intent reservation view, from the planned intent and the store rows still held for it."""
    side, symbol = intent["side"], intent["symbol"]
    return {"symbol": symbol, "side": side, "pay_units": intent["pay_units"],
            "round_id": round_id, "kind": intent.get("kind", "BSTOCK_TRADE"),
            "min_receive_units": intent["min_receive_units"],
            "cash_units": held.get("USDT", 0) if side == "BUY" else 0,
            "bnb_units": held.get("BNB", 0),
            "token_units": held.get(INCOMING + symbol, 0) if side == "BUY" else held.get(symbol, 0)}


def balances_of(ledger: dict) -> dict:
    """The settled balances the store checks reservations against, exactly as `ledger_from` expects them."""
    return {"USDT": ledger["cash_units"], "BNB": ledger["bnb_units"],
            **{s: p["units"] for s, p in ledger["positions"].items()}}


def refund_attempt(projection, intent):
    """IDEA-097 S4-F1: give back the S1 attempt of an expired command the execution service never claimed.

    Only the latest attempt of that leg in the budget's own session, so an older or out-of-order fact never reopens a
    slot; a round without S1 bounds or budget is unchanged. The cap still bounds every attempt that reached the wallet."""
    bounds, budget = intent.get("execution_bounds"), projection.get("execution_attempt_budget")
    if type(bounds) is not dict or type(budget) is not dict:
        return
    leg, ordinal = bounds.get("leg"), bounds.get("ordinal")
    counts, closed = dict(budget.get("counts", {})), dict(budget.get("closed", {}))
    if budget.get("session") != bounds.get("session_index") or type(ordinal) is not int or counts.get(leg) != ordinal:
        return
    if ordinal > 1:
        counts[leg] = ordinal - 1
        if leg in closed:
            closed[leg] = min(closed[leg], ordinal - 1)
    else:
        counts.pop(leg)
        closed.pop(leg, None)
    projection["execution_attempt_budget"] = dict(budget, counts=counts, closed=closed)


def settle(current, observation):
    """Coordinator reducer for ExecutionObservation.v1. Returns {projection, reservation_deltas}."""
    c, o = current.read(), _observation(observation)
    if (o["run_id"], o["wallet_id"]) != (c["run_id"], c["wallet_id"]):
        raise ContractError("Observation belongs to another run or wallet")
    projection = deepcopy(c["projection"])
    record = projection.get("round_records", {}).get(o["round_id"])
    if record is None:
        raise ContractError("Execution observation has no open round record")
    intents = record["plan"].get("intents", [])
    index = next((n for n, i in enumerate(intents) if i["intent_id"] == o["intent_id"]), None)
    if index is None:
        raise ContractError("Observation names an intent its round did not plan")
    intent = intents[index]
    final = record.setdefault("final_intents", [])
    if o["intent_id"] in final:
        raise ContractError("Intent already reached a terminal fact")
    held = {r["asset"]: r["units"] for r in c["reservations"] if r["intent_id"] == o["intent_id"]}
    kind = o["kind"]
    if kind == "BROADCAST_ATTEMPTED":
        broadcasts = record.setdefault("execution_broadcasts", {})
        identity = o["intent_id"] + ":" + o["step"]
        previous = broadcasts.get(identity)
        if previous is not None and previous != o["tx_hash"].lower():
            raise ContractError("Execution step already broadcast under another hash")
        broadcasts[identity] = o["tx_hash"].lower()
        if o["step"] == "swap":
            tx = o["tx_hash"].lower()
            order = record["orders"][index]
            if order.get("tx_hash") not in (None, tx):
                raise ContractError("Swap already broadcast under another hash; replacement is disabled")
            order["tx_hash"] = tx
            if not any(m["tx_hash"] == tx for m in record["swap_mappings"]):
                record["swap_mappings"].append({"tx_hash": tx, "decision_id": intent["decision_id"], "step": "swap"})
            if not intent["mandatory"] and intent.get("kind", "BSTOCK_TRADE") == "BSTOCK_TRADE":
                # Consume the allowance only once economic submission is possible,
                # not on quotes, approval, or a definitely unsubmitted intent.
                # This captured session also makes recovery/replay deterministic.
                session = record.get("policy_input", {}).get("context", {}).get("session_index")
                if type(session) is not int or session < 0:
                    raise ContractError("Discretionary swap has no recorded session")
                previous_session = projection.get("last_discretionary_session")
                projection["last_discretionary_session"] = max(session, previous_session) \
                    if type(previous_session) is int else session
                profile = record.get("policy_input", {}).get("context", {}).get("profile", {})
                if profile.get("baseline") == "TREND_GUARDED_VOL":
                    # IDEA-076 Q14: S1 budgets discretionary swaps per name per session.
                    legs = projection.get("discretionary_legs")
                    if type(legs) is not dict or type(legs.get("session")) is not int or legs["session"] < session:
                        legs = {"session": session, "counts": {}}
                    if legs["session"] == session:
                        counts = dict(legs["counts"])
                        counts[intent["symbol"]] = counts.get(intent["symbol"], 0) + 1
                        projection["discretionary_legs"] = {"session": session, "counts": counts}
                observed_ms = iso_ms(o["observed_at"])
                projection["last_discretionary_observed_ms"] = max(
                    observed_ms, projection.get("last_discretionary_observed_ms", observed_ms))
        return Document.from_dict({"projection": projection, "reservation_deltas": []})
    supporting_approval = o.get('step') in {'approve', *(s.lower() for s in REVOKE_TOKENS)}
    if supporting_approval and kind in ("APPROVAL", "REVERT"):
        expected = record.get("execution_broadcasts", {}).get(o["intent_id"] + ':' + o['step'])
        if expected != o["tx_hash"].lower():
            raise ContractError("Final approval fact names an unrecorded broadcast")
    if kind in ("FILL", "REVERT", "ABNORMAL") and not supporting_approval and o["tx_hash"].lower() != (record["orders"][index].get("tx_hash") or "").lower():
        raise ContractError("Final swap fact names a hash this round never broadcast")
    if kind != "NOT_SUBMITTED":
        portfolio = deepcopy(projection["portfolio"])
        portfolio["mode"] = c["mode"].upper()
        portfolio["reservations"] = {o["intent_id"]: _accounting_reservation(intent, held, o["round_id"])}
        accounted = dict(o)  # retain receipt provenance and committed round binding for accounting
        after = advance_accounting(Document.from_dict(portfolio), Document.from_dict(accounted)).read()
        after["reservations"] = {}
        projection["portfolio"] = after
        projection["balances"] = balances_of(after)
        block = (o.get("receipt") or {}).get("block_number")
        if type(block) is int:  # balance checks compare only at or after the newest applied receipt (IDEA-055)
            projection["settled_block"] = max(block, projection.get("settled_block") or 0)
    elif record["orders"][index].get("tx_hash") is not None:
        raise ContractError("A broadcast swap cannot end as NOT_SUBMITTED")
    else:
        # Logged without a tx hash, with the reason in the round's output (kit convention; IDEA-042 L2).
        order = record["orders"][index]
        if o.get("attempt_refund") is True:
            if any(key.startswith(o["intent_id"] + ":") for key in record.get("execution_broadcasts", {})):
                raise ContractError("A broadcast intent cannot refund an unclaimed attempt")
            refund_attempt(projection, intent)
        record.setdefault("aborted", []).append({"intent_id": o["intent_id"], "symbol": order["symbol"],
                                                 "side": order["side"], "amount": order["amount"],
                                                 "reason": o.get("reason", "NOT_SUBMITTED")})
    if kind == "ABNORMAL":
        # Immutable observation bytes are also journaled by Coordinator.observe. Keep
        # a durable incident/latch in the projection so replay and every signing gate agree.
        projection.setdefault("abnormal_outcomes", {})[o["event_id"]] = deepcopy(o)
        record.setdefault("abnormal_outcomes", []).append(o["event_id"])
    if o["intent_terminal"]:
        final.append(o["intent_id"])
        deltas = [{"intent_id": o["intent_id"], "asset": asset, "units": -units}
                  for asset, units in sorted(held.items()) if units]
    else:
        spent = min(held.get("BNB", 0), o.get("gas_bnb_units", 0))
        deltas = [{"intent_id": o["intent_id"], "asset": "BNB", "units": -spent}] if spent else []
    return Document.from_dict({"projection": projection, "reservation_deltas": deltas})
