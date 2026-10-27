"""IDEA-110 TEMP-SC: the temporary sub-1-USDT final-wallet self-check profile (W2: fixed buy window).

From the reviewed FS1 recovery profile's exact bytes, change only: `policy_id`, the self-check (0.90 USDT, same name),
its own 1000bp entry-cost floor and the windows. W2 (Keith, 2026-10-28 SGT): buy 12:00-14:00 SGT Oct 28
(04:00-06:00Z), flat by 07:00Z (= trade_after), new risk ends and the terminal flatten starts at 07:01Z, signing ends
at 08:00Z. The temp policy never opens S1 risk, so the one self-check BUY is the only buy. Everything ends by the
F-127 pause (2026-10-28T10:00Z). No ports, keys or installation.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from larp.contracts import ContractError, Document
from larp.strategy import self_check
from larp.strategy.profiles import validate_live
from larp.strategy.schema import instant

DECISION = 'IDEA-110 TEMP-SC W2 (Keith, 2026-10-28 SGT)'
PAY_UNITS = 900_000  # 0.90 USDT: above the 1000bp floor at the pinned costs (0.589 USDT), below 1 USDT
WINDOW = dict(buy_after='2026-10-28T04:00:00Z', buy_until='2026-10-28T06:00:00Z', flat_by='2026-10-28T07:00:00Z')
TERMINAL = dict(trade_after='2026-10-28T07:00:00Z', new_risk_end='2026-10-28T07:01:00Z',
                flatten_start='2026-10-28T07:01:00Z', signing_end='2026-10-28T08:00:00Z')


def build(*, fs1_raw, now):
    """The temp profile from the exact pinned FS1 recovery profile bytes; refused once its buy window has closed."""
    from tools.deploy.prepare_fs1 import PROFILE_SHA
    from larp.runtime import gate_a
    if type(fs1_raw) is not bytes or gate_a.digest(fs1_raw) != PROFILE_SHA:
        raise ContractError('The temp self-check is built only from the reviewed FS1 recovery profile')
    if (now if type(now) is datetime else instant(now)) >= instant(WINDOW['buy_until']):
        raise ContractError('Too late: the temp self-check buy window closed at ' + WINDOW['buy_until'])
    p = json.loads(fs1_raw)
    p['activation_self_check'] = dict(p['activation_self_check'], pay_units=PAY_UNITS, **WINDOW)
    p.update(TERMINAL, policy_id=self_check.TEMP_POLICY_ID, **{self_check.TEMP_COST_KEY: self_check.TEMP_COST_CAP_BPS})
    p['provenance']['activation_self_check'] = dict(decision_id=DECISION,
        formula='FS1 self-check name; pay 0.90 USDT (< 1 USDT total); buy 04:00-06:00Z Oct 28 (12:00-14:00 SGT), '
                'flat by 07:00Z')
    p['provenance']['policy_id'] = dict(decision_id=DECISION,
        formula='Temporary final-wallet self-check only: no S1 risk, ends by the F-127 pause; not FS1')
    p['provenance'][self_check.TEMP_COST_KEY] = dict(decision_id=DECISION,
        formula='Self-check BUY only: 1000bp entry-cost cap and its validate_live gas floor; FS1 minimum unchanged')
    for key in TERMINAL:
        p['provenance'][key] = dict(decision_id=DECISION,
            formula='trade_after = flat_by = 07:00Z; new risk end = flatten = 07:01Z; signing end 08:00Z, Oct 28')
    validate_live(p)
    return Document.from_dict(p)


def main(argv=None):
    from tools.deploy.prepare_fs1 import PROFILE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--now', help='ISO-8601 UTC preparation time for review; default: the current time')
    args = parser.parse_args(argv)
    now = instant(args.now) if args.now else datetime.now(timezone.utc)
    p = build(fs1_raw=PROFILE.read_bytes(), now=now)
    with args.output.open('xb') as stream:
        stream.write(p.payload + b'\n')
    from larp.runtime import gate_a
    print(json.dumps(dict(file_sha256=gate_a.digest(p.payload + b'\n'), strategy_profile_v1=p.digest('StrategyProfile.v1'),
                          **p.read()['activation_self_check'])))


if __name__ == '__main__':
    main()
