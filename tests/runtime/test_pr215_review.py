"""LD02cd-RV01: collector privacy, proof boundaries and actual probe timing, offline only."""
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
USDT = '0x55d398326f99059ff775485246999027b3197955'
TOKEN = '0x02fca66c1d1afb4e2a7884261eb00f63598a7436'
WALLET = '0x' + 'ab' * 20
SECRET = 'PrivateCredentialValueThatMustNeverAppear1234567890'


def load(name):
    path = ROOT / 'docs/build/ops/ld02-20261020' / name
    source = path.read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    ns = {'__name__': 'offline_pr215'}
    exec(compile(source, str(path), 'exec'), ns)
    return ns


def scope():
    return dict(wallet=WALLET, usdt=USDT, tokens={USDT, TOKEN}, calldata={'0xad43f73d00'},
                usdt_units=10**12, slots={}, forbidden=[SECRET, WALLET, WALLET[2:]])


@pytest.mark.parametrize('name', ['rfq-rpc-check.sh', 'size-sell-check.sh'])
@pytest.mark.parametrize('message', ['x' * 55 + SECRET, 'RFQ_' + SECRET])
def test_error_private_values_are_scanned_before_shortening_or_extraction(name, message):
    ns, s = load(name), scope()
    def rpc(url, method, params, scope, *args):
        if method == 'eth_getBlockByNumber': return dict(number='0x10')
        if method == 'eth_getStorageAt': return hex(10**12)
        if method == 'eth_call': return hex(2**255)
        raise ns['RpcRefused'](dict(code=3, message=message))
    ns['rpc'] = rpc
    with pytest.raises(ValueError, match='SANITIZER_FORBIDDEN_VALUE'):
        if name.startswith('rfq'):
            ns['DELAYS'] = (0,)
            out = ns['rfq_check']('https://p', s, {'NVDAB': dict(t0=0, data='0xad43f73d00')}, clock=lambda: 100)
        else:
            out = ns['simulate']('https://p', s, '0xad43f73d00', {})
        ns['sanitize'](json.dumps(out), s['forbidden'])


def test_quote_error_secret_is_scanned_before_the_second_80_character_cut():
    ns, s = load('size-sell-check.sh'), scope()
    def quote(*args): raise RuntimeError('x' * 55 + SECRET)
    with pytest.raises(ValueError, match='SANITIZER_FORBIDDEN_VALUE'):
        out = ns['sweep']('https://p', s, quote, {}, {}, sizes=(10,))
        ns['sanitize'](json.dumps(out), s['forbidden'])


def test_collect_wires_private_values_into_route_marker_filtering():
    ns = load('rfq-rpc-check.sh')
    config = dict(wallet_address=WALLET, database_host='private-db.example',
                  driver=dict(balance_rpc_providers=[dict(source_id='P', url='https://rpc.example/private')]))
    def opened(path, mode='rb'):
        return io.BytesIO(json.dumps(config if path.endswith('runtime.json') else dict(minimum_trade_units=10)).encode())
    class Port:
        def __init__(self, *args, **kwargs): pass
        def quote(self, *args):
            return dict(response=dict(data=dict(tx=dict(to=ns['ROUTER'], data='0xad43f73d00', gas='250000'),
                      routerResult=dict(vendorName='x' * 70 + SECRET))))
    ns['rpc'] = lambda *a, **kw: '0x1'
    ns['rfq_check'] = lambda *a, **kw: {}
    ns['rpc_check'] = lambda *a, **kw: {}
    with patch('builtins.open', opened), patch('larp.runtime.credentials.runtime_secrets', return_value={
            'BINANCE_API_KEY': SECRET, 'BINANCE_SECRET_KEY': 'OtherPrivateCredential'}), \
            patch('larp.marketdata.port.MarketPort', Port), patch('larp.marketdata.web3.Web3Client'):
        with pytest.raises(ValueError, match='SANITIZER_FORBIDDEN_VALUE'):
            packet, forbidden = ns['collect']()
            ns['sanitize'](json.dumps(packet), forbidden)


def test_rfq_override_is_exact_allowance_slot_and_value():
    ns, s = load('rfq-rpc-check.sh'), scope()
    slot = ns['mapping_slot'](ns['ROUTER'], ns['mapping_slot'](WALLET, 2))
    value = '0x' + ns['word_hex'](ns['OVERRIDE_ALLOWANCE'])
    tx = dict({'from': WALLET, 'to': ns['ROUTER'], 'data': '0xad43f73d00'})
    assert ns['allowed_call']('eth_estimateGas', [tx, 'latest', {USDT: {'stateDiff': {slot: value}}}], s)
    for diff in [{'0x' + '0' * 64: value}, {slot: '0x0'}, 'x']:
        assert not ns['allowed_call']('eth_estimateGas', [tx, 'latest', {USDT: {'stateDiff': diff}}], s)


def test_discovery_slots_never_authorize_swap_simulations():
    ns, s = load('size-sell-check.sh'), scope()
    ns['permit_slots'](s, TOKEN, 0)
    slot = ns['mapping_slot'](WALLET, 0)
    tx = dict({'from': WALLET, 'to': ns['ROUTER'], 'data': '0xad43f73d00'})
    assert not ns['allowed_call']('eth_estimateGas', [tx, 'latest', {TOKEN: {
        'stateDiff': {slot: '0x' + ns['word_hex'](ns['PLENTY'])}}}], s)


def test_rfq_bounds_use_actual_probe_start_age_not_requested_delay():
    ns, s = load('rfq-rpc-check.sh'), scope()
    clock = {'t': 111.0}
    def rpc(url, method, params, scope, *args):
        clock['t'] += 2
        if method == 'eth_getBlockByNumber': return dict(number='0x10')
        if method == 'eth_getStorageAt': return hex(10**12)
        if method == 'eth_call': return hex(2**255)
        return hex(500_000)
    ns['rpc'], ns['DELAYS'] = rpc, (0, 3)
    out = ns['rfq_check']('https://p', s, {'NVDAB': dict(t0=100.0, data='0xad43f73d00')},
                           clock=lambda: clock['t'], sleep=lambda delay: clock.__setitem__('t', clock['t'] + delay))
    row = out['symbols']['NVDAB']
    assert row['elapsed_since_quote_response_s']['0'] >= 11
    assert row['last_success_s'] == row['elapsed_since_quote_response_s']['3'] > 3
