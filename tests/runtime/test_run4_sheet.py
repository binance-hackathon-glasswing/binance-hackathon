"""IDEA-089 S2-7: the RC7 run-4 (S2) run sheet pins one run, one database, the S2 profile, its probe and the router
policy pair consistently. Static checks only: no script is executed against a host, AWS or a database.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RC6, RC7 = ROOT / 'docs/build/ops/rehearsal-install-rc6-20261023', ROOT / 'docs/build/ops/rehearsal-install-rc7-20261024'
PROFILE = 'docs/build/evidence/s2-rehearsal-profile-20261024/rehearsal-s2-deterministic.json'
RUN3_PROFILE = 'docs/build/evidence/s1-rehearsal-profile-20261023/rehearsal-s1-deterministic.json'
RUN, DB = 'larp-dev-rehearsal-20261024-s2', 'larp_rehearsal4'
RUN3, RC6_BUILD = 'larp-dev-rehearsal-20261024', '9dc5edab61b6bffdb3c75cc4d498bb651a91ba43'
POLICY_SHA = '05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5'


def text(name):
    return (RC7 / name).read_text()


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
        for needed in ('larp/marketdata/basis.py', 'larp/marketdata/quote_verifier.py', 'KIT_OPEN_STATE'):
            assert needed in text(name), (name, needed)


def test_one_run_and_one_database_across_the_sheet():
    m3, m4, p4 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py'), text('host/p4-init-activate-start.sh')
    assert f"run_id='{RUN}', database_name='{DB}'" in m3
    assert f"RUN, DB = '{RUN}', '{DB}'" in m4
    assert f'RUN={RUN}\n' in p4 and f'"database_name": *"{DB}"' in p4
    assert f"NEW = '{DB}'" in text('mac/setup_rehearsal_db.py')
    assert f"TARGET = '{DB}'" in text('mac/prepare_rehearsal_db.py')
    assert f'tunnel-{DB}.log' in text('mac/d1-create-db.sh')
    for path in RC7.rglob('*'):
        if path.is_file() and path.name != 'README.md':
            for run in set(re.findall(r'larp-dev-rehearsal-\d{8}(?:-s2)?', path.read_text())):
                assert run in (RUN, RUN3) or path.name in ('setup_rehearsal_db.py', 'chain-monitor.py'), (path, run)
            for db in set(re.findall(r'larp_rehearsal\d', path.read_text())):
                assert db in (DB, 'larp_rehearsal3') or path.name == 'setup_rehearsal_db.py', (path, db)


def test_retirement_and_diff_base_are_run_three():
    for name in ('host/r1-retire-primary.sh', 'host/r1-retire-signer.sh'):
        assert f'RUN={RUN3}; BUILD={RC6_BUILD}\n' in text(name), name
    assert '"database_name": *"larp_rehearsal3"' in text('host/r1-retire-primary.sh')
    m3, m4 = text('mac/m3-recapture-assemble.sh'), text('mac/m4-prepare.py')
    assert f"b['run_id'] == '{RUN3}'" in m3 and f"b['build_id'] == '{RC6_BUILD}'" in m3
    assert "b['database_name'] == 'larp_rehearsal3'" in m3
    # Run 3's installed signer.json (IDEA-049-C SJ-11-A1).
    assert "'49cb1a08c3d2a3b3c7409ad1c3beb68e0a43e3282bd9296ad7bcec770530209a'" in m4
    assert "changed == ['build_id', 'database_name', 'run_id']" in m4


def test_s2_10_router_policy_pair_is_written_checked_and_readable():
    m4, p3 = text('mac/m4-prepare.py'), text('host/p3-install-primary.sh')
    assert ("'--untrusted-router-policy-file', '/etc/larp/untrusted-router-policy.json', "
            "'--untrusted-router-policy-sha256', POLICY_SHA") in m4
    assert f"POLICY_SHA = '{POLICY_SHA}'" in m4
    assert "== ('/etc/larp/untrusted-router-policy.json', POLICY_SHA), 'runtime router policy pair" in m4
    assert 'runuser -u larp-runtime -g larp-runtime -G larp-evidence -- $P -I -c' in p3
    assert 'untrusted_router_policy_sha256' in p3 and 'readable_by=larp-runtime' in p3


def test_s2_6_s2_12_quote_check_covers_every_name_both_sides():
    from larp.marketdata.port import TOKENS
    q1 = text('mac/q1-quote-check.sh')
    assert 'for s in ' + ' '.join(sorted(TOKENS)) + '; do' in q1 and 'for side in BUY SELL; do' in q1
    assert '-m tools.deploy.quote_check --symbol "$s" --side "$side"' in q1 and 'Q1_DONE' in q1
    # The tool pins run 3's profile; S2 differs from it only where the quote path does not read.
    s2, s1 = (json.loads((ROOT / p).read_bytes()) for p in (PROFILE, RUN3_PROFILE))
    from tools.deploy import quote_check
    assert quote_check.PROFILE == ROOT / RUN3_PROFILE
    read = ('slippage_bps', 'impact_bps', 'per_trade_cap_units', 'cost_reserve_units', 'quote_age_seconds', 'mode',
            'gas_action_budget_units', 'gas_sizing_budget_units', 'quote_cost_summary', 'impact_median_bps')
    assert all(s2[k] == s1[k] for k in read)
    assert {k for k in s2 if s2[k] != s1[k]} == {'trade_after', 'new_risk_end', 'flatten_start', 'signing_end',
                                                 'policy_id', 's1', 'provenance'}


def test_approvals_are_supplied_not_prewritten():
    p4, m4 = text('host/p4-init-activate-start.sh'), text('mac/m4-prepare.py')
    assert 'REVIEWER=${1:?' in p4 and 'APPROVAL=${2:?' in p4 and '--reviewer "$REVIEWER"' in p4
    assert "SCOPE = os.environ.get('SCOPE_CONFIRMATION', '').strip()" in m4
    assert "require(SCOPE != ''" in m4


def test_unchanged_steps_are_byte_identical_to_the_rc6_sheet():
    changed = {'README.md', 'mac/m1-local-bundle.sh', 'mac/m1-fetch-bundle.sh', 'mac/d1-create-db.sh',
               'mac/setup_rehearsal_db.py', 'mac/prepare_rehearsal_db.py', 'mac/m3-recapture-assemble.sh',
               'mac/m4-prepare.py', 'host/r1-retire-primary.sh', 'host/r1-retire-signer.sh',
               'host/p3-install-primary.sh', 'host/p4-init-activate-start.sh'}
    rc6 = {str(p.relative_to(RC6)) for p in RC6.rglob('*') if p.is_file()}
    rc7 = {str(p.relative_to(RC7)) for p in RC7.rglob('*') if p.is_file()}
    assert rc7 == rc6 | {'mac/q1-quote-check.sh'}
    for name in sorted(rc6 - changed):
        assert (RC6 / name).read_bytes() == (RC7 / name).read_bytes(), name


def test_shell_scripts_parse():
    for path in sorted(RC7.rglob('*.sh')):
        result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
        assert result.returncode == 0, (path, result.stderr)
    for path in sorted(RC7.rglob('*.py')):
        compile(path.read_text(), str(path), 'exec')
