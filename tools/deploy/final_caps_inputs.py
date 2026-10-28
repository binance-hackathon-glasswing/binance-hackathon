"""IDEA-110 / FS1 Q1: fresh FINAL GateBCapsInputs.v1 from a prepared FINAL directory and live final-wallet quotes.

  python -m tools.deploy.final_caps_inputs --prepared <prepare_fs1 --out dir> --terraform-output <tf-output.json> \
    --rds-ca-sha256 <sha> --balance-rpc-config <private providers file> --env-file <.env> --output <new private dir>

The rehearsal builder (review_rehearsal_caps.py) is REHEARSAL-only and needs an installed run's host probe; the final
wallet has neither. This builds the same inputs locally:
  - profile, initial state and run/database/router identities: the exact bytes `prepare_fs1` just wrote;
  - signing policy: the reviewed CAP-02 `final` policy (signer-numeric-ceilings-20261021), with only the zero-only
    allowance recovery switched on, as FS1 pins recovery;
  - execution config: the same fields the S5 hosted path (review_rehearsal_caps --bindings + M4) produced, FINAL/live;
  - quotes: Web3 `aggregator/quote-and-swap` for the final wallet at the profile's sizes (BUY minimum and cap, the full
    SELL and its planned balanced exit children), through the runtime's own MarketPort with the profile's slippage.
    Quote reads are free, need no balance and never sign or send.
Then it runs the release's own numeric reviewer. `prepare_fs1 --caps-inputs <output>/inputs.json` must follow within
the 300 s quote validity; it re-reviews and assembles the key-free signer.json. Nothing here approves or installs.
stdout carries status, blockers and hashes only: no URLs, keys, hosts or DSNs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from larp.contracts import ContractError
from larp.execution_live.caps_review import ERRORS, exit_children, review
from larp.marketdata.port import TOKENS, MarketPort
from larp.marketdata.web3 import Web3Client, credentials, utc
from larp.risk.planner import exit_parts
from larp.strategy import s1 as s1_plan
from larp.strategy.schema import ceil, fraction

ROOT = Path(__file__).resolve().parents[2]
CEILINGS = ROOT / 'docs/build/evidence/signer-numeric-ceilings-20261021.json'
# IDEA-110: the self-check BUY itself, quoted as evidence beside the profile sizes (0.90 USDT, micro-USDT).
SELF_CHECK_PAY_UNITS = 900000


class MemoryArtifacts:
    """`Artifacts.put` without a disk write; each record is pinned into the private output instead."""

    def __init__(self):
        self.records = []

    def put(self, observation):
        raw = json.dumps(observation, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.records.append(json.loads(raw))
        return hashlib.sha256(raw).hexdigest()


def require(ok, why):
    if not ok:
        raise ContractError(why)


def max_exit_children(profile):
    """The reviewer's bound on balanced children for one full exit (caps_review.review)."""
    s1 = s1_plan.config(profile) if profile['baseline'] == s1_plan.BASELINE else None
    hard = s1['hard'] if s1 else fraction(profile['hard_name_weight'])
    return exit_parts(ceil(hard * profile['expected_equity_units']), profile['per_trade_cap_units'])


def quotes(port, profile, decimals, extra_buys=None):
    """Request-bound quotes: BUY minimum and cap (and any extra BUY), the largest bought amount as the full SELL,
    then each distinct planned exit child of it. The port records every quote; a refused quote stops the run."""
    extra_buys = extra_buys or {}
    minimum, cap = profile['minimum_trade_units'], profile['per_trade_cap_units']
    cap_raw, limit = cap * 10**12, max_exit_children(profile) + 1
    for symbol in TOKENS:
        bought = 0
        for units in sorted({minimum, cap, *extra_buys.get(symbol, ())}):
            data = single(port.quote(symbol, 'BUY', units * 10**12, decimals[symbol]))
            bought = max(bought, int(data['routerResult']['toTokenAmount']))
        require(bought > 0, 'BUY quote returned no units')
        whole = single(port.quote(symbol, 'SELL', bought, decimals[symbol]))
        proceeds = int(whole['routerResult']['toTokenAmount'])
        for child in sorted(set(exit_children(bought, proceeds, cap_raw, limit)) - {bought}):
            port.quote(symbol, 'SELL', child, decimals[symbol])


def single(record):
    data = record['response']['data'] if 'response' in record else record['data']
    return data[0] if type(data) is list else data


