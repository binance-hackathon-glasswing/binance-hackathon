"""IDEA-105 TH-01: read-only probe of the Web3 hourly candle timestamp convention.

FS1, FS1-R and S5 need a TokenHistoryConfig.v1 whose `timestamp_evidence_sha256` hashes real evidence that an
hourly row stamped T covers [T, T+1h) (`timestamp_kind` OPEN). This polls the five names' latest hourly and
one-minute candles every 60 s across one UTC hour boundary, through the runtime's own history transport, and
assesses the IDEA-105 criteria: the bar in progress is stamped with its start and keeps changing (TS2), it is
frozen after its hour (TS3), and no row is stamped in the future (TS1); minute bars corroborate (TS4).

GET `market/rwa/tokens` and `market/candles` only: no quotes, swaps, signing, model or ai-seeds calls.

Usage, from the repository root with BINANCE_API_KEY / BINANCE_SECRET_KEY in .env (or the environment):
  python -m tools.th01_candle_timestamps probe --out ~/larp-th01/<new-dir> [--adjustment-version V]
  python -m tools.th01_candle_timestamps config --evidence <dir>/timestamp-evidence.json \
      --adjustment-version V --out-file <new token-history.json>

The probe runs 23-83 minutes (about 35-40 if started at :40-:45 past the hour); prefer the US session.
Exit codes: 0 PASS, 3 INCONCLUSIVE (rerun), 4 FAIL or refused.
"""
import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from larp.contracts import ContractError
from larp.marketdata.port import TOKENS, MarketPort
from larp.marketdata.web3 import Artifacts, Unavailable, Web3Client, credentials
from larp.strategy.schema import instant

ROOT = Path(__file__).resolve().parents[1]
MIN_MS, HOUR_MS = 60_000, 3_600_000
LEAD_MS, TAIL_MS, GRACE_MS = 8 * MIN_MS, 15 * MIN_MS, 5 * MIN_MS
# `available_at` is the local clock: a host a few seconds behind the provider must not fail TS1. An end-labelled
# hourly bar in progress would still lead by 5-55 minutes in every TS2 poll.
CLOCK_TOLERANCE_MS = 30_000
POLL_S = 60
REQUESTS = (('1h', 3), ('1m', 150))
MIN_NAMES = 3
UNUSED_WALLET = '0x' + '00' * 20  # MarketPort requires an address; candle and token reads never use it


