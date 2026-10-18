"""IDEA-076 Q01-Q15, L09: the S1 policy and planner (IDEA-075 plan §4-§6, PR #123). Synthetic fixtures only.

Fixture: five names at 100 USDT per token (1 unit = 0.01 USDT), 200 USDT equity, equal frozen weights 1/5, so the
95% target per name is 19% (about 3798 units after the cost reserve) and the 60% target is 12%.
"""
from datetime import timedelta
from fractions import Fraction
import unittest

from larp.contracts import Document, TargetKind
from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from tests.strategy.test_equal_weight import by_symbol, five_names, with_state
from tests.strategy.test_s1_core import block

NAMES = ("GOOGLB", "MSFTB", "NVDAB", "SKHYB", "TSLAB")
S1 = {"baseline": "TREND_GUARDED_VOL", "s1": block()}
AT_95 = 3798  # floor(0.19 x 199.9 USDT / 0.01)
AT_60 = 2398


def token_series(s, path):
    """Session closes for every name ending the day before the decision; path[-1] is the latest close."""
    now = s.observed_at
    series = {}
    for symbol in NAMES:
        bars = [dict(session_index=70 + k, close_units=close, quality="VALID", corporate_action_version="v1",
                     close_at=(now - timedelta(days=len(path) - k)).isoformat(),
                     available_at=(now - timedelta(days=len(path) - k)).isoformat())
                for k, close in enumerate(path)]
        series[symbol] = dict(schema="PriceSeries.v1", instrument_kind="TOKEN", quality="VALID",
                              token_id="fixture-token-" + symbol, corporate_action_version="v1", bars=bars)
    return series


def snap(held=None, *, state=None, path=None, risk=None, profile_changes=None, **context):
    s = five_names(held=held, profile_changes={**S1, **(profile_changes or {})})
    c = s.context.read()
    opened = s.observed_at.replace(hour=13, minute=30, second=0, microsecond=0)
    context.setdefault('execution_session', dict(index=context.get('session_index', c['session_index']),
        open_ms=int(opened.timestamp()*1000), close_ms=int((opened + timedelta(hours=6, minutes=30)).timestamp()*1000),
        next_open_ms=int((opened + timedelta(days=1)).timestamp()*1000)))
    c["series"] = token_series(s, path) if path else {}
    c["portfolio"]["positions"]["SKHYB"]["units"] = (held or {}).get("SKHYB", 0)  # five_names adds it empty
    c["portfolio"]["positions"]["SKHYB"]["cost_basis_units"] = (held or {}).get("SKHYB", 0) * 10_000
    if risk:
        c["portfolio"]["risk"].update(risk)
    c.update(context)
    s = changed(s, series=c["series"], portfolio=c["portfolio"], **context)
    return with_state(s, state) if state is not None else s


def settled(level, trend="UP", evaluated=None, rebalance=False):
    return {"s1": {"trend_state": trend, "trend_evaluated_session": evaluated,
                   "limiter": {"level": "NORMAL", "expires_session": None, "used_evidence_ids": []},
                   "applied_target": level, "rebalance": rebalance}}


def first_intent(s):
    s = with_quotes(s)
    r = plan(s, decide(s, s.policy_state)).read()
    return r, r["intents"][0] if r["intents"] else None


FALLING = [100_000_000 - 3_000_000 * k for k in range(6)]
RISING = [100_000_000 + 3_000_000 * k for k in range(6)]
FLAT = [100_000_000] * 6


