"""IDEA-061: one gas top-up round end to end (#30 acceptance 2, top-up audit round slice).

The real planner plans the USDT -> BNB top-up from a gas quote; the runtime adapter and the Coordinator commit it as
its own GAS_TOP_UP round on PostgreSQL; the committed command is mapped by the real I3 consumer (`map_command`) to a
native-BNB intent; the broadcast and the transaction-bound native receipt (`final_observation`, GB-NATIVE) pass the
real I4 reducer (`settle`); the round closes and its one ai-seeds log carries the BNB order with the USDT spent and
the swap hash. Synthetic chain facts only: no provider, signing or broadcast.
"""

import json
import unittest

from larp.contracts import ContractError, Document
from larp.execution import USDT, NATIVE_BNB, Attempt, Blocked, Execution, Payload
from larp.execution_live.service import broadcast_observation, map_command
from larp.execution_live.settlement import TRANSFER, final_observation
from larp.integration.runtime import INCOMING, RuntimePlanner, ledger_from
from larp.integration.settlement import ExecutionBridge, settle
from tests.integration import test_evidence_pipeline as pipeline
from tests.risk.test_live_resource_receipts import resource_plan

RUN = pipeline.RUN
WALLET = "0x" + "1" * 40
ROUTER = "0x" + "2" * 40
TX = "0x" + "ab" * 32
BLOCK = "0x" + "cd" * 32
NONCE = 7
GAS_USED, GAS_PRICE = 50_000, 10**8  # 5e12 wei = 5 BNB units at 6 decimals
STAMP = "2026-10-12T14:00:00+00:00"
LIMITS = dict(per_trade_cap_units=40_200_000, max_gas=300_000, max_gas_price=10**10, gas_budget=10**16)


def _transfer(token, source, destination, amount):
    pad = "0x" + "0" * 24
    return dict(address=token, topics=[TRANSFER, pad + source[2:], pad + destination[2:]],
                data="0x" + format(amount, "064x"))


def _command(symbol="BNB", side="BUY", kind="GAS_TOP_UP"):
    """An I3 command as the Coordinator commits it (synthetic, no database)."""
    bnb = kind == "GAS_TOP_UP"
    p = dict(intent_id="i", decision_id="d", expires_ms=1_000_000, symbol=symbol, side=side, kind=kind,
             amount_kind="EXACT_IN", pay_asset="USDT" if side == "BUY" else symbol, pay_units=241_207,
             min_receive_units=240_000, receive_decimals=6 if bnb or side == "SELL" else 18, cash_units=241_207,
             fee_units=0)
    if bnb:
        p["decimals"] = 6
    return dict(kind="EXECUTION_REQUEST", command_id="i", decision_id="d", expires_ms=1_000_000, round_id="r",
                payload=p)


class NativeSettlementGate(unittest.TestCase):
    """T7/T8: the execution service never starts a top-up whose fill it could not settle."""

    def mapped(self, command, **flag):
        return map_command(command, run_id="run", wallet=WALLET, version_id="v", router=ROUTER,
                           token_decimals={"NVDAB": 18}, limits=LIMITS, now_ms=100, **flag)

    def test_t7_top_up_is_refused_unless_native_settlement_is_enabled(self):
        for flag in ({}, {"native_settlement": False}):
            with self.subTest(flag=flag), self.assertRaisesRegex(Blocked, "native settlement"):
                self.mapped(_command(), **flag)
        economic = self.mapped(_command(), native_settlement=True)
        self.assertEqual((economic.kind, economic.receive_token), ("GAS_TOP_UP", NATIVE_BNB))
        for side in ("BUY", "SELL"):  # stock trades settle from token transfer logs and never need the trace
            with self.subTest(side=side):
                self.assertEqual(self.mapped(_command("NVDAB", side, "BSTOCK_TRADE")).kind, "BSTOCK_TRADE")

    def test_t8_execution_mapping_binds_native_settlement_to_native_trace(self):
        from larp.execution_live.main import execution_mapping
        config = dict(build_id="b", router=ROUTER, max_gas=1, max_gas_price=2, gas_budget=3)
        profile = dict(per_trade_cap_units=40_200_000, slippage_bps=20)
        decimals = {"NVDAB": 18}
        for trace, expected in ((None, False), (False, False), (True, True)):
            with self.subTest(native_trace=trace):
                value = dict(config) if trace is None else dict(config, native_trace=trace)
                mapping = execution_mapping(value, profile, decimals, wallet=WALLET)
                self.assertIs(mapping["native_settlement"], expected)
                self.assertEqual(mapping["limits"], dict(per_trade_cap_units=40_200_000, slippage_bps=20,
                                                         max_gas=1, max_gas_price=2, gas_budget=3))
                self.assertEqual((mapping["wallet"], mapping["version_id"], mapping["router"],
                                  mapping["token_decimals"]), (WALLET, "b", ROUTER, decimals))


