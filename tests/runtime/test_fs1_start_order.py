"""PR296-RV01: execute the actual shell steps against synthetic systemctl/runuser, never a host."""
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHEETS = [ROOT / 'docs/build/ops/rehearsal-install-s5-20261026', ROOT / 'docs/build/ops/final-fs1']


def run_step(tmp_path, sheet, name, *, execution='inactive', runtime='inactive', restarts='0'):
    bin_dir = tmp_path / 'bin'; bin_dir.mkdir(exist_ok=True)
    log = tmp_path / 'calls'
    stubs = dict(systemctl='''#!/bin/bash
echo "systemctl $*" >> "$CALLS"
case "$1" in
  is-active)
    case "$2" in
      larp-execution) echo "$EXECUTION_STATE";;
      larp-runtime) echo "$RUNTIME_STATE";;
      *) echo active;;
    esac;;
  show) if [[ $2 == larp-execution ]]; then echo "$EXECUTION_RESTARTS"; else echo 0; fi;;
esac
''', runuser='#!/bin/bash\necho "runuser $*" >> "$CALLS"\n', sleep='#!/bin/bash\nexit 0\n',
        grep='#!/bin/bash\nexit 0\n')
    for command, body in stubs.items():
        path = bin_dir / command; path.write_text(body); path.chmod(0o755)
    path = tmp_path / name
    path.write_text((sheet / 'host' / name).read_text().replace('cd /opt/larp/current', 'cd "' + str(tmp_path) + '"'))
    env = dict(os.environ, PATH=str(bin_dir) + ':' + os.environ['PATH'], CALLS=str(log),
        EXECUTION_STATE=execution, RUNTIME_STATE=runtime, EXECUTION_RESTARTS=restarts)
    out = subprocess.run(['bash', str(path), 'synthetic-reviewer', 'synthetic-approval'], env=env,
                         text=True, capture_output=True)
    return out, log.read_text() if log.exists() else ''


@pytest.mark.parametrize('sheet', SHEETS)
def test_init_activates_without_starting_planning_or_disabling_execution(tmp_path, sheet):
    out, calls = run_step(tmp_path, sheet, 'p4-init-activate-start.sh')
    assert out.returncode == 0, out.stdout + out.stderr
    assert 'larp.runtime.service init ' in calls and 'larp.runtime.service activate ' in calls
    assert 'systemctl start larp-runtime' not in calls
    assert 'disable' not in calls and 'P4_DONE' in out.stdout


@pytest.mark.parametrize('sheet', SHEETS)
@pytest.mark.parametrize('state', ['active', 'activating', 'deactivating', 'failed'])
def test_init_refuses_a_running_or_transitioning_runtime(tmp_path, sheet, state):
    out, calls = run_step(tmp_path, sheet, 'p4-init-activate-start.sh', runtime=state)
    assert out.returncode == 5 and 'larp.runtime.service init ' not in calls


@pytest.mark.parametrize('sheet', SHEETS)
@pytest.mark.parametrize('execution,restarts', [('inactive', '0'), ('failed', '0'), ('active', '1')])
def test_runtime_never_starts_without_clean_execution(tmp_path, sheet, execution, restarts):
    out, calls = run_step(tmp_path, sheet, 'p6-start-runtime.sh', execution=execution, restarts=restarts)
    assert out.returncode == 5
    assert 'systemctl start larp-runtime' not in calls and 'P6_DONE' not in out.stdout


@pytest.mark.parametrize('sheet', SHEETS)
def test_runtime_starts_after_execution_and_checks_both_services(tmp_path, sheet):
    out, calls = run_step(tmp_path, sheet, 'p6-start-runtime.sh', execution='active', runtime='active')
    assert out.returncode == 0, out.stdout + out.stderr
    assert calls.index('systemctl is-active larp-execution') < calls.index('systemctl start larp-runtime')
    assert 'P6_DONE' in out.stdout


def test_final_scripts_parse_and_have_no_rehearsal_identity_or_dependency():
    for path in (SHEETS[1] / 'host').glob('*.sh'):
        assert subprocess.run(['bash', '-n', str(path)]).returncode == 0
        assert 'larp_rehearsal' not in path.read_text() and 'larp-dev-' not in path.read_text()
