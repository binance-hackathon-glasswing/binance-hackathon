"""WR-C #44 (WR02): the signer's own pinned signing policy (IDEA-049-C, WR-C criteria 1-5).

The signer must refuse an approve or swap outside its own root-owned configuration even when the intent that primary
wrote agrees with it. Real PostgreSQL with the deployed roles; throwaway keys; nothing is broadcast.
"""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from larp.contracts import ContractError
from larp.execution import USDT
from tests.execution_fixtures import FakeDecoder, ROUTER, TOKEN, finalized
from tests.signer import test_service as fixtures

ROOT = Path(__file__).resolve().parents[2]
ATTACKER = '0x' + 'a' * 40
OTHER_BSTOCK = '0x3f53de71c126bdabae20f9cd64848d317f6c3238'
UNLIMITED = 2**256 - 1
CAP = 1000
FEE_CAP = 150000  # the fixture approve uses 120000 gas at price 1


def policy_config(**changes):
    value = dict(cap_basis='TEST_FIXTURE', allowed_spenders=[ROUTER], allowed_tokens=[USDT, TOKEN],
                 max_input_units={USDT: str(CAP), TOKEN: str(CAP)}, max_fee_wei=str(FEE_CAP))
    value.update(changes)
    return value


def policy(**changes):
    from larp.signer.policy import SigningPolicy
    return SigningPolicy.from_config(policy_config(**changes))


class PolicyConfiguration(unittest.TestCase):
    def test_valid_policy_parses(self):
        parsed = policy()
        self.assertEqual(parsed.allowed_spenders, frozenset({ROUTER}))
        self.assertEqual(parsed.max_input_units[USDT], CAP)

    def test_invalid_policies_are_refused(self):
        cases = {
            'no spender': dict(allowed_spenders=[]),
            'checksummed spender': dict(allowed_spenders=['0x' + 'A' * 40]),
            'token outside the universe': dict(allowed_tokens=[USDT, TOKEN, ATTACKER],
                                               max_input_units={USDT: '1', TOKEN: '1', ATTACKER: '1'}),
            'missing cap': dict(max_input_units={USDT: str(CAP)}),
            'cap for a token not allowed': dict(max_input_units={USDT: '1', TOKEN: '1', OTHER_BSTOCK: '1'}),
            'zero cap': dict(max_input_units={USDT: '0', TOKEN: '1'}),
            'unlimited cap': dict(max_input_units={USDT: str(2**128), TOKEN: '1'}),
            'numeric cap': dict(max_input_units={USDT: CAP, TOKEN: '1'}),
            'fee cap missing': dict(max_fee_wei=None),
            'cap basis missing': dict(cap_basis=''),
        }
        for name, change in cases.items():
            with self.subTest(name=name), self.assertRaises(ContractError):
                policy(**change)
        with self.assertRaises(ContractError):
            from larp.signer.policy import SigningPolicy
            SigningPolicy.from_config({**policy_config(), 'extra': 1})

    def config(self, **changes):
        value = dict(schema='SignerService.v1', run_id='run', build_id='b' * 40, mode='dev',
                     wallet_address='0x' + '1' * 40, key_file='/k', interval_seconds=1,
                     database_dsn_file='/d', signing_policy=policy_config())
        value.update(changes)
        return value

    def test_signer_configuration_requires_the_policy(self):
        from larp.signer.service import validate_config
        validate_config(self.config())
        for change in (dict(signing_policy=None), dict(signing_policy=policy_config(allowed_spenders=[]))):
            with self.subTest(change=change), self.assertRaises(ContractError):
                validate_config(self.config(**change))

    def test_live_run_refuses_example_caps(self):
        from larp.signer.policy import EXAMPLE_CAP_BASIS
        from larp.signer.service import validate_config
        example = policy_config(cap_basis=EXAMPLE_CAP_BASIS)
        validate_config(self.config(signing_policy=example))  # dev may use the marked example values
        with self.assertRaises(ContractError):
            validate_config(self.config(mode='live', signing_policy=example))
        validate_config(self.config(mode='live'))

    def test_example_config_marks_its_caps_as_an_example(self):
        from larp.signer.policy import EXAMPLE_CAP_BASIS
        from larp.signer.service import validate_config
        example = json.loads((ROOT / 'config/hosts/signer.example.json').read_text())
        self.assertEqual(example['signing_policy']['cap_basis'], EXAMPLE_CAP_BASIS)
        filled = {**example, 'run_id': 'run', 'build_id': 'b' * 40, 'wallet_address': '0x' + '1' * 40,
                  'database_host': 'h', 'database_ca_sha256': '0' * 64,
                  'signing_policy': {**example['signing_policy'], 'allowed_spenders': [ROUTER]}}
        validate_config(filled)


class PolicyCase(fixtures.RolesCase):
    """The deployed roles: `larp_execution` registers and authorizes, `larp_signer` answers."""

    def setUp(self):
        super().setUp()
        self.service = self.policy_signer()

    def policy_signer(self, decoder=None, **changes):
        from larp.signer.service import SignerService
        return SignerService(store=self.as_role['larp_signer'], run_id='run', wallet=self.wallet,
                             credentials=dict(WALLET_PRIVATE_KEY=self.account.key.hex()),
                             clock_s=lambda: self.now if self.signer_now is None else self.signer_now,
                             decoder=decoder, policy=policy(**changes))

    def refused_without_key(self, request_id, fragment):
        with patch.object(self.service.signer.account, 'sign_transaction',
                          wraps=self.service.signer.account.sign_transaction) as sign:
            self.service.once()
        sign.assert_not_called()
        self.assertEqual(self.signatures(), [])
        self.assertIn(fragment, self.refusals()[request_id])


