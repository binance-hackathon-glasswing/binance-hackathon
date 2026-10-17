"""Swap decoder pinned to router evidence (IDEA-070; GAP-29, C-OPEN-004).

A swap's calldata decides where the wallet's tokens go, so nothing is signed until a decoder can show, from the bytes
alone, the tokens, input amount, recipient, minimum output and deadline. The router's ABI is not guessed here.
`RouterEvidence.v1` is filled in by a person from the router's verified source (BscScan "Contract" tab) and records:

- the router (the quote's `tx.to`, equal to the approve's `dexContractAddress`) and, for a proxy, its implementation;
- the swap function's canonical signature, whose keccak-256 must give the recorded selector;
- where each economic field sits in the decoded arguments, as a path of tuple indices;
- the address(es) the router uses for native BNB;
- hashes of the verified source and ABI, and who reviewed them;
- source properties the reviewer read, each exactly `true`: the router checks the minimum output against
  the recipient's balance, enforces the deadline, and pulls the input only from the sender. The decoder cannot see
  nested route calls; the additional debit guarantee must cover those calls too: wallet token debits are limited
  to the decoded pay token and amount, with no other wallet asset/approval authority available to the route.

`PinnedRouterDecoder` decodes a swap only from that evidence and binds the result to the bytes: the calldata must
re-encode to exactly the same bytes, so trailing data, dirty padding and non-canonical offsets are refused rather
than ignored. Without evidence the services keep `UnverifiedRouter`, and nothing changes.

    python -m larp.execution_live.router selector --signature 'swap(...)'
    python -m larp.execution_live.router check --evidence FILE --sha256 HEX --artifacts DIR [--out REPORT]

`check` replays recorded quote responses (IDEA-063 capture artifacts, `Web3Observation.v1`) through the decoder,
compares each route with what was asked for and quoted, and checks that tampered copies of each real route are
refused. It reads files only.
"""

import argparse
from dataclasses import replace as replaced
import hashlib
import json
from pathlib import Path
import re
import sys

from eth_abi import decode as abi_decode, encode as abi_encode, is_encodable_type
from eth_abi.exceptions import DecodingError, EncodingError, ParseError
from eth_abi.grammar import BasicType, TupleType, normalize, parse
from eth_utils import keccak

from larp.contracts import ContractError
from .config import evidence_settings
from larp.execution import BSTOCKS, NATIVE_BNB, USDT, Blocked, Payload, SwapEconomics

SCHEMA = 'RouterEvidence.v1'
FIELDS = ('pay_token', 'receive_token', 'amount', 'minimum_output', 'recipient', 'deadline')
ADDRESS_FIELDS = frozenset({'pay_token', 'receive_token', 'recipient'})
GUARANTEES = ('minimum_output_checked_on_recipient_balance', 'deadline_enforced', 'input_pulled_only_from_sender',
              'wallet_debits_limited_to_pay_token_and_amount')
KEYS = frozenset({'schema', 'chain_id', 'router', 'implementation', 'function', 'fields', 'native_sentinels',
                  'source', 'guarantees', 'review'})
SOURCE_KEYS = frozenset({'verified_on', 'url', 'contract_name', 'compiler', 'source_sha256', 'abi_sha256',
                         'retrieved_at'})
REVIEW_KEYS = frozenset({'reviewed_by', 'review_ref'})
_ADDRESS = re.compile(r'0x[0-9a-f]{40}')
_SHA256 = re.compile(r'[0-9a-f]{64}')
_SELECTOR = re.compile(r'0x[0-9a-f]{8}')
_NAME = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
TOKENS = frozenset({USDT}) | BSTOCKS


def selector(signature):
    """The 4-byte function selector of a canonical signature, as 0x-prefixed lowercase hex."""
    return '0x' + keccak(text=signature)[:4].hex()


def _refuse(what):
    raise ContractError('RouterEvidence: ' + what)


def _address(value, what):
    if type(value) is not str or not _ADDRESS.fullmatch(value):
        _refuse(what + ' must be a lowercase 0x address')
    return value


def _text(value, what):
    if type(value) is not str or not value.strip():
        _refuse(what + ' is required')
    return value


