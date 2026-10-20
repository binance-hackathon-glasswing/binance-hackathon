"""LD06 I4: PostgreSQL round/audit ownership, gas-only maintenance, replay/idempotence."""
import unittest

from larp.contracts import ContractError
from tests.integration import test_settlement as s
from tests.execution.test_allowance_recovery import step
from larp.execution import USDT


class CleanupRound(unittest.TestCase):
    def setUp(self):
        self.case = s.Settlement('test_b5_2_approval_releases_its_gas_only')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.c, self.i = self.case.buy_round('r1')
        self.meta = dict(step=step(USDT).lower(), maintenance='ALLOWANCE_REVOKE',
                         token_contract=USDT, spender='0x'+'12'*20, approved_amount='0')

    def observation(self, identity, kind, **values):
        return s.observation(self.i, 'r1', identity, kind, **{**self.meta, **values})

    def test_cleanup_receipt_gas_and_abort_close_without_swap_hash_or_asset_changes(self):
        case, c, i = self.case, self.c, self.i
        before = case.store.load(s.RUN).read()
        held = {r['asset']:r['units'] for r in case.rows(i['intent_id'])}
        case.observe(c, self.observation('cleanup-send', 'BROADCAST_ATTEMPTED'))
        self.assertNotIn('tx_hash', case.planned('r1')['orders'][0])
        fact = self.observation('cleanup-final', 'APPROVAL')
        case.observe(c, fact)
        version = case.store.load(s.RUN).read()['version']
        case.observe(c, fact)
        self.assertEqual(case.store.load(s.RUN).read()['version'], version)
        now = {r['asset']:r['units'] for r in case.rows(i['intent_id'])}
        self.assertEqual(now, dict(held, BNB=held['BNB']-8000))
        after = case.store.load(s.RUN).read()['projection']['balances']
        self.assertEqual(after, dict(before['projection']['balances'], BNB=before['projection']['balances']['BNB']-8000))
        self.assertEqual(case.planned('r1')['swap_mappings'], [])
        case.observe(c, s.observation(i, 'r1', 'abort', 'NOT_SUBMITTED'))
        self.assertEqual(case.rows(i['intent_id']), [])
        c.close('r1', case.w.clock(), 'COMPLETE')
        self.assertFalse(any(o.get('tx_hash') == s.TX for o in case.closed_orders('r1')))
        with case.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM swap_owners WHERE run_id=%s', (s.RUN,)).fetchone()[0], 0)
        # Recompute policy/planning, every maintenance observation and the final audit log
        # into an empty disposable target; compare the exact journal head, not only balances.
        from larp.runtime.replay import replay
        from larp.integration.settlement import ExecutionBridge, settle
        from larp.integration.runtime import initial_projection
        from larp.storage.postgres import doc
        from tests.integration.test_evidence_pipeline import pipeline_ledger
        journal, expected = case.store.journal(s.RUN), case.store.verify(s.RUN)
        with case.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        replay(journal, doc(initial_projection(pipeline_ledger())), case.store, run_id=s.RUN,
               wallet_id='fake-wallet', chain_id=56, version_id='integration-fixture', profile_hash=case.h,
               address='0x'+'1'*40, policy=c.policy, planner=c.planner, execution=ExecutionBridge(),
               reducer=settle, context_builder=c.context_builder, initial_policy_state=c.initial_policy_state)
        self.assertEqual(case.store.verify(s.RUN), expected)

    def test_reverted_cleanup_is_not_a_swap_revert_and_releases_parent_reservations(self):
        case, c, i = self.case, self.c, self.i
        case.observe(c, self.observation('cleanup-send', 'BROADCAST_ATTEMPTED'))
        case.observe(c, self.observation('cleanup-revert', 'REVERT'))
        self.assertEqual(case.rows(i['intent_id']), [])
        self.assertEqual(case.planned('r1')['swap_mappings'], [])
        self.assertNotIn('tx_hash', case.planned('r1')['orders'][0])

    def test_unrecorded_cleanup_hash_cannot_charge_gas(self):
        with self.assertRaises(ContractError):
            self.case.observe(self.c, self.observation('fake-final', 'APPROVAL'))
