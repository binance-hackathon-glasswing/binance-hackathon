"""Settlement of execution observations (interface I4) and the published I3 contract (IDEA-042 item 1, B3-B5)."""

from datetime import datetime, timezone
import unittest

from larp.contracts import ContractError, Document
from larp.integration.runtime import INCOMING, RuntimePlanner, ledger_from
from larp.integration.settlement import ExecutionBridge
from larp.ports import validate_execution_observation, validate_execution_request
from larp.research.fixtures import snapshot, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from tests.integration import test_evidence_pipeline as pipeline

RUN, WALLET = pipeline.RUN, "fake-wallet"
TX = "0x" + "ab" * 32
BLOCK = "0x" + "cd" * 32
AT = "2026-10-12T14:00:00+00:00"


def command(intent, round_id="r"):
    """The command exactly as Coordinator.start commits it."""
    return dict(command_id=intent["intent_id"], kind="EXECUTION_REQUEST", payload=intent, round_id=round_id,
                decision_id=intent["decision_id"], expires_ms=intent["expires_ms"])


def raw_buy_plan():
    """Keith's planner output for a BUY (research fixture), before the runtime adapter."""
    s = with_quotes(snapshot())
    return plan(s, decide(s, s.policy_state)).read()


def buy_plan():
    s = with_quotes(snapshot())
    return RuntimePlanner(job_validity_ms=60_000, job_max_attempts=3).plan(s, decide(s, s.policy_state)).read()


def observation(intent, round_id, event_id, kind, **fields):
    o = dict(schema="ExecutionObservation.v1", run_id=RUN, wallet_id=WALLET, round_id=round_id,
             intent_id=intent["intent_id"], event_id=event_id, kind=kind, observed_at=AT)
    if kind == "BROADCAST_ATTEMPTED":
        o.update(step="swap", tx_hash=TX)
    elif kind != "NOT_SUBMITTED":
        o.update(settlement="FINAL", origin="SCRIPTED_FAKE", tx_hash=TX, block_hash=BLOCK, canonical=True,
                 gas_bnb_units=8000, gas_value_units=5000, intent_terminal=kind != "APPROVAL",
                 round_terminal=kind != "APPROVAL")
    else:
        o.update(settlement="FINAL", origin="EXECUTION_RECONCILER", intent_terminal=True, round_terminal=True)
    o.update(fields)
    return o


class Contracts(unittest.TestCase):
    def test_i3_real_planner_output_is_a_valid_execution_request(self):
        intents = buy_plan()["intents"]
        self.assertTrue(intents)
        for intent in intents:
            validate_execution_request(command(intent))

    def test_i3_refuses_wrong_amount_and_non_gas_bnb(self):
        intent = buy_plan()["intents"][0]
        with self.assertRaises(ContractError):  # token quantity is not the BUY amount (A10)
            validate_execution_request(command(dict(intent, amount=str(intent["token_units"]))))
        with self.assertRaises(ContractError):  # BNB only as a gas top-up (I7)
            validate_execution_request(command(dict(intent, symbol="BNB")))
        validate_execution_request(command(dict(intent, symbol="BNB", kind="GAS_TOP_UP")))
        for old in (dict(kind="GAS_TOPUP"), dict(purpose="GAS_TOPUP"), dict(kind="GAS_TOP_UP", purpose="TRADE")):
            with self.subTest(old), self.assertRaises(ContractError):  # the pre-agreement spelling (IDEA-042 §4 X3)
                validate_execution_request(command(dict(intent, symbol="BNB", **old)))

    def test_i4_boundaries(self):
        intent = {"intent_id": "i"}
        attempt = observation(intent, "r", "e1", "BROADCAST_ATTEMPTED")
        validate_execution_observation(attempt)
        with self.assertRaises(ContractError):  # a broadcast attempt never carries accounting facts
            validate_execution_observation(dict(attempt, gas_bnb_units=1))
        fill = observation(intent, "r", "e2", "FILL", symbol="NVDAB", side="SELL", token_units=1, cash_units=1,
                           fee_units=0)
        validate_execution_observation(fill)
        for bad in (dict(fill, settlement="PENDING"), dict(fill, canonical=False), dict(fill, intent_terminal=False),
                    dict(observation(intent, "r", "e3", "APPROVAL"), round_terminal=True)):
            with self.assertRaises(ContractError):
                validate_execution_observation(bad)


