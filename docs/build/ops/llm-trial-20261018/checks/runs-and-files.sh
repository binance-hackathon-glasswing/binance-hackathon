set -eu
cd /opt/larp/current
sudo env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from contextlib import contextmanager
from pathlib import Path
import json
from larp.runtime.database import IamPostgresStore,rds_client

class RO(IamPostgresStore):
 @contextmanager
 def transaction(self):
  with super().transaction() as db:
   db.execute('SET TRANSACTION READ ONLY');yield db
c=json.loads(Path('/etc/larp/runtime.json').read_text());s=RO(c,rds_client(c['region']))
out=[]
with s.transaction() as db:
 for r in db.execute('SELECT run_id,wallet_id,chain_id,mode,quarantined,epoch,version,projection FROM runs ORDER BY run_id').fetchall():
  p=json.loads(bytes(r[7]));rv=p.get('registered_version') or {}
  out.append({'run_id':r[0],'wallet_prefix':r[1][:6]+'…'+r[1][-4:],'chain':r[2],'mode':r[3],'quarantined':r[4],'epoch':r[5],'version':r[6],'registered_build':rv.get('build_id'),'same_wallet_as_config':r[1]==c['wallet_address']})
print(json.dumps({'section':'runs_read_only','runs':out,'configured_run_id':c['run_id']},sort_keys=True))
PY
sudo ls -la /etc/larp /opt/larp/releases /var/lib/larp-runtime | sed -E 's/ +/ /g'
