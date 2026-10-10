from dataclasses import replace
from datetime import timedelta
import unittest

from larp.contracts import ContractError, Document
from larp.research.fixtures import snapshot, changed, with_quotes, reserve_fixture, fill_fixture
from larp.risk.accounting import advance_accounting, roll_day, update_risk, economic_views
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.schema import equity, markets, profile


class RiskTests(unittest.TestCase):
    def planned(self, s, policy=True, **quote_options):
        s = with_quotes(s, policy=policy, **quote_options)
        return s, plan(s, decide(s, s.policy_state) if policy else None)

    def test_baseline_reservations_and_actual_fill(self):
        s, result = self.planned(snapshot())
        intent = result.read()["intents"][0]
        self.assertEqual(s.context.read()["portfolio"]["positions"][intent["symbol"]]["units"], 0)
        reserved = reserve_fixture(s, result)
        before = Document.from_dict(reserved.context.read()["portfolio"])
        event = fill_fixture(s, intent)
        after = advance_accounting(before, event)
        self.assertEqual(after.read()["positions"][intent["symbol"]]["units"], intent["token_units"])
        self.assertEqual(advance_accounting(after, event), after)
        altered = event.read()
        altered["cash_units"] += 1
        with self.assertRaises(ContractError):
            advance_accounting(after, Document.from_dict(altered))

    def test_invalid_and_absent_policy_still_reduce(self):
        s = snapshot(held={"NVDAB": 8000})
        old = decide(s, s.policy_state)
        c = s.context.read()
        c["portfolio"]["cash_units"] -= 1
        s = changed(s, portfolio=c["portfolio"])
        s = with_quotes(s, policy=False)
        for p in (None, old):
            result = plan(s, p).read()
            self.assertTrue(result["requirements"])
            self.assertTrue(result["intents"][0]["mandatory"])

    def test_strictest_reduction_and_no_discretionary_buy(self):
        s = snapshot(held={"NVDAB": 6000, "MSFTB": 6000})
        c = s.context.read()
        c["portfolio"]["cash_units"] -= 40_000_000
        s = changed(s, portfolio=c["portfolio"], reduction_constraints=[
            {"symbol": "NVDAB", "max_units": 1000, "reason": "EXTRA_REDUCTION"}])
        s, result = self.planned(s)
        r = result.read()
        n = next(x for x in r["requirements"] if x["symbol"] == "NVDAB")
        self.assertLessEqual(n["max_units"], 1000)
        self.assertIn("DEEP_DRAWDOWN", n["reasons"])
        self.assertTrue(all(x["side"] == "SELL" for x in r["intents"]))

    def test_mandatory_bypasses_minimum_and_cadence_but_market_blocks(self):
        s = snapshot(held={"NVDAB": 100})
        s = changed(s, reduction_constraints=[{"symbol": "NVDAB", "max_units": 0, "reason": "FIXTURE_EXIT"}],
                    last_discretionary_session=80)
        s, result = self.planned(s, policy=False)
        self.assertTrue(result.read()["intents"])
        c = s.context.read()
        c["markets"][0]["underlying_open"] = False
        blocked = plan(changed(s, markets=c["markets"]), None).read()
        self.assertFalse(blocked["intents"])
        self.assertEqual(blocked["requirements"][0]["status"], "BLOCKED_MARKET")

    def test_pending_buy_and_sell_block_allocation_and_retain_requirement(self):
        s = snapshot(held={"NVDAB": 8000})
        c = s.context.read()
        c["portfolio"]["reservations"] = {"pending": {"side": "BUY", "symbol": "MSFTB",
            "cash_units": 30_000_000, "bnb_units": 10000, "token_units": 3000}}
        s = changed(s, portfolio=c["portfolio"])
        r = plan(s, None).read()
        self.assertEqual(r["worst_case_gross_units"], 110_000_000)
        self.assertFalse(r["intents"])
        self.assertTrue(r["requirements"])
        self.assertIn("WALLET_PENDING", r["rejections"][-1]["gates"])
        c["portfolio"]["reservations"]["pending"].update(side="SELL", symbol="NVDAB", cash_units=0)
        self.assertFalse(plan(changed(s, portfolio=c["portfolio"]), None).read()["intents"])

    def test_midnight_only_resets_daily_latch_and_marks_missing_anchor(self):
        s = snapshot()
        p = s.context.read()["portfolio"]
        p["risk"].update(daily_halt=True, run_halt=True, deep_cut=True)
        day = "2026-10-11T00:00:00Z"
        after = roll_day(Document.from_dict(p), boundary=day, anchor_units=200_000_000)
        self.assertFalse(after.read()["risk"]["daily_halt"])
        self.assertTrue(after.read()["risk"]["run_halt"])
        self.assertTrue(after.read()["risk"]["deep_cut"])
        risk = update_risk(after, now=s.observed_at + timedelta(days=1), equity_units=190_000_000)
        self.assertTrue(risk.read()["risk"]["daily_halt"])
        with self.assertRaises(ContractError):
            roll_day(after, boundary=day, anchor_units=190_000_000)

    def test_exit_may_spend_exit_gas_reserve_but_zero_gas_blocks(self):
        s = snapshot(held={"NVDAB": 8000})
        c = s.context.read()
        c["portfolio"]["bnb_units"] = 15000
        s, result = self.planned(changed(s, portfolio=c["portfolio"]), policy=False)
        self.assertTrue(result.read()["intents"])
        c = s.context.read()
        c["portfolio"]["bnb_units"] = 0
        blocked = plan(changed(s, portfolio=c["portfolio"]), None).read()
        self.assertFalse(blocked["intents"])
        self.assertTrue(blocked["requirements"])

    def test_split_exit_dust_and_post_cost_cap(self):
        s = snapshot(held={"NVDAB": 8000}, profile_changes={"per_trade_cap_units": 15_000_000})
        s, result = self.planned(s, policy=False)
        intent = result.read()["intents"][0]
        self.assertLessEqual(intent["cash_units"], 15_000_000)
        self.assertGreater(intent["parent_remaining_units"], 0)
        s = snapshot(held={"NVDAB": 10}, profile_changes={"dust_units": 20})
        r = plan(changed(s, reduction_constraints=[{"symbol": "NVDAB", "max_units": 0, "reason": "EXIT"}]), None).read()
        self.assertEqual(r["requirements"][0]["status"], "DUST_OR_UNEXECUTABLE")

    def test_approvals_reverts_gas_service_and_terminal_equity(self):
        s, result = self.planned(snapshot())
        intent = result.read()["intents"][0]
        committed = reserve_fixture(s, result)
        initial = Document.from_dict(committed.context.read()["portfolio"])
        approval = fill_fixture(s, intent, kind="APPROVAL", gas=4000, terminal=False)
        a = advance_accounting(initial, approval)
        self.assertEqual(a.read()["positions"][intent["symbol"]]["units"], 0)
        self.assertTrue(a.read()["reservations"])
        revert = fill_fixture(s, intent, kind="REVERT", gas=6000)
        b = advance_accounting(a, revert)
        E = equity(b.read(), markets(s, profile(s)))
        self.assertEqual(E, 200_000_000 - 10000)
        views = economic_views(b, equity_units=E).read()
        self.assertEqual(views["wallet_net_units"], -10000)
        service = Document.from_dict({"schema": "ServiceCostObservation.v1", "run_id": s.run_id,
            "wallet_id": s.wallet_id, "event_id": "fake-model-cost", "cost_units": 5000,
            "observed_at": s.observed_at.isoformat()})
        b = advance_accounting(b, service)
        views = economic_views(b, equity_units=E).read()
        self.assertEqual(views["total_economic_net_units"], -15000)
        self.assertEqual(advance_accounting(b, service), b)
        self.assertFalse(b.read()["reservations"])
        terminal = snapshot(held={"NVDAB": 2000}, now=s.observed_at.replace(day=21))
        terminal, r = self.planned(terminal, policy=False)
        self.assertIn("TERMINAL_FLATTEN", r.read()["intents"][0]["reasons"])

    def test_costly_opportunity_rejected(self):
        s = snapshot(profile_changes={"cost_reserve_units": 1_000_000})
        s, result = self.planned(s, spread_bps=80)
        self.assertFalse(result.read()["intents"])
        self.assertIn("ENTRY_COST_CAP", [x["reason"] for x in result.read()["rejections"]])

    def test_unknown_integrity_blocks_mandatory_and_invalid_price_preserves_holdings(self):
        s = snapshot(held={"NVDAB": 8000})
        c = s.context.read()
        c["health"]["journal_ok"] = False
        r = plan(changed(s, health=c["health"]), None).read()
        self.assertFalse(r["intents"])
        self.assertTrue(r["requirements"])
        c["markets"][0]["quality"] = "UNKNOWN"
        r = plan(changed(s, markets=c["markets"]), None).read()
        self.assertTrue(r["requirements"])
        self.assertEqual(s.context.read()["portfolio"]["positions"]["NVDAB"]["units"], 8000)

    def test_post_cost_caps_at_both_wallet_sizes(self):
        for funding in (100_000_000, 200_000_000):
            s = snapshot()
            c = s.context.read()
            c["portfolio"]["cash_units"] = funding - 1_000_000
            c["portfolio"]["opening_equity_units"] = funding
            c["portfolio"]["risk"].update(day_anchor_units=funding, peak_units=funding)
            s, r = self.planned(changed(s, portfolio=c["portfolio"]))
            intent = r.read()["intents"][0]
            m = next(x for x in s.context.read()["markets"] if x["symbol"] == intent["symbol"])
            from larp.strategy.schema import value
            mark = value(intent["token_units"], m)
            cost = intent["cash_units"] - mark + intent["fee_units"] + intent["gas_bnb_units"]
            self.assertLessEqual(mark * 5, funding - cost)
            self.assertGreaterEqual(c["portfolio"]["cash_units"] - intent["cash_units"], (funding - cost) / 5)

    def test_split_parent_replanned_after_actual_fill_and_fee(self):
        s, r = self.planned(snapshot(held={"NVDAB": 8000}, profile_changes={"per_trade_cap_units": 15_000_000}), policy=False)
        c = s.context.read()
        for quote in c["markets"][0]["quotes"]:
            quote["fee_units"] = 100
        s = changed(s, markets=c["markets"])
        r = plan(s, None)
        intent = r.read()["intents"][0]
        reserved = reserve_fixture(s, r)
        settled = advance_accounting(Document.from_dict(reserved.context.read()["portfolio"]), fill_fixture(s, intent))
        self.assertEqual(settled.read()["accounting"]["fees_units"], 100)
        self.assertEqual(settled.read()["positions"]["NVDAB"]["units"], 8000 - intent["token_units"])
        following = plan(changed(s, portfolio=settled.read()), None).read()
        self.assertGreater(following["requirements"][0]["remaining_sell_units"], 0)
        self.assertLess(following["requirements"][0]["remaining_sell_units"], r.read()["requirements"][0]["remaining_sell_units"])

    def test_mandatory_cost_above_planning_estimate_does_not_veto_reduction(self):
        s, r = self.planned(snapshot(held={"NVDAB": 8000}, profile_changes={"cost_reserve_units": 1000}), policy=False)
        self.assertTrue(r.read()["intents"])
        self.assertTrue(r.read()["intents"][0]["mandatory"])
        self.assertIn("POST_QUOTE_COST_REDUCTION", [c["reason"] for c in r.read()["clamps"]])
        self.assertTrue(r.read()["requirements"])

    def test_malformed_quote_is_blocked_not_an_exception(self):
        s = with_quotes(snapshot(held={"NVDAB": 8000}), policy=False)
        for patch_value in ({"fee_units": -1}, {"gas_bnb_units": "bad"},
                            {"expires_at": "bad"}, {"quote_id": ""}, {"route_valid": "yes"}):
            c = s.context.read()
            c["markets"][0]["quotes"][0].update(patch_value)
            r = plan(changed(s, markets=c["markets"]), None).read()
            self.assertFalse(r["intents"])
            self.assertEqual(r["requirements"][0]["status"], "BLOCKED_QUOTE")

    def test_exact_input_buy_records_variable_received_quantity(self):
        s, result = self.planned(snapshot())
        intent = result.read()["intents"][0]
        self.assertEqual(intent["pay_asset"], "USDT")
        before = Document.from_dict(reserve_fixture(s, result).context.read()["portfolio"])
        for received in (intent["token_units"] - 1, intent["token_units"], intent["token_units"] + 1):
            e = fill_fixture(s, intent).read()
            e["token_units"] = received
            after = advance_accounting(before, Document.from_dict(e)).read()
            self.assertEqual(after["positions"][intent["symbol"]]["units"], received)
            self.assertEqual(after["positions"][intent["symbol"]]["cost_basis_units"], intent["cash_units"] + intent["fee_units"])
            self.assertFalse(after["reservations"])
        for patch in ({"token_units": intent["min_receive_units"] - 1}, {"cash_units": intent["cash_units"] - 1},
                      {"fee_units": before["reservations"][intent["intent_id"]]["cash_units"] + 1}):
            e = {**fill_fixture(s, intent).read(), **patch}
            with self.assertRaises(ContractError):
                advance_accounting(before, Document.from_dict(e))
        request = plan(snapshot(), decide(snapshot(), snapshot().policy_state)).read()["quote_requests"][0]
        self.assertEqual(request["pay_asset"], "USDT")
        self.assertNotIn("token_units", request)

    def test_exact_input_sell_accepts_variable_proceeds_above_minimum(self):
        s, result = self.planned(snapshot(held={"NVDAB": 8000}), policy=False)
        intent = result.read()["intents"][0]
        initial = Document.from_dict(reserve_fixture(s, result).context.read()["portfolio"])
        for cash in (intent["cash_units"] - 1, intent["cash_units"] + 1):
            e = {**fill_fixture(s, intent).read(), "cash_units": cash}
            settled = advance_accounting(initial, Document.from_dict(e)).read()
            self.assertEqual(settled["cash_units"], initial.read()["cash_units"] + cash - intent["fee_units"])
        for patch in ({"token_units": intent["token_units"] - 1}, {"cash_units": intent["min_receive_units"] - 1}):
            with self.assertRaises(ContractError):
                advance_accounting(initial, Document.from_dict({**fill_fixture(s, intent).read(), **patch}))

    def test_stale_name_does_not_block_healthy_terminal_or_cap_exit(self):
        for terminal in (False, True):
            s = snapshot(held={"NVDAB": 8000, "MSFTB": 2000})
            if terminal:
                s = snapshot(held={"NVDAB": 8000, "MSFTB": 2000}, now=s.observed_at.replace(day=21))
            c = s.context.read()
            msft = next(m for m in c["markets"] if m["symbol"] == "MSFTB")
            msft["observed_at"] = (s.observed_at - timedelta(minutes=5)).isoformat()
            s = changed(s, markets=c["markets"])
            raw = plan(s, None).read()
            self.assertEqual(raw["valuation_status"], "LOWER_BOUND")
            self.assertIsNone(raw["worst_case_gross_units"])
            self.assertEqual(raw["risk_state"], c["portfolio"]["risk"])
            self.assertTrue(any(q["symbol"] == "NVDAB" for q in raw["quote_requests"]))
            self.assertFalse(any(q["symbol"] == "MSFTB" for q in raw["quote_requests"]))
            s, result = self.planned(s, policy=False)
            self.assertEqual(result.read()["intents"][0]["symbol"], "NVDAB")
            blocked = next(r for r in result.read()["requirements"] if r["symbol"] == "MSFTB")
            self.assertEqual(blocked["status"], "BLOCKED_MARK")
            self.assertEqual(blocked["held_units"], 2000)

    def test_nonpositive_terminal_equity_retains_flatten_requirement(self):
        s = snapshot(held={"NVDAB": 2000}, now=snapshot().observed_at.replace(day=21))
        c = s.context.read()
        c["portfolio"].update(cash_units=0, bnb_units=0)
        c["markets"][0]["quality"] = "UNKNOWN"
        r = plan(changed(s, portfolio=c["portfolio"], markets=c["markets"]), None).read()
        self.assertEqual(r["risk_equity_lower_bound_units"], 0)
        self.assertIn("TERMINAL_FLATTEN", r["requirements"][0]["reasons"])
        self.assertFalse(r["intents"])

    def test_better_sell_price_requests_smaller_quote_and_can_progress(self):
        s = with_quotes(snapshot(held={"NVDAB": 8000}, profile_changes={"per_trade_cap_units": 15_000_000}),
                        policy=False, spread_bps=-7)
        r = plan(s, None).read()
        self.assertFalse(r["intents"])
        q = next(q for q in r["quote_requests"] if q["symbol"] == "NVDAB")
        self.assertLess(q["pay_units"], 1500)
        self.assertEqual(r["requirements"][0]["status"], "REQUOTE_REQUIRED")
        # New observed exact-size quote, not a fabricated proportional fill.
        following = with_quotes(s, policy=False, spread_bps=-7)
        r = plan(following, None).read()
        self.assertTrue(r["intents"])
        self.assertLessEqual(r["intents"][0]["cash_units"] + r["intents"][0]["fee_units"], 15_000_000)
        self.assertGreater(r["intents"][0]["parent_remaining_units"], 0)

    def test_rejected_cost_overrun_does_not_rescale_other_requirements(self):
        s = snapshot(held={"NVDAB": 8000, "MSFTB": 6000}, profile_changes={"cost_reserve_units": 1000})
        before = plan(s, None).read()
        quoted = with_quotes(s, policy=False, gas=2_000_000)
        after = plan(quoted, None).read()
        self.assertFalse(after["intents"])
        self.assertNotIn("POST_QUOTE_COST_REDUCTION", [c["reason"] for c in after["clamps"]])
        self.assertEqual([(r["symbol"], r["max_units"]) for r in before["requirements"]],
                         [(r["symbol"], r["max_units"]) for r in after["requirements"]])
        self.assertTrue(all(r["status"] == "BLOCKED_GAS" for r in after["requirements"]))
