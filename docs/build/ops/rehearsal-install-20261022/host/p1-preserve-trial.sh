# P1 (primary, host mutation): move (never delete) the retired trial's configs to /etc/larp-history/.
# The trial run was stopped and exported 2026-10-20 (PC-STOP01, PR204). Its databases, evidence store and model-budget
# ledger stay in place. Run only after M3, whose probe reads these files. Refuses if any service is active.
set -euo pipefail
RUN=larp-dev-llm-trial-20261018t170339z; BUILD=ea25b52325656a19b29e8ddb07b94dd792be6e18
for u in larp-runtime larp-uploader larp-evidence larp-execution larp-archive.service larp-archive.timer; do
  [[ $(systemctl is-active $u || true) != active ]] || { echo "$u is active; refusing"; exit 3; }
done
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
H=/etc/larp-history/${BUILD:0:7}-$RUN
[[ ! -e $H ]] || { echo "history dir already exists; not overwriting"; exit 3; }
install -d -m 0750 -o root -g root /etc/larp-history "$H"
for f in release.json runtime.json operations.json uploader.json initial-state.json strategy-profile.json \
         session-calendar.json evidence.env registration-evidence.json model-routing.json; do
  if [[ -f /etc/larp/$f ]]; then mv -n "/etc/larp/$f" "$H/$f"; fi
done
(cd "$H" && sha256sum *)
ls /etc/larp
echo P1_DONE
