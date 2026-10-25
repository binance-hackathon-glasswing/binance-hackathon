"""IDEA-097: the run-5 (S4) run sheet pins one run, one database, the S4 profile, its probe, the carry-over export and
allowance recovery consistently. Static checks plus one synthetic X1 round trip; nothing runs against a host."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / 'docs/build/ops/rehearsal-install-s4-20261025'
PROFILE = 'docs/build/evidence/s4-rehearsal-profile-20261025/rehearsal-s4-deterministic.json'
RUN, DB = 'larp-dev-rehearsal-20261025-s4', 'larp_rehearsal5'
OLD_RUN, OLD_DB, OLD_BUILD = 'larp-dev-rehearsal-20261024-s2', 'larp_rehearsal4', '2d160073d0f26c1f35c6c977c3dd6167a5ee0d26'


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
        for needed in ('larp/strategy/carry_over.py', 'larp/marketdata/quote_verifier.py', 'KIT_OPEN_STATE'):
            assert needed in text(name), (name, needed)


def test_one_new_run_and_database_and_run_4_retired():
    m3, m4, p4 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py'), text('host/p4-init-activate-start.sh')
    assert f"run_id='{RUN}', database_name='{DB}'" in m3
    assert f"RUN, DB = '{RUN}', '{DB}'" in m4 and f"SOURCE_RUN = '{OLD_RUN}'" in m4
    assert f'RUN={RUN}\n' in p4 and f'"database_name": *"{DB}"' in p4
    for name in ('mac/prepare_rehearsal_db.py', 'mac/setup_rehearsal_db.py'):
        assert f"'{DB}'" in text(name)
    for name in ('host/r1-retire-primary.sh', 'host/r1-retire-signer.sh', 'host/x1-export-holdings.sh'):
        assert f'RUN={OLD_RUN}; BUILD={OLD_BUILD}' in text(name), name
    assert f'"database_name": *"{OLD_DB}"' in text('host/r1-retire-primary.sh')
    for name in ('mac/m3-recapture-assemble.sh', 'mac/m4-prepare.py', 'host/p4-init-activate-start.sh',
                 'mac/prepare_rehearsal_db.py', 'mac/setup_rehearsal_db.py', 'mac/d1-create-db.sh'):
        assert 'larp_rehearsal3' not in text(name) and 'eb55d76a' not in text(name), name


def test_recovery_and_carry_over_reach_every_config():
    m3, m4 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py')
    assert '--allowance-recovery' in m3
    assert "'--allowance-recovery', '--carry-over', str(CARRY_OVER)" in m4
    assert "rt['driver'].get('allowance_recovery') is True" in m4
    assert "reviewed['allowance_recovery'] is True" in m4
    assert "dict(old_value['signing_policy'], allowance_recovery=True)" in m4
    assert "'56e029afe93819b75edb39bd1b5b32e5a6cef2c4f9d7fcfcaff47007d3acc8c1'" in m4


def test_scripts_parse():
    for path in sorted(SHEET.rglob('*.sh')):
        assert subprocess.run(['bash', '-n', str(path)]).returncode == 0, path
    for path in sorted(SHEET.rglob('*.py')):
        compile(path.read_text(), str(path), 'exec')


def test_x1_output_round_trips_into_the_s4_starting_state(tmp_path):
    from larp.runtime import gate_a
    from tests.strategy.test_s4_carry_over import export, held_capture, s4_shadow
    sheet = tmp_path / 'sheet'
    (sheet / 'mac').mkdir(parents=True)
    (sheet / 'results').mkdir()
    (sheet / 'mac/x1-save-export.py').write_bytes((SHEET / 'mac/x1-save-export.py').read_bytes())
    line = json.dumps(export(source_run_id=OLD_RUN), sort_keys=True, separators=(',', ':'))
    (sheet / 'results/x1-export-holdings-stdout.txt').write_text('CARRY_OVER ' + line + '\nX1_DONE\n')
    out = subprocess.run([sys.executable, '-I', str(sheet / 'mac/x1-save-export.py')], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    saved = (sheet / 'private/holdings-carry-over.json').read_bytes()
    assert json.loads(out.stdout)['sha256'] == hashlib.sha256(saved).hexdigest()
    assert (sheet / 'private/holdings-carry-over.json').stat().st_mode & 0o777 == 0o600
    state = gate_a.initial_state(held_capture(), s4_shadow(), RUN, carry_over=json.loads(saved))
    assert state['positions']['SKHYB']['units'] == 137879758388310745
    # A second save never overwrites, and a truncated or in-flight export is refused.
    again = subprocess.run([sys.executable, '-I', str(sheet / 'mac/x1-save-export.py')], capture_output=True, text=True)
    assert again.returncode != 0
    (sheet / 'private/holdings-carry-over.json').unlink()
    (sheet / 'results/x1-export-holdings-stdout.txt').write_text('CARRY_OVER ' + line + '\n')
    assert subprocess.run([sys.executable, '-I', str(sheet / 'mac/x1-save-export.py')]).returncode != 0
    busy = json.dumps(export(source_run_id=OLD_RUN, reservations={'r': {}}), sort_keys=True)
    (sheet / 'results/x1-export-holdings-stdout.txt').write_text('CARRY_OVER ' + busy + '\nX1_DONE\n')
    assert subprocess.run([sys.executable, '-I', str(sheet / 'mac/x1-save-export.py')]).returncode != 0


def test_x1_reads_live_reservations_and_the_execution_barrier_not_the_projection_copy():
    """Review fix (PR284): `projection['portfolio']['reservations']` is never updated (ledger_from rebuilds reservations
    from the table), so X1's in-flight check must read the reservations table and unfinished execution records."""
    x1 = text('host/x1-export-holdings.sh')
    assert "FROM reservations WHERE run_id=%s AND units<>0" in x1
    assert "FROM execution_records WHERE run_id=%s AND NOT terminal" in x1
    assert "portfolio.get('reservations'" not in x1
    assert 'reservations=reservations, positions=positions' in x1
