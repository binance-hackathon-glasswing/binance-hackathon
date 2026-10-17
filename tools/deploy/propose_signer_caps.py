"""Build unapproved signer-cap candidates from a public, historical price reference.

Offline only: no service config, wallet, network, signing or installation. CP-01 / #44.
The output is a proposal wrapper, not SignerService.v1. Its embedded policies retain
EXAMPLE_PENDING_TEAM_DECISION until the owners approve and bind an actual configuration.
"""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from larp.contracts import ContractError
from larp.execution import USDT, NATIVE_BNB
from larp.marketdata.port import TOKENS
from larp.signer.policy import SigningPolicy, EXAMPLE_CAP_BASIS

ROUTER = '0xb44446b0c8e56988c34f7ff73ae904982b5fdda5'
FEE_WEI = 200_000_000_000_000
REFERENCE_KEYS = {'schema', 'chain_id', 'price_unit', 'reference_scope', 'observed_at',
                  'artifact_sha256', 'response_sha256', 'tokens'}
SHA256 = re.compile(r'[0-9a-f]{64}')
PRICE = re.compile(r'[0-9]{1,30}(?:\.[0-9]{1,40})?')


def reference(value):
    """Strict public fields only; provenance identifies retained bytes, not source verification."""
    def refuse():
        raise ContractError('Invalid public signer-cap reference')

    if type(value) is not dict or set(value) != REFERENCE_KEYS:
        refuse()
    if (value['schema'] != 'SignerCapsReference.v1' or type(value['chain_id']) is not int
            or value['chain_id'] != 56 or value['price_unit'] != 'USDT_PER_WHOLE_TOKEN'
            or value['reference_scope'] != 'HISTORICAL_REFERENCE_ONLY'):
        refuse()
    for field in ('artifact_sha256', 'response_sha256'):
        if type(value[field]) is not str or not SHA256.fullmatch(value[field]):
            refuse()
    stamp = value['observed_at']
    if type(stamp) is not str or not stamp.endswith('Z'):
        refuse()
    try:
        if datetime.fromisoformat(stamp[:-1] + '+00:00').utcoffset() != timezone.utc.utcoffset(None):
            refuse()
    except ValueError:
        refuse()
    rows = value['tokens']
    if type(rows) is not dict or set(rows) != set(TOKENS):
        refuse()
    for symbol, address in TOKENS.items():
        row = rows[symbol]
        if (type(row) is not dict or set(row) != {'address', 'decimals', 'price_usdt'}
                or row['address'] != address or type(row['decimals']) is not int
                or not 1 <= row['decimals'] <= 30 or type(row['price_usdt']) is not str
                or not PRICE.fullmatch(row['price_usdt']) or Fraction(row['price_usdt']) <= 0):
            refuse()
    return value


def build(value):
    value = reference(value)
    candidates = {}
    for mode, cash in (('development', 35), ('final', 70)):
        caps, calculation = {USDT: str(cash * 10**18)}, {}
        for symbol, row in sorted(value['tokens'].items()):
            floor = Fraction(row['price_usdt']) / 2
            units = Fraction(cash * 10**row['decimals'], 1) / floor
            rounded = (units.numerator + units.denominator - 1) // units.denominator
            caps[row['address']] = str(rounded)
            calculation[symbol] = dict(reference_price_usdt=row['price_usdt'], decimals=row['decimals'],
                floor_price_ratio=[str(floor.numerator), str(floor.denominator)],
                max_input_units=str(rounded))
        policy = dict(cap_basis=EXAMPLE_CAP_BASIS, allowed_spenders=[ROUTER],
            allowed_tokens=[USDT, *[TOKENS[s] for s in sorted(TOKENS)], NATIVE_BNB],
            max_input_units=caps, max_fee_wei=str(FEE_WEI))
        SigningPolicy.from_config(policy)  # actual consumer: universe, finite caps, types and units
        candidates[mode] = dict(usdt_input_cap=str(cash), signing_policy=policy, calculation=calculation)
    return dict(schema='SignerCapsProposal.v1', status='UNAPPROVED_HISTORICAL_CANDIDATES',
        ready_to_install=False, decision_ref='IDEA-049-C CP-01 / #44',
        source_reference=value, floor_fraction=[1, 2], max_fee_bnb='0.0002',
        limitations=['CURRENT_PROFILE_AND_HOLDINGS_REVIEW_REQUIRED', 'PRICE_FLOOR_NOT_GUARANTEED',
                     'SPLIT_AND_ADJUSTMENT_REVIEW_REQUIRED', 'PER_TRANSACTION_NOT_CUMULATIVE_CAP',
                     'ROUTER_SOURCE_AND_OWNER_APPROVAL_REQUIRED'], candidates=candidates)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='new file; never overwrites')
    args = parser.parse_args(argv)
    try:
        report = build(json.loads(args.reference.read_bytes()))
        raw = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
    except (ContractError, OSError, ValueError):
        print(json.dumps(dict(status='CAPS_PROPOSAL_REFUSED')))
        return 4
    print(json.dumps(dict(status=report['status'], ready_to_install=False)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