class Settlement(pipeline.PipelineHarness):
    def bridge(self, coordinator):
        coordinator.execution = ExecutionBridge()
        return coordinator

    def rows(self, intent_id):
        return [r for r in self.store.load(RUN).read()["reservations"] if r["intent_id"] == intent_id]

    def observe(self, c, o):
        from larp.integration.settlement import settle
        return c.observe(o["event_id"], Document.from_dict(o), settle)

    def planned(self, round_id):
        return self.store.load(RUN).read()["projection"]["round_records"][round_id]

    def closed_orders(self, round_id):
        import json
        with self.store.transaction() as db:
            raw = db.execute("SELECT document FROM audit_events WHERE run_id=%s AND round_id=%s",
                             (RUN, round_id)).fetchone()[0]
        return json.loads(Document(bytes(raw)).read()["log"])["data"]["orders"]

    def test_b5_1_sell_broadcast_then_fill(self):
        c = self.bridge(self.coordinator("MANDATORY_REDUCTION"))
        self.round(c, "r1", "EXSEMI_402_8K")
        intent = self.planned("r1")["plan"]["intents"][0]
        before = self.store.load(RUN).read()
        self.observe(c, observation(intent, "r1", "o1", "BROADCAST_ATTEMPTED"))
        after = self.store.load(RUN).read()
        for key in ("balances", "portfolio"):
            self.assertEqual(after["projection"][key], before["projection"][key])
        self.assertEqual(after["reservations"], before["reservations"])
        self.assertEqual(self.planned("r1")["orders"][0]["tx_hash"], TX)
        self.observe(c, observation(intent, "r1", "o2", "FILL", symbol="NVDAB", side="SELL",
                                    token_units=intent["token_units"], cash_units=intent["min_receive_units"],
                                    fee_units=0))
        value = self.store.load(RUN).read()
        self.assertEqual(self.rows(intent["intent_id"]), [])
        balances = value["projection"]["balances"]
        self.assertEqual(balances["NVDAB"], before["projection"]["balances"]["NVDAB"] - intent["token_units"])
        self.assertEqual(balances["USDT"], before["projection"]["balances"]["USDT"] + intent["min_receive_units"])
        self.assertEqual(balances["BNB"], before["projection"]["balances"]["BNB"] - 8000)
        ledger_from(value["projection"], value["reservations"])  # the next round accepts the settled state
        c.close("r1", self.w.clock(), "COMPLETE")
        self.assertEqual(self.closed_orders("r1")[0]["tx_hash"], TX)
        with self.store.transaction() as db:  # IDEA-042 L8: the settled swap belongs to this round's log
            owner = db.execute("SELECT round_id,decision_id FROM swap_owners WHERE run_id=%s AND tx_hash=%s",
                               (RUN, TX)).fetchone()
        self.assertEqual(owner, ("r1", intent["decision_id"]))

    def buy_round(self, round_id):
        raw = raw_buy_plan()
        c = self.bridge(self.coordinator("SHADOW"))
        inner = RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3,
                               plan_fn=lambda s, p: Document.from_dict(dict(raw, snapshot_id=s.snapshot_id)))
        c.planner = inner
        self.round(c, round_id, "EXSEMI_Q2_8K")
        intent = self.planned(round_id)["plan"]["intents"][0]
        self.assertEqual(intent["side"], "BUY")
        assets = sorted(r["asset"] for r in self.rows(intent["intent_id"]))
        self.assertEqual(assets, ["BNB", INCOMING + intent["symbol"], "USDT"])
        return c, intent

    def test_b5_2_buy_fill_releases_usdt_bnb_and_incoming(self):
        c, intent = self.buy_round("r1")
        before = self.store.load(RUN).read()["projection"]["balances"]
        self.observe(c, observation(intent, "r1", "o1", "BROADCAST_ATTEMPTED"))
        self.observe(c, observation(intent, "r1", "o2", "FILL", symbol=intent["symbol"], side="BUY",
                                    token_units=intent["min_receive_units"], cash_units=intent["pay_units"],
                                    fee_units=0))
        self.assertEqual(self.rows(intent["intent_id"]), [])
        after = self.store.load(RUN).read()["projection"]["balances"]
        self.assertEqual(after["USDT"], before["USDT"] - intent["pay_units"])
        self.assertEqual(after[intent["symbol"]], before[intent["symbol"]] + intent["min_receive_units"])
        c.close("r1", self.w.clock(), "COMPLETE")
        self.assertEqual(self.closed_orders("r1")[0]["amount"], intent["amount"])

    def test_b5_2_buy_revert_releases_everything_and_charges_only_gas(self):
        c, intent = self.buy_round("r1")
        before = self.store.load(RUN).read()["projection"]["balances"]
        self.observe(c, observation(intent, "r1", "o1", "BROADCAST_ATTEMPTED"))
        self.observe(c, observation(intent, "r1", "o2", "REVERT"))
        self.assertEqual(self.rows(intent["intent_id"]), [])
        after = self.store.load(RUN).read()["projection"]["balances"]
        self.assertEqual(after, dict(before, BNB=before["BNB"] - 8000))
        c.close("r1", self.w.clock(), "COMPLETE")
        self.assertEqual(self.closed_orders("r1")[0]["tx_hash"], TX)  # a reverted swap is still logged (F-100)

    def test_b5_2_approval_releases_its_gas_only(self):
        c, intent = self.buy_round("r1")
        held = {r["asset"]: r["units"] for r in self.rows(intent["intent_id"])}
        self.observe(c, observation(intent, "r1", "o1", "APPROVAL"))
        now = {r["asset"]: r["units"] for r in self.rows(intent["intent_id"])}
        self.assertEqual(now, dict(held, BNB=held["BNB"] - 8000))
        self.assertTrue(self.planned("r1")["execution_pending"])

    def test_b5_3_repeated_observation_is_a_no_op(self):
        c, intent = self.buy_round("r1")
        o = observation(intent, "r1", "o1", "BROADCAST_ATTEMPTED")
        first = self.observe(c, o)
        version = self.store.load(RUN).read()["version"]
        self.assertEqual(self.observe(c, o).read(), first.read())
        self.assertEqual(self.store.load(RUN).read()["version"], version)
        with self.assertRaises(ContractError):
            self.observe(c, dict(o, tx_hash="0x" + "ef" * 32))

    def test_b5_4_refusals_change_nothing(self):
        c, intent = self.buy_round("r1")
        self.observe(c, observation(intent, "r1", "o1", "BROADCAST_ATTEMPTED"))
        value = self.store.load(RUN).read()
        fill = dict(symbol=intent["symbol"], side="BUY", token_units=intent["min_receive_units"],
                    cash_units=intent["pay_units"], fee_units=0)
        for event_id, bad in (("x1", observation({"intent_id": "unplanned"}, "r1", "x1", "FILL", **fill)),
                              ("x2", observation(intent, "r1", "x2", "FILL", settlement="PROVISIONAL", **fill)),
                              ("x3", observation(intent, "r1", "x3", "FILL", wallet_id="other-wallet", **fill)),
                              ("x4", observation(intent, "r1", "x4", "FILL", **dict(fill, tx_hash="0x" + "11" * 32)))):
            with self.subTest(event_id), self.assertRaises(ContractError):
                self.observe(c, bad)
        self.assertEqual(self.store.load(RUN).read(), value)

    def test_attestation_is_checked_against_final_facts(self):
        c, intent = self.buy_round("r1")
        self.observe(c, observation(intent, "r1", "o1", "BROADCAST_ATTEMPTED"))
        record = self.planned("r1")
        self.assertEqual(len(record["plan"]["intents"]), 1)
        # An APPROVAL is never terminal, so it can never seal the round (validator refuses round_terminal on it).
        with self.assertRaises(ContractError):
            self.observe(c, observation(intent, "r1", "o2", "APPROVAL", round_terminal=True))
        self.assertTrue(self.planned("r1")["execution_pending"])

    def test_not_submitted_releases_without_accounting(self):
        c, intent = self.buy_round("r1")
        before = self.store.load(RUN).read()["projection"]["balances"]
        self.observe(c, observation(intent, "r1", "o1", "NOT_SUBMITTED", reason="QUOTE_EXPIRED"))
        self.assertEqual(self.rows(intent["intent_id"]), [])
        self.assertEqual(self.store.load(RUN).read()["projection"]["balances"], before)
        self.assertFalse(self.planned("r1")["execution_pending"])
        c.close("r1", self.w.clock(), "COMPLETE")
        # Logged without a tx hash, with the reason in output.aborted (IDEA-042 L2, kit convention).
        import json
        with self.store.transaction() as db:
            raw = db.execute("SELECT document FROM audit_events WHERE run_id=%s AND round_id=%s",
                             (RUN, "r1")).fetchone()[0]
        data = json.loads(Document(bytes(raw)).read()["log"])["data"]
        self.assertEqual(data["orders"], [{"symbol": intent["symbol"], "side": "BUY", "amount": intent["amount"]}])
        self.assertEqual(data["output"]["aborted"][0]["reason"], "QUOTE_EXPIRED")


if __name__ == "__main__":
    unittest.main()
