"""RP01 fresh local read-only quotes/preflight; no signer, AWS, DB or submission capability."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

from larp.contracts import ContractError, reflects_secret
from larp.execution import Payload, USDT
from larp.execution_live.chain import Rpc, quantity
from larp.execution_live.untrusted_router import check, load_policy
from larp.marketdata.port import MarketPort, TOKENS, integer
from larp.marketdata.web3 import Artifacts, Web3Client, credentials, single, utc
from larp.strategy.profiles import validate_live

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'docs/build/evidence/untrusted-router-policy-ld03-20261020.json'
POLICY_SHA = '05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5'
SOURCES = ('BSC_BNBCHAIN_PUBLIC', 'BSC_NODEREAL_PUBLIC')


class QuoteOnlyClient(Web3Client):
    endpoints = frozenset({('GET', 'market/rwa/tokens'), ('GET', 'aggregator/quote-and-swap')})


class BoundedRpc(Rpc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.read_count = 0

    def call(self, method, params):
        self.read_count += 1
        if self.read_count > 125:
            raise ContractError('Bounded read budget exceeded')
        return super().call(method, params)


def public_bytes(report, forbidden):
    raw = (json.dumps(report, sort_keys=True, indent=2) + '\n').encode()
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, item in value.items():
                yield from strings(key)
                yield from strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from strings(item)
    private = [v.lower() for v in forbidden if v]
    if (reflects_secret(raw.lower(), private)
            or any(reflects_secret(v.lower().encode(), private) for v in strings(report))):
        raise ContractError('Public report privacy refusal')
    return raw


def run(args):
    target = args.out.absolute()
    if target.resolve() == ROOT or ROOT in target.resolve().parents:
        raise ContractError('Private output must be outside checkout')
    profile_raw = args.profile.read_bytes()
    p = json.loads(profile_raw)
    validate_live(p)
    if p['environment'] != 'REHEARSAL' or p['baseline'] != 'EQUAL_WEIGHT' or not p.get('initial_gas_only'):
        raise ContractError('This probe only measures the rehearsal fallback candidate')
    settings = json.loads(args.providers.read_bytes())
    providers = settings['balance_rpc_providers']
    if len(providers) != 2 or tuple(row['source_id'] for row in providers) != SOURCES:
        raise ContractError('Selected provider order differs')
    selected = credentials(args.env_file, environ={})  # excludes wallet keys and logging secrets
    wallet = selected.get('AI_SEEDS_ADDRESS', '').lower()
    forbidden = [*selected.values(), wallet, *[row['url'] for row in providers]]
    target.mkdir(mode=0o700)  # never overwrite an earlier measurement
    artifacts = Artifacts(target / 'web3')
    client = QuoteOnlyClient(selected['BINANCE_API_KEY'], selected['BINANCE_SECRET_KEY'], artifacts=artifacts)
    market = MarketPort(client, wallet, quote_limits=p)
    decoder = load_policy(POLICY, POLICY_SHA)
    rpc_rows = []
    for row in providers:
        rpc = BoundedRpc(row['url'], source_id=row['source_id'], artifacts=Artifacts(target / row['source_id']))
        if quantity(rpc.call('eth_chainId', [])) != 56:
            raise ContractError('Provider chain differs')
        rpc_rows.append((row['source_id'], rpc))
    started = utc()
    metadata = market.metadata()
    rows = []
    for symbol in sorted(TOKENS):
        meta, _ = metadata[symbol]
        if meta['statusInfo']['openState'] is not True:
            raise ContractError('Token not open for candidate measurement')
        decimals = integer(meta['decimals'])
        sell_amount = None
        for side in ('BUY', 'SELL'):
            amount = p['expected_equity_units'] // 5 * 10**12 if side == 'BUY' else sell_amount
            start = time.monotonic()
            observation = market.quote(symbol, side, amount, decimals)
            tx = single(observation)['tx']
            # No derivative/normalized observation is manufactured for the canonical checker.
            payload = Payload(56, wallet, tx['to'].lower(), integer(tx['value']), 0,
                              integer(tx['gas']), integer(tx['gasPrice']), tx['data'])
            economics = decoder.decode(payload)
            pay, receive = ((USDT, TOKENS[symbol]) if side == 'BUY' else (TOKENS[symbol], USDT))
            if (economics.pay_token != pay or economics.receive_token != receive
                    or economics.amount != amount or economics.minimum_output != integer(tx['minReceiveAmount'])):
                raise ContractError('Decoded economics differs from fresh quote request')
            intent = SimpleNamespace(router=decoder.router, wallet=wallet, pay_token=pay, amount=amount)
            preflights = {}
            for source, rpc in rpc_rows:
                try:
                    decoder.bind(rpc).preflight(intent, payload, approved=True)
                    preflights[source] = 'PASS'
                except Exception as error:
                    preflights[source] = dict(status='REFUSED', error_type=type(error).__name__)
            age_ms = int((time.monotonic() - start) * 1000)
            rows.append(dict(symbol=symbol, side=side, observed_at=observation['available_at'],
                             observation_sha256=observation['artifact_sha256'],
                             preflight_end_age_ms=age_ms,
                             within_profile_quote_age=age_ms <= p['quote_age_seconds'] * 1000,
                             preflight=preflights))
            if side == 'BUY':
                sell_amount = integer(single(observation)['routerResult']['toTokenAmount'])
    replay = check(decoder, artifacts.root)
    passed = (replay['status'] == 'PASS' and replay['quotes'] == 10
              and all(row['within_profile_quote_age'] and all(v == 'PASS' for v in row['preflight'].values())
                      for row in rows))
    report = dict(schema='LocalRouterReadOnlyReview.v1', decision_id='IDEA-070 LD03-RP01',
                  status='PASS_LOCAL_READONLY' if passed else 'BLOCKED_LOCAL_READONLY',
                  started_at=started, completed_at=utc(), policy_sha256=POLICY_SHA,
                  profile_sha256=hashlib.sha256(profile_raw).hexdigest(),
                  wallet_fingerprint=hashlib.sha256(wallet.encode()).hexdigest(),
                  buy_size_usdt=p['expected_equity_units'] // 5 // 10**6,
                  sell_size_basis='hypothetical BUY output, not reconciled actual holdings',
                  provider_reads={source: rpc.read_count for source, rpc in rpc_rows},
                  rows=rows, canonical_replay=replay, signing_enabled=False, ready_to_install=False,
                  host_binding_accepted=False, current_full_holdings_checked=False,
                  remaining=['actual selected profile/current full holdings/execution config',
                             'production host/release binding and runtime preflight on every real attempt',
                             'RFQ usability, actual gas/receipt/fee/round ACK at LD19/20'])
    raw = public_bytes(report, forbidden)
    fd = os.open(target / 'report.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
    print(json.dumps(dict(status=report['status'], quotes=replay['quotes'], policy_sha256=POLICY_SHA,
                          report_sha256=hashlib.sha256(raw).hexdigest(), signing_enabled=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('out', 'profile', 'providers', 'env-file'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args)
    except Exception as error:
        print(json.dumps(dict(status='PROBE_REFUSED', error_type=type(error).__name__, signing_enabled=False)))
        return 4
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
