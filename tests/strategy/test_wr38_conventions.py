"""WR-38 (#38, IDEA-049-B): pin current portfolio/cost conventions, synthetic.

These tests characterize behaviour; they do not adopt it. B-DEC-02 (risk mark), B-DEC-03 (concentration and
staggered build) and B-DEC-06 (exit costs) are open team decisions. A decision that changes one of these
conventions must change the matching test on purpose and record why in docs/ledger/IDEA-049-B.md.
"""
from dataclasses import replace
from datetime import timedelta
from fractions import Fraction
import unittest

from larp.contracts import Document, TargetKind
from larp.research.fixtures import changed, fill_fixture, reserve_fixture, with_quotes
from larp.risk.accounting import advance_accounting
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.schema import ceil, floor, value
from tests.strategy.test_equal_weight import by_symbol, ew, five_names

NAMES = ("NVDAB", "GOOGLB", "TSLAB", "MSFTB")


def run(s):
    proposal = decide(s, s.policy_state)
    return proposal, plan(s, proposal).read()


class RiskMarkConvention(unittest.TestCase):
    """WR38-1: risk equity and the loss latches use the token mark, not executable sell proceeds."""

    def test_wr38_1_sell_quotes_below_the_mark_do_not_change_risk_equity_or_halts(self):
        s = ew(held=dict.fromkeys(NAMES, 4500))  # 22.5% each, gross 90%: no trim
        c = s.context.read()
        haircut_proceeds = 0
        for m in c["markets"]:
            units = c["portfolio"]["positions"][m["symbol"]]["units"]
            cash = floor(value(units, m) * Fraction(9, 10))  # executable proceeds 10% below the mark
            haircut_proceeds += cash
            m["quotes"].append({"quote_id": "fake-liquidation-" + m["symbol"], "side": "SELL",
                                "amount_kind": "EXACT_IN", "pay_asset": m["symbol"], "pay_units": units,
                                "token_units": units, "cash_units": cash, "min_receive_units": cash,
                                "fee_units": 0, "gas_bnb_units": 10000, "route_valid": True,
                                "slippage_bps": 20, "impact_bps": 1000, "quoted_depth_units": units * 100,
                                "available_at": s.observed_at.isoformat(), "observed_at": s.observed_at.isoformat(),
                                "expires_at": (s.observed_at + timedelta(seconds=30)).isoformat(), "origin": "SCRIPTED_FAKE"})
        quoted = changed(s, markets=c["markets"])

        base_proposal, base = run(s)
        quoted_proposal, result = run(quoted)
        for key in ("risk_equity_lower_bound_units", "valuation_status", "risk_state"):
            self.assertEqual(result[key], base[key], key)
        self.assertEqual(result["valuation_status"], "COMPLETE")
        self.assertEqual(result["risk_equity_lower_bound_units"], 200_000_000)
        risk = result["risk_state"]
        self.assertEqual(risk["peak_units"], 200_000_000)
        self.assertFalse(risk["run_halt"] or risk["deep_cut"] or risk["daily_halt"])
        self.assertEqual(quoted_proposal.targets, base_proposal.targets)

        # The documented gap: at the quoted proceeds the same book is at or below the 92% run-halt line.
        ledger = c["portfolio"]
        liquidation = ledger["cash_units"] + ledger["bnb_units"] * ledger["bnb_price_units"] // 10 ** ledger["bnb_decimals"]
        liquidation += haircut_proceeds
        self.assertLessEqual(liquidation * 100, risk["peak_units"] * 92)


