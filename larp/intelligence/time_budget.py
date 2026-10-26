"""IDEA083 absolute assessment deadlines, shared limits and deterministic tool shares."""
from contextvars import ContextVar
import time

from larp.intelligence.common import IntelligenceError

MAX_ASSESSMENT_MS = 180000
PRIMARY_MAX_MS = 60000
REVIEW_MAX_MS = 90000
ACTIVE_DEADLINE = ContextVar('larp_assessment_deadline', default=None)


def stage_limits(total):
    if type(total) is not int or not 0 < total <= MAX_ASSESSMENT_MS:
        raise IntelligenceError('Invalid assessment deadline')
    primary = min(PRIMARY_MAX_MS, total // 3)
    return primary, min(REVIEW_MAX_MS, total-primary)


def reviewer_tools(total, reserved, count):
    if (type(total) is not int or not 0 <= total <= 6 or type(reserved) is not int
            or not 0 <= reserved <= total or type(count) is not int or count not in (1,2)):
        raise IntelligenceError('Invalid global tool allocation')
    remaining = total-reserved
    return tuple(remaining//count + (i < remaining%count) for i in range(count))


class Deadline:
    def __init__(self, budget_ms, clock, *, parent=None):
        self.clock, self.start, self.wall = clock, clock(), time.monotonic()
        self.budget, self.parent = budget_ms, parent

    def remaining(self):
        elapsed = max(self.clock()-self.start, int((time.monotonic()-self.wall)*1000))
        left = max(0, self.budget-elapsed)
        return min(left,self.parent.remaining()) if self.parent is not None else left


def remaining(allowance):
    deadline = ACTIVE_DEADLINE.get()
    return min(allowance,deadline.remaining()) if deadline is not None else allowance
