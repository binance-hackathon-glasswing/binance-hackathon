"""Top-level inference functions for LocalCheckpointModel tests (they run in a worker process)."""

import time


def finish(state):
    """Finishes at once; an input with "block": true never returns in time (a hung inference)."""
    if state.get("block"):
        time.sleep(120)
    return {"action": "FINISH", "claims": [], "notes": "local"}


def broken(state):
    raise RuntimeError("synthetic inference failure")
