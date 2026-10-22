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
for u in larp-evidence larp-uploader larp-runtime larp-execution larp-archive.timer; do
  echo "$u $(systemctl is-active $u || true) restarts=$(systemctl show $u -p NRestarts --value)"
done
echo P4_DONE
