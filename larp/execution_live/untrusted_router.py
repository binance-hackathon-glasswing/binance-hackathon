"""Swap checks for a router whose source is unavailable (IDEA-070 B02-U; DEV-23).

The kit's router (`0xb44446…fdda5`, a diamond proxy) and its swap facet publish no verified source, so
`RouterEvidence.v1` cannot be written and `PinnedRouterDecoder` cannot be built. The team decided on 2026-10-19 to
treat the router as untrusted, retaining input checks while accepting unverified contract behavior. This module supplies:

- `UntrustedRouterDecoder.decode`: a byte-exact check of the calldata layout every recorded quote has used (IDEA-070
  B02-U), returning the pay token, receive token, amount, minimum output and inner deadline that the layout carries.
  The router's own enforcement of those fields is not proven, and the wallet address is not in the calldata at all,
  so the recipient is returned as `None` (unverified). Nothing here claims the four RouterEvidence guarantees.
- `preflight` (primary only; the signer has no internet route): at a numeric block, the facet slot for the swap
  selector holds the pinned facet, the router's and facet's code hashes equal the pinned ones, the router's
  allowance from the wallet is at most the amount for the pay token and zero for every other pinned token.

Exact approves, signer input/fee caps and settlement checks constrain submitted authority and detect anomalous
outcomes. They do not prove a maximum loss or recover lost funds: recipient, nested-call debit and on-chain
deadline enforcement remain unverified. An anomalous unsettled fill withholds further signing (DEV-23).

    python -m larp.execution_live.untrusted_router observe --rpc-url URL --artifacts DIR --out NEW_FILE
    python -m larp.execution_live.untrusted_router check --policy FILE --sha256 HEX --artifacts DIR

`observe` (operator, on primary) drafts the policy from live public chain state and the recorded quotes: code hashes,
the facet the selector dispatches to, and the fixed head words all quotes share. Its review fields say
REVIEW_REQUIRED, which `validate_policy` refuses until a named reviewer fills them in.
"""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import sys

from eth_utils import keccak

from larp.contracts import ContractError
from larp.execution import BSTOCKS, USDT, Blocked, Payload, SwapEconomics

SCHEMA = 'UntrustedRouterPolicy.v1'
KEYS = frozenset({'schema', 'chain_id', 'router', 'router_codehash', 'selector', 'diamond_storage_base',
                  'facet_slot', 'facet', 'facet_codehash', 'fixed_words', 'inner_selector', 'deviation', 'review'})
TOKENS = frozenset({USDT}) | BSTOCKS
REVIEW_REQUIRED = 'REVIEW_REQUIRED'
# The kit router's diamond: selector -> facet mapping base, read from its runtime code (IDEA-070 B02-U).
ROUTER = '0xb44446b0c8e56988c34f7ff73ae904982b5fdda5'
DIAMOND_STORAGE_BASE = '0x5e12654f390e4153c4f63b3dfcc122cf7876a5cdfb496dccf7284c10517a35c5'
SWAP_SELECTOR, INNER_SELECTOR = '0xad43f73d', '0x47ee97ff'
ALLOWANCE_CALL = '0xdd62ed3e'  # = chain.ALLOWANCE_CALL; not imported, so the signer never loads the RPC client
# Outer head words (index -> meaning), as all 15 recorded quotes lay them out (IDEA-070 B02-U).
PAY, AMOUNT, RECEIVE, MINIMUM, QUOTED, BLOB_OFFSET, BLOB_LENGTH = 3, 4, 5, 6, 8, 9, 10
HEAD_WORDS = 11
# Inner call words, after its 4-byte selector.
INNER_PAY, INNER_RECEIVE, INNER_AMOUNT, INNER_MINIMUM, INNER_DEADLINE = 6, 7, 8, 9, 10
INNER_WORDS = 11
_ADDRESS = re.compile(r'0x[0-9a-f]{40}')
_WORD = re.compile(r'0x[0-9a-f]{64}')
_SELECTOR = re.compile(r'0x[0-9a-f]{8}')


def _refuse(what):
    raise ContractError('UntrustedRouterPolicy: ' + what)


def _address(value, what):
    if type(value) is not str or not _ADDRESS.fullmatch(value):
        _refuse(what + ' must be a lowercase 0x address')
    return value


