"""M4 (Mac, local only; IDEA-110 TEMP-SC): bind the A1-approved M3 outputs to the release manifest of
temp-selfcheck-e261bcfc, check the signer config against it, and write one private package for both hosts.

  LARP_PY=<venv python> python3 -I mac/m4-bind-package.py <M3 stamp>

Refuses unless profile/signer/execution are exactly the A1 hashes and the bundle is Keith's published release.
No AWS call: the upload is m4-upload.sh (Yao). stdout carries hashes and the P3/S1 commands only.
"""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys

STAMP = sys.argv[1]
MAIN = Path(os.environ.get('LARP_REPO', '/Users/songyaozhu/binance-hackathon'))
REL = Path(__file__).resolve().parents[5]
BASE = MAIN / 'deploy/activation/selfcheck-temp-20261028'
PRIVATE, BUNDLE = BASE / 'private', BASE / 'bundle-e261/x/larp-e261bcfc7a33-x86_64'
PREPARED = REL / 'deploy/activation' / ('selfcheck-temp-' + STAMP) / 'prepared-with-caps'
SERVICES = PRIVATE / ('services-' + STAMP)
OUT = PRIVATE / ('package-' + STAMP)
PY = os.environ['LARP_PY']
BUILD = 'e261bcfc7a339a5e28388b843798b4197a9993a6'
# A1 (Yao Zhu + Isaac, relayed in chat 2026-10-28 SGT); for e261bcfc signer/execution differ from the approved
# 9e574c31/1be4c303 only in build_id, run under Yao's instruction to run this release.
A1 = {'strategy-profile.json': 'b2e85827c65d99b709c0d958c2b1bf734e62cc271bba35ac536284dcba1b4187',
      'signer.json': '91cf3f78ce4d9745e18bf5872c93a93449ef285386d2461306cb4b4bfbf7a5af',
      'execution.json': '061ee8b2280b68c42f4221f70e9b9f4781c4998cc069b3814f930c635b9abfd6'}
MANIFEST_SHA = '7635b1965a7655f22953d5d61702af1ac57c26ac1b386db575e3c48ac766d41c'
digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require(ok, why):
    if not ok:
        raise SystemExit('M4 refused: ' + why)


require(digest(BUNDLE / 'release-manifest.json') == MANIFEST_SHA, 'bundle manifest is not the published release')
require(not OUT.exists(), 'package directory exists; choose a new M3 stamp')
OUT.mkdir(mode=0o700)
for n in ('runtime.json', 'uploader.json', 'operations.json', 'strategy-profile.json', 'session-calendar.json',
          'initial-state.json', 'evidence.env', 'token-history.json', 'model-routing.json'):
    shutil.copyfile(PREPARED / n, OUT / n)
for n in ('execution.json', 'signer.json', 'untrusted-router-policy.json'):
    shutil.copyfile(SERVICES / n, OUT / n)
for n, sha in A1.items():
    require(digest(OUT / n) == sha, n + ' differs from the A1 hash')
rt = json.loads((OUT / 'runtime.json').read_text())
require((rt['run_id'], rt['database_name'], rt['build_id'], rt['mode']) ==
        ('larp-final-selfcheck-temp', 'larp_final_selfcheck', BUILD, 'live'), 'runtime identity differs')
(OUT / 'registration-evidence.json').write_text(json.dumps(dict(
    schema='RegistrationEvidence.v1', build_id=BUILD,
    repository='https://github.com/binance-hackathon-glasswing/binance-hackathon',
    evidence_ref=('Final wallet registered by the organisers (F-125); its issued ai-seeds secret. IDEA-110 TEMP-SC '
                  'release temp-selfcheck-e261bcfc, run larp-final-selfcheck-temp, database larp_final_selfcheck, '
                  'profile b2e85827, signer 91cf3f78; A1 Yao Zhu + Isaac 2026-10-28 SGT.'))) + '\n')
root = BUNDLE / 'release'
call = lambda args: subprocess.run(args, cwd=root, check=True, stdout=subprocess.DEVNULL)
call([PY, '-m', 'larp.runtime.preflight', '--bind', str(BUNDLE / 'release-manifest.json'), '--root', str(root),
      '--output', str(OUT / 'release.json'), '--registration-evidence', str(OUT / 'registration-evidence.json'),
      '--config', str(OUT / 'operations.json'), '--runtime-config', str(OUT / 'runtime.json'),
      '--service-config', 'uploader=' + str(OUT / 'uploader.json'),
      '--service-config', 'execution=' + str(OUT / 'execution.json'),
      '--service-config', 'signer=' + str(OUT / 'signer.json')])
call([PY, '-m', 'larp.signer.service', 'check', '--config', str(OUT / 'signer.json'),
      '--manifest', str(OUT / 'release.json'), '--root', str(root)])
names = ['release.json', 'runtime.json', 'uploader.json', 'operations.json', 'execution.json', 'signer.json',
         'strategy-profile.json', 'session-calendar.json', 'initial-state.json', 'evidence.env',
         'registration-evidence.json', 'untrusted-router-policy.json', 'token-history.json', 'model-routing.json']
hashes = {n: digest(OUT / n) for n in names}
prefix = 'releases/final-selfcheck-temp-' + STAMP.lower() + '/'
record = dict(record_id='IDEA-110 M4', build_id=BUILD, run_id=rt['run_id'], database=rt['database_name'],
              package=OUT.name, prefix=prefix, hashes=hashes)
(OUT / 'package-record.json').write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
print(json.dumps(record, sort_keys=True))
primary = [n for n in names if n != 'signer.json']
print('M4U: bash mac/m4-upload.sh ' + STAMP)
print('P3: python3 -I ssm_run.py host/p3-install-primary.sh @artifact_bucket ' + prefix + ' '
      + ' '.join(f'{n}={hashes[n]}' for n in primary))
print('S1: python3 -I ssm_run.py --signer host/s1-install-signer.sh @artifact_bucket ' + prefix + ' '
      + ' '.join(f'{n}={hashes[n]}' for n in ('release.json', 'signer.json', 'untrusted-router-policy.json')))
print('M4_DONE')