class CostRankingConvention(unittest.TestCase):
    """WR38-2: entries rank by the market row's static measured_roundtrip_bps, not the exact-size all-in cost."""

    @staticmethod
    def requote(quote, m, *, spread_bps, gas):
        q = quote["pay_units"] * 10 ** m["decimals"] * 10000 // (m["price_units"] * (10000 + spread_bps))
        quote.update(token_units=q, min_receive_units=max(1, q * 9980 // 10000), gas_bnb_units=gas,
                     impact_bps=spread_bps, quoted_depth_units=q * 100)

    @staticmethod
    def all_in_cost(quote, m, ledger):
        # The planner's own BUY cost: spread against the mark, plus fee, plus gas valued at the BNB mark.
        gas_value = ceil(Fraction(quote["gas_bnb_units"] * ledger["bnb_price_units"], 10 ** ledger["bnb_decimals"]))
        mark = value(quote["token_units"], m)
        return max(Fraction(0), quote["cash_units"] - mark) + quote["fee_units"] + gas_value, mark

    def test_wr38_2_cheapest_measured_name_is_bought_even_when_its_quote_costs_more(self):
        s = with_quotes(five_names())
        c = s.context.read()
        rows = {m["symbol"]: m for m in c["markets"]}
        buys = {symbol: [q for q in m["quotes"] if q["side"] == "BUY"] for symbol, m in rows.items()}
        self.assertEqual(sorted(symbol for symbol, q in buys.items() if q), sorted(NAMES))
        self.requote(buys["NVDAB"][0], rows["NVDAB"], spread_bps=15, gas=20000)
        self.requote(buys["GOOGLB"][0], rows["GOOGLB"], spread_bps=0, gas=0)
        s = changed(s, markets=c["markets"])

        reserve = c["profile"]["cost_reserve_units"]
        nvdab, nvdab_mark = self.all_in_cost(buys["NVDAB"][0], rows["NVDAB"], c["portfolio"])
        googlb, _ = self.all_in_cost(buys["GOOGLB"][0], rows["GOOGLB"], c["portfolio"])
        self.assertLess(rows["NVDAB"]["measured_roundtrip_bps"], rows["GOOGLB"]["measured_roundtrip_bps"])
        self.assertGreater(nvdab, googlb)  # the exact-size all-in order is reversed
        self.assertLessEqual(nvdab, reserve)  # both stay inside the reserve and the 50 bp entry cap
        self.assertLessEqual(nvdab * 10000, nvdab_mark * 50)

        proposal, result = run(s)
        targets = by_symbol(proposal)
        self.assertEqual(sorted(t for t, x in targets.items() if x.kind is TargetKind.TARGET_WEIGHT), sorted(NAMES))
        self.assertEqual(targets["SKHYB"].reason, "NO_PORTFOLIO_CAPACITY")
        self.assertEqual([(i["symbol"], i["side"], i["mandatory"]) for i in result["intents"]],
                         [("NVDAB", "BUY", False)])


class StaggeredBuildConvention(unittest.TestCase):
    """WR38-3: one child per plan and one discretionary action per session, so four fresh names need four sessions."""

    def settle(self, s, proposal, planned, session):
        result = planned.read()
        reserved = reserve_fixture(s, planned)
        ledger = reserved.context.read()["portfolio"]
        ledger["risk"] = result["risk_state"]
        ledger = advance_accounting(Document.from_dict(ledger), fill_fixture(s, result["intents"][0])).read()
        markets = [dict(m, quotes=[]) for m in s.context.read()["markets"]]
        return changed(replace(s, policy_state=proposal.next_policy_state), portfolio=ledger,
                       markets=markets, last_discretionary_session=session)

    def test_wr38_3_fresh_four_name_book_takes_four_distinct_sessions(self):
        s = ew()
        bought = []
        for session in range(80, 85):
            s = changed(s, session_index=session, remaining_sessions=90 - session)
            s = with_quotes(s)
            proposal = decide(s, s.policy_state)
            if session == 80:
                entries = {t.symbol for t in proposal.targets if t.reason == "UNVALIDATED_BASELINE_ENTRY"}
                self.assertEqual(entries, set(NAMES))  # the policy proposes the whole book at once
            planned = plan(s, proposal)
            intents = planned.read()["intents"]
            held = {n for n, p in s.context.read()["portfolio"]["positions"].items() if p["units"]}
            self.assertEqual(held, set(bought))
            if session == 84:
                self.assertEqual(intents, [])
                self.assertEqual(len(held), 4)
                break
            with self.subTest(session=session):
                self.assertEqual(len(intents), 1)
                self.assertEqual((intents[0]["side"], intents[0]["mandatory"]), ("BUY", False))
                self.assertNotIn(intents[0]["symbol"], held)
                again = changed(s, last_discretionary_session=session)
                repeat = plan(again, decide(again, again.policy_state)).read()
                self.assertEqual(repeat["intents"], [])
                self.assertIn("DISCRETIONARY_CADENCE", {r["reason"] for r in repeat["rejections"]})
            bought.append(intents[0]["symbol"])
            s = self.settle(s, proposal, planned, session)
            self.assertEqual(len(bought), session - 79)
        self.assertEqual(sorted(bought), sorted(NAMES))


if __name__ == "__main__":
    unittest.main()
