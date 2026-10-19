# R8 (host mutation): bind ea25b52 with this host's configs, run checks, create and activate the new run in
# larp_trial2, then start the unsigned services. larp-execution stays disabled and stopped.
set -euo pipefail
BUILD=ea25b52325656a19b29e8ddb07b94dd792be6e18
REF="IDEA-066 PC-DEPLOY02: Yao Zhu chat approval 2026-10-18; PR178 OpenAI JSON fix, local build ea25b52 (no CI), unsigned capped trial, larp_trial2"
[[ ${#REF} -le 200 ]] || { echo "review reference too long"; exit 3; }
cd /opt/larp/current
readlink -f /opt/larp/current | grep -q $BUILD
[[ ! -e /etc/larp/release.json ]] || { echo "release.json exists; not rebinding"; exit 3; }
P=".venv/bin/python"; export PYTHONDONTWRITEBYTECODE=1
$P -m larp.runtime.preflight --bind /opt/larp/current/release-manifest.json --root /opt/larp/current \
  --output /etc/larp/release.json --registration-evidence /etc/larp/registration-evidence.json \
  --config /etc/larp/operations.json --runtime-config /etc/larp/runtime.json \
  --service-config uploader=/etc/larp/uploader.json
chmod 0644 /etc/larp/release.json
echo "release.json $(sha256sum /etc/larp/release.json | cut -d' ' -f1)"
$P -m larp.runtime.preflight --manifest /etc/larp/release.json --root /opt/larp/current
AS_RT="runuser -u larp-runtime -g larp-runtime -G larp-evidence --"
$AS_RT $P -m larp.runtime.service check --config /etc/larp/runtime.json --manifest /etc/larp/release.json --root /opt/larp/current
install -d -m 0700 /root/gate-a-evidence
R=/root/gate-a-evidence/routes-${BUILD:0:7}-$(date -u +%Y%m%dT%H%M%SZ).json
# The report goes to the file only (its lines name every destination host, including the database endpoint).
if $P -m larp.runtime.routes --role primary --config runtime=/etc/larp/runtime.json --config uploader=/etc/larp/uploader.json \
     --config operations=/etc/larp/operations.json --root /opt/larp/current --output "$R" > /dev/null; then
  echo "routes PASS $(sha256sum "$R" | cut -d' ' -f1) destinations=$(grep -c '"status"' "$R" || true)"
else
  echo "routes FAILED; report kept at $R on the host"; exit 5
fi
chronyc tracking | grep -E 'Reference ID|Stratum|System time|Leap status'
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
journalctl -u larp-runtime -u larp-evidence -u larp-uploader --since "-2min" -o cat --no-pager \
  | grep -o '"release_verified": *[a-z]*' | sort | uniq -c || true
echo R8_DONE
