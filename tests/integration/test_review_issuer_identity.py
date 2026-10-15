"""IDEA-049-D WR-D1 (#25, A-FND-012, A-T15): policy-requested reviews name the canonical SEC issuer, not the ticker.

Criteria pre-registered in docs/ledger/IDEA-049-D.md "WR-D" before these tests ran. Real policy, market port, registry,
planner and evidence-job consumer; only the Web3 API client is synthetic.
"""

from dataclasses import replace
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.intelligence.agent import check_job
from larp.intelligence.common import IntelligenceError
from larp.intelligence.config import load_registry
from larp.intelligence.scenarios import EXSEMI
from larp.integration.runtime import RuntimePlanner
from larp.marketdata.port import MarketPort
from larp.research.fixtures import changed, snapshot
from larp.strategy.policy import decide
from tests.marketdata.test_live_port import Client
import tests.runtime.test_driver as driver_tests

ROOT = Path(__file__).resolve().parents[2]
NVIDIA = 'SEC-CIK-0001045810'


def review_round():
    """A-T15's construction: actual NVDA market metadata, a held NVDAB position whose horizon review is due."""
    s = snapshot(held={'NVDAB': 2000}, now=datetime(2026, 10, 11, 16, tzinfo=timezone.utc))
    s = replace(s, policy_state=replace(s.policy_state, data=Document.from_dict(
        {'lifecycle': {'NVDAB': {'last_review_session': 70}}})))
    s = changed(s, markets=[m for m in MarketPort(Client(), '0x' + '1' * 40)(0) if m['symbol'] in s.universe])
    ledger = s.context.read()['portfolio']
    for position in ledger['positions'].values():
        position['units'] *= 10**14  # the same quantity at the actual 18-decimal token metadata
        position['decimals'] = 18
    s = changed(s, portfolio=ledger)
    return s, decide(s, s.policy_state)


def horizon_jobs(planner, s, proposal):
    return [j for j in planner._jobs(s, proposal, int(s.observed_at.timestamp() * 1000))
            if j['payload']['reason'] == 'HORIZON_REASSESSMENT']


class ScheduledReviewIssuer(unittest.TestCase):
    def setUp(self):
        self.s, self.proposal = review_round()
        nvda = next(m for m in self.s.context.read()['markets'] if m['symbol'] == 'NVDAB')
        self.assertEqual(nvda['underlying_id'], 'NVDA')  # the fixture keeps the market's own ticker namespace

    def test_a_t15_policy_review_from_real_market_metadata_schedules_the_sec_issuer(self):
        wanted = load_registry().by_token('NVDAB').issuer_id
        self.assertEqual(wanted, NVIDIA)
        jobs = horizon_jobs(RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3), self.s, self.proposal)
        self.assertEqual([j['payload']['issuer_id'] for j in jobs], [wanted])
        # A's explicit proof, unchanged, now passes (it is kept outside default discovery by A).
        result = subprocess.run([sys.executable, 'tests/intelligence/proofs/issue25_runtime_review.py'], cwd=ROOT,
                                env=dict(os.environ, PYTHONPATH=str(ROOT)), capture_output=True, text=True,
                                timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])

    def test_the_scheduled_job_passes_the_evidence_consumer(self):
        [job] = horizon_jobs(RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3), self.s, self.proposal)
        check_job(job, NVIDIA)  # the evidence agent accepts it as this issuer's scheduled job
        with self.assertRaises(IntelligenceError):
            check_job(job, 'NVDA')

    def test_an_explicit_mapping_keeps_synthetic_identities_and_job_ids(self):
        planner = RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3,
                                 issuers={EXSEMI: {'token': 'NVDAB', 'underlying_id': EXSEMI}})
        [job] = horizon_jobs(planner, self.s, self.proposal)
        context = self.s.context.read()
        payload = {'kind': 'REASSESS_ISSUER', 'issuer_id': EXSEMI, 'reason': 'HORIZON_REASSESSMENT',
                   'session': context['session_index']}
        due = context.get('session_started_ms')
        expected = planner._job(payload, due if type(due) is int else int(self.s.observed_at.timestamp() * 1000), 50)
        self.assertEqual(job, expected)

    def test_unresolvable_identity_fails_closed(self):
        planner = RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3,
                                 issuers={'SEC-CIK-0000789019': {'token': 'MSFTB', 'underlying_id': 'MSFT'}})
        jobs = planner._jobs(self.s, self.proposal, int(self.s.observed_at.timestamp() * 1000))
        self.assertEqual(horizon_jobs(planner, self.s, self.proposal), [])  # NVDAB has no issuer here
        self.assertNotIn('NVDA', [j['payload']['issuer_id'] for j in jobs])
        with self.assertRaises(ContractError):
            RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3,
                           issuers={'A': {'token': 'NVDAB', 'underlying_id': 'NVDA'},
                                    'B': {'token': 'NVDAB', 'underlying_id': 'NVDA'}})
        with patch('larp.integration.runtime.load_registry', side_effect=IntelligenceError('unreadable')):
            with self.assertRaises(IntelligenceError):
                RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3)


class ServicePlanner(driver_tests.Composition):
    def test_the_service_planner_uses_the_driver_issuers(self):
        from larp.runtime.service import build_driver
        driver = build_driver(self.config(), driver_tests.Store(), self.secrets)
        self.assertEqual(driver.coordinator.planner.issuer_by_token, {'NVDAB': NVIDIA})


for _name in [n for n in dir(driver_tests.Composition) if n.startswith('test_')]:
    setattr(ServicePlanner, _name, None)  # only this module's test runs here; the originals run in their module


if __name__ == '__main__':
    unittest.main()