class SignerPolicyRefusals(PolicyCase):
    def test_wr02_malicious_intent_written_as_larp_execution_is_refused(self):
        """The issue's scenario: primary registers approve(attacker, 2**256-1) and authorizes it."""
        state, attempt = self.authorized(router=ATTACKER, amount=UNLIMITED)
        self.assertEqual(attempt.state, 'AUTHORIZED')  # primary's own checks accept the self-consistent intent
        self.assertEqual(attempt.payload.data[34:74], 'a' * 40)
        request_id, _ = self.request(state, attempt)
        self.refused_without_key(request_id, 'spender')

    def test_wr02_each_policy_limit_refuses_before_key_use(self):
        cases = (
            ('unlimited approve to the allowed spender', dict(amount=UNLIMITED), None, 'unlimited'),
            ('one unit above the cap', dict(amount=CAP + 1), None, 'cap'),
            ('fee above the cap', dict(), 160000, 'fee'),
            ('token outside the list', dict(receive_token=OTHER_BSTOCK), None, 'token'),
        )
        for number, (name, changes, estimate, fragment) in enumerate(cases):
            with self.subTest(name=name):
                if estimate is not None:
                    self.venue.estimate = estimate
                state, attempt = self.authorized(intent_id=f'wr02-{number}', **changes)
                self.assertEqual(attempt.state, 'AUTHORIZED')
                request_id, _ = self.request(state, attempt)
                self.refused_without_key(request_id, fragment)
                self.executor.abort_unbroadcast(state.intent.key, 13)
                self.venue.estimate = 100000

    def test_wr02_approve_within_the_policy_is_signed(self):
        state, attempt = self.authorized(amount=CAP)
        request_id, _ = self.request(state, attempt)
        self.service.once()
        self.assertEqual([row[0] for row in self.signatures()], [attempt.attempt_id])
        self.assertNotIn(request_id, self.refusals())

    def approved_swap(self):
        state, attempt = self.authorized()
        self.now = 13
        self.executor.sign(state.intent.key, 13)
        sent = self.executor.broadcast(state.intent.key, 14).attempts[-1]
        self.venue.outcomes[sent.tx_hash] = finalized(sent, sender=self.wallet)
        self.executor.reconcile(state.intent.key, 17)
        self.guards.nonce = 1
        self.executor.prepare(state.intent.key, 18)
        state = self.executor.authorize(state.intent.key, 19)
        self.assertEqual(state.attempts[-1].step, 'SWAP')
        self.now = 19
        return state, state.attempts[-1]

    def test_wr02_swap_is_checked_against_the_policy(self):
        state, swap = self.approved_swap()
        for name, changes, fragment in (('input above the cap', dict(max_input_units={USDT: '99', TOKEN: '1'}), 'cap'),
                                        ('router outside the list', dict(allowed_spenders=['0x' + '9' * 40]),
                                         'spender')):
            with self.subTest(name=name):
                self.service = self.policy_signer(decoder=FakeDecoder(), **changes)
                request_id, _ = self.request(state, swap, now=19)
                with patch.object(self.service.signer.account, 'sign_transaction') as sign:
                    self.service.once()
                sign.assert_not_called()
                self.assertIn(fragment, self.refusals()[request_id])
                self.assertEqual(len(self.signatures()), 1)  # the approval only
        self.service = self.policy_signer(decoder=FakeDecoder())
        self.request(state, swap, now=20)
        self.now = 20
        self.service.once()
        self.assertEqual(len(self.signatures()), 2)

    def test_wr02_gap29_swap_refusal_still_holds_with_a_policy(self):
        state, swap = self.approved_swap()
        request_id, _ = self.request(state, swap, now=19)
        self.service.once()
        self.assertIn('verified router', self.refusals()[request_id])

    def test_wr02_service_requires_a_policy(self):
        from larp.signer.service import SignerService
        with self.assertRaises(TypeError):
            SignerService(store=self.as_role['larp_signer'], run_id='run', wallet=self.wallet,
                          credentials=dict(WALLET_PRIVATE_KEY=self.account.key.hex()), clock_s=lambda: 12)


class PinnedPolicyFile(fixtures.CommandCase):
    """The policy comes only from the root-owned config file pinned by the release manifest, never the database."""

    def setUp(self):
        super().setUp()
        self.config['signing_policy'] = policy_config()

    def test_wr02_policy_edit_after_pinning_refuses_start(self):
        self.unquarantine()
        args = self.write()
        self.assertEqual(self.main('check', args)[0], 0)
        path = Path(args[1])
        edited = dict(self.config, signing_policy=policy_config(allowed_spenders=[ATTACKER]))
        path.write_bytes(json.dumps(edited).encode())
        code, out = self.main('run', args, max_cycles=1)
        self.assertEqual((code, json.loads(out)['reason']), (4, 'START_REFUSED'))

    def test_wr02_started_signer_reports_its_cap_basis(self):
        self.unquarantine()
        code, out = self.main('run', self.write(), max_cycles=1)
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out.splitlines()[0])['cap_basis'], 'TEST_FIXTURE')

    def test_wr02_missing_policy_refuses_start(self):
        del self.config['signing_policy']
        self.assertEqual(self.main('check', self.write())[0], 4)
