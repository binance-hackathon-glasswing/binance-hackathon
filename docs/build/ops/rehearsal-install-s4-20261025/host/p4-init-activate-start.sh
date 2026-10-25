# P4 (primary, host mutation; S4 run sheet): create and activate run 5 (S4) in larp_rehearsal5, then start the
# runtime-side services. larp-execution stays disabled until the signer has started (S2, then P5). Until then a
# committed intent waits, unsigned. The S4 profile has no buy window: its flatten began 2026-10-25 10:30 UTC, so every
# round sells; signing ends 2026-10-27 12:00 UTC (IDEA-097).
#   ssm_run.py host/p4-init-activate-start.sh "<reviewer>" "<IDEA-097 record of the run-5 approval>"
# The reviewer and approval reference are arguments: this sheet was drafted before the approval existed.
set -euo pipefail
RUN=larp-dev-rehearsal-20261025-s4
REVIEWER=${1:?reviewer name}; APPROVAL=${2:?IDEA-097 record of the run-5 approval}
REF="IDEA-097 S4: $APPROVAL; dev signed rehearsal $RUN, larp_rehearsal5, S4 e79a92fc carry-over from larp-dev-rehearsal-20261024-s2"
[[ ${#REF} -le 200 ]] || { echo "review reference too long"; exit 3; }
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
grep -q '"database_name": *"larp_rehearsal5"' /etc/larp/runtime.json || { echo "unexpected database"; exit 3; }
cd /opt/larp/current
P=".venv/bin/python"; export PYTHONDONTWRITEBYTECODE=1
AS_RT="runuser -u larp-runtime -g larp-runtime -G larp-evidence --"
$AS_RT $P -m larp.runtime.service init --config /etc/larp/runtime.json --manifest /etc/larp/release.json --root /opt/larp/current
$AS_RT $P -m larp.runtime.service activate --config /etc/larp/runtime.json --manifest /etc/larp/release.json \
  --root /opt/larp/current --reviewer "$REVIEWER" --review-ref "$REF"
systemctl disable --now larp-execution.service 2>/dev/null || true
systemctl start larp-evidence
sleep 5
systemctl start larp-uploader larp-runtime
systemctl start larp-archive.timer
sleep 30
bad=0
for u in larp-evidence larp-uploader larp-runtime larp-execution larp-archive.timer; do
  state=$(systemctl is-active $u || true); restarts=$(systemctl show $u -p NRestarts --value)
  echo "$u $state restarts=$restarts"
  # SJ-06-RV01: fail closed. Execution must still be off; every other unit active with no restarts. A timer has
  # no NRestarts property (empty value), so it only has to be active (SJ-06 P4 finding).
  if [[ $u == larp-execution ]]; then [[ $state != active ]] || bad=1
  elif [[ $u == *.timer ]]; then [[ $state == active ]] || bad=1
  else [[ $state == active && $restarts == 0 ]] || bad=1; fi
done
[[ $bad == 0 ]] || { echo "a unit is not in its expected state; stop here (no P4_DONE)"; exit 5; }
echo P4_DONE
