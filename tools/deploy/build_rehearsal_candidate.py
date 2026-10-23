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


def s1_block(raw):
    """The S1 block from its exact bytes. At about 100 USDT every weight must be 1/5 (SJ-09-PC01 C5)."""
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
    return block


def build(exit_children=1, *, s1_raw=None, s1_decision=None):
    """`exit_children=1` reproduces the historical LD10-Q01 bytes; LD10-P03 selects 2.

    With `s1_raw` (the exact bytes of Keith's S1 block) and `s1_decision`, the profile is TREND_GUARDED_VOL under the
    same SHADOW scope (SJ-11-RH01), and the reserve covers five positions x `exit_children`."""
    if exit_children not in (1, 2):
        raise ValueError('exit_children must be 1 (historical Q01) or 2 (LD10-P03)')
    if (s1_raw is None) != (s1_decision is None) or (
            s1_decision is not None and (type(s1_decision) is not str or not s1_decision.strip())):
        raise ContractError('An S1 block and the decision behind it go together')
    s1 = None if s1_raw is None else s1_block(s1_raw)
    def document(path):
        return Document.from_dict(json.loads(path.read_bytes()))
    authority = dict(seconds=660, margin=30, decision_id='IDEA-049-C LD04-V01 (Keegan, 2026-10-20)',
        data_hash=hashlib.sha256((EVIDENCE / 'ld02-execution-packet-20261020.json').read_bytes()).hexdigest())
    budget = dict(action_units=384000000000000, sizing_units=80004608000000,
        decision_id='IDEA-049-C LD10-Q01 (Keegan delegation, 2026-10-21)',
        data_hash=hashlib.sha256((EVIDENCE / 'signer-numeric-ceilings-20261021.json').read_bytes()).hexdigest())
    p = build_live_profiles(document(EVIDENCE / 'quotes-complete-20261020/quote-cost-summary.json'),
        document(ROOT / 'config/intelligence/red_flags.v1.json'), initial_gas_only=True,
        authority=authority, gas_budget=budget,
        **({} if s1 is None else dict(s1=s1, s1_decision=s1_decision)))['REHEARSAL'].read()
    p['provenance']['gas_action_budget_units']['formula'] = '2*1200000 max signed child gas*160000000 max gas price; cleanup disabled'
    p['provenance']['gas_sizing_budget_units']['formula'] = 'ceil(1000057*5/4) independently rounded child allowance at 64000000 expected gas price'
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
    validate_live(p)
    return Document.from_dict(p)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--exit-children', type=int, choices=(1, 2), required=True,
                        help='1 reproduces historical LD10-Q01; 2 is the LD10-P03 selection')
    parser.add_argument('--s1-config', type=Path, help="Keith's S1 block (JSON, weights 1/5 each); default: equal weight")
    parser.add_argument('--s1-decision', help='decision ID for the supplied S1 block; required with --s1-config')
    args = parser.parse_args(argv)
    if (args.s1_config is None) != (args.s1_decision is None):
        parser.error('--s1-config and --s1-decision must be supplied together')
    s1 = {} if args.s1_config is None else dict(s1_raw=args.s1_config.read_bytes(), s1_decision=args.s1_decision)
    p = build(args.exit_children, **s1)
    with args.output.open('xb') as stream:
        stream.write(p.payload + b'\n')
    print(p.digest('StrategyProfile.v1'))


if __name__ == '__main__':
    main()