def _argument_types(signature):
    """Canonical argument types of `name(types)`; refuses anything a Solidity compiler would not hash."""
    if type(signature) is not str or '(' not in signature or not signature.endswith(')'):
        _refuse('function.signature must be name(types)')
    name, inner = signature.split('(', 1)
    if not _NAME.fullmatch(name) or ' ' in signature:
        _refuse('function.signature must be canonical (no spaces, a plain name)')
    inner = inner[:-1]
    try:
        parsed = parse('(' + inner + ')')
        parsed.validate()
        if not is_encodable_type('(' + inner + ')'):
            _refuse('function.signature contains unsupported ABI types')
        canonical = normalize('(' + inner + ')')
    except (ParseError, ValueError, TypeError):
        _refuse('function.signature does not parse')
    if canonical != '(' + inner + ')':
        _refuse('function.signature must use canonical types (e.g. uint256, not uint)')
    if not isinstance(parsed, TupleType) or parsed.arrlist is not None or not parsed.components:
        _refuse('function.signature needs at least one argument')
    return parsed, [component.to_type_str() for component in parsed.components]


def _leaf(arguments, path, field):
    """The type a field path ends on: only tuple indices, never into an array."""
    if type(path) is not list or not path or any(type(i) is not int or i < 0 for i in path):
        _refuse('fields.' + field + ' must be a non-empty list of argument/tuple indices')
    node = arguments
    for depth, index in enumerate(path):
        if not isinstance(node, TupleType) or node.arrlist is not None:
            _refuse('fields.' + field + ' passes through a non-tuple at depth ' + str(depth))
        if index >= len(node.components):
            _refuse('fields.' + field + ' index out of range at depth ' + str(depth))
        node = node.components[index]
    if not isinstance(node, BasicType) or node.arrlist is not None:
        _refuse('fields.' + field + ' must end on a basic type')
    if field in ADDRESS_FIELDS and node.base != 'address':
        _refuse('fields.' + field + ' must be an address')
    if field not in ADDRESS_FIELDS and node.base != 'uint':
        _refuse('fields.' + field + ' must be a uintN')
    return node


def validate_evidence(value):
    """A checked `RouterEvidence.v1` document; ContractError otherwise. Pure: no file or network access."""
    if type(value) is not dict or set(value) != KEYS:
        _refuse('needs exactly: ' + ','.join(sorted(KEYS)))
    if value['schema'] != SCHEMA:
        _refuse('schema must be ' + SCHEMA)
    if type(value['chain_id']) is not int or value['chain_id'] != 56:
        _refuse('chain_id must be 56')
    router = _address(value['router'], 'router')
    if router in TOKENS or router == NATIVE_BNB:
        _refuse('router cannot be a token')
    if value['implementation'] is not None:
        _address(value['implementation'], 'implementation')
    function = value['function']
    if type(function) is not dict or set(function) != {'signature', 'selector'}:
        _refuse('function needs exactly: selector,signature')
    arguments, types = _argument_types(function['signature'])
    if type(function['selector']) is not str or not _SELECTOR.fullmatch(function['selector']):
        _refuse('function.selector must be 0x + 8 lowercase hex')
    if selector(function['signature']) != function['selector']:
        _refuse('function.selector is not keccak-256 of function.signature')
    fields = value['fields']
    if type(fields) is not dict or set(fields) != set(FIELDS):
        _refuse('fields needs exactly: ' + ','.join(FIELDS))
    for field in FIELDS:
        _leaf(arguments, fields[field], field)
    sentinels = value['native_sentinels']
    if type(sentinels) is not list or len(set(map(str, sentinels))) != len(sentinels):
        _refuse('native_sentinels must be a list without repeats')
    for sentinel in sentinels:
        if _address(sentinel, 'native_sentinels entry') in TOKENS:
            _refuse('a native sentinel cannot be a token')
    source = value['source']
    if type(source) is not dict or set(source) != SOURCE_KEYS:
        _refuse('source needs exactly: ' + ','.join(sorted(SOURCE_KEYS)))
    for key in ('verified_on', 'url', 'contract_name', 'compiler', 'retrieved_at'):
        _text(source[key], 'source.' + key)
    for key in ('source_sha256', 'abi_sha256'):
        if type(source[key]) is not str or not _SHA256.fullmatch(source[key]):
            _refuse('source.' + key + ' must be a lowercase SHA-256')
    guarantees = value['guarantees']
    if type(guarantees) is not dict or set(guarantees) != set(GUARANTEES):
        _refuse('guarantees needs exactly: ' + ','.join(GUARANTEES))
    for key in GUARANTEES:
        if guarantees[key] is not True:
            _refuse('guarantees.' + key + ' must be true, read in the verified source')
    review = value['review']
    if type(review) is not dict or set(review) != REVIEW_KEYS:
        _refuse('review needs exactly: review_ref,reviewed_by')
    for key in REVIEW_KEYS:
        _text(review[key], 'review.' + key)
    return dict(value, _types=types)


