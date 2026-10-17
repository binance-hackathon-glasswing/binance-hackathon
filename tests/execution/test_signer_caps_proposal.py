"""CP-01: actual signer-policy boundaries; no keys, networking, service or DB."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from larp.contracts import ContractError
from larp.execution import Blocked, Payload, SwapEconomics, USDT, NATIVE_BNB
from larp.marketdata.port import TOKENS
from larp.signer.policy import SigningPolicy, EXAMPLE_CAP_BASIS
from tools.deploy.propose_signer_caps import build, main, ROUTER, FEE_WEI

WALLET = '0x' + '12' * 20


def inputs():
    return dict(schema='SignerCapsReference.v1', chain_id=56, price_unit='USDT_PER_WHOLE_TOKEN',
        reference_scope='HISTORICAL_REFERENCE_ONLY', observed_at='2026-10-10T11:38:00.565Z',
        artifact_sha256='a' * 64, response_sha256='b' * 64,
        tokens={s: dict(address=a, decimals=18, price_usdt='4') for s, a in TOKENS.items()})


class CapsProposal(unittest.TestCase):
    def test_units_finite_proposals_and_no_approval(self):
        result = build(inputs())
        self.assertFalse(result['ready_to_install'])
        self.assertEqual(result, build(inputs()))
        for name, cash in [('development', 35), ('final', 70)]:
            cfg = result['candidates'][name]['signing_policy']
            self.assertEqual(cfg['cap_basis'], EXAMPLE_CAP_BASIS)
            self.assertEqual(cfg['allowed_spenders'], [ROUTER])
            self.assertEqual(cfg['max_input_units'][USDT], str(cash * 10**18))
            self.assertEqual(cfg['max_input_units'][TOKENS['NVDAB']], str(cash * 10**18 // 2))
            self.assertNotIn(NATIVE_BNB, cfg['max_input_units'])
            self.assertEqual(cfg['max_fee_wei'], '200000000000000')

    def test_fractional_units_round_up_without_float(self):
        ref = inputs()
        ref['tokens']['NVDAB'].update(decimals=8, price_usdt='3')
        row = build(ref)['candidates']['development']['calculation']['NVDAB']
        self.assertEqual(row['max_input_units'], '2333333334')  # ceil(35/1.5 * 10**8)
        self.assertEqual(row['floor_price_ratio'], ['3', '2'])

    def check(self, policy, token, amount, step, *, fee=FEE_WEI, spender=ROUTER, native_value=0):
        receive = TOKENS['NVDAB'] if token == USDT else USDT
        intent = SimpleNamespace(pay_token=token, receive_token=receive, router=spender)
        data = '0x095ea7b3' + '0' * 24 + spender[2:] + format(amount, '064x')
        payload = Payload(56, WALLET, token if step == 'APPROVE' else spender,
                          native_value, 0, 1, fee, data)
        decoded = SwapEconomics(token, receive, amount, WALLET, 1, 123, native_value)
        decoder = SimpleNamespace(decode=lambda _: decoded)
        policy.check(intent, step, payload, decoder, WALLET)

    def test_every_real_policy_input_boundary_for_approve_and_swap(self):
        for candidate in build(inputs())['candidates'].values():
            policy = SigningPolicy.from_config(candidate['signing_policy'])
            for token, cap in policy.max_input_units.items():
                for step in ['APPROVE', 'SWAP']:
                    with self.subTest(token=token, step=step, cap=cap):
                        self.check(policy, token, cap, step)
                        with self.assertRaises(Blocked):
                            self.check(policy, token, cap + 1, step)

    def test_fee_spender_native_input_and_native_value_boundaries(self):
        policy = SigningPolicy.from_config(build(inputs())['candidates']['development']['signing_policy'])
        for step in ['APPROVE', 'SWAP']:
            self.check(policy, USDT, 1, step, fee=FEE_WEI)
            for change in [dict(fee=FEE_WEI + 1), dict(spender='0x' + '34' * 20), dict(native_value=1)]:
                with self.subTest(step=step, change=change), self.assertRaises(Blocked):
                    self.check(policy, USDT, 1, step, **change)
            with self.assertRaises(Blocked):
                self.check(policy, NATIVE_BNB, 1, step)

    def test_malformed_or_private_reference_fields_are_refused(self):
        cases = []
        for field, value in [('chain_id', True), ('chain_id', 1), ('artifact_sha256', 'A' * 64),
                             ('response_sha256', ''), ('observed_at', 'yesterdayZ'),
                             ('observed_at', '2026-10-10T11:38:00'),
                             ('reference_scope', 'APPROVED'), ('price_unit', 'USD_PER_SHARE')]:
            ref = inputs(); ref[field] = value; cases.append(ref)
        ref = inputs(); ref['wallet'] = WALLET; cases.append(ref)
        ref = inputs(); ref['tokens'].pop('NVDAB'); cases.append(ref)
        for change in [dict(price_usdt=4), dict(price_usdt=0.5), dict(price_usdt='0'),
                       dict(price_usdt='-1'), dict(price_usdt='NaN'), dict(decimals=True),
                       dict(decimals=0), dict(decimals=31), dict(address=USDT), dict(secret='x'),
                       dict(decimals=30, price_usdt='0.' + '0' * 39 + '1')]:
            ref = inputs(); ref['tokens']['NVDAB'].update(change); cases.append(ref)
        for i, ref in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(ContractError):
                build(ref)

    def test_cli_creates_private_proposal_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            src, dst = Path(directory) / 'reference.json', Path(directory) / 'proposal.json'
            src.write_text(json.dumps(inputs()))
            args = ['--reference', str(src), '--output', str(dst)]
            self.assertEqual(main(args), 0)
            before = dst.read_bytes()
            self.assertEqual(dst.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(before)['schema'], 'SignerCapsProposal.v1')
            self.assertEqual(main(args), 4)
            self.assertEqual(before, dst.read_bytes())

    def test_invalid_reference_cannot_create_output_or_echo_unknown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            src, dst = Path(directory) / 'reference.json', Path(directory) / 'proposal.json'
            ref = inputs(); ref['unexpected'] = 'DO_NOT_ECHO'
            src.write_text(json.dumps(ref))
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(['--reference', str(src), '--output', str(dst)]), 4)
            self.assertFalse(dst.exists())
            self.assertNotIn('DO_NOT_ECHO', output.getvalue())


if __name__ == '__main__':
    unittest.main()
