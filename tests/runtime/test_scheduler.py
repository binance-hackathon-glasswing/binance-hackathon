from datetime import datetime

from larp.runtime.scheduler import Scheduler,utc_ms
from larp.storage.postgres import Conflict
from tests.support import DatabaseCase,job


class Scheduling(DatabaseCase):
    def test_duplicate_missed_and_backward_ticks(self):
        self.store.commit(self.batch(jobs=[job(),job()]))
        scheduler=Scheduler(self.store,lease_ms=10)
        claim=scheduler.claim('run',self.epoch,'policy',100)
        self.assertIsNone(scheduler.claim('run',self.epoch,'policy',100))
        scheduler.finish('run',claim)
        self.assertIsNone(scheduler.claim('run',self.epoch,'policy',150))
        with self.assertRaises(Conflict): scheduler.claim('run',self.epoch,'policy',99)

    def test_crash_lease_retry_budget_and_stale_completion(self):
        self.store.commit(self.batch(jobs=[job(lane='safety')]))
        scheduler=Scheduler(self.store,lease_ms=10)
        first=scheduler.claim('run',self.epoch,'safety',100)
        second=scheduler.claim('run',self.epoch,'safety',111)
        self.assertEqual(2,second.read()['attempt'])
        with self.assertRaises(Conflict): scheduler.finish('run',first)
        self.assertIsNone(scheduler.claim('run',self.epoch,'safety',122))

    def test_evidence_overload_does_not_consume_safety_capacity(self):
        self.store.commit(self.batch(jobs=[job(str(i),'evidence') for i in range(100)]+[job('safe','safety')]))
        scheduler=Scheduler(self.store)
        self.assertEqual('safe',scheduler.claim('run',self.epoch,'safety',100).read()['job']['job_id'])
        self.assertIsNotNone(scheduler.claim('run',self.epoch,'evidence',101))

    def test_expired_policy_but_reconciliation_catches_up(self):
        self.store.commit(self.batch(jobs=[job(),job('recovery','reconcile')]))
        scheduler=Scheduler(self.store)
        self.assertIsNone(scheduler.claim('run',self.epoch,'policy',300))
        self.assertIsNotNone(scheduler.claim('run',self.epoch,'reconcile',300))

    def test_dst_midnight_and_timezone_provenance(self):
        local=datetime(2026,11,1,1,30)
        early=utc_ms(local,'America/New_York',fold=0)
        late=utc_ms(local,'America/New_York',fold=1)
        self.assertEqual(3600000,late-early)
        before=utc_ms(datetime(2026,10,10,23,59),'UTC')
        after=utc_ms(datetime(2026,10,11,0,0),'UTC')
        self.store.commit(self.batch(jobs=[job('midnight','policy',after,after+60000)]))
        scheduler=Scheduler(self.store)
        self.assertIsNone(scheduler.claim('run',self.epoch,'policy',before))
        self.assertIsNotNone(scheduler.claim('run',self.epoch,'policy',after))
        with self.assertRaises(ValueError): utc_ms(datetime(2026,3,8,2,30),'America/New_York')
