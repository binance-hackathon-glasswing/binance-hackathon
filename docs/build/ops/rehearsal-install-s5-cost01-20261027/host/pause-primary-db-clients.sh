# Pause (primary, host mutation; SJ-06 J8 DB incident): stop every primary unit that logs in to the database, so the
# restart storm stops. larp-evidence (local SQLite) keeps polling. Nothing is disabled, so resume-primary-db-clients.sh
# (or a reboot) brings them back. Execution stops first; no trade can be in flight (signing is blocked while the
# database is unreachable).
set -euo pipefail
umask 077
systemctl stop larp-execution.service
systemctl stop larp-runtime.service larp-uploader.service larp-archive.timer larp-archive.service 2>/dev/null || true
sleep 5
bad=0
for u in larp-execution larp-runtime larp-uploader larp-archive.timer larp-archive.service; do
  state=$(systemctl is-active $u || true); echo "$u $state"; [[ $state != active && $state != activating ]] || bad=1
done
echo "larp-evidence $(systemctl is-active larp-evidence || true)"
[[ $bad == 0 ]] || { echo "a database client is still running; stop here (no PAUSE_DONE)"; exit 5; }
echo PAUSE_DONE
