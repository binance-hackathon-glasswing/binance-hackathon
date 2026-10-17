"""Read-only, local qualification of an IDEA-058 prepared shadow package.

Exit 0 means the local files pass; it never means Gate A passed. No database,
AWS client, network transport, service, activation or uploader is constructed.
CI artifact download/hash verification and every hosted drill remain separate.
"""
import argparse
import copy
import json
from pathlib import Path
import re

from larp.contracts import ContractError, Document
from larp.runtime import gate_a

REQUIRED = frozenset(('runtime.json', 'uploader.json', 'operations.json', 'strategy-profile.json',
                      'session-calendar.json', 'initial-state.json', 'input-capture.json',
                      'preparation-report.json'))
OPTIONAL = frozenset(('evidence.env', 'model-routing.json'))
MAX_FILE_BYTES = 16 * 1024 * 1024


def read_file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ContractError('Invalid local file')
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ContractError('Local file exceeds budget')
    return raw


def package_files(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ContractError('Prepared directory required')
    names = {p.name for p in directory.iterdir()}
    if not REQUIRED <= names or names - REQUIRED - OPTIONAL:
        raise ContractError('Unexpected or missing package file')
    files = {name: read_file(directory / name) for name in sorted(names)}
    report = json.loads(files['preparation-report.json'])
    if (report.get('schema') != 'GateAPreparation.v1' or report.get('prepared') is not True
            or report.get('gate_a_passed') is not False or report.get('signing_enabled') is not False
            or report.get('host_checks') != dict.fromkeys(gate_a.HOST_CHECKS, 'NOT_RUN')):
        raise ContractError('Expected an unqualified preparation report')
    if report.get('input_hashes') != {n: gate_a.digest(raw) for n, raw in files.items()
                                     if n != 'preparation-report.json'}:
        raise ContractError('Preparation hashes differ')
    return files, report


def check_scope(values, report):
    runtime, uploader, operations, state = (values[n] for n in
                                            ('runtime.json', 'uploader.json', 'operations.json', 'initial-state.json'))
    driver = runtime['driver']
    signed = report.get('execution') == 'service'
    mode = report.get('runtime_mode')
    if (mode not in ('dev', 'live') or (not signed and mode != 'dev')
            or any(v.get('mode') != mode for v in (runtime, uploader, state))
            or driver.get('execution') != ('service' if signed else 'shadow')
            or driver.get('assessor') not in (('aiand_routed',) if signed else ('deterministic', 'aiand_routed'))
            or driver.get('intelligence_mode') != ('live' if signed else 'shadow') or 'signing' in driver
            or driver.get('cadence_ms') != gate_a.CADENCE_MS or driver.get('day_roll_window_ms') != gate_a.DAY_ROLL_MS
            or report.get('execution') not in ('shadow', 'service')):
        raise ContractError('Preparation scope differs')
    ref = driver.get('model_adoption_ref')
    if signed and (type(ref) is not str or not ref.strip() or report.get('model_adoption_ref') != ref):
        raise ContractError('Signed scope requires the reviewed adoption reference')
    if not signed and ('model_adoption_ref' in driver or 'model_adoption_ref' in report):
        raise ContractError('Unexpected signed adoption in shadow scope')
    routed = driver['assessor'] == 'aiand_routed'
    if routed != ('model-routing.json' in values) or routed != ('model_routing' in report):
        raise ContractError('Model routing file and preparation scope differ')
    if routed and report['model_routing'] != gate_a.model_routing_report(
            values['model-routing.json'], driver.get('model_routing_sha256')):
        raise ContractError('Model preparation report differs')
    run_id, build_id = report['run_id'], report['build_id']
    if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', run_id)
            or not re.fullmatch(r'[0-9a-f]{40}', build_id)
            or any(c.get('run_id') != run_id for c in (runtime, uploader, operations, state))
            or any(c.get('build_id') != build_id for c in (runtime, uploader))):
        raise ContractError('Run/build identities differ')
    wallet = gate_a.wallet_address(values['input-capture.json']['wallet'])
    if any(c.get('wallet_address') != wallet for c in (runtime, uploader)) or state.get('wallet_id') != wallet:
        raise ContractError('Wallet identities differ')
    # Local DSN credentials are never read; this path checks the hosted IAM configuration.
    if any(c.get('database_dsn_file') for c in (runtime, uploader, operations)):
        raise ContractError('Hosted IAM configuration required')
    connection = ('database_host', 'database_name', 'database_ca_file', 'database_ca_sha256', 'region')
    if any(any(c.get(k) != runtime.get(k) for k in connection) for c in (uploader, operations)):
        raise ContractError('Service database identities differ')


