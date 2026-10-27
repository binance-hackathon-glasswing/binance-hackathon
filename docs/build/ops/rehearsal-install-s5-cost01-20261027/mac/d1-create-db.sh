#!/bin/bash
# D1 (Mac, Yao; S5 run sheet, IDEA-104): create larp_rehearsal8cost01 with the migrations of RC4 d03bbb1, which are
# byte-identical to the S5 build's (checked below). Adapted from the RC7 sheet (larp_rehearsal4) and SJ-04-DB01.
# Opens the SSM port-forward through primary to RDS, runs setup_rehearsal_db.py, closes the tunnel (and its plugin
# child process). Prints no host/ARN/secret. Adapted from redeploy-20261018/db/run-db-setup.sh (PC-DB02).
set -euo pipefail
umask 077
cd "$(dirname "$0")"
# A Python 3.12 venv built from requirements.lock (psycopg); /private/tmp venvs get cleaned, so the default is in $HOME.
PY=${LARP_PY:-$HOME/larp-monitor-venv/bin/python}
[ -x "$PY" ] || { echo "python venv missing"; exit 5; }
MAIN=${LARP_REPO:?set LARP_REPO to the canonical repository checkout}
git -C "$MAIN" diff --quiet d03bbb16cf51277c73d7f381b08f9551d0c10415 3ae830981b9ce1c4b80a46dbeb086825d91ae7ec -- migrations deploy/postgres/roles.sql \
  || { echo "migrations or roles.sql changed since RC4; review before creating the database"; exit 3; }
OUT=${D1_OUT:-$MAIN/deploy/activation/rehearsal-db-run8}; install -d -m 0700 "$OUT"
if lsof -nP -iTCP:15432 -sTCP:LISTEN >/dev/null 2>&1; then echo "port 15432 already in use; close the old tunnel first"; exit 3; fi
H=$(python3 -I -c "import json,os;t=json.load(open(os.environ['LARP_REPO']+'/deploy/activation/tf-output.json'));v=t['database_host'];print(v['value'] if isinstance(v,dict) else v)")
LOG="$OUT/tunnel-larp_rehearsal8cost01.log"; : > "$LOG"
aws --profile larp --region ap-southeast-2 ssm start-session --target i-040fc5fea8b700e9a \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "host=$H,portNumber=5432,localPortNumber=15432" > "$LOG" 2>&1 &
T=$!
trap 'pkill -P $T 2>/dev/null || true; kill $T 2>/dev/null || true' EXIT
# Wait for the plugin's own readiness line; a bare TCP probe can consume the forwarded session.
for i in $(seq 1 45); do grep -q 'Waiting for connections' "$LOG" && break; sleep 1; done
grep -q 'Waiting for connections' "$LOG" || { echo "tunnel did not open"; exit 4; }
sleep 2
D1_OUT="$OUT" "$PY" -I setup_rehearsal_db.py
