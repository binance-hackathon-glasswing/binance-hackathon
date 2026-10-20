"""LD06: synthetic transports/bytes only; original quote shapes, no network/wallet operation."""
from copy import deepcopy
from dataclasses import replace
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from larp.contracts import ContractError, Document
from larp.execution import (Attempt, Blocked, Conflict, Execution, Executor, Payload, REVOKE_TOKENS,
                            USDT, NATIVE_BNB, validate_payload, validate_sequence, possible_swap_hashes)
from larp.execution_live.service import ExecutionService, broadcast_observation
from larp.execution_live.venue import LiveVenue
from larp.ports import validate_execution_observation
from larp.signer.policy import SigningPolicy
from tests import execution_fixtures as f
from tests.execution import test_untrusted_router as u
from tests.execution import test_settlement as receipt_fixtures
from tests.signer import test_service as signer_fixtures


def step(token):
    return 'REVOKE:' + token


def zero_payload(i, token, nonce=0, amount=0):
    return Payload(56, i.wallet, token, 0, nonce, 100000, 1,
                   '0x095ea7b3' + '0' * 24 + i.router[2:] + format(amount, '064x'))


class Guards(f.FakeGuards):
    mode = 'live'  # actual Executor capability branch; every transport is synthetic


class Signer(f.FakeSigner):
    mode = 'live'  # deliberately unbroadcastable fixture bytes


class Venue(f.FakeVenue):
    mode = 'live'

    def quote(self, i, nonce):
        self.quote_calls += 1
        _, params, tx = next(row for row in u.quotes()
            if row[1]['fromTokenAddress'].lower() == i.pay_token
            and row[1]['toTokenAddress'].lower() == i.receive_token)
        data = u.u._set_word(tx['data'], u.u.INNER_DEADLINE, i.valid_until, inner=True)
        return replace(u.swap(params, tx), sender=i.wallet, nonce=nonce, data=data)

    def revoke(self, i, token, nonce):
        return zero_payload(i, token, nonce)


class Harness:
    def __init__(self, directory):
        self.path = Path(directory) / 'state.sqlite'
        self.store = f.SQLiteFixture(self.path)
        self.guards, self.venue = Guards(self.store), Venue(self.store)
        self.decoder = u.u.UntrustedRouterDecoder(u.policy())
        self.rpc = u.FakeRpc(self.decoder, f.WALLET, USDT, 0)
        self.decoder.bind(self.rpc)
        self.now = 10
        self.restart()

    def restart(self, enabled=True):
        self.executor = Executor(self.store, self.guards, self.venue, Signer(self.store), self.decoder,
                                 allowance_recovery=enabled)

    def close(self):
        self.store.close()

    def intent(self, name='first', *, sell=False, valid_until=1000, gas_budget=10**7):
        _, params, tx = next(row for row in u.quotes()
            if (row[1]['fromTokenAddress'].lower() != USDT) == sell)
        return replace(u.swap_intent(params, tx, self.decoder), wallet=f.WALLET,
                       intent_id=name, reservation_id=name, valid_until=valid_until, gas_budget=gas_budget)

    def finish_step(self, i, *, status='SUCCESS', clear=True):
        e = self.executor
        self.now += 1
        state = e.prepare(i.key, self.now)
        if not state.attempts or state.attempts[-1].state != 'PREPARED':
            raise AssertionError('prepare refused: ' + str(state.blocked_reason))
        for method in (e.authorize, e.sign, e.broadcast):
            self.now += 1
            state = method(i.key, self.now)
        attempt = state.attempts[-1]
        self.venue.outcomes[attempt.tx_hash] = f.finalized(attempt, status)
        self.now += 3
        state = e.reconcile(i.key, self.now)
        self.guards.nonce += 1
        if status == 'SUCCESS':
            if attempt.step in REVOKE_TOKENS and clear:
                self.rpc.allowances[REVOKE_TOKENS[attempt.step]] = 0
            elif attempt.step == 'APPROVE':
                self.rpc.allowances[i.pay_token] = i.amount
            elif attempt.step == 'SWAP':
                self.rpc.allowances[i.pay_token] = 0
        return state


