"""IDEA-093 FS1: offline FINAL profile for the scored run, 24/7 under the kit's openState; no ports or installation.

S1 (TREND_GUARDED_VOL) with the decided v1 FINAL scope (BOUNDED_FALSIFIER evidence, DISCRETIONARY_EXIT falsifiers),
built from the same pinned inputs as S2 (IDEA-089), plus:
- `s1.execution.hours` KIT_OPEN_STATE and 5 attempts per leg (F-119: orders can be placed 24/7);
- the PF-04 calendar (IDEA-084), set here so the generator's historical FINAL windows still rebuild;
- `slippage_bps` 20, so a post-approve requote survives an adverse move the 8 bp limit did not (S2-F6).
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from larp.contracts import ContractError, Document
from larp.risk.planner import exit_parts
from larp.strategy.profiles import validate_live
from larp.strategy.schema import ceil, floor, fraction
from tools.deploy.build_rehearsal_candidate import fs1_review_options, gas_formulas, pinned_profiles

DECISION = 'IDEA-093 FS1 (2026-10-25)'
# IDEA-084 PF-04 (adopted): first buy Oct 29 14:00, new risk ends Nov 9 21:00, flatten Nov 10 19:00, signing ends
# Nov 11 14:45, all UTC; flat-by target Nov 11 15:00.
PF04_WINDOW = dict(trade_after='2026-10-29T14:00:00Z', new_risk_end='2026-11-09T21:00:00Z',
                   flatten_start='2026-11-10T19:00:00Z', signing_end='2026-11-11T14:45:00Z')
SLIPPAGE_BPS = 20
# IDEA-093 SC (GAP-74, F-125): the activation self-check before Oct 29 UTC, in the same run as the scored run.
F125_GAS_UNITS = 30_000_000  # the organiser-directed 30 USDT -> BNB seed (F-125)
SELF_CHECK_WINDOW = dict(buy_after='2026-10-27T00:00:00Z', buy_until='2026-10-28T18:00:00Z',
                         flat_by='2026-10-28T23:00:00Z')
POLICY_ID = 'larp-fs1-final-v1'
EXIT_CHILDREN = 2


def fs1_block(raw):
    """The FS1 block from its exact bytes: weights 1/5, deterministic limiter, KIT_OPEN_STATE hours, 5 attempts."""
    if type(raw) is not bytes:
        raise ContractError('FS1 configuration must be the exact file bytes')
    try:
        block = json.loads(raw)
    except (TypeError, ValueError):
        raise ContractError('FS1 configuration must be a JSON object') from None
    if type(block) is not dict or type(block.get('weights')) is not dict:
        raise ContractError('FS1 configuration must be a JSON object with weights')
    if any(fraction(w) != Fraction(1, 5) for w in block['weights'].values()):
        raise ContractError('FS1 weights must be 1/5 each (IDEA-091 rank 2, IDEA-093)')
    # The runtime never sets exposure_assessment, so a MODEL limiter would never move (SJ-11-RH01-L1).
    if block.get('limiter_mode') != 'DETERMINISTIC':
        raise ContractError('FS1 needs limiter_mode DETERMINISTIC')
    execution = block.get('execution')
    if type(execution) is not dict or execution.get('hours') != 'KIT_OPEN_STATE':
        raise ContractError('FS1 trades 24/7: s1.execution.hours must be KIT_OPEN_STATE (IDEA-093)')
    if execution.get('max_attempts_per_leg_session') != 5:
        raise ContractError('FS1 sets max_attempts_per_leg_session to 5: one session spans a weekend (IDEA-089 S2-9)')
    return block


def build(*, s1_raw, s1_decision):
    if type(s1_decision) is not str or not s1_decision.strip():
        raise ContractError('An FS1 block and the decision behind it go together')
    block = fs1_block(s1_raw)
    # The shared generator validates its profiles before the hours are set; the hours go on with the final values.
    base = dict(block, execution={k: v for k, v in block['execution'].items() if k != 'hours'})
    p = pinned_profiles(s1=base, s1_decision=s1_decision)['FINAL'].read()
    gas_formulas(p)
    p['provenance']['s1']['data_hash'] = hashlib.sha256(s1_raw).hexdigest()
    # The caps review reserves every position's balanced exit at the hard name line (LD10-P03 D3), as for S2.
    from larp.strategy.s1 import config
    if exit_parts(ceil(config(p)['hard'] * p['expected_equity_units']), p['per_trade_cap_units']) > EXIT_CHILDREN:
        raise ContractError('The FS1 hard name line needs more exit children than the reserve covers')
    p['exit_gas_reserve_units'] = 5 * EXIT_CHILDREN * p['gas_action_budget_units']
    p['provenance']['exit_gas_reserve_units'] = dict(p['provenance']['exit_gas_reserve_units'],
        decision_id='IDEA-049-C LD10-P03 (Keegan delegation, 2026-10-21); IDEA-093 FS1',
        formula='5 positions*2 balanced exit children*gas_action_budget_units; cleanup disabled')
    p['s1'] = block
    fs1_review_options(p)
    p.update(PF04_WINDOW, slippage_bps=SLIPPAGE_BPS, policy_id=POLICY_ID)
    for key in PF04_WINDOW:
        p['provenance'][key] = dict(decision_id='IDEA-084 PF-04 (adopted); ' + DECISION,
            formula='Final calendar: first buy Oct 29 14:00, new risk ends Nov 9 21:00, flatten Nov 10 19:00, '
                    'signing ends Nov 11 14:45 UTC; flat by Nov 11 15:00')
    p['provenance']['slippage_bps'] = dict(p['provenance']['slippage_bps'], decision_id=DECISION,
        formula='20 bp (<= 50): measured max p90 requote drift was 8 bp, and 3 of 4 run-4 buys aborted at the '
                'post-approve requote under it (S2-F6, IDEA-090 F16)')
    p['provenance']['policy_id'] = dict(decision_id=DECISION,
        formula='FS1, the final scored-run strategy: S1 with 24/7 KIT_OPEN_STATE hours under openState, live FINAL only')
    p['activation_self_check'] = self_check(p)
    p['provenance']['activation_self_check'] = dict(decision_id='IDEA-093 SC (GAP-74, F-125; 2026-10-25, proposed)',
        formula='cheapest measured round trip (spread + 2*median impact + fee, then symbol); '
                'pay_units = an ordinary FS1 entry: floor(0.95*1/5*(expected equity - 30 USDT F-125 gas - cost reserve)) '
                'in whole USDT, so it passes the same authorized-minimum 50 bp cost gate; '
                'buy Oct 27 00:00 to Oct 28 18:00, flat by Oct 28 23:00 UTC')
    validate_live(p)
    return Document.from_dict(p)


def self_check(p):
    """One ordinary-size round trip in the cheapest measured name before Oct 29 (F-125's real final-wallet trade).

    A minimum-size (about 19 USDT) leg would fail the authorized-minimum 50 bp entry-cost gate (20 bp slippage, spread
    and about 30 bp of gas); an ordinary FS1 entry at 170 USDT cash (about 32 USDT) passes it, as scored entries do."""
    rows = p['quote_cost_summary']['symbols']
    symbol = min(rows, key=lambda s: (rows[s]['spread_bps'] + 2 * rows[s]['median_impact_bps'] + rows[s]['fee_bps'], s))
    stock_capital = p['expected_equity_units'] - F125_GAS_UNITS - p['cost_reserve_units']
    pay = floor(Fraction(19, 100) * stock_capital) // 1_000_000 * 1_000_000
    return dict(symbol=symbol, pay_units=pay, **SELF_CHECK_WINDOW)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--s1-config', type=Path, required=True, help='the FS1 block (JSON)')
    parser.add_argument('--s1-decision', required=True, help='decision ID for the supplied block')
    args = parser.parse_args(argv)
    p = build(s1_raw=args.s1_config.read_bytes(), s1_decision=args.s1_decision)
    with args.output.open('xb') as stream:
        stream.write(p.payload + b'\n')
    print(p.digest('StrategyProfile.v1'))


if __name__ == '__main__':
    main()
