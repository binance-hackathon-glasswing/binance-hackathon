"""Live replay with recorded ports (DR-19; IDEA-042 item 4, criteria P1-P4)."""

import json

from larp.contracts import Document
from larp.integration.replay import RecordedPorts, replay_live
from larp.integration.runtime import RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection
from larp.integration.settlement import ExecutionBridge, settle
from larp.storage.postgres import IntegrityError, doc
from tests.integration import test_evidence_pipeline as pipeline
from tests.integration.test_settlement import TX, observation

RUN = pipeline.RUN


class Gone(Exception):
    pass


def gone(*args):
    raise Gone("the live world has moved on; replay must not call this port")


class LiveReplay(pipeline.PipelineHarness):
    def live(self, authority="MANDATORY_REDUCTION"):
        c = self.coordinator(authority)
        c.execution = ExecutionBridge()
        builder = c.context_builder
        calls = {"n": 0}
        market = builder.market

        def moving_market(now_ms):  # a live port whose answers change from round to round
            calls["n"] += 1
            out = market(now_ms)
            for m in out:
                m["price_units"] += calls["n"] * 1000
            return out
        builder.market = moving_market
        return c

    def kill_ports(self, builder):
        builder.market = builder.calendar = builder.health = builder.series = gone

    def replay(self, journal, builder):
        with self.store.transaction() as db:
            db.execute("TRUNCATE runs CASCADE")
        return replay_live(journal, doc(initial_projection(pipeline.pipeline_ledger())), self.store, builder=builder,
                           run_id=RUN, wallet_id="fake-wallet", chain_id=56, version_id="integration-fixture",
                           profile_hash=self.h, address="0x" + "1" * 40, policy=StrategyPolicy(),
                           planner=RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                           execution=ExecutionBridge(), reducer=settle,
                           initial_policy_state=initial_policy_state(RUN, self.profile))

    def settle_reduction(self, c, round_id):
        record = self.store.load(RUN).read()["projection"]["round_records"][round_id]
        intent = record["plan"]["intents"][0]
        self.assertEqual((intent["side"], intent["mandatory"]), ("SELL", True))
        c.observe(round_id + ":b", Document.from_dict(observation(intent, round_id, round_id + ":b",
                                                                  "BROADCAST_ATTEMPTED")), settle)
        c.observe(round_id + ":f", Document.from_dict(observation(
            intent, round_id, round_id + ":f", "FILL", symbol="NVDAB", side="SELL", token_units=intent["token_units"],
            cash_units=intent["min_receive_units"], fee_units=0)), settle)
        c.close(round_id, self.w.clock(), "COMPLETE")

    def test_p2_mandatory_reduction_round_with_settlement_replays(self):
        c = self.live()
        self.round(c, "r1", "EXSEMI_402_8K")
        self.settle_reduction(c, "r1")
        expected, journal = self.store.verify(RUN), self.store.journal(RUN)
        kinds = [d.read()["event"]["kind"] for d in journal]
        self.assertEqual(kinds, ["ROUND_PLANNED", "OBSERVATION", "OBSERVATION", "ROUND_CLOSED"])
        builder = c.context_builder
        self.kill_ports(builder)
        self.assertEqual(self.replay(journal, builder), expected)
        # Control: the same replay with the live (now dead) ports instead of recorded ones cannot reproduce the run.
        from larp.runtime.replay import replay
        with self.store.transaction() as db:
            db.execute("TRUNCATE runs CASCADE")
        with self.assertRaises(IntegrityError):
            replay(journal, doc(initial_projection(pipeline.pipeline_ledger())), self.store, context_builder=builder,
                   run_id=RUN, wallet_id="fake-wallet", chain_id=56, version_id="integration-fixture",
                   profile_hash=self.h, address="0x" + "1" * 40, policy=StrategyPolicy(),
                   planner=RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                   execution=ExecutionBridge(), reducer=settle,
                   initial_policy_state=initial_policy_state(RUN, self.profile))

    def test_p1_p3_rehearsal_day_replays_from_recorded_ports_only(self):
        c = self.live()
        builder = c.context_builder
        self.round(c, "r1", "EXSEMI_Q2_8K")                # clean filing, hold
        self.round(c, "r2", "EXSEMI_402_8K")               # adverse finding -> mandatory reduction
        self.settle_reduction(c, "r2")
        healthy = builder.market
        builder.market = lambda now_ms: (_ for _ in ()).throw(ValueError("market port down"))
        self.round(c, "r3", "OCCURRED_8K")                 # context failure, evidence still latched
        builder.market = healthy
        self.round(c, "r4", "EXSEMI_Q2_8K")                # holds after the failure (duplicate filing)
        self.round(c, "r5", "OCCURRED_8K")
        records = [d.read()["event"].get("record", {}) for d in self.store.journal(RUN)]
        errors = [e for r in records for e in r.get("errors", [])]
        self.assertIn("CONTEXT_UNAVAILABLE:ValueError", errors)
        self.assertGreaterEqual(sum(1 for r in records if r.get("round_id")), 5)
        expected, journal = self.store.verify(RUN), self.store.journal(RUN)
        self.kill_ports(builder)  # P1: any live port call now raises Gone
        self.assertEqual(self.replay(journal, builder), expected)

    def test_p1_recorded_failure_keeps_its_cause(self):
        record = {"errors": ["CONTEXT_UNAVAILABLE:TimeoutError"], "policy_input": {"context": {}}}
        builder = RecordedPorts(self.coordinator("SHADOW").context_builder).builder_for(record)
        with self.assertRaises(Exception) as caught:
            builder.market(0)
        self.assertEqual(type(caught.exception).__name__, "TimeoutError")

    def test_p4_a_changed_recorded_market_is_detected(self):
        c = self.live()
        self.round(c, "r1", "EXSEMI_402_8K")
        self.settle_reduction(c, "r1")
        expected, journal = self.store.verify(RUN), self.store.journal(RUN)
        batch = journal[0].read()
        batch["event"]["record"]["policy_input"]["context"]["markets"][0]["price_units"] += 1
        tampered = [Document.from_dict(batch)] + journal[1:]
        builder = c.context_builder
        self.kill_ports(builder)
        with self.assertRaises(IntegrityError):
            head = self.replay(tampered, builder)
            self.store.verify(RUN, anchored_head=expected)
            self.fail("tampered journal replayed to " + json.dumps(head))
