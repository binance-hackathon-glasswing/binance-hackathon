"""IDEA-096 AL7: recomputed candidate passes numeric review without granting installation authority."""
import json
import unittest

from larp.contracts import ContractError, Document
from larp.execution import NATIVE_BNB
from larp.strategy.profiles import build_live_profiles, validate_live
from tests.execution.test_caps_review import CapsReview
from tests.strategy.live_fixtures import registry
from tools.deploy.enable_allowance_recovery import candidate


class RecoveryCandidate(unittest.TestCase):
    def test_eight_child_candidate_and_exit_reserve_pass_caps_review(self):
        c = CapsReview('test_pins_and_private_output_no_overwrite_or_content_echo')
        c.setUp(); self.addCleanup(c.doCleanups)
        c.profile = build_live_profiles(Document.from_dict(c.profile['quote_cost_summary']), registry(),
                                        initial_gas_only=True)['REHEARSAL'].read()
        c.config.update(untrusted_router_policy_file='/synthetic/policy.json',
                        untrusted_router_policy_sha256='a' * 64)
        c.policy['allowed_tokens'].remove(NATIVE_BNB)
        c.inputs['quote_artifacts'] = [ref for ref in c.inputs['quote_artifacts'] if ref['path'] != 'BNB.json']
        runtime = {k: c.config[k] for k in ('run_id', 'build_id', 'wallet_address', 'mode')}
        runtime['driver'] = {k: c.config[k] for k in
                             ('untrusted_router_policy_file', 'untrusted_router_policy_sha256')}
        files = candidate(c.profile, c.config, c.policy, runtime, decision_id='IDEA-096 AL-IMPL01 candidate')
        c.profile, c.config, c.policy = [json.loads(files[n]) for n in
                                        ('profile.json', 'execution-config.json', 'signing-policy.json')]
        c.ledger['bnb_units'] = c.profile['exit_gas_reserve_units']
        c.save_inputs()
        result = c.report()
        self.assertEqual(result['numeric_status'], 'COVERED', result['blockers'])
        checks = {row['check']: row for row in result['checks']}
        self.assertEqual(checks['INITIAL_SIGNED_CHILD_GAS_ENVELOPE']['required'], str(8 * 100000 * 2 * 10**9))
        self.assertTrue(json.loads(files['runtime.json'])['driver']['allowance_recovery'])
        self.assertFalse(json.loads(files['allowance-recovery-review.json'])['ready_to_install'])
        validate_live(c.profile)
        c.config['gas_budget'] -= 1
        c.save_inputs()
        self.assertIn('INITIAL_SIGNED_CHILD_GAS_ENVELOPE', c.report()['blockers'])

    def test_runtime_cannot_claim_a_different_router_policy(self):
        from tests.marketdata.test_untrusted_quote_verifier import profile
        with self.assertRaises(ContractError):
            candidate(profile(), {}, {}, {}, decision_id='test')
