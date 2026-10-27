"""M4 (Mac, Yao): fresh wallet capture and signed-rehearsal preparation for the new build, then one bound release.json
for BOTH hosts, a local signer check, and upload of the host package (IDEA-104 S5 run sheet, run 8 on S5).

  LARP_PY=<venv python> OLD_SIGNER=<source run 8 signer.json source run8 signer> TOKEN_HISTORY=<qualified TokenHistoryConfig.v1>
  SCOPE_CONFIRMATION=<record of the S5 decision, e.g. "IDEA-104 R2 (Yao, 2026-10-26)">
  python3 -I mac/m4-prepare.py <M3 stamp>

Run 8 is a fresh run on the flat dev wallet (no carry-over), with IDEA-096 allowance recovery on in runtime.json,
execution.json and signer.json, and FS1's pinned token history (IDEA-103, PR295) packaged as token-history.json; M4
refuses any other combination. runtime.json's driver block must also carry the LD03 untrusted-router policy pair
(S2-10), or there is no quote verifier.

The signer refuses unless its release manifest is byte-identical to the one the run registered, so release.json binds
runtime, uploader, operations, execution and signer configs together and both hosts install the same bytes.
stdout carries hashes and flags only: no URLs, keys, hosts or wallet values.
"""
from pathlib import Path
import datetime, hashlib, json, os, shlex, subprocess, sys
os.umask(0o077)
here = Path(__file__).resolve().parents[1]
env = dict(line.split('=', 1) for line in (here / 'pins.sh').read_text().split())
BUILD, BUNDLE = env['BUILD'], env['BUNDLE']
STAMP = sys.argv[1]
main = Path(os.environ['LARP_REPO']).resolve()
wt = main / '.claude/worktrees' / ('release-' + BUILD[:7])
private = here / 'private'
py = os.environ['LARP_PY']
RUN, DB = 'larp-dev-rehearsal-20261027-s5-small-r2', 'larp_rehearsal8r2'
# IDEA-104 R3: the S5 REHEARSAL profile (FS1 at rehearsal size: FS1 model authority, recovery, token history,
# window selling Tue Oct27 23:00SGT).
PROFILE = here / 'inputs/rehearsal-s5-next.json'
PROFILE_SHA = '1dbb52b12b6b8e379a1b3996d427b2ab83b520f98ec6275d29f536600f327e4c'
# IDEA-104 R3: FS1's reviewed AIand/ChatGPT routing (IDEA-093), as FS1 installs it.
ROUTING = wt / 'config/intelligence/aiand-routing.fs1.json'
ROUTING_SHA = '9b86c7327eddca76e0739f6639211f9b609f18c027bc4e61bf83dc804dfcf1f4'
TOKEN_HISTORY = Path(os.environ['TOKEN_HISTORY'])
# S5-SIZE01: fresh cash must fund the selected profile's opening lot within its existing caps.
POLICY = wt / 'docs/build/evidence/untrusted-router-policy-ld03-20261020.json'
POLICY_SHA = '05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5'
# The S5 scope is the team's IDEA-104 decision; M4 refuses to prepare without that record.
SCOPE = os.environ.get('SCOPE_CONFIRMATION', '').strip()
ADOPTION = 'IDEA-104 S5 FS1 dev rehearsal; FS1 v1 scope and routing; recovery; token history; confirmed ' + SCOPE
release = here / 'bundle/x' / BUNDLE
digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require(ok, why):
    """An explicit check: unlike assert, python -O cannot strip it (Keegan PR244 review; Keith PR239)."""
    if not ok:
        raise SystemExit('M4 refused: ' + str(why))

