"""Fourteen-day B consumer replay, real PostgreSQL and internal components.

Only market/RFQ, model and chain facts are synthetic. Midnight observations are
explicit test inputs, journaled as INCIDENT facts; this does not qualify D's
missing production midnight scheduler or the unmerged IDEA-048 driver.
"""

from copy import deepcopy
from datetime import timedelta
from fractions import Fraction
import json

from larp.contracts import Document
from larp.intelligence.redflags import CONFIG
from larp.integration.replay import replay_live
from larp.integration.runtime import ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection, ledger_from
from larp.integration.settlement import ExecutionBridge, settle
from larp.research.fixtures import with_quotes
from larp.risk.accounting import roll_day, update_risk
from larp.runtime.coordinator import Coordinator, batch_for
from larp.runtime.fixtures import assess as model_response
from larp.strategy.schema import equity, instant, value
from larp.strategy.profiles import build_live_profiles
from tests.strategy.live_fixtures import live_snapshot, summary
from tests.support import DatabaseCase, request


class SyntheticModel:
    def __init__(self, observations):
        self.observations = observations

    def assess(self, request):
        if self.observations["day"] >= 4:
            raise TimeoutError("Synthetic external model outage")
        return model_response(request)


class FourteenDayRun(DatabaseCase):
    def test_b_req_045_fourteen_days_caps_loss_closed_markets_terminal_revert_and_replay(self):
        start = instant("2026-10-29T00:00:00Z")
        seed = live_snapshot(now=start, held={s: 4000 for s in ("NVDAB", "GOOGLB", "MSFTB", "TSLAB")})
        p = build_live_profiles(summary(), Document.from_dict(json.loads(CONFIG.read_text())))['FINAL'].read()
        # Candidate amounts remain synthetic and confer no LIVE release authority.
        p.update(mode="OFFLINE_FIXTURE", values_origin="SYNTHETIC")
        profile_hash = Document.from_dict(p).digest("StrategyProfile.v1")
        ledger = seed.context.read()["portfolio"]
        ledger.update(run_id="run", wallet_id="wallet", mode="OFFLINE")
        initial = Document.from_dict(initial_projection(ledger))
        with self.store.transaction() as db:
            db.execute("TRUNCATE runs CASCADE")
        self.store.initialize("run", "wallet", 56, initial)
        self.store.takeover("run", 1, offline=True)
        observed = {}
        builder = ContextBuilder(profile=p, profile_hash=profile_hash, run_id="run", issuers={},
            market=lambda _: deepcopy(observed["markets"]),
            health=lambda _: {"integrity_ok": True, "journal_ok": True, "ownership_ok": True,
                              "clock_ok": True, "new_spending_ok": observed["day"] < 4},
            calendar=lambda _: {"index": observed["session"], "remaining": 14 - observed["day"]})
        runtime = Coordinator(self.store, SyntheticModel(observed), StrategyPolicy(),
            RuntimePlanner(job_validity_ms=60000, job_max_attempts=3), execution=ExecutionBridge(),
            run_id="run", version_id="b-synthetic-14-day", profile_hash=profile_hash,
            address="0x" + "1" * 40, context_builder=builder,
            initial_policy_state=initial_policy_state("run", p), clock_ms=lambda: observed["now_ms"])
        previous_marks = seed.context.read()["markets"]
        session = 80
        reverted = False
        terminal_gas = 0
        plans = []
        for day in range(14):
            boundary = start + timedelta(days=day)
            at = boundary + (timedelta(hours=14, minutes=40) if day == 13 else timedelta(hours=15))
            if at.weekday() < 5:
                session += 1
            observed.update(day=day, session=session, now_ms=int(at.timestamp() * 1000))
            current = self.store.load("run")
            projection = current.read()["projection"]
            ledger = ledger_from(projection, current.read()["reservations"])
            if day:
                # Trusted boundary mark precedes the next intraday price shock.
                anchor = equity(ledger, {m["symbol"]: m for m in previous_marks})
                rolled = roll_day(Document.from_dict(ledger), boundary=boundary.isoformat(), anchor_units=anchor).read()
                projection.update(portfolio=rolled, risk_state=rolled["risk"])
                self.store.commit(batch_for(current, f"midnight:{day}",
                    {"kind": "INCIDENT", "synthetic_boundary": boundary.isoformat(), "anchor_units": anchor},
                    projection=projection))
                assert not rolled["risk"]["daily_halt"]
                if day > 4:
                    assert rolled["risk"]["run_halt"] and rolled["risk"]["deep_cut"]
            observed["markets"] = live_snapshot(now=at).context.read()["markets"]
            for m in observed["markets"]:
                m["price_units"] = 75_000_000 if day >= 4 else 100_000_000
                if m["symbol"] == "NVDAB" and 1 <= day <= 3:
                    m["price_units"] = 150_000_000 if day == 1 else 220_000_000
                m["token_open"] = m["underlying_open"] = at.weekday() < 5
                m["quotes"] = []
            # Multiple mandatory children require a fresh settled-state plan.
            for child in range(10):
                current = self.store.load("run")
                context, _ = builder(current.read(), {}, None, observed["now_ms"])
                snap = runtime.snapshot(current, observed["now_ms"], context)
                observed["markets"] = with_quotes(snap, policy=False).context.read()["markets"]
                round_id = f"day:{day}:child:{child}"
                req = request(job=round_id, cutoff=observed["now_ms"]).read()
                req["policy_profile_hash"] = profile_hash
                runtime.start(round_id, Document.from_dict(req), observed["now_ms"], defer_close=True)
                record = self.store.load("run").read()["projection"]["round_records"][round_id]
                result = record["plan"]
                plans.append(result)
                assert result["risk_state"] is not None, record["errors"]
                if day < 4:
                    assert record["policy_output"] is not None, record["errors"]
                assert all(i["side"] == "SELL" and i["symbol"] in snap.universe for i in result["intents"])
                if day == 4:
                    assert result["risk_state"]["daily_halt"] and result["risk_state"]["run_halt"] and result["risk_state"]["deep_cut"]
                if not result["intents"]:
                    runtime.close(round_id, observed["now_ms"], "COMPLETE")
                    break
                intent = result["intents"][0]
                assert intent["mandatory"] and intent["token_units"] <= ledger_from(
                    self.store.load("run").read()["projection"], [])['positions'][intent['symbol']]['units']
                tx = "0x" + Document.from_dict({"round": round_id}).digest("synthetic-chain")
                base = dict(schema="ExecutionObservation.v1", run_id="run", wallet_id="wallet", round_id=round_id,
                    intent_id=intent["intent_id"], observed_at=at.isoformat(), tx_hash=tx)
                broadcast = dict(base, event_id=round_id + ":broadcast", kind="BROADCAST_ATTEMPTED", step="swap")
                runtime.observe(broadcast["event_id"], Document.from_dict(broadcast), settle)
                kind = "REVERT" if day == 12 and not reverted else "FILL"
                reverted |= kind == "REVERT"
                facts = dict(base, event_id=round_id + ":final", kind=kind, settlement="FINAL", origin="SCRIPTED_FAKE",
                    block_hash="0x" + "b" * 64, canonical=True, intent_terminal=True, round_terminal=True,
                    gas_bnb_units=10000, gas_value_units=10000)
                if kind == "FILL":
                    facts.update(symbol=intent["symbol"], side="SELL", token_units=intent["pay_units"],
                                 cash_units=intent["min_receive_units"], fee_units=0)
                receipt = runtime.observe(facts["event_id"], Document.from_dict(facts), settle)
                assert runtime.observe(facts["event_id"], Document.from_dict(facts), settle) == receipt
                assert not self.store.load("run").read()["reservations"]
                runtime.close(round_id, observed["now_ms"], "COMPLETE")
                if day >= 12:
                    terminal_gas += 10000
                if kind == "REVERT":
                    # Failure did not create proceeds or falsely complete flattening.
                    assert self.store.load("run").read()["projection"]["balances"][intent["symbol"]] > 0
                    break
                observed["markets"] = [dict(m, quotes=[]) for m in observed["markets"]]
            settled = self.store.load("run").read()
            ledger = ledger_from(settled["projection"], settled["reservations"])
            marks = {m["symbol"]: m for m in observed["markets"]}
            safe_equity = equity(ledger, marks) - p["cost_reserve_units"]
            if day == 1:
                assert value(ledger["positions"]["NVDAB"]["units"], marks["NVDAB"]) <= Fraction(safe_equity, 5)
            if day == 4:
                gross = sum(value(pos["units"], marks[symbol]) for symbol, pos in ledger["positions"].items())
                assert gross <= Fraction(safe_equity * 2, 5)
            previous_marks = deepcopy(observed["markets"])
        final = self.store.load("run").read()
        assert reverted and terminal_gas >= 20000
        assert all(p["units"] == 0 for p in final["projection"]["portfolio"]["positions"].values())
        assert not final["reservations"]
        assert final["projection"]["portfolio"]["accounting"]["gas_value_units"] >= terminal_gas
        assert any(r["requirements"] and not r["intents"] for r in plans)
        journal, head = self.store.journal("run"), self.store.verify("run")
        with self.store.transaction() as db:
            db.execute("TRUNCATE runs CASCADE")
        replay_live(journal, initial, self.store, run_id="run", wallet_id="wallet", chain_id=56,
                    version_id="b-synthetic-14-day", profile_hash=profile_hash, address="0x" + "1" * 40,
                    builder=builder, policy=StrategyPolicy(),
                    planner=RuntimePlanner(job_validity_ms=60000, job_max_attempts=3),
                    execution=ExecutionBridge(), reducer=settle,
                    initial_policy_state=initial_policy_state("run", p))
        assert self.store.verify("run") == head
        assert self.store.load("run").read() == final


def test_b_req_017_019_020_exact_loss_boundaries_and_utc_reset():
    portfolio = Document.from_dict(live_snapshot().context.read()["portfolio"])
    anchor = portfolio.read()["risk"]["day_anchor_units"]
    now = instant("2026-10-29T23:59:59Z")
    for percent, field in ((97, "daily_halt"), (92, "run_halt"), (88, "deep_cut")):
        assert not update_risk(portfolio, now=now, equity_units=anchor * percent // 100 + 1).read()["risk"][field]
        hit = update_risk(portfolio, now=now, equity_units=anchor * percent // 100)
        assert hit.read()["risk"][field]
        assert update_risk(hit, now=now, equity_units=anchor).read()["risk"][field]
    reset = roll_day(hit, boundary="2026-10-30T00:00:00Z", anchor_units=anchor).read()["risk"]
    assert not reset["daily_halt"] and reset["run_halt"] and reset["deep_cut"]
