"""Assemble a key-free signer configuration from reviewed numeric inputs (SA-01).

    python -m larp.signer.assembly --inputs /private/path/caps-inputs.json --out /private/path/new-candidate

Offline only. The existing GateBCapsInputs.v1 reviewer rechecks the pinned live
profile, full holdings, policy, execution settings and fresh quotes. All referenced
files, including the CA and selected router evidence/policy at their configured paths, must be
locally available. Success creates an installation candidate, never approval.
The selected run/release/database must be supplied explicitly; no unsigned run
or historical caps are chosen here. No database, AWS, network or wallet key access.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from larp.contracts import ContractError
from larp.execution_live.caps_review import ERRORS, review
from larp.execution_live.gate_b import pinned, read_json
from larp.execution_live.main import router_decoder as execution_decoder
from larp.marketdata.web3 import utc
from larp.runtime.database import IAM_SETTINGS
from larp.signer.policy import EXAMPLE_CAP_BASIS, SigningPolicy
from larp.signer.service import router_decoder, validate_config
from larp.strategy.schema import initial_gas_only

ROOT = Path(__file__).resolve().parents[2]
REMAINING_GATES = [
    'EXACT_POLICY_OWNER_APPROVAL',
    'SIGNING_LIFETIME_27',
    'NATIVE_PROVIDER_AND_ROUTE_FEE_QUALIFICATION',
    'REGISTERED_RELEASE_AND_HOST_ACCEPTANCE',
    'APPROVED_SIGNER_SESSION_AND_KEY_PLACEMENT',
]


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def assemble(inputs, *, now, base_dir):
    """{filename: bytes}; refuse any incomplete numeric or local config checks.

    Input hashes identify reviewed bytes; they do not authenticate provenance or
    an owner's decision. A non-example cap_basis is still an operator assertion.
    Only final release binding and host acceptance can authorize installation.
    """
    numeric = review(inputs, now=now, base_dir=base_dir)
    if numeric['numeric_status'] != 'COVERED':
        raise ContractError('Signer numeric coverage is incomplete')
    profile = pinned(inputs['files']['profile'], base_dir)
    config = pinned(inputs['files']['execution_config'], base_dir)
    policy_value = pinned(inputs['files']['signing_policy'], base_dir)
    policy = SigningPolicy.from_config(policy_value)
    if policy.cap_basis.strip() == EXAMPLE_CAP_BASIS:
        raise ContractError('Exact policy decision required')
    if (config.get('database_dsn_file') not in (None, '')
            or any(type(config.get(key)) is not str or not config[key].strip() for key in IAM_SETTINGS)
            or type(config['run_id']) is not str
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', config['run_id'])):
        raise ContractError('Explicit hosted signer bindings required')
    # The execution decoder also binds the evidence's router to execution's
    # router. The signer independently binds it to its own spender allow-list.
    decoder = execution_decoder(config)
    if decoder.mode not in ('verified', 'untrusted'):
        raise ContractError('Pinned router evidence or an untrusted-router policy required')
    swap_keys = (('router_evidence_file', 'router_evidence_sha256') if decoder.mode == 'verified' else
                 ('untrusted_router_policy_file', 'untrusted_router_policy_sha256'))  # IDEA-070 B02-U, DEV-23
    signer = {key: config[key] for key in (
        'run_id', 'build_id', 'mode', 'wallet_address', *IAM_SETTINGS, *swap_keys)}
    signer.update(schema='SignerService.v1', database_user='larp_signer',
                  key_credential='wallet.key', interval_seconds=1, max_clock_skew_seconds=2,
                  signing_policy=policy_value)
    validate_config(signer)
    router_decoder(signer, policy)
    raw = encoded(signer)
    report = dict(
        schema='SignerAssemblyReport.v1', status='ASSEMBLED_REQUIRES_APPROVAL',
        ready_to_install=False, signing_enabled=False, gate_b_accepted=False,
        scope='OFFLINE_NUMERIC_AND_LOCAL_CONFIGURATION_ONLY', checked_at=now,
        signer_config_sha256=hashlib.sha256(raw).hexdigest(),
        input_hashes={name: ref['sha256'] for name, ref in inputs['files'].items()},
        router_mode=decoder.mode,
        router_evidence_sha256=signer.get('router_evidence_sha256'),
        untrusted_router_policy_sha256=signer.get('untrusted_router_policy_sha256'),
        database_ca_sha256=signer['database_ca_sha256'],
        numeric_review=numeric, allowance_recovery=policy.allowance_recovery, remaining_gates=[
            *[('INITIAL_GAS_RESERVE_SEEDING_AND_ROUTE_FEE_QUALIFICATION'
               if gate == 'NATIVE_PROVIDER_AND_ROUTE_FEE_QUALIFICATION' and initial_gas_only(profile) else gate)
              for gate in REMAINING_GATES],
            ('ROUTER_SOURCE_REVIEW_AND_REAL_ROUTE_REPLAY' if decoder.mode == 'verified' else
             'UNTRUSTED_POLICY_REVIEW_REPLAY_AND_LIVE_PREFLIGHT'),
            *(['ALLOWANCE_RECOVERY_GAS_AND_HOST_ACCEPTANCE'] if policy.allowance_recovery else [])],
    )
    return {'signer.json': raw, 'signer-assembly-report.json': encoded(report)}


def write_new(directory, files):
    """Exclusive private output, with cleanup of this attempt on write failure."""
    directory = Path(directory)
    if directory.is_symlink():
        raise ContractError('Signer output must not be a symlink')
    directory = directory.resolve()
    if directory == ROOT or ROOT in directory.parents:
        raise ContractError('Signer candidates must remain outside the checkout')
    directory.mkdir(mode=0o700)  # existing directories and symlinks always refuse
    created = []
    try:
        for name, raw in files.items():
            path = directory / name
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        directory.rmdir()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path, help='new directory outside the checkout')
    parser.add_argument('--now', help='explicit review timestamp for reproducible offline checks')
    args = parser.parse_args(argv)
    try:
        _, inputs = read_json(args.inputs)
        files = assemble(inputs, now=args.now or utc(), base_dir=args.inputs.resolve().parent)
        write_new(args.out, files)
    except ERRORS:
        # Never echo hostnames, paths, DSNs, raw input or exception messages.
        print(json.dumps(dict(status='SIGNER_ASSEMBLY_REFUSED', ready_to_install=False,
                              signing_enabled=False, gate_b_accepted=False)))
        return 4
    print(json.dumps(dict(status='ASSEMBLED_REQUIRES_APPROVAL', ready_to_install=False,
                          signing_enabled=False, gate_b_accepted=False,
                          signer_config_sha256=hashlib.sha256(files['signer.json']).hexdigest())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
