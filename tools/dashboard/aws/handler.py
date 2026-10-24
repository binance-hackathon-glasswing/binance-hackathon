"""AWS Lambda: hourly refresh of the private dashboard (IDEA-091).

Each run: load the chain monitor's state from the private bucket, one `tools.dashboard.refresh` run (monitor poll,
decisions export, redacted build), then upload the page under `site/` and the new state under `state/`. A run that
fails uploads nothing, so the last good page stays. The Lambda may run only the two read-only SSM documents named in
its configuration, only on the configured primary; it has no permission to send other commands.

Configuration (environment): BUCKET, PRIMARY_INSTANCE_ID, DECISIONS_DOCUMENT, TX_DOCUMENT, WALLET, START_NONCE,
START_USDT, and optionally WEB3_SECRET_ARN (a JSON secret with the read-only BINANCE_API_KEY and BINANCE_SECRET_KEY,
for prices).
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

from tools.dashboard import refresh

STATE_FILES = ('state.json', 'snapshots.jsonl', 'transactions.jsonl', 'alerts.jsonl', 'decisions.jsonl')
SITE = (('index.html', 'text/html; charset=utf-8'), ('data.json', 'application/json'))
POLL_S, TIMEOUT_S = 2, 240


def document_runner(ssm, instance, documents):
    """A `refresh` SSM runner that can send only the named documents (script file name -> SSM document name)."""
    def run(script_path, *args):
        name = Path(script_path).name
        if name not in documents:
            raise PermissionError('No SSM document is configured for ' + name)
        parameters = {'limit': [str(int(args[0]))]} if args else {}
        sent = ssm.send_command(InstanceIds=[instance], DocumentName=documents[name], Parameters=parameters,
                                TimeoutSeconds=600)
        command_id, deadline = sent['Command']['CommandId'], time.time() + TIMEOUT_S
        while time.time() < deadline:
            time.sleep(POLL_S)
            try:
                result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance)
            except ssm.exceptions.InvocationDoesNotExist:
                continue
            if result['Status'] in ('Pending', 'InProgress', 'Delayed'):
                continue
            if result['Status'] != 'Success':
                raise RuntimeError(documents[name] + ' ' + result['Status'])
            return command_id, result.get('StandardOutputContent', '')
        raise TimeoutError(documents[name] + ' did not finish')
    return run


def download_state(s3, bucket, work):
    monitor = work / 'monitor'
    monitor.mkdir(parents=True)
    for name in STATE_FILES + ('refresh-state.json',):
        target = work / name if name == 'refresh-state.json' else monitor / name
        try:
            s3.download_file(bucket, 'state/' + name, str(target))
        except Exception as error:  # absent on the first run
            if getattr(error, 'response', {}).get('Error', {}).get('Code') not in ('404', 'NoSuchKey', 'NotFound'):
                raise


def upload(s3, bucket, work):
    site = work / 'site'
    for name, content_type in SITE:
        s3.upload_file(str(site / name), bucket, 'site/' + name,
                       ExtraArgs={'ContentType': content_type, 'CacheControl': 'no-cache'})
    for name in STATE_FILES:
        if (work / 'monitor' / name).is_file():
            s3.upload_file(str(work / 'monitor' / name), bucket, 'state/' + name)
    s3.upload_file(str(work / 'refresh-state.json'), bucket, 'state/refresh-state.json')


def web3_env_file(secrets, arn, work):
    """The read-only Web3 key as the monitor's env file, only inside this run's temporary folder."""
    if not arn:
        return str(work / 'no-web3-key.env')  # the monitor then reports prices as unavailable
    key = json.loads(secrets.get_secret_value(SecretId=arn)['SecretString'])
    path = work / 'web3.env'
    path.write_text(''.join(f'{k}={key[k]}\n' for k in ('BINANCE_API_KEY', 'BINANCE_SECRET_KEY')))
    path.chmod(0o600)
    return str(path)


def run(env, clients):
    """One refresh; `clients` maps 's3', 'ssm' and 'secretsmanager' to boto3 clients (fakes in tests)."""
    bucket = env['BUCKET']
    work = Path(tempfile.mkdtemp(prefix='larp-dashboard-'))
    try:
        download_state(clients['s3'], bucket, work)
        os.environ['LARP_ENV_FILE'] = web3_env_file(clients['secretsmanager'], env.get('WEB3_SECRET_ARN'), work)
        runner = document_runner(clients['ssm'], env['PRIMARY_INSTANCE_ID'],
                                 {refresh.EXPORT.name: env['DECISIONS_DOCUMENT'], refresh.TX_EXPORT.name: env['TX_DOCUMENT']})
        settings = dict(wallet=env['WALLET'], start_nonce=int(env['START_NONCE']), start_usdt=float(env['START_USDT']))
        summary = refresh.refresh(work, runner=runner, settings=settings)
        upload(clients['s3'], bucket, work)
        return {k: summary[k] for k in ('as_of_utc', 'chain', 'export', 'rounds', 'export_command', 'export_error')}
    finally:
        shutil.rmtree(work, ignore_errors=True)  # the key file goes with it


def lambda_handler(event, context):
    import boto3
    clients = {name: boto3.client(name) for name in ('s3', 'ssm', 'secretsmanager')}
    summary = run(os.environ, clients)
    print(json.dumps(summary, sort_keys=True))
    return summary
