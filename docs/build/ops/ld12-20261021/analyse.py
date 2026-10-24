"""LD12-M01 offline analysis of an ops-collect.sh packet (IDEA-066 LD12-M01 M2-M8). No network, no host access.

python docs/build/ops/ld12-20261021/analyse.py PACKET.json > SUMMARY.json

PACKET.json is the decoded packet: the two JSON lines (host, database) that ops-collect.sh gzips. The summary
reports observed distributions only; it adopts no LD14 value.
"""
import json
import sys

HOUR_MS = 3_600_000
HTTP_TIMEOUT_S = 15  # socket timeout only; not a whole-request or positive-ACK deadline


def percentile(values, q):
    """Nearest-rank percentile of a non-empty list; None when empty."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * q // 100))
    return ordered[int(rank) - 1]


def spread(values):
    values = [v for v in values if v is not None]
    return dict(n=len(values), p50=percentile(values, 50), p95=percentile(values, 95), p99=percentile(values, 99),
                max=max(values, default=None), min=min(values, default=None))


def backoff_ms(attempts, retry_ms, max_backoff_ms):
    """Same rule as DeliveryWorker.backoff_ms: the delay after the attempts-th send."""
    return min(retry_ms * 2 ** min(attempts - 1, 32), max_backoff_ms)


def delivery(chunks, retry_ms, max_backoff_ms):
    """M2 correction: stored attempt clocks only; actual network send and ACK times are absent."""
    logs, statuses, codes, attempts = {}, {}, {}, {}
    for row in chunks:
        timestamp_ms, _index, tries, next_ms, status, code, acked = row[:7]
        identity = ('event', row[7]) if len(row) == 8 else ('legacy_timestamp', timestamp_ms)
        statuses[status] = statuses.get(status, 0) + 1
        codes[str(code)] = codes.get(str(code), 0) + 1
        attempts[str(tries)] = attempts.get(str(tries), 0) + 1
        log = logs.setdefault(identity, dict(acked=True, send_ms=None, timestamp_ms=timestamp_ms))
        if status != 'ACK' or not acked or tries < 1:
            log['acked'] = False
            continue
        send = next_ms - backoff_ms(tries, retry_ms, max_backoff_ms)
        log['send_ms'] = send if log['send_ms'] is None else max(log['send_ms'], send)
    delays = [(v['send_ms'] - v['timestamp_ms']) / 1000 for v in logs.values() if v['acked'] and v['send_ms'] is not None]
    return dict(logs=len(logs), acked_logs=len(delays), unacked_logs=sum(not v['acked'] for v in logs.values()),
                chunk_status=statuses, last_code=codes, attempts=attempts,
                dispatch_to_latest_attempt_clock_s=spread(delays),
                actual_dispatch_to_ack_s='NOT_MEASURED', configured_socket_timeout_s=HTTP_TIMEOUT_S,
                grouping=('event_ordinal' if all(len(row) == 8 for row in chunks) else 'legacy_timestamp'),
                note='Stored attempt clocks precede DB/network work; no send or positive-ACK timestamps. '
                     'A stored ACK may belong to an earlier concurrent attempt. Socket timeout is not a whole-request deadline. '
                     'Legacy timestamp groups may merge events; chunk rows alone do not prove expected-chunk completeness.')


def cycle(rounds):
    """M3: start -> decision -> log per round, and the assessment's own start/complete."""
    def gap(r, a, b):
        return (r[b] - r[a]) / 1000 if r.get(a) is not None and r.get(b) is not None else None
    decided = [r for r in rounds if r.get('started_ms') is not None]
    missing = {k: sum(r.get(k) is None for r in decided) for k in ('decision_ms', 'log_ms', 'assessment_completed_ms')}
    return dict(rounds=len(rounds), with_start=len(decided), missing=missing,
                kinds={k: sum(r.get('kind') == k for r in rounds) for k in sorted({str(r.get('kind')) for r in rounds})},
                start_to_decision_s=spread([gap(r, 'started_ms', 'decision_ms') for r in decided]),
                decision_to_log_s=spread([gap(r, 'decision_ms', 'log_ms') for r in decided]),
                start_to_log_s=spread([gap(r, 'started_ms', 'log_ms') for r in decided]),
                assessment_s=spread([gap(r, 'assessment_started_ms', 'assessment_completed_ms') for r in decided]))


def archive(anchors, outbox):
    """M4: time-of-hour offsets only, not slot-to-store lag; actual slot bindings are absent."""
    kinds = {}
    for kind, _slot, status, tries, _next, error in outbox:
        k = kinds.setdefault(kind, dict(status={}, attempts={}, errors=0))
        k['status'][status] = k['status'].get(status, 0) + 1
        k['attempts'][str(tries)] = k['attempts'].get(str(tries), 0) + 1
        k['errors'] += bool(error)
    return dict(anchors=len(anchors), anchor_stored_offset_within_hour_s=spread([(ms % HOUR_MS) / 1000 for _, ms in anchors]),
                outbox=kinds, slot_to_store_lag_s='NOT_MEASURED')


def sessions(rows):
    """M5: process sessions, their length and the downtime between one session's last heartbeat and the next."""
    lengths = [((ended or beat) - start) / 3_600_000 for start, beat, ended, _ in rows]
    gaps = [(rows[i + 1][0] - (rows[i][2] or rows[i][1])) / 1000 for i in range(len(rows) - 1)]
    return dict(count=len(rows), builds=sorted({r[3] for r in rows}), length_h=spread(lengths),
                restart_gap_s=spread(gaps))


def summary(host, db):
    uploader = host.get('uploader') or {}
    retry, cap = uploader.get('retry_ms') or 30000, uploader.get('max_backoff_ms') or 300000
    events = db.get('events') or {}
    units = {u: {k: v.get(k) for k in ('ActiveState', 'UnitFileState', 'NRestarts', 'MemoryCurrent', 'MemoryPeak',
                                       'MemoryMax', 'MemoryHigh')} for u, v in (host.get('units') or {}).items()}
    return dict(
        schema='LD12OpsSummary.v2',
        identity=dict(run_id=db.get('run_id'), database_name=db.get('database_name'),
                      runtime=host.get('runtime'), operations=host.get('operations'), run=db.get('run')),
        delivery=dict(delivery(db.get('chunks') or [], retry, cap), retry_ms=retry, max_backoff_ms=cap,
                      interval_seconds=uploader.get('interval_seconds')),
        cycle=cycle(events.get('rounds') or []), event_kinds=events.get('kinds'),
        archive=archive(db.get('anchors') or [], db.get('archive') or []),
        sessions=sessions(db.get('sessions') or []),
        resources=dict(units=units, journal=host.get('journal'), disk=host.get('disk'), memory=host.get('memory'),
                       swap_total=host.get('memory_swap_total'), nproc=host.get('nproc'),
                       db_size=db.get('db_size'), largest_tables=db.get('tables'), jobs=db.get('jobs'),
                       rounds_by_status=db.get('rounds'), systemd=host.get('systemd_version')),
        clock=host.get('chrony'),
        collection_errors=db.get('errors'),
        missing_measurement=['actual network-send and positive-ACK timings; hard delivery bound', 'anchor slot-to-store lag', 'signed execution/finality/worker-drain timings', 'stalled-call behaviour on the signed '
                             'path', 'memory history (only the current/peak values systemd reports)'])


def main(argv=None):
    path = (argv or sys.argv[1:])[0]
    host, db = (json.loads(line) for line in open(path, encoding='utf-8').read().strip().splitlines())
    print(json.dumps(summary(host, db), indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
