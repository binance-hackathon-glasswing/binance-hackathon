# P4 (primary, host mutation): create and activate the signed rehearsal run in larp_rehearsal1, then start the
# runtime-side services. larp-execution stays disabled until the signer has started (S2, then P5). Until then a
# committed intent waits, unsigned, and the profile allows no buy before 2026-10-23 00:00 UTC anyway.
set -euo pipefail
RUN=larp-dev-rehearsal-20261022
REF="IDEA-049-C SJ-06: Yao Zhu chat approval 2026-10-22; dev signed rehearsal $RUN, larp_rehearsal1, LV-01 build"
[[ ${#REF} -le 200 ]] || { echo "review reference too long"; exit 3; }
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
grep -q '"database_name": *"larp_rehearsal1"' /etc/larp/runtime.json || { echo "unexpected database"; exit 3; }
cd /opt/larp/current
P=".venv/bin/python"; export PYTHONDONTWRITEBYTECODE=1
AS_RT="runuser -u larp-runtime -g larp-runtime -G larp-evidence --"
$AS_RT $P -m larp.runtime.service init --config /etc/larp/runtime.json --manifest /etc/larp/release.json --root /opt/larp/current
$AS_RT $P -m larp.runtime.service activate --config /etc/larp/runtime.json --manifest /etc/larp/release.json \
  --root /opt/larp/current --reviewer "Yao Zhu" --review-ref "$REF"
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
  # SJ-06-RV01: fail closed. Execution must still be off; every other unit active with no restarts.
  if [[ $u == larp-execution ]]; then [[ $state != active ]] || bad=1
  else [[ $state == active && $restarts == 0 ]] || bad=1; fi
done
[[ $bad == 0 ]] || { echo "a unit is not in its expected state; stop here (no P4_DONE)"; exit 5; }
echo P4_DONE
