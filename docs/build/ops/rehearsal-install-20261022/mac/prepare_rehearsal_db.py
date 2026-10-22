"""Run the release checkout's `tools/deploy/prepare_shadow.py` with ONE override: after the reviewed renderer has filled
the configs from the real Terraform output (database `larp`, so its example/Terraform cross-check passes), point every
config that names a database at `larp_rehearsal1` (SJ-04-DB01). Same pattern as the trial's prepare_trial_db.py.

  python3.12 -I prepare_rehearsal_db.py <release checkout> <prepare_shadow args...>
"""
import sys
from pathlib import Path
TARGET = 'larp_rehearsal1'
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / 'tools/deploy'))
sys.path.insert(0, str(root))
import render_host_configs  # noqa: E402
import prepare_shadow  # noqa: E402
assert prepare_shadow.renderer is render_host_configs
original = render_host_configs.render


def render(tf, wallet, rds_ca_sha256=None):
    if tf['database_name'] != 'larp':
        raise render_host_configs.Refused('expected the real Terraform database name')
    configs = original(tf, wallet, rds_ca_sha256)
    for config in configs.values():
        if 'database_name' in config:
            if config['database_name'] != 'larp':
                raise render_host_configs.Refused('unexpected rendered database name')
            config['database_name'] = TARGET
    return configs


render_host_configs.render = render
sys.exit(prepare_shadow.main(sys.argv[2:]))