def _word(value, what):
    if type(value) is not str or not _WORD.fullmatch(value):
        _refuse(what + ' must be 0x + 64 lowercase hex')
    return value


def selector_slot(selector, base):
    """The diamond's storage slot for a selector: keccak256(bytes32(selector) ‖ base), as the router computes it."""
    return '0x' + keccak(bytes.fromhex(selector[2:]) + bytes(28) + bytes.fromhex(base[2:])).hex()


def validate_policy(value):
    """A checked `UntrustedRouterPolicy.v1`; ContractError otherwise. Pure: no file or network access."""
    if type(value) is not dict or set(value) != KEYS:
        _refuse('needs exactly: ' + ','.join(sorted(KEYS)))
    if value['schema'] != SCHEMA:
        _refuse('schema must be ' + SCHEMA)
    if type(value['chain_id']) is not int or value['chain_id'] != 56:
        _refuse('chain_id must be 56')
    router, facet = _address(value['router'], 'router'), _address(value['facet'], 'facet')
    if router in TOKENS or facet in TOKENS or router == facet:
        _refuse('router and facet must be distinct non-token contracts')
    for key in ('router_codehash', 'facet_codehash', 'diamond_storage_base', 'facet_slot'):
        _word(value[key], key)
    for key in ('selector', 'inner_selector'):
        if type(value[key]) is not str or not _SELECTOR.fullmatch(value[key]):
            _refuse(key + ' must be 0x + 8 lowercase hex')
    if selector_slot(value['selector'], value['diamond_storage_base']) != value['facet_slot']:
        _refuse('facet_slot is not the diamond slot of the selector')
    fixed = value['fixed_words']
    if type(fixed) is not dict or not fixed:
        _refuse('fixed_words must map head word indices to words')
    for key, word in fixed.items():
        if not re.fullmatch(r'[0-9]|10', str(key)) or int(key) in (PAY, AMOUNT, RECEIVE, MINIMUM, QUOTED, BLOB_LENGTH):
            _refuse('fixed_words may pin only non-economic head words (0-10)')
        _word(word, 'fixed_words.' + key)
    if fixed.get(str(BLOB_OFFSET)) != '0x' + format(32 * (BLOB_OFFSET + 1), '064x'):
        _refuse('fixed_words must pin the inner-call offset word')
    if type(value['deviation']) is not str or not re.fullmatch(r'DEV-[0-9]{2}', value['deviation']):
        _refuse('deviation must name the deviations-register row')
    review = value['review']
    if (type(review) is not dict or set(review) != {'reviewed_by', 'review_ref'}
            or any(type(v) is not str or not v.strip() or v.strip() == REVIEW_REQUIRED for v in review.values())):
        _refuse('review needs reviewed_by and review_ref')
    return value


def load_policy(path, sha256):
    """The policy pinned by its file hash; ContractError on any mismatch."""
    if type(sha256) is not str or not re.fullmatch(r'[0-9a-f]{64}', sha256):
        raise ContractError('untrusted_router_policy_sha256 must be a lowercase SHA-256')
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ContractError('Untrusted router policy differs from its pinned hash')
    try:
        value = json.loads(raw)
    except ValueError:
        raise ContractError('Untrusted router policy is not JSON') from None
    return UntrustedRouterDecoder(value, policy_sha256=sha256)


def _int(raw, i):
    return int.from_bytes(raw[32 * i:32 * i + 32], 'big')


def _token(word):
    if word >= 2**160:
        raise Blocked('non-canonical address word in swap calldata')
    token = '0x' + format(word, '040x')
    if token not in TOKENS:
        raise Blocked('swap token outside USDT and the eligible bStocks')
    return token


