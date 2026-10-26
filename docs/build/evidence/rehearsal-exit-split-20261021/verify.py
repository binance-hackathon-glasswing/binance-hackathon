"""LD10-P03 public reproduction: profile bytes, exit-child bound, reserve and funding arithmetic.

Offline only. Uses committed files; no private packet, network, host, key or funding.
Run from the repository root: PYTHONPATH=. python3 docs/build/evidence/rehearsal-exit-split-20261021/verify.py
"""
import hashlib
import json
from pathlib import Path

from larp.execution_live.caps_review import exit_children
from larp.risk.planner import exit_parts
from larp.strategy.schema import ceil, fraction
from tools.deploy.build_rehearsal_candidate import build

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
Q01 = ROOT / 'docs/build/evidence/rehearsal-qualified-inputs-20261021'
RECORDED_NATIVE_WEI = 2_694_498_869_362_886  # dated 2026-10-21 14:10:31Z read-only packet
PLANNING_PAIRS = 15


def main():
    raw = (HERE / 'rehearsal-deterministic.json').read_bytes()
    doc = build(exit_children=2)
    assert doc.payload + b'\n' == raw
    assert build().payload + b'\n' == (Q01 / 'rehearsal-deterministic.json').read_bytes()
    p, old = doc.read(), build().read()
    assert {k for k in p if p[k] != old[k]} == {'exit_gas_reserve_units', 'provenance'}
    scope = json.loads((HERE / 'rehearsal-deterministic-scope.json').read_bytes())
    assert scope['profile_file_sha256'] == hashlib.sha256(raw).hexdigest()
    assert scope['profile_document_sha256'] == doc.digest('StrategyProfile.v1')
    assert scope['effective_falsifier_authority'] == p['falsifier_authority'] == 'SHADOW'
    assert scope['selected_coverage_file'] is None and not scope['signing_enabled']

    cap = p['per_trade_cap_units']
    action = p['gas_action_budget_units']
    hard_value = ceil(fraction(p['hard_name_weight']) * p['expected_equity_units'])
    children = exit_parts(hard_value, cap)
    # Largest position value still exited in at most `children` balanced children.
    covered_value = cap * children * 10000 // 10100
    reserve = 4 * children * action
    assert children == 2 and reserve == p['exit_gas_reserve_units'] == 3_072_000_000_000_000
    target = (PLANNING_PAIRS + 4 * children) * action
    additional = target - RECORDED_NATIVE_WEI

    packet = json.loads((Q01 / 'coverage-decision-deterministic.json').read_bytes())
    row = next(r for r in packet['quote_rows'] if r['symbol'] == 'NVDAB' and r['side'] == 'SELL')
    p02 = exit_children(row['pay_units'], row['receive_units'], cap * 10**12, children)
    assert sum(p02) == row['pay_units'] and len(p02) == 2

    result = dict(schema='LD10P03PublicCheck.v1', status='REPRODUCED_PENDING_FRESH_CHILD_QUOTES',
        profile_file_sha256=hashlib.sha256(raw).hexdigest(),
        profile_document_sha256=doc.digest('StrategyProfile.v1'),
        per_trade_cap_units=cap, hard_name_value_units=hard_value, max_children_per_position=children,
        max_value_within_children_units=covered_value, positions=4,
        exit_gas_reserve_wei=reserve, planning_target_wei=target,
        additional_vs_recorded_wei=additional,
        p02_nvdab_sell=dict(full_pay_units=row['pay_units'], proceeds_raw=row['receive_units'],
                            planned_children=p02, note='historical hypothetical; sizing proxy only'),
        signing_enabled=False, ready_to_install=False, funding_authorized=False)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
