"""IDEA-104 R2: the run-7 (S5) run sheet pins one run, one database, the S5 profile, its probe, FS1's token history,
allowance recovery and the declared USDT top-up consistently, and retires run 6. Static checks only; nothing runs
against a host or the wallet."""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / 'docs/build/ops/rehearsal-install-s5-20261026'
RUN5 = ROOT / 'docs/build/ops/rehearsal-install-s4-20261025'
PROFILE = 'docs/build/evidence/s5-rehearsal-profile-20261026/rehearsal-s5.json'
RUN, DB = 'larp-dev-rehearsal-20261026-s5', 'larp_rehearsal7'
OLD_RUN, OLD_DB, OLD_BUILD = 'larp-dev-rehearsal-20261026-s4b', 'larp_rehearsal6', '7fc9f6019b54dccaf13b886c2e1123e703abf67a'


def text(name):
    return (SHEET / name).read_text()


def test_profile_and_probe_pins_match_the_committed_profile():
    from tools.deploy.ld10_readonly_packet import script
    raw = (ROOT / PROFILE).read_bytes()
    m3, m4 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py')
    assert 'PROFILE=' + PROFILE + '\n' in m3 and m3.count('--profile "$WT/$PROFILE"') == 2
    assert 'PROBE_SHA=' + hashlib.sha256(script(raw).encode()).hexdigest() + '\n' in m3
    assert "PROFILE = wt / '" + PROFILE + "'" in m4
    assert "PROFILE_SHA = '" + hashlib.sha256(raw).hexdigest() + "'" in m4
    for name in ('mac/m1-local-bundle.sh', 'mac/m1-fetch-bundle.sh'):
        assert PROFILE in text(name) and '== ' + hashlib.sha256(raw).hexdigest()[:8] + '*' in text(name), name
        assert 'grep -q larp-s5-rehearsal-v1 "$BUILD" -- larp/marketdata/history.py' in text(name), name


def test_one_new_run_and_database_and_run_6_retired():
    m3, m4, p4 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py'), text('host/p4-init-activate-start.sh')
    assert f"run_id='{RUN}', database_name='{DB}'" in m3
    assert f"b['run_id'] == '{OLD_RUN}'" in m3 and f"b['database_name'] == '{OLD_DB}'" in m3
    assert f"RUN, DB = '{RUN}', '{DB}'" in m4
    assert f'RUN={RUN}\n' in p4 and f'"database_name": *"{DB}"' in p4
    for name in ('mac/prepare_rehearsal_db.py', 'mac/setup_rehearsal_db.py'):
        assert f"'{DB}'" in text(name)
    for name in ('host/r1-retire-primary.sh', 'host/r1-retire-signer.sh'):
        assert f'RUN={OLD_RUN}; BUILD={OLD_BUILD}' in text(name), name
    assert f'"database_name": *"{OLD_DB}"' in text('host/r1-retire-primary.sh')
    assert not (SHEET / 'host/x1-export-holdings.sh').exists() and not (SHEET / 'mac/x1-save-export.py').exists()
    for name in ('mac/m3-recapture-assemble.sh', 'mac/m4-prepare.py', 'host/p4-init-activate-start.sh',
                 'mac/prepare_rehearsal_db.py', 'mac/setup_rehearsal_db.py', 'mac/d1-create-db.sh'):
        for stale in ('larp_rehearsal5', '58b31806', '379c476b', "'--carry-over'", 'CARRY_OVER'):
            assert stale not in text(name), (name, stale)


def test_recovery_token_history_and_top_up_reach_every_config():
    m3, m4, p3 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py'), text('host/p3-install-primary.sh')
    assert '--allowance-recovery' in m3 and '--accept-usdt-surplus-units "$TOPUP"' in m3
    assert "'--allowance-recovery', '--token-history-config', str(TOKEN_HISTORY)" in m4
    assert "rt['driver'].get('allowance_recovery') is True" in m4 and "reviewed['allowance_recovery'] is True" in m4
    assert "== (CONFIG_FILE, hashlib.sha256(history_raw).hexdigest())" in m4
    assert "'untrusted-router-policy.json', 'token-history.json']" in m4
    assert "changed == ['build_id', 'database_name', 'run_id']" in m4 and "startswith('1e052e26')" in m4
    assert "state['cash_units'] >= MIN_CASH_UNITS" in m4 and 'MIN_CASH_UNITS = 98_320_000' in m4
    assert p3.count('token-history.json') >= 3 and 'runtime_token_history readable_by=larp-runtime' in p3


def test_synthetic_history_is_refused_by_m4_guard():
    """The M4 guard rejects the test suite's synthetic semantics (all-'e' evidence hash, SYNTHETIC version)."""
    from tests.marketdata.test_session_history import SEMANTICS
    guard = (lambda h: len(set(h['timestamp_evidence_sha256'])) > 1
             and not h['token_adjustment_version'].upper().startswith('SYNTHETIC'))
    assert 'len(set(history[\'timestamp_evidence_sha256\'])) > 1' in text('mac/m4-prepare.py')
    assert not guard(SEMANTICS)
    assert guard(dict(SEMANTICS, timestamp_evidence_sha256='0123456789abcdef' * 4, token_adjustment_version='v1'))


def test_unchanged_steps_are_byte_identical_to_the_run_5_sheet():
    for name in ('ssm_run.py', 'host/p2-provision.sh', 'host/p5-start-execution.sh', 'host/s1-install-signer.sh',
                 'host/s1b-credential-mode-test.sh', 'host/s2-key-check-start-signer.sh', 'mac/m2-upload-bundle.sh',
                 'mac/m9-cleanup-s3-package.sh', 'mac/chain-monitor.py', 'mac/signer-reach.sh',
                 'checks/trading-status.sh', 'checks/primary-status.sh', 'checks/db-top-queries.sh'):
        assert (SHEET / name).read_bytes() == (RUN5 / name).read_bytes(), name


def test_scripts_parse():
    for path in sorted(SHEET.rglob('*.sh')):
        assert subprocess.run(['bash', '-n', str(path)]).returncode == 0, path
    for path in sorted(SHEET.rglob('*.py')):
        compile(path.read_text(), str(path), 'exec')
