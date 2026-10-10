import os
import unittest
import uuid

from larp.storage.postgres import PostgresStore,doc
from larp.runtime.coordinator import batch_for


class DatabaseCase(unittest.TestCase):
    def setUp(self):
        dsn=os.environ.get('LARP_TEST_DATABASE_URL')
        if not dsn:
            self.skipTest('Disposable PostgreSQL not configured')
        import psycopg
        from psycopg.conninfo import make_conninfo
        self.admin_dsn=dsn
        self.schema='larp_test_'+uuid.uuid4().hex
        with psycopg.connect(dsn) as db:
            db.execute('CREATE SCHEMA '+self.schema)
        self.store=PostgresStore(make_conninfo(dsn,options='-c search_path='+self.schema))
        self.store.migrate()
        self.store.initialize('run','wallet',56,doc(dict(balances=dict(USDT=100,BNB=10,NVDAB=0))))
        self.epoch=self.store.takeover('run',1,offline=True)
        self.addCleanup(self.cleanup_schema)

    def cleanup_schema(self):
        import psycopg
        with psycopg.connect(self.admin_dsn) as db:
            db.execute('DROP SCHEMA '+self.schema+' CASCADE')

    def batch(self,event_id='e1',**kwargs):
        return batch_for(self.store.load('run'),event_id,dict(kind='SYNTHETIC'),**kwargs)


def request(action='HOLD',job='job',cutoff=1791590400000):
    return doc(dict(schema='AssessmentRequest.v1',job_id=job,run_id='run',issuer_id='NVDA',cutoff_ms=cutoff,
        context_hash='c'*64,policy_profile_hash='a'*64,evidence_refs=[dict(source='synthetic',content_hash='e'*64,
        observed_ms=cutoff,available_ms=cutoff,quality='SYNTHETIC')],allowed_tools=[],
        budget=dict(tool_calls=6,deadline_ms=60000),fixture_action=action))


def job(identity='job',lane='policy',due=100,until=200):
    return dict(job_id=identity,lane=lane,due_ms=due,valid_until_ms=until,max_attempts=2,payload={},
        calendar_id='synthetic-calendar-v1',tzdata_version='2026.4',missed='expire' if lane=='policy' else 'catch_up')