def load_evidence(path, sha256):
    """Evidence pinned by its file hash (as the strategy profile is); ContractError on any mismatch."""
    if type(sha256) is not str or not _SHA256.fullmatch(sha256):
        raise ContractError('router_evidence_sha256 must be a lowercase SHA-256')
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ContractError('Router evidence differs from its pinned hash')
    try:
        value = json.loads(raw)
    except ValueError:
        raise ContractError('Router evidence is not JSON') from None
    return PinnedRouterDecoder(value, evidence_sha256=sha256)




class PinnedRouterDecoder:
    """`Decoder` port built from checked router evidence. Decodes only the evidenced function, bound to its bytes."""
    mode = 'verified'

    def __init__(self, evidence, *, evidence_sha256=None):
        checked = validate_evidence(evidence)
        self.router = checked['router']
        self.selector = checked['function']['selector']
        self.types = checked['_types']
        self.fields = {field: tuple(checked['fields'][field]) for field in FIELDS}
        self.native = frozenset(checked['native_sentinels'])
        self.evidence_sha256 = evidence_sha256

    def _field(self, values, field):
        value = values
        for index in self.fields[field]:
            value = value[index]
        return value

    def _token(self, value):
        value = value.lower()
        return NATIVE_BNB if value in self.native else value

    def decode(self, payload):
        if not isinstance(payload, Payload) or payload.to != self.router:
            raise Blocked('swap is not addressed to the evidenced router')
        data = payload.data
        if type(data) is not str or not re.fullmatch(r'0x(?:[0-9a-fA-F]{2})+', data):
            raise Blocked('malformed calldata')
        raw = bytes.fromhex(data[2:])
        if '0x' + raw[:4].hex() != self.selector:
            raise Blocked('swap selector differs from the evidenced function')
        body = raw[4:]
        try:
            values = abi_decode(self.types, body, strict=True)
            if abi_encode(self.types, values) != body:
                raise Blocked('swap calldata is not the canonical encoding of its decoded values')
        except (DecodingError, EncodingError, ValueError, TypeError, OverflowError):
            raise Blocked('swap calldata does not decode under the evidenced ABI') from None
        recipient = self._field(values, 'recipient').lower()
        if recipient in self.native:
            raise Blocked('swap recipient is a native sentinel')
        return SwapEconomics(pay_token=self._token(self._field(values, 'pay_token')),
                             receive_token=self._token(self._field(values, 'receive_token')),
                             amount=self._field(values, 'amount'), recipient=recipient,
                             minimum_output=self._field(values, 'minimum_output'),
                             deadline=self._field(values, 'deadline'), native_value=payload.value)


# --- recorded-route check (R8) -------------------------------------------------------------------------------------

def _reencoded(decoder, data, field, change):
    """`data` with one economic field changed and canonically re-encoded: a well-formed but different route."""
    raw = bytes.fromhex(data[2:])
    values = list(abi_decode(decoder.types, raw[4:], strict=True))

    def replace(node, path):
        if not path:
            return change(node)
        items = list(node)
        items[path[0]] = replace(items[path[0]], path[1:])
        return tuple(items)

    path = decoder.fields[field]
    values[path[0]] = replace(values[path[0]], path[1:])
    return '0x' + raw[:4].hex() + abi_encode(decoder.types, values).hex()


