"""Repository-side acceptance day (IDEA-042 T1; DR-20 partial).

One synthetic day through every real component on this branch: evidence assessor with fake EDGAR, strategy and the
independent planner, the coordinator with the version event, scripted I4 execution facts (Isaac's execution service
replaces them at integration), settlement and close, round-log delivery with ACK proof, the guard, hourly anchors and
replay with recorded ports.
"""

from pathlib import Path

from larp.audit.delivery import DeliveryWorker
from larp.contracts import Document
from larp.integration.replay import replay_live
from larp.integration.runtime import RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection
from larp.integration.settlement import ExecutionBridge, settle
from larp.runtime.fixtures import FakeReceiver
from larp.runtime.maintenance import HOUR_MS, Maintenance, verify_anchors
from larp.runtime.register import load_register
from larp.runtime.supervision import Guard
from larp.storage.archive import S3Archive
from larp.storage.postgres import doc
from tests.integration import test_evidence_pipeline as pipeline
from tests.integration.test_settlement import observation
from tests.storage.test_archive import FakeS3

RUN = pipeline.RUN
BUILD = 'integration-fixture'


class AcceptanceDay(pipeline.PipelineHarness):
    def test_t1_one_day_through_every_component(self):
        c = self.coordinator('MANDATORY_REDUCTION')
        c.execution, c.require_version = ExecutionBridge(), True
        root = Path(__file__).resolve().parents[2]
        manifest = Document.from_dict(dict(schema='ReleaseManifest.v1', build_id=BUILD, repository='synthetic',
                                           files={}, services=['synthetic'], release_register=load_register(root)))
        c.register_version(manifest, self.w.clock())

        # 1. A clean filing: assessed, held.
        self.round(c, 'r1', 'EXSEMI_Q2_8K')
        # 2. An Item 4.02 filing: mandatory reduction planned, its command taken by the execution side, settled, closed.
        self.round(c, 'r2', 'EXSEMI_402_8K')
        record = self.store.load(RUN).read()['projection']['round_records']['r2']
        intent = record['plan']['intents'][0]
        command = self.store.command(RUN, intent['intent_id'], self.epoch, self.w.clock())
        self.assertEqual(command.read()['payload']['side'], 'SELL')
        for o in (observation(intent, 'r2', 'r2:b', 'BROADCAST_ATTEMPTED'),
                  observation(intent, 'r2', 'r2:f', 'FILL', symbol='NVDAB', side='SELL',
                              token_units=intent['token_units'], cash_units=intent['min_receive_units'], fee_units=0)):
            c.observe(o['event_id'], Document.from_dict(o), settle)
        c.close('r2', self.w.clock(), 'COMPLETE')
        self.assertEqual(self.store.load(RUN).read()['reservations'], [])
        # 3. Every round's log is delivered with a stored acknowledgement for each chunk.
        uploader = DeliveryWorker(self.store, FakeReceiver(), retry_ms=1)
        while uploader.once(RUN, self.epoch, self.w.clock()):
            pass
        status = uploader.status(RUN)
        self.assertEqual(len(status['delivered']), 2)
        self.assertEqual((status['failed'], status['pending_chunks']), ([], 0))
        # 4. Nothing for the guard to do; the hourly anchor verifies against the journal.
        self.assertEqual(Guard(self.store, RUN, max_failures=3, clear_after=2).evaluate(self.w.clock()), [])
        Maintenance(self.store, S3Archive(FakeS3(), bucket='fixture', account_id='123456789012', kms_key='k',
                                          prefix='archive/dev', retention_days=90),
                    backup_interval_ms=24 * HOUR_MS).prepare(RUN, self.w.clock())
        with self.store.transaction() as db:
            anchors = [Document(bytes(r[0])).read() for r in db.execute(
                "SELECT payload FROM archive_outbox WHERE run_id=%s AND kind='anchor'", (RUN,))]
        verify_anchors(self.store, RUN, anchors)
        # 5. The day replays from the journal alone, live ports switched off.
        expected, journal = self.store.verify(RUN), self.store.journal(RUN)
        kinds = [d.read()['event']['kind'] for d in journal]
        self.assertEqual(kinds[0], 'VERSION_REGISTERED')
        builder = c.context_builder

        def gone(*args):
            raise AssertionError('live port called during replay')
        builder.market = builder.calendar = builder.health = builder.series = gone
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        head = replay_live(journal, doc(initial_projection(pipeline.pipeline_ledger())), self.store, builder=builder,
                           run_id=RUN, wallet_id='fake-wallet', chain_id=56, version_id=BUILD, profile_hash=self.h,
                           address='0x' + '1' * 40, policy=StrategyPolicy(),
                           planner=RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                           execution=ExecutionBridge(), reducer=settle,
                           initial_policy_state=initial_policy_state(RUN, self.profile), require_version=True)
        self.assertEqual(head, expected)
