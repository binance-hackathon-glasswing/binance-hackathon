"""IR179-08: measured bounded-I/O substitute, 1:100 time scale; no hosted qualification."""
import threading
import time
from unittest.mock import patch

from larp.runtime.deferred_models import DeferredAssessments
from larp.runtime.service import Service
from larp.runtime.supervision import Guard
from tests.intelligence import test_openai_pacing as preferred
from tests.support import DatabaseCase


class CompositeCycle(DatabaseCase):
    def test_unsigned_cycle_and_signed_heartbeat_fit_half_the_scaled_watchdog(self):
        for signed in (False,True):
            with self.subTest(signed=signed):
                fixture=preferred.Preferred();fixture.setUp();self.addCleanup(fixture.doCleanups)
                f=fixture.fx;dispatched=[];lock=threading.Lock();hung=[]
                def bounded(url,headers,body,timeout):
                    with lock:dispatched.append(url)
                    threading.Event().wait(timeout)
                    raise TimeoutError('synthetic full transport allowance')
                f.openai=f.aiand=bounded
                router=f.build()
                req=f.w.request(['EXSEMI_Q3_8K'],issuer_id=preferred.fixtures.EXSEMI,
                                job_id='composite',deadline_ms=1800)
                queue=DeferredAssessments(router,root=f.root/'composite',run_id=req.read()['run_id'],
                                          build_id='e'*40,profile_hash=req.read()['policy_profile_hash'])
                elapsed=[]
                class Cycle:
                    def once(inner,now):
                        started=time.monotonic()
                        # Separate balance, initial market/day-roll and three subsequent
                        # quote/market exchanges at their injected bounded maxima.
                        for delay in (.05,.10,.05):threading.Event().wait(delay)
                        if signed:queue.submit('composite',req)
                        else:
                            path=queue.root/'unsigned.jsonl';path.touch(mode=0o600)
                            queue._append(path,dict(kind='REQUEST',request=req.read()))
                            router.audit_hook=lambda e:queue._append(path,e)
                            value=router.assess(req).read()
                            queue._append(path,dict(kind='RESULT',result=value))
                            self.assertEqual(value['status'],'UNAVAILABLE')
                        for delay in (.10,.10,.10):threading.Event().wait(delay)
                        elapsed.append(time.monotonic()-started)
                # Only stage ceilings are scaled; real worker joins, durable SQLite,
                # artifact verification, audit fsync, PG guard and heartbeat execute.
                with patch('larp.intelligence.time_budget.PRIMARY_MAX_MS',600), \
                     patch('larp.intelligence.time_budget.REVIEW_MAX_MS',900):
                    service=Service(self.store,'run','build-1',guard=Guard(self.store,'run',max_failures=3,clear_after=1),
                        driver=Cycle(),clock_ms=f.w.clock,interval_s=0,cycle_timeout_s=6,on_hang=hung.append)
                    self.assertEqual(service.run(max_cycles=1),0)
                    if signed:
                        self.assertFalse(queue.finished.is_set(),'heartbeat must not wait for reviewer completion')
                        self.assertTrue(queue.finished.wait(3))
                        queue.ack('composite')
                    for worker in router._workers:worker.join(2)
                self.assertEqual(hung,[])
                self.assertLess(elapsed[0],3,'300-second target at 1:100 scale')
                self.assertEqual(len(dispatched),3)
                with self.store.transaction() as db:
                    self.assertIsNotNone(db.execute('SELECT ended_ms FROM process_sessions WHERE session_id=%s',
                                                   (service.session_id,)).fetchone()[0])