def check_inputs(files, values):
    runtime, profile, capture = (values[n] for n in ('runtime.json', 'strategy-profile.json', 'input-capture.json'))
    driver = runtime['driver']
    model_keys = ('model_routing_file', 'model_routing_sha256', 'model_budget_root')
    if driver.get('assessor') == 'aiand_routed':
        gate_a.model_routing(files['model-routing.json'], driver.get('model_routing_sha256'))
        if (driver.get('model_routing_file') != gate_a.MODEL_ROUTING_FILE
                or driver.get('model_budget_root') != gate_a.MODEL_BUDGET_ROOT):
            raise ContractError('Prepared model paths differ from the shared host paths')
    elif 'model-routing.json' in files or any(k in driver for k in model_keys):
        raise ContractError('Unexpected model configuration in deterministic preparation')
    pins = ((runtime, 'initial_state_sha256', 'initial_state_file', 'initial-state.json'),
            (driver, 'strategy_profile_sha256', 'strategy_profile_file', 'strategy-profile.json'),
            (driver, 'session_calendar_sha256', 'session_calendar_file', 'session-calendar.json'))
    for config, pin, path, name in pins:
        if config.get(pin) != gate_a.digest(files[name]) or Path(config[path]).name != name:
            raise ContractError('Runtime input pin differs')
    if profile.get('mode') != 'LIVE' or profile.get('environment') != ('FINAL' if runtime['mode'] == 'live' else 'REHEARSAL'):
        raise ContractError('Reviewed LIVE rehearsal profile required')
    gate_a.validate_live(profile)
    if capture.get('schema') != 'GateAInputs.v1' or driver['issuers'] != gate_a.issuer_map(capture):
        raise ContractError('Captured issuer binding differs')
    # Freshness is enforced at capture/preparation and again by the running balance check;
    # this read-only transfer check does not pretend old captures are current balances.
    gate_a.check_chain(capture)
    from larp.runtime.service import balance_providers
    providers = balance_providers(driver)
    if not providers or capture['chain'].get('source_id') != providers[0]['source_id']:
        raise ContractError('Chain capture and configured RPC differ')
    if values['initial-state.json'] != gate_a.initial_state(capture, profile, runtime['run_id'], mode=runtime['mode']):
        raise ContractError('Starting state differs from captured balances')
    calendar = gate_a.SessionCalendar(values['session-calendar.json'])
    for at in (capture['observed_at'], profile['signing_end']):
        calendar(int(gate_a.instant(at).timestamp() * 1000))


def check_configs(values, ca_file):
    from larp.audit.service import validate_config as validate_uploader
    from larp.runtime.operations import validate_config as validate_operations
    from larp.runtime.service import balance_settings, validate_config as validate_runtime
    ca = read_file(ca_file)
    for name, validate in (('runtime.json', validate_runtime), ('uploader.json', validate_uploader),
                           ('operations.json', validate_operations)):
        config = copy.deepcopy(values[name])
        if config.get('database_ca_sha256') != gate_a.digest(ca):
            raise ContractError('Pinned RDS CA differs')
        # Validate the same bytes before transfer; the configured /etc path exists only on the host.
        config['database_ca_file'] = str(Path(ca_file).resolve())
        validate(config)
    balance_settings(values['runtime.json']['driver'], values['runtime.json']['mode'])


