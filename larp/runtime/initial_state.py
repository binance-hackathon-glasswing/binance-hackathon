"""IDEA-058: the pinned initial state (`PortfolioState.v1`) that `service init` builds a dev or live run from.

It reads the wallet at one finalized block (larp/execution_live/balances.py), books what the chain holds and decides
nothing: USDT floored to the 6-decimal money scale (the dust stays on chain, a recorded surplus, IDEA-055), BNB in
exact wei (gate_b DR-06), the BNB price from the pinned LIVE profile (IDEA-055 D6), and opening equity, peak and day
anchor at that valuation. A wallet that already holds a stock token is refused: its cost basis would be invented.

    python -m larp.runtime.initial_state --rpc-url https://<manifested BSC RPC> --rpc-source-id <id> \\
        --wallet 0x<public> --run-id <run> --mode dev --profile <pinned LIVE profile> --output initial-state.json
"""

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

from larp.contracts import ContractError, Document
from larp.risk.reconcile import CASH_DECIMALS, NATIVE_DECIMALS, compare_balances

ACCOUNTING = ('realized_units', 'fees_units', 'gas_value_units', 'service_units', 'turnover_units')


def build_initial_state(observation, *, run_id, wallet, mode, profile):
    """PortfolioState.v1 for `observation` (ChainBalances.v1); raises ContractError instead of guessing."""
    from larp.integration.runtime import initial_projection, ledger_from
    from larp.strategy.profiles import quote_summary
    o, wallet = observation, str(wallet).lower()
    if mode not in ('dev', 'live'):
        raise ContractError('Initial state is for a dev or live run')
    if type(run_id) is not str or not run_id:
        raise ContractError('Run ID required')
    if o.get('schema') != 'ChainBalances.v1' or o.get('wallet') != wallet or o.get('chain_id') != 56:
        raise ContractError('Balance observation is for another wallet or chain')
    if o['latest_nonce'] != o['pending_nonce']:
        raise ContractError('A transaction is still pending; read again once it is final')
    if type(profile) is not dict or profile.get('mode') != 'LIVE' or 'quote_cost_summary' not in profile:
        raise ContractError('A pinned LIVE profile with its quote-cost summary is required')
    price = quote_summary(profile['quote_cost_summary'])['bnb_price_units']
    held = sorted(s for s, row in o['tokens'].items() if s != 'USDT' and row['units'])
    if held:
        raise ContractError('The wallet already holds ' + ','.join(held) + '; their cost basis is unknown')
    if not o['native_wei']:
        raise ContractError('The wallet holds no BNB for gas (Q-03); DR-06 requires native funding')
    usdt = o['tokens']['USDT']
    if usdt['decimals'] < CASH_DECIMALS:
        raise ContractError('USDT decimals below the money scale')
    cash = usdt['units'] // 10 ** (usdt['decimals'] - CASH_DECIMALS)
    equity = cash + int(Fraction(o['native_wei'] * price, 10**NATIVE_DECIMALS))
    day = datetime.fromisoformat(o['observed_at'].replace('Z', '+00:00')).astimezone(timezone.utc).date().isoformat()
    state = {
        'schema': 'PortfolioState.v1', 'mode': 'dev' if mode == 'dev' else 'LIVE', 'run_id': run_id,
        'wallet_id': wallet, 'cash_units': cash, 'bnb_units': o['native_wei'], 'bnb_price_units': price,
        'bnb_decimals': NATIVE_DECIMALS, 'opening_equity_units': equity,
        'positions': {s: {'units': 0, 'decimals': row['decimals'], 'cost_basis_units': 0}
                      for s, row in sorted(o['tokens'].items()) if s != 'USDT'},
        'reservations': {}, 'applied_events': {}, 'accounting': {k: 0 for k in ACCOUNTING},
        'risk': {'day': day, 'day_anchor_units': equity, 'peak_units': equity, 'daily_halt': False,
                 'run_halt': False, 'deep_cut': False}}
    # Self-checks: the runtime can build its ledger from it, it agrees with the chain it came from, and it meets
    # gate_b DR-06 (exact wei, funded, dev/LIVE mode).
    ledger_from(initial_projection(state), [])
    check = compare_balances(state, o, settled_block=None)
    if check['status'] not in ('MATCH', 'SURPLUS_ONLY') or set(check['surplus']) - {'USDT'}:
        raise ContractError('The built state does not agree with the chain read')
    if equity < 1:
        raise ContractError('Opening equity must be positive')
    return state


def observe(rpc_url, source_id, wallet, artifact_dir):
    """The finalized-block balance read over the manifested RPC (read-only)."""
    from larp.execution_live.balances import read_balances
    from larp.execution_live.chain import Rpc
    from larp.marketdata.web3 import Artifacts
    rpc = Rpc(rpc_url, artifacts=Artifacts(str(artifact_dir)), source_id=source_id)
    observed = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    return read_balances(rpc, wallet=wallet, observed_at=observed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('--rpc-url', '--rpc-source-id', '--wallet', '--run-id', '--profile', '--output'):
        parser.add_argument(name, required=True)
    parser.add_argument('--mode', required=True, choices=('dev', 'live'))
    args = parser.parse_args(argv)
    output = Path(args.output)
    provenance_path = output.with_name(output.name + '.provenance.json')
    try:
        if output.exists() or provenance_path.exists():
            raise ContractError(f'{output} or its provenance exists; a pinned state is never replaced')
        profile_bytes = Path(args.profile).read_bytes()
        observation = observe(args.rpc_url, args.rpc_source_id, args.wallet,
                              output.parent / (output.name + '.artifacts'))
        state = build_initial_state(observation, run_id=args.run_id, wallet=args.wallet, mode=args.mode,
                                    profile=json.loads(profile_bytes))
    except (ContractError, OSError, ValueError, KeyError, TypeError) as refused:
        print('refused:', refused, file=sys.stderr)
        return 2
    raw = json.dumps(state, indent=2, sort_keys=True).encode() + b'\n'
    output.write_bytes(raw)
    provenance_path.write_text(json.dumps(dict(
        schema='InitialStateProvenance.v1', block_number=observation['block_number'],
        block_hash=observation['block_hash'], observed_at=observation['observed_at'],
        observation_sha256=Document.from_dict(observation).digest('ChainBalances.v1'),
        profile_sha256=hashlib.sha256(profile_bytes).hexdigest(),
        usdt_dust_chain_units=observation['tokens']['USDT']['units'] % 10 ** (
            observation['tokens']['USDT']['decimals'] - CASH_DECIMALS)), indent=2, sort_keys=True) + '\n')
    print('PortfolioState.v1', hashlib.sha256(raw).hexdigest(), '->', output,
          '(put this SHA-256 in runtime.json initial_state_sha256)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
