# P0 (primary, host mutation; SJ-06-A2): set aside what P2/P3 installed from the superseded LOCAL bundle 0286e727...,
# so P2 can install the original CI artifact for the same build. Moves only, never deletes. Refuses if any service is
# active or if P4 already ran (the run would have registered the local manifest; then a new database is needed).
#   p0-supersede-local-bundle.sh <build id> <local manifest sha256>
set -euo pipefail
BUILD=$1; LOCAL_MANIFEST=$2
for u in larp-runtime larp-uploader larp-evidence larp-execution larp-archive.service larp-archive.timer; do
  [[ $(systemctl is-active $u || true) != active ]] || { echo "$u is active; refusing"; exit 3; }
done
R=/opt/larp/releases/$BUILD
[[ $(sha256sum "$R/release-manifest.json" | cut -d' ' -f1) == "$LOCAL_MANIFEST" ]] \
  || { echo "installed release is not the local bundle; nothing to supersede"; exit 3; }
# P4 writes nothing under /etc/larp, so check the database: the run must not exist yet.
cd "$R"
runuser -u larp-runtime -g larp-runtime -G larp-evidence -- env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import json, sys
from larp.runtime.database import open_service_store
from larp.storage.postgres import Conflict
c = json.load(open('/etc/larp/runtime.json'))
store = open_service_store(c)
try:
    store.load(c['run_id'])
except Conflict:
    print(json.dumps(dict(run_exists=False)))
else:
    print(json.dumps(dict(run_exists=True)))
    sys.exit('the run already exists (P4 ran): stop and take a new database')
PY
cd /
T=$(date -u +%Y%m%dT%H%M%SZ)
H=/etc/larp-history/superseded-local-${BUILD:0:7}-$T
install -d -m 0750 -o root -g root "$H"
for f in release.json runtime.json uploader.json operations.json execution.json strategy-profile.json \
         session-calendar.json initial-state.json evidence.env registration-evidence.json untrusted-router-policy.json; do
  if [[ -f /etc/larp/$f ]]; then mv -n "/etc/larp/$f" "$H/$f"; fi
done
install -d -m 0700 /root/superseded
mv -n "$R" "/root/superseded/release-${BUILD:0:7}-local-$T"
for f in /root/releases/larp-${BUILD:0:12}-x86_64.tar.gz /root/releases/larp-${BUILD:0:12}-x86_64.tar.gz.sha256; do
  if [[ -f $f ]]; then mv -n "$f" "/root/superseded/$(basename "$f").local-$T"; fi
done
(cd "$H" && sha256sum *)
ls /etc/larp
echo "current -> $(readlink /opt/larp/current) (dangling until P2 reinstalls)"
echo P0_DONE
