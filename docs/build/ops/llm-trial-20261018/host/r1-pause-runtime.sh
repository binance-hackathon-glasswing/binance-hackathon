# R1 (host mutation): pause rounds on larp-dev-llm-trial-20261018t160739z because every OpenAI
# primary call is refused (HTTP 400: Responses json_object needs the word 'json' in input) while the ledger keeps
# each attempt as an UNKNOWN maximum charge. Evidence, uploader and archive keep running (source qualification,
# audit delivery, anchors). Nothing is deleted; the ledger, run and journal are untouched.
set -euo pipefail
grep -q '"run_id": *"larp-dev-llm-trial-20261018t160739z"' /etc/larp/runtime.json || { echo "unexpected run"; exit 3; }
systemctl stop larp-runtime
for u in larp-runtime larp-evidence larp-uploader larp-execution larp-archive.timer; do
  echo "$u $(systemctl is-active $u || true)"
done
python3 - <<'PY'
import sqlite3, json
con = sqlite3.connect('file:/var/lib/larp-runtime/model-budget/openai-budget.sqlite?mode=ro', uri=True)
rows = con.execute('SELECT state,count(*),sum(amount) FROM charges GROUP BY state').fetchall()
print(json.dumps(dict(charges_by_state=rows, trial_charges=con.execute('SELECT count(*) FROM trial_charges').fetchone()[0])))
PY
echo STEP9_DONE
