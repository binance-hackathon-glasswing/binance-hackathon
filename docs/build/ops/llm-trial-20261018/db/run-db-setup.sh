#!/bin/bash
# Owner-run (Yao). Usage: run-db-setup.sh <new database> <release checkout> <expected commit>
# Opens the SSM port-forward through primary to RDS, runs setup_trial_db.py, closes the tunnel (and its plugin
# child process). Prints no host/ARN/secret.
set -euo pipefail
cd "$(dirname "$0")"
if lsof -nP -iTCP:15432 -sTCP:LISTEN >/dev/null 2>&1; then echo "port 15432 already in use; close the old tunnel first"; exit 3; fi
H=$(/opt/homebrew/bin/python3.12 -I -c "import json;t=json.load(open('/Users/songyaozhu/binance-hackathon/deploy/activation/tf-output.json'));v=t['database_host'];print(v['value'] if isinstance(v,dict) else v)")
LOG="tunnel-$1.log"; : > "$LOG"
/opt/homebrew/bin/aws --profile larp --region ap-southeast-2 ssm start-session --target i-040fc5fea8b700e9a \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "host=$H,portNumber=5432,localPortNumber=15432" > "$LOG" 2>&1 &
T=$!
trap 'pkill -P $T 2>/dev/null || true; kill $T 2>/dev/null || true' EXIT
# Wait for the plugin's own readiness line; a bare TCP probe can consume the forwarded session.
for i in $(seq 1 45); do grep -q 'Waiting for connections' "$LOG" && break; sleep 1; done
grep -q 'Waiting for connections' "$LOG" || { echo "tunnel did not open"; exit 4; }
sleep 2
"${LARP_PG_PYTHON:?set LARP_PG_PYTHON to a Python 3.12 venv with psycopg==3.3.6 and psycopg-binary==3.3.6}" -I setup_trial_db.py "$@"
