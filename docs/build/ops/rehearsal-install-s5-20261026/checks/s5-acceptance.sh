# S5-DEPLOY01: bounded read-only post-start evidence; no model/provider/signing calls or secret output.
set -euo pipefail
cd /opt/larp/current
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
import hashlib, json
from larp.audit.delivery import delivery_status
from larp.runtime.database import IamPostgresStore, rds_client

class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY')
            yield db

def load(raw):
    return json.loads(bytes(raw))

def summaries(value, series, models):
    if isinstance(value, dict):
        if value.get('schema') == 'PriceSeries.v1':
            series[value.get('symbol')] = dict(quality=value.get('quality'), history_status=value.get('history_status'),
                bars=len(value.get('bars', [])), adjustment=value.get('corporate_action_version'))
        if isinstance(value.get('model_io'), dict):
            models.append(dict(steps=len(value['model_io'].get('steps', []))))
        for item in value.values():
            summaries(item, series, models)
    elif isinstance(value, list):
        for item in value:
            summaries(item, series, models)

c = json.loads(Path('/etc/larp/execution.json').read_bytes())
runtime = json.loads(Path('/etc/larp/runtime.json').read_bytes())
assert c['run_id'] == runtime['run_id'] == 'larp-dev-rehearsal-20261026-s5'
assert c['database_name'] == runtime['database_name'] == 'larp_rehearsal7'
s = RO(c, rds_client(c['region']))
with s.transaction() as db:
    q, raw = db.execute('SELECT quarantined,projection FROM runs WHERE run_id=%s', (c['run_id'],)).fetchone()
    projection = load(raw)
    series, models = {}, []
    summaries(projection.get('round_records', {}), series, models)
    logs = []
    for rid, raw in db.execute('SELECT round_id,document FROM audit_events WHERE run_id=%s ORDER BY event_id DESC LIMIT 10',
                              (c['run_id'],)).fetchall():
        event = load(raw)
        data = json.loads(event['log'])['data']
        summaries(data['input'], series, models)
        logs.append(dict(round_id=rid, reason_summary_present=bool(data['output'].get('reason_summary')),
                         orders=len(data['orders']), swap_hashes=[x['tx_hash'] for x in data['orders'] if x.get('tx_hash')]))
    delivery = delivery_status(db, c['run_id'])
    result = dict(run_id=c['run_id'], build_id=runtime['build_id'], quarantined=q,
        assessor=runtime['driver']['assessor'], history_sha256=runtime['driver']['token_history_sha256'],
        series=series, model_io=models, recent_logs=logs,
        rounds=dict(db.execute('SELECT status,count(*) FROM rounds WHERE run_id=%s GROUP BY status', (c['run_id'],))),
        delivery=dict(by_status=dict(Counter(delivery['events'].values())), pending_chunks=delivery['pending_chunks']),
        execution_records=[dict(terminal=t, count=n) for t,n in db.execute(
            'SELECT terminal,count(*) FROM execution_records WHERE run_id=%s GROUP BY terminal', (c['run_id'],))])
    print(json.dumps(result, sort_keys=True))
PY
echo S5_ACCEPTANCE_READ_DONE