def plan(start_ms):
    """The first whole UTC hour at least LEAD_MS away, and the end TAIL_MS after it."""
    boundary = -(-(start_ms + LEAD_MS) // HOUR_MS) * HOUR_MS
    return boundary, boundary + TAIL_MS


def _ms(value):
    return int(instant(value).timestamp() * 1000)


def _metadata(port):
    try:
        return {s: dict(tokenToShareRatio=row.get('tokenToShareRatio'), tokenPrice=row.get('tokenPrice'),
                        statusInfo=row.get('statusInfo'), available_at=r['available_at'],
                        content_hash=r['artifact_sha256'])
                for s, (row, r) in sorted(port.metadata().items())}
    except Unavailable as exc:
        return dict(error=str(exc))  # fixed outcome strings only; provider text is never kept


def poll(port, at_ms):
    symbols = {}
    for symbol in sorted(TOKENS):
        symbols[symbol] = {}
        for bar, limit in REQUESTS:
            try:
                r = port.candles(symbol, bar=bar, limit=limit)
                symbols[symbol][bar] = dict(available_at=r['available_at'], content_hash=r['content_hash'],
                                            rows=r['rows'])
            except Unavailable as exc:
                symbols[symbol][bar] = dict(error=str(exc))
    return dict(at_ms=at_ms, symbols=symbols)


def collect(port, *, clock, sleep, interval_s=POLL_S):
    start = clock()
    boundary, end = plan(start)
    record = dict(started_ms=start, boundary_ms=boundary, end_ms=end, interval_s=interval_s,
                  metadata_start=_metadata(port), polls=[])
    tick = 0
    while clock() < end:
        record['polls'].append(poll(port, clock()))
        tick += 1
        sleep(max(0, (start + tick * interval_s * 1000 - clock()) / 1000))
    record['metadata_end'] = _metadata(port)
    return record


def _stamp(row):
    value = row[5]
    return int(value) if type(value) is str and value.isdigit() else value


def _ok(entry):
    return type(entry) is dict and 'error' not in entry and type(entry.get('rows')) is list


def _aggregate(rows, first, last):
    """First open, max high, min low, last close and summed trades of minute rows stamped in [first, last]."""
    items = [r for r in rows if first <= _stamp(r) <= last]
    if not items:
        return None
    trades = None if any(r[6] is None for r in items) else sum(int(r[6]) for r in items)
    return [Decimal(str(items[0][0])), max(Decimal(str(r[1])) for r in items),
            min(Decimal(str(r[2])) for r in items), Decimal(str(items[-1][3])), trades]


def _shape(row):
    # A missing trade count compares prices only, never a guessed count.
    return [Decimal(str(row[0])), Decimal(str(row[1])), Decimal(str(row[2])), Decimal(str(row[3])),
            None if row[6] is None else int(row[6])]


def _symbol(polls, symbol, boundary):
    hour = boundary - HOUR_MS
    found = dict(ts1=True, ts2=False, ts3=False, ts4=dict(open_match=None, end_match=None), contradictions=[])
    try:
        for p in polls:
            for bar, _ in REQUESTS:
                entry = p['symbols'][symbol][bar]
                if not _ok(entry):
                    continue
                available = _ms(entry['available_at'])
                for row in entry['rows']:
                    stamp = _stamp(row)
                    if (type(stamp) is not int or stamp > available + CLOCK_TOLERANCE_MS
                            or (bar == '1h' and stamp % HOUR_MS)):
                        found['ts1'] = False
        live = []
        for p in polls:
            entry = p['symbols'][symbol]['1h']
            if hour + 5 * MIN_MS <= p['at_ms'] < boundary and _ok(entry) and entry['rows']:
                if _stamp(entry['rows'][-1]) == hour:
                    live.append(json.dumps(entry['rows'][-1], sort_keys=True))
        found['ts2'] = len(live) >= 2 and len(set(live)) > 1
        after = [p for p in polls if p['at_ms'] >= boundary + GRACE_MS and _ok(p['symbols'][symbol]['1h'])]
        frozen = [json.dumps(row, sort_keys=True) for p in after for row in p['symbols'][symbol]['1h']['rows']
                  if _stamp(row) == hour]
        found['ts3'] = len(frozen) >= 3 and len(set(frozen)) == 1
        if len(set(frozen)) > 1:
            found['contradictions'].append('TS3')
        last = next((p for p in reversed(after) if _ok(p['symbols'][symbol]['1m'])), None)
        if last is not None:
            hourly = [r for r in last['symbols'][symbol]['1h']['rows'] if _stamp(r) == hour]
            minutes = last['symbols'][symbol]['1m']['rows']
            oldest = min((_stamp(r) for r in minutes), default=None)
            if hourly and oldest is not None:
                target = _shape(hourly[0])

                def same(window):
                    if window is None:
                        return False
                    if None in (window[4], target[4]):
                        return window[:4] == target[:4]
                    return window == target
                if oldest <= hour:
                    found['ts4']['open_match'] = same(_aggregate(minutes, hour, boundary - MIN_MS))
                if oldest <= hour - 59 * MIN_MS:
                    found['ts4']['end_match'] = same(_aggregate(minutes, hour - 59 * MIN_MS, hour))
        if found['ts4']['end_match'] is True and found['ts4']['open_match'] is not True:
            found['contradictions'].append('TS4')
    except (KeyError, TypeError, ValueError, IndexError, InvalidOperation, ContractError):
        found['contradictions'].append('MALFORMED')
    if not found['ts1']:
        found['contradictions'].insert(0, 'TS1')
    return found


def assess(record):
    symbols = {s: _symbol(record['polls'], s, record['boundary_ms']) for s in sorted(TOKENS)}
    ok = sorted(s for s, v in symbols.items() if v['ts2'] and v['ts3'] and not v['contradictions'])
    if any(v['contradictions'] for v in symbols.values()):
        verdict = 'FAIL'
    elif len(ok) >= MIN_NAMES:
        verdict = 'PASS'
    else:
        verdict = 'INCONCLUSIVE'
    return dict(criteria='IDEA-105 TS1-TS4', verdict=verdict, names_ok=ok, minimum_names=MIN_NAMES,
                grace_ms=GRACE_MS, symbols=symbols)


def _encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode()


def _write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def config_bytes(evidence_sha256, adjustment_version):
    """Only the runtime's own validator decides what a valid TokenHistoryConfig.v1 is."""
    from larp.marketdata.history import configuration
    return _encoded(configuration(dict(schema='TokenHistoryConfig.v1', timestamp_kind='OPEN',
        timestamp_evidence_sha256=evidence_sha256, token_adjustment_version=adjustment_version)))


def _commit():
    try:
        return subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                              timeout=10, check=True).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def production_port(creds, raw_root):
    """The runtime's history transport (service.build_driver): five-second timeout, exact JSON decimals."""
    client = Web3Client(creds['BINANCE_API_KEY'], creds['BINANCE_SECRET_KEY'], artifacts=Artifacts(raw_root),
                        timeout=5, exact_decimals=True)
    return MarketPort(client, UNUSED_WALLET)


