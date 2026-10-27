"""Send one local bash script to primary or signer over SSM (base64), wait, keep the result in results/.

  python3 -I ssm_run.py [--signer] host/<script>.sh [args...]

Args are appended as positional parameters (public values only: hashes, prefixes, run IDs). `@artifact_bucket` is
resolved locally from the git-ignored Terraform output and never printed. Output files:
results/<script-name>-{parameters.json,command-id.txt,ssm-result.json,stdout.txt,stderr.txt}. Host output can name
the database endpoint, so this folder must stay in git-ignored deploy/activation/.
"""
import base64, json, os, pathlib, shlex, subprocess, sys, time
os.umask(0o077)
here = pathlib.Path(__file__).parent
args = sys.argv[1:]
signer = args[:1] == ['--signer']
if signer:
    args = args[1:]
script = pathlib.Path(args[0]); name = ('signer-' if signer else 'primary-') + script.stem; extra = args[1:]
if '@artifact_bucket' in extra:
    tf = json.loads((pathlib.Path(os.environ['LARP_REPO']) / 'deploy/activation/tf-output.json').read_text())
    v = tf['artifact_bucket']; bucket = v['value'] if isinstance(v, dict) else v
    extra = [bucket if a == '@artifact_bucket' else a for a in extra]
out = here / 'results'; out.mkdir(exist_ok=True)
aws = [os.environ.get('AWS_CLI', 'aws'), '--profile', os.environ.get('LARP_AWS_PROFILE', 'larp'), '--region', 'ap-southeast-2']
instance = 'i-0f8fe5d5fe5ccba36' if signer else 'i-040fc5fea8b700e9a'
encoded = base64.b64encode(script.read_bytes()).decode()
command = ('set -eu; script_path=$(mktemp /root/larp-ssm-step.XXXXXX); '
           + 'trap \'rm -f "$script_path"\' EXIT; printf %s ' + shlex.quote(encoded)
           + ' | base64 --decode > "$script_path"; bash "$script_path" '
           + ' '.join(shlex.quote(a) for a in extra))
params = {'commands': [command], 'executionTimeout': ['1800']}
p = out / (name + '-parameters.json'); p.write_text(json.dumps(params))


def call(argv, wait_not_found=False):
    r = subprocess.run(aws + argv, capture_output=True, text=True)
    if r.returncode:
        if wait_not_found and 'InvocationDoesNotExist' in r.stderr:
            return None
        (out / (name + '-aws-error.txt')).write_text(r.stderr)
        raise SystemExit('AWS call failed; see results/' + name + '-aws-error.txt')
    return json.loads(r.stdout)


x = call(['ssm', 'send-command', '--instance-ids', instance, '--document-name', 'AWS-RunShellScript',
          '--timeout-seconds', '600', '--parameters', 'file://' + str(p), '--output', 'json'])
c = x['Command']['CommandId']; (out / (name + '-command-id.txt')).write_text(c)
print('sent', name, 'to', 'signer' if signer else 'primary', c, flush=True)
y = dict(Status='TimedOut', StandardOutputContent='', StandardErrorContent='')
for _ in range(900):
    time.sleep(2)
    response = call(['ssm', 'get-command-invocation', '--command-id', c, '--instance-id', instance, '--output', 'json'],
                    wait_not_found=True)
    if response is None:
        continue
    y = response
    if y['Status'] not in ('Pending', 'InProgress', 'Delayed'):
        break
(out / (name + '-ssm-result.json')).write_text(json.dumps(y))
(out / (name + '-stdout.txt')).write_text(y.get('StandardOutputContent', ''))
(out / (name + '-stderr.txt')).write_text(y.get('StandardErrorContent', ''))
print(y.get('StandardOutputContent', ''))
print(json.dumps({'command_id': c, 'status': y['Status'], 'stderr_bytes': len(y.get('StandardErrorContent', ''))}))
sys.exit(0 if y['Status'] == 'Success' else 1)
