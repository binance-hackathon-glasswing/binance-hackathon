# R3 (host mutation), after r1 paused rounds and an hourly anchor slot after that stop is ACK.
# $1 = run being retired (larp-dev-llm-trial-20261018t160739z), $2 = its build (86b1476...).
# Stops the remaining services, takes consistent copies of the evidence store and the model-budget ledger,
# and moves (never deletes) the run's configs. The ledger itself stays in place for the next run.
set -euo pipefail
RUN=$1; BUILD=$2
cd /opt/larp/current
readlink -f /opt/larp/current | grep -q "$BUILD" || { echo "unexpected current release"; exit 3; }
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
[[ $(systemctl is-active larp-runtime || true) != active ]] || { echo "runtime still active; run r1 first"; exit 3; }
stop_ms=$(date -d "$(systemctl show larp-runtime -p InactiveEnterTimestamp --value)" +%s%3N)
echo "runtime stopped at_ms=$stop_ms"
env PYTHONDONTWRITEBYTECODE=1 STOP_MS=$stop_ms .venv/bin/python - <<'PY'
from contextlib import contextmanager
from pathlib import Path
import json, os, sys
from larp.runtime.database import IamPostgresStore, rds_client
class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY'); yield db
c = json.loads(Path('/etc/larp/operations.json').read_text()); s = RO(c, rds_client(c['region'])); r = c['run_id']
with s.transaction() as db:
    anchor = db.execute("SELECT max(slot_ms) FROM archive_outbox WHERE run_id=%s AND kind='anchor' AND status='ACK'",
                        (r,)).fetchone()[0]
    pending = db.execute("SELECT kind,status,count(*) FROM archive_outbox WHERE run_id=%s AND status NOT IN "
                         "('ACK','PERMANENT') GROUP BY kind,status", (r,)).fetchall()
    chunks = dict(db.execute('SELECT status,count(*) FROM audit_chunks WHERE run_id=%s GROUP BY status', (r,)).fetchall())
    unchunked = db.execute('SELECT count(*) FROM audit_events e WHERE run_id=%s AND NOT EXISTS (SELECT 1 FROM audit_chunks k '
                           'WHERE k.run_id=e.run_id AND k.event_id=e.event_id)', (r,)).fetchone()[0]
x = dict(run_id=r, database=c['database_name'], latest_anchor_ack_slot_ms=anchor, stop_ms=int(os.environ['STOP_MS']),
         pending_archive=pending, chunks=chunks, unchunked=unchunked)
print(json.dumps(x, sort_keys=True))
if anchor is None or anchor <= x['stop_ms'] or pending or set(chunks) - {'ACK'} or unchunked:
    sys.exit('run not fully anchored/drained yet; wait for the next hourly anchor ACK and rerun')
PY
systemctl stop larp-archive.timer
for i in $(seq 1 60); do [[ $(systemctl is-active larp-archive.service || true) == active ]] || break; sleep 2; done
systemctl stop larp-uploader larp-evidence
for u in larp-runtime larp-uploader larp-evidence larp-execution larp-archive.service larp-archive.timer; do
  echo "$u $(systemctl is-active $u || true)"
done
H=/etc/larp-history/${BUILD:0:7}-$RUN
[[ ! -e $H ]] || { echo "history dir already exists; not overwriting"; exit 3; }
install -d -m 0750 -o root -g root /etc/larp-history "$H"
for f in release.json runtime.json operations.json uploader.json initial-state.json strategy-profile.json \
         session-calendar.json evidence.env registration-evidence.json model-routing.json; do
  [[ -f /etc/larp/$f ]] && mv -n "/etc/larp/$f" "$H/$f"
done
(cd "$H" && sha256sum * > SHA256SUMS && chmod 0444 SHA256SUMS)
ls -la /etc/larp "$H" | sed -E 's/ +/ /g'
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
# Evidence store and poll log: consistent copies beside them.
B=/var/lib/larp-evidence/preserved-pre-redeploy-$STAMP
install -d -m 0750 -o larp-evidence -g larp-evidence "$B"
runuser -u larp-evidence -- env B=$B python3 - <<'PY'
import os, sqlite3
src = sqlite3.connect('file:/var/lib/larp-evidence/evidence.sqlite?mode=ro', uri=True)
dst = sqlite3.connect(os.environ['B'] + '/evidence.sqlite'); src.backup(dst); dst.close(); src.close()
PY
runuser -u larp-evidence -- cp -p /var/lib/larp-evidence/live/polls.jsonl "$B/polls.jsonl"
(cd "$B" && sha256sum evidence.sqlite polls.jsonl | tee SHA256SUMS)
# Model-budget ledger: consistent SQLite backup-API copy (never a file copy of a live database). The ledger stays.
LB=/var/lib/larp-runtime/model-budget-backups
install -d -m 0700 -o larp-runtime -g larp-runtime $LB
runuser -u larp-runtime -- env LB=$LB STAMP=$STAMP python3 - <<'PY'
import json, os, sqlite3
src = sqlite3.connect('file:/var/lib/larp-runtime/model-budget/openai-budget.sqlite?mode=ro', uri=True)
path = os.environ['LB'] + '/openai-budget-' + os.environ['STAMP'] + '.sqlite'
dst = sqlite3.connect(path); src.backup(dst); dst.close()
print(json.dumps(dict(ledger_backup=os.path.basename(path),
                      charges_by_state=src.execute('SELECT state,count(*),sum(amount) FROM charges GROUP BY state').fetchall(),
                      trial_charges=src.execute('SELECT count(*) FROM trial_charges').fetchone()[0],
                      trial=src.execute('SELECT stopped,reason FROM trial').fetchall(),
                      switches=src.execute('SELECT count(*) FROM switches').fetchone()[0])))
src.close()
PY
(cd $LB && sha256sum openai-budget-$STAMP.sqlite)
echo R3_DONE
