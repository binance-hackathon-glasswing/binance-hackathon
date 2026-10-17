"""Offline #44 coverage review. Never approves, installs, signs or contacts services.

Pins establish which local bytes were reviewed, not their provenance or truth.
Owner approval, decoder qualification and all Gate B host checks remain separate.
"""
import argparse
import json
import os
from pathlib import Path
import re

from larp.contracts import ContractError
from larp.execution import Blocked, NATIVE_BNB, USDT
from larp.execution_live.gate_b import address, pinned, read_json
from larp.execution_live.main import validate_config
from larp.marketdata.port import TOKENS
from larp.marketdata.web3 import utc
from larp.signer.policy import EXAMPLE_CAP_BASIS, SigningPolicy
from larp.strategy.profiles import validate_live
from larp.strategy.schema import instant, integer

FILES = {'profile', 'signing_policy', 'execution_config', 'initial_state'}
KEYS = {'schema', 'wallet', 'run_id', 'build_id', 'environment', 'max_age_seconds', 'files', 'quote_artifacts'}
ERRORS = (ContractError, Blocked, OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError)
UINT = re.compile(r'0|[1-9][0-9]{0,77}')
MAX_ARTIFACTS = 256
ROOT = Path(__file__).resolve().parents[2]


def quantity(value, minimum=0):
    if type(value) not in (int, str) or not UINT.fullmatch(str(value)):
        raise ContractError('Invalid review quantity')
    number = int(value)
    if not minimum <= number < 2**256:
        raise ContractError('Review quantity outside uint256')
    return number


