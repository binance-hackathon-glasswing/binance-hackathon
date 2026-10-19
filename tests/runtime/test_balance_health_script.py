"""Offline regression checks for the operator's journal diagnostic; no host calls."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / 'docs/build/ops/llm-trial-20261018/checks/balance-health.sh'


class BalanceHealthScriptTests(unittest.TestCase):
    def setUp(self):
        source = SCRIPT.read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        self.namespace = {'__name__': 'offline_balance_health'}
        exec(compile(source, str(SCRIPT), 'exec'), self.namespace)
        self.state = dict(ActiveState='active', SubState='running', MainPID='123',
                          InvocationID='a' * 32, ExecMainStartTimestampMonotonic='1000000', NRestarts='0')
        self.start_ms = 1_800_000_000_000

    def state_output(self, state):
        return SimpleNamespace(stdout='\n'.join(f'{k}={v}' for k, v in state.items()))

    def event(self, sequence, **event):
        return sequence, json.dumps(dict(event=event)).encode()

    def rows(self, status='MATCH', health=True):
        ms = self.start_ms
        return [self.event(3, kind='BALANCE_CHECKED', checked_ms=ms,
                           check=dict(status=status), observation_sha256='b' * 64),
                self.event(4, kind='ROUND_PLANNED', record=dict(round_id='round', started_ms=ms + 1,
                           policy_input=dict(context=dict(health=dict(balances_ok=health)))))]

    def inspect(self, states, rows=None):
        return self.namespace['inspect_process'](
            dict(run_id='dev', build_id='reviewed'), lambda: next(states),
            lambda config: list(reversed(self.rows() if rows is None else rows)),
            lambda: (self.start_ms + 1000, 2_000_000))

    def test_stable_process_retains_match_and_later_gate(self):
        report = self.inspect(iter([self.state, self.state]))
        self.assertTrue(report['process_identity_stable'])
        self.assertEqual(report['process']['MainPID'], '123')
        self.assertTrue(report['balance_checks'][0]['this_process'])
        self.assertEqual(report['balance_checks'][0]['observation'], 'b' * 16)
        self.assertTrue(report['rounds'][0]['health']['balances_ok'])

    def test_restart_during_query_refuses_partial_attribution(self):
        for key, value in [('MainPID', '124'), ('InvocationID', 'b' * 32),
                           ('ExecMainStartTimestampMonotonic', '2000000'), ('NRestarts', '1')]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'PROCESS_CHANGED'):
                self.inspect(iter([self.state, dict(self.state, **{key: value})]))

    def test_active_service_and_complete_identity_required(self):
        fn = self.namespace['process_state']
        with patch('subprocess.run', return_value=self.state_output(self.state)):
            self.assertEqual(fn(), self.state)
        for key, value in [('ActiveState', 'inactive'), ('SubState', 'dead'), ('MainPID', '0'),
                           ('InvocationID', ''), ('ExecMainStartTimestampMonotonic', '0'), ('NRestarts', '')]:
            with self.subTest(key=key), patch('subprocess.run', return_value=self.state_output(
                    dict(self.state, **{key: value}))), self.assertRaises(ValueError):
                fn()
        missing = self.state.copy()
        missing.pop('MainPID')
        with patch('subprocess.run', return_value=self.state_output(missing)), self.assertRaises(ValueError):
            fn()

    def test_restart_history_and_deficit_do_not_become_current_success(self):
        rows = self.rows('DEFICIT', False)
        result = self.namespace['summarize'](rows, self.start_ms + 2)
        self.assertFalse(result['balance_checks'][0]['this_process'])
        self.assertFalse(result['rounds'][0]['this_process'])
        self.assertFalse(result['rounds'][0]['health']['balances_ok'])
        self.assertEqual(result['balance_checks'][0]['status'], 'DEFICIT')

    def test_decision_time_and_missing_health_are_retained(self):
        row = self.event(5, kind='ROUND_PLANNED', record=dict(
            round_id='delayed', started_ms=self.start_ms - 100, decision_ms=self.start_ms + 100))
        result = self.namespace['summarize']([row], self.start_ms)
        self.assertTrue(result['rounds'][0]['this_process'])
        self.assertIsNone(result['rounds'][0]['health'])

    def test_invalid_future_process_start_refused(self):
        state = dict(self.state, ExecMainStartTimestampMonotonic='3000000')
        with self.assertRaisesRegex(ValueError, 'PROCESS_START_INVALID'):
            self.inspect(iter([state, state]))

    def test_recent_window_keeps_only_requested_number(self):
        result = self.namespace['summarize'](self.rows() * 20, self.start_ms)
        self.assertEqual(len(result['balance_checks']), 8)
        self.assertEqual(len(result['rounds']), 8)


if __name__ == '__main__':
    unittest.main()
