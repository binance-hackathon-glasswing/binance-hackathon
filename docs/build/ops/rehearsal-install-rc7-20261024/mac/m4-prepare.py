"""M4 (Mac, Yao): fresh wallet capture and signed-rehearsal preparation for the new build, then one bound release.json
for BOTH hosts, a local signer check, and upload of the host package (IDEA-089 S2, RC7 run sheet, run 4 on S2).

  LARP_PY=<venv python> OLD_SIGNER=<run 3 signer.json 49cb1a08...> SCOPE_CONFIRMATION=<record of Yao's S2 decision,
  e.g. "IDEA-089 Decision (Yao, 2026-10-23)"> /opt/homebrew/bin/python3.12 -I mac/m4-prepare.py <M3 stamp>

S2-10: runtime.json's driver block must carry the LD03 untrusted-router policy pair, or the runtime has no quote
verifier and behaves exactly like run 3 (no executable quote). M4 passes the pair to prepare and refuses without it.

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
RUN, DB = 'larp-dev-rehearsal-20261024-s2', 'larp_rehearsal4'
# IDEA-089: the run-4 S2 REHEARSAL profile (run 3's S1 block with KIT_OPEN_STATE hours, 5 attempts, the weekend window).
PROFILE = wt / 'docs/build/evidence/s2-rehearsal-profile-20261024/rehearsal-s2-deterministic.json'
PROFILE_SHA = 'eb55d76a36b9fb931f551752da9266c379072611d789ab85d9cb1fc2291d8e68'
POLICY = wt / 'docs/build/evidence/untrusted-router-policy-ld03-20261020.json'
POLICY_SHA = '05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5'
# S2-1: the S2 scope is Yao's IDEA-089 decision; M4 refuses to prepare without that record.
SCOPE = os.environ.get('SCOPE_CONFIRMATION', '').strip()
ADOPTION = 'IDEA-089 S2 scoped deterministic weekend rehearsal on the dev wallet; S2-1 scope; confirmed ' + SCOPE
release = here / 'bundle/x' / BUNDLE
digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require(ok, why):
    """An explicit check: unlike assert, python -O cannot strip it (Keegan PR244 review; Keith PR239)."""
    if not ok:
        raise SystemExit('M4 refused: ' + str(why))

require(subprocess.run(['git', '-C', str(wt), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip() == BUILD, 'release checkout is not BUILD')
require(not subprocess.run(['git', '-C', str(wt), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip(), 'release checkout is not clean')
require(SCOPE != '' and len(ADOPTION) <= 200, 'SCOPE_CONFIRMATION (the record of Yao\'s IDEA-089 S2 decision) is required')
require(digest(PROFILE) == PROFILE_SHA and digest(POLICY) == POLICY_SHA, 'profile or router policy hash differs')
require(digest(release / 'release-manifest.json') == env['MANIFEST_SHA256'], 'bundle manifest differs from build.env')
assembly = json.loads((private / f'assembly-{STAMP}.json').read_text().strip().splitlines()[-1])
signer = private / f'signer-{STAMP}' / 'signer.json'
require(assembly['status'] == 'ASSEMBLED_REQUIRES_APPROVAL' and assembly['numeric_status'] == 'COVERED', 'assembly is not ASSEMBLED/COVERED')
require(digest(signer) == assembly['signer_config_sha256'], 'signer.json differs from the assembly report')
# S2-7: as in SJ-11, the candidate may differ from run 3's installed 49cb1a08... in build_id, run_id and
# database_name alone, with exactly the new values. signer.json carries no profile field, so the S2 profile changes
# nothing else; anything else (policy, caps, router policy, wallet) needs a new decision. Isaac still approves the
# new profile and signer.json hashes.
old = Path(os.environ['OLD_SIGNER'])
require(digest(old) == '49cb1a08c3d2a3b3c7409ad1c3beb68e0a43e3282bd9296ad7bcec770530209a', 'OLD_SIGNER is not run 3 49cb1a08')
old_value, new_value = json.loads(old.read_bytes()), json.loads(signer.read_bytes())
changed = sorted(k for k in set(old_value) | set(new_value) if old_value.get(k) != new_value.get(k))
require(changed == ['build_id', 'database_name', 'run_id'], 'signer.json differs beyond build_id/run_id/database_name: new decision needed')
require((new_value['build_id'], new_value['run_id'], new_value['database_name']) == (BUILD, RUN, DB), 'signer.json identity differs')
print(json.dumps(dict(signer_diff_vs_49cb1a08=changed, signer_config_sha256=digest(signer))))
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
      '--execution', 'service', '--runtime-mode', 'dev', '--model-adoption-ref', ADOPTION,
      '--untrusted-router-policy-file', '/etc/larp/untrusted-router-policy.json', '--untrusted-router-policy-sha256', POLICY_SHA,
      '--out', str(out)])
# gate_a_check reads only prepare's own files, so it runs before the extra host files are added (SJ-06 J3).
q = json.loads(call([py, '-m', 'larp.runtime.gate_a_check', '--prepared', str(out), '--ci-manifest', str(release / 'release-manifest.json'),
                     '--release-root', str(release / 'release'), '--rds-ca', str(release / 'rds-ca.pem'),
                     '--artifact-root', '/Users/songyaozhu/larp-artifacts'], allow_fail=True))
require(all(v == 'PASS' for v in q['checks'].values()) and q['local_ready'] is True, 'package check failed')
rt = json.loads((out / 'runtime.json').read_text())
require((rt['run_id'], rt['build_id'], rt['mode'], rt['database_name']) == (RUN, BUILD, 'dev', DB), 'runtime identity differs')
require((rt['driver']['execution'], rt['driver']['assessor'], rt['driver']['intelligence_mode']) == ('service', 'deterministic', 'live'), 'runtime scope is not service/deterministic/live')
require(rt['driver']['strategy_profile_sha256'] == PROFILE_SHA, 'runtime profile pin differs')
# S2-10: without this pair the runtime wires no quote verifier and run 4 behaves exactly like run 3.
require((rt['driver'].get('untrusted_router_policy_file'), rt['driver'].get('untrusted_router_policy_sha256'))
        == ('/etc/larp/untrusted-router-policy.json', POLICY_SHA), 'runtime router policy pair missing or differs (S2-10)')
require(rt['driver'].get('balance_rpc_providers') and all(p.get('url') and p.get('source_id') for p in rt['driver']['balance_rpc_providers']),
        'the runtime quote verifier needs the balance RPC providers')
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
    require(execution[key] == rt[key], key)
require((execution['untrusted_router_policy_file'], execution['untrusted_router_policy_sha256']) == ('/etc/larp/untrusted-router-policy.json', POLICY_SHA), 'execution router policy pair differs')
require(execution['strategy_profile_sha256'] == PROFILE_SHA and execution['database_user'] == 'larp_execution', 'execution profile pin or database user differs')
(out / 'execution.json').write_bytes(json.dumps(execution, indent=1, sort_keys=True).encode() + b'\n')
(out / 'signer.json').write_bytes(signer.read_bytes())
(out / 'untrusted-router-policy.json').write_bytes(POLICY.read_bytes())
(out / 'registration-evidence.json').write_text(json.dumps(dict(
    schema='RegistrationEvidence.v1', build_id=BUILD, repository='https://github.com/binance-hackathon-glasswing/binance-hackathon',
    evidence_ref=('Existing team registration (GAP-41/F-113, issued ai-seeds secret) unchanged; no new organiser registration. '
                  f'Build {BUILD} = RC7, canonical with the SJ-11-QV01 quote verifier (PR268) and the IDEA-089 S2 '
                  f'weekend test; bundle provenance {env["MIRROR_RUN"]}. Dev signed rehearsal {RUN} on S2 profile '
                  f'{PROFILE_SHA[:8]}, database {DB} (IDEA-089).'))) + '\n')
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
record = dict(record_id='S2-J3', build_id=BUILD, run_id=RUN, database=DB, package=out.name, prefix=prefix, hashes=hashes,
              signer_config_sha256=assembly['signer_config_sha256'], execution_rpc_source_id=first['source_id'])
(out / 'package-record.json').write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
print(json.dumps(record, sort_keys=True))
print('P3: python3.12 -I ssm_run.py host/p3-install-primary.sh @artifact_bucket ' + prefix + ' '
      + ' '.join(f'{n}={hashes[n]}' for n in primary))
print('S1: python3.12 -I ssm_run.py --signer host/s1-install-signer.sh @artifact_bucket ' + prefix + ' '
      + ' '.join(f'{n}={hashes[n]}' for n in ('release.json', 'signer.json', 'untrusted-router-policy.json')))
