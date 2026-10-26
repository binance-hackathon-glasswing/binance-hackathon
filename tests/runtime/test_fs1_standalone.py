"""PR296-RV01: fresh FINAL preparation/startup, without a rehearsal run or signer. No external calls."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from larp.contracts import ContractError
from larp.runtime import gate_a, gate_a_check
from tests.marketdata.test_session_history import SEMANTICS
from tests.runtime.test_gate_a import NOW, WALLET, Node, rehash, terraform_output, with_chain
import render_host_configs

ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / 'docs/build/evidence/fs1-final-20261025/fs1-final-recovery.json'
ROUTING = ROOT / 'config/intelligence/aiand-routing.fs1.json'


def prepare(**changes):
    from tools.deploy.prepare_fs1 import prepare_final
    configs = render_host_configs.render(render_host_configs.outputs(terraform_output()), WALLET, 'c' * 64)
    capture = with_chain(Node(usdt=170 * 10**18, native=4 * 10**16))
    balances = capture['balances']['response']['data'][0]['tokenAssets']
    balances[0]['rawBalance'], balances[1]['rawBalance'] = str(170 * 10**18), str(4 * 10**16)
    options = dict(wallet=WALLET, database_name='larp_final', capture_raw=json.dumps(rehash(capture)).encode(),
        calendar_raw=(ROOT / 'config/runtime/session-calendar.2026.json').read_bytes(),
        token_history_raw=json.dumps(SEMANTICS).encode(), run_id='larp-final-fs1', build_id='b' * 40, now=NOW,
        adoption_ref='SYNTHETIC FINAL ADOPTION', balance_rpc_url='https://rpc.invalid/',
        balance_rpc_source_id='synthetic-rpc')
    options.update(changes)
    with patch('socket.create_connection', side_effect=AssertionError('No network in preparation')):
        return prepare_final(configs, **options)


def test_fresh_final_preparation_needs_no_rehearsal_and_keeps_exact_pins():
    files = prepare()
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    runtime = values['runtime.json']
    assert runtime['mode'] == 'live' and runtime['run_id'] == 'larp-final-fs1'
    assert all(values[n]['database_name'] == 'larp_final' for n in
               ('runtime.json', 'uploader.json', 'operations.json'))
    assert runtime['driver']['assessor'] == 'aiand_routed'
    assert runtime['driver']['allowance_recovery'] is True
    assert runtime['ai_seeds_dir'] == '/var/lib/larp-runtime/final-' + WALLET[2:] + '/ai-seeds'
    assert runtime['nonce_dir'] == '/var/lib/larp-runtime/final-' + WALLET[2:] + '/nonce'
    assert files['strategy-profile.json'] == FINAL.read_bytes()
    assert files['model-routing.json'] == ROUTING.read_bytes()
    assert runtime['driver']['token_history_sha256'] == hashlib.sha256(files['token-history.json']).hexdigest()
    assert not any(p['units'] for p in values['initial-state.json']['positions'].values())
    assert 'activation_self_check' in values['strategy-profile.json']
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)


@pytest.mark.parametrize('changes', [dict(wallet='0x' + '2' * 40), dict(token_history_raw=None),
    dict(adoption_ref=''), dict(database_name='larp_rehearsal7'), dict(database_name='larp')])
def test_fresh_final_preparation_refuses_mismatched_or_missing_inputs(changes):
    with pytest.raises(ContractError):
        prepare(**changes)


def test_final_preparer_refuses_replacing_its_profile_with_s5(tmp_path, monkeypatch):
    from tools.deploy import prepare_fs1
    path = tmp_path / 'profile.json'
    path.write_bytes((ROOT / 'docs/build/evidence/s5-rehearsal-profile-20261026/rehearsal-s5.json').read_bytes())
    monkeypatch.setattr(prepare_fs1, 'PROFILE', path)
    with pytest.raises(ContractError, match='reviewed pins'):
        prepare()


def test_final_cli_writes_only_local_candidate_files_and_refuses_missing_adoption(tmp_path, monkeypatch, capsys):
    from tools.deploy import prepare_fs1
    import prepare_shadow
    prepared = prepare()
    capture = tmp_path / 'capture.json'; capture.write_bytes(prepared['input-capture.json'])
    history = tmp_path / 'history.json'; history.write_bytes(prepared['token-history.json'])
    terraform = tmp_path / 'terraform.json'; terraform.write_text(json.dumps(terraform_output()))
    monkeypatch.setattr(prepare_fs1, 'utc', lambda: NOW)
    monkeypatch.setattr(prepare_shadow, 'rpc_providers', lambda _: [dict(url='https://rpc.invalid/', source_id='synthetic-rpc')])
    monkeypatch.setattr(render_host_configs, 'ignored_by_git', lambda _: True)
    args = ['--terraform-output', str(terraform), '--wallet', WALLET, '--capture', str(capture),
        '--token-history-config', str(history), '--build-id', 'b' * 40, '--balance-rpc-config', 'synthetic-rpc.json',
        '--rds-ca-sha256', 'c' * 64, '--out', str(tmp_path / 'prepared'), '--model-adoption-ref', 'SYNTHETIC FINAL']
    with patch('socket.socket', side_effect=AssertionError('No network')):
        assert prepare_fs1.main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['status'] == 'FS1_PREPARED_REQUIRES_APPROVAL' and report['signing_enabled'] is False
    assert (tmp_path / 'prepared/strategy-profile.json').read_bytes() == FINAL.read_bytes()
    args[-1] = ''
    args[args.index('--out') + 1] = str(tmp_path / 'refused')
    assert prepare_fs1.main(args) == 4
    assert WALLET not in capsys.readouterr().out and not (tmp_path / 'refused').exists()


def runtime_fixture(profile=FINAL, mode='live', assessor='aiand_routed'):
    from larp.intelligence.model_budget import ModelBudget
    from tests.runtime.test_driver import Composition
    fixture = Composition(); fixture.setUp()
    raw = ROUTING.read_bytes()
    (fixture.root / 'routing.json').write_bytes(raw)
    pacing = json.loads(raw)['openai_pacing']
    ModelBudget.initialize(fixture.root / 'openai-budget.sqlite', json.loads(raw)['budget_account'],
        initial_spent=pacing['prior_spent_micro_usd'], total=pacing['total_micro_usd'], reserve=0, pacing=pacing)
    (fixture.root / 'profile.json').write_bytes(profile.read_bytes())
    history_raw = json.dumps(SEMANTICS).encode()
    (fixture.root / 'token-history.json').write_bytes(history_raw)
    cfg = fixture.config(execution='service', intelligence_mode='live', expiry_grace_ms=5000, assessor=assessor,
        model_routing_file=str(fixture.root / 'routing.json'), model_routing_sha256=hashlib.sha256(raw).hexdigest(),
        model_budget_root=str(fixture.root), model_adoption_ref='SYNTHETIC FINAL ADOPTION',
        strategy_profile_sha256=hashlib.sha256(profile.read_bytes()).hexdigest(),
        token_history_file=str(fixture.root / 'token-history.json'), token_history_sha256=hashlib.sha256(history_raw).hexdigest())
    base = json.loads((ROOT / 'config/runtime/runtime.example.json').read_bytes())['driver']
    for key in ('balance_check_interval_ms', 'balance_check_max_age_ms', 'price_jump_check_bps',
                'assessment_workers', 'continuation_rounds'):
        cfg['driver'][key] = base[key]
    cfg['driver']['balance_rpc_providers'] = [dict(url='https://rpc.invalid/', source_id='synthetic-rpc')]
    cfg['driver']['issuers'] = gate_a.issuer_map(with_chain())
    cfg['mode'] = mode
    return fixture, cfg


def test_final_runtime_builds_from_clean_state_without_s5():
    from larp.intelligence.routing import RoutedAssessor
    from larp.marketdata.history import SessionHistory
    from larp.runtime.service import build_driver
    from tests.runtime.test_driver import Store
    fixture, cfg = runtime_fixture()
    try:
        with patch('socket.create_connection', side_effect=AssertionError('No network during construction')):
            runtime = build_driver(cfg, Store(), dict(fixture.secrets, LARP_AIAND_API_KEY='synthetic-aiand-key'))
        runtime.ports['evidence'].close()
        assert len(runtime.assessments.assessors) == 5
        assert all(isinstance(a, RoutedAssessor) for a in runtime.assessments.assessors)
        assert isinstance(runtime.coordinator.context_builder.series, SessionHistory)
    finally:
        fixture.doCleanups()


def test_fresh_final_caps_assemble_without_a_previous_run_and_reject_stale_or_other_holdings(tmp_path):
    from larp.execution import USDT
    from larp.signer.policy import SigningPolicy
    from tests.runtime.test_fs1_recovery import recovery_inputs
    from tools.deploy import prepare_fs1 as tool
    files = prepare()
    profile = json.loads(files['strategy-profile.json'])
    c, _ = recovery_inputs(profile)
    try:
        runtime = json.loads(files['runtime.json'])
        # Locally available public CA/router artifacts stand in for the identical absolute host paths.
        ca = tmp_path / 'ca.pem'; ca.write_bytes(b'synthetic-public-CA')
        policy = tmp_path / 'router.json'; policy.write_bytes(tool.POLICY.read_bytes())
        runtime.update(database_ca_file=str(ca), database_ca_sha256=hashlib.sha256(ca.read_bytes()).hexdigest())
        runtime['driver']['untrusted_router_policy_file'] = str(policy)
        files['runtime.json'] = json.dumps(runtime).encode()
        c.profile = profile
        c.ledger = json.loads(files['initial-state.json'])
        c.config.update({k: runtime[k] for k in ('mode', 'wallet_address', 'run_id', 'build_id',
            'database_host', 'database_name', 'database_ca_file', 'database_ca_sha256', 'region')})
        c.config.pop('database_dsn_file')
        c.config.update(database_user='larp_execution', allowance_recovery=True,
            untrusted_router_policy_file=str(policy), untrusted_router_policy_sha256=tool.POLICY_SHA,
            gas_budget=profile['gas_action_budget_units'], strategy_profile_file=runtime['driver']['strategy_profile_file'],
            runtime_secret_id=runtime['runtime_secret_id'], rpc_url='https://rpc.invalid/', rpc_source_id='synthetic-rpc',
            market_artifact_root='/var/lib/larp-execution/market', chain_artifact_root='/var/lib/larp-execution/chain')
        decision = json.loads((ROOT / 'docs/build/evidence/signer-numeric-ceilings-20261021.json').read_bytes())
        c.policy = dict(decision['policies']['final']['signing_policy'], allowance_recovery=True)
        c.inputs.update(wallet=WALLET, run_id=runtime['run_id'], build_id=runtime['build_id'], environment='FINAL')
        c.save_inputs()
        c.inputs['files']['profile'] = dict(path=str(FINAL), sha256=tool.PROFILE_SHA)
        c.config['strategy_profile_sha256'] = tool.PROFILE_SHA
        c.inputs['files']['execution_config'] = c.pin('execution_config.json', c.config)
        for n, ref in enumerate(c.inputs['quote_artifacts']):
            quote = json.loads((c.root / ref['path']).read_bytes())
            quote.update(requested_at=NOW)
            quote['params']['userWalletAddress'] = WALLET
            quote['response']['data']['tx'].update(gasPrice='64000000', **{'from': WALLET})
            c.inputs['quote_artifacts'][n] = c.pin(ref['path'], quote)
        with patch('socket.socket', side_effect=AssertionError('Offline assembly only')):
            result = tool.final_services(files, c.inputs, now=NOW, base_dir=c.root)
        signer = json.loads(result['signer.json'])
        assert signer['mode'] == 'live' and signer['wallet_address'] == WALLET
        assert signer['run_id'] == runtime['run_id'] and signer['database_name'] == 'larp_final'
        assert SigningPolicy.from_config(signer['signing_policy']).allowance_recovery
        assert int(signer['signing_policy']['max_input_units'][USDT]) >= profile['per_trade_cap_units'] * 10**12
        assert json.loads(result['signer-assembly-report.json'])['numeric_review']['numeric_status'] == 'COVERED'
        c.ledger['cash_units'] -= 1
        c.inputs['files']['initial_state'] = c.pin('other-holdings.json', c.ledger)
        with pytest.raises(ContractError, match='fresh FINAL initial state'):
            tool.final_services(files, c.inputs, now=NOW, base_dir=c.root)
        c.inputs['files']['initial_state'] = c.pin('fresh-holdings.json', json.loads(files['initial-state.json']))
        with pytest.raises(ContractError):
            tool.final_services(files, c.inputs, now='2026-10-19T13:00:00Z', base_dir=c.root)
    finally:
        c.doCleanups()


@pytest.mark.parametrize('path,mode', [(FINAL, 'live'),
    (ROOT / 'docs/build/evidence/s5-rehearsal-profile-20261026/rehearsal-s5.json', 'dev')])
def test_runtime_cannot_bypass_preparation_with_deterministic_signed_assessment(path, mode):
    from larp.runtime.service import build_driver
    from tests.runtime.test_driver import Store
    fixture, cfg = runtime_fixture(path, mode, 'deterministic')
    try:
        with pytest.raises(ContractError, match='Deterministic signed scope'):
            runtime = build_driver(cfg, Store(), fixture.secrets)
            runtime.ports['evidence'].close()
    finally:
        fixture.doCleanups()
