"""Offline checks for the LD02d SELL-gas/size-sweep script (IDEA-070 LD02d S1-S6); no host or network calls."""
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'docs/build/ops/ld02-20261020/size-sell-check.sh'
USDT = '0x55d398326f99059ff775485246999027b3197955'
NVDAB = '0x02fca66c1d1afb4e2a7884261eb00f63598a7436'
WALLET = '0x' + 'ab' * 20


class Ld02dScriptTests(unittest.TestCase):
    def setUp(self):
        source = SCRIPT.read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        self.ns = {'__name__': 'offline_ld02d'}
        exec(compile(source, str(SCRIPT), 'exec'), self.ns)
        self.scope = dict(wallet=WALLET, usdt=USDT, tokens={USDT, NVDAB}, calldata={'0xad43f73d00'}, slots={})

    def fake_chain(self, layouts):
        """eth_call answers as a token whose balances/allowances live at `layouts[token]` = (balance, allowance)."""
        ns = self.ns

        def rpc(url, method, params, scope):
            if not ns['allowed_call'](method, params, scope):
                raise ValueError('RPC_CALL_REFUSED')
            tx, override = params[0], (params[2] if len(params) == 3 else {})
            diff = override.get(tx['to'], {}).get('stateDiff', {})
            balance_base, allowance_base = layouts[tx['to']]
            if tx['data'].startswith(ns['BALANCE_OF_CALL']):
                slot = ns['mapping_slot'](WALLET, balance_base)
            else:
                slot = ns['allowance_slot'](WALLET, allowance_base)
            return diff.get(slot, '0x0')
        ns['rpc'] = rpc

    def test_s2_slot_proof_finds_plain_and_namespaced_layouts(self):
        oz = self.ns['OZ5_ERC20']
        self.fake_chain({USDT: (1, 2), NVDAB: (oz, oz + 1)})
        usdt = self.ns['prove_slots']('https://p', self.scope, USDT)
        self.assertEqual((usdt['proven'], usdt['balance_base'], usdt['allowance_base']), (True, '0x1', '0x2'))
        token = self.ns['prove_slots']('https://p', self.scope, NVDAB)
        self.assertEqual((token['proven'], int(token['balance_base'], 16)), (True, oz))
        proof = self.scope['proven_slots'][NVDAB]
        self.assertEqual(proof, dict(balance=token['balance_slot'], allowance=token['allowance_slot']))
        sim = {'from': WALLET, 'to': self.ns['ROUTER'], 'data': '0xad43f73d00'}
        diff = {s: '0x' + self.ns['word_hex'](self.ns['PLENTY']) for s in proof.values()}
        self.assertTrue(self.ns['allowed_call']('eth_estimateGas', [sim, 'latest', {NVDAB: {'stateDiff': diff}}], self.scope))
        for bad in ({self.ns['mapping_slot'](WALLET, 0): '0x1'},
                    {s: '0x1' for s in proof.values()}):
            self.assertFalse(self.ns['allowed_call']('eth_estimateGas', [sim, 'latest', {NVDAB: {'stateDiff': bad}}], self.scope))

    def test_s2_unknown_layout_is_not_proven(self):
        self.fake_chain({NVDAB: (99, 100)})
        self.assertEqual(self.ns['prove_slots']('https://p', self.scope, NVDAB),
                         dict(proven=False, reason='balance slot not found'))

    def test_s5_overrides_only_on_permitted_slots_of_pinned_tokens(self):
        ok = self.ns['allowed_call']
        self.ns['permit_slots'](self.scope, NVDAB, 0)
        good = self.ns['mapping_slot'](WALLET, 0)
        allowance = self.ns['allowance_slot'](WALLET, 1)
        self.scope['proven_slots'] = {NVDAB: dict(balance=good, allowance=allowance)}
        sim = {'from': WALLET, 'to': self.ns['ROUTER'], 'data': '0xad43f73d00', 'value': '0x0'}
        self.assertTrue(ok('eth_estimateGas', [sim, 'latest', {NVDAB: {'stateDiff': {
            good: '0x' + self.ns['word_hex'](self.ns['PLENTY']),
            allowance: '0x' + self.ns['word_hex'](self.ns['PLENTY'])}}}], self.scope))
        for method, params in [
                ('eth_sendRawTransaction', ['0x00']),
                ('eth_getLogs', [{}]),
                ('eth_estimateGas', [sim, 'latest']),
                ('eth_estimateGas', [sim, 'latest', {NVDAB: {'stateDiff': {'0x' + '0' * 63 + '5': '0x1'}}}]),
                ('eth_estimateGas', [sim, 'latest', {'0x' + '9' * 40: {'stateDiff': {good: '0x1'}}}]),
                ('eth_estimateGas', [sim, 'latest', {NVDAB: {'state': {good: '0x1'}}}]),
                ('eth_estimateGas', [sim, 'latest', {NVDAB: {'stateDiff': {good: '0x1'}, 'code': '0x00'}}]),
                ('eth_estimateGas', [dict(sim, data='0xad43f73d01'), 'latest', {NVDAB: {'stateDiff': {good: '0x1'}}}]),
                ('eth_estimateGas', [dict(sim, value='0x1'), 'latest', {NVDAB: {'stateDiff': {good: '0x1'}}}]),
                ('eth_call', [dict(to=NVDAB, data='0xa9059cbb' + '0' * 128), 'latest'])]:
            with self.subTest(method=method, params=str(params)[:60]):
                self.assertFalse(ok(method, params, self.scope))
                with self.assertRaisesRegex(ValueError, 'RPC_(CALL|METHOD)_REFUSED'):
                    self.ns['rpc']('https://a.b', method, params, self.scope)

    def test_s1_s3_s4_sweep_reports_gas_and_round_trip(self):
        quotes = []

        def quote(symbol, side, units):
            quotes.append((symbol, side, units))
            if symbol == 'MSFTB':
                raise RuntimeError('quote refused')
            out = units * 2 if side == 'BUY' else units // 2 * 99 // 100
            data = '0xad43f73d' + side.lower().encode().hex() + format(units, 'x')
            return dict(response=dict(data=dict(tx=dict(to=self.ns['ROUTER'], data=data, gas='250000'),
                        routerResult=dict(fromTokenAmount=str(units), toTokenAmount=str(out)))))

        def rpc(url, method, params, scope):
            self.assertTrue(self.ns['allowed_call'](method, params, scope))
            return hex(500_000 if bytes.fromhex(params[0]['data'][10:14]) == b'bu' else 600_000)
        self.ns['rpc'] = rpc
        token = {'NVDAB': {NVDAB: {'stateDiff': {}}}}
        self.ns['permit_slots'](self.scope, USDT, 1)
        self.scope['proven_slots'] = {
            USDT: dict(balance=self.ns['mapping_slot'](WALLET, 1), allowance=self.ns['allowance_slot'](WALLET, 2)),
            NVDAB: dict(balance=self.ns['mapping_slot'](WALLET, 0), allowance=self.ns['allowance_slot'](WALLET, 1))}
        usdt = {USDT: {'stateDiff': {s: '0x' + self.ns['word_hex'](self.ns['PLENTY'])
                                   for s in self.scope['proven_slots'][USDT].values()}}}
        token['NVDAB'][NVDAB]['stateDiff'] = {s: '0x' + self.ns['word_hex'](self.ns['PLENTY'])
                                            for s in self.scope['proven_slots'][NVDAB].values()}
        self.ns['permit_slots'](self.scope, NVDAB, 0)
        out = self.ns['sweep']('https://p', self.scope, quote, usdt, token, sizes=(10, 20))
        nvda = out['NVDAB']
        self.assertEqual((nvda['max_buy_gas'], nvda['max_sell_gas']), (500_000, 600_000))
        self.assertEqual(nvda['sizes']['10']['round_trip_bp'], 100.0)
        self.assertEqual(nvda['sizes']['10']['sell']['in_units'], 20 * 10**18)
        self.assertEqual(out['GOOGLB']['sizes']['10']['sell']['gas'], 'NOT_PROVEN')
        self.assertIn('quote refused', out['MSFTB']['sizes']['10']['buy_error'])
        self.assertIn(('NVDAB', 'SELL', 20 * 10**18), quotes)
        self.assertNotIn('ad43f73d', json.dumps(out))

    def test_refusal_and_sanitizer(self):
        self.assertEqual(self.ns['refusal'](RuntimeError('rpc.example.org')),
                         dict(error='LD02D_REFUSED', signing_enabled=False, reason='RuntimeError'))
        with self.assertRaises(ValueError):
            self.ns['sanitize'](json.dumps(dict(x=WALLET)), [WALLET])
        with self.assertRaises(ValueError):
            self.ns['sanitize']('see https://x', [])


if __name__ == '__main__':
    unittest.main()
