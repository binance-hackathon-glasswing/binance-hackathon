"""Live replay from the journal alone (DR-19; IDEA-042 item 4, IDEA-035 A2).

A live `ContextBuilder` round reads external ports: market, calendar, health and series. Their answers are recorded in
the round's `policy_input.context`, so replay feeds those recorded answers back instead of calling the ports. The
evidence step (gate acceptance and consumption) is pure and is re-run; the model's output comes from the recorded
assessment (`larp.runtime.replay.RecordedAssessment`) and execution facts from the journaled observations. A round
whose context failed re-raises the recorded cause at the first port it reaches, so its batch replays byte-identically.
"""

from copy import copy

from larp.runtime.replay import replay as runtime_replay

FAILURE = "CONTEXT_UNAVAILABLE:"


def _failing(cause: str):
    error = type(cause, (Exception,), {})  # same class name, so the coordinator records the same cause

    def port(*args):
        raise error("Recorded port failure replayed")
    return port


class RecordedPorts:
    """Builds, per journal record, a copy of the live builder whose ports return what they returned then."""

    def __init__(self, builder):
        self.builder = builder

    def builder_for(self, record: dict):
        context = (record.get("policy_input") or {}).get("context") or {}
        cause = next((e[len(FAILURE):] for e in record.get("errors", []) if e.startswith(FAILURE)), None)
        recorded = copy(self.builder)
        if cause is not None:
            recorded.market = recorded.calendar = recorded.health = recorded.series = recorded.gas_quotes = _failing(cause)
            return recorded
        recorded.market = lambda now_ms: context["markets"]
        recorded.calendar = lambda now_ms: {
            "index": context["last_discretionary_session"]
            if now_ms == context.get("last_discretionary_observed_ms") else context["session_index"],
            "remaining": context["remaining_sessions"]}
        if 'execution_session' in context:
            recorded.calendar.window = lambda now_ms: context['execution_session']
        recorded.health = lambda current: context["health"]
        recorded.series = lambda now_ms: context["series"]
        recorded.gas_quotes = (lambda now_ms: context["gas_quotes"]) if "gas_quotes" in context else None
        # ContextBuilder takes the portfolio's mode from the run. Replay runs
        # remain OFFLINE for safety, but the decision originally saw DEV/LIVE.
        # Preserve that recorded input in the copied builder only; never change
        # the target store's mode or activate its signing capability (IDEA-058).
        mode = (context.get('portfolio') or {}).get('mode')
        if mode in ('OFFLINE', 'PAPER', 'DEV', 'LIVE'):
            return RecordedMode(recorded, mode.lower())
        return recorded


class RecordedMode:
    """Replay-only context mode; all other ports/attributes are the copied builder's."""

    def __init__(self, builder, mode):
        self.builder, self.mode = builder, mode

    def __getattr__(self, name):
        return getattr(self.builder, name)

    def __call__(self, current, *args):
        return self.builder(dict(current, mode=self.mode), *args)


def replay_live(batches, initial, target, *, builder, **options):
    """`larp.runtime.replay.replay` with recorded ports: no live port is called."""
    return runtime_replay(batches, initial, target, builder_for=RecordedPorts(builder).builder_for, **options)
