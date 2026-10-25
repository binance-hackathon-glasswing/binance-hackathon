"""Peak memory of one storage operation in a fresh process (IDEA-094 AR7).

`python -m tests.runtime.memory_probe <dsn> verify` prints {"growth_bytes": n}: the growth of the process's peak RSS
during a full journal verification of run "run". tracemalloc cannot see libpq's result buffers; RSS can.
"""

import json
import sys

from larp.storage.postgres import PostgresStore


def status(field):
    for line in open('/proc/self/status', encoding='ascii'):
        if line.startswith(field + ':'):
            return int(line.split()[1]) * 1024  # kB
    raise SystemExit('no ' + field)


def main(argv):
    dsn, mode = argv[0], argv[1]
    store = PostgresStore(dsn)
    store.metrics('run')  # connection, imports and a first query before the baseline
    # The peak RSS mark is inherited from the forking test process; reset it (Linux clear_refs 5) and start from
    # the current resident size.
    with open('/proc/self/clear_refs', 'w', encoding='ascii') as refs:
        refs.write('5')
    before = status('VmRSS')
    if mode == 'verify':
        store.verified_snapshot('run')
    else:
        raise SystemExit('unknown mode')
    print(json.dumps(dict(growth_bytes=status('VmHWM') - before)))


if __name__ == '__main__':
    main(sys.argv[1:])
