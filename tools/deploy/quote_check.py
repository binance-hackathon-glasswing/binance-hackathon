"""SJ-11-QV01 live read-only quote check (IDEA-088 A1): one real quote through the service's own verifier.

    python -m tools.deploy.quote_check --symbol NVDAB [--side BUY|SELL] [--pay-units N] [--mandatory]
        [--env-file .env] [--rpc-url https://bsc-dataseed.bnbchain.org] [--out NEW_DIR]

One `MarketPort.observe` call for one symbol and side, with the quote verifier built by
`larp.runtime.service.quote_verifier` from the pinned run-3 S1 profile (`6bcf1dfb…`, the port's `quote_limits`), the
LD03 UNTRUSTED router policy (`05759e90…`), the dev wallet and a public read RPC. A BUY defaults to the largest BUY
the planner requests at this profile (`per_trade_cap_units - cost_reserve_units`, 19 USDT); a SELL defaults to the
token units a fresh BUY quote of that size returns, which is hypothetical, not holdings.

Read-only: the Web3 client allows only the four read endpoints the quote path uses; the RPC is the read-only `Rpc`;
there is no signer, AWS, database or submit path, and only the read-only Web3 key pair is loaded from the env file.
Raw responses go to a new private directory outside the checkout. The printed JSON holds public values only and is
scanned for the credentials, RPC URLs, wallet and calldata before printing.

Exit 0 only for VERIFIED_EXECUTABLE; 2 for a refused quote (its exact reason is printed); 4 for a tool or input error.
The result depends on the time: outside the US session a refusal can be legitimate.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from larp.contracts import ContractError
from larp.execution import USDT
from larp.marketdata.port import TOKENS, MarketPort, integer
from larp.marketdata.web3 import Artifacts, Unavailable, Web3Client, credentials, single, utc
from tools.deploy.replay_router_readonly import public_bytes

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / 'docs/build/evidence/s1-rehearsal-profile-20261023/rehearsal-s1-deterministic.json'
PROFILE_SHA = '6bcf1dfbd7f0c29893dd62bf67d9bcf7a04299b1d24a29d7310b6d769f8c1526'
POLICY = ROOT / 'docs/build/evidence/untrusted-router-policy-ld03-20261020.json'
POLICY_SHA = '05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5'
DEV_WALLET = '0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479'
PUBLIC_RPC = 'https://bsc-dataseed.bnbchain.org'  # BSC_BNBCHAIN_PUBLIC, the qualified balance-read provider


class ReadOnlyClient(Web3Client):
    endpoints = frozenset({('GET', 'market/rwa/tokens'), ('GET', 'market/rwa/underlying-market'),
                           ('GET', 'market/rwa/price'), ('GET', 'aggregator/quote-and-swap')})


class Recording:
    """The service's verifier, keeping its last proof for the report. `decoder` is the verifier's own, so the
    port's recipient rule sees exactly what it sees in the service."""

    def __init__(self, verifier):
        self.verifier, self.decoder, self.proof = verifier, verifier.decoder, None

    def __call__(self, raw, request, observation):
        self.proof = self.verifier(raw, request, observation)
        return self.proof


def pinned(path, sha256, what):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ContractError(what + ' differs from its pinned hash')
    return json.loads(raw)


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--symbol', required=True, choices=sorted(TOKENS))
    parser.add_argument('--side', default='BUY', choices=('BUY', 'SELL'))
    parser.add_argument('--pay-units', type=int, help='BUY: USDT at 6 decimals; SELL: token units')
    parser.add_argument('--mandatory', action='store_true', help='validate as a mandatory exit (impact ignored)')
    parser.add_argument('--env-file', type=Path, default=Path('.env'))
    parser.add_argument('--rpc-url', action='append', help='read RPC, tried in order (default: public BNB Chain)')
    parser.add_argument('--out', type=Path, help='new private directory for raw responses (default: a temp dir)')
    return parser.parse_args(argv)


