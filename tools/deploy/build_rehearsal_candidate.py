"""LD10-Q01/LD11-RH01 (equal weight), SJ-11-RH01 (S1): offline scoped rehearsal profile, no ports or installation."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from larp.contracts import ContractError, Document
from larp.risk.planner import exit_parts
from larp.strategy.profiles import build_live_profiles, validate_live
from larp.strategy.schema import ceil, fraction

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence'
# IDEA-089 S2-4 (Yao, 2026-10-23): Sat 09:00 SGT to Sun 23:00 SGT, flat before signing_end.
S2_WINDOW = dict(trade_after='2026-10-24T01:00:00Z', new_risk_end='2026-10-25T08:00:00Z',
                 flatten_start='2026-10-25T09:00:00Z', signing_end='2026-10-25T15:00:00Z')
S2_POLICY_ID = 'larp-s2-rehearsal-v1'
# IDEA-092 S3: S2 plus a scheduled sell-all; the requested 12 noon is 12:00 SGT Sunday, inside S2's buy window.
S3_FLATTEN_AT = '2026-10-25T04:00:00Z'
S3_POLICY_ID = 'larp-s3-rehearsal-v1'
# IDEA-093 FS1-R: FS1's block and slippage on the dev wallet; starts an hour after run 4's signing_end, ends before
# Monday's NYSE open on the Oct 26 freeze day (proposed; the run owner may rebuild with other times).
FS1R_WINDOW = dict(trade_after='2026-10-25T16:00:00Z', new_risk_end='2026-10-26T06:00:00Z',
                  flatten_start='2026-10-26T07:00:00Z', signing_end='2026-10-26T12:00:00Z')
FS1R_POLICY_ID = 'larp-fs1-rehearsal-v1'
FS1_SLIPPAGE_BPS = 20


def fs1_review_options(p):
    """Explicit, hashed review refinements shared by FINAL and its rehearsal (IDEA-093 PR278-RV01)."""
    p.update(run_halt_recovery_bps=500, s1_reduction_cost_cap_bps=50, entry_cost_basis='AUTHORIZED_MINIMUM',
             s1_capital_basis='EXCLUDE_GAS')
    p['provenance']['s1_capital_basis'] = dict(decision_id='IDEA-093 PR278-RV01-GAS; F-125 (review candidate)',
        formula='Nominal S1 levels apply to cash plus marked stocks minus cost reserve; native gas excluded')
    p['provenance']['entry_cost_basis'] = dict(decision_id='IDEA-093 PR278-RV01 (review candidate)',
        formula='BUY cost reserve and 50bp entry cap use authorized minimum output plus fee and expected gas')
    p['provenance']['run_halt_recovery_bps'] = dict(decision_id='IDEA-084 PF-02; IDEA-093 PR278-RV01',
        formula='Clear only the 8% buy stop strictly below 5% drawdown with fresh complete reconciled valuation')
    p['provenance']['s1_reduction_cost_cap_bps'] = dict(decision_id='IDEA-093 PR278-RV01 (review candidate)',
        formula='Pending S1 level SELL may be below entry minimum only at authorized-minimum cost <=50bp and cost reserve')
# IDEA-097 S4: S2 from run 4's carried-over book, already inside the terminal flatten when run 5 starts; no BUY window.
S4_WINDOW = dict(trade_after='2026-10-25T10:00:00Z', new_risk_end='2026-10-25T10:30:00Z',
                 flatten_start='2026-10-25T10:30:00Z', signing_end='2026-10-26T20:00:00Z')
S4_POLICY_ID = 'larp-s4-rehearsal-v1'
# IDEA-104 S5 (R2): FS1-R (FS1's block, 20 bp, review refinements, recovery gas) running to Tue Oct 27 12:00 SGT:
# buys from Mon 14:00 to Tue 07:00 SGT, flatten from Tue 08:00 SGT, signing to Tue 12:00 SGT (Oct 27 04:00 UTC, inside
# the development time extended to Oct 28, F-126). FS1 itself is unchanged.
S5_WINDOW = dict(trade_after='2026-10-26T06:00:00Z', new_risk_end='2026-10-26T23:00:00Z',
                 flatten_start='2026-10-27T00:00:00Z', signing_end='2026-10-27T04:00:00Z')
S5_POLICY_ID = 'larp-s5-rehearsal-v1'
# IDEA-096 AL-IMPL01 (tools/deploy/enable_allowance_recovery.py): eight signed children per intent at the configured
# execution envelope (max_gas 1200000 x max_gas_price 160000000), so S4 runs with allowance recovery on.
RECOVERY_MAX_GAS, RECOVERY_MAX_GAS_PRICE, RECOVERY_CHILDREN = 1200000, 160000000, 8


def s1_block(raw):
    """The S1 block from its exact bytes: weights 1/5 each at about 100 USDT (SJ-09-PC01 C5), deterministic limiter."""
    if type(raw) is not bytes:
        raise ContractError('S1 configuration must be the exact file bytes')
    try:
        block = json.loads(raw)
    except (TypeError, ValueError):
        raise ContractError('S1 configuration must be a JSON object') from None
    if type(block) is not dict or type(block.get('weights')) is not dict:
        raise ContractError('S1 configuration must be a JSON object with weights')
    if any(fraction(w) != Fraction(1, 5) for w in block['weights'].values()):
        raise ContractError('S1 rehearsal weights must be 1/5 each (SJ-09-PC01 C5)')
    # No hosted models in this scope, and the runtime never sets exposure_assessment: a MODEL limiter would never move.
    if block.get('limiter_mode') != 'DETERMINISTIC':
        raise ContractError('S1 rehearsal without hosted models needs limiter_mode DETERMINISTIC (SJ-11-RH01-L1)')
    execution = block.get('execution')
    if (type(execution) is dict and execution.get('hours') == 'KIT_OPEN_STATE'
            and execution.get('max_attempts_per_leg_session') != 5):
        raise ContractError('S2 sets max_attempts_per_leg_session to 5: one session spans the weekend (IDEA-089 S2-9)')
    return block


def pinned_profiles(**s1):
    """`build_live_profiles` on the pinned measured inputs, L/m and initial-only gas budgets (also IDEA-093 FS1)."""
    def document(path):
        return Document.from_dict(json.loads(path.read_bytes()))
    authority = dict(seconds=660, margin=30, decision_id='IDEA-049-C LD04-V01 (Keegan, 2026-10-20)',
        data_hash=hashlib.sha256((EVIDENCE / 'ld02-execution-packet-20261020.json').read_bytes()).hexdigest())
    budget = dict(action_units=384000000000000, sizing_units=80004608000000,
        decision_id='IDEA-049-C LD10-Q01 (Keegan delegation, 2026-10-21)',
        data_hash=hashlib.sha256((EVIDENCE / 'signer-numeric-ceilings-20261021.json').read_bytes()).hexdigest())
    return build_live_profiles(document(EVIDENCE / 'quotes-complete-20261020/quote-cost-summary.json'),
        document(ROOT / 'config/intelligence/red_flags.v1.json'), initial_gas_only=True,
        authority=authority, gas_budget=budget, **s1)


# IDEA-049-C CAP-02 signed per-child ceilings (signer-numeric-ceilings-20261021.json): the recovery envelope's inputs.
SIGNED_CHILD_GAS, SIGNED_GAS_PRICE = 1_200_000, 160_000_000
CEILINGS = Path(__file__).resolve().parents[2] / 'docs/build/evidence/signer-numeric-ceilings-20261021.json'
RECOVERY_DECISION = 'IDEA-098 (IDEA-096 F2/F3 recovery gas at the CAP-02 ceilings)'


def with_recovery_gas(p):
    """IDEA-098: PR282's eight-child recovery envelope and exit reserve at the CAP-02 signed ceilings, so the profile
    Isaac approves already carries what `enable_allowance_recovery` would set at install (it then keeps the bytes)."""
    from tools.deploy.enable_allowance_recovery import recovery_gas
    expected = json.loads(CEILINGS.read_bytes())['execution_ceiling']
    if (expected['max_gas'], expected['max_gas_price_wei']) != (SIGNED_CHILD_GAS, SIGNED_GAS_PRICE):
        raise ContractError('CAP-02 ceilings differ from the recovery builder constants')
    return recovery_gas(p, max_gas=SIGNED_CHILD_GAS, max_gas_price=SIGNED_GAS_PRICE, decision_id=RECOVERY_DECISION,
                        data_hash=hashlib.sha256(CEILINGS.read_bytes()).hexdigest())


def gas_formulas(p):
    p['provenance']['gas_action_budget_units']['formula'] = '2*1200000 max signed child gas*160000000 max gas price; cleanup disabled'
    p['provenance']['gas_sizing_budget_units']['formula'] = 'ceil(1000057*5/4) independently rounded child allowance at 64000000 expected gas price'


def open_state(block):
    """IDEA-089 S2: the block sets KIT_OPEN_STATE hours (a weekend REHEARSAL test, never a final profile)."""
    return block is not None and type(block.get('execution')) is dict and block['execution'].get('hours') == 'KIT_OPEN_STATE'


def build(exit_children=1, *, s1_raw=None, s1_decision=None, scheduled_flatten_at=None, fs1_rehearsal=False,
          allowance_recovery=False, carry_over=False, s5=False):
    """`exit_children=1` reproduces the historical LD10-Q01 bytes; LD10-P03 selects 2.

    With `s1_raw` (the exact bytes of Keith's S1 block) and `s1_decision`, the profile is TREND_GUARDED_VOL under the
    same SHADOW scope (SJ-11-RH01), and the reserve covers five positions x `exit_children`. With an S2 block,
    `scheduled_flatten_at` makes it S3 (IDEA-092): everything sold at that time, then S2 again; `fs1_rehearsal` makes it
    FS1-R (IDEA-093): the final FS1 block and slippage in S2's dev scope, on the FS1-R window. `carry_over` makes it
    S4 (IDEA-097): run 5 starts from run 4's exported book inside the terminal flatten, with allowance recovery gas.
    `s5` makes FS1-R with recovery into S5 (IDEA-104): the same profile on a window ending Tue Oct 27 12:00 SGT."""
    if exit_children not in (1, 2):
        raise ValueError('exit_children must be 1 (historical Q01) or 2 (LD10-P03)')
    if (s1_raw is None) != (s1_decision is None) or (
            s1_decision is not None and (type(s1_decision) is not str or not s1_decision.strip())):
        raise ContractError('An S1 block and the decision behind it go together')
    s1 = None if s1_raw is None else s1_block(s1_raw)
    s2 = open_state(s1)
    if scheduled_flatten_at is not None and not s2:
        raise ContractError('A scheduled flatten (S3) builds only on an S2 block (IDEA-092)')
    if fs1_rehearsal and (not s2 or scheduled_flatten_at is not None):
        raise ContractError('FS1-R builds only on a KIT_OPEN_STATE block, without a scheduled flatten (IDEA-093)')
    if allowance_recovery and not fs1_rehearsal:
        raise ContractError('Allowance recovery gas is built only for FS1-R (IDEA-098)')
    if carry_over and (not s2 or scheduled_flatten_at is not None or exit_children != 2):
        raise ContractError('A carry-over (S4) builds only on an S2 block, with two exit children and no S3 (IDEA-097)')
    if carry_over and fs1_rehearsal:
        raise ContractError('S4 (IDEA-097) and FS1-R (IDEA-093) are separate rehearsals')
    if s5 and not (fs1_rehearsal and allowance_recovery):
        raise ContractError('S5 (IDEA-104) builds only on FS1-R with allowance recovery')
    if s2:
        # The shared builder validates its BOUNDED_FALSIFIER profiles, which S2-1 refuses; the hours are set below,
        # once the SHADOW scope is.
        base_s1 = dict(s1, execution={k: v for k, v in s1['execution'].items() if k != 'hours'})
    p = pinned_profiles(**({} if s1 is None else dict(s1=base_s1 if s2 else s1, s1_decision=s1_decision)))['REHEARSAL'].read()
    gas_formulas(p)
    positions = 4
    if s1 is not None:
        positions = 5
        p['provenance']['s1']['data_hash'] = hashlib.sha256(s1_raw).hexdigest()
        # The caps review reserves every position's balanced exit at the hard name line (LD10-P03 D3).
        from larp.strategy.s1 import config
        if exit_parts(ceil(config(p)['hard'] * p['expected_equity_units']), p['per_trade_cap_units']) > exit_children:
            raise ContractError('The S1 hard name line needs more exit children than the reserve covers')
    if exit_children == 2:
        p['exit_gas_reserve_units'] = positions * 2 * p['gas_action_budget_units']
        p['provenance']['exit_gas_reserve_units'] = dict(p['provenance']['exit_gas_reserve_units'],
            decision_id='IDEA-049-C LD10-P03 (Keegan delegation, 2026-10-21)' + ('; SJ-11-RH01 C7' if s1 else ''),
            formula='%d positions*2 balanced exit children*gas_action_budget_units; cleanup disabled' % positions)
    p['evidence_mode'] = 'SHADOW'
    p['falsifier_authority'] = 'SHADOW'
    p['provenance']['evidence_mode'] = dict(decision_id='IDEA-083 LD11-RH01 (Keegan, 2026-10-21)',
        formula='Scoped EQUAL_WEIGHT rehearsal; deterministic assessor, hosted models and discretionary model exits deferred')
    if s1 is not None:
        p['provenance']['evidence_mode'] = dict(decision_id='IDEA-049-C SJ-11 (Yao, 2026-10-23); scope SJ-11-RH01',
            formula='Scoped TREND_GUARDED_VOL rehearsal; deterministic assessor, hosted models and discretionary '
                    'model exits deferred')
    p['provenance']['falsifier_authority'] = dict(p['provenance']['evidence_mode'])
    if s2:
        p['s1'] = s1
        p.update(S2_WINDOW, policy_id=S2_POLICY_ID)
        for key in S2_WINDOW:
            p['provenance'][key] = dict(decision_id='IDEA-089 S2-4 (Yao, 2026-10-23)',
                formula='Weekend window: buys Sat 09:00 to Sun 16:00 SGT, flatten from Sun 17:00 SGT, signing to Sun 23:00 SGT')
        p['provenance']['policy_id'] = dict(decision_id='IDEA-089 S2 (Yao, 2026-10-23)',
            formula='REHEARSAL-only weekend trade test on the dev wallet; never installed for the final run')
    if scheduled_flatten_at is not None:
        p.update(scheduled_flatten_at=scheduled_flatten_at, policy_id=S3_POLICY_ID)
        p['provenance']['scheduled_flatten_at'] = dict(decision_id='IDEA-092 S3 (team request, 2026-10-24)',
            formula='Sell every held name from this time, no buys until flat, then S2 resumes from a fresh book')
        p['provenance']['policy_id'] = dict(decision_id='IDEA-092 S3 (team request, 2026-10-24)',
            formula='S2 with a scheduled sell-all; REHEARSAL-only on the dev wallet; never installed for the final run')
    if fs1_rehearsal:
        fs1_review_options(p)
        p.update(FS1R_WINDOW, slippage_bps=FS1_SLIPPAGE_BPS, policy_id=FS1R_POLICY_ID)
        for key in FS1R_WINDOW:
            p['provenance'][key] = dict(decision_id='IDEA-093 FS1-R (2026-10-25, proposed window)',
                formula='Off-hours dev test of FS1: buys Mon 00:00 to 14:00 SGT, flatten from 15:00, signing to 20:00 SGT')
        p['provenance']['slippage_bps'] = dict(p['provenance']['slippage_bps'], decision_id='IDEA-093 FS1',
            formula='20 bp (<= 50), the FS1 final value after S2-F6 (IDEA-090 F16)')
        p['provenance']['policy_id'] = dict(decision_id='IDEA-093 FS1-R (2026-10-25)',
            formula='REHEARSAL-only dev test of the FS1 final settings; never installed for the final run')
    if allowance_recovery:
        with_recovery_gas(p)
    if s5:
        p.update(S5_WINDOW, policy_id=S5_POLICY_ID)
        for key in S5_WINDOW:
            p['provenance'][key] = dict(decision_id='IDEA-104 S5 R2 (team request, 2026-10-26)',
                formula='Dev test of FS1: buys from Mon 14:00 SGT to Tue 07:00 SGT, flatten from Tue 08:00 SGT, signing '
                        'to Tue 12:00 SGT (Oct 27 04:00 UTC, inside the development time extended to Oct 28, F-126)')
        p['provenance']['policy_id'] = dict(decision_id='IDEA-104 S5 R2 (team request, 2026-10-26)',
            formula='FS1-R with recovery and FS1 token history, selling everything from Tue 08:00 SGT; REHEARSAL-only '
                    'on the dev wallet; never installed for the final run (FS1 stays the final strategy)')
        # IDEA-104 R3: FS1 FINAL's evidence authority, so AIand/ChatGPT findings act on S5 as they do on FS1.
        p.update(evidence_mode='BOUNDED_FALSIFIER', falsifier_authority='DISCRETIONARY_EXIT')
        for key in ('evidence_mode', 'falsifier_authority'):
            p['provenance'][key] = dict(decision_id='IDEA-104 S5 R3 (team request, 2026-10-26)',
                formula='FS1 FINAL v1 scope: routed AIand/ChatGPT assessment, verified red flags exit or block entry; '
                        'needs reviewed routing (no deterministic signing)')
    if carry_over:
        p.update(S4_WINDOW, policy_id=S4_POLICY_ID, holdings_carry_over='RUN_EXPORT')
        for key in S4_WINDOW:
            p['provenance'][key] = dict(decision_id='IDEA-097 S4 (Yao, 2026-10-25)',
                formula='Flatten test: no buys, terminal flatten from 18:30 SGT Sun Oct 25 (before run 5 starts), '
                        'signing to 04:00 SGT Tue Oct 27 (Mon Oct 26 20:00 UTC): inside the development phase, which '
                        'ends Oct 26 (F-125), and before final activation needs the hosts (PR284-RV01-3)')
        p['provenance']['policy_id'] = dict(decision_id='IDEA-097 S4 (Yao, 2026-10-25)',
            formula='S2 from the previous run\'s carried-over book, flatten only; REHEARSAL-only on the dev wallet; '
                    'never installed for the final run')
        p['provenance']['holdings_carry_over'] = dict(decision_id='IDEA-097 S4 (Yao, 2026-10-25)',
            formula='gate_a.initial_state takes exact chain units and the previous run\'s recorded cost basis from a '
                    'HoldingsCarryOver.v1 export; opening equity at that cost')
        action = RECOVERY_CHILDREN * RECOVERY_MAX_GAS * RECOVERY_MAX_GAS_PRICE
        p.update(gas_action_budget_units=action, exit_gas_reserve_units=positions * 2 * action)
        recovery = 'IDEA-096 AL-IMPL01 (PR282) for IDEA-097 S4'
        p['provenance']['gas_action_budget_units'] = dict(decision_id=recovery,
            formula='8 children*max_gas*max_gas_price; <=5 other-token revokes + approve + swap or abort pay-token '
                    'revoke; original authority only')
        p['provenance']['exit_gas_reserve_units'] = dict(decision_id=recovery,
            formula='%d positions*2 balanced exit children*gas_action_budget_units' % positions)
    validate_live(p)
    return Document.from_dict(p)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--exit-children', type=int, choices=(1, 2), required=True,
                        help='1 reproduces historical LD10-Q01; 2 is the LD10-P03 selection')
    parser.add_argument('--s1-config', type=Path, help="Keith's S1 block (JSON, weights 1/5 each); default: equal weight")
    parser.add_argument('--s1-decision', help='decision ID for the supplied S1 block; required with --s1-config')
    parser.add_argument('--scheduled-flatten-at', nargs='?', const=S3_FLATTEN_AT,
                        help='S3 (IDEA-092): sell everything at this UTC instant, then S2 again; default ' + S3_FLATTEN_AT)
    parser.add_argument('--fs1-rehearsal', action='store_true',
                        help='FS1-R (IDEA-093): the FS1 block with FS1 slippage 20 bp on the FS1-R dev window')
    parser.add_argument('--allowance-recovery', action='store_true',
                        help='IDEA-098: FS1-R with the IDEA-096 recovery gas envelope at the CAP-02 ceilings')
    parser.add_argument('--s5', action='store_true',
                        help='S5 (IDEA-104): FS1-R with recovery on a window ending Tue Oct 27 12:00 SGT')
    parser.add_argument('--carry-over', action='store_true',
                        help='S4 (IDEA-097): start from the previous run\'s exported book, flatten only, recovery gas')
    args = parser.parse_args(argv)
    if (args.s1_config is None) != (args.s1_decision is None):
        parser.error('--s1-config and --s1-decision must be supplied together')
    s1 = {} if args.s1_config is None else dict(s1_raw=args.s1_config.read_bytes(), s1_decision=args.s1_decision)
    p = build(args.exit_children, **s1, scheduled_flatten_at=args.scheduled_flatten_at, fs1_rehearsal=args.fs1_rehearsal,
              allowance_recovery=args.allowance_recovery, carry_over=args.carry_over, s5=args.s5)
    with args.output.open('xb') as stream:
        stream.write(p.payload + b'\n')
    print(p.digest('StrategyProfile.v1'))


if __name__ == '__main__':
    main()