def _probe(args, port_factory, clock, sleep):
    out = Path(args.out).expanduser()
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)  # e.g. ~/larp-th01 on a first run
    out.mkdir(mode=0o700)  # a new directory only: never mix two runs' evidence
    port = port_factory(out)
    start = clock()
    boundary, end = plan(start)
    print('Polling every %d s until %s UTC (%d min); hour boundary %s UTC.' % (
        POLL_S, time.strftime('%H:%M', time.gmtime(end / 1000)), round((end - start) / MIN_MS),
        time.strftime('%H:%M', time.gmtime(boundary / 1000))), file=sys.stderr)
    record = collect(port, clock=clock, sleep=sleep)
    assessment = assess(record)
    evidence = dict(schema='TokenHistoryTimestampEvidence.v1', idea='IDEA-105', source_commit=_commit(),
                    tool='tools/th01_candle_timestamps.py', record=record, assessment=assessment)
    sha = _write_new(out / 'timestamp-evidence.json', _encoded(evidence))
    summary = dict(status='TH01_PROBE_COMPLETE', verdict=assessment['verdict'], names_ok=assessment['names_ok'],
                   timestamp_evidence_sha256=sha, evidence=str(out / 'timestamp-evidence.json'))
    if assessment['verdict'] == 'PASS' and args.adjustment_version is not None:
        summary['config_sha256'] = _write_new(out / 'token-history.json', config_bytes(sha, args.adjustment_version))
        summary['config'] = str(out / 'token-history.json')
    print(json.dumps(summary, sort_keys=True))
    return dict(PASS=0, INCONCLUSIVE=3).get(assessment['verdict'], 4)


def _config(args):
    raw = Path(args.evidence).read_bytes()
    evidence = json.loads(raw)
    if evidence.get('schema') != 'TokenHistoryTimestampEvidence.v1':
        raise ContractError('Not a TH-01 timestamp evidence file')
    assessment = assess(evidence['record'])  # re-assess: the stored verdict is not trusted
    if assessment['verdict'] != 'PASS' or assessment != evidence.get('assessment'):
        raise ContractError('Evidence does not re-assess as the stored PASS')
    sha = hashlib.sha256(raw).hexdigest()
    target = Path(args.out_file).expanduser()
    config_sha = _write_new(target, config_bytes(sha, args.adjustment_version))
    print(json.dumps(dict(status='TH01_CONFIG_WRITTEN', timestamp_evidence_sha256=sha, config=str(target),
                          config_sha256=config_sha), sort_keys=True))
    return 0


def main(argv=None, *, port_factory=None, clock=None, sleep=time.sleep):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    probe = sub.add_parser('probe', help='poll across one hour boundary and write the evidence')
    probe.add_argument('--out', required=True, help='new directory for raw/ and timestamp-evidence.json')
    probe.add_argument('--env-file', default='.env', help='Web3 credentials file (default .env, if present)')
    probe.add_argument('--adjustment-version', help="Keith's token_adjustment_version; on PASS also write the config")
    config = sub.add_parser('config', help='write token-history.json from PASS evidence')
    config.add_argument('--evidence', required=True)
    config.add_argument('--adjustment-version', required=True)
    config.add_argument('--out-file', required=True)
    args = parser.parse_args(argv)
    clock = clock or (lambda: int(time.time() * 1000))
    try:
        if args.command == 'config':
            return _config(args)
        if port_factory is None:
            env_file = args.env_file if Path(args.env_file).is_file() else None
            creds = credentials(env_file)
            port_factory = lambda out: production_port(creds, out / 'raw')  # noqa: E731
        return _probe(args, port_factory, clock, sleep)
    except (ContractError, Unavailable, OSError, ValueError, KeyError, TypeError) as exc:
        # Exception text is not printed: transport or file errors could echo private values.
        print(json.dumps(dict(status='TH01_PROBE_REFUSED', reason=type(exc).__name__)))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