def run(args, *, client=None, rpcs=None, now=utc):
    from larp.execution_live.chain import Rpc
    from larp.risk.planner import _quote_at_cap
    from larp.runtime.service import quote_verifier
    from larp.strategy.schema import instant
    profile = pinned(PROFILE, PROFILE_SHA, 'Strategy profile')
    pinned(POLICY, POLICY_SHA, 'Router policy')
    urls = args.rpc_url or [PUBLIC_RPC]
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix='larp-quote-check-'))
    if out.absolute().resolve() == ROOT or ROOT in out.absolute().resolve().parents:
        raise ContractError('Raw responses must stay outside the checkout')
    out.mkdir(mode=0o700, exist_ok=args.out is None)
    selected = credentials(args.env_file, environ={})  # the Web3 key pair only; never a wallet key
    keys = [selected['BINANCE_API_KEY'], selected['BINANCE_SECRET_KEY']]
    forbidden = [*keys, *urls, DEV_WALLET, DEV_WALLET[2:], selected.get('AI_SEEDS_ADDRESS')]
    client = client or ReadOnlyClient(*keys, artifacts=Artifacts(out / 'web3'))
    if rpcs is None:
        rpcs = [Rpc(url, artifacts=Artifacts(out / 'chain'), source_id='rpc-%d' % i) for i, url in enumerate(urls)]
    for rpc in rpcs:
        if int(rpc.call('eth_chainId', []), 16) != 56:
            raise ContractError('Read RPC is not BNB Smart Chain')
    driver = dict(untrusted_router_policy_file=str(POLICY), untrusted_router_policy_sha256=POLICY_SHA)
    verifier = Recording(quote_verifier(driver, profile, wallet=DEV_WALLET, rpcs=rpcs,
                                        projection=dict(portfolio=dict(bnb_decimals=18))))
    market = MarketPort(client, DEV_WALLET, quote_verifier=verifier, quote_limits=profile,
                        cost_observation=lambda symbol: None)  # no extra cost-probe quotes
    report = dict(schema='QuoteCheck.v1', decision_id='IDEA-088 A1', symbol=args.symbol, side=args.side,
                  profile_sha256=PROFILE_SHA, policy_sha256=POLICY_SHA, started_at=now(), signing_enabled=False)
    try:
        decimals = integer(market.metadata()[args.symbol][0]['decimals'])
        if args.side == 'BUY':
            pay = args.pay_units or profile['per_trade_cap_units'] - profile['cost_reserve_units']
        elif args.pay_units:
            pay, report['sell_amount_basis'] = args.pay_units, 'GIVEN'
        else:
            cash = (profile['per_trade_cap_units'] - profile['cost_reserve_units']) * 10**12
            pay = integer(single(market.quote(args.symbol, 'BUY', cash, decimals))['routerResult']['toTokenAmount'])
            report['sell_amount_basis'] = 'HYPOTHETICAL_BUY_OUTPUT'
        request = dict(schema='MarketRequest.v1', symbol=args.symbol, side=args.side, amount_kind='EXACT_IN',
                       pay_asset='USDT' if args.side == 'BUY' else args.symbol, pay_units=pay,
                       pay_decimals=6 if args.side == 'BUY' else decimals, mandatory=args.mandatory)
        report['pay_units'] = pay
        observation = market.observe(request)
    except Unavailable as error:
        report.update(status='REFUSED', reason=str(error), quote_status=None)
        return 2, public_bytes(report, forbidden)
    report.update(quote_status=observation['quote_status'], token_open=observation['token_open'],
                  underlying_open=observation['underlying_open'])
    measured = observation.get('quote_measurement') or {}
    report['impact_bps'] = measured.get('impact_bps')
    if observation['quote_status'] != 'VERIFIED_EXECUTABLE':
        report.update(status='REFUSED', reason=observation['quote_status'])
        return 2, public_bytes(report, forbidden)
    [quote] = observation['quotes']
    proof, e = verifier.proof, verifier.proof['economics']
    report.update(status='VERIFIED_EXECUTABLE', economics=dict(
        pay_token=e.pay_token, receive_token=e.receive_token, amount=str(e.amount),
        recipient=('MATCHES_WALLET' if e.recipient == DEV_WALLET else
                   'UNVERIFIED_UNTRUSTED_LAYOUT' if e.recipient is None else 'MISMATCH'),
        minimum_output=str(e.minimum_output), native_value=e.native_value,
        deadline=datetime.fromtimestamp(e.deadline, timezone.utc).isoformat(),
        deadline_after_quote_s=round(e.deadline - instant(quote['available_at']).timestamp(), 3)),
        **{k: quote[k] for k in ('token_units', 'cash_units', 'min_receive_units', 'gas_bnb_units',
                                 'expected_gas_bnb_units', 'fee_units', 'slippage_bps', 'impact_bps',
                                 'observed_at', 'expires_at')},
        gas_basis=proof['gas_basis'], fee_basis=proof['fee_basis'])
    checked = now()
    accepted, _, rejections, status = _quote_at_cap(observation, args.side, pay, profile, instant(checked),
                                                    quote['token_units'], args.mandatory)
    report['quote_at_cap'] = dict(accepted=accepted is quote, status=status, rejections=rejections,
                                  checked_at=checked)
    return (0 if accepted is quote else 2), public_bytes(report, forbidden)


def main(argv=None, **ports):
    try:
        args = parse(argv)
        code, raw = run(args, **ports)
    except SystemExit:
        raise
    except Exception as error:  # the class only: a message may carry a provider URL or credential
        code, raw = 4, (json.dumps(dict(status='CHECK_REFUSED', error_type=type(error).__name__,
                                        signing_enabled=False)) + '\n').encode()
    sys.stdout.write(raw.decode())
    return code


if __name__ == '__main__':
    raise SystemExit(main())
