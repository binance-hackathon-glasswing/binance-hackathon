# P5 (primary, host mutation): start the execution service, only after S2 shows the signer started.
set -euo pipefail
umask 077
cd /opt/larp/current
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m larp.execution_live.main check \
  --config /etc/larp/execution.json --manifest /etc/larp/release.json --root /opt/larp/current
systemctl enable --now larp-execution.service
sleep 20
state=$(systemctl is-active larp-execution || true); restarts=$(systemctl show larp-execution -p NRestarts --value)
echo "larp-execution $state restarts=$restarts"
# Start/refusal lines are fixed JSON texts; they carry no DSN, URL or key.
journalctl -u larp-execution --since "-2 min" --no-pager -o cat | grep -E '^\{' | tail -3 || true
# SJ-06-RV01: fail closed before T2 removes signer access.
[[ $state == active && $restarts == 0 ]] || { echo "larp-execution is not running cleanly; stop here (no P5_DONE)"; exit 5; }
echo P5_DONE
