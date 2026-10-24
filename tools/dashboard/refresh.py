"""Rebuild the private dashboard page from the chain and the primary's decisions (IDEA-087 DR).

  python -m tools.dashboard.refresh --work <dir> [--seed-blocks 129462184,129462303,...]

One refresh: a chain-monitor poll (docs/build/ops/rehearsal-install-rc7-20261024/mac/chain-monitor.py) into
<dir>/monitor, the read-only decisions export over SSM (tools/dashboard/decisions-export.sh) merged into it, the
redacted build, and that page adapted for a claude.ai Artifact in <dir>/artifact/ (larp-dashboard.html, data.json).
Publishing the page is a separate step. The SSM calls use the environment's AWS credentials.

The monitor scans the blocks since its last poll. Without its state (a new machine), the first poll books the
wallet's known transaction blocks instead of a full scan: --seed-blocks, else <dir>/refresh-state.json, else the
blocks of the transactions in the run's execution records (tools/dashboard/tx-export.sh, read-only). The monitor still
checks that the nonces are contiguous. The block list stays in <dir>: published with the page it would identify the
wallet. Nothing is signed or sent; the redacted page has no wallet address, hashes, blocks, nonces or round IDs.
"""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import time

from tools.dashboard import build, decisions

ROOT = Path(__file__).resolve().parents[2]
MONITOR = ROOT / 'docs/build/ops/rehearsal-install-rc7-20261024/mac/chain-monitor.py'
EXPORT = ROOT / 'tools/dashboard/decisions-export.sh'
TX_EXPORT = ROOT / 'tools/dashboard/tx-export.sh'
PRIMARY = 'i-040fc5fea8b700e9a'  # run 4's primary (ssm_run.py)
REGION = 'ap-southeast-2'
GUTTER = ('.wrap { padding-left: max(16px, env(safe-area-inset-left, 0px)); '
          'padding-right: max(16px, env(safe-area-inset-right, 0px)); }\n')
SKELETON = ('<!doctype html>\n', '<html lang="en">\n', '<head>\n', '<meta charset="utf-8">\n',
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n', '</head>\n', '<body>\n',
            '</body>\n', '</html>\n')
TITLE = '<title>LARP wallet dashboard</title>\n'


def artifact_page(html):
    """The built page without its document skeleton (the Artifact publisher adds one), with the safe-area gutter."""
    for tag in SKELETON + (TITLE, '</style>'):
        if html.count(tag) != 1:
            raise ValueError('Unexpected dashboard page shape: ' + tag.strip())
    for tag in SKELETON:
        html = html.replace(tag, '')
    html = html.replace(TITLE, TITLE + '<meta name="claude:viewport-fit-sides" content="cover">\n')
    return html.replace('</style>', GUTTER + '</style>')


def known_blocks(monitor_dir):
    rows, _ = build.read_jsonl(Path(monitor_dir) / 'transactions.jsonl')
    return sorted({t['block'] for t in rows if type(t.get('block')) is int})


def chain_monitor(monitor_dir):
    os.environ['LARP_MONITOR_DIR'] = str(monitor_dir)
    os.environ.setdefault('LARP_ENV_FILE', str(ROOT / '.env'))  # read-only Web3 key for prices, if present
    spec = importlib.util.spec_from_file_location('chain_monitor', MONITOR)
    monitor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(monitor)
    return monitor


def seeds_from_primary(monitor):
    """Blocks of the transactions in the run's execution records (read-only export over SSM)."""
    _, stdout = ssm_run(TX_EXPORT)
    hashes = [row['tx_hash'] for row in map(json.loads, filter(None, stdout.splitlines())) if row.get('section') == 'tx']
    receipts = monitor.rpc(None, None, batch=[('eth_getTransactionReceipt', [h]) for h in hashes]) if hashes else []
    return sorted({int(r['blockNumber'], 16) for r in receipts if r})