class Policy(unittest.TestCase):
    def test_q01_flat_book_builds_five_names_to_95_percent(self):
        s = snap()
        proposal = decide(s, s.policy_state)
        t = by_symbol(proposal)
        for symbol in NAMES:
            self.assertEqual((t[symbol].kind, t[symbol].reason, t[symbol].weight),
                             (TargetKind.TARGET_WEIGHT, "S1_LEVEL_CHANGE", Fraction(19, 100)))
        state = proposal.next_policy_state.data.read()
        self.assertEqual(state["s1_round"]["trend"]["status"], "TREND_INPUT_UNAVAILABLE")  # S04: starts UP
        self.assertEqual(state["s1"]["applied_target"], [19, 20])
        r, intent = first_intent(s)
        self.assertEqual((intent["side"], intent["mandatory"]), ("BUY", False))
        self.assertLessEqual(intent["cash_units"] + intent["fee_units"], s.context.read()["profile"]["per_trade_cap_units"])

    def test_q02_up_to_down_sells_every_name_toward_60_percent(self):
        s = snap({n: AT_95 for n in NAMES}, state=settled([19, 20]), path=FALLING)
        proposal = decide(s, s.policy_state)
        t = by_symbol(proposal)
        self.assertEqual(proposal.next_policy_state.data.read()["s1"]["trend_state"], "DOWN")
        for symbol in NAMES:
            self.assertEqual((t[symbol].reason, t[symbol].weight), ("S1_LEVEL_CHANGE", Fraction(3, 25)))
        r, intent = first_intent(s)
        self.assertEqual(intent["side"], "SELL")

    def test_q03_dead_band_holds_the_state(self):
        s = snap({n: AT_60 for n in NAMES}, state=settled([3, 5], trend="DOWN"), path=FLAT)
        proposal = decide(s, s.policy_state)
        self.assertEqual(proposal.next_policy_state.data.read()["s1"]["trend_state"], "DOWN")
        self.assertTrue(all(t.kind is TargetKind.KEEP_QUANTITY for t in proposal.targets))

    def test_q04_no_sale_on_drift(self):
        held = {n: 3500 for n in NAMES}
        held["NVDAB"] = 5000  # 25%: above its 19% target, below the 35% line; gross 95%
        s = snap(held, state=settled([19, 20]))
        self.assertTrue(all(t.kind is TargetKind.KEEP_QUANTITY for t in decide(s, s.policy_state).targets))
        r, intent = first_intent(s)
        self.assertIsNone(intent)
        self.assertFalse(r["requirements"])

    def test_q05_top_up_only_below_target_minus_band(self):
        held = {n: 3600 for n in NAMES}  # gross 90%: not below 95% - 5 pp
        s = snap(held, state=settled([19, 20]))
        self.assertTrue(all(t.kind is TargetKind.KEEP_QUANTITY for t in decide(s, s.policy_state).targets))
        held = dict(held, NVDAB=2000, TSLAB=3000)  # gross 82%
        s = snap(held, state=settled([19, 20]))
        t = by_symbol(decide(s, s.policy_state))
        self.assertEqual((t["NVDAB"].reason, t["TSLAB"].reason), ("S1_TOP_UP", "S1_TOP_UP"))
        self.assertEqual(t["GOOGLB"].kind, TargetKind.KEEP_QUANTITY)  # 18% is within one minimum trade of 19%
        r, intent = first_intent(s)
        self.assertEqual((intent["symbol"], intent["side"]), ("NVDAB", "BUY"))  # largest gap first

    def test_q09_after_new_risk_end_no_buys_but_level_cuts_still_sell(self):
        late = {"new_risk_end": "2026-10-10T13:00:00Z"}
        s = snap({n: AT_60 for n in NAMES}, state=settled([3, 5], trend="DOWN"), path=RISING, profile_changes=late)
        self.assertTrue(all(t.kind is TargetKind.KEEP_QUANTITY for t in decide(s, s.policy_state).targets))
        s = snap({n: AT_95 for n in NAMES}, state=settled([19, 20]), path=FALLING, profile_changes=late)
        self.assertTrue(all(t.reason == "S1_LEVEL_CHANGE" for t in decide(s, s.policy_state).targets))

    def test_q10_terminal_exits_everything(self):
        s = snap({n: AT_95 for n in NAMES}, state=settled([19, 20]),
                 profile_changes={"new_risk_end": "2026-10-10T12:00:00Z", "flatten_start": "2026-10-10T13:00:00Z"})
        self.assertTrue(all(t.kind is TargetKind.EXIT for t in decide(s, s.policy_state).targets))

    def test_q11_a_class_1_name_weight_stays_in_cash(self):
        s = snap(state={"blocked": {"NVDAB": {"reason": "CLASS_1_EXIT", "run_id": "synthetic-run"}}})
        t = by_symbol(decide(s, s.policy_state))
        self.assertNotEqual(t["NVDAB"].kind, TargetKind.TARGET_WEIGHT)
        self.assertEqual(sum(x.weight for x in t.values() if x.weight is not None), Fraction(19, 25))

    def test_limiter_caution_lowers_the_target(self):
        evidence = [dict(evidence_id=e, verified=True, session_index=80, symbols=[sym], **{"class": "CLASS_2_RED_FLAG"})
                    for e, sym in (("e1", "NVDAB"), ("e2", "MSFTB"))]
        s = snap({n: AT_95 for n in NAMES}, state=settled([19, 20]), exposure_evidence=evidence,
                 profile_changes={"s1": block(limiter_mode="DETERMINISTIC")})
        proposal = decide(s, s.policy_state)
        self.assertEqual(proposal.next_policy_state.data.read()["s1"]["limiter"]["level"], "CAUTION")
        self.assertTrue(all(t.weight == Fraction(3, 25) for t in proposal.targets))

    def test_rebalance_ends_when_every_name_is_at_target(self):
        s = snap({n: AT_95 for n in NAMES}, state=settled([19, 20], rebalance=True))
        proposal = decide(s, s.policy_state)
        self.assertTrue(all(t.kind is TargetKind.KEEP_QUANTITY for t in proposal.targets))
        self.assertFalse(proposal.next_policy_state.data.read()["s1"]["rebalance"])

    def test_a_name_whose_rebalance_completed_is_not_sold_on_drift(self):
        # IDEA-076 R1: a level change is underway; four names are at the 95% target, SKHYB is still unbought (for
        # example its buy keeps failing the planner's entry-cost gate, IDEA-075 §16 O3). The four complete now.
        held = {n: AT_95 for n in NAMES if n != "SKHYB"}
        s = snap(held, state=settled([19, 20], rebalance=True))
        proposal = decide(s, s.policy_state)
        t = by_symbol(proposal)
        self.assertEqual(t["SKHYB"].reason, "S1_LEVEL_CHANGE")
        self.assertTrue(all(t[n].kind is TargetKind.KEEP_QUANTITY for n in held))
        # Next round NVDAB has drifted to 25%, more than one minimum trade above its target; SKHYB is still unbought.
        # Only SKHYB is still rebalancing, so NVDAB is held (no sale on drift, IDEA-075 §5.2).
        s = snap(dict(held, NVDAB=5000), state=proposal.next_policy_state.data.read())
        t = by_symbol(decide(s, s.policy_state))
        self.assertEqual(t["NVDAB"].kind, TargetKind.KEEP_QUANTITY)
        self.assertEqual(t["SKHYB"].reason, "S1_LEVEL_CHANGE")


    def test_l09_an_assessor_outage_never_rebuys_above_the_cut(self):
        # IDEA-076 R2 (review TRV-01): an accepted CAUTION, then three times the expiry of sessions with no usable
        # model output. The cut stands, so the policy plans no level change back to 95% and the planner no buy.
        model = {"s1": block(limiter_mode="MODEL")}
        evidence = [dict(evidence_id=e, verified=True, session_index=80, symbols=[sym], **{"class": "CLASS_2_RED_FLAG"})
                    for e, sym in (("e1", "NVDAB"), ("e2", "MSFTB"))]
        held = {n: AT_60 for n in NAMES}
        s = snap(held, state=settled([19, 20]), profile_changes=model, exposure_evidence=evidence,
                 exposure_assessment=dict(level="CAUTION", evidence_ids=["e1", "e2"], reason="r", falsifier="f"))
        state = decide(s, s.policy_state).next_policy_state.data.read()
        self.assertEqual(state["s1"]["limiter"]["level"], "CAUTION")
        bad = (None, {"level": "NORMAL"}, dict(level="CAUTION", evidence_ids=["e9"], reason="r", falsifier="f"))
        for k, session in enumerate(range(81, 90)):
            s = snap(held, state=state, profile_changes=model, session_index=session, exposure_evidence=evidence,
                     exposure_assessment=bad[k % 3])
            proposal = decide(s, s.policy_state)
            state = proposal.next_policy_state.data.read()
            self.assertEqual(state["s1"]["limiter"]["level"], "CAUTION")
            self.assertEqual(state["s1"]["applied_target"], [3, 5])
            for target in proposal.targets:
                self.assertTrue(target.kind is not TargetKind.TARGET_WEIGHT or target.weight <= Fraction(3, 25))
            r, _ = first_intent(s)
            self.assertFalse([i for i in r["intents"] if i["side"] == "BUY"])
            self.assertFalse([q for q in r["quote_requests"] if q["side"] == "BUY"])

