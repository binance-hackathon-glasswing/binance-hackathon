"""Offline checks for the KG-DEC-01-H host script (IDEA-070): outcome classification and pre-truncation filtering."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'docs/build/ops/ld02-20261020/presign-check.sh'
WALLET = '0x' + 'ab' * 20


def load():
    source = SCRIPT.read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    ns = {'__name__': 'offline_presign'}
    exec(compile(source, str(SCRIPT), 'exec'), ns)
    return ns


def test_estimate_outcomes():
    ns = load()
    from larp.marketdata.web3 import Unavailable

    class Client:
        def __init__(self, answer):
            self.answer = answer

        def request(self, method, endpoint, params):
            assert (method, endpoint) == ('POST', 'pre-transaction/gas-limit')
            assert params['evmTx'] == {'from': WALLET, 'to': '0x1', 'data': '0xab', 'value': '0'}
            if isinstance(self.answer, Exception):
                raise self.answer
            return {'response': {'data': [{'gasLimit': self.answer}]}}
    est = lambda answer: ns['estimate'](Client(answer), WALLET, '0x1', '0xab')
    assert est('55243') == {'outcome': 'ESTIMATE', 'gas_limit': 55243}
    assert est('0') == {'outcome': 'NON_POSITIVE', 'gas_limit': 0}
    assert est(Unavailable('execution_reverted'))['outcome'] == 'REFUSED'
    assert est(None)['outcome'] == 'REFUSED_SCHEMA'


def test_private_values_are_filtered_before_shortening():
    ns = load()
    ns['FORBIDDEN'][:] = [WALLET]
    long_reason = 'x' * 110 + WALLET  # truncation alone would cut the address and hide it from a later scan
    assert ns['plain'](long_reason) == 'FILTERED'
    assert ns['plain']('see https://x') == 'FILTERED'
    assert ns['plain']('execution reverted') == 'execution reverted'
