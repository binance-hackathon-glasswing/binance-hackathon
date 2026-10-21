"""Offline checks for LD12-M01 (IDEA-066): the collector stays read-only and the analysis is exact. No host access."""
import importlib.util
from pathlib import Path
import re

from larp.audit.delivery import DeliveryWorker

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'docs/build/ops/ld12-20261021'
spec = importlib.util.spec_from_file_location('ld12_analyse', FOLDER / 'analyse.py')
analyse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyse)


def test_backoff_matches_the_delivery_worker():
    worker = DeliveryWorker(store=None, receiver=None, retry_ms=30000, max_backoff_ms=300000)
    for attempts in range(1, 40):
        assert analyse.backoff_ms(attempts, 30000, 300000) == worker.backoff_ms(attempts)


def test_delivery_reconstructs_the_final_send_of_each_log():
    t = 1_000_000
    chunks = [
        [t, 0, 1, t + 2_000 + 30_000, 'ACK', '200', True],        # sent at t+2s, first try
        [t, 1, 3, t + 95_000 + 120_000, 'ACK', '200', True],      # third try sent at t+95s
        [t + 5_000, 0, 2, t + 70_000 + 60_000, 'ACK', '200', True],
        [t + 9_000, 0, 4, t + 999_999, 'PENDING', '503', False],
    ]
    out = analyse.delivery(chunks, 30000, 300000)
    assert (out['logs'], out['acked_logs'], out['unacked_logs']) == (3, 2, 1)
    assert out['dispatch_to_final_send_s']['max'] == 95.0  # the slower chunk of the first log
    assert out['dispatch_to_final_send_s']['min'] == 65.0
    assert out['chunk_status'] == {'ACK': 3, 'PENDING': 1}
    assert out['attempts'] == {'1': 1, '3': 1, '2': 1, '4': 1}


def test_cycle_counts_missing_fields_instead_of_guessing():
    rounds = [dict(kind='ROUND_PLANNED', started_ms=0, decision_ms=4_000, log_ms=5_000,
                   assessment_started_ms=1_000, assessment_completed_ms=3_000),
              dict(kind='ROUND_CLOSED', started_ms=10_000, decision_ms=None, log_ms=12_000),
              dict(log_ms=99)]
    out = analyse.cycle(rounds)
    assert out['with_start'] == 2 and out['missing']['decision_ms'] == 1
    assert out['start_to_decision_s']['n'] == 1 and out['start_to_log_s']['max'] == 5.0
    assert out['decision_to_log_s']['p50'] == 1.0 and out['assessment_s']['p50'] == 2.0


def test_sessions_and_archive():
    h = analyse.HOUR_MS
    rows = [[0, 3_600_000, 3_600_000, 'b1'], [3_610_000, 7_200_000, None, 'b1']]
    out = analyse.sessions(rows)
    assert out['count'] == 2 and out['restart_gap_s']['max'] == 10.0 and out['length_h']['max'] == 1.0
    arch = analyse.archive([[1, h + 90_000], [2, 2 * h + 30_000]],
                           [['anchor', h, 'ACK', 1, 0, ''], ['backup', h, 'PENDING', 2, 0, 'Timeout']])
    assert arch['anchor_store_lag_after_hour_s']['max'] == 90.0
    assert arch['outbox']['backup'] == dict(status={'PENDING': 1}, attempts={'2': 1}, errors=1)


def test_percentile_is_nearest_rank():
    assert analyse.percentile(list(range(1, 101)), 95) == 95
    assert analyse.percentile([7], 99) == 7 and analyse.percentile([], 50) is None


def test_collector_only_reads():
    text = (FOLDER / 'ops-collect.sh').read_text()
    assert 'READ ONLY' in text
    shell = re.sub(r"<<'PY'\n.*?\nPY", '', text, flags=re.S)
    assert not re.search(r'(^|\s)(>|>>)\s*[/\w$"]', shell)  # no shell redirection into files
    for word in ('mktemp', 'rm -', 'systemctl start', 'systemctl stop', 'systemctl restart', 'systemctl kill',
                 'systemctl enable', 'systemctl disable', ' aws ', 'INSERT', 'UPDATE ', 'DELETE', 'chmod', 'chown',
                 'write_text', 'write_bytes', 'larp-signer.service start'):
        assert word not in text, word
    assert not re.search(r'(?<![A-Za-z.])open\(', text)  # Popen(journalctl) only reads a child's stdout
    for unit_read in ('systemctl', 'journalctl', 'du', 'df', 'chronyc', 'free'):
        assert unit_read in text
