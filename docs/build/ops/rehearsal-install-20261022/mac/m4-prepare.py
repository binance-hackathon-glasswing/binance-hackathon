"""M4 (Mac, Yao): fresh wallet capture and signed-rehearsal preparation for the new build, then one bound release.json
for BOTH hosts, a local signer check, and upload of the host package (IDEA-049-C SJ-06 J3).

  LARP_PY=<venv python> OLD_SIGNER=<SJ-04 signer.json> /opt/homebrew/bin/python3.12 -I mac/m4-prepare.py <M3 stamp>

The signer refuses unless its release manifest is byte-identical to the one the run registered, so release.json binds
runtime, uploader, operations, execution and signer configs together and both hosts install the same bytes.
stdout carries hashes and flags only: no URLs, keys, hosts or wallet values.
"""
from pathlib import Path
import datetime, hashlib, json, os, shlex, subprocess, sys
here = Path(__file__).resolve().parents[1]
env = dict(line.split('=', 1) for line in (here / 'build.env').read_text().split())
BUILD, BUNDLE = env['BUILD'], env['BUNDLE']
STAMP = sys.argv[1]
main = Path('/Users/songyaozhu/binance-hackathon')
wt = main / '.claude/worktrees' / ('release-' + BUILD[:7])
private = here / 'private'
py = os.environ['LARP_PY']
RUN, DB = 'larp-dev-rehearsal-20261022', 'larp_rehearsal1'
PROFILE = wt / 'docs/build/evidence/rehearsal-exit-split-20261021/rehearsal-deterministic.json'
PROFILE_SHA = 'e95d5842d15c07e0e2bb5dab761e6a1730f69aed4af4cfce2596eec68e070250'
POLICY = wt / 'docs/build/evidence/untrusted-router-policy-ld03-20261020.json'
POLICY_SHA = '05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5'
ADOPTION = 'IDEA-083 LD11-RH01 scoped deterministic rehearsal (Keegan 2026-10-21); IDEA-049-C SJ-06 (Yao Zhu 2026-10-22)'
release = here / 'bundle/x' / BUNDLE
digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert subprocess.run(['git', '-C', str(wt), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip() == BUILD
assert not subprocess.run(['git', '-C', str(wt), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
assert digest(PROFILE) == PROFILE_SHA and digest(POLICY) == POLICY_SHA
assert digest(release / 'release-manifest.json') == env['MANIFEST_SHA256']
assembly = json.loads((private / f'assembly-{STAMP}.json').read_text().strip().splitlines()[-1])
signer = private / f'signer-{STAMP}' / 'signer.json'
assert assembly['status'] == 'ASSEMBLED_REQUIRES_APPROVAL' and assembly['numeric_status'] == 'COVERED'
assert digest(signer) == assembly['signer_config_sha256']
# SJ-06 J2: Yao's approval covers this candidate only if it differs from SJ-04's f632bbcb... in build_id alone.
old = Path(os.environ['OLD_SIGNER'])
assert digest(old) == 'f632bbcba22ac79d5c38590984d3250534db0aa6a4f23e21f3c38af9ca47880b'
old_value, new_value = json.loads(old.read_bytes()), json.loads(signer.read_bytes())
changed = sorted(k for k in set(old_value) | set(new_value) if old_value.get(k) != new_value.get(k))
assert changed == ['build_id'] and new_value['build_id'] == BUILD, 'signer.json differs beyond build_id: new decision needed'
print(json.dumps(dict(signer_diff_vs_f632bbcb=changed)))
reviewed = json.loads((private / f'review-{STAMP}' / 'execution-config.json').read_text())
results = here / 'results'; results.mkdir(exist_ok=True)
# prepare_shadow writes only inside the release checkout's git-ignored deploy/activation/ (as the trial's r6 did).
out = wt / 'deploy/activation' / ('package-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
capture = Path('/private/tmp') / ('larp-rehearsal-capture-' + out.name[8:]); capture.mkdir(mode=0o700)
step = [0]


def call(args, cwd=wt, allow_fail=False):
    step[0] += 1
    p = subprocess.run(args, cwd=cwd, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), text=True, capture_output=True)
    (results / f'm4-step-{step[0]}.stdout').write_text(p.stdout)
    (results / f'm4-step-{step[0]}.stderr').write_text(p.stderr)  # private, never echoed
    print(p.stdout.strip() or json.dumps({'step': step[0], 'exit': p.returncode}), flush=True)
    if p.returncode and not allow_fail:
        raise SystemExit(p.returncode)
    return p.stdout


wallet = json.loads((main / 'deploy/activation/gate-a-prepared-20261017/runtime.json').read_text())['wallet_address']
rpc = main / 'deploy/activation/balance-rpc/selected-providers.json'
tf = main / 'deploy/activation/tf-output.json'
contact = next(shlex.split(line)[0].split('=', 1)[1] for line in
               (main / 'deploy/activation/gate-a-prepared-20261017/evidence.env').read_text().splitlines()
               if line.startswith('LARP_SEC_USER_AGENT='))
call([py, 'tools/deploy/prepare_shadow.py', 'capture', '--env-file', str(main / '.env'), '--wallet', wallet,
      '--artifact-root', str(capture / 'web3'), '--balance-rpc-config', str(rpc), '--output', str(capture / 'inputs.json')])
call([py, str(here / 'mac/prepare_rehearsal_db.py'), str(wt), 'prepare', '--terraform-output', str(tf),
      '--profile', str(PROFILE), '--capture', str(capture / 'inputs.json'), '--run-id', RUN, '--build-id', BUILD,
      '--rds-ca-sha256', env['CA_SHA256'], '--sec-contact', contact, '--balance-rpc-config', str(rpc),
      '--execution', 'service', '--runtime-mode', 'dev', '--model-adoption-ref', ADOPTION, '--out', str(out)])
rt = json.loads((out / 'runtime.json').read_text())
assert (rt['run_id'], rt['build_id'], rt['mode'], rt['database_name']) == (RUN, BUILD, 'dev', DB)
assert (rt['driver']['execution'], rt['driver']['assessor'], rt['driver']['intelligence_mode']) == ('service', 'deterministic', 'live')
assert rt['driver']['strategy_profile_sha256'] == PROFILE_SHA
# execution.json: the exact reviewed SJ-06 execution config, plus the runtime-only settings the assembly does not pin.
sys.path.insert(0, str(wt / 'tools/deploy')); sys.path.insert(0, str(wt))
import render_host_configs, prepare_shadow
rendered = render_host_configs.render(render_host_configs.outputs(json.loads(tf.read_text())), wallet, env['CA_SHA256'])['execution.json']
# Execution reads through the first (primary) qualified provider: BNB Chain public (KG-REV01 read-RPC approval).
first = prepare_shadow.rpc_providers(rpc)[0]
execution = dict(reviewed, runtime_secret_id=rendered['runtime_secret_id'], market_artifact_root=rendered['market_artifact_root'],
                 chain_artifact_root=rendered['chain_artifact_root'], signer_timeout_seconds=rendered['signer_timeout_seconds'],
                 rpc_url=first['url'], rpc_source_id=first['source_id'])
for key in ('run_id', 'build_id', 'mode', 'wallet_address', 'database_host', 'database_name', 'database_ca_file',
            'database_ca_sha256', 'region'):
    assert execution[key] == rt[key], key
assert (execution['untrusted_router_policy_file'], execution['untrusted_router_policy_sha256']) == ('/etc/larp/untrusted-router-policy.json', POLICY_SHA)
assert execution['strategy_profile_sha256'] == PROFILE_SHA and execution['database_user'] == 'larp_execution'
(out / 'execution.json').write_bytes(json.dumps(execution, indent=1, sort_keys=True).encode() + b'\n')
(out / 'signer.json').write_bytes(signer.read_bytes())
(out / 'untrusted-router-policy.json').write_bytes(POLICY.read_bytes())
(out / 'registration-evidence.json').write_text(json.dumps(dict(
    schema='RegistrationEvidence.v1', build_id=BUILD, repository='https://github.com/binance-hackathon-glasswing/binance-hackathon',
    evidence_ref=('Existing team registration (GAP-41/F-113, issued ai-seeds secret) unchanged; no new organiser registration. '
                  f'Build {BUILD} = canonical after PR243 (LV-01); bundle provenance {env["MIRROR_RUN"]}. Dev signed rehearsal '
                  f'{RUN}, database {DB} (IDEA-049-C SJ-06).'))) + '\n')
call([py, '-m', 'larp.runtime.gate_a_check', '--prepared', str(out), '--ci-manifest', str(release / 'release-manifest.json'),
      '--release-root', str(release / 'release'), '--rds-ca', str(release / 'rds-ca.pem'),
      '--artifact-root', '/Users/songyaozhu/larp-artifacts'], allow_fail=True)
call([py, '-m', 'larp.runtime.preflight', '--bind', str(release / 'release-manifest.json'), '--root', str(release / 'release'),
      '--output', str(out / 'release.json'), '--registration-evidence', str(out / 'registration-evidence.json'),
      '--config', str(out / 'operations.json'), '--runtime-config', str(out / 'runtime.json'),
      '--service-config', 'uploader=' + str(out / 'uploader.json'), '--service-config', 'execution=' + str(out / 'execution.json'),
      '--service-config', 'signer=' + str(out / 'signer.json')], cwd=release / 'release')
call([py, '-m', 'larp.signer.service', 'check', '--config', str(out / 'signer.json'), '--manifest', str(out / 'release.json'),
      '--root', str(release / 'release')], cwd=release / 'release')
names = ['release.json', 'runtime.json', 'uploader.json', 'operations.json', 'execution.json', 'signer.json',
         'strategy-profile.json', 'session-calendar.json', 'initial-state.json', 'evidence.env',
         'registration-evidence.json', 'untrusted-router-policy.json']
hashes = {n: digest(out / n) for n in names}
prefix = 'releases/rehearsal-' + out.name[8:].lower() + '/'
t = json.loads(tf.read_text()); bucket = t['artifact_bucket']['value'] if isinstance(t['artifact_bucket'], dict) else t['artifact_bucket']
for n in names:
    subprocess.run(['/opt/homebrew/bin/aws', '--profile', 'larp', '--region', 'ap-southeast-2', 's3', 'cp', '--only-show-errors',
                    str(out / n), f's3://{bucket}/{prefix}{n}'], check=True)
primary = [n for n in names if n != 'signer.json']
record = dict(record_id='SJ-06-J3', build_id=BUILD, run_id=RUN, database=DB, package=out.name, prefix=prefix, hashes=hashes,
              signer_config_sha256=assembly['signer_config_sha256'], execution_rpc_source_id=first['source_id'])
(out / 'package-record.json').write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
print(json.dumps(record, sort_keys=True))
print('P3: python3.12 -I ssm_run.py host/p3-install-primary.sh @artifact_bucket ' + prefix + ' '
      + ' '.join(f'{n}={hashes[n]}' for n in primary))
print('S1: python3.12 -I ssm_run.py --signer host/s1-install-signer.sh @artifact_bucket ' + prefix + ' '
      + ' '.join(f'{n}={hashes[n]}' for n in ('release.json', 'signer.json', 'untrusted-router-policy.json')))
