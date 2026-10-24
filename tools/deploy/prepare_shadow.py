"""Prepare Gate A without signing, activation or cloud provisioning (IDEA-058).

capture: two read-only Web3 endpoints, from committed/pushed code; artifacts outside Git.
prepare: assemble ignored host inputs; unsigned dev-shadow by default, explicitly reviewed signed/live scope optional.
Neither command starts a service or uploads ai-seeds logs. See docs/build/GATE_A.md.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from larp.contracts import ContractError  # noqa: E402
from larp.execution import Blocked, DependencyUnavailable  # noqa: E402
from larp.runtime.gate_a import MAX_ROUTING_BYTES, capture_inputs, prepare, rpc_provider_list  # noqa: E402
from larp.marketdata.web3 import Artifacts, Unavailable, Web3Client, credentials, encoded, utc  # noqa: E402
from larp.sources.live import Refused, git_state, require_committed  # noqa: E402
import render_host_configs as renderer  # noqa: E402
from qualify_balance_rpc import private_config  # noqa: E402


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


def rpc_providers(path):
    """GA15: the private ordered provider file, read and checked by qualify_balance_rpc's own reader (GA15b), so
    prepare accepts exactly the files qualification accepts. No message ever repeats a URL."""
    return None if path is None else private_config(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    capture = sub.add_parser('capture')
    capture.add_argument('--env-file', type=Path)
    capture.add_argument('--wallet', help='Public dev wallet address; otherwise AI_SEEDS_ADDRESS from the input environment')
    capture.add_argument('--artifact-root', type=Path, required=True)
    capture.add_argument('--output', type=Path, required=True)
    capture.add_argument('--balance-rpc-url', help='Manifested BSC RPC (HTTPS): also capture finalized chain balances '
                         'and refuse while a wallet transaction is in flight (IDEA-058 GA11)')
    capture.add_argument('--balance-rpc-source-id', help='Source ID recorded with that RPC')
    capture.add_argument('--balance-rpc-config', type=Path, help='Private ordered provider file (git-ignored); the '
                         'chain read uses its first provider. Not with --balance-rpc-url (GA15)')
    assembly = sub.add_parser('prepare')
    assembly.add_argument('--terraform-output', type=Path, required=True)
    assembly.add_argument('--profile', type=Path, required=True)
    assembly.add_argument('--capture', type=Path, required=True)
    assembly.add_argument('--calendar', type=Path, default=ROOT / 'config/runtime/session-calendar.2026.json')
    assembly.add_argument('--run-id', required=True)
    assembly.add_argument('--build-id', required=True, help='Exact CI bundle commit SHA')
    assembly.add_argument('--rds-ca-sha256', required=True)
    assembly.add_argument('--sec-contact', help='Public SEC User-Agent identity; never a credential')
    assembly.add_argument('--balance-rpc-url', help='Manifested BSC RPC (HTTPS) for the chain-balance check (IDEA-055)')
    assembly.add_argument('--balance-rpc-source-id', help='Source ID recorded with that RPC')
    assembly.add_argument('--balance-rpc-config', type=Path, help='Private ordered provider file (git-ignored), '
                          'written in order to driver.balance_rpc_providers. Not with --balance-rpc-url (GA15)')
    assembly.add_argument('--out', type=Path, required=True)
    assembly.add_argument('--model-routing', type=Path, help='Reviewed public AIand routing JSON; opt into the '
                          'documented GLM/OpenAI/Kimi shadow trial (no credentials)')
    assembly.add_argument('--model-routing-sha256', help='Expected SHA256 of the reviewed routing file; '
                          'required together with --model-routing')
    assembly.add_argument('--execution', choices=('shadow', 'service'), default='shadow')
    assembly.add_argument('--runtime-mode', choices=('dev', 'live'), default='dev')
    assembly.add_argument('--model-adoption-ref', help='Reviewed signed/live model decision; with service execution')
    assembly.add_argument('--untrusted-router-policy-file',
                          help="Host path of the signer's UntrustedRouterPolicy.v1; enables the runtime quote verifier")
    assembly.add_argument('--untrusted-router-policy-sha256', help='Reviewed SHA-256 of that policy file (LD03)')
    args = parser.parse_args(argv)
    try:
        if args.command == 'capture':
            require_committed(git_state(), False)
            root, output = args.artifact_root.resolve(), args.output.resolve()
            if root.is_relative_to(ROOT) or output.is_relative_to(ROOT):
                raise ContractError('Read-only captures must remain outside the repository')
            if output.exists():
                raise ContractError('Capture already exists')
            providers = rpc_provider_list(args.balance_rpc_url, args.balance_rpc_source_id,
                                          rpc_providers(args.balance_rpc_config))
            keys = credentials(args.env_file)
            client = Web3Client(keys['BINANCE_API_KEY'], keys['BINANCE_SECRET_KEY'], artifacts=Artifacts(root))
            rpc = None
            if providers is not None:
                from larp.execution_live.chain import Rpc
                first = providers[0]  # primary first; prepare accepts a capture from any listed provider
                rpc = Rpc(first['url'], artifacts=Artifacts(root / 'chain'), source_id=first['source_id'])
            value = capture_inputs(client, args.wallet or keys.get('AI_SEEDS_ADDRESS'), rpc=rpc)
            output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with output.open('xb') as stream:
                stream.write(encoded(value) + b'\n')
            print(json.dumps(dict(captured=True, signing_enabled=False, round_logs_uploaded=False)))
            return 0
        routing_raw = None
        if (args.model_routing is None) != (args.model_routing_sha256 is None):
            raise ContractError('Model routing file and reviewed SHA256 are required together')
        if args.model_routing is not None:
            with args.model_routing.open('rb') as stream:
                routing_raw = stream.read(MAX_ROUTING_BYTES + 1)
        capture_raw = args.capture.read_bytes()
        wallet = json.loads(capture_raw)['wallet']
        configs = renderer.render(renderer.outputs(json.loads(args.terraform_output.read_bytes())),
                                  wallet, args.rds_ca_sha256)
        files = prepare(configs, profile_raw=args.profile.read_bytes(), capture_raw=capture_raw,
                        calendar_raw=args.calendar.read_bytes(), run_id=args.run_id, build_id=args.build_id,
                        now=utc(), sec_contact=args.sec_contact,
                        balance_rpc_url=args.balance_rpc_url, balance_rpc_source_id=args.balance_rpc_source_id,
                        balance_rpc_providers=rpc_providers(args.balance_rpc_config),
                        model_routing_raw=routing_raw, model_routing_sha256=args.model_routing_sha256,
                        execution=args.execution, runtime_mode=args.runtime_mode, adoption_ref=args.model_adoption_ref,
                        untrusted_router_policy_file=args.untrusted_router_policy_file,
                        untrusted_router_policy_sha256=args.untrusted_router_policy_sha256)
        write_new(args.out, files)
        report = json.loads(files['preparation-report.json'])
        # No account IDs, wallet, contacts, endpoints, credentials or raw input data in stdout.
        summary = dict(prepared=True, gate_a_passed=False, signing_enabled=False,
                       missing_inputs=report['missing_inputs'], host_checks=report['host_checks'])
        if 'model_routing' in report:
            summary.update(assessor='aiand_routed', model_checks=report['model_routing']['checks'])
        print(json.dumps(summary))
        return 0
    except (ContractError, Unavailable, Refused, renderer.Refused, OSError, ValueError, KeyError, TypeError,
            AttributeError, Blocked, DependencyUnavailable, subprocess.SubprocessError) as error:
        # These three carry no secret values (identity, scale, freshness text and public tickers). Web3, RPC, OS and
        # parsing errors may echo a URL or header, so only their class is printed (GA13d).
        detail = str(error) if isinstance(error, (ContractError, Refused, renderer.Refused)) else type(error).__name__
        print(json.dumps(dict(prepared=False, reason='INPUTS_REFUSED', detail=detail, signing_enabled=False)))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
