"""C-REQ-037/043/049: independent run authority, real PostgreSQL, throwaway keys."""
from unittest.mock import patch

from tests.signer import test_service as fixtures


class SignerAuthority(fixtures.SigningCase):
    def setUp(self):
        super().setUp()
        # Bind the genesis row before the first journal event. Changing it after
        # registration would invalidate the journal, obscuring the authority test.
        with self.store.transaction() as db:
            db.execute('UPDATE runs SET wallet_id=%s WHERE run_id=%s', (self.wallet, 'run'))

    def projection(self, **changes):
        current = self.store.load('run').read()
        projection = dict(current['projection'], **changes)
        self.store.commit(self.batch(event_id='authority:' + str(current['version']), projection=projection))

    def production(self, registered='version', build='version', wallet=None, manifest='a' * 64):
        self.projection(registered_version={} if registered is None else dict(
            build_id=registered, manifest_sha256=manifest))
        with self.store.transaction() as db:
            db.execute('UPDATE runs SET mode=%s,wallet_id=%s WHERE run_id=%s',
                       ('dev', wallet or self.wallet, 'run'))
        self.service.build_id = build  # the signer's own verified release identity
        self.service.manifest_sha256 = 'a' * 64
        self.service.registry.signer_build_id = build
        self.service.registry.signer_manifest_sha256 = 'a' * 64

    def halt(self):
        self.projection(halt=dict(reasons=dict(CLOCK=dict(since_ms=13000, latched=True))))

    def assert_no_key_use(self, request_id):
        with patch.object(self.service.signer.account, 'sign_transaction',
                          wraps=self.service.signer.account.sign_transaction) as sign:
            self.service.once()
        sign.assert_not_called()
        self.assertEqual(self.signatures(), [])
        self.assertIn(request_id, self.refusals())

    def test_c_req_037_halt_after_request_creation_overrides_true_request_gates(self):
        state, attempt = self.authorized()
        request_id, request = self.request(state, attempt)
        self.assertTrue(request['gates']['risk_valid'])
        self.halt()
        self.assert_no_key_use(request_id)

    def test_c_req_043_registered_build_mismatch_refuses_before_signing(self):
        state, attempt = self.authorized()
        self.production(registered='another-build')
        request_id, _ = self.request(state, attempt)
        self.assert_no_key_use(request_id)

    def test_c_req_043_signer_release_mismatch_refuses_before_signing(self):
        state, attempt = self.authorized()
        self.production(build='another-build')
        request_id, _ = self.request(state, attempt)
        self.assert_no_key_use(request_id)

    def test_c_req_043_unregistered_production_run_refuses_before_signing(self):
        state, attempt = self.authorized()
        self.production(registered=None)
        request_id, _ = self.request(state, attempt)
        self.assert_no_key_use(request_id)

    def test_c_req_043_production_signer_without_build_refuses_before_signing(self):
        state, attempt = self.authorized()
        self.production(build=None)
        request_id, _ = self.request(state, attempt)
        self.assert_no_key_use(request_id)

    def test_c_req_003_authoritative_run_wallet_must_match(self):
        state, attempt = self.authorized()
        self.production(wallet='0x' + '7' * 40)
        request_id, _ = self.request(state, attempt)
        self.assert_no_key_use(request_id)

    def test_c_req_043_matching_production_build_signs_once_and_recovers(self):
        state, attempt = self.authorized()
        self.production()
        request_id, _ = self.request(state, attempt)
        self.assertEqual(self.service.once(), 1)
        signed = self.execution.lookup(attempt.attempt_id, attempt.payload.hash)
        self.assertTrue(self.remote.verify(attempt.payload, signed))
        self.assertEqual(self.service.once(), 0)
        self.assertEqual(len(self.signatures()), 1)
        self.assertNotIn(request_id, self.refusals())
        self.halt()
        self.assertEqual(self.execution.lookup(attempt.attempt_id, attempt.payload.hash), signed)
        self.execution.check_authority(attempt.epoch, attempt.guard_version)
        fact = dict(event_id='reconciliation-fixture', run_id='run', kind='SYNTHETIC')
        self.assertEqual(self.execution.put_observation(fact, attempt.epoch, attempt.guard_version), fact)

    def test_c_req_037_halt_before_registry_commit_cannot_release_bytes(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, attempt)
        put = self.execution.put_if_absent

        def intervene(*args):
            self.halt()
            return put(*args)

        with patch.object(self.service.registry, 'put_if_absent', side_effect=intervene):
            self.service.once()
        self.assertEqual(self.signatures(), [])
        self.assertIn(request_id, self.refusals())

    def test_c_req_043_version_change_before_registry_commit_cannot_release_bytes(self):
        state, attempt = self.authorized()
        self.production()
        request_id, _ = self.request(state, attempt)
        put = self.execution.put_if_absent

        def intervene(*args):
            self.projection(registered_version=dict(build_id='another-build'))
            return put(*args)

        with patch.object(self.service.registry, 'put_if_absent', side_effect=intervene):
            self.service.once()
        self.assertEqual(self.signatures(), [])
        self.assertIn(request_id, self.refusals())

    def test_c_req_043_explicit_offline_registration_mismatch_is_refused(self):
        state, attempt = self.authorized()
        self.projection(registered_version=dict(build_id='another-build'))
        request_id, _ = self.request(state, attempt)
        self.assert_no_key_use(request_id)

    def test_c_req_058_same_build_different_manifest_refuses_before_signing(self):
        state, attempt = self.authorized()
        self.production(manifest='b' * 64)
        request_id, _ = self.request(state, attempt)
        self.assert_no_key_use(request_id)

    def test_c_req_058_manifest_change_before_registry_commit_cannot_release_bytes(self):
        state, attempt = self.authorized()
        self.production()
        request_id, _ = self.request(state, attempt)
        put = self.service.registry.put_if_absent

        def intervene(*args):
            self.projection(registered_version=dict(build_id='version', manifest_sha256='b' * 64))
            return put(*args)

        with patch.object(self.service.registry, 'put_if_absent', side_effect=intervene):
            self.service.once()
        self.assertEqual(self.signatures(), [])
        self.assertIn(request_id, self.refusals())
