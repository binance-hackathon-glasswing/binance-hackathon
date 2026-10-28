"""IDEA-110 TA1-TA4: deferred final declarations authorize only the exact pre-scored pipeline test."""
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from larp.contracts import Document
from larp.runtime.register import load_register
from larp.runtime.service import StartRefused, activate_run, temporary_self_check_activation
from larp.storage.postgres import doc
from larp.strategy.schema import instant
from tests.support import DatabaseCase
from tools.deploy.build_selfcheck_temp import build
from tools.deploy.prepare_fs1 import PROFILE

ROOT = Path(__file__).resolve().parents[2]
NOW = int(instant('2026-10-28T02:00:00Z').timestamp() * 1000)
WALLET = '0x' + '5' * 40


def candidate(tmp_path):
    raw = build(fs1_raw=PROFILE.read_bytes(), now='2026-10-28T02:00:00Z').payload + b'\n'
    path = tmp_path / 'profile.json'
    path.write_bytes(raw)
    config = dict(mode='live', run_id='larp-final-selfcheck-temp', database_name='larp_final_selfcheck',
                  wallet_address=WALLET, build_id='b' * 40,
                  driver=dict(strategy_profile_file=str(path), strategy_profile_sha256=hashlib.sha256(raw).hexdigest()))
    manifest = Document.from_dict(dict(schema='ReleaseManifest.v1', build_id='b' * 40,
        repository='https://github.com/binance-hackathon-glasswing/binance-hackathon',
        release_register=load_register(ROOT)))
    return config, manifest


def test_exact_temp_scope_retains_and_records_deferred_rows(tmp_path):
    c, m = candidate(tmp_path)
    scope = temporary_self_check_activation(c, m.read()['release_register'], NOW)
    assert scope['purpose'] == 'TEMPORARY_PIPELINE_SELF_CHECK'
    assert scope['deferred_deviations'] == m.read()['release_register']['draft_deviations']


@pytest.mark.parametrize('change', ['fs1', 'database', 'mode', 'pin', 'file', 'size', 'window',
                                  'missing_register', 'open', 'extra_draft', 'register_hash', 'cutoff', 'previous_day'])
def test_every_scope_mismatch_refuses_before_activation(tmp_path, change):
    c, m = candidate(tmp_path)
    data = m.read()
    now = NOW
    if change == 'fs1': c['run_id'] = 'larp-final-fs1'
    if change == 'database': c['database_name'] = 'larp_final'
    if change == 'mode': c['mode'] = 'dev'
    if change == 'pin': c['driver']['strategy_profile_sha256'] = '0' * 64
    if change == 'file': Path(c['driver']['strategy_profile_file']).unlink()
    if change in ('size', 'window'):
        path = Path(c['driver']['strategy_profile_file'])
        profile = json.loads(path.read_bytes())
        if change == 'size': profile['activation_self_check']['pay_units'] = 1_000_000
        else: profile['activation_self_check']['buy_until'] = '2026-10-29T06:00:00Z'
        path.write_text(json.dumps(profile))
        # Even repinning a modified file must not qualify for the exact exception.
        c['driver']['strategy_profile_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    if change == 'missing_register': data.pop('release_register')
    if change == 'open': data['release_register']['open_deviations'] = ['DEV-01']
    if change == 'extra_draft': data['release_register']['draft_deviations'].append('DEV-25')
    if change == 'register_hash': data['release_register']['deviations_sha256'] = '0' * 64
    if change == 'cutoff': now = int(instant('2026-10-28T06:00:00Z').timestamp() * 1000)
    if change == 'previous_day': now = int(instant('2026-10-27T23:59:59Z').timestamp() * 1000)
    store = Mock()
    store.load.return_value = doc(dict(mode='live', wallet_id=WALLET, projection={}, quarantined=True, epoch=1))
    with pytest.raises(StartRefused):
        activate_run(c, store, Document.from_dict(data), reviewer='Synthetic', review_ref='IDEA-110 TA-01', now_ms=now)
    store.activate.assert_not_called()
    store.commit.assert_not_called()


def test_changed_bytes_without_repin_refuse(tmp_path):
    c, m = candidate(tmp_path)
    Path(c['driver']['strategy_profile_file']).write_text('{}')
    with pytest.raises(StartRefused):
        temporary_self_check_activation(c, m.read()['release_register'], NOW)


class TemporaryActivation(DatabaseCase):
    def test_existing_quarantined_run_registers_build_and_records_explicit_scope(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            c, m = candidate(Path(directory))
            self.store.initialize(c['run_id'], WALLET, 56, doc(dict(balances=dict(USDT=100, BNB=10))), mode='live')
            assert self.store.load(c['run_id']).read()['quarantined']
            result = activate_run(c, self.store, m, reviewer='Synthetic', review_ref='IDEA-110 TA-01', now_ms=NOW)
            assert result['activated'] and not result['signing_enabled']
            run = self.store.load(c['run_id']).read()
            assert not run['quarantined']
            assert run['projection']['registered_version']['build_id'] == c['build_id']
            activated = self.store.event(c['run_id'], 'activate:' + str(result['epoch']))
            assert activated['temporary_self_check']['purpose'] == 'TEMPORARY_PIPELINE_SELF_CHECK'
            assert activated['temporary_self_check']['deferred_deviations'] == load_register(ROOT)['draft_deviations']
            with pytest.raises(StartRefused):
                activate_run(c, self.store, m, reviewer='Synthetic', review_ref='IDEA-110 TA-01', now_ms=NOW + 1)
