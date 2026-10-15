"""Hung-cycle watchdog for the supervised runtime (IDEA-049 D-FND-004, #35; DR-13, C5).

A process that is alive but stuck inside one cycle (a blocked call, DNS, a lock) never exits, so systemd never
restarts it, and rounds, logs and heartbeats stop with no person allowed to act (F-114). `Watchdog` watches the
current cycle's start time from a daemon thread; when a cycle runs longer than its timeout it prints every thread's
stack (file, line and function names only) and ends the process with exit status 1. The session row stays open, so
the restart of the same build records a RESTART incident, as for any crash.
"""

import faulthandler
import os
import sys
import threading
import time

EXIT_HUNG = 1


def hard_exit(code):
    faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
    os._exit(code)


class Watchdog:
    def __init__(self, timeout_s, *, on_hang=hard_exit, monotonic=time.monotonic):
        if type(timeout_s) not in (int, float) or not timeout_s > 0:
            raise ValueError('Watchdog timeout must be a positive number of seconds')
        self.timeout, self.on_hang, self.monotonic = float(timeout_s), on_hang, monotonic
        self.started, self.fired = None, False
        self.stopping = threading.Event()
        self.thread = None

    def begin(self):
        """Mark the start of a cycle."""
        self.started = self.monotonic()

    def end(self):
        """Mark the end of a cycle; time between cycles is never counted."""
        self.started = None

    def start(self):
        self.thread = threading.Thread(target=self._watch, name='larp-watchdog', daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.stopping.set()

    def _watch(self):
        step = min(self.timeout / 4, 1.0)
        while not self.stopping.wait(step):
            started = self.started
            if started is not None and not self.fired and self.monotonic() - started > self.timeout:
                self.fired = True
                self.on_hang(EXIT_HUNG)
