"""Replay interface-level fake observations through production reducers/ports.

This is not Isaac's execution simulator, a durable store, or live audit replay.
"""

from dataclasses import replace
from datetime import timedelta
import random

from larp.contracts import ContractError, Document
from larp.risk.accounting import advance_accounting, roll_day
from larp.risk.planner import plan
from larp.strategy.policy import decide


class FakeClock:
    def __init__(self, now):
        self.now = now

    def advance(self, seconds):
        if seconds < 0:
            raise ContractError("Fake clock cannot move backward")
        self.now += timedelta(seconds=seconds)
        return self.now


def replay_snapshots(snapshots, *, decide_port=decide, plan_port=plan):
    """Recorded snapshots/results, no hidden time or network; no invented fills."""
    trace = []
    for snapshot in snapshots:
        try:
            proposal = decide_port(snapshot, snapshot.policy_state)
            policy_hash = proposal.proposal_id
        except (ContractError, KeyError, TypeError, ValueError) as exc:
            proposal, policy_hash = None, None
            policy_error = str(exc)
        else:
            policy_error = None
        result = plan_port(snapshot, proposal)
        trace.append({"snapshot_id": snapshot.snapshot_id, "proposal_id": policy_hash,
                      "policy_error": policy_error, "plan_hash": result.digest("PlanResult.v1"),
                      "plan": result.read()})
    return Document.from_dict({"schema": "OfflineReplay.v1", "origin": "SCRIPTED_FAKE",
                               "trace": trace, "live_execution_parity": False})


def replay_accounting(initial, observations):
    state = initial
    hashes = []
    for observation in observations:
        if observation.read().get("schema") == "DayBoundary.v1":
            e = observation.read()
            state = roll_day(state, boundary=e["boundary"], anchor_units=e["anchor_units"])
        else:
            state = advance_accounting(state, observation)
        hashes.append(state.digest("PortfolioState.v1"))
    return Document.from_dict({"schema": "AccountingReplay.v1", "hashes": hashes,
                               "portfolio": state.read(), "origin": "SCRIPTED_FAKE"})


def seeded_observations(seed, times, symbols):
    """Scenario/time/entity streams don't change with a policy's call count."""
    result = []
    for t in times:
        for symbol in symbols:
            identity = Document.from_dict({"seed": seed, "time": t, "symbol": symbol})
            rng = random.Random(identity.digest("FixtureStream.v1"))
            result.append({"time": t, "symbol": symbol,
                           "price_move_bps": rng.randrange(-200, 201),
                           "fault": rng.choice(["NONE", "QUOTE_MISSING", "MARKET_CLOSED", "PENDING"]),
                           "origin": "SCRIPTED_FAKE"})
    return Document.from_dict({"schema": "SeededFixture.v1", "observations": result})
