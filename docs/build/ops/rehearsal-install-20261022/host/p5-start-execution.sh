# P5 (primary, host mutation): start the execution service, only after S2 shows the signer started.
set -euo pipefail
cd /opt/larp/current
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m larp.execution_live.main check \
  --config /etc/larp/execution.json --manifest /etc/larp/release.json --root /opt/larp/current
systemctl enable --now larp-execution.service
sleep 20
echo "larp-execution $(systemctl is-active larp-execution || true) restarts=$(systemctl show larp-execution -p NRestarts --value)"
# Start/refusal lines are fixed JSON texts; they carry no DSN, URL or key.
journalctl -u larp-execution --since "-2 min" --no-pager -o cat | grep -E '^\{' | tail -3 || true
echo P5_DONE