def build(prepared, rendered_execution, providers, keys, output, *, now=None, port_factory=None):
    """`port_factory(artifacts)` replaces the live MarketPort in offline tests; it must `put` every quote record."""
    prepared = Path(prepared)
    runtime = json.loads((prepared / 'runtime.json').read_bytes())
    profile_raw = (prepared / 'strategy-profile.json').read_bytes()
    state_raw = (prepared / 'initial-state.json').read_bytes()
    profile, state = json.loads(profile_raw), json.loads(state_raw)
    driver = runtime['driver']
    require(runtime['mode'] == 'live' and profile['environment'] == 'FINAL', 'FINAL/live preparation required')
    require(driver['strategy_profile_sha256'] == hashlib.sha256(profile_raw).hexdigest(), 'profile differs from runtime')
    require(runtime['initial_state_sha256'] == hashlib.sha256(state_raw).hexdigest(), 'initial state differs from runtime')
    require(driver.get('allowance_recovery') is True, 'FINAL preparation must carry allowance recovery')
    wallet = runtime['wallet_address']
    require(state['wallet_id'] == wallet and state['run_id'] == runtime['run_id'], 'initial state identity differs')
    decision = json.loads(CEILINGS.read_bytes())
    final = decision['policies']['final']
    base = json.dumps(final['signing_policy'], sort_keys=True, separators=(',', ':')).encode() + b'\n'
    require(hashlib.sha256(base).hexdigest() == final['sha256_canonical_json_lf'], 'CAP-02 final policy differs')
    policy = dict(final['signing_policy'], allowance_recovery=True)
    decimals = {s: state['positions'][s]['decimals'] for s in TOKENS}
    first = providers[0]
    config = dict(schema='ExecutionService.v1', run_id=runtime['run_id'], build_id=runtime['build_id'], mode='live',
        wallet_address=wallet, interval_seconds=1, router=policy['allowed_spenders'][0], token_decimals=decimals,
        max_gas=decision['execution_ceiling']['max_gas'], max_gas_price=decision['execution_ceiling']['max_gas_price_wei'],
        gas_budget=profile['gas_action_budget_units'], allowance_recovery=True,
        strategy_profile_file=driver['strategy_profile_file'], strategy_profile_sha256=driver['strategy_profile_sha256'],
        database_user='larp_execution', untrusted_router_policy_file=driver['untrusted_router_policy_file'],
        untrusted_router_policy_sha256=driver['untrusted_router_policy_sha256'],
        runtime_secret_id=runtime['runtime_secret_id'], rpc_url=first['url'], rpc_source_id=first['source_id'],
        **{k: runtime[k] for k in ('database_host', 'database_name', 'database_ca_file', 'database_ca_sha256', 'region')},
        **{k: rendered_execution[k] for k in ('market_artifact_root', 'chain_artifact_root', 'signer_timeout_seconds')})
    require(any((p['url'], p['source_id']) == (first['url'], first['source_id'])
                for p in driver.get('balance_rpc_providers') or []), 'execution RPC is not a runtime provider')
    artifacts = MemoryArtifacts()
    port = (port_factory(artifacts) if port_factory else
            MarketPort(Web3Client(keys['BINANCE_API_KEY'], keys['BINANCE_SECRET_KEY'], artifacts=artifacts),
                       wallet, quote_limits=profile))
    extra = {}
    check = profile.get('activation_self_check')
    if check:
        extra[check['symbol']] = (check['pay_units'],)
    quotes(port, profile, decimals, extra)
    output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)

    def pin(name, value=None, raw=None):
        raw = raw if raw is not None else json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'
        with (output / name).open('xb') as stream:
            stream.write(raw)
        (output / name).chmod(0o600)
        return dict(path=name, sha256=hashlib.sha256(raw).hexdigest())
    inputs = dict(schema='GateBCapsInputs.v1', wallet=wallet, run_id=runtime['run_id'], build_id=runtime['build_id'],
        environment='FINAL', max_age_seconds=300,
        files=dict(profile=pin('profile.json', raw=profile_raw), signing_policy=pin('signing-policy.json', policy),
                   execution_config=pin('execution-config.json', config),
                   initial_state=pin('initial-state.json', raw=state_raw)),
        quote_artifacts=[pin('quote-%02d.json' % n, r) for n, r in enumerate(artifacts.records)])
    now = now or utc()
    result = review(inputs, now=now, base_dir=output)
    pin('inputs.json', inputs)
    pin('review.json', result)
    return inputs, result, now


def main(argv=None):
    sys.path.insert(0, str(ROOT / 'tools/deploy'))
    import prepare_shadow
    import render_host_configs as renderer
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'terraform-output', 'balance-rpc-config', 'env-file', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--rds-ca-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        out = args.output.resolve()
        require(not (out == ROOT or ROOT in out.parents), 'private output must stay outside the checkout')
        runtime = json.loads((args.prepared / 'runtime.json').read_bytes())
        rendered = renderer.render(renderer.outputs(json.loads(args.terraform_output.read_bytes())),
                                   runtime['wallet_address'], args.rds_ca_sha256)['execution.json']
        inputs, result, now = build(args.prepared, rendered, prepare_shadow.rpc_providers(args.balance_rpc_config),
                                    credentials(args.env_file), out)
    except (*ERRORS, renderer.Refused) as error:
        print(json.dumps(dict(status='FINAL_CAPS_INPUTS_REFUSED', reason=type(error).__name__,
                              signing_enabled=False, ready_to_install=False)))
        return 4
    print(json.dumps(dict(status='FINAL_CAPS_INPUTS_WRITTEN', numeric_status=result['numeric_status'],
                          blockers=result['blockers'], missing=result['missing_quote_coverage'], reviewed_at=now,
                          quotes=len(inputs['quote_artifacts']),
                          inputs_sha256=hashlib.sha256((out / 'inputs.json').read_bytes()).hexdigest(),
                          signing_enabled=False, ready_to_install=False)))
    return 0 if result['numeric_status'] == 'COVERED' else 3


if __name__ == '__main__':
    raise SystemExit(main())
