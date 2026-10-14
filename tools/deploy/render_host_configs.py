"""Fill the host configs' infrastructure values from `terraform output -json` (IDEA-051; AWS_RUNBOOK.md step 7).

    terraform -chdir=deploy/aws output -json > /tmp/tf-outputs.json
    python tools/deploy/render_host_configs.py --terraform-output /tmp/tf-outputs.json \
        --wallet 0x<public dev wallet address> --out deploy/activation/development [--rds-ca-sha256 <hex>]

Writes runtime.json, execution.json, signer.json, uploader.json and operations.json (mode 0600) into a git-ignored
directory, each a copy of its example under config/ with only the values the infrastructure determines filled in:
wallet address, database host and name, secret IDs, region, account, buckets and KMS key. Every value still unset is
listed per file: run and build IDs, profile and calendar hashes, policy values. Those are decided elsewhere, never
guessed here. It reads no secret and writes no secret value: a secret ID is a name, not a value.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = {
    'runtime.json': 'config/runtime/runtime.example.json',
    'execution.json': 'config/hosts/execution.example.json',
    'signer.json': 'config/hosts/signer.example.json',
    'uploader.json': 'config/hosts/uploader.example.json',
    'operations.json': 'config/runtime/operations.example.json',
}
WALLET = re.compile(r'0x[0-9a-fA-F]{40}')
SHA256 = re.compile(r'[0-9a-f]{64}')
SECRET_ARN = re.compile(r'arn:aws:secretsmanager:([a-z0-9-]+):(\d{12}):secret:(.+)/(runtime|uploader|evidence)-[A-Za-z0-9]{6}')
CA_FILE = '/etc/larp/rds-ca.pem'


class Refused(Exception):
    pass


def outputs(raw):
    """`terraform output -json` -> {name: value}, with the fields this tool needs checked."""
    values = {k: v.get('value') for k, v in raw.items()} if type(raw) is dict else {}
    needed = ('archive_bucket', 'archive_kms_key', 'database_host', 'database_name', 'service_secret_arns')
    missing = [k for k in needed if not values.get(k)]
    if missing:
        raise Refused('terraform output lacks: ' + ', '.join(missing))
    secrets = {}
    for service, arn in values['service_secret_arns'].items():
        match = SECRET_ARN.fullmatch(arn) if type(arn) is str else None
        if not match or match.group(4) != service:
            raise Refused('unexpected secret ARN for ' + str(service))
        secrets[service] = match
    if not {'runtime', 'uploader'} <= set(secrets):
        raise Refused('runtime and uploader secrets are required')
    if len({(m.group(1), m.group(2), m.group(3)) for m in secrets.values()}) != 1:
        raise Refused('secrets disagree on region, account or name')
    region, account, name = secrets['runtime'].group(1, 2, 3)
    return dict(values, region=region, account_id=account, name=name,
                secret_ids={s: f'{name}/{s}' for s in secrets})


def render(tf, wallet, rds_ca_sha256=None):
    """{file name: config dict}; only infrastructure-determined values are set."""
    if not WALLET.fullmatch(wallet or ''):
        raise Refused('wallet must be 0x followed by 40 hex characters')
    if rds_ca_sha256 is not None and not SHA256.fullmatch(rds_ca_sha256):
        raise Refused('--rds-ca-sha256 must be 64 lowercase hex characters')
    wallet = wallet.lower()  # the uploader and execution configs accept lowercase hex only
    result = {}
    for out, example in EXAMPLES.items():
        config = json.loads((ROOT / example).read_text())
        for key in ('wallet_address',):
            if key in config:
                config[key] = wallet
        if 'database_host' in config:
            config['database_host'] = tf['database_host']
        if config.get('database_name') not in (None, tf['database_name']):
            raise Refused(f'{example} names database {config["database_name"]!r}, Terraform {tf["database_name"]!r}')
        if 'database_name' in config:
            config['database_name'] = tf['database_name']
        if 'region' in config:
            config['region'] = tf['region']
        if 'database_ca_file' in config:
            config['database_ca_file'] = CA_FILE
        if rds_ca_sha256 and 'database_ca_sha256' in config:
            config['database_ca_sha256'] = rds_ca_sha256
        if 'runtime_secret_id' in config:
            config['runtime_secret_id'] = tf['secret_ids']['runtime']
        if 'uploader_secret_id' in config:
            config['uploader_secret_id'] = tf['secret_ids']['uploader']
        if out == 'operations.json':
            config.update(deployment=tf['name'], account_id=tf['account_id'], archive_bucket=tf['archive_bucket'],
                          kms_key=tf['archive_kms_key'])
        result[out] = config
    return result


def unset(value, path=''):
    """Dotted paths of every null or empty value."""
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in unset(v, f'{path}.{k}' if path else k)]
    return [path] if value is None or value == '' else []


def ignored_by_git(directory):
    probe = directory / '.probe'
    run = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(probe)], capture_output=True)
    return run.returncode == 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--terraform-output', required=True, type=Path)
    parser.add_argument('--wallet', required=True, help='public wallet address (0x…)')
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--rds-ca-sha256', help="SHA-256 of the bundle's rds-ca.pem (bundle metadata)")
    parser.add_argument('--force', action='store_true', help='overwrite existing files')
    args = parser.parse_args(argv)
    try:
        out = args.out.resolve()
        if not ignored_by_git(out):
            raise Refused(f'{args.out} is not git-ignored; use deploy/activation/<environment>')
        configs = render(outputs(json.loads(args.terraform_output.read_text())), args.wallet, args.rds_ca_sha256)
        existing = [n for n in configs if (out / n).exists()]
        if existing and not args.force:
            raise Refused('would overwrite ' + ', '.join(existing) + ' (pass --force)')
        out.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name, config in configs.items():
            path = out / name
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as handle:
                handle.write(json.dumps(config, indent=2) + '\n')
            os.chmod(path, 0o600)
    except (Refused, OSError, ValueError) as exc:
        print('refused:', exc, file=sys.stderr)
        return 2
    print(f'wrote {len(configs)} configs to {args.out}. Still unset (decided elsewhere):')
    for name, config in configs.items():
        print(f'  {name}: ' + (', '.join(unset(config)) or 'nothing'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
