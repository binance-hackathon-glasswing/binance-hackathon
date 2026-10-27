"""Read local configuration metadata only; print no credentials, endpoints or wallet values."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys


def require(ok, reason):
    if not ok:
        raise SystemExit('Inputs refused: ' + reason)


here = Path(__file__).resolve().parents[1]
package = json.loads((here / 'package.json').read_text())
require(sys.version_info[:2] == (3, 12), 'use a Python3.12 venv')
for command in ('aws', 'session-manager-plugin', 'git', 'bash', 'lsof', 'shasum'):
    require(shutil.which(command) is not None, 'missing command ' + command)
repo = Path(os.environ['LARP_REPO']).resolve()
for name in ('OLD_BINDINGS', 'OLD_SIGNER', 'LARP_ENV_FILE', 'TOKEN_HISTORY', 'LARP_PY'):
    require(name in os.environ and Path(os.environ[name]).is_file(), 'missing private selector/file ' + name)
for name in ('tf-output.json', 'balance-rpc/selected-providers.json',
             'gate-a-prepared-20261017/runtime.json', 'gate-a-prepared-20261017/evidence.env'):
    require((repo / 'deploy/activation' / name).is_file(), 'missing existing private input ' + name)
for name in ('OLD_BINDINGS', 'OLD_SIGNER'):
    value = json.loads(Path(os.environ[name]).read_text())
    require((value.get('run_id'), value.get('database_name'), value.get('build_id')) ==
            (package['source_run_id'], package['source_database'], package['old_build_id']),
            name + ' does not bind original run8')
require(hashlib.sha256(Path(os.environ['TOKEN_HISTORY']).read_bytes()).hexdigest() == package['history_sha256'],
        'TOKEN_HISTORY differs from qualified pin')
require(os.environ.get('SCOPE_CONFIRMATION', '').strip(), 'set SCOPE_CONFIRMATION')
print(json.dumps(dict(local_private_inputs='PRESENT', source_run8_metadata='MATCH', history_pin='MATCH',
                      aws_connectivity='NOT_CHECKED', ready_to_start=False)))
