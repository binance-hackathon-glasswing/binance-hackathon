"""Offline operator-package refusal tests. No AWS, host or wallet access."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / 'docs/build/ops/rehearsal-install-s5-cost01-20261027'
spec = importlib.util.spec_from_file_location('s5_cost01_stage', PACKAGE / 'stage.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def bundle(tmp_path, unsafe=False):
    sha = lambda b: hashlib.sha256(b).hexdigest()
    files = {'release-manifest.json': json.dumps({'build_id': 'b' * 40}).encode(),
             'provision.sh': b'echo no-action\n', 'rds-ca.pem': b'synthetic CA', 'release/code.py': b'pass\n'}
    files['SHA256SUMS'] = ''.join(sha(v) + '  ' + k + '\n' for k, v in files.items()).encode()
    path = tmp_path / 'bundle.tar.gz'
    with tarfile.open(path, 'w:gz') as archive:
        root = tarfile.TarInfo('fixture'); root.type = tarfile.DIRTYPE; archive.addfile(root)
        for name, raw in files.items():
            member = tarfile.TarInfo('fixture/' + name); member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
        if unsafe:
            member = tarfile.TarInfo('fixture/escape'); member.type = tarfile.SYMTYPE
            member.linkname = '/etc/passwd'; archive.addfile(member)
    pins = dict(BUNDLE='fixture', BUNDLE_SHA256=sha(path.read_bytes()),
                MANIFEST_SHA256=sha(files['release-manifest.json']), PROVISION_SHA256=sha(files['provision.sh']),
                CA_SHA256=sha(files['rds-ca.pem']))
    return path, dict(build_id='b' * 40, pins=pins)


def test_stage_accepts_complete_checksums_without_extracting(tmp_path):
    path, config = bundle(tmp_path)
    assert stage.verify_bundle(path, config) == 4
    assert sorted(p.name for p in tmp_path.iterdir()) == ['bundle.tar.gz']


def test_stage_refuses_changed_bundle_before_extracting(tmp_path):
    path, config = bundle(tmp_path)
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(SystemExit, match='bundle digest'):
        stage.verify_bundle(path, config)


def test_stage_refuses_links_even_when_outer_digest_matches(tmp_path):
    path, config = bundle(tmp_path, unsafe=True)
    with pytest.raises(SystemExit, match='unsafe archive member'):
        stage.verify_bundle(path, config)


def test_stage_refuses_manifest_from_a_different_build(tmp_path):
    path, config = bundle(tmp_path)
    config['build_id'] = 'c' * 40
    with pytest.raises(SystemExit, match='manifest build'):
        stage.verify_bundle(path, config)


def test_ssm_access_denied_stops_instead_of_polling_for_half_an_hour(tmp_path):
    shutil.copyfile(PACKAGE / 'ssm_run.py', tmp_path / 'ssm_run.py')
    (tmp_path / 'check.sh').write_text('echo synthetic\n')
    cli = tmp_path / 'aws'
    cli.write_text('#!' + sys.executable + '\n' + '''import json,sys
if 'send-command' in sys.argv:
    print(json.dumps({'Command': {'CommandId': 'synthetic'}}))
else:
    print('AccessDenied: synthetic refused call', file=sys.stderr)
    sys.exit(1)
''')
    cli.chmod(0o700)
    result = subprocess.run([sys.executable, str(tmp_path / 'ssm_run.py'), 'check.sh'], cwd=tmp_path,
                            env=dict(os.environ, AWS_CLI=str(cli)), capture_output=True, text=True, timeout=8)
    assert result.returncode == 1
    assert 'AWS call failed' in result.stderr
    assert 'AccessDenied' not in result.stdout
    assert (tmp_path / 'results/primary-check-aws-error.txt').stat().st_mode & 0o077 == 0
