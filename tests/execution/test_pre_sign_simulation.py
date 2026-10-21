"""PS-01: narrow RPC simulation and real PostgreSQL pre-request refusal/recovery."""
from dataclasses import replace
import json
from unittest.mock import Mock

import pytest

from larp.execution import Blocked, DependencyUnavailable, Payload
from larp.execution_live.chain import Rpc
from larp.execution_live.service import ExecutionService
from tests.execution_fixtures import WALLET, ROUTER, finalized, FakeDecoder
from tests.marketdata.test_transport import Response
from tests.signer import test_service as fixtures


class Memory:
    def __init__(self): self.rows = []
    def put(self, row): self.rows.append(row)


class Opener:
    def __init__(self, result='0x', error=None):
        self.result, self.error, self.calls = result, error, []
    def open(self, request, timeout):
        row = json.loads(request.data);self.calls.append(row)
        if self.error == 'offline': raise OSError('PRIVATE_ENDPOINT')
        reply = dict(jsonrpc='2.0', id=row['id'])
        if self.error: reply['error'] = dict(code=3, message=self.error)
        else: reply['result'] = self.result
        return Response(json.dumps(reply).encode())


def payload():
    return Payload(56, WALLET, ROUTER, 0, 1, 900_000, 50_000_000, '0xad43f73d00')


def test_rpc_simulates_only_the_configured_exact_payload_at_latest_without_overrides():
    transport, artifacts = Opener(), Memory()
    rpc = Rpc('https://rpc.example', artifacts=artifacts, source_id='fixture', opener=transport,
              simulation_router=ROUTER)
    assert rpc.simulate_swap(payload()) is True
    assert transport.calls[0]['method'] == 'eth_call'
    assert transport.calls[0]['params'] == [dict({'from': WALLET}, to=ROUTER, value='0x0',
        nonce='0x1', gas=hex(900_000), gasPrice=hex(50_000_000), data='0xad43f73d00'), 'latest']
    assert artifacts.rows[0]['params'] == transport.calls[0]['params']
    with pytest.raises(Blocked): rpc.call('eth_call', transport.calls[0]['params'])


@pytest.mark.parametrize('changes', [dict(chain_id=1), dict(to=WALLET), dict(value=1), dict(gas=True),
                                    dict(data='0xabc'), dict(sender='not-a-wallet')])
def test_rpc_simulation_scope_refuses_before_network(changes):
    transport = Opener()
    rpc = Rpc('https://rpc.example', artifacts=Memory(), source_id='fixture', opener=transport,
              simulation_router=ROUTER)
    with pytest.raises(Blocked): rpc.simulate_swap(replace(payload(), **changes))
    assert not transport.calls


@pytest.mark.parametrize('result,error', [('0x','RFQ_OrderExpired'), ('0x','Min return not reached'),
                                         ('0x','offline'), (None,None), ('0xz',None)])
def test_rpc_simulation_failures_are_refusals_without_private_error_text(result, error):
    rpc = Rpc('https://rpc.example', artifacts=Memory(), source_id='fixture', opener=Opener(result,error),
              simulation_router=ROUTER)
    with pytest.raises(Blocked) as info: rpc.simulate_swap(payload())
    assert 'PRIVATE' not in str(info.value) and 'RFQ_' not in str(info.value)


class PreSignFlow(fixtures.SigningCase):
    def swap(self):
        self.service = self.signer(decoder=FakeDecoder())
        state, _ = self.authorized()
        self.executor.sign(state.intent.key, 12)
        sent = self.executor.broadcast(state.intent.key, 13).attempts[-1]
        self.venue.outcomes[sent.tx_hash] = finalized(sent, sender=self.wallet)
        self.executor.reconcile(state.intent.key, 17)
        self.guards.nonce = 1
        self.executor.prepare(state.intent.key, 18)
        state = self.executor.authorize(state.intent.key, 19)
        self.now = 19
        return state, state.attempts[-1]

    def flow(self):
        def settlement(state, attempt):
            return dict(schema='ExecutionObservation.v1', settlement='FINAL', kind='APPROVAL',
                        intent_id=state.intent.intent_id, attempt_id=attempt.attempt_id, tx_hash=attempt.tx_hash)
        return ExecutionService(store=self.store, executor=self.executor, mapping={}, observe=lambda fact: None,
            wallet_id=self.wallet, epoch=self.epoch, authority_version=self.execution.execution_authority()[0],
            settlement=settlement)

    def requests(self):
        with self.store.transaction() as db:
            return db.execute('SELECT request_id FROM signing_requests WHERE run_id=%s', ('run',)).fetchall()

    def test_failed_or_missing_simulation_aborts_before_a_new_signing_request(self):
        state, _ = self.swap()
        before = self.requests()
        self.remote.pre_sign_swap = Mock(side_effect=DependencyUnavailable('RPC unavailable'))
        result = self.flow().advance(state.intent.key, 19)
        self.assertEqual(result.status, 'ABORTED')
        self.assertEqual(self.requests(), before)
        self.assertEqual(result.attempts[-1].state, 'ABORTED')
        self.assertEqual(result.blocked_reason, 'PRE_SIGN_SWAP_SIMULATION_REFUSED')
        self.assertEqual(result.attempts[0].state, 'FINAL_SUCCESS')
        self.assertEqual(result.intent.valid_until, state.intent.valid_until)

    def test_successful_simulation_binds_the_exact_authorized_bytes(self):
        state, swap = self.swap()
        self.remote.pre_sign_swap = Mock(return_value=True)
        result = self.flow().advance(state.intent.key, 19)
        self.remote.pre_sign_swap.assert_called_once_with(swap.payload)
        self.assertEqual(result.attempts[-1].state, 'SIGNED_DURABLE')
        self.assertEqual(result.attempts[-1].payload.hash, swap.payload.hash)

    def test_expiry_during_simulation_refuses_a_new_request(self):
        state, swap = self.swap(); before = self.requests()
        def simulate(_): self.now = state.intent.valid_until;return True
        self.remote.pre_sign_swap = simulate
        with self.assertRaises(Blocked): self.remote.sign(swap.attempt_id, swap.payload, swap.epoch, swap.guard_version)
        self.assertEqual(self.requests(), before)

    def test_nonce_change_during_simulation_refuses_a_new_request(self):
        state, swap = self.swap(); before = self.requests()
        def simulate(_): self.guards.nonce += 1;return True
        self.remote.pre_sign_swap = simulate
        with self.assertRaises(Blocked): self.remote.sign(swap.attempt_id, swap.payload, swap.epoch, swap.guard_version)
        self.assertEqual(self.requests(), before)