class AllowanceRecovery(unittest.TestCase):
    def harness(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        h = Harness(tmp.name)
        self.addCleanup(h.close)
        return h

    def test_abandoned_reverted_and_expired_approval_allow_fresh_cross_token_exit(self):
        for cause in ('no_swap', 'revert', 'expired'):
            with self.subTest(cause=cause):
                h = self.harness()
                i = h.intent()
                h.executor.create(i, h.now)
                self.assertEqual(h.finish_step(i).attempts[-1].step, 'APPROVE')
                if cause == 'revert':
                    self.assertEqual(h.finish_step(i, status='REVERT').status, 'FAILED')
                else:
                    h.now = i.valid_until if cause == 'expired' else h.now + 1
                    h.executor.abort_unsigned(i.key, h.now)
                self.assertEqual(h.rpc.allowances[USDT], i.amount)
                exit_i = h.intent('fresh-final-exit', sell=True, valid_until=2000)
                self.assertNotEqual(exit_i.pay_token, USDT)
                h.restart(enabled=False)
                h.executor.create(exit_i, h.now)
                blocked = h.executor.prepare(exit_i.key, h.now + 1)
                self.assertFalse(blocked.attempts)
                self.assertIn('allowance', blocked.blocked_reason)  # original liveness failure
                h.now += 1
                h.restart()
                state = h.finish_step(exit_i)
                self.assertEqual(state.attempts[-1].step, step(USDT))
                # Reopen durable state between cleanup and trade approval.
                h.store.close()
                h.store = f.SQLiteFixture(h.path)
                h.guards.store = h.venue.store = h.store
                h.restart()
                self.assertEqual(h.finish_step(exit_i).attempts[-1].step, 'APPROVE')
                state = h.finish_step(exit_i)
                self.assertEqual(state.status, 'COMPLETED')
                self.assertEqual([a.step for a in state.attempts], [step(USDT), 'APPROVE', 'SWAP'])
                self.assertEqual(possible_swap_hashes(state), (state.attempts[-1].tx_hash,))
                self.assertEqual(len({a.attempt_id for a in state.attempts}), 3)
                self.assertEqual(h.store.db.execute('SELECT count(*) FROM signatures').fetchone()[0],
                                 5 if cause == 'revert' else 4)

    def test_all_six_dirty_tokens_are_cleared_once_then_normal_trade(self):
        h = self.harness()
        i = h.intent()
        h.rpc.allowances = {token: 10 for token in u.u.TOKENS}
        h.executor.create(i, h.now)
        for token in sorted(u.u.TOKENS):
            state = h.finish_step(i)
            self.assertEqual(state.attempts[-1].step, step(token))
        h.finish_step(i)
        state = h.finish_step(i)
        self.assertEqual(state.status, 'COMPLETED')
        self.assertEqual(len(state.attempts), 8)
        self.assertEqual(len(h.venue.broadcasts), 8)
        self.assertEqual(len(set(h.venue.broadcasts)), 8)

    def test_confirmed_revoke_that_leaves_allowance_nonzero_never_retries(self):
        h = self.harness(); i = h.intent()
        h.rpc.allowances[USDT] = 1
        h.executor.create(i, h.now)
        h.finish_step(i, clear=False)
        for _ in range(i.max_prepare_probes):
            h.now += 1
            state = h.executor.prepare(i.key, h.now)
            self.assertIn('no repeat authority', state.blocked_reason)
        with self.assertRaises(Blocked):
            h.executor.prepare(i.key, h.now + 1)
        self.assertEqual(len(state.attempts), 1)
        self.assertEqual(len(h.venue.broadcasts), 1)

    def test_unknown_cleanup_retains_wallet_barrier_after_expiry_restart_and_timeout(self):
        h = self.harness(); i = h.intent()
        h.rpc.allowances[USDT] = 1
        h.executor.create(i, h.now)
        h.executor.prepare(i.key, 11)
        h.executor.authorize(i.key, 12)
        signed = h.executor.sign(i.key, 13)
        h.venue.broadcast_fault = TimeoutError()
        sent = h.executor.broadcast(i.key, 14)
        h.restart()
        self.assertEqual(h.executor.signer.lookup(signed.attempts[-1].attempt_id,
                          signed.attempts[-1].payload.hash).tx_hash, signed.attempts[-1].tx_hash)
        # A second broadcast never occurs, even after the parent expires.
        h.executor.broadcast(i.key, 2000)
        h.executor.reconcile(i.key, 2000)
        self.assertEqual(len(h.venue.broadcasts), 1)
        self.assertEqual(h.executor.prepare(i.key, 2001).attempts[-1].state, 'UNKNOWN')
        with self.assertRaises(Blocked):h.executor.abort_unbroadcast(i.key, 2001)
        with self.assertRaises(Conflict):h.executor.create(h.intent('other', valid_until=3000), 2001)
        self.assertEqual(sent.attempts[-1].step, step(USDT))

    def test_cleanup_uses_parent_gas_budget_and_expiry_never_renews_it(self):
        h = self.harness(); i = h.intent(gas_budget=150000)
        h.rpc.allowances[USDT] = 1
        h.executor.create(i, h.now)
        h.finish_step(i)
        state = h.executor.prepare(i.key, h.now + 1)  # 50k spent + 120k next > 150k
        self.assertIn('parent gas budget', state.blocked_reason)
        self.assertEqual(len(state.attempts), 1)
        service = ExecutionService(store=None, executor=h.executor, mapping={}, observe=lambda _: None,
            wallet_id=f.WALLET, epoch=1, authority_version=1)
        # Pure Executor expiry guard independently refuses fresh cleanup/approval.
        state = h.executor.prepare(i.key, i.valid_until)
        self.assertIn('expired', state.blocked_reason)
        self.assertEqual(h.executor.abort_unsigned(i.key, i.valid_until).status, 'ABORTED')

    def test_route_change_or_rpc_failure_refuses_cleanup_before_sign_or_send(self):
        for failure in ('code', 'rpc'):
            with self.subTest(failure=failure):
                h = self.harness(); i = h.intent()
                h.rpc.allowances[USDT] = 1
                h.executor.create(i, h.now)
                h.executor.prepare(i.key, 11)
                h.executor.authorize(i.key, 12)
                if failure == 'code':h.rpc.code[h.decoder.router] = '0x00'
                else:h.rpc.fail = Blocked('synthetic RPC failure')
                with self.assertRaises(Blocked):h.executor.sign(i.key, 13)
                self.assertFalse(h.venue.broadcasts)


class Scope(unittest.TestCase):
    def setUp(self):
        self.i = f.intent(router=u.u.ROUTER)
        self.decoder = u.u.UntrustedRouterDecoder(u.policy())
        self.gates = u.gates(10)
        self.payload = zero_payload(self.i, USDT, nonce=7)
        cfg = signer_fixtures.policy_config()
        cfg.update(allowed_spenders=[u.u.ROUTER], allowance_recovery=True)
        self.config = cfg
        self.policy = SigningPolicy.from_config(cfg)

    def test_both_boundaries_allow_only_exact_zero_eligible_token_and_same_router(self):
        for token in u.u.TOKENS:
            p = replace(self.payload, to=token)
            validate_payload(self.i, step(token), p, self.gates, 10, self.decoder)
            self.policy.check(self.i, step(token), p, self.decoder, f.WALLET)
        changes = [dict(value=1), dict(to=NATIVE_BNB), dict(to='0x' + 'ab'*20),
                   dict(data=self.payload.data[:-1]+'1'), dict(data='0xa9059cbb'+self.payload.data[10:]),
                   dict(data='0x095ea7b3'+'0'*24+('ab'*20)+'0'*64)]
        for change in changes:
            with self.subTest(change=change):
                p = replace(self.payload, **change)
                with self.assertRaises(Blocked):validate_payload(self.i, step(USDT), p, self.gates, 10, self.decoder)
                with self.assertRaises(Blocked):self.policy.check(self.i, step(USDT), p, self.decoder, f.WALLET)
        disabled = SigningPolicy.from_config({k:v for k,v in self.config.items() if k!='allowance_recovery'})
        with self.assertRaises(Blocked):disabled.check(self.i, step(USDT), self.payload, self.decoder, f.WALLET)
        with self.assertRaises(Blocked):self.policy.check(self.i, 'APPROVE', self.payload, self.decoder, f.WALLET)
        for value in (1, 'true', None):
            with self.subTest(value=value), self.assertRaises(ContractError):
                SigningPolicy.from_config(dict(self.config, allowance_recovery=value))

    def test_repeated_or_post_approval_cleanup_and_wrong_nonce_refuse(self):
        a = Attempt('a', 'APPROVE', 'FINAL_SUCCESS', self.payload, 1, 1)
        with self.assertRaises(Blocked):
            validate_sequence(Execution(self.i, attempts=(a,)), step(USDT), self.payload, self.gates)
        a = replace(a, step=step(USDT))
        with self.assertRaises(Blocked):
            validate_sequence(Execution(self.i, attempts=(a, a)), step(USDT), self.payload, self.gates)
        with self.assertRaises(Blocked):
            validate_sequence(Execution(self.i, attempts=(a,)), 'APPROVE', self.payload,
                              replace(self.gates, nonce=9))

    def test_web3_revoke_builder_uses_only_zero_api_approval_and_rejects_wrong_spender(self):
        calls = []
        def request(method, endpoint, params):
            calls.append((method, endpoint, params))
            return dict(response=dict(data=dict(dexContractAddress=self.i.router, gasLimit='100000',
                                                gasPrice='1', data=self.payload.data)))
        venue = LiveVenue(SimpleNamespace(request=request), None, decoder=self.decoder)
        venue.vendors[self.i.key] = 'LiquidMesh'
        result = venue.revoke(self.i, USDT, 7)
        self.assertEqual(result, self.payload)
        self.assertEqual(calls[0][0:2], ('GET', 'aggregator/approve-transaction'))
        self.assertEqual(calls[0][2]['approveAmount'], '0')
        with self.assertRaises(Blocked):venue.revoke(self.i, NATIVE_BNB, 7)
        self.assertEqual(len(calls), 1)


class Receipt(unittest.TestCase):
    def setUp(self):
        self.case = receipt_fixtures.SettlementTests('test_actual_receipt_passes_accounting_and_replay')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        c = self.case
        p = zero_payload(c.intent, USDT, nonce=3)
        c.attempt = replace(c.attempt, step=step(USDT), payload=p)
        c.state = replace(c.state, attempts=(c.attempt,), status='ACTIVE')
        c.proof['tx'].update(to=p.to, input=p.data, gas=hex(p.gas), gasPrice=hex(p.gas_price))
        c.proof['receipt'].update(effectiveGasPrice=hex(p.gas_price), logs=[])

    def test_cleanup_receipt_accounts_only_gas_once_and_never_becomes_order(self):
        from larp.risk.accounting import advance_accounting
        c = self.case
        fact = c.observed()
        value = fact.read()
        validate_execution_observation(value)
        self.assertEqual(value['kind'], 'APPROVAL')
        self.assertEqual(value['maintenance'], 'ALLOWANCE_REVOKE')
        self.assertFalse(value['intent_terminal'])
        self.assertEqual(possible_swap_hashes(c.state), ())
        after = advance_accounting(c.portfolio, fact)
        self.assertEqual(after.read()['cash_units'], c.portfolio.read()['cash_units'])
        self.assertEqual(after.read()['positions'], c.portfolio.read()['positions'])
        self.assertEqual(after.read()['bnb_units'], c.portfolio.read()['bnb_units']-50000)
        self.assertEqual(advance_accounting(after, fact), after)
        validate_execution_observation(broadcast_observation(c.state, c.attempt, wallet_id='fake-wallet'))
        c.proof['receipt']['status'] = '0x0'
        reverted = c.observed().read()
        self.assertEqual(reverted['kind'], 'REVERT')
        self.assertTrue(reverted['intent_terminal'])

    def test_unexpected_token_movement_or_fake_nonzero_maintenance_fact_refuses(self):
        c = self.case
        value = c.observed().read()
        for change in (dict(approved_amount='1'), dict(token_contract=NATIVE_BNB), dict(kind='FILL')):
            with self.subTest(change=change), self.assertRaises(ContractError):
                validate_execution_observation(dict(value, **change))
        c.proof['receipt']['logs'] = [receipt_fixtures.log(USDT, c.intent.wallet, c.intent.router, 1)]
        with self.assertRaises(Blocked):c.observed()
