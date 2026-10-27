"""Which start-up errors refuse a start for good and which are transient (IDEA-109 F2). No runtime imports: the
signer host loads this module too.

The units stop restarting on exit 4 (`RestartPreventExitStatus=2 3 4`), and during the scored run no person may start
them again (F-114, F-124). Exit 4 is kept for what a restart with the same files cannot cure: a contract or value
error, and a missing or unreadable file. Any other OSError (a refused or reset connection, a timeout, DNS, a
`requests` failure, an I/O error) may pass, so the caller re-raises it and the service exits 1 for systemd to restart.
"""

FILE_ERRORS = (FileNotFoundError, PermissionError, IsADirectoryError, NotADirectoryError)


def refuses_start(error):
    """True when `error` is a ContractError/ValueError-style refusal or a file error; False for a transient OSError."""
    return not isinstance(error, OSError) or isinstance(error, FILE_ERRORS)
