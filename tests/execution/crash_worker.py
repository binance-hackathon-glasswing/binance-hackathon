"""Disposable process-death fixture; no real keys, venue or network requests."""
import os
import sys

from larp.execution import Executor
from larp.execution_live.store import ExecutionStore
from larp.storage.postgres import PostgresStore
from tests.execution.test_postgres_execution import RegistrySigner, ExecutionGuards
from tests.execution_fixtures import FakeDecoder, FakeGuards, FakeVenue, WALLET, finalized


def main():
    stage, key = sys.argv[1:]
    store = ExecutionStore(PostgresStore(os.environ['LARP_TEST_DATABASE_URL']), run_id='run', wallet=WALLET)
    guards = ExecutionGuards(store)

    class CrashVenue(FakeVenue):
        def broadcast(self, signed, epoch, version):
            super().broadcast(signed, epoch, version)
            os._exit(77)  # After possible external send, before a response/state update.

        def outcome(self, tx_hash):
            if stage == 'AFTER_RECEIPT':
                super().outcome(tx_hash)
                os._exit(77)  # After reading receipt, before final-state persistence.
            return super().outcome(tx_hash)

    venue = CrashVenue(store)
    executor = Executor(store, guards, venue, RegistrySigner(store), FakeDecoder())
    state = store.load(key)
    attempt = state.attempts[-1]
    guards.nonce = attempt.payload.nonce
    if stage == 'BEFORE_SIGN':
        os._exit(77)
    if stage == 'AFTER_SIGN':
        # Registry commit is durable, but execution remains AUTHORIZED.
        executor.signer.sign(attempt.attempt_id, attempt.payload, attempt.epoch, attempt.guard_version)
        os._exit(77)
    if stage == 'AFTER_BROADCAST':
        executor.broadcast(key, 30)
    if stage == 'AFTER_RECEIPT':
        venue.outcomes[attempt.tx_hash] = finalized(attempt)
        executor.reconcile(key, 35)
    raise SystemExit('Unknown or unreached crash stage')


if __name__ == '__main__':
    main()