def mutations(decoder, payload):
    """Tampered copies of a real route. Each must be refused or decode to different economics."""
    data = payload.data
    other = '0x' + format((int(data[2:10], 16) + 1) % 2**32, '08x') + data[10:]
    original = decoder.decode(payload).recipient
    wrong_address = '0x' + ('de' if original != '0x' + 'de' * 20 else 'ad') * 20
    return {
        'selector': (other, 'refused'),
        'trailing_byte': (data + '00', 'refused'),
        'truncated': (data[:-2], 'refused'),
        'recipient': (_reencoded(decoder, data, 'recipient', lambda _: wrong_address), 'differs'),
        'amount': (_reencoded(decoder, data, 'amount', lambda v: v - 1 if v else 1), 'differs'),
        'minimum_output': (_reencoded(decoder, data, 'minimum_output', lambda v: v - 1 if v else 1), 'differs'),
        'deadline': (_reencoded(decoder, data, 'deadline', lambda v: v - 1 if v else 1), 'differs'),
    }


def _load_artifacts(directory):
    rows, hashes, problems = [], [], []
    for path in sorted(Path(directory).glob('*.json')):
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        hashes.append(sha)
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            problems.append('invalid artifact JSON: ' + sha)
            continue
        if type(value) is dict and value.get('schema') == 'Web3Observation.v1' and value.get('outcome') == 'ok':
            rows.append((sha, value))
    return rows, hashes, problems


def _data(record):
    response = record['response']
    if (record.get('http_status') != 200 or type(response.get('code')) is not int
            or response['code'] != 0):
        raise ValueError('artifact is not a successful API response')
    data = response['data']
    if isinstance(data, list) and len(data) == 1:
        data = data[0]
    if type(data) is not dict:
        raise ValueError('artifact data must be an object')
    return data


def _quantity(value, *, positive=False):
    if type(value) not in (str, int) or not re.fullmatch(r'0|[1-9][0-9]{0,77}', str(value)):
        raise ContractError('canonical uint256 quantity required')
    value = int(value)
    if value >= 2**256 or (positive and value == 0):
        raise ContractError('quantity outside allowed uint256 range')
    return value


def _route_address(value):
    if type(value) is not str:
        raise ContractError('route address required')
    return _address(value.lower(), 'route address')


def _direction(pay, receive):
    if pay == USDT and receive in BSTOCKS:
        return 'BUY'
    if receive == USDT and pay in BSTOCKS:
        return 'SELL'
    if pay == USDT and receive == NATIVE_BNB:
        return 'GAS'
    raise ContractError('unsupported route token pair')


def check_routes(decoder, directory):
    """R8/R13 report: every successful recorded route must match chain56 and supported swap economics."""
    rows, hashes, input_problems = _load_artifacts(directory)
    spenders = set()
    errors = (KeyError, TypeError, ValueError, AttributeError, ContractError, Blocked)
    for sha, record in rows:
        if record.get('endpoint') == 'aggregator/approve-transaction':
            try:
                if str(record['params']['binanceChainId']) != '56':
                    raise ValueError('wrong approval chain')
                spenders.add(_route_address(_data(record)['dexContractAddress']))
            except errors:
                input_problems.append('invalid approval artifact: ' + sha)
    routes, directions = [], set()
    for sha, record in rows:
        if record.get('endpoint') != 'aggregator/quote-and-swap':
            continue
        result = dict(artifact_sha256=sha, problems=[])
        try:
            params, data = record['params'], _data(record)
            if str(params['binanceChainId']) != '56':
                raise ValueError('wrong quote chain')
            if data.get('executionMode') != 'SWAP' or data.get('rfq') is not None:
                raise ValueError('unsupported quote execution mode')
            tx = data['tx']
            payload = Payload(56, _route_address(params['userWalletAddress']), _route_address(tx['to']),
                              _quantity(tx['value']), 0, _quantity(tx['gas'], positive=True),
                              _quantity(tx['gasPrice'], positive=True), tx['data'])
            economics = decoder.decode(payload)
            expected = dict(pay_token=decoder._token(_route_address(params['fromTokenAddress'])),
                            receive_token=decoder._token(_route_address(params['toTokenAddress'])),
                            amount=str(_quantity(params['amount'], positive=True)), recipient=payload.sender,
                            minimum_output=str(_quantity(tx['minReceiveAmount'], positive=True)))
            decoded = dict(pay_token=economics.pay_token, receive_token=economics.receive_token,
                           amount=str(_quantity(economics.amount, positive=True)), recipient=economics.recipient,
                           minimum_output=str(_quantity(economics.minimum_output, positive=True)))
            _quantity(economics.deadline, positive=True)
            direction = _direction(economics.pay_token, economics.receive_token)
            for key, want in expected.items():
                if decoded[key] != want:
                    result['problems'].append(key + ' decoded ' + decoded[key] + ' but request/quote says ' + want)
            if economics.native_value != 0:
                result['problems'].append('native value is not zero')
            if spenders - {decoder.router}:
                result['problems'].append('an approve names a spender other than the evidenced router')
            for name, (mutated, expect) in mutations(decoder, payload).items():
                try:
                    changed = decoder.decode(replaced(payload, data=mutated))
                except Blocked:
                    continue
                if expect == 'refused' or changed == economics:
                    result['problems'].append('mutation not caught: ' + name)
            directions.add(direction)
            result.update(decoded=decoded, deadline=economics.deadline)
        except errors:
            result['problems'].append('artifact shape, chain, execution mode or swap economics refused')
        routes.append(result)
    if input_problems:
        status = 'FAIL'
    elif not routes:
        status = 'NO_ROUTES'
    elif all(not r['problems'] for r in routes) and {'BUY', 'SELL'} <= directions:
        status = 'PASS'
    else:
        status = 'FAIL'
    return dict(schema='RouterRouteCheck.v1', chain_id=56, status=status, router=decoder.router,
                selector=decoder.selector, evidence_sha256=decoder.evidence_sha256,
                directions=sorted(directions), routes=routes, artifacts_read=hashes, input_problems=input_problems)