class UntrustedRouterDecoder:
    """`Decoder` port for the untrusted-router mode. `rpc` is set only on primary (`bind`); the signer decodes
    offline and never calls `preflight`."""
    mode = 'untrusted'

    def __init__(self, policy, *, policy_sha256=None, rpc=None):
        checked = validate_policy(policy)
        self.router, self.facet = checked['router'], checked['facet']
        self.selector, self.inner_selector = checked['selector'], checked['inner_selector']
        self.slot = checked['facet_slot']
        self.router_codehash, self.facet_codehash = checked['router_codehash'], checked['facet_codehash']
        self.fixed = {int(k): int(v, 16) for k, v in checked['fixed_words'].items()}
        self.deviation = checked['deviation']
        self.policy_sha256, self.rpc = policy_sha256, rpc

    def bind(self, rpc):
        if getattr(rpc, 'mode', None) != 'live' or not callable(getattr(rpc, 'call', None)):
            raise Blocked('a live RPC is required for untrusted-router preflight')
        self.rpc = rpc
        return self

    def decode(self, payload):
        if not isinstance(payload, Payload) or payload.to != self.router:
            raise Blocked('swap is not addressed to the pinned router')
        data = payload.data
        if type(data) is not str or not re.fullmatch(r'0x(?:[0-9a-fA-F]{2})+', data):
            raise Blocked('malformed calldata')
        raw = bytes.fromhex(data[2:])
        if '0x' + raw[:4].hex() != self.selector:
            raise Blocked('swap selector differs from the pinned function')
        body = raw[4:]
        if len(body) % 32 or len(body) < 32 * HEAD_WORDS:
            raise Blocked('swap calldata is not word-aligned or too short')
        if any(_int(body, i) != word for i, word in self.fixed.items()):
            raise Blocked('swap calldata differs from a pinned head word')
        start, length = 32 * HEAD_WORDS, _int(body, BLOB_LENGTH)
        padded = start + -(-length // 32) * 32
        if padded != len(body) or any(body[start + length:]):
            raise Blocked('inner call length or padding is not canonical')
        inner = body[start:start + length]
        # An ABI call is a selector and whole words, so a length that borrows padding bytes is refused.
        if (length < 4 + 32 * INNER_WORDS or (length - 4) % 32
                or '0x' + inner[:4].hex() != self.inner_selector):
            raise Blocked('inner call differs from the pinned shape')
        inner = inner[4:]
        pay, receive = _token(_int(body, PAY)), _token(_int(body, RECEIVE))
        amount, minimum = _int(body, AMOUNT), _int(body, MINIMUM)
        deadline = _int(inner, INNER_DEADLINE)
        if (pay == receive or not 0 < amount < 2**255 or not 0 < minimum <= _int(body, QUOTED)
                or _int(inner, INNER_PAY) != _int(body, PAY) or _int(inner, INNER_RECEIVE) != _int(body, RECEIVE)
                or _int(inner, INNER_AMOUNT) != amount or _int(inner, INNER_MINIMUM) < minimum
                or not 0 < deadline < 2**64):
            raise Blocked('outer and inner swap economics disagree')
        return SwapEconomics(pay_token=pay, receive_token=receive, amount=amount, recipient=None,
                             minimum_output=minimum, deadline=deadline, native_value=payload.value)

    def _code_hash(self, contract, block):
        code = self.rpc.call('eth_getCode', [contract, block])
        if type(code) is not str or not re.fullmatch(r'0x(?:[0-9a-fA-F]{2})+', code):
            raise Blocked('contract code missing at the pinned address')
        return '0x' + keccak(bytes.fromhex(code[2:])).hex()

    def _word(self, value):
        if type(value) is not str or not re.fullmatch(r'0x[0-9a-fA-F]{1,64}', value):
            raise Blocked('malformed RPC word')
        return int(value, 16)

    def preflight(self, intent, payload, *, approved=True):
        """Raise Blocked unless the live router state still bounds this swap (B02-U U3). Primary only.

        Before this execution's own approve (`approved=False`) the pay token's allowance is not limited: the approve
        overwrites it. A leftover allowance on any other token (e.g. after a reverted swap) always refuses."""
        if self.rpc is None:
            raise Blocked('untrusted-router preflight needs a bound RPC')
        if intent.router != self.router or payload.to != self.router or payload.value != 0:
            raise Blocked('swap router or native value differs from the pinned router')
        latest = self.rpc.call('eth_getBlockByNumber', ['latest', False])
        if type(latest) is not dict:
            raise Blocked('latest block unavailable')
        block = hex(self._word(latest.get('number')))
        if self._word(self.rpc.call('eth_getStorageAt', [self.router, self.slot, block])) % 2**160 != int(self.facet, 16):
            raise Blocked('router dispatches the swap selector to another facet')
        if (self._code_hash(self.router, block) != self.router_codehash
                or self._code_hash(self.facet, block) != self.facet_codehash):
            raise Blocked('router or facet code differs from the pinned code')
        owner, spender = intent.wallet[2:].rjust(64, '0'), self.router[2:].rjust(64, '0')
        for token in sorted(TOKENS):
            allowance = self._word(self.rpc.call('eth_call', [dict(to=token, data=ALLOWANCE_CALL + owner + spender),
                                                              block]))
            if token == intent.pay_token and not approved:
                continue
            limit = intent.amount if token == intent.pay_token else 0
            if allowance > limit:
                raise Blocked('router allowance exceeds what this swap may take')


# --- recorded-quote check --------------------------------------------------------------------------------------------

def _quotes(directory):
    for path in sorted(Path(directory).glob('*.json')):
        raw = path.read_bytes()
        try:
            value = json.loads(raw)
            data = value['response']['data']
            tx, params = data['tx'], value['params']
        except (ValueError, KeyError, TypeError):
            continue
        if type(tx) is dict and str(tx.get('data', '')).startswith('0x'):
            yield hashlib.sha256(raw).hexdigest(), params, tx


def check(decoder, directory):
    """Replay recorded quotes through `decode` and refuse tampered copies of each (B02-U U1/U2). Reads files only."""
    rows = []
    for sha, params, tx in _quotes(directory):
        payload = Payload(56, params['userWalletAddress'].lower(), str(tx['to']).lower(), int(tx.get('value') or 0),
                          0, 1, 1, tx['data'])
        row = dict(artifact_sha256=sha, status='FAIL')
        try:
            e = decoder.decode(payload)
            row['matches_quote'] = (e.pay_token == params['fromTokenAddress'].lower()
                                    and e.receive_token == params['toTokenAddress'].lower()
                                    and e.amount == int(params['amount'])
                                    and e.minimum_output == int(tx['minReceiveAmount']) and e.recipient is None)
            refused = [name for name, data in mutations(tx['data']).items()
                       if _refuses(decoder, replace(payload, data=data))]
            row['tampered_refused'] = len(refused) == len(mutations(tx['data']))
            row['status'] = 'PASS' if row['matches_quote'] and row['tampered_refused'] else 'FAIL'
        except Blocked as refusal:
            row['refused'] = str(refusal)
        rows.append(row)
    passed = bool(rows) and all(r['status'] == 'PASS' for r in rows)
    return dict(schema='UntrustedRouteCheck.v1', policy_sha256=decoder.policy_sha256, quotes=len(rows),
                status='PASS' if passed else 'FAIL', rows=rows, signing_enabled=False)


def _refuses(decoder, payload):
    try:
        decoder.decode(payload)
    except Blocked:
        return True
    return False


def _set_word(data, index, value, *, inner=False):
    raw = bytearray(bytes.fromhex(data[2:]))
    offset = 4 + 32 * (HEAD_WORDS + index) + 4 if inner else 4 + 32 * index
    raw[offset:offset + 32] = value.to_bytes(32, 'big')
    return '0x' + raw.hex()


def mutations(data):
    """Tampered copies of a recorded quote; every one must be refused."""
    raw = bytes.fromhex(data[2:])
    word = lambda i, inner=False: _int(raw[4 + (32 * HEAD_WORDS + 4 if inner else 0):], i)
    other_selector = '0x' + format((int(data[2:10], 16) + 1) % 2**32, '08x') + data[10:]
    return {
        'selector': other_selector,
        'trailing_byte': data + '00',
        'truncated': data[:-2],
        'fixed_word_2': _set_word(data, 2, word(2) ^ 1),
        'fixed_word_7': _set_word(data, 7, word(7) ^ 1),
        'non_canonical_pay': _set_word(data, PAY, word(PAY) | 1 << 200),
        'blob_offset': _set_word(data, BLOB_OFFSET, word(BLOB_OFFSET) + 32),
        'blob_length': _set_word(data, BLOB_LENGTH, word(BLOB_LENGTH) + 1),
        'inner_selector': data[:2 + 8 + 64 * HEAD_WORDS] + 'ffffffff' + data[2 + 8 + 64 * HEAD_WORDS + 8:],
        'inner_amount': _set_word(data, INNER_AMOUNT, word(INNER_AMOUNT, True) + 1, inner=True),
        'inner_pay': _set_word(data, INNER_PAY, word(INNER_RECEIVE, True), inner=True),
        'inner_minimum_below': _set_word(data, INNER_MINIMUM, word(MINIMUM) - 1, inner=True),
        'outer_amount': _set_word(data, AMOUNT, word(AMOUNT) + 1),
        'outer_receive_native': _set_word(data, RECEIVE, int('ee' * 20, 16)),
        'padding': data[:-2] + '01',
    }


def _json_rpc(url, method, params):
    from urllib.request import Request, urlopen
    if method not in ('eth_getCode', 'eth_getStorageAt', 'eth_getBlockByNumber') or not url.startswith('https://'):
        raise ContractError('observe uses only read-only HTTPS RPC calls')
    body = json.dumps(dict(jsonrpc='2.0', id=1, method=method, params=params)).encode()
    with urlopen(Request(url, data=body, headers={'Content-Type': 'application/json'}), timeout=20) as response:
        reply = json.loads(response.read(2 * 1024 * 1024))
    if type(reply) is not dict or 'result' not in reply or 'error' in reply:
        raise ContractError('RPC refused ' + method)
    return reply['result']


def observe(rpc_url, directory):
    """(draft policy, block, quote count) from live state at one block and the recorded quotes' shared head words.
    The draft is never reviewed: its review fields hold REVIEW_REQUIRED."""
    block = _json_rpc(rpc_url, 'eth_getBlockByNumber', ['latest', False])['number']
    slot = selector_slot(SWAP_SELECTOR, DIAMOND_STORAGE_BASE)
    facet = '0x' + format(int(_json_rpc(rpc_url, 'eth_getStorageAt', [ROUTER, slot, block]), 16) % 2**160, '040x')
    code = {c: _json_rpc(rpc_url, 'eth_getCode', [c, block]) for c in (ROUTER, facet)}
    if any(len(v) <= 2 for v in code.values()):
        raise ContractError('router or facet has no code at the observed block')
    heads = [bytes.fromhex(tx['data'][10:10 + 64 * HEAD_WORDS]) for _, _, tx in _quotes(directory)
             if tx['data'].startswith(SWAP_SELECTOR)]
    if not heads:
        raise ContractError('no recorded swap quotes')
    fixed = {str(i): '0x' + heads[0][32 * i:32 * i + 32].hex() for i in range(HEAD_WORDS)
             if i not in (PAY, AMOUNT, RECEIVE, MINIMUM, QUOTED, BLOB_LENGTH)
             and all(h[32 * i:32 * i + 32] == heads[0][32 * i:32 * i + 32] for h in heads)}
    return dict(schema=SCHEMA, chain_id=56, router=ROUTER,
                router_codehash='0x' + keccak(bytes.fromhex(code[ROUTER][2:])).hex(),
                selector=SWAP_SELECTOR, diamond_storage_base=DIAMOND_STORAGE_BASE, facet_slot=slot, facet=facet,
                facet_codehash='0x' + keccak(bytes.fromhex(code[facet][2:])).hex(), fixed_words=fixed,
                inner_selector=INNER_SELECTOR, deviation='DEV-23',
                review=dict(reviewed_by=REVIEW_REQUIRED, review_ref=REVIEW_REQUIRED)), block, len(heads)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    o = sub.add_parser('observe')
    o.add_argument('--rpc-url', required=True)
    o.add_argument('--artifacts', required=True)
    o.add_argument('--out', required=True)
    c = sub.add_parser('check')
    c.add_argument('--policy', required=True)
    c.add_argument('--sha256', required=True)
    c.add_argument('--artifacts', required=True)
    args = parser.parse_args(argv)
    if args.command == 'observe':
        try:
            draft, block, quotes = observe(args.rpc_url, args.artifacts)
            with open(args.out, 'x', encoding='utf-8') as stream:
                stream.write(json.dumps(draft, indent=2, sort_keys=True) + '\n')
        except (ContractError, OSError, ValueError, KeyError, TypeError) as error:
            print(json.dumps(dict(status='REFUSED', reason=type(error).__name__, signing_enabled=False)))
            return 2
        print(json.dumps(dict(status='DRAFT_REVIEW_REQUIRED', facet=draft['facet'], block=block, quotes=quotes,
                              fixed_words=sorted(draft['fixed_words']), signing_enabled=False)))
        return 0
    try:
        report = check(load_policy(args.policy, args.sha256), args.artifacts)
    except (ContractError, OSError) as error:
        print(json.dumps(dict(status='REFUSED', reason=str(error), signing_enabled=False)))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
