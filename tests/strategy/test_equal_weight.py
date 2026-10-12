"""IDEA-037 pass criteria P01-P11 and P14-P17: EQUAL_WEIGHT baseline, top-up rebalancing and hard trim lines (synthetic)."""
from dataclasses import replace
from fractions import Fraction
import unittest

from larp.contracts import ContractError, Document, TargetKind
from larp.research.fixtures import snapshot, changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.schema import profile

EW = {"baseline": "EQUAL_WEIGHT", "operating_name_weight": [1, 5], "operating_gross_weight": [4, 5],
      "regime_gross_weight": [4, 5], "top_up_below_gross_weight": [3, 4],
      "hard_name_weight": [1, 4], "hard_gross_weight": [9, 10]}
COSTS = {"NVDAB": 20, "GOOGLB": 30, "TSLAB": 40, "MSFTB": 50, "SKHYB": 60}


def five_names(**kwargs):
    """The four-name fixture plus SKHYB, each with a distinct measured round-trip cost."""
    s = snapshot(profile_changes={**EW, **kwargs.pop("profile_changes", {})}, **kwargs)
    c = s.context.read()
    m = dict(c["markets"][0], symbol="SKHYB", underlying_id="fixture-issuer-SKHYB", token_id="fixture-token-SKHYB")
    c["markets"].append(m)
    c["series"]["SKHYB"] = dict(c["series"]["NVDAB"], entity_id="fixture-issuer-SKHYB")
    c["portfolio"]["positions"]["SKHYB"] = {"units": 0, "decimals": 4, "cost_basis_units": 0}
    for market in c["markets"]:
        market["measured_roundtrip_bps"] = COSTS[market["symbol"]]
    return replace(s, universe=s.universe + ("SKHYB",), context=Document.from_dict(c))


def ew(**kwargs):
    return snapshot(profile_changes={**EW, **kwargs.pop("profile_changes", {})}, **kwargs)


def with_state(s, data):
    return replace(s, policy_state=replace(s.policy_state, data=Document.from_dict(data)))


def by_symbol(proposal):
    return {t.symbol: t for t in proposal.targets}


