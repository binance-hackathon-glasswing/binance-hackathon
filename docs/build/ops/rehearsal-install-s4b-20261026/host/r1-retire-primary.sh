# R1p (primary, host mutation): retire run larp-dev-rehearsal-20261025-s4 (build 7fc9f60, larp_rehearsal5) so run 6 can be
# installed on S4 (IDEA-097). Stops and disables every unit, so a reboot cannot restart the old run. Moves (never
# deletes) its configs to /etc/larp-history/. The database larp_rehearsal5, its rows and the evidence/state directories
# stay. Run only after M3, whose read-only probe reads these files; X1 then exports run 5's book from the history copy.
set -euo pipefail
RUN=larp-dev-rehearsal-20261025-s4; BUILD=7fc9f6019b54dccaf13b886c2e1123e703abf67a
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
grep -q '"database_name": *"larp_rehearsal5"' /etc/larp/runtime.json || { echo "unexpected database"; exit 3; }
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
         session-calendar.json evidence.env registration-evidence.json untrusted-router-policy.json model-routing.json; do
  if [[ -f /etc/larp/$f ]]; then mv -n "/etc/larp/$f" "$H/$f"; fi
done
(cd "$H" && sha256sum *)
ls /etc/larp
echo R1P_DONE
