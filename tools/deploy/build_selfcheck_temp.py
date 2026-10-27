"""IDEA-110 TEMP-SC: the temporary sub-1-USDT final-wallet self-check profile, stamped at preparation time.

From the reviewed FS1 recovery profile's exact bytes, change only: `policy_id`, the self-check (0.90 USDT, same name),
its own 1000bp entry-cost floor and the windows. With T = the stamp rounded up to the next whole minute: buy from T to
T+1h, flat by T+2h (= trade_after), new risk ends and the terminal flatten starts at T+2h+1min, signing ends at T+3h.
The temp policy never opens S1 risk, so the one self-check BUY is the only buy. Everything must end by the F-127
pause (2026-10-28T10:00Z), or validation refuses the profile. No ports, keys or installation.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from larp.contracts import ContractError, Document
from larp.strategy import self_check
from larp.strategy.profiles import validate_live
from larp.strategy.schema import instant

DECISION = 'IDEA-110 TEMP-SC (Keith, 2026-10-28 SGT)'
PAY_UNITS = 900_000  # 0.90 USDT: above the 1000bp floor at the pinned costs (0.589 USDT), below 1 USDT


def stamp(now):
    """T: `now` (an aware datetime or an ISO-8601 UTC instant) rounded up to the next whole minute."""
    if type(now) is str:
        now = instant(now)
    if type(now) is not datetime or now.tzinfo is None:
        raise ContractError('The stamp needs an aware UTC time')
    now = now.astimezone(timezone.utc)
    whole = now.replace(second=0, microsecond=0)
    return whole if whole == now else whole + timedelta(minutes=1)


def iso(value):
    return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def build(*, fs1_raw, now):
    """The temp profile for preparation at `now`, from the exact pinned FS1 recovery profile bytes."""
    from tools.deploy.prepare_fs1 import PROFILE_SHA
    from larp.runtime import gate_a
    if type(fs1_raw) is not bytes or gate_a.digest(fs1_raw) != PROFILE_SHA:
        raise ContractError('The temp self-check is built only from the reviewed FS1 recovery profile')
    p = json.loads(fs1_raw)
    t = stamp(now)
    window = dict(buy_after=iso(t), buy_until=iso(t + timedelta(hours=1)), flat_by=iso(t + timedelta(hours=2)))
    terminal = dict(trade_after=iso(t + timedelta(hours=2)), new_risk_end=iso(t + timedelta(hours=2, minutes=1)),
                    flatten_start=iso(t + timedelta(hours=2, minutes=1)), signing_end=iso(t + timedelta(hours=3)))
    if instant(terminal['signing_end']) > instant(self_check.TEMP_PAUSE):
        raise ContractError('Too late: the temp self-check must end by the F-127 pause ' + self_check.TEMP_PAUSE)
    p['activation_self_check'] = dict(p['activation_self_check'], pay_units=PAY_UNITS, **window)
    p.update(terminal, policy_id=self_check.TEMP_POLICY_ID, **{self_check.TEMP_COST_KEY: self_check.TEMP_COST_CAP_BPS})
    p['provenance']['activation_self_check'] = dict(decision_id=DECISION,
        formula='FS1 self-check name; pay 0.90 USDT (< 1 USDT total); buy T..T+1h, flat by T+2h, '
                'T = preparation time rounded up to the minute')
    p['provenance']['policy_id'] = dict(decision_id=DECISION,
        formula='Temporary final-wallet self-check only: no S1 risk, ends by the F-127 pause; not FS1')
    p['provenance'][self_check.TEMP_COST_KEY] = dict(decision_id=DECISION,
        formula='Self-check BUY only: 1000bp entry-cost cap and its validate_live gas floor; FS1 minimum unchanged')
    for key in terminal:
        p['provenance'][key] = dict(decision_id=DECISION,
            formula='trade_after = flat_by = T+2h; new risk end = flatten = T+2h+1min; signing end T+3h')
    validate_live(p)
    return Document.from_dict(p)


def main(argv=None):
    from tools.deploy.prepare_fs1 import PROFILE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--now', help='ISO-8601 UTC stamp for review; default: the current time')
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
