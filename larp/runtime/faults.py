"""RG2 boundary crash injection (IDEA-042 RG2-D01/D02/H01). Inert unless a drill arms one named point, once.

A signed development drill sets, through an approved systemd drop-in, `LARP_FAULT_POINT` to one point below and
`LARP_FAULT_TOKEN` to the absolute path of a token file it created. When execution reaches that point, the token is
consumed by an atomic rename and the process sends itself SIGKILL: no cleanup, no `finally`, the same as an OOM kill.
The restarted process finds no token and runs normally. Without `LARP_FAULT_POINT` a point costs one environment
lookup and touches no file. A final (`live`) run refuses to start or sign while a point is armed.

    F3  SignerService._sign, before the signature is written     F4  SignerService._sign, after it is written
    F5  Executor.sign, signature verified, before SIGNED_DURABLE
    F7a Executor.broadcast, BROADCAST_ATTEMPTED committed, before the send
    F7b Executor.broadcast, send returned, before the phase commit
    F8  Executor.reconcile, receipt read, before the phase commit
"""
import os
import signal

POINTS = frozenset(('F3', 'F4', 'F5', 'F7a', 'F7b', 'F8'))
POINT_ENV, TOKEN_ENV = 'LARP_FAULT_POINT', 'LARP_FAULT_TOKEN'
_kill = os.kill  # tests replace this; production always sends SIGKILL to its own process


def point(name, environ=os.environ):
    """Crash here if, and only if, this point is armed and its one-shot token can still be consumed."""
    if name not in POINTS:
        raise ValueError('Unknown fault point')
    if environ.get(POINT_ENV) != name:
        return
    token = environ.get(TOKEN_ENV)
    if not token or not os.path.isabs(token):
        return
    try:
        os.rename(token, token + '.consumed')  # atomic: a restarted process can never consume it again
    except OSError:
        return
    _kill(os.getpid(), signal.SIGKILL)


def check(mode, environ=os.environ):
    """Refuse a misconfigured drill in any mode, and any armed point in a final (`live`) run."""
    from larp.contracts import ContractError
    armed = environ.get(POINT_ENV)
    if armed is None:
        return
    if armed not in POINTS:
        raise ContractError('Unknown fault point configured')
    if not os.path.isabs(environ.get(TOKEN_ENV) or ''):
        raise ContractError('An armed fault point needs an absolute token path')
    if mode == 'live':
        raise ContractError('Fault injection is refused in a final (live) run')