require(subprocess.run(['git', '-C', str(wt), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip() == BUILD, 'release checkout is not BUILD')
require(not subprocess.run(['git', '-C', str(wt), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip(), 'release checkout is not clean')
require(SCOPE != '' and len(ADOPTION) <= 200, 'SCOPE_CONFIRMATION (the record of the IDEA-104 S5 decision) is required')
# IDEA-103: the qualified history input, validated by the release's own parser. A synthetic test value is refused.
sys.path.insert(0, str(wt))
from larp.marketdata.history import CONFIG_FILE, MAX_CONFIG_BYTES, configuration as history_configuration
from larp.strategy.rehearsal_sizing import opening_cash_check
history_raw = TOKEN_HISTORY.read_bytes()
require(hashlib.sha256(history_raw).hexdigest() == '5e572570bc24fb2ca7b692dccf71f67a37c5fac3d75330e4558634cf45417be9', 'history differs from the qualified package pin')
require(len(history_raw) <= MAX_CONFIG_BYTES, 'token history file too large')
history = history_configuration(json.loads(history_raw))
require(len(set(history['timestamp_evidence_sha256'])) > 1
        and not history['token_adjustment_version'].upper().startswith('SYNTHETIC'), 'token history input is synthetic')
require(digest(PROFILE) == PROFILE_SHA and digest(POLICY) == POLICY_SHA, 'profile or router policy hash differs')
require(digest(ROUTING) == ROUTING_SHA, 'FS1 routing file differs from 9b86c732')
require(digest(release / 'release-manifest.json') == env['MANIFEST_SHA256'], 'bundle manifest differs from pins.sh')
assembly = json.loads((private / f'assembly-{STAMP}.json').read_text().strip().splitlines()[-1])
signer = private / f'signer-{STAMP}' / 'signer.json'
reviewed_at = datetime.datetime.fromisoformat(assembly['reviewed_at'].replace('Z', '+00:00'))
require(0 <= (datetime.datetime.now(datetime.timezone.utc) - reviewed_at).total_seconds() <= 300,
        'M3 numeric review is stale; rerun fresh capture and review before M4')
require(assembly['status'] == 'ASSEMBLED_REQUIRES_APPROVAL' and assembly['numeric_status'] == 'COVERED', 'assembly is not ASSEMBLED/COVERED')
require(digest(signer) == assembly['signer_config_sha256'], 'signer.json differs from the assembly report')
# IDEA-104: the candidate may differ from source run 8's installed source run8 signer only in build_id, run_id and database_name,
# with exactly the new values; source run 8 already had allowance recovery on. Anything else (caps, router policy, wallet,
# signing policy) needs a new decision. Isaac still approves the new profile and signer.json hashes.
old = Path(os.environ['OLD_SIGNER'])
old_value, new_value = json.loads(old.read_bytes()), json.loads(signer.read_bytes())
require(old_value.get('build_id') == 'bdd515f80dbc57e80ffeb60c6001091d6e1d7c08' and old_value.get('run_id') == 'larp-dev-rehearsal-20261027-s5-small'
        and old_value.get('database_name') == 'larp_rehearsal8', 'OLD_SIGNER does not bind the original run8')
changed = sorted(k for k in set(old_value) | set(new_value) if old_value.get(k) != new_value.get(k))
require(changed == ['build_id', 'database_name', 'run_id'], 'signer.json differs beyond identity: new decision needed')
require((new_value['build_id'], new_value['run_id'], new_value['database_name']) == (BUILD, RUN, DB), 'signer.json identity differs')
require(new_value['signing_policy'].get('allowance_recovery') is True, 'signer policy lacks allowance_recovery')
print(json.dumps(dict(signer_diff_vs_source_run8=changed, signer_config_sha256=digest(signer))))
reviewed = json.loads((private / f'review-{STAMP}' / 'execution-config.json').read_text())
profile = json.loads(PROFILE.read_bytes())
# IDEA-096: execution opts into recovery with the eight-child envelope the S5 profile reserves.
require(reviewed['allowance_recovery'] is True and reviewed['gas_budget'] == profile['gas_action_budget_units']
        == 8 * reviewed['max_gas'] * reviewed['max_gas_price'], 'reviewed execution config lacks the recovery scope or budget')
results = here / 'results'; results.mkdir(exist_ok=True)
# prepare_shadow writes only inside the release checkout's git-ignored deploy/activation/ (as the trial's r6 did).
out = wt / 'deploy/activation' / ('package-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
capture = Path(os.environ.get('TMPDIR', '/tmp')) / ('larp-rehearsal-capture-' + out.name[8:]); capture.mkdir(mode=0o700)
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
call([py, 'tools/deploy/prepare_shadow.py', 'capture', '--env-file', os.environ['LARP_ENV_FILE'], '--wallet', wallet,
      '--artifact-root', str(capture / 'web3'), '--balance-rpc-config', str(rpc), '--output', str(capture / 'inputs.json')])
call([py, str(here / 'mac/prepare_rehearsal_db.py'), str(wt), 'prepare', '--terraform-output', str(tf),
      '--profile', str(PROFILE), '--capture', str(capture / 'inputs.json'), '--run-id', RUN, '--build-id', BUILD,
      '--rds-ca-sha256', env['CA_SHA256'], '--sec-contact', contact, '--balance-rpc-config', str(rpc),
      '--execution', 'service', '--runtime-mode', 'dev', '--model-adoption-ref', ADOPTION,
      '--untrusted-router-policy-file', '/etc/larp/untrusted-router-policy.json', '--untrusted-router-policy-sha256', POLICY_SHA,
      '--model-routing', str(ROUTING), '--model-routing-sha256', ROUTING_SHA,
      '--allowance-recovery', '--token-history-config', str(TOKEN_HISTORY), '--out', str(out)])
# gate_a_check reads only prepare's own files, so it runs before the extra host files are added (SJ-06 J3).
q = json.loads(call([py, '-m', 'larp.runtime.gate_a_check', '--prepared', str(out), '--ci-manifest', str(release / 'release-manifest.json'),
                     '--release-root', str(release / 'release'), '--rds-ca', str(release / 'rds-ca.pem'),
                     '--artifact-root', str(Path.home() / 'larp-artifacts')], allow_fail=True))
require(all(v == 'PASS' for v in q['checks'].values()) and q['local_ready'] is True, 'package check failed')
rt = json.loads((out / 'runtime.json').read_text())
require((rt['run_id'], rt['build_id'], rt['mode'], rt['database_name']) == (RUN, BUILD, 'dev', DB), 'runtime identity differs')
require((rt['driver']['execution'], rt['driver']['assessor'], rt['driver']['intelligence_mode']) == ('service', 'aiand_routed', 'live'), 'runtime scope is not service/aiand_routed/live')
require((rt['driver'].get('model_routing_file'), rt['driver'].get('model_routing_sha256')) == ('/etc/larp/model-routing.json', ROUTING_SHA)
        and (out / 'model-routing.json').read_bytes() == ROUTING.read_bytes(), 'runtime model routing pin missing or differs')
require(rt['driver']['strategy_profile_sha256'] == PROFILE_SHA, 'runtime profile pin differs')
require(rt['driver'].get('allowance_recovery') is True, 'runtime allowance recovery is not on (IDEA-096)')
# IDEA-103: the runtime pins the packaged history bytes at the fixed host path.
require((rt['driver'].get('token_history_file'), rt['driver'].get('token_history_sha256'))
        == (CONFIG_FILE, hashlib.sha256(history_raw).hexdigest()), 'runtime token history pin missing or differs (IDEA-103)')
require((out / 'token-history.json').read_bytes() == history_raw, 'packaged token-history.json differs from TOKEN_HISTORY')
state = json.loads((out / 'initial-state.json').read_text())
require(not any(p['units'] for p in state['positions'].values()), 'the dev wallet holds stock: S5 is a fresh run')
size_check = opening_cash_check(profile, state['cash_units'])
print(json.dumps(dict(opening_equity_units=state['opening_equity_units'], cash_units=state['cash_units'],
                      token_history_sha256=hashlib.sha256(history_raw).hexdigest(), **size_check)))
# S2-10: without this pair the runtime wires no quote verifier and the run behaves exactly like run 3.
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
                  f'Build {BUILD}: canonical with FS1 (IDEA-093/098), FS1 token history (IDEA-103) and S5 (IDEA-104 R3, FS1 routing); '
                  f'bundle provenance {env["MIRROR_RUN"]}. Dev signed rehearsal {RUN} on S5 profile '
                  f'{PROFILE_SHA[:8]}, database {DB}, fresh book on the dev wallet.'))) + '\n')
call([py, '-m', 'larp.runtime.preflight', '--bind', str(release / 'release-manifest.json'), '--root', str(release / 'release'),
      '--output', str(out / 'release.json'), '--registration-evidence', str(out / 'registration-evidence.json'),
      '--config', str(out / 'operations.json'), '--runtime-config', str(out / 'runtime.json'),
      '--service-config', 'uploader=' + str(out / 'uploader.json'), '--service-config', 'execution=' + str(out / 'execution.json'),
      '--service-config', 'signer=' + str(out / 'signer.json')], cwd=release / 'release')
call([py, '-m', 'larp.signer.service', 'check', '--config', str(out / 'signer.json'), '--manifest', str(out / 'release.json'),
      '--root', str(release / 'release')], cwd=release / 'release')
names = ['release.json', 'runtime.json', 'uploader.json', 'operations.json', 'execution.json', 'signer.json',
         'strategy-profile.json', 'session-calendar.json', 'initial-state.json', 'evidence.env',
         'registration-evidence.json', 'untrusted-router-policy.json', 'token-history.json', 'model-routing.json']
hashes = {n: digest(out / n) for n in names}
prefix = 'releases/run8r2-' + out.name[8:].lower() + '/'
t = json.loads(tf.read_text()); bucket = t['artifact_bucket']['value'] if isinstance(t['artifact_bucket'], dict) else t['artifact_bucket']
for n in names:
    subprocess.run(['aws', '--profile', 'larp', '--region', 'ap-southeast-2', 's3', 'cp', '--only-show-errors',
                    str(out / n), f's3://{bucket}/{prefix}{n}'], check=True)
primary = [n for n in names if n != 'signer.json']
record = dict(record_id='S5-J3', build_id=BUILD, run_id=RUN, database=DB, package=out.name, prefix=prefix, hashes=hashes,
              signer_config_sha256=assembly['signer_config_sha256'], execution_rpc_source_id=first['source_id'],
              numeric_reviewed_at=assembly['reviewed_at'], profile_sha256=PROFILE_SHA, source_run='larp-dev-rehearsal-20261027-s5-small')
(out / 'package-record.json').write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
print(json.dumps(record, sort_keys=True))
print('P3: python3.12 -I ssm_run.py host/p3-install-primary.sh @artifact_bucket ' + prefix + ' '
      + ' '.join(f'{n}={hashes[n]}' for n in primary))
print('S1: python3.12 -I ssm_run.py --signer host/s1-install-signer.sh @artifact_bucket ' + prefix + ' '
      + ' '.join(f'{n}={hashes[n]}' for n in ('release.json', 'signer.json', 'untrusted-router-policy.json')))
