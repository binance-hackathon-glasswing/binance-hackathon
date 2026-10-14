"""Run host preflight in systemd's main process, then exec the service (IDEA-047 R13).

    python -m larp.runtime.launch <preflight arguments> -- -m <service module> <service arguments>

An invalid release exits 4 where RestartPreventExitStatus can see it. A successful preflight replaces this process
with the service using the same interpreter and PID, preserving systemd signal handling and service exit codes.
"""
import os
import sys

from larp.runtime import preflight


def main(argv=None, *, execv=os.execv):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        boundary = args.index('--')
    except ValueError:
        return 4
    service = args[boundary + 1:]
    if not service or not args[:boundary]:
        return 4
    if preflight.main(args[:boundary]) != 0:
        return 4
    try:
        execv(sys.executable, [sys.executable, *service])
    except OSError:
        # No arbitrary exception text: it may contain host-local paths or configuration.
        return 1
    return 0  # injected execv in offline tests only; a real successful exec never returns


if __name__ == '__main__':
    raise SystemExit(main())