class GasTopUpRound(pipeline.PipelineHarness):
    """Planner -> Coordinator (PostgreSQL) -> I3 -> native receipt -> I4 -> closed GAS_TOP_UP audit round."""

    def top_up_round(self, round_id="g1"):
        _, result = resource_plan()  # real planner: BNB below the floor, one valid gas quote
        raw = result.read()
        self.assertEqual([i["kind"] for i in raw["intents"]], ["GAS_TOP_UP"])
        c = self.coordinator("SHADOW")
        c.execution = ExecutionBridge()
        c.planner = RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3,
                                   plan_fn=lambda s, p: Document.from_dict(dict(raw, snapshot_id=s.snapshot_id)))
        self.round(c, round_id, "EXSEMI_Q2_8K")
        record = self.record(round_id)
        self.assertEqual(record.get("round_kind"), "GAS_TOP_UP")
        intent = record["plan"]["intents"][0]
        return c, intent

    def record(self, round_id):
        return self.store.load(RUN).read()["projection"]["round_records"][round_id]

    def rows(self, intent_id):
        return {r["asset"]: r["units"] for r in self.store.load(RUN).read()["reservations"]
                if r["intent_id"] == intent_id}

    def committed_command(self, intent):
        rows = [(cid, payload) for cid, payload in self.commands() if cid == intent["intent_id"]]
        self.assertEqual(len(rows), 1)
        payload = rows[0][1]
        return Document(bytes(payload)).read() if isinstance(payload, (bytes, memoryview)) else payload

    def execution(self, command, *, received_wei, gas_used=GAS_USED):
        """The real I3 mapping of the committed command and a finalized native swap for it (synthetic chain)."""
        economic = map_command(command, run_id=RUN, wallet=WALLET, version_id="integration-fixture", router=ROUTER,
                               token_decimals={}, limits=LIMITS, now_ms=command["expires_ms"] - 1,
                               native_settlement=True)
        payload = Payload(56, WALLET, ROUTER, 0, NONCE, 200_000, GAS_PRICE, "0xdeadbeef")
        attempt = Attempt(economic.intent_id + ":swap", "SWAP", "FINAL_SUCCESS", payload, 1, 1, tx_hash=TX,
                          broadcast_at=1_791_734_400, finalized_at=1_791_734_460)
        state = Execution(economic, attempts=(attempt,), status="COMPLETED")
        gas = gas_used * GAS_PRICE
        before = 10**18
        proof = dict(finality_verified=True, block_hash=BLOCK, block_number=10, finalized_height=12,
                     tx=dict(hash=TX, nonce=hex(NONCE), to=ROUTER, input="0xdeadbeef", value="0x0", chainId="0x38",
                             gas=hex(200_000), gasPrice=hex(GAS_PRICE), **{"from": WALLET}),
                     receipt=dict(transactionHash=TX, blockHash=BLOCK, blockNumber="0xa", gasUsed=hex(gas_used),
                                  effectiveGasPrice=hex(GAS_PRICE), status="0x1", **{"from": WALLET},
                                  logs=[_transfer(USDT, WALLET, ROUTER, economic.amount)]),
                     native_balance=dict(schema="TransactionNativeBalance.v1", method="GETH_PRESTATE_DIFF",
                                         source_id="synthetic-chain", tx_hash=TX, block_hash=BLOCK, wallet=WALLET,
                                         nonce=NONCE, before_wei=before, after_wei=before + received_wei - gas,
                                         trace_sha256="d" * 64))
        return economic, state, attempt, proof

    def observe(self, c, o):
        return c.observe(o["event_id"], Document.from_dict(o), settle)

    def closed_log(self, round_id):
        with self.store.transaction() as db:
            raw = db.execute("SELECT document FROM audit_events WHERE run_id=%s AND round_id=%s",
                             (RUN, round_id)).fetchone()[0]
        event = Document(bytes(raw)).read()
        return event, json.loads(event["log"])["data"]

    def test_t1_planned_top_up_is_its_own_round_with_usdt_bnb_and_incoming_bnb_reserved(self):
        c, intent = self.top_up_round()
        self.assertEqual((intent["symbol"], intent["side"], intent["kind"]), ("BNB", "BUY", "GAS_TOP_UP"))
        self.assertEqual(self.rows(intent["intent_id"]),
                         {"USDT": intent["cash_units"] + intent["fee_units"], "BNB": intent["gas_bnb_units"],
                          INCOMING + "BNB": intent["token_units"]})
        self.assertEqual(intent["amount"], "0.241207")  # the organiser's BUY amount: USDT spent (GAP-46 B11)

    def test_t2_committed_command_maps_to_a_native_bnb_intent(self):
        c, intent = self.top_up_round()
        economic, *_ = self.execution(self.committed_command(intent), received_wei=intent["token_units"] * 10**12)
        self.assertEqual((economic.kind, economic.pay_token, economic.receive_token),
                         ("GAS_TOP_UP", USDT, NATIVE_BNB))
        self.assertEqual(economic.amount, intent["pay_units"] * 10**12)
        self.assertEqual(economic.minimum_output, intent["min_receive_units"] * 10**12)

    def test_t3_native_fill_settles_releases_and_closes_the_gas_top_up_round(self):
        c, intent = self.top_up_round()
        before = self.store.load(RUN).read()["projection"]["balances"]
        received = intent["token_units"] * 10**12  # the quoted output, in wei
        economic, state, attempt, proof = self.execution(self.committed_command(intent), received_wei=received)
        self.observe(c, broadcast_observation(state, attempt, wallet_id="fake-wallet"))
        self.assertEqual(self.record("g1")["orders"][0]["tx_hash"], TX)
        self.assertEqual(self.store.load(RUN).read()["projection"]["balances"], before)  # a broadcast is no fill
        fact = final_observation(state, attempt, proof, wallet_id="fake-wallet", bnb_price_units=1_000_000,
                                 observed_at=STAMP, bnb_decimals=6)
        fact["round_terminal"] = True  # ReceiptFacts sets it when the execution owner finished the round
        self.observe(c, fact)
        self.assertEqual(self.rows(intent["intent_id"]), {})  # USDT, BNB and INCOMING:BNB all released
        value = self.store.load(RUN).read()
        after = value["projection"]["balances"]
        gas_units = GAS_USED * GAS_PRICE // 10**12
        self.assertEqual(after["USDT"], before["USDT"] - intent["pay_units"])
        self.assertEqual(after["BNB"], before["BNB"] - gas_units + intent["token_units"])
        self.assertEqual({k: v for k, v in after.items() if k not in ("USDT", "BNB")},
                         {k: v for k, v in before.items() if k not in ("USDT", "BNB")})  # no stock moved
        portfolio = value["projection"]["portfolio"]
        self.assertEqual(portfolio["accounting"]["gas_top_up_cash_units"], intent["pay_units"])
        self.assertEqual(portfolio["accounting"]["turnover_units"], 0)
        ledger_from(value["projection"], value["reservations"])  # the next round accepts the settled state
        c.close("g1", self.w.clock(), "COMPLETE")
        self.assertEqual(list(self.store.open_rounds(RUN)), [])
        event, log = self.closed_log("g1")
        self.assertEqual(event.get("round_kind"), "GAS_TOP_UP")
        self.assertEqual(log["orders"], [dict(symbol="BNB", side="BUY", amount=intent["amount"], tx_hash=TX)])
        self.assertTrue(log["cot"].startswith("Gas top-up round") if type(log["cot"]) is str
                        else log["cot"][0].startswith("Gas top-up round"))
        with self.store.transaction() as db:  # IDEA-042 L8: the swap belongs to this round's log
            owner = db.execute("SELECT round_id,decision_id FROM swap_owners WHERE run_id=%s AND tx_hash=%s",
                               (RUN, TX)).fetchone()
        self.assertEqual(owner, ("g1", intent["decision_id"]))

    def test_t4_replayed_receipt_is_a_no_op(self):
        c, intent = self.top_up_round()
        economic, state, attempt, proof = self.execution(self.committed_command(intent),
                                                         received_wei=intent["token_units"] * 10**12)
        self.observe(c, broadcast_observation(state, attempt, wallet_id="fake-wallet"))
        fact = final_observation(state, attempt, proof, wallet_id="fake-wallet", bnb_price_units=1_000_000,
                                 observed_at=STAMP, bnb_decimals=6)
        fact["round_terminal"] = True
        first = self.observe(c, fact)
        version = self.store.load(RUN).read()["version"]
        self.assertEqual(self.observe(c, fact).read(), first.read())
        self.assertEqual(self.store.load(RUN).read()["version"], version)

    def test_t5_short_output_or_unbound_trace_never_reaches_the_round(self):
        c, intent = self.top_up_round()
        short = (intent["min_receive_units"] - 1) * 10**12
        economic, state, attempt, proof = self.execution(self.committed_command(intent), received_wei=short)
        with self.assertRaises(Blocked):
            final_observation(state, attempt, proof, wallet_id="fake-wallet", bnb_price_units=1_000_000,
                              observed_at=STAMP, bnb_decimals=6)
        economic, state, attempt, proof = self.execution(self.committed_command(intent),
                                                         received_wei=intent["token_units"] * 10**12)
        proof["native_balance"]["wallet"] = ROUTER  # another account's balance change
        with self.assertRaises(Blocked):
            final_observation(state, attempt, proof, wallet_id="fake-wallet", bnb_price_units=1_000_000,
                              observed_at=STAMP, bnb_decimals=6)

    def test_t6_a_bnb_fill_outside_the_planned_top_up_is_refused(self):
        c, intent = self.top_up_round()
        economic, state, attempt, proof = self.execution(self.committed_command(intent),
                                                         received_wei=intent["token_units"] * 10**12)
        self.observe(c, broadcast_observation(state, attempt, wallet_id="fake-wallet"))
        fact = final_observation(state, attempt, proof, wallet_id="fake-wallet", bnb_price_units=1_000_000,
                                 observed_at=STAMP, bnb_decimals=6)
        version = self.store.load(RUN).read()["version"]
        for n, bad in enumerate((dict(fact, intent_id="unplanned"), dict(fact, symbol="NVDAB"),
                                 dict(fact, cash_units=fact["cash_units"] + 1))):
            with self.subTest(case=n), self.assertRaises(ContractError):
                self.observe(c, dict(bad, event_id=bad["event_id"] + ":x"))
        self.assertEqual(self.store.load(RUN).read()["version"], version)