def check_release(manifest_path, release_root, report):
    from larp.runtime.preflight import bind_manifest
    manifest = Document(read_file(manifest_path))
    value = manifest.read()
    registered = json.loads(read_file(Path(release_root) / 'config/release/repository.v1.json'))['repository']
    if (value.get('build_id') != report['build_id'] or value.get('repository') != registered
            or value.get('build_origin') not in (registered, registered + '.git')
            or value.get('remote_verified') is not True):
        raise ContractError('Expected matching registered-repository CI release bytes')
    # Reuse the production code/register/path checks without writing or registering its returned manifest.
    bind_manifest(manifest, release_root)


def source_reasons(files, artifact_root, release_root):
    from larp.intelligence.config import load_config
    from larp.sources.register import live_preflight, load_edgar_terms, load_register
    lines = files['evidence.env'].decode('utf-8').splitlines()
    signed = json.loads(files['runtime.json'])['driver']['execution'] == 'service'
    intelligence_mode = 'live' if signed else 'shadow'
    if (len(lines) != 3 or lines[:2] != ['LARP_ARTIFACT_ROOT=/var/lib/larp-evidence',
                                       'LARP_EVIDENCE_CONFIG_MODE=' + intelligence_mode]
            or not lines[2].startswith('LARP_SEC_USER_AGENT=')):
        raise ContractError('Expected generated public evidence environment')
    contact = json.loads(lines[2].partition('=')[2])
    root = Path(release_root)
    load_config(intelligence_mode, root / 'config/intelligence')
    register = root / 'config/sources/sources.v1.json'
    # Return only counts to the caller. Source/exception text is never reflected in stdout.
    return live_preflight(load_register(register)[0],
                          {'LARP_SEC_USER_AGENT': contact, 'LARP_ARTIFACT_ROOT': str(artifact_root)},
                          load_edgar_terms(register))


def qualify(directory, *, rds_ca=None, ci_manifest=None, release_root=None, artifact_root=None):
    checks = {}
    result = dict(schema='GateALocalQualification.v1', local_ready=False, gate_a_passed=False,
                  signing_enabled=False, remote_ci_verified=False, checks=checks,
                  host_checks=dict.fromkeys(gate_a.HOST_CHECKS, 'NOT_RUN'))

    def run(name, fn, *, missing=False):
        if missing:
            checks[name] = 'NOT_RUN'
            return False
        try:
            fn()
        except Exception:
            # Files and SDK/validation errors can include local addresses or URL credentials.
            checks[name] = 'FAIL'
            return False
        checks[name] = 'PASS'
        return True

    package = []
    if not run('PACKAGE_INTEGRITY', lambda: package.extend(package_files(directory))):
        return result
    files, report = package
    values = {}
    if not run('PACKAGE_JSON', lambda: values.update({n: json.loads(raw) for n, raw in files.items()
                                                     if n.endswith('.json')})):
        return result
    run('UNSIGNED_IDENTITIES', lambda: check_scope(values, report))
    run('PINNED_INPUTS', lambda: check_inputs(files, values))
    run('SERVICE_CONFIGS', lambda: check_configs(values, rds_ca), missing=rds_ca is None)
    run('CI_RELEASE_BYTES', lambda: check_release(ci_manifest, release_root, report),
        missing=ci_manifest is None or release_root is None)

    def sources():
        if source_reasons(files, artifact_root, release_root or gate_a.ROOT):
            raise ContractError('Source prerequisites unavailable')
    run('SOURCE_TERMS', sources, missing=artifact_root is None or 'evidence.env' not in files)
    result['local_ready'] = all(status == 'PASS' for status in checks.values())
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', required=True, type=Path)
    parser.add_argument('--rds-ca', type=Path, help='local copy of the CI bundle RDS CA')
    parser.add_argument('--ci-manifest', type=Path, help='unbound release-manifest.json from the downloaded CI bundle')
    parser.add_argument('--release-root', type=Path, help='release/ from that same bundle')
    parser.add_argument('--artifact-root', type=Path, help='local retained terms store, outside Git')
    args = parser.parse_args(argv)
    report = qualify(args.prepared, rds_ca=args.rds_ca, ci_manifest=args.ci_manifest,
                     release_root=args.release_root, artifact_root=args.artifact_root)
    print(json.dumps(report, sort_keys=True))
    return 0 if report['local_ready'] else 4


if __name__ == '__main__':
    raise SystemExit(main())
