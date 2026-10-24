"""Run the exact 86b1476 `tools/deploy/prepare_shadow.py prepare` with ONE override: after the reviewed renderer has
filled the configs from the real Terraform output (database `larp`, so its example/Terraform cross-check passes),
point every config that names a database at the separate trial database (LARP_TRIAL_DB, e.g. larp_trial2) on the same RDS instance
(Yao's option 1, IDEA-066 PC-DEPLOY01). Nothing else changes; prepare() then computes every package hash over the
final bytes, and gate_a_check still requires all service configs to agree on the database.

  python3.12 -I prepare_trial_db.py <release checkout> prepare <prepare_shadow prepare args...>
"""
import os
import sys
from pathlib import Path
TARGET = os.environ['LARP_TRIAL_DB']
assert TARGET.startswith('larp_trial')
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
