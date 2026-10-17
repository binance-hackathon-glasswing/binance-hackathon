"""RV-131 R4-R8: synthetic regression cases, not market or policy adoption evidence."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from larp.contracts import ContractError, TargetKind
from larp.risk.planner import plan
from larp.strategy import s1
from larp.strategy.policy import decide
from larp.strategy.schema import equity, markets
from tests.strategy.test_s1_core import block, cfg, evidence, after, WeightFreeze as _WeightFreeze, series, NAMES
from tests.strategy.test_s1_plan import snap, settled, by_symbol, AT_95, AT_60, FALLING, RISING


class PolicyReview(unittest.TestCase):
    def test_entry_only_block_cannot_prevent_an_s1_level_reduction(self):
        state = settled([19, 20])
        state['blocked'] = {'NVDAB': {'reason': 'CLASS_2_ENTRY_BLOCK', 'expires_session': 90}}
        snapshot = snap({n: AT_95 for n in NAMES}, state=state, path=FALLING)
        proposal = decide(snapshot, snapshot.policy_state)
        target = by_symbol(proposal)['NVDAB']
        self.assertEqual((target.kind, target.reason, target.weight),
                         (TargetKind.TARGET_WEIGHT, 'S1_LEVEL_CHANGE', Fraction(3, 25)))
        self.assertIn('NVDAB', proposal.next_policy_state.data.read()['s1']['rebalance'])

    def test_entry_only_block_still_prevents_increasing_the_name(self):
        state = settled([3, 5], trend='DOWN')
        state['blocked'] = {'NVDAB': {'reason': 'CLASS_2_ENTRY_BLOCK', 'expires_session': 90}}
        snapshot = snap({n: AT_60 for n in NAMES}, state=state, path=RISING)
        proposal = decide(snapshot, snapshot.policy_state)
        self.assertEqual(by_symbol(proposal)['NVDAB'].kind, TargetKind.KEEP_QUANTITY)
        self.assertIn('NVDAB', proposal.next_policy_state.data.read()['s1']['rebalance'])

    def test_planner_bounds_a_proposal_by_its_own_frozen_weight(self):
        weights = {s: [9, 40] for s in NAMES}
        weights['NVDAB'] = [1, 10]
        snapshot = snap(profile_changes={'s1': block(weights=weights)})
        proposal = decide(snapshot, snapshot.policy_state)
        proposal = replace(proposal, targets=tuple(
            replace(t, weight=Fraction(57, 200)) for t in proposal.targets if t.symbol == 'NVDAB'))
        result = plan(snapshot, proposal).read()
        p = snapshot.context.read()['profile']
        budget = int(Fraction(19, 200) * (equity(snapshot.context.read()['portfolio'], markets(snapshot, p))
                                        - p['cost_reserve_units']))
        requests = [q for q in result['quote_requests'] if q['symbol'] == 'NVDAB']
        self.assertTrue(requests, result)
        self.assertTrue(all(q['pay_units'] <= budget for q in requests), requests)

    def test_hard_name_trim_uses_current_reduced_target_on_a_hold_round(self):
        for gross, trend, limiter in (([3, 5], 'DOWN', 'NORMAL'), ([3, 10], 'UP', 'SEVERE')):
            with self.subTest(gross=gross):
                state = settled(gross, trend=trend)
                state['s1']['limiter']['level'] = limiter
                snapshot = snap({**{n: 1000 for n in NAMES}, 'NVDAB': 7200}, state=state)
                proposal = decide(snapshot, snapshot.policy_state)
                self.assertEqual(by_symbol(proposal)['NVDAB'].kind, TargetKind.KEEP_QUANTITY)
                result = plan(snapshot, proposal).read()
                requirement = next(r for r in result['requirements'] if r['symbol'] == 'NVDAB')
                p = snapshot.context.read()['profile']
                market = markets(snapshot, p)
                m = market['NVDAB']
                expected = int(Fraction(*gross)*Fraction(1, 5)
                               *(equity(snapshot.context.read()['portfolio'], market)-p['cost_reserve_units'])
                               *10**m['decimals']/m['price_units'])
                self.assertEqual(requirement['max_units'], expected)


class LimiterReview(unittest.TestCase):
    def cut(self, mode='DETERMINISTIC'):
        items = [evidence('suspension', 'TRADING_SUSPENSION', ['NVDAB'], 10)]
        assessment = dict(level='SEVERE', evidence_ids=['suspension'], reason='test', falsifier='test')
        state, _ = s1.limiter_step(None, session=10, cfg=cfg(limiter_mode=mode), evidence=items, assessment=assessment)
        self.assertEqual(state['level'], 'SEVERE')
        return state

    def test_malformed_deterministic_input_does_not_expire_a_cut(self):
        malformed = [dict(), 'bad', [None], [evidence('x', 'CLASS_2_RED_FLAG', [{}], 11)],
                     [evidence('dup', 'SCHEDULED_EVENT', [], 11), evidence('dup', 'SCHEDULED_EVENT', [], 11)]]
        for value in malformed:
            with self.subTest(value=value):
                state = self.cut()
                for session in range(11, 15):
                    state, record = s1.limiter_step(state, session=session, cfg=cfg(), evidence=value, assessment=None)
                    self.assertFalse(record['healthy'])
                    self.assertEqual((state['level'], state['healthy_sessions']), ('SEVERE', 0))

    def test_malformed_evidence_in_model_mode_is_rejected_without_crashing(self):
        state = self.cut('MODEL')
        state, record = s1.limiter_step(state, session=11, cfg=cfg(limiter_mode='MODEL'),
            evidence=[evidence('bad', 'TRADING_SUSPENSION', [{}], 11)],
            assessment=dict(level='SEVERE', evidence_ids=['bad'], reason='test', falsifier='test'))
        self.assertFalse(record['healthy'])
        self.assertEqual(state['level'], 'SEVERE')


class FreezeReview(unittest.TestCase):
    def test_invalid_parameters_fail_with_contract_error(self):
        data = {s: series(_WeightFreeze().make(0.02), s) for s in NAMES}
        for changes in ({'minimum': 1, 'window': 1}, {'minimum': 0}, {'scale': 0},
                        {'scale': 1.5}, {'window': True}, {'minimum': 61, 'window': 60}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                s1.freeze_weights(data, cutoff=after(80), cap=Fraction(3, 10), **changes)
        with self.assertRaises(ContractError):
            s1.freeze_weights([{}], cutoff=after(80), cap=Fraction(3, 10))

    def test_old_pre_gap_returns_are_not_borrowed_into_the_recent_window(self):
        data = {s: series(_WeightFreeze().make(0.02), s) for s in NAMES}
        data[NAMES[0]] = series({k: 1000000 + (k % 2)*1000 for k in [*range(26), *range(100, 106)]}, NAMES[0])
        _, basis = s1.freeze_weights(data, cutoff=after(110), cap=Fraction(3, 10))
        self.assertIn(NAMES[0], basis['substituted_median'])


class ProfileCliReview(unittest.TestCase):
    def run_cli(self, root, *extra):
        return subprocess.run([sys.executable, '-m', 'larp.strategy.profiles', '--summary', str(root/'summary.json'),
            '--predicates', str(root/'predicates.json'), '--output-dir', str(root/'profiles'), *extra],
            capture_output=True, text=True)

    def write_inputs(self, root):
        from tests.strategy.live_fixtures import summary, registry
        (root/'summary.json').write_bytes(summary().payload)
        (root/'predicates.json').write_bytes(registry().payload)
        (root/'s1.json').write_text(json.dumps(block()))

    def test_explicit_s1_cli_selection_and_source_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_inputs(root)
            args = ('--s1-config', str(root/'s1.json'), '--s1-decision', 'SYNTHETIC_REVIEW_NOT_ADOPTED')
            result = self.run_cli(root, *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            path = root/'profiles/final-live.json'
            original = path.read_bytes()
            profile = json.loads(original)
            self.assertEqual(profile['baseline'], s1.BASELINE)
            self.assertEqual(profile['provenance']['s1']['data_hash'], hashlib.sha256((root/'s1.json').read_bytes()).hexdigest())
            self.assertNotEqual(self.run_cli(root, *args).returncode, 0)
            self.assertEqual(path.read_bytes(), original)

    def test_default_remains_equal_weight_and_half_selection_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_inputs(root)
            result = self.run_cli(root, '--s1-config', str(root/'s1.json'))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root/'profiles').exists())
            result = self.run_cli(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((root/'profiles/final-live.json').read_bytes())['baseline'], 'EQUAL_WEIGHT')
