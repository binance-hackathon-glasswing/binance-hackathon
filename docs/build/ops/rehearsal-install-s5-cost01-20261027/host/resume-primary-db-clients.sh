# Resume (primary, host mutation; SJ-06 J8 DB incident): start the database clients again after the database is
# resized and available. Same order as P4/P5: uploader, runtime and archive timer first, execution last. Fails closed
# unless each service is active and its restart counter did not move during a 90 s watch.
set -euo pipefail
umask 077
systemctl start larp-uploader larp-runtime
systemctl start larp-archive.timer
sleep 20
systemctl start larp-execution
declare -A before
for u in larp-uploader larp-runtime larp-execution; do before[$u]=$(systemctl show $u -p NRestarts --value); done
sleep 90
bad=0
for u in larp-evidence larp-uploader larp-runtime larp-execution larp-archive.timer; do
  state=$(systemctl is-active $u || true); now=$(systemctl show $u -p NRestarts --value)
  echo "$u $state restarts=$now (at start ${before[$u]:-n/a})"
  [[ $state == active ]] || bad=1
  [[ -z ${before[$u]:-} || $now == "${before[$u]}" ]] || bad=1
done
for u in larp-runtime larp-execution larp-uploader; do
  journalctl -u $u --since "-3 min" --no-pager -o cat | grep -E '^\{' | tail -2 | cut -c1-300 || true
done
[[ $bad == 0 ]] || { echo "a unit is not running cleanly; stop here (no RESUME_DONE)"; exit 5; }
echo RESUME_DONE
