"""IDEA-049-C SJ-11-RH01-P1: the committed run-3 S1 REHEARSAL profile (PF-01 values, weights 1/5). No ports or keys."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import unittest

from larp.contracts import Document
from larp.runtime import gate_a, gate_a_check
from larp.strategy import s1
from larp.strategy.profiles import validate_live
from tests.signer import test_hosted_rehearsal_assembly as hosted
from tests.strategy import test_s1_rehearsal as rh

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence/s1-rehearsal-profile-20261023'
BLOCK, PROFILE = EVIDENCE / 's1-block.json', EVIDENCE / 'rehearsal-s1-deterministic.json'
PROFILE_SHA256 = '6bcf1dfbd7f0c29893dd62bf67d9bcf7a04299b1d24a29d7310b6d769f8c1526'
PROFILE_DIGEST = 'b2c81e99a570ba85566291403afdcf4e15dffdd20b6178592688fd107f71f421'
PROBE_SHA256 = '75547c8e7d3d02e977e9859665f713580f64cc935f41641a3c129edc68fd9b99'
RUN2_USDT, RUN2_BNB = 96_000_000, 5_325_625_054_330_011  # IDEA-049-C SJ-10 BALANCE_CHECKED (micro-USDT, wei)


def profile():
    return json.loads(PROFILE.read_bytes())


def test_p1_block_is_pf01_with_rehearsal_weights():
    cfg = s1.config(dict(s1=json.loads(BLOCK.read_bytes())))
    assert (cfg['high'], cfg['mid'], cfg['low']) == (Fraction(19, 20), Fraction(3, 5), Fraction(3, 10))
    assert (cfg['window'], cfg['band_bps'], cfg['delay'], cfg['start']) == (5, 100, 900, 'UP')
    assert (cfg['cap'], cfg['hard'], cfg['band']) == (Fraction(3, 10), Fraction(7, 20), Fraction(1, 20))
    assert set(cfg['weights'].values()) == {Fraction(1, 5)} and len(cfg['weights']) == 5
    assert (cfg['expiry'], cfg['legs'], cfg['limiter_mode']) == (3, 3, 'DETERMINISTIC')
    assert json.loads(BLOCK.read_bytes())['execution'] == dict(
        open_delay_seconds=1800, close_buffer_seconds=900, max_attempts_per_leg_session=3)


def test_p2_p3_profile_rebuilds_byte_for_byte_and_hashes_are_pinned():
    from tools.deploy.build_rehearsal_candidate import build
    raw = PROFILE.read_bytes()
    p = json.loads(raw)
    rebuilt = build(2, s1_raw=BLOCK.read_bytes(), s1_decision=p['provenance']['s1']['decision_id'])
    assert rebuilt.payload + b'\n' == raw
    assert hashlib.sha256(raw).hexdigest() == PROFILE_SHA256
    assert rebuilt.digest('StrategyProfile.v1') == PROFILE_DIGEST
    assert p['provenance']['s1']['data_hash'] == hashlib.sha256(BLOCK.read_bytes()).hexdigest()
    assert 'PF-01' in p['provenance']['s1']['decision_id'] and 'SJ-11-RH01-P1' in p['provenance']['s1']['decision_id']
    assert (p['environment'], p['baseline'], p['evidence_mode'], p['falsifier_authority']) == (
        'REHEARSAL', 'TREND_GUARDED_VOL', 'SHADOW', 'SHADOW')
    assert p['exit_gas_reserve_units'] == 10 * p['gas_action_budget_units'] == 3_840_000_000_000_000
    validate_live(p)


def test_p3_probe_hash_and_only_the_profile_line_differs_from_the_reviewed_probe():
    from tools.deploy.ld10_readonly_packet import script
    probe = script(PROFILE.read_bytes())
    assert hashlib.sha256(probe.encode()).hexdigest() == PROBE_SHA256
    reviewed = script((ROOT / 'docs/build/evidence/rehearsal-exit-split-20261021/rehearsal-deterministic.json')
                      .read_bytes())
    changed = [(a, b) for a, b in zip(reviewed.splitlines(), probe.splitlines()) if a != b]
    assert len(reviewed.splitlines()) == len(probe.splitlines())
    assert len(changed) == 1 and all(line.startswith('SELECTED_PROFILE_B64 = ') for line in changed[0])


def test_p4_signed_dev_preparation_checks_and_runtime_build():
    files = rh.prepared(profile())
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    assert values['runtime.json']['driver']['assessor'] == 'deterministic'
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)
    rh.build_runtime(PROFILE.read_bytes())


class RunTwoBalances(unittest.TestCase):
    # The hosted-assembly fixture (synthetic packet and bindings); importing its class would re-run its tests.
    setUp = hosted.HostedRehearsalAssembly.setUp

    def test_p5_caps_review_covers_both_reserves_at_run_two_balances(self):
        from tools.deploy import review_rehearsal_caps as tool
        packet = deepcopy(self.packet)
        packet['selected_profile_sha256'] = PROFILE_SHA256
        portfolio = packet['private_caps_inputs']['portfolio']
        portfolio.update(cash_units=RUN2_USDT, bnb_units=RUN2_BNB)
        packet['holdings']['assets'].update(USDT=dict(chain=RUN2_USDT, ledger=RUN2_USDT, cls='MATCH'),
                                            BNB=dict(chain=RUN2_BNB, ledger=RUN2_BNB, cls='MATCH'))
        _, result, _ = tool.collect(packet, self.root / 'p5-private', hosted.BUILD, now=hosted.NOW, profile=PROFILE)
        checks = {c['check']: c for c in result['checks']}
        p = profile()
        assert result['evidence_hashes']['profile'] == PROFILE_SHA256
        assert checks['FULL_BOOK_EXIT_RESERVE'] == dict(check='FULL_BOOK_EXIT_RESERVE',
            required=str(10 * p['gas_action_budget_units']), cap=str(p['exit_gas_reserve_units']), covered=True)
        assert checks['INITIAL_BNB_EXIT_RESERVE'] == dict(check='INITIAL_BNB_EXIT_RESERVE',
            required=str(p['exit_gas_reserve_units']), cap=str(RUN2_BNB), covered=True)
        assert checks['FULL_POSITION_USDT']['covered']
        # No quotes in this synthetic packet, so coverage is incomplete; nothing else blocks.
        assert set(result['blockers']) == {'QUOTE_COVERAGE_INCOMPLETE', 'OWNER_REVIEW_REQUIRED'}
        # Planner gas floor for the first buy (larp/risk/planner.py): BNB - action budget >= exit reserve.
        assert RUN2_BNB - p['gas_action_budget_units'] >= p['exit_gas_reserve_units']
        assert Document.from_dict(p).digest('StrategyProfile.v1') == PROFILE_DIGEST
