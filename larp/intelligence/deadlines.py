"""IDEA-083: one declared ceiling and absolute, monotonic dispatch bounds."""
from contextvars import ContextVar
import math
import threading
import time

MAX_ASSESSMENT_MS = 180000
MAX_PRIMARY_MS = MAX_ASSESSMENT_MS // 3
MAX_REVIEW_MS = MAX_ASSESSMENT_MS // 2
CURRENT_DEADLINE = ContextVar('assessment_deadline', default=None)


class Deadline:
    def __init__(self, milliseconds, clock, *, parent=None, monotonic=time.monotonic):
        self.limit, self.clock, self.parent = milliseconds, clock, parent
        self.monotonic = monotonic
        self.started, self.wall = clock(), monotonic()
        self.cancel = threading.Event()

    def remaining(self):
        elapsed = self.clock() - self.started
        if elapsed < 0 or self.cancel.is_set():
            self.cancel.set()
            return 0
        left = max(0, self.limit - max(elapsed, math.ceil((self.monotonic()-self.wall)*1000)))
        return min(left, self.parent.remaining()) if self.parent else left


def dispatch_remaining(milliseconds):
    deadline = CURRENT_DEADLINE.get()
    return min(milliseconds, deadline.remaining()) if deadline else milliseconds
