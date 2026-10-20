#!/bin/bash
# PC-STOP01: operator-authorized retirement of this exact unsigned trial only.
# Run on primary through SSM after a verified private pre-stop download and after
# runtime/evidence have been stopped and disabled. No decisions, inference or trade.
set -euo pipefail
cd /opt/larp/current
export PYTHONDONTWRITEBYTECODE=1
.venv/bin/python - <<'PY'
import json,subprocess
from pathlib import Path
c=json.loads(Path('/etc/larp/runtime.json').read_bytes())
assert c['run_id']=='larp-dev-llm-trial-20261018t170339z'
assert c['build_id']=='ea25b52325656a19b29e8ddb07b94dd792be6e18'
assert c['database_name']=='larp_trial2' and c['driver']['execution']=='shadow'
for u in ('larp-runtime','larp-evidence','larp-execution'):
 assert subprocess.run(['systemctl','is-active',u],capture_output=True).stdout.strip()==b'inactive',u
 assert subprocess.run(['systemctl','is-enabled',u],capture_output=True).stdout.strip()==b'disabled',u
PY
# Stop the timer first, then any already-running maintenance invocation. Originals
# and outbox states remain. Refuse below if any delivery is left incomplete.
systemctl disable --now larp-archive.timer
systemctl stop larp-archive.service
.venv/bin/python - <<'PY'
from contextlib import contextmanager
from pathlib import Path
import hashlib,json,time
from larp.runtime.database import IamPostgresStore,rds_client
from larp.runtime.operations import cloud_clients
from larp.storage.archive import S3Archive
from larp.storage.postgres import doc
class RO(IamPostgresStore):
 @contextmanager
 def transaction(self):
  with super().transaction() as db:
   db.execute('SET TRANSACTION READ ONLY');yield db
c=json.loads(Path('/etc/larp/operations.json').read_bytes());r=c['run_id']
s=RO(c,rds_client(c['region']))
with s.transaction() as db:
 assert db.execute("SELECT count(*) FROM rounds WHERE run_id=%s AND status<>'CLOSED'",(r,)).fetchone()[0]==0
 assert db.execute("SELECT count(*) FROM audit_chunks WHERE run_id=%s AND status<>'ACK'",(r,)).fetchone()[0]==0
 assert db.execute('SELECT count(*) FROM audit_events e WHERE run_id=%s AND NOT EXISTS '
                   '(SELECT 1 FROM audit_chunks k WHERE k.run_id=e.run_id AND k.event_id=e.event_id)',(r,)).fetchone()[0]==0
 assert db.execute("SELECT count(*) FROM archive_outbox WHERE run_id=%s AND status NOT IN ('ACK','PERMANENT')",(r,)).fetchone()[0]==0
 assert db.execute('SELECT count(*) FROM process_sessions WHERE run_id=%s AND ended_ms IS NULL',(r,)).fetchone()[0]==0
 version,head,epoch=db.execute('SELECT version,head,epoch FROM runs WHERE run_id=%s',(r,)).fetchone()
now=time.time_ns()//1000000
anchor=doc(dict(schema='Anchor.v2',run_id=r,slot_ms=now//3600000*3600000,
                captured_ms=now,sequence=version,head=head,owner_epoch=epoch))
# Independent on-demand namespace: never overwrites or claims to be a scheduled
# hourly outbox entry. Installed S3Archive verifies exact version bytes, checksum,
# compliance retention and KMS encryption by reading the new object back.
a=S3Archive(cloud_clients(c)['s3'],bucket=c['archive_bucket'],account_id=c['account_id'],
            kms_key=c['kms_key'],prefix='archive/manual-trial-stop-20261020',retention_days=c['retention_days'])
receipt=a.put('stopped-journal-anchor.json',anchor.payload,created_ms=now,now_ms=now)
p=Path('/var/lib/larp-trial-stop-records-20261020');p.mkdir(mode=0o700,exist_ok=False)
(p/'stopped-journal-anchor.json').write_bytes(anchor.payload)
(p/'stopped-journal-anchor-receipt.json').write_bytes(receipt.payload)
print(json.dumps({'anchor_status':receipt.read()['status'],'sequence':version,'head':head,
                  'anchor_sha256':hashlib.sha256(anchor.payload).hexdigest(),'captured_ms':now,
                  'retention_days':c['retention_days'],'scheduled_outbox_modified':False},sort_keys=True))
PY
systemctl disable --now larp-uploader
for u in larp-runtime larp-evidence larp-uploader larp-execution larp-archive.service larp-archive.timer; do
 echo "$u";systemctl show "$u" -p ActiveState -p SubState -p UnitFileState -p MainPID
 done