def review(inputs, *, now, base_dir):
    if type(inputs) is not dict or set(inputs) != KEYS or inputs['schema'] != 'GateBCapsInputs.v1':
        raise ContractError('GateBCapsInputs.v1 exact fields required')
    wallet = address(inputs['wallet'])
    if (inputs['wallet'] != wallet or type(inputs['run_id']) is not str or not inputs['run_id']
            or type(inputs['build_id']) is not str or not re.fullmatch(r'[0-9a-f]{40}', inputs['build_id'])
            or inputs['environment'] not in ('REHEARSAL', 'FINAL')):
        raise ContractError('Review identity required')
    now = instant(now)
    age = integer(inputs['max_age_seconds'], 1)
    refs = inputs['files']
    artifacts = inputs['quote_artifacts']
    if type(refs) is not dict or set(refs) != FILES:
        raise ContractError('All four pinned review inputs required')
    if type(artifacts) is not list or len(artifacts) > MAX_ARTIFACTS:
        raise ContractError('Bounded quote artifact list required')
    values = {name: pinned(refs[name], base_dir) for name in sorted(FILES)}
    p, policy_value, config, ledger = (values[name] for name in
                                     ('profile', 'signing_policy', 'execution_config', 'initial_state'))
    validate_live(p)
    policy = SigningPolicy.from_config(policy_value)
    validate_config(config)
    mode = 'dev' if inputs['environment'] == 'REHEARSAL' else 'live'
    if (p.get('schema') != 'StrategyProfile.v1' or p.get('mode') != 'LIVE'
            or p['environment'] != inputs['environment'] or config['mode'] != mode
            or config['wallet_address'] != wallet or config['run_id'] != inputs['run_id']
            or config['build_id'] != inputs['build_id']
            or config['strategy_profile_sha256'] != refs['profile']['sha256']
            or ledger['schema'] != 'PortfolioState.v1' or ledger['wallet_id'] != wallet
            or ledger['run_id'] != inputs['run_id'] or ledger['mode'].lower() != mode):
        raise ContractError('Review input identities differ')
    router = address(config['router'])
    decimals = config['token_decimals']
    if (type(decimals) is not dict or set(decimals) != set(TOKENS)
            or any(type(d) is not int or not 0 <= d <= 30 for d in decimals.values())
            or type(ledger['positions']) is not dict or set(ledger['positions']) != set(TOKENS)
            or type(ledger['bnb_decimals']) is not int or ledger['bnb_decimals'] != 18):
        raise ContractError('Complete token metadata and exact native units required')
    for field in ('cash_units', 'bnb_units'):
        integer(ledger[field])
    blockers, checks = [], []

    def check(name, required, cap):
        covered = required <= cap
        checks.append(dict(check=name, required=str(required), cap=str(cap), covered=covered))
        if not covered:
            blockers.append(name)

    if policy.allowed_spenders != {router} or policy.allowed_tokens != {USDT, NATIVE_BNB, *TOKENS.values()}:
        blockers.append('TOKEN_OR_SPENDER_SCOPE')
    if ledger.get('reservations') != {}:
        blockers.append('IN_FLIGHT_PORTFOLIO_REVIEW')
    # Portfolio cash is micro-USDT; the signer's USDT inputs are raw 18-decimal units.
    required_cash = max(p['per_trade_cap_units'], p['gas_top_up_cash_units']) * 10**12
    check('FULL_POSITION_AND_TOPUP_USDT', required_cash, policy.max_input_units.get(USDT, 0))
    for symbol, token in sorted(TOKENS.items()):
        holding = ledger['positions'][symbol]
        if type(holding['decimals']) is not int or holding['decimals'] != decimals[symbol]:
            raise ContractError('Holding/token metadata scales differ')
        check('FULL_HOLDING_' + symbol, integer(holding['units']), policy.max_input_units.get(token, 0))
    gas = integer(config['max_gas'], 1)
    price = integer(config['max_gas_price'], 1)
    check('CONFIGURED_FEE_ENVELOPE_WEI', gas * price, policy.max_fee_wei)
    integer(config['gas_budget'], 1)
    # The profile validator proves that per_trade_cap includes a full target position plus reserve.
    summary = p['quote_cost_summary']
    if summary['bnb_decimals'] != ledger['bnb_decimals']:
        raise ContractError('Profile and ledger native accounting scales differ')
    scale = 10**integer(summary['bnb_decimals'], 1)
    for symbol, row in sorted(summary['symbols'].items()):
        for step in ('approve', 'swap'):
            check('MEASURED_' + step.upper() + '_FEE_' + symbol,
                  _scaled_up(row[step + '_gas_bnb_units'], scale), policy.max_fee_wei)

    coverage, hashes = set(), []
    by_address = {token: symbol for symbol, token in TOKENS.items()}
    for ref in artifacts:
        try:
            record = pinned(ref, base_dir)
            sha = ref['sha256']
            if sha in hashes:
                raise ContractError('Duplicate quote artifact')
            hashes.append(sha)
            response, params = record['response'], record['params']
            elapsed = (now - instant(record['requested_at'])).total_seconds()
            if (record['schema'] != 'Web3Observation.v1' or record['source_id'] != 'BINANCE_WEB3'
                    or record['endpoint'] != 'aggregator/quote-and-swap' or record['outcome'] != 'ok'
                    or type(record['http_status']) is not int or record['http_status'] != 200
                    or type(response['code']) is not int or response['code'] != 0
                    or type(params['binanceChainId']) not in (int, str) or str(params['binanceChainId']) != '56'
                    or address(params['userWalletAddress']) != wallet or not 0 <= elapsed <= age):
                raise ContractError('Quote identity, success or freshness differs')
            data = response['data']
            if type(data) is list and len(data) == 1:
                data = data[0]
            tx = data['tx']
            pay, receive = address(params['fromTokenAddress']), address(params['toTokenAddress'])
            if (data.get('executionMode') != 'SWAP' or data.get('rfq') is not None
                    or address(tx['to']) != router or quantity(tx['value']) != 0):
                raise ContractError('Unsupported quote route')
            if pay == USDT and receive in by_address:
                pair = by_address[receive] + ':BUY'
            elif receive == USDT and pay in by_address:
                pair = by_address[pay] + ':SELL'
            elif pay == USDT and receive == NATIVE_BNB:
                pair = 'BNB:BUY'
            else:
                raise ContractError('Unsupported quote pair')
            amount = quantity(params['amount'], 1)
            quantity(tx['minReceiveAmount'], 1)
            fee = quantity(tx['gas'], 1) * quantity(tx['gasPrice'], 1)
            check('QUOTE_INPUT_' + sha, amount, policy.max_input_units.get(pay, 0))
            check('QUOTE_FEE_' + sha, fee, policy.max_fee_wei)
            if quantity(tx['gas'], 1) > gas or quantity(tx['gasPrice'], 1) > price:
                blockers.append('QUOTE_EXCEEDS_EXECUTION_GAS_LIMITS')
            coverage.add(pair)
        except ERRORS:
            blockers.append('QUOTE_ARTIFACT_REFUSED')
    missing = sorted(({s + ':' + side for s in TOKENS for side in ('BUY', 'SELL')} | {'BNB:BUY'}) - coverage)
    if missing:
        blockers.append('QUOTE_COVERAGE_INCOMPLETE')
    numeric_status = 'BLOCKED' if blockers else 'COVERED'
    if policy.cap_basis == EXAMPLE_CAP_BASIS:
        blockers.append('POLICY_APPROVAL_REQUIRED')
    blockers.append('OWNER_REVIEW_REQUIRED')
    return dict(schema='GateBSignerCapsReview.v1', status='BLOCKED', numeric_status=numeric_status,
                signing_enabled=False, ready_to_install=False, build_id=inputs['build_id'],
                run_id=inputs['run_id'], wallet=wallet, environment=inputs['environment'],
                blockers=sorted(set(blockers)), missing_quote_coverage=missing, checks=checks,
                evidence_hashes={name: refs[name]['sha256'] for name in sorted(FILES)},
                quote_artifact_hashes=hashes,
                scope='LOCAL_NUMERIC_COVERAGE_ONLY_NOT_SOURCE_OR_HOST_QUALIFICATION')


def _scaled_up(units, scale):
    # No float conversion: a sub-wei measured amount rounds upward for this cap comparison only.
    return (units * 10**18 + scale - 1) // scale


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--now', default=None)
    args = parser.parse_args(argv)
    try:
        if args.output.resolve() == ROOT or ROOT in args.output.resolve().parents:
            raise ContractError('Cap review output must be outside the checkout')
        _, inputs = read_json(args.inputs)
        result = review(inputs, now=args.now or utc(), base_dir=args.inputs.resolve().parent)
        raw = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
    except ERRORS:
        print(json.dumps(dict(status='CAPS_REVIEW_REFUSED', signing_enabled=False)))
        return 4
    print(json.dumps(dict(status=result['status'], numeric_status=result['numeric_status'],
                          blockers=result['blockers'], signing_enabled=False)))
    return 2  # This tool never reports Gate B acceptance, even with numeric coverage.


if __name__ == '__main__':
    raise SystemExit(main())
