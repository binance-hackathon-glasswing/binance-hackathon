"""Prepare Gate A without signing, activation or cloud provisioning (IDEA-057).

capture: two read-only Web3 endpoints, from committed/pushed code; artifacts outside Git.
prepare: assemble local ignored host inputs using a separately reviewed LIVE rehearsal profile.
Neither command starts a service or uploads ai-seeds logs. See docs/build/GATE_A.md.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from larp.contracts import ContractError  # noqa: E402
from larp.runtime.gate_a import capture_inputs, prepare  # noqa: E402
from larp.marketdata.web3 import Artifacts, Unavailable, Web3Client, credentials, encoded, utc  # noqa: E402
from larp.sources.live import Refused, git_state, require_committed  # noqa: E402
import render_host_configs as renderer  # noqa: E402


def write_new(directory, files):
    """Exclusive writes; refuse partial replacements and symlink destinations."""
    directory = directory.resolve()
    if not renderer.ignored_by_git(directory):
        raise ContractError('Output must be git-ignored (deploy/activation/<new name>)')
    if directory.exists() and any(directory.iterdir()):
        raise ContractError('Choose a new empty output directory; frozen inputs are never overwritten')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, raw in files.items():
        descriptor = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    capture = sub.add_parser('capture')
    capture.add_argument('--env-file', type=Path)
    capture.add_argument('--artifact-root', type=Path, required=True)
    capture.add_argument('--output', type=Path, required=True)
    assembly = sub.add_parser('prepare')
    assembly.add_argument('--terraform-output', type=Path, required=True)
    assembly.add_argument('--profile', type=Path, required=True)
    assembly.add_argument('--capture', type=Path, required=True)
    assembly.add_argument('--calendar', type=Path, default=ROOT / 'config/runtime/session-calendar.2026.json')
    assembly.add_argument('--run-id', required=True)
    assembly.add_argument('--build-id', required=True, help='Exact CI bundle commit SHA')
    assembly.add_argument('--rds-ca-sha256', required=True)
    assembly.add_argument('--sec-contact', help='Public SEC User-Agent identity; never a credential')
    assembly.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'capture':
            require_committed(git_state(), False)
            root, output = args.artifact_root.resolve(), args.output.resolve()
            if root.is_relative_to(ROOT) or output.is_relative_to(ROOT):
                raise ContractError('Read-only captures must remain outside the repository')
            if output.exists():
                raise ContractError('Capture already exists')
            keys = credentials(args.env_file)
            client = Web3Client(keys['BINANCE_API_KEY'], keys['BINANCE_SECRET_KEY'], artifacts=Artifacts(root))
            value = capture_inputs(client, keys['AI_SEEDS_ADDRESS'])
            output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with output.open('xb') as stream:
                stream.write(encoded(value) + b'\n')
            print(json.dumps(dict(captured=True, signing_enabled=False, round_logs_uploaded=False)))
            return 0
        capture_raw = args.capture.read_bytes()
        wallet = json.loads(capture_raw)['wallet']
        configs = renderer.render(renderer.outputs(json.loads(args.terraform_output.read_bytes())),
                                  wallet, args.rds_ca_sha256)
        files = prepare(configs, profile_raw=args.profile.read_bytes(), capture_raw=capture_raw,
                        calendar_raw=args.calendar.read_bytes(), run_id=args.run_id, build_id=args.build_id,
                        now=utc(), sec_contact=args.sec_contact)
        write_new(args.out, files)
        report = json.loads(files['preparation-report.json'])
        # No account IDs, wallet, contacts, endpoints, credentials or raw input data in stdout.
        print(json.dumps(dict(prepared=True, gate_a_passed=False, signing_enabled=False,
                              missing_inputs=report['missing_inputs'], host_checks=report['host_checks'])))
        return 0
    except (ContractError, Unavailable, Refused, renderer.Refused, OSError, ValueError, KeyError, TypeError,
            AttributeError):
        print(json.dumps(dict(prepared=False, reason='INPUTS_REFUSED', signing_enabled=False)))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
