"""PC-FIX01: durable trial boundaries, concurrent reservations and dispatch UTC days."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from larp.intelligence.common import IntelligenceError
from larp.intelligence.model_budget import ModelBudget, AdmissionDeferred
from larp.intelligence.routing import validate_routing_spec

DAY=86_400_000


def trial():
    return dict(schema='OpenAITrial.v1',trial_id='unsigned-v3-test',start_ms=0,end_ms=3*DAY,
                total_micro_usd=8_000_000,utc_day_micro_usd=2_500_000)


class Caps(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'budget';self.now=1000;self.t=trial()
        self.p=dict(schema='OpenAIPacing.v1',total_micro_usd=50_000_000,prior_spent_micro_usd=2_000_000,
                    start_ms=0,end_ms=10*DAY,period_ms=DAY)

    def options(self):return dict(total=50_000_000,reserve=0,pacing=self.p,trial=self.t,clock_ms=lambda:self.now)
    def init(self):return ModelBudget.initialize(self.path,'trial',initial_spent=2_000_000,**self.options())
    def reopen(self):return ModelBudget(self.path,'trial',**self.options())
    def charged(self):
        with sqlite3.connect(self.path) as db:return db.execute('SELECT * FROM charges ORDER BY id').fetchall()

    def test_daily_boundary_includes_reserved_unknown_and_exact_equality(self):
        b=self.init();x=b.admit(1_500_000,'one');b.before_dispatch(x);b.settle(x,None)
        with self.assertRaisesRegex(AdmissionDeferred,'TRIAL_DAILY_LIMIT'):b.admit(1_000_000,'equal')
        y=b.admit(999_999,'fits');self.assertIsNotNone(y)
        with self.assertRaises(AdmissionDeferred):self.reopen().admit(1,'equal-again')
        self.assertEqual(b.snapshot()['trial']['charged_micro_usd'],2_499_999)

    def test_concurrent_workers_cannot_cross_daily_cap(self):
        self.init()
        def run(i):
            try:return self.reopen().admit(1_500_000,str(i))
            except IntelligenceError:return None
        with ThreadPoolExecutor(max_workers=4) as pool:tokens=list(pool.map(run,range(4)))
        self.assertEqual(sum(x is not None for x in tokens),1)

    def test_day_rollover_and_delayed_settlement_keep_dispatch_attribution(self):
        b=self.init();self.now=DAY-1;x=b.admit(2_000_000,'yesterday');b.before_dispatch(x)
        self.now=DAY+1;b.settle(x,1_000_000)
        self.assertEqual(b.snapshot()['trial']['utc_day_charged_micro_usd'],0)
        y=b.admit(2_000_000,'today');b.before_dispatch(y)
        self.assertEqual(b.snapshot()['trial']['charged_micro_usd'],3_000_000)

    def test_dispatch_across_midnight_rechecks_new_day_and_refunds_unsent(self):
        b=self.init();self.now=DAY-1;x=b.admit(2_000_000,'queued')
        self.now=DAY+1;y=b.admit(2_000_000,'new-day');b.before_dispatch(y)
        with self.assertRaisesRegex(AdmissionDeferred,'TRIAL_DAILY_LIMIT'):b.before_dispatch(x)
        self.assertEqual(b.snapshot()['trial']['charged_micro_usd'],2_000_000)
        self.assertEqual(b.snapshot()['trial']['utc_day_charged_micro_usd'],2_000_000)

    def test_total_carries_across_days_and_unknowns(self):
        b=self.init();self.t['end_ms']=5*DAY  # cannot alter a running frozen policy
        with self.assertRaises(IntelligenceError):self.reopen()
        self.t['end_ms']=3*DAY
        for day in range(3):
            self.now=day*DAY+1000;x=b.admit(2_499_999,str(day));b.before_dispatch(x);b.settle(x,None)
        self.assertEqual(b.snapshot()['trial']['charged_micro_usd'],7_499_997)
        self.assertEqual(b.snapshot()['trial']['remaining_micro_usd'],500_003)

    def test_exact_total_refused_even_with_daily_headroom(self):
        self.t['total_micro_usd']=2_000_000;b=self.init()
        with self.assertRaisesRegex(AdmissionDeferred,'TRIAL_TOTAL_LIMIT'):b.admit(2_000_000,'equal')
        self.assertIsNotNone(b.admit(1_999_999,'below'))

    def test_stop_at_actual_boundary_survives_refund_restart_and_clock_rollback(self):
        b=self.init();x=b.admit(2_499_999,'bound');b.before_dispatch(x);b.settle(x,2_500_000)
        self.assertTrue(self.reopen().snapshot()['trial']['stopped'])
        self.now=0
        self.assertIsNone(self.reopen().admit(1,'rollback'))  # existing account latch already refuses all spend
        self.now=DAY+1
        self.assertTrue(self.reopen().snapshot()['trial']['stopped'])

    def test_clock_rollback_without_prior_latch_refuses_and_persists_watermark(self):
        b=self.init();self.now=2000;b.snapshot();self.now=1000
        with self.assertRaisesRegex(AdmissionDeferred,'CLOCK_ROLLBACK'):self.reopen().admit(1,'backward')

    def test_window_boundary_refunds_only_unsent(self):
        b=self.init();x=b.admit(100,'unsent');y=b.admit(200,'sent');b.before_dispatch(y);b.settle(y,None)
        self.now=self.t['end_ms']
        with self.assertRaisesRegex(AdmissionDeferred,'TRIAL_WINDOW_ENDED'):b.before_dispatch(x)
        self.assertEqual(b.snapshot()['trial']['charged_micro_usd'],200)

    def test_existing_ledger_cannot_bypass_trial_by_omitting_or_changing_policy(self):
        self.init()
        with self.assertRaises(IntelligenceError):ModelBudget(self.path,'trial',total=50_000_000,reserve=0,pacing=self.p)
        changed=deepcopy(self.t);changed['total_micro_usd']+=1
        opts=self.options();opts['trial']=changed
        with self.assertRaises(IntelligenceError):ModelBudget(self.path,'trial',**opts)

    def test_explicit_enable_preserves_original_rows_and_account_latch(self):
        opts=self.options();opts.pop('trial')
        b=ModelBudget.initialize(self.path,'trial',initial_spent=2_000_000,**opts)
        b.external_only('OPENAI_CREDIT_EXHAUSTED');before=self.charged()
        upgraded=ModelBudget.enable_trial(self.path,'trial',**self.options())
        self.assertEqual(before,self.charged());self.assertTrue(upgraded.snapshot()['external_only'])

    def test_ambiguous_existing_requests_refuse_migration_without_changing_rows(self):
        opts=self.options();opts.pop('trial')
        b=ModelBudget.initialize(self.path,'trial',initial_spent=2_000_000,**opts)
        b.admit(100,'prior-request');before=self.charged()
        with self.assertRaises(IntelligenceError):ModelBudget.enable_trial(self.path,'trial',**self.options())
        self.assertEqual(before,self.charged())

    def test_trial_config_requires_valid_frozen_limits_and_is_reported(self):
        root=Path(__file__).resolve().parents[2]
        s=json.loads((root/'config/intelligence/aiand-routing.openai-preferred.example.json').read_bytes())
        s['openai_trial']=dict(trial(),start_ms=s['openai_pacing']['start_ms'],end_ms=s['openai_pacing']['end_ms'])
        validate_routing_spec(s)
        for bad in (True,0,-1,1.5):
            mutated=deepcopy(s);mutated['openai_trial']['utc_day_micro_usd']=bad
            with self.subTest(bad=bad),self.assertRaises(IntelligenceError):validate_routing_spec(mutated)
