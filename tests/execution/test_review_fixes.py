"""Keegan B1/B2/B3/S1–S5 regression fixtures; no registered credentials."""
from dataclasses import replace
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from larp.execution import Blocked, DependencyUnavailable, Executor, Outcome
from larp.execution_live.service import ExecutionService
from larp.execution_live.venue import LiveVenue
from larp.marketdata.web3 import Unavailable, credentials
from tests.execution_fixtures import SQLiteFixture, FakeGuards, FakeVenue, FakeSigner, FakeDecoder, intent
from tests.execution.test_live_boundaries import LiveBoundaries


class MappingReviewTests(LiveBoundaries):
    def test_oversized_and_malformed_commands_block(self):
        c = self.command()
        c['payload'].update(pay_units=1000000 * 10**6, cash_units=1000000 * 10**6)
        with self.assertRaises(Blocked):self.mapped(c)
        for key in ('payload','expires_ms','round_id'):
            c = self.command();del c[key]
            with self.subTest(key=key),self.assertRaises(Blocked):self.mapped(c)

    def test_gas_accounting_units_convert_to_native_chain_units(self):
        c = self.command()
        c['payload'].update(kind='GAS_TOP_UP', symbol='BNB', decimals=6, receive_decimals=6,
                            min_receive_units=1000)
        self.assertEqual(self.mapped(c).minimum_output, 1000 * 10**12)


class DependencyReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.store = SQLiteFixture(Path(self.directory.name)/'state.db');self.addCleanup(self.store.close)
        self.guards = FakeGuards(self.store);self.venue = FakeVenue(self.store)
        self.executor = Executor(self.store, self.guards, self.venue, FakeSigner(self.store), FakeDecoder())
        self.i = intent();self.executor.create(self.i, 10)
        self.executor.prepare(self.i.key, 11);self.executor.authorize(self.i.key, 12)
        self.executor.sign(self.i.key, 13);self.sent = self.executor.broadcast(self.i.key, 14)

    def test_absent_and_pending_evidence_are_not_mismatches(self):
        a = self.sent.attempts[-1]
        self.venue.outcomes[a.tx_hash] = Outcome(a.tx_hash, None, None, 'UNKNOWN')
        self.executor.reconcile(self.i.key, 17)
        self.assertNotEqual(self.store.events()[-1]['type'],'OUTCOME_MISMATCH')

    def test_rpc_outage_has_persistent_backoff_without_spending_chain_probe_budget(self):
        def unavailable(_):raise DependencyUnavailable('sanitized fixture failure')
        self.venue.outcome=unavailable
        state=self.executor.reconcile(self.i.key,17)
        self.assertEqual(state.attempts[-1].probes,0)
        self.assertGreater(state.attempts[-1].next_probe,17)
        self.assertEqual(self.store.events()[-1]['type'],'RECOVERY_DEPENDENCY_UNAVAILABLE')

    def test_live_reconciliation_continues_after_fast_budget(self):
        self.venue.periodic_reconciliation=True
        for now in range(17,42,3):self.executor.reconcile(self.i.key,now)
        state=self.store.load(self.i.key)
        self.assertGreater(state.attempts[-1].probes,self.i.max_recovery_probes)
        self.assertGreaterEqual(state.attempts[-1].next_probe-state.last_observed_at,60)
        self.assertEqual(state.status,'ACTIVE')

    def test_venue_response_errors_are_sanitized_blocked_errors(self):
        class Client:
            def request(self,*args):raise Unavailable('rate_limited')
        venue=LiveVenue(Client(),None,decoder=FakeDecoder())
        with self.assertRaises(DependencyUnavailable):venue.quote(self.i,0)
        class BrokenClient:
            def request(self,*args):return {'response':{'data':{'executionMode':'SWAP'}}}
        with self.assertRaises(Blocked):LiveVenue(BrokenClient(),None,decoder=FakeDecoder()).quote(self.i,0)

    def test_environment_file_conflicts_are_rejected(self):
        p=Path(self.directory.name)/'credentials'
        p.write_text('BINANCE_API_KEY=file-key\nBINANCE_SECRET_KEY=fixture-secret\n')
        with self.assertRaises(Unavailable):
            credentials(p,environ={'BINANCE_API_KEY':'process-key'})
