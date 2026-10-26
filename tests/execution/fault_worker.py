"""RG2-H01 H5: a child process that runs one executor step with one fault point armed; synthetic only, no network."""
import os
import sys

from larp.execution import Executor
from larp.execution_live.store import ExecutionStore
from larp.storage.postgres import PostgresStore
from tests.execution.test_postgres_execution import ExecutionGuards, RegistrySigner
from tests.execution_fixtures import FakeDecoder, FakeVenue, WALLET, finalized


def main():
    step, key, now = sys.argv[1], sys.argv[2], int(sys.argv[3])
    store = ExecutionStore(PostgresStore(os.environ['LARP_TEST_DATABASE_URL']), run_id='run', wallet=WALLET)
    guards, venue = ExecutionGuards(store), FakeVenue(store)
    executor = Executor(store, guards, venue, RegistrySigner(store), FakeDecoder())
    attempt = store.load(key).attempts[-1]
    guards.nonce = attempt.payload.nonce
    if step == 'reconcile':
        venue.outcomes[attempt.tx_hash] = finalized(attempt)
    getattr(executor, step)(key, now)
    raise SystemExit(0)  # the armed point was not reached: the parent test fails on this exit code


if __name__ == '__main__':
    main()