class EqualWeightPolicy(unittest.TestCase):
    def test_p01_initial_build_takes_four_cheapest(self):
        s = five_names()
        t = by_symbol(decide(s, s.policy_state))
        for symbol in ("NVDAB", "GOOGLB", "TSLAB", "MSFTB"):
            self.assertEqual((t[symbol].kind, t[symbol].weight), (TargetKind.TARGET_WEIGHT, Fraction(1, 5)))
        self.assertEqual((t["SKHYB"].kind, t["SKHYB"].reason), (TargetKind.KEEP_QUANTITY, "NO_PORTFOLIO_CAPACITY"))
        self.assertEqual(sum(x.weight for x in t.values() if x.weight is not None), Fraction(4, 5))

    def test_p02_red_flagged_name_is_replaced_by_the_next_cheapest(self):
        s = five_names()
        s = with_state(s, {"blocked": {"GOOGLB": {"reason": "VERIFIED_FALSIFIER", "run_id": s.run_id}}})
        t = by_symbol(decide(s, s.policy_state))
        self.assertNotEqual(t["GOOGLB"].kind, TargetKind.TARGET_WEIGHT)
        self.assertEqual((t["SKHYB"].kind, t["SKHYB"].weight), (TargetKind.TARGET_WEIGHT, Fraction(1, 5)))

    def test_p03_no_buy_at_or_above_threshold(self):
        for units in (5000, 5100):  # 3 x 50 USDT = 75% exactly; 3 x 51 USDT = 76.5%
            s = ew(held={"NVDAB": units, "GOOGLB": units, "TSLAB": units})
            t = by_symbol(decide(s, s.policy_state))
            self.assertEqual((t["MSFTB"].kind, t["MSFTB"].reason), (TargetKind.KEEP_QUANTITY, "ABOVE_TOP_UP_THRESHOLD"))

    def test_p04_reinvests_freed_slot_after_a_sale(self):
        s = ew(held={"NVDAB": 4000, "GOOGLB": 4000, "TSLAB": 4000})  # 3 x 20%, gross 60%
        t = by_symbol(decide(s, s.policy_state))
        self.assertEqual((t["MSFTB"].kind, t["MSFTB"].weight), (TargetKind.TARGET_WEIGHT, Fraction(1, 5)))
        s = with_quotes(s)
        r = plan(s, decide(s, s.policy_state)).read()
        self.assertEqual([(i["symbol"], i["side"], i["mandatory"]) for i in r["intents"]], [("MSFTB", "BUY", False)])
        safe = 200_000_000 - s.context.read()["profile"]["cost_reserve_units"]
        self.assertLessEqual(r["intents"][0]["cash_units"] + r["intents"][0]["fee_units"], safe // 5)

    def test_p05_no_sell_on_drift(self):
        # Revised by the IDEA-037 addendum: the fallen name is now topped up (P14); the drifted one is still held.
        s = ew(held={"NVDAB": 4400, "GOOGLB": 3000})  # about 22% and 15%, gross 37%
        t = by_symbol(decide(s, s.policy_state))
        self.assertEqual(t["NVDAB"].kind, TargetKind.KEEP_QUANTITY)
        self.assertEqual((t["GOOGLB"].kind, t["GOOGLB"].weight), (TargetKind.TARGET_WEIGHT, Fraction(1, 5)))
        s = with_quotes(s)
        r = plan(s, decide(s, s.policy_state)).read()
        self.assertFalse(r["requirements"])
        self.assertFalse([i for i in r["intents"] if i["side"] == "SELL"])

    def test_p14_p15_tops_up_held_names_and_skips_small_gaps(self):
        s = ew(held={"NVDAB": 3000, "GOOGLB": 4000, "TSLAB": 4000, "MSFTB": 3500})  # gross 72.5%
        t = by_symbol(decide(s, s.policy_state))
        for symbol in ("NVDAB", "MSFTB"):
            self.assertEqual((t[symbol].kind, t[symbol].reason, t[symbol].weight),
                             (TargetKind.TARGET_WEIGHT, "TOP_UP_TO_EQUAL_WEIGHT", Fraction(1, 5)))
        for symbol in ("GOOGLB", "TSLAB"):
            self.assertEqual(t[symbol].kind, TargetKind.KEEP_QUANTITY)
        s = with_quotes(s)
        r = plan(s, decide(s, s.policy_state)).read()
        self.assertEqual([(i["symbol"], i["side"], i["mandatory"]) for i in r["intents"]], [("NVDAB", "BUY", False)])
        self.assertIn({"symbol": "MSFTB", "reason": "MINIMUM_TRADE"}, r["rejections"])

    def test_p16_no_top_up_at_or_above_threshold(self):
        s = ew(held={"NVDAB": 3000, "GOOGLB": 4000, "TSLAB": 4000, "MSFTB": 4500})  # gross 77.5%
        self.assertEqual(by_symbol(decide(s, s.policy_state))["NVDAB"].kind, TargetKind.KEEP_QUANTITY)

    def test_p17_loss_stop_blocks_top_ups(self):
        s = ew(held={"NVDAB": 3000, "GOOGLB": 4000, "TSLAB": 4000, "MSFTB": 3500})
        c = s.context.read()
        c["portfolio"]["risk"]["run_halt"] = True
        s = with_quotes(changed(s, portfolio=c["portfolio"]))
        r = plan(s, decide(s, s.policy_state)).read()
        self.assertFalse(r["intents"])
        self.assertIn({"symbol": "NVDAB", "reason": "NEW_RISK_HALTED"}, r["rejections"])

    def test_p09_gates_retained(self):
        held = {"NVDAB": 4000}
        flatten = ew(held=held, profile_changes={"flatten_start": "2026-10-10T13:00:00Z",
                                                  "new_risk_end": "2026-10-10T12:00:00Z"})
        self.assertTrue(all(t.kind is TargetKind.EXIT for t in decide(flatten, flatten.policy_state).targets
                            if t.symbol == "NVDAB"))
        late = ew(held={"NVDAB": 3000}, profile_changes={"new_risk_end": "2026-10-10T13:00:00Z"})
        self.assertFalse([t for t in decide(late, late.policy_state).targets if t.kind is TargetKind.TARGET_WEIGHT])
        s = ew(held={"NVDAB": 4000, "GOOGLB": 4000, "TSLAB": 4000})
        s = with_state(s, {"lifecycle": {"MSFTB": {"status": "CASH_REVIEW", "last_review_session": 80,
                                                   "ever_held": True, "observed_session": 79}}})
        self.assertEqual(by_symbol(decide(s, s.policy_state))["MSFTB"].reason, "ENTRY_OR_REENTRY_UNAVAILABLE")
        s = ew()
        c = s.context.read()
        c["portfolio"]["risk"]["run_halt"] = True
        s = with_quotes(changed(s, portfolio=c["portfolio"]))
        r = plan(s, decide(s, s.policy_state)).read()
        self.assertFalse(r["intents"])
        self.assertIn("NEW_RISK_HALTED", {x["reason"] for x in r["rejections"]})

    def test_p10_no_price_history_needed(self):
        s = ew()
        series = s.context.read()["series"]
        series["NVDAB"] = dict(series["NVDAB"], bars=series["NVDAB"]["bars"][-20:])
        short = changed(s, series=series)
        self.assertEqual(by_symbol(decide(short, short.policy_state))["NVDAB"].kind, TargetKind.TARGET_WEIGHT)
        declared = snapshot()
        declared = changed(declared, series=series)
        self.assertEqual(by_symbol(decide(declared, declared.policy_state))["NVDAB"].reason, "INSUFFICIENT_FEATURES")


class HardTrimLines(unittest.TestCase):
    def requirements(self, held, **risk):
        s = ew(held=held)
        if risk:
            c = s.context.read()
            c["portfolio"]["risk"].update(risk)
            s = changed(s, portfolio=c["portfolio"])
        return s, {r["symbol"]: r for r in plan(s, None).read()["requirements"]}

    def test_p06_hard_per_name_line(self):
        _, below = self.requirements({"NVDAB": 4800})  # about 24%
        self.assertFalse(below)
        s, above = self.requirements({"NVDAB": 5200})  # about 26%
        r = above["NVDAB"]
        self.assertIn("POSITION_CAP", r["reasons"])
        safe = 200_000_000 - s.context.read()["profile"]["cost_reserve_units"]
        self.assertLessEqual(r["max_units"] * 10_000, safe // 5)

    def test_p07_hard_gross_line(self):
        _, held_85 = self.requirements({s: 4250 for s in ("NVDAB", "GOOGLB", "TSLAB", "MSFTB")})
        self.assertFalse(held_85)
        s, held_92 = self.requirements({s: 4600 for s in ("NVDAB", "GOOGLB", "TSLAB", "MSFTB")})
        self.assertEqual(len(held_92), 4)
        self.assertTrue(all("GROSS_OR_REGIME_CAP" in r["reasons"] for r in held_92.values()))
        safe = 200_000_000 - s.context.read()["profile"]["cost_reserve_units"]
        self.assertLessEqual(sum(r["max_units"] for r in held_92.values()) * 10_000, safe * 4 // 5)

    def test_p08_deep_drawdown_trims_at_forty_percent(self):
        s, held = self.requirements({"NVDAB": 4000, "GOOGLB": 4000, "TSLAB": 4000}, deep_cut=True)
        self.assertEqual(len(held), 3)
        self.assertTrue(all("DEEP_DRAWDOWN" in r["reasons"] for r in held.values()))
        safe = 200_000_000 - s.context.read()["profile"]["cost_reserve_units"]
        self.assertLessEqual(sum(r["max_units"] for r in held.values()) * 10_000, safe * 2 // 5)


class ProfileValidation(unittest.TestCase):
    def test_p11_rejects_out_of_range_settings(self):
        for changes in ({"top_up_below_gross_weight": None}, {"top_up_below_gross_weight": [81, 100]},
                        {"hard_name_weight": [19, 100]}, {"hard_name_weight": [26, 100]},
                        {"hard_gross_weight": [79, 100]}, {"hard_gross_weight": [91, 100]}):
            s = ew(profile_changes=changes)
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                profile(s)
        s = ew(profile_changes={"operating_name_weight": [1, 5], "hard_name_weight": [1, 5]})
        self.assertEqual(profile(s)["hard_name_weight"], [1, 5])
        with self.assertRaises(ContractError):
            profile(ew(profile_changes={"baseline": "BUY_THE_DIP"}))


if __name__ == "__main__":
    unittest.main()
