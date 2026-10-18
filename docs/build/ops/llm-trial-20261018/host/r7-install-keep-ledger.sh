# R7 (host mutation): install the prepared ea25b52 package (hash-checked) and its registration evidence.
# The existing model-budget ledger is KEPT exactly as it is: no init, migration, status or export here. A read-only
# SQLite inspection confirms it already carries the same pacing and trial policies as the pinned routing file.
# $1 = artifact bucket, $2 = s3 prefix, $3.. = name=sha256 for each prepared host file.
set -euo pipefail
BUCKET=$1; PREFIX=$2; shift 2
BUILD=ea25b52325656a19b29e8ddb07b94dd792be6e18
ROUTING=a5fca50a6f3e166b48299a0d29e686aa6dbfd2428f4bb011839acc684b222d8d
readlink -f /opt/larp/current | grep -q $BUILD || { echo "ea25b52 is not current; run r5"; exit 3; }
[[ $(systemctl is-active larp-runtime || true) != active ]] || { echo "runtime active"; exit 3; }
for f in release.json runtime.json operations.json uploader.json; do
  [[ ! -e /etc/larp/$f ]] || { echo "/etc/larp/$f already exists; not overwriting"; exit 3; }
done
L=/var/lib/larp-runtime/model-budget/openai-budget.sqlite
[[ -f $L ]] || { echo "expected the existing ledger; refusing to continue without it"; exit 4; }
W=$(mktemp -d /root/pkg.XXXXXX); trap 'rm -rf "$W"' EXIT
declare -A want
for kv in "$@"; do want[${kv%%=*}]=${kv#*=}; done
[[ ${want[model-routing.json]} == "$ROUTING" ]] || { echo "routing hash is not the capped trial file"; exit 3; }
for n in "${!want[@]}"; do
  aws s3 cp --only-show-errors "s3://$BUCKET/$PREFIX$n" "$W/$n"
  [[ $(sha256sum "$W/$n" | cut -d' ' -f1) == "${want[$n]}" ]] || { echo "$n hash differs"; exit 3; }
done
install -m 0640 -o root -g larp-evidence "$W/runtime.json" /etc/larp/runtime.json
install -m 0640 -o root -g larp-uploader "$W/uploader.json" /etc/larp/uploader.json
install -m 0640 -o root -g larp-archive "$W/operations.json" /etc/larp/operations.json
for n in strategy-profile.json session-calendar.json initial-state.json evidence.env model-routing.json; do
  install -m 0644 -o root -g root "$W/$n" "/etc/larp/$n"
done
cat > /etc/larp/registration-evidence.json <<EOF
{"schema":"RegistrationEvidence.v1","build_id":"$BUILD","repository":"https://github.com/binance-hackathon-glasswing/binance-hackathon","evidence_ref":"Existing team registration (GAP-41/F-113, issued ai-seeds secret) unchanged; no new organiser registration. Build $BUILD = merged PR178 (OpenAI JSON-input fix), LOCAL build per Yao 2026-10-18, no CI run (PC-BUILD01). Unsigned dev/shadow LLM trial, larp_trial2 database (IDEA-066 PC-DEPLOY02)."}
EOF
chmod 0644 /etc/larp/registration-evidence.json
[[ $(sha256sum /etc/larp/model-routing.json | cut -d' ' -f1) == "$ROUTING" ]]
grep -q '"database_name": *"larp_trial2"' /etc/larp/runtime.json
(cd /etc/larp && sha256sum runtime.json uploader.json operations.json strategy-profile.json session-calendar.json \
  initial-state.json evidence.env model-routing.json registration-evidence.json)
runuser -u larp-runtime -- python3 - <<'PY'
import json, sqlite3
routing = json.load(open('/etc/larp/model-routing.json'))
con = sqlite3.connect('file:/var/lib/larp-runtime/model-budget/openai-budget.sqlite?mode=ro', uri=True)
def policy(table):
    raw = con.execute(f'SELECT policy FROM {table}').fetchone()[0]
    try: return json.loads(raw)
    except Exception: return raw
pacing, trial = policy('pacing'), policy('trial')
def same(stored, want):
    if isinstance(stored, dict):
        return all(stored.get(k) == v for k, v in want.items())
    return all(str(v) in str(stored) for v in want.values())
x = dict(account=con.execute('SELECT name,total,reserve,external_only,reason FROM account').fetchall(),
         charges_by_state=con.execute('SELECT state,count(*),sum(amount) FROM charges GROUP BY state').fetchall(),
         trial_charges=con.execute('SELECT count(*) FROM trial_charges').fetchone()[0],
         trial_state=con.execute('SELECT stopped,reason FROM trial').fetchall(),
         switches=con.execute('SELECT count(*) FROM switches').fetchone()[0],
         pacing_matches_routing=same(pacing, routing['openai_pacing']),
         trial_matches_routing=same(trial, routing['openai_trial']))
print(json.dumps(x))
if not (x['pacing_matches_routing'] and x['trial_matches_routing']):
    raise SystemExit('ledger policies differ from the pinned routing; stop and review')
PY
echo R7_DONE
