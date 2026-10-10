from dataclasses import replace
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.research.candles import adjacent_pairs, ar_estimate, category_variance
from larp.research.evaluation import evaluate, fusion_rows
from larp.research.fixtures import snapshot, changed, with_quotes, reserve_fixture, fill_fixture
from larp.risk.accounting import advance_accounting
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.research.replay import replay_snapshots, seeded_observations, replay_accounting, replay_seeded
from tools.realised_vol import bstock_series, stats


class ResearchTests(unittest.TestCase):
    def test_gaps_and_session_filters_do_not_create_lag_pairs(self):
        returns = [(1, .01), (2, -.01), (10, .03), (11, -.02), (12, .01)]
        self.assertEqual(len(adjacent_pairs(returns, 1)), 3)
        self.assertEqual(adjacent_pairs(returns, 1, lambda t: t in {2, 10}), [])

    def test_cross_session_gap_is_not_category_variance(self):
        totals, gaps = category_variance({14: 100, 15: 101, 18: 110}, 1,
                                         lambda t: "RTH" if t < 16 else "AFTER")
        self.assertEqual(totals["RTH"][1], 1)
        self.assertNotIn("AFTER", totals)
        self.assertEqual(gaps[0][2], 3)

    def test_ar_pairs_require_exact_interval(self):
        bars = {0: [100, 102, 98, 101], 1: [100, 101, 99, 100], 9: [110, 115, 105, 110]}
        self.assertEqual(ar_estimate(bars, 1)[1], 1)

    def test_entity_failure_cannot_shift_other_token_volatility(self):
        raw = [
            {"endpoint": "rwa/underlying-market", "symbol": "NVDAB"},
            {"bar": "1d", "response": {"code": 500, "data": None}},
            {"endpoint": "rwa/underlying-market", "symbol": "GOOGLB"},
            {"bar": "1d", "response": {"code": 0, "data": [[1, 1, 1, 22, 1, 0, 1]]}}]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "synthetic.json"
            p.write_text(json.dumps({"raw": raw, "report": {"run_utc": "1970-01-03T00:00:00Z"}}))
            result = bstock_series(p)
        self.assertEqual(result["NVDAB"], [])
        self.assertEqual(result["GOOGLB"], [(0, 22.0)])
        with self.assertRaises(ValueError):
            stats([(i, 1) for i in range(10)])
        with self.assertRaises(ValueError):
            stats([(i, float("nan")) for i in range(21)])

    def test_mc_midnight_and_terminal_gas_counterexamples(self):
        # No Monte Carlo experiment: only two deterministic source-regression paths.
        import numpy as np
        spec = importlib.util.spec_from_file_location("fixture_mc", "tools/idea018/mc_run.py")
        module = importlib.util.module_from_spec(spec)
        with patch("sys.argv", ["mc_run.py", "0.5", "1"]):
            spec.loader.exec_module(module)
        shock = np.zeros((1, module.HRS, 4))
        midnight = int(np.flatnonzero(module.NEWDAY)[0])
        shock[:, midnight, :] = -.1
        result = module.run(shock, 0, 0, 0, {"ladder": True})
        self.assertTrue(result[4][0])
        flat = module.run(np.zeros_like(shock), 0, 1, 0, {})
        self.assertAlmostEqual(flat[1][0], .04)

    def test_exact_replay_and_policy_failure_fallback_hashes(self):
        s = snapshot(held={"NVDAB": 8000})
        a = replay_snapshots([s])
        b = replay_snapshots([s])
        self.assertEqual(a, b)
        def failed(*args):
            raise ContractError("scripted policy failure")
        fallback = replay_snapshots([s], decide_port=failed).read()
        self.assertTrue(fallback["trace"][0]["plan"]["requirements"])

    def test_seeded_market_stream_independent_of_call_count_and_order(self):
        a = seeded_observations(4, [1, 2], ["NVDAB", "MSFTB"]).read()["observations"]
        b = seeded_observations(4, [2, 1], ["MSFTB", "NVDAB"]).read()["observations"]
        key = lambda o: (o["time"], o["symbol"])
        self.assertEqual(sorted(a, key=key), sorted(b, key=key))

    def test_accounting_replay_matches_direct_settlement_and_duplicate_hashes(self):
        s = with_quotes(snapshot())
        result = plan(s, decide(s, s.policy_state))
        initial = Document.from_dict(reserve_fixture(s, result).context.read()["portfolio"])
        observation = fill_fixture(s, result.read()["intents"][0])
        settled = advance_accounting(initial, observation)
        replay = replay_accounting(initial, [observation, observation]).read()
        self.assertEqual(replay["portfolio"], settled.read())
        self.assertEqual(replay["hashes"], [settled.digest("PortfolioState.v1")] * 2)

    def test_seeded_faults_run_through_production_ports(self):
        s = snapshot(held={"NVDAB": 8000})
        a = replay_seeded(s, seed=7, rounds=3)
        self.assertEqual(a, replay_seeded(s, seed=7, rounds=3))
        self.assertFalse(a.read()["live_execution_parity"])
        self.assertEqual(len(a.read()["trace"]), 3)
        self.assertTrue(any(t["plan"]["requirements"] for t in a.read()["trace"]))

    def test_no_data_fusion_is_inconclusive_and_in_sample_prediction_rejected(self):
        self.assertEqual(fusion_rows(Document.from_dict({"rights_cleared": False})).read()["status"], "INCONCLUSIVE")
        pred = {"origin": "IN_SAMPLE", "fold_id": "fake", "training_label_end": "2026-01-01T00:00:00Z",
                "predicted_at": "2026-01-02T00:00:00Z", "available_at": "2026-01-02T00:00:00Z",
                "training_last_session": 1}
        request = {"rights_cleared": True, "purge_sessions": 5, "embargo_sessions": 5,
                   "rows": [{"decision_at": "2026-01-03T00:00:00Z", "session_index": 30,
                             "evidence_prediction": pred, "price_prediction": pred}]}
        with self.assertRaises(ContractError):
            fusion_rows(Document.from_dict(request))
        pred["origin"] = "CHRONOLOGICAL_OOF"
        self.assertEqual(fusion_rows(Document.from_dict(request)).read()["status"], "NOT_RUN")
        pred["training_label_end"] = "2026-01-04T00:00:00Z"
        with self.assertRaises(ContractError):
            fusion_rows(Document.from_dict(request))

    def registration(self):
        return {"schema": "EconomicRegistration.v1", "experiment_id": "SYNTHETIC_UNIT_CHECK_NOT_EXP",
                "origin": "SYNTHETIC_VERIFICATION", "hypothesis": "fixture incremental outcome",
                "population": "synthetic portfolio windows", "dataset_hash": "a" * 64,
                "rights_basis": "generated synthetic values", "rights_cleared": True,
                "cost_model": "fixture observed accounting", "detection_delay": 1,
                "purge_sessions": 5, "embargo_sessions": 5, "fixed_parameters": {"fake": True},
                "paired_metric": "after-service-cost portfolio return",
                "confidence_method": "PAIRED_CALENDAR_CLUSTER_BOOTSTRAP", "confidence_bps": 9500,
                "bootstrap_draws": 100, "minimum_clusters": 2, "seed": 7,
                "kill_rule": "negative bound", "inconclusive_rule": "too few paired clusters",
                "default": "frozen baseline", "registered_commit": "0" * 40,
                "variants": ["baseline", "evidence"],
                "windows": [{"cluster_id": "one", "start": "2026-01-01T00:00:00Z",
                             "label_end": "2026-01-07T00:00:00Z"},
                            {"cluster_id": "two", "start": "2026-01-20T00:00:00Z",
                             "label_end": "2026-01-27T00:00:00Z"}]}

    def outcomes(self):
        return [Document.from_dict({"schema": "PortfolioOutcome.v1", "variant": v,
                "cluster_id": cluster, "dataset_hash": "a" * 64, "opening_equity_units": 200000000,
                "wallet_net_units": 100000 if v == "baseline" else 50000,
                "service_units": 10000, "fees_units": 10000, "gas_units": 10000,
                "turnover_units": 40000000, "rejected_allocations": 1, "missed_upside_units": 5000,
                "maximum_drawdown_bps": 100}) for cluster in ("one", "two") for v in ("baseline", "evidence")]

    def test_paired_costs_negative_edge_and_missing_allocations(self):
        registration = Document.from_dict(self.registration())
        report = evaluate(registration, self.outcomes()).read()
        self.assertEqual(report["status"], "NOT_SUPPORTED")
        self.assertEqual(report["paired_clusters"], 2)
        self.assertFalse(report["promotion_authorized"])
        self.assertEqual(report["summary"]["evidence"]["rejected_allocations"], 2)
        self.assertEqual(evaluate(registration, self.outcomes()[:-1]).read()["status"], "INCONCLUSIVE")

    def test_incomplete_registration_and_overlapping_windows_not_run(self):
        self.assertEqual(evaluate(Document.from_dict({}), []).read()["status"], "NOT_RUN")
        d = self.registration()
        d["windows"][1]["start"] = "2026-01-03T00:00:00Z"
        self.assertEqual(evaluate(Document.from_dict(d), []).read()["status"], "NOT_RUN")