class Planner(unittest.TestCase):
    def requirements(self, s):
        return {r["symbol"]: r for r in plan(s, decide(s, s.policy_state)).read()["requirements"]}

    def test_q06_hard_name_line_trims_to_target_and_latches(self):
        held = {n: 3000 for n in NAMES}  # others 15%; NVDAB varies
        below = self.requirements(snap(dict(held, NVDAB=6900), state=settled([19, 20])))  # about 34.5%
        self.assertFalse(below)
        s = snap(dict(held, NVDAB=7200), state=settled([19, 20]))  # 36%
        r = plan(s, decide(s, s.policy_state)).read()
        req = {x["symbol"]: x for x in r["requirements"]}["NVDAB"]
        self.assertIn("POSITION_CAP", req["reasons"])
        self.assertEqual(req["max_units"], AT_95)
        latched = snap(dict(held, NVDAB=6000), state=settled([19, 20]), risk={"cap_trims": r["risk_state"]["cap_trims"]})
        self.assertIn("POSITION_CAP", self.requirements(latched)["NVDAB"]["reasons"])  # 30%: still trimming

    def test_q07_deep_cut_sells_to_forty_percent_at_any_level(self):
        s = snap({n: AT_95 for n in NAMES}, state=settled([19, 20]), risk={"deep_cut": True})
        reqs = self.requirements(s)
        self.assertEqual(len(reqs), 5)
        self.assertTrue(all("DEEP_DRAWDOWN" in r["reasons"] for r in reqs.values()))
        safe = 200_000_000 - s.context.read()["profile"]["cost_reserve_units"]
        self.assertLessEqual(sum(r["max_units"] for r in reqs.values()) * 10_000, safe * 2 // 5)

    def test_no_gross_trim_at_97_percent(self):
        s = snap({n: 3880 for n in NAMES}, state=settled([19, 20]))  # 97% from price drift
        self.assertFalse(self.requirements(s))

    def test_q08_stop_blocks_a_down_to_up_rebuy(self):
        s = snap({n: AT_60 for n in NAMES}, state=settled([3, 5], trend="DOWN"), path=RISING, risk={"run_halt": True})
        self.assertTrue(all(t.reason == "S1_LEVEL_CHANGE" for t in decide(s, s.policy_state).targets))
        r, intent = first_intent(s)
        self.assertIsNone(intent)
        self.assertIn("NEW_RISK_HALTED", {x["reason"] for x in r["rejections"]})

    def test_q12_five_positions_and_a_five_percent_cash_floor(self):
        held = {n: AT_95 for n in NAMES[:4]}
        s = snap(held, state=settled([19, 20], rebalance=True))
        r, intent = first_intent(s)
        self.assertEqual((intent["symbol"], intent["side"]), ("TSLAB", "BUY"))
        c = s.context.read()
        cash_after = c["portfolio"]["cash_units"] - intent["cash_units"] - intent["fee_units"]
        self.assertGreaterEqual(cash_after, 0)
        self.assertNotIn("POSITION_COUNT_CAP", {x["reason"] for x in r["rejections"]})

    def test_q14_per_name_leg_budget_replaces_the_session_rule(self):
        s = snap(last_discretionary_session=80)  # the old rule would block every discretionary trade
        r, intent = first_intent(s)
        self.assertIsNotNone(intent)
        first = intent["symbol"]
        s = snap(last_discretionary_session=80, discretionary_legs={first: 3})
        r, intent = first_intent(s)
        self.assertIn({"symbol": first, "reason": "DISCRETIONARY_CADENCE"}, r["rejections"])
        self.assertNotEqual(intent["symbol"], first)

    def test_q14_equal_weight_keeps_one_swap_per_session(self):
        from tests.strategy.test_equal_weight import ew
        s = changed(ew(), last_discretionary_session=80)
        r, intent = first_intent(s)
        self.assertIsNone(intent)
        self.assertIn("DISCRETIONARY_CADENCE", {x["reason"] for x in r["rejections"]})

    def live_s1(self, held, state):
        """A LIVE (FINAL) S1 snapshot inside the trading window, with Web3-origin markets."""
        from dataclasses import replace
        from larp.strategy.profiles import build_live_profiles
        from larp.strategy.schema import instant
        from tests.strategy.live_fixtures import registry, summary
        p = build_live_profiles(summary(), registry(), s1=block())["FINAL"].read()
        s = five_names(held=held, now=instant("2026-10-29T14:00:00Z"))
        c = s.context.read()
        c.update(profile=p, red_flag_predicates=registry().read())
        opened = s.observed_at.replace(hour=13, minute=30, second=0, microsecond=0)
        c['execution_session'] = dict(index=c['session_index'], open_ms=int(opened.timestamp()*1000),
            close_ms=int((opened + timedelta(hours=6, minutes=30)).timestamp()*1000),
            next_open_ms=int((opened + timedelta(days=1)).timestamp()*1000))
        c["health"]["new_spending_ok"] = True
        for m in c["markets"]:
            m.update(origin="WEB3_OPEN_API", source_id="WEB3")
        s = replace(s, policy_profile_hash=Document.from_dict(p).digest("StrategyProfile.v1"),
                    policy_state=replace(s.policy_state, policy_id=p["policy_id"]), context=Document.from_dict(c))
        return with_state(s, state)

    def test_q15_a_mandatory_safety_sell_ignores_impact_and_cost_limits_but_not_quote_checks(self):
        # IDEA-076 R3 (review TRV-02): under the S1 profile a mandatory sell (here a Class 1 exit) is exempt from the
        # impact threshold and the entry-style cost limits (DEV-05), which bind discretionary trades only; the
        # quote's route, slippage, age, expiry and LIVE-origin checks still apply.
        s = self.live_s1({"NVDAB": 1000}, {"blocked": {"NVDAB": {"reason": "CLASS_1_EXIT", "run_id": "synthetic-run"}}})
        s = with_quotes(s)
        c = s.context.read()
        p = c["profile"]
        nvdab = next(m for m in c["markets"] if m["symbol"] == "NVDAB")
        (q,) = [q for q in nvdab["quotes"] if q["side"] == "SELL"]
        mark = q["token_units"] * nvdab["price_units"] // 10 ** nvdab["decimals"]
        cash = mark // 2
        q.update(origin="WEB3_OPEN_API", impact_bps=10 * p["impact_bps"] + 100, cash_units=cash,
                 min_receive_units=cash * (10000 - p["slippage_bps"]) // 10000)
        q.pop("quoted_depth_units", None)
        self.assertGreater(q["impact_bps"], p["impact_bps"])
        self.assertGreater((mark - cash) * 10000, mark * 50)  # far over the 50 bp entry cost cap
        self.assertGreater(mark - cash, p["cost_reserve_units"])
        good = changed(s, markets=c["markets"])
        r = plan(good, decide(good, good.policy_state)).read()
        self.assertEqual([(i["symbol"], i["side"], i["mandatory"]) for i in r["intents"]], [("NVDAB", "SELL", True)])
        self.assertIn("CLASS_1_EXIT", r["intents"][0]["reasons"])
        self.assertNotIn("QUOTE_ROUTE_OR_SLIPPAGE", {x["reason"] for x in r["rejections"]})
        late = (s.observed_at - timedelta(seconds=p["quote_age_seconds"] + 1)).isoformat()
        for name, change in (("slippage", dict(slippage_bps=p["slippage_bps"] + 1)),
                             ("expired", dict(expires_at=s.observed_at.isoformat())),
                             ("stale", dict(observed_at=late, available_at=late)),
                             ("route", dict(route_valid=False)),
                             ("origin", dict(origin="SCRIPTED_FAKE")),
                             ("minimum", dict(min_receive_units=cash * (10000 - p["slippage_bps"]) // 10000 - 1))):
            with self.subTest(name):
                c = good.context.read()
                quotes = next(m for m in c["markets"] if m["symbol"] == "NVDAB")["quotes"]
                next(x for x in quotes if x["side"] == "SELL").update(change)
                b = changed(good, markets=c["markets"])
                r = plan(b, decide(b, b.policy_state)).read()
                self.assertFalse(r["intents"])
                self.assertIn("QUOTE_ROUTE_OR_SLIPPAGE", {x["reason"] for x in r["rejections"]})
                req = {x["symbol"]: x for x in r["requirements"]}["NVDAB"]
                self.assertEqual((req["status"], req["max_units"]), ("BLOCKED_QUOTE", 0))


class Settlement(unittest.TestCase):  # Q14: the per-name count comes from the settlement record
    def settle_swap(self, baseline, session=80, projection=None):
        from larp.integration.settlement import settle
        from tests.integration.test_settlement import RUN, WALLET, observation
        intent = dict(intent_id="i1", symbol="NVDAB", mandatory=False, decision_id="d1")
        record = dict(plan=dict(intents=[intent]), orders=[{}], swap_mappings=[],
                      policy_input=dict(context=dict(session_index=session, profile=dict(baseline=baseline))))
        current = Document.from_dict(dict(run_id=RUN, wallet_id=WALLET, reservations=[],
                                          projection=dict(projection or {}, round_records={"r1": record})))
        out = settle(current, Document.from_dict(observation(intent, "r1", "e1", "BROADCAST_ATTEMPTED")))
        return out.read()["projection"]

    def test_s1_counts_legs_per_name_per_session(self):
        p = self.settle_swap("TREND_GUARDED_VOL")
        self.assertEqual(p["discretionary_legs"], {"session": 80, "counts": {"NVDAB": 1}})
        p = self.settle_swap("TREND_GUARDED_VOL", projection={"discretionary_legs": {"session": 80, "counts": {"NVDAB": 2}}})
        self.assertEqual(p["discretionary_legs"]["counts"], {"NVDAB": 3})
        p = self.settle_swap("TREND_GUARDED_VOL", session=81,
                             projection={"discretionary_legs": {"session": 80, "counts": {"NVDAB": 3}}})
        self.assertEqual(p["discretionary_legs"], {"session": 81, "counts": {"NVDAB": 1}})

    def test_other_baselines_record_nothing_new(self):
        self.assertNotIn("discretionary_legs", self.settle_swap("EQUAL_WEIGHT"))

    def test_runtime_context_reads_only_this_session(self):
        from larp.integration.runtime import _legs
        p = {"discretionary_legs": {"session": 80, "counts": {"NVDAB": 2}}}
        self.assertEqual(_legs(p, 80), {"NVDAB": 2})
        self.assertEqual(_legs(p, 81), {})
        self.assertEqual(_legs({}, 80), {})


if __name__ == "__main__":
    unittest.main()


class LiveProfiles(unittest.TestCase):  # S05
    def build(self, **s1_changes):
        from larp.strategy.profiles import build_live_profiles
        from tests.strategy.live_fixtures import registry, summary
        return build_live_profiles(summary(), registry(), s1=block(**s1_changes))

    def test_s1_profiles_validate_and_size_for_a_full_top_position(self):
        from larp.strategy.profiles import validate_live
        from larp.strategy.schema import ceil
        for env, document in self.build().items():
            p = document.read()
            validate_live(p)
            self.assertEqual((p["baseline"], p["policy_id"]), ("TREND_GUARDED_VOL", "larp-s1-" + env.lower() + "-v1"))
            self.assertNotIn("operating_gross_weight", p)
            top = ceil(p["expected_equity_units"] * Fraction(19, 20) * Fraction(1, 5))
            self.assertEqual(p["per_trade_cap_units"], top + p["cost_reserve_units"])
            pair = max(r["approve_gas_bnb_units"] + r["swap_gas_bnb_units"]
                       for r in p["quote_cost_summary"]["symbols"].values())
            self.assertEqual(p["exit_gas_reserve_units"], 5 * pair)
            self.assertIn("proposed", p["provenance"]["s1"]["decision_id"])

    def test_validator_refuses_s1_defects(self):
        from larp.contracts import ContractError
        from larp.strategy.profiles import validate_live
        p = self.build()["FINAL"].read()
        for change in (dict(per_trade_cap_units=p["per_trade_cap_units"] - 1),
                       dict(exit_gas_reserve_units=p["exit_gas_reserve_units"] - 1),
                       dict(s1=dict(p["s1"], weight_cap=[2, 5]))):
            with self.subTest(change), self.assertRaises(ContractError):
                validate_live(dict(p, **change))
        with self.assertRaises(ContractError):
            validate_live({k: v for k, v in p.items() if k != "s1"})

    def test_equal_weight_profiles_are_unchanged(self):
        from larp.strategy.profiles import build_live_profiles
        from tests.strategy.live_fixtures import registry, summary
        p = build_live_profiles(summary(), registry())["FINAL"].read()
        self.assertEqual((p["baseline"], p["operating_gross_weight"]), ("EQUAL_WEIGHT", [4, 5]))
