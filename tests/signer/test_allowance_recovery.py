"""LD06: actual PostgreSQL request/registry and isolated signer on ephemeral fixture keys."""
from dataclasses import replace

from larp.execution import Attempt, REVOKE_TOKENS, digest
from larp.execution_live import signing
from larp.signer.local import verify
from larp.signer.policy import SigningPolicy
from tests.execution import test_allowance_recovery as recovery
from tests.execution import test_untrusted_router as u
from tests.signer import test_service as fixtures


class CleanupSigner(fixtures.SigningCase):
    def queued(self, *, enabled=True, **payload_changes):
        i = recovery.f.intent(wallet=self.wallet, router=u.u.ROUTER)
        state = self.executor.create(i, 10)
        gates = self.guards.snapshot(i, 12)
        p = replace(recovery.zero_payload(i, recovery.USDT), **payload_changes)
        name = recovery.step(recovery.USDT)
        a = Attempt(digest([i.key, name]), name, 'AUTHORIZED', p, gates.epoch, gates.authority_version)
        state = self.execution.commit(state, replace(state, attempts=(a,)), dict(type='SYNTHETIC_AUTHORIZED'),
                                      gates.epoch, gates.state_version)
        cfg = fixtures.policy_config()
        cfg.update(allowed_spenders=[i.router], allowance_recovery=enabled)
        self.policy = SigningPolicy.from_config(cfg)
        self.decoder = u.u.UntrustedRouterDecoder(u.policy())  # signer has no RPC
        self.service = fixtures.signer_service(self, policy=self.policy, decoder=self.decoder)
        request_id, _ = self.request(state, a)
        return i, a, request_id

    def test_zero_cleanup_signs_once_and_registry_survives_signer_restart(self):
        i, a, request_id = self.queued()
        self.assertEqual(self.service.once(), 1)
        signed = self.execution.lookup(a.attempt_id, a.payload.hash)
        self.assertTrue(verify(a.payload, signed))
        self.assertEqual(len(self.signatures()), 1)
        self.service = fixtures.signer_service(self, policy=self.policy, decoder=self.decoder)
        self.assertEqual(self.service.once(), 0)
        self.assertEqual(self.execution.lookup(a.attempt_id, a.payload.hash), signed)
        self.assertIsNone(self.decoder.rpc)
        self.assertFalse(self.refusals())

    def test_disabled_cleanup_policy_refuses_before_signature(self):
        _, _, request_id = self.queued(enabled=False)
        self.assert_refusal(request_id, 'not authorized')

    def test_nonzero_cleanup_request_refuses_before_signature(self):
        i = recovery.f.intent(wallet=self.wallet, router=u.u.ROUTER)
        _, _, request_id = self.queued(data=recovery.zero_payload(i, recovery.USDT, amount=1).data)
        self.assert_refusal(request_id, 'not authorized')

    def test_stale_nonce_is_refused_by_signer_independent_payload_validation(self):
        _, _, request_id = self.queued(nonce=1)
        self.assert_refusal(request_id, 'nonce mismatch')
