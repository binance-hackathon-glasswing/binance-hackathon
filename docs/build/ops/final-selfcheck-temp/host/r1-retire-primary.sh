# R1p (primary, host mutation; IDEA-110 TEMP-SC): retire dev run larp-dev-rehearsal-20261027-s5-cost01 (build 3ae83098, larp_rehearsal8cost01) before the
# final-wallet self-check install. Stops and disables every unit, so a reboot cannot restart the old run. Moves (never
# deletes) its configs to /etc/larp-history/. Its database, rows and evidence/state directories stay.
# The dev wallet is flat (W0-style read 2026-10-28 00:47Z: no stock, no allowance), so nothing is carried over.
set -euo pipefail
umask 077
RUN=larp-dev-rehearsal-20261027-s5-cost01; BUILD=3ae830981b9ce1c4b80a46dbeb086825d91ae7ec
[[ $(readlink -f /opt/larp/current) == /opt/larp/releases/$BUILD ]] || { echo "unexpected source release; refusing retirement"; exit 3; }
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
grep -q '"database_name": *"larp_rehearsal8cost01"' /etc/larp/runtime.json || { echo "unexpected database"; exit 3; }
for u in larp-execution.service larp-runtime.service larp-uploader.service larp-archive.timer larp-archive.service \
         larp-evidence.service; do
  systemctl disable --now "$u" 2>/dev/null || true
done
sleep 3
for u in larp-execution larp-runtime larp-uploader larp-archive.timer larp-archive.service larp-evidence; do
  state=$(systemctl is-active $u || true); enabled=$(systemctl is-enabled $u 2>/dev/null || true)
  echo "$u $state $enabled"
  [[ $state != active && $state != activating && $enabled != enabled ]] || { echo "$u still running or enabled"; exit 5; }
done
H=/etc/larp-history/${BUILD:0:7}-$RUN
[[ ! -e $H ]] || { echo "history dir already exists; not overwriting"; exit 3; }
install -d -m 0750 -o root -g root /etc/larp-history "$H"
for f in release.json runtime.json operations.json uploader.json execution.json initial-state.json strategy-profile.json \
         session-calendar.json evidence.env registration-evidence.json untrusted-router-policy.json model-routing.json token-history.json; do
  if [[ -f /etc/larp/$f ]]; then mv -n "/etc/larp/$f" "$H/$f"; fi
done
(cd "$H" && sha256sum *)
ls /etc/larp
echo R1P_DONE
