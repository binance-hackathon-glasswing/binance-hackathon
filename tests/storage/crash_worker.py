"""Subprocess killed at real PostgreSQL durability boundaries; synthetic only."""

from contextlib import contextmanager
import os
from pathlib import Path
import sys

from larp.audit.delivery import DeliveryWorker
from larp.storage.postgres import PostgresStore,doc
from tests.audit.test_protocol import event
from tests.support import batch_for


def main():
    phase=sys.argv[1]
    store=PostgresStore(os.environ['LARP_TEST_DATABASE_URL'])
    original=store.transaction
    if phase=='before_commit':
        class CrashConnection:
            def __init__(self,connection): self.connection=connection
            def execute(self,sql,params=None):
                result=self.connection.execute(sql,params)
                if sql.startswith('INSERT INTO events'):
                    os._exit(73)
                return result
        @contextmanager
        def crashing():
            with original() as db: yield CrashConnection(db)
        store.transaction=crashing
    if phase in ('before_commit','after_commit'):
        store.commit(batch_for(store.load('run'),'crash',dict(kind='CRASH_FIXTURE'),
            reservation_deltas=[dict(intent_id='i',asset='USDT',units=10)],audit=[event()]))
        os._exit(73)
    if phase=='after_send':
        class Receiver:
            def deliver(self,value):
                with Path(sys.argv[2]).open('wb') as stream:
                    stream.write(value.payload); stream.flush(); os.fsync(stream.fileno())
                # Remote durable write succeeded; controller dies before local ACK.
                os._exit(73)
        DeliveryWorker(store,Receiver(),retry_ms=1).once('run',store.load('run').read()['epoch'],100)
    raise ValueError('Unknown crash phase')


if __name__=='__main__':
    main()
