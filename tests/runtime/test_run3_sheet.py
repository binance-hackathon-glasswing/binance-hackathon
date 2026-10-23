"""IDEA-049-C SJ-11: the RC6 run-3 (S1) run sheet pins one run, one database, the S1 profile and its probe consistently.

Static checks only: no script is executed against a host, AWS or a database.
"""
import hashlib
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RC5, RC6 = ROOT / 'docs/build/ops/rehearsal-install-rc5-20261023', ROOT / 'docs/build/ops/rehearsal-install-rc6-20261023'
PROFILE = 'docs/build/evidence/s1-rehearsal-profile-20261023/rehearsal-s1-deterministic.json'
RUN, DB = 'larp-dev-rehearsal-20261024', 'larp_rehearsal3'
RUN2, RC5_BUILD = 'larp-dev-rehearsal-20261023', 'd53d1b7aa8f18790f0bdde73cfdcdbed95555043'


def text(name):
    return (RC6 / name).read_text()


def test_profile_and_probe_pins_match_the_committed_profile():
    from tools.deploy.ld10_readonly_packet import script
    raw = (ROOT / PROFILE).read_bytes()
    m3, m4 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py')
    assert 'PROFILE=' + PROFILE + '\n' in m3 and '--profile "$WT/$PROFILE"' in m3
    assert m3.count('--profile "$WT/$PROFILE"') == 2  # the probe and the caps review read the same profile
    assert 'PROBE_SHA=' + hashlib.sha256(script(raw).encode()).hexdigest() + '\n' in m3
    assert "PROFILE = wt / '" + PROFILE + "'" in m4
    assert "PROFILE_SHA = '" + hashlib.sha256(raw).hexdigest() + "'" in m4
    for name in ('mac/m1-local-bundle.sh', 'mac/m1-fetch-bundle.sh'):
        assert PROFILE in text(name) and '== ' + hashlib.sha256(raw).hexdigest()[:8] + '*' in text(name), name
        assert 'larp/marketdata/basis.py' in text(name), name


def test_one_run_and_one_database_across_the_sheet():
    m3, m4, p4 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py'), text('host/p4-init-activate-start.sh')
    assert f"run_id='{RUN}', database_name='{DB}'" in m3
    assert f"RUN, DB = '{RUN}', '{DB}'" in m4
    assert f'RUN={RUN}\n' in p4 and f'"database_name": *"{DB}"' in p4
    assert f"NEW = '{DB}'" in text('mac/setup_rehearsal_db.py')
    assert f"TARGET = '{DB}'" in text('mac/prepare_rehearsal_db.py')
    assert f'tunnel-{DB}.log' in text('mac/d1-create-db.sh')
    # Every run and database name the sheet uses is run 3's or, for retirement and the diff base, run 2's.
    for path in RC6.rglob('*'):
        if path.is_file() and path.name != 'README.md':
            for run in set(re.findall(r'larp-dev-rehearsal-\d{8}', path.read_text())):
                assert run in (RUN, RUN2) or path.name in ('setup_rehearsal_db.py', 'chain-monitor.py'), (path, run)


def test_retirement_and_diff_base_are_run_two():
    for name in ('host/r1-retire-primary.sh', 'host/r1-retire-signer.sh'):
        assert f'RUN={RUN2}; BUILD={RC5_BUILD}\n' in text(name), name
    assert '"database_name": *"larp_rehearsal2"' in text('host/r1-retire-primary.sh')
    m3, m4 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py')
    assert f"b['run_id'] == '{RUN2}'" in m3 and f"b['build_id'] == '{RC5_BUILD}'" in m3
    # Run 2's installed signer.json (IDEA-049-C SJ-10 J2 / SJ-10-A1).
    assert "'1a4cda6fcbad7066ddd8c9375115a5156320b629f6c81d3c0aa3a64390c2b1b1'" in m4
    assert "changed == ['build_id', 'database_name', 'run_id']" in m4


def test_approvals_are_supplied_not_prewritten():
    p4, m4 = text('host/p4-init-activate-start.sh'), text('mac/m4-prepare.py')
    assert 'REVIEWER=${1:?' in p4 and 'APPROVAL=${2:?' in p4 and '--reviewer "$REVIEWER"' in p4
    assert 'Yao Zhu chat approval' not in p4
    assert "SCOPE = os.environ.get('SCOPE_CONFIRMATION', '').strip()" in m4
    assert "require(SCOPE != ''" in m4


def test_unchanged_steps_are_byte_identical_to_the_rc5_sheet():
    changed = {'README.md', 'mac/m1-local-bundle.sh', 'mac/m1-fetch-bundle.sh', 'mac/d1-create-db.sh',
               'mac/setup_rehearsal_db.py', 'mac/prepare_rehearsal_db.py', 'mac/m3-recapture-assemble.sh',
               'mac/m4-prepare.py', 'host/r1-retire-primary.sh', 'host/r1-retire-signer.sh',
               'host/p4-init-activate-start.sh'}
    rc5 = {str(p.relative_to(RC5)) for p in RC5.rglob('*') if p.is_file()}
    rc6 = {str(p.relative_to(RC6)) for p in RC6.rglob('*') if p.is_file()}
    assert rc5 == rc6
    for name in sorted(rc5 - changed):
        assert (RC5 / name).read_bytes() == (RC6 / name).read_bytes(), name


def test_shell_scripts_parse():
    for path in sorted(RC6.rglob('*.sh')):
        result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
        assert result.returncode == 0, (path, result.stderr)