def validate_route_report(value, decoder, *, wallet):
    """Validate the pinned check report's contents for this wallet, never just its PASS flag (R14).

    The report remains owner-reviewed evidence, not independent execution authority or a real source audit.
    """
    if (value['schema'] != 'RouterRouteCheck.v1' or value['status'] != 'PASS'
            or type(value['chain_id']) is not int or value['chain_id'] != 56
            or value['evidence_sha256'] != decoder.evidence_sha256 or value['router'] != decoder.router
            or value['selector'] != decoder.selector or value['input_problems'] != []):
        raise Blocked('recorded-route check absent, failing or for other evidence')
    hashes, routes = value['artifacts_read'], value['routes']
    if (type(hashes) is not list or not hashes or any(type(h) is not str or not _SHA256.fullmatch(h) for h in hashes)
            or len(set(hashes)) != len(hashes) or type(routes) is not list or not routes):
        raise Blocked('nonempty route evidence and artifact hashes required')
    directions, route_hashes = set(), set()
    for route in routes:
        sha, decoded = route['artifact_sha256'], route['decoded']
        if (sha not in hashes or sha in route_hashes or route['problems'] != []
                or decoded['recipient'] != wallet):
            raise Blocked('route evidence differs from this wallet or has problems')
        route_hashes.add(sha)
        for field in ('amount', 'minimum_output'):
            _quantity(decoded[field], positive=True)
        _quantity(route['deadline'], positive=True)
        directions.add(_direction(decoded['pay_token'], decoded['receive_token']))
    if value['directions'] != sorted(directions) or not {'BUY', 'SELL'} <= directions:
        raise Blocked('both recorded route directions required')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    commands = parser.add_subparsers(dest='command', required=True)
    sel = commands.add_parser('selector', help='keccak-256 selector of a canonical signature')
    sel.add_argument('--signature', required=True)
    chk = commands.add_parser('check', help='replay recorded quote responses through the pinned decoder')
    chk.add_argument('--evidence', required=True)
    chk.add_argument('--sha256', required=True)
    chk.add_argument('--artifacts', required=True)
    chk.add_argument('--out')
    args = parser.parse_args(argv)
    if args.command == 'selector':
        print(selector(args.signature))
        return 0
    try:
        decoder = load_evidence(args.evidence, args.sha256)
    except (ContractError, OSError) as refused:
        print(json.dumps(dict(status='EVIDENCE_REFUSED', detail=str(refused))))
        return 4
    report = check_routes(decoder, args.artifacts)
    text = json.dumps(report, sort_keys=True, indent=2)
    if args.out:
        Path(args.out).write_text(text + '\n')
    print(json.dumps(dict(status=report['status'], routes=len(report['routes']),
                          failed=sum(1 for r in report['routes'] if r['problems']),
                          directions=report['directions'])))
    return 0 if report['status'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
