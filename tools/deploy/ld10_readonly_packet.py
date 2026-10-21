"""Generate an in-memory-only primary-host LD10 probe from the reviewed LD02 collector.

The selected profile travels via stdin; no host files, configs, services or ledger are written.
The compressed sanitized result includes private exact quote/portfolio evidence. Keep it outside Git.
"""
import argparse
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def script(profile_bytes):
    source = (ROOT / 'docs/build/ops/ld02-20261020/execution-packet.sh').read_text()
    source = source.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    source = 'SELECTED_PROFILE_B64 = ' + repr(base64.b64encode(profile_bytes).decode()) + '\n' + source
    needle = "    driver = config['driver']\n"
    source = source.replace(needle, "    selected_raw = base64.b64decode(SELECTED_PROFILE_B64)\n    profile = json.loads(selected_raw)\n" + needle, 1)
    source = source.replace("    forbidden = forbidden_values(config, secrets, providers)\n", "    forbidden = [v for v in forbidden_values(config, secrets, providers) if not isinstance(v, str) or v.lower() not in (wallet, wallet[2:])]\n", 1)
    source = source.replace("    return packet, forbidden\n", """    packet['selected_profile_sha256'] = hashlib.sha256(selected_raw).hexdigest()
    packet['private_caps_inputs'] = dict(wallet=wallet, portfolio=portfolio,
        token_decimals={s: observation['tokens'][s]['decimals'] for s in TOKENS},
        quote_artifacts=web3.records)
    # Private review needs the public wallet address. Continue refusing secrets,
    # provider URLs and database endpoints; omit only public token image metadata.
    for record in packet['private_caps_inputs']['quote_artifacts']:
        response_data = record.get('response', {}).get('data')
        rows = response_data if isinstance(response_data, list) else [response_data]
        for row in rows:
            if isinstance(row, dict):
                rr = row.get('routerResult', {})
                for side in ('fromToken', 'toToken'):
                    if isinstance(rr.get(side), dict):
                        rr[side] = {k: v for k, v in rr[side].items()
                                    if k in ('tokenContractAddress', 'decimal')}

    return packet, forbidden
""", 1)
    source = source.replace('    print(text)\n', "    print(base64.b64encode(zlib.compress(text.encode(), 9)).decode())\n", 1)
    return "set -eu\ncd /opt/larp/current\nenv PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'\n" + source + '\nPY\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.output.open('x') as stream:
        stream.write(script(args.profile.read_bytes()))


if __name__ == '__main__':
    main()