def poll(monitor_dir, seed_blocks):
    monitor = chain_monitor(monitor_dir)
    state = monitor.load_state()
    if state['block'] is None and not seed_blocks:
        seed_blocks = seeds_from_primary(monitor)
    if state['block'] is None and seed_blocks:
        scan = monitor.wallet_txs

        def seeded(start, end):
            blocks = monitor.rpc(None, None, batch=[('eth_getBlockByNumber', [hex(n), True]) for n in seed_blocks])
            found = [t for b in blocks for t in (b or {}).get('transactions', []) if t['from'].lower() == monitor.WALLET]
            try:
                nonce = int(monitor.rpc('eth_getTransactionCount', [monitor.WALLET, hex(end)]), 16)
            except (RuntimeError, OSError, ValueError, TypeError):
                nonce = None  # unknown: scan
            if nonce is not None and {int(t['nonce'], 16) for t in found} >= set(range(state['nonce'], nonce)):
                return found  # the seeds hold every transaction up to `end`
            return found + scan(max(seed_blocks) + 1, end)  # else also scan after the last seed
        monitor.wallet_txs = seeded
    snap, alerts = monitor.poll(state)
    return dict(utc=snap['utc'], nonce=snap['nonce'], trades=snap['trades'], failed_txs=snap['failed_txs'],
                alerts=sorted({a['kind'] for a in alerts}), price_error=snap['price_error'])


def ssm_run(script_path, *args, timeout_s=300):
    """Send one read-only check script to the primary the way ssm_run.py does; return (command ID, stdout)."""
    import boto3
    ssm = boto3.client('ssm', region_name=REGION)
    script = base64.b64encode(Path(script_path).read_bytes()).decode()
    command = ('echo ' + script + ' | base64 --decode > /root/larp-ssm-step.sh && bash /root/larp-ssm-step.sh '
               + ' '.join(str(int(a)) for a in args) + '; rc=$?; rm -f /root/larp-ssm-step.sh; exit $rc')
    sent = ssm.send_command(InstanceIds=[PRIMARY], DocumentName='AWS-RunShellScript', TimeoutSeconds=600,
                            Parameters={'commands': [command], 'executionTimeout': ['600']})
    command_id, deadline = sent['Command']['CommandId'], time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(2)
        try:
            result = ssm.get_command_invocation(CommandId=command_id, InstanceId=PRIMARY)
        except ssm.exceptions.InvocationDoesNotExist:
            continue
        if result['Status'] not in ('Pending', 'InProgress', 'Delayed'):
            if result['Status'] != 'Success':
                raise RuntimeError(Path(script_path).name + ' ' + result['Status'])
            return command_id, result.get('StandardOutputContent', '')
    raise TimeoutError(Path(script_path).name + ' did not finish')


def refresh(work, seed_blocks=()):
    work = Path(work)
    monitor_dir, site, out = work / 'monitor', work / 'site', work / 'artifact'
    for folder in (monitor_dir, site, out):
        folder.mkdir(parents=True, exist_ok=True)
    saved = work / 'refresh-state.json'
    if not seed_blocks and saved.is_file():
        seed_blocks = json.loads(saved.read_text()).get('blocks', [])
    chain = poll(monitor_dir, sorted(seed_blocks))
    command_id, stdout = ssm_run(EXPORT, 40)
    merged = decisions.merge(stdout, monitor_dir)
    data = build.build(monitor_dir, site)
    (out / 'larp-dashboard.html').write_text(artifact_page((site / 'index.html').read_text()))
    (out / 'data.json').write_bytes((site / 'data.json').read_bytes())
    saved.write_text(json.dumps(dict(blocks=known_blocks(monitor_dir)), sort_keys=True) + '\n')
    return dict(chain=chain, export_command=command_id, export=merged.get('summary'), rounds=merged['rounds'],
                as_of_utc=data['summary']['as_of_utc'], page=str(out / 'larp-dashboard.html'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--work', required=True, help='working folder (monitor state, site, artifact page)')
    ap.add_argument('--seed-blocks', default='', help='comma-separated known transaction blocks, for a first poll')
    args = ap.parse_args()
    seeds = [int(b) for b in args.seed_blocks.split(',') if b.strip()]
    print(json.dumps(refresh(args.work, seeds), sort_keys=True))


if __name__ == '__main__':
    main()
