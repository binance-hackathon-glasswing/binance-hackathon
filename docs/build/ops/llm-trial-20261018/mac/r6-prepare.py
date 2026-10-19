"""R6 (Mac, owner): fresh wallet capture and preparation from the exact merged ea25b52 checkout (PR178), pointed at
the separate larp_trial2 database, with the capped trial routing. Then the package check and upload of the host files
to a fresh releases/ prefix. Run directly:  /opt/homebrew/bin/python3.12 -I mac/r6-prepare.py
Based on the reviewed pr174-verification-20261018/prepare-local.py; stdout carries no URLs, keys or wallet.
"""
from pathlib import Path
import datetime, hashlib, json, os, shlex, subprocess, sys
main = Path('/Users/songyaozhu/binance-hackathon')
checkout = Path('/Users/songyaozhu/binance-hackathon/.claude/worktrees/release-ea25b52')
here = Path(__file__).resolve().parents[1]; results = here / 'results'; results.mkdir(exist_ok=True)
BUILD = 'ea25b52325656a19b29e8ddb07b94dd792be6e18'
DB = 'larp_trial2'
ROUTING_SHA = 'a5fca50a6f3e166b48299a0d29e686aa6dbfd2428f4bb011839acc684b222d8d'
CA_SHA = 'd73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b'
head = subprocess.run(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(['git', '-C', str(checkout), 'status', '--porcelain', '--untracked-files=no'],
                       capture_output=True, text=True).stdout.strip()
assert head == BUILD and not dirty, 'release checkout is not clean ea25b52'
assert hashlib.sha256((checkout / 'config/intelligence/aiand-routing.openai-trial.example.json').read_bytes()).hexdigest() == ROUTING_SHA
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
run_id = 'larp-dev-llm-trial-' + stamp.lower()
capture = Path('/private/tmp') / ('larp-ea25b52-capture-' + stamp); capture.mkdir(mode=0o700)
out = checkout / 'deploy/activation' / ('llm-trial-' + stamp)
python = '/opt/homebrew/bin/python3.12'; env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', LARP_TRIAL_DB=DB)
# The real Terraform output; prepare_trial_db.py points the rendered configs at LARP_TRIAL_DB (PC-DB02).
tf_path = main / 'deploy/activation/tf-output.json'
tf = json.loads(tf_path.read_text())
wrapper = Path(__file__).resolve().with_name('prepare_trial_db.py')
step = [0]


def call(args):
    step[0] += 1
    p = subprocess.run([python, *args], cwd=checkout, env=env, text=True, capture_output=True)
    (results / f'prepare-step-{step[0]}.stdout').write_text(p.stdout)
    (results / f'prepare-step-{step[0]}.stderr').write_text(p.stderr)  # private, never echoed
    print(p.stdout.strip() or json.dumps({'step': step[0], 'exit': p.returncode}), flush=True)
    if p.returncode and not (args[:2] == ['-m', 'larp.runtime.gate_a_check']):
        raise SystemExit(p.returncode)
    return p.stdout


wallet = json.loads((main / 'deploy/activation/gate-a-prepared-20261017/runtime.json').read_text())['wallet_address']
rpc = main / 'deploy/activation/balance-rpc/selected-providers.json'
call(['tools/deploy/prepare_shadow.py', 'capture', '--env-file', str(main / '.env'), '--wallet', wallet,
      '--artifact-root', str(capture / 'web3'), '--balance-rpc-config', str(rpc), '--output', str(capture / 'gate-a-inputs.json')])
contact = next(shlex.split(line)[0].split('=', 1)[1] for line in
               (main / 'deploy/activation/gate-a-prepared-20261017/evidence.env').read_text().splitlines()
               if line.startswith('LARP_SEC_USER_AGENT='))
call(['-I', str(wrapper), str(checkout), 'prepare', '--terraform-output', str(tf_path),
      '--profile', str(main / 'deploy/activation/interim-20261017/profiles/rehearsal-live.json'),
      '--capture', str(capture / 'gate-a-inputs.json'), '--run-id', run_id, '--build-id', BUILD,
      '--rds-ca-sha256', CA_SHA, '--sec-contact', contact, '--balance-rpc-config', str(rpc),
      '--model-routing', 'config/intelligence/aiand-routing.openai-trial.example.json',
      '--model-routing-sha256', ROUTING_SHA, '--execution', 'shadow', '--runtime-mode', 'dev', '--out', str(out)])
bundle = main / 'deploy/activation/redeploy-20261018/verified-bundle'
q = json.loads(call(['-m', 'larp.runtime.gate_a_check', '--prepared', str(out), '--ci-manifest', str(bundle / 'release-manifest.json'),
                     '--release-root', str(bundle / 'release'), '--rds-ca', str(bundle / 'rds-ca.pem'),
                     '--artifact-root', '/Users/songyaozhu/larp-artifacts']))
checks = q['checks']
# Local build (PC-BUILD01): CI_RELEASE_BYTES may pass or fail by origin; production bind re-checks the bytes.
bad = {k: v for k, v in checks.items() if v != 'PASS' and k != 'CI_RELEASE_BYTES'}
if bad:
    raise SystemExit('package check failed: ' + json.dumps(bad))
rt = json.loads((out / 'runtime.json').read_text())
assert rt['database_name'] == DB and rt['run_id'] == run_id and rt['build_id'] == BUILD
assert rt['driver']['assessor'] == 'aiand_routed' and rt['driver']['execution'] == 'shadow' and rt['mode'] == 'dev'
assert rt['driver']['model_routing_sha256'] == ROUTING_SHA
for name in ('operations.json', 'uploader.json'):
    c = json.loads((out / name).read_text()); assert c['database_name'] == DB and c.get('run_id', run_id) == run_id, name
host_files = ['runtime.json', 'uploader.json', 'operations.json', 'strategy-profile.json', 'session-calendar.json',
              'initial-state.json', 'evidence.env', 'model-routing.json']
hashes = {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in host_files}
assert hashes['model-routing.json'] == ROUTING_SHA
prefix = 'releases/llm-trial-' + stamp.lower() + '/'
bucket = tf['artifact_bucket']['value'] if isinstance(tf['artifact_bucket'], dict) else tf['artifact_bucket']
for n in host_files:
    subprocess.run(['/opt/homebrew/bin/aws', '--profile', 'larp', '--region', 'ap-southeast-2', 's3', 'cp', '--only-show-errors',
                    str(out / n), f's3://{bucket}/{prefix}{n}'], check=True)
record = dict(record_id='PC-PREP04', prepared_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              run_id=run_id, build_id=BUILD, database=DB, prepared=str(out), s3_prefix=prefix,
              capture_sha256=hashlib.sha256((capture / 'gate-a-inputs.json').read_bytes()).hexdigest(),
              database_override='prepare_trial_db.py: rendered database_name larp -> ' + DB + ' only (PC-DB02)',
              checks=checks, accepted_mirror_only_failure=checks.get('CI_RELEASE_BYTES') != 'PASS', hashes=hashes)
(results / 'prepared.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(dict(record, prepared='<local>'), indent=2))
print('Next: /opt/homebrew/bin/python3.12 -I ssm_run.py host/r7-install-keep-ledger.sh @artifact_bucket', prefix,
      ' '.join(f'{n}={h}' for n, h in hashes.items()))
