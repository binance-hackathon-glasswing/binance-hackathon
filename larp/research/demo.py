"""python -m larp.research.demo -- synthetic verification traces, no profit experiment."""

from larp.contracts import Document
from larp.strategy.policy import decide
from larp.risk.planner import plan
from .fixtures import snapshot, with_quotes, changed
from .replay import replay_snapshots


def snapshot_record(s):
    """Versioned inputs, including immutable state, sufficient to reconstruct s."""
    return {"schema": "larp.snapshot.v1", "run_id": s.run_id, "wallet_id": s.wallet_id,
            "engine_version": s.engine_version, "policy_profile_hash": s.policy_profile_hash,
            "event_sequence": s.event_sequence, "observed_at": s.observed_at.isoformat(),
            "universe": list(s.universe), "policy_state": s.policy_state.record(),
            "context": s.context.read(), "snapshot_id": s.snapshot_id}


def traces():
    baseline = with_quotes(snapshot())
    costly = with_quotes(snapshot(profile_changes={"cost_reserve_units": 1000000}), spread_bps=80)
    blocked = snapshot(held={"NVDAB": 8000})
    c = blocked.context.read()
    c["markets"][0]["underlying_open"] = False
    blocked = changed(blocked, markets=c["markets"])
    return Document.from_dict({"schema": "StrategyExamples.v1", "origin": "SYNTHETIC_VERIFICATION",
        "baseline": {"snapshot": snapshot_record(baseline),
                     "targets": [t.record() for t in decide(baseline, baseline.policy_state).targets],
                     "plan": plan(baseline, decide(baseline, baseline.policy_state)).read()},
        "costly_opportunity": plan(costly, decide(costly, costly.policy_state)).read(),
        "blocked_mandatory_exit": plan(blocked, None).read(),
        "scenario_inputs": {"costly_opportunity": snapshot_record(costly),
                            "blocked_mandatory_exit": snapshot_record(blocked)},
        "replay_hash": replay_snapshots([baseline, costly, blocked]).digest("OfflineReplay.v1")})


if __name__ == "__main__":
    print(traces().payload.decode("utf-8"))
