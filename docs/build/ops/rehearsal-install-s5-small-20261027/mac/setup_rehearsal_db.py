"""D1 (Mac, Yao; IDEA-104 S5): create the signed-rehearsal database larp_rehearsal8 on the existing RDS instance,
apply the migrations of RC4 d03bbb1 (byte-identical to the S5 build; d1-create-db.sh checks), and the reviewed roles.sql with
only the database name changed. Adapted from SJ-04-DB01 (larp_rehearsal1). Reads `larp` read-only. Refuses an
existing database that holds a run. Prints no host, ARN, user or password.

  d1-create-db.sh   (it opens the tunnel and calls this script)
"""
import json, os, subprocess, sys, hashlib
from pathlib import Path
NEW = 'larp_rehearsal8'
SRC = 'd03bbb16cf51277c73d7f381b08f9551d0c10415'
MAIN = Path('/Users/songyaozhu/binance-hackathon')
REL = MAIN / '.claude/worktrees/release-d03bbb1'
CA = MAIN / 'deploy/activation/pr174-verification-20261018/verified-bundle/rds-ca.pem'
OUT = Path(os.environ['D1_OUT']) / ('setup-result-' + NEW + '.json')
sys.path.insert(0, str(REL))
import psycopg
from larp.storage.postgres import PostgresStore, digest

assert subprocess.run(['git', '-C', str(REL), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip() == SRC
assert not subprocess.run(['git', '-C', str(REL), 'status', '--porcelain', '--untracked-files=no'],
                          capture_output=True, text=True).stdout.strip(), 'release checkout is dirty'
assert hashlib.sha256(CA.read_bytes()).hexdigest() == 'd73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b'
tf = json.loads((MAIN / 'deploy/activation/tf-output.json').read_text())
val = lambda k: tf[k]['value'] if isinstance(tf[k], dict) and 'value' in tf[k] else tf[k]
arn = val('database_admin_secret_arn')
assert val('database_name') == 'larp'
raw = subprocess.run(['/opt/homebrew/bin/aws', '--profile', 'larp', '--region', 'ap-southeast-2', 'secretsmanager',
                      'get-secret-value', '--secret-id', arn, '--query', 'SecretString', '--output', 'text'],
                     capture_output=True, text=True)
if raw.returncode:
    sys.exit('could not read the admin secret (AWS error withheld)')
cred = json.loads(raw.stdout); del raw
kw = lambda db: dict(host='127.0.0.1', port=15432, dbname=db, user=cred['username'], password=cred['password'],
                     sslmode='verify-ca', sslrootcert=str(CA), connect_timeout=10)
result = {'record_id': 'S5-D1', 'database': NEW, 'source': SRC}
with psycopg.connect(**kw('larp'), autocommit=True) as c:
    c.execute('SET default_transaction_read_only = on')
    result['tls'] = c.execute("SELECT version FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()[0]
    old = dict(c.execute('SELECT name,sha256 FROM schema_migrations ORDER BY name').fetchall())
    result['databases_before'] = sorted(r[0] for r in c.execute(
        "SELECT datname FROM pg_database WHERE datname LIKE 'larp%%'").fetchall())
    exists = NEW in result['databases_before']
result['new_database_preexisted'] = exists
if exists:
    # Refuse anything but an empty, earlier-created copy of this exact schema.
    with psycopg.connect(**kw(NEW), autocommit=True) as c:
        c.execute('SET default_transaction_read_only = on')
        has_runs = c.execute("SELECT to_regclass('public.runs') IS NOT NULL").fetchone()[0]
        if has_runs and c.execute('SELECT count(*) FROM runs').fetchone()[0]:
            sys.exit(NEW + ' already holds a run; refusing')
else:
    with psycopg.connect(**kw('larp'), autocommit=True) as c:
        c.execute('CREATE DATABASE ' + NEW)
dsn = psycopg.conninfo.make_conninfo(**kw(NEW))
PostgresStore(dsn).migrate()
# User-authorized F0d: preload must already be active after planned maintenance.
with psycopg.connect(dsn, autocommit=True) as c:
    c.execute('CREATE EXTENSION IF NOT EXISTS pg_stat_statements')
    result['query_monitoring_rows'] = c.execute('SELECT count(*) FROM pg_stat_statements').fetchone()[0]
roles = (REL / 'deploy/postgres/roles.sql').read_text()
assert roles.count('ON DATABASE larp TO') == 1
roles_new = roles.replace('ON DATABASE larp TO', 'ON DATABASE ' + NEW + ' TO')
result['roles_sql_sha256'] = hashlib.sha256(roles.encode()).hexdigest()
result['roles_sql_new_sha256'] = hashlib.sha256(roles_new.encode()).hexdigest()
with psycopg.connect(dsn) as c:
    c.execute(roles_new)
release = {p.name: digest(p.read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8'))
           for p in sorted((REL / 'migrations').glob('*.sql'))}
with psycopg.connect(dsn, autocommit=True) as c:
    new = dict(c.execute('SELECT name,sha256 FROM schema_migrations ORDER BY name').fetchall())
    result['migrations'] = sorted(new)
    result['migrations_equal_release'] = new == release
    result['migrations_equal_larp'] = new == old
    result['tables'] = c.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone()[0]
    result['runs'] = c.execute('SELECT count(*) FROM runs').fetchone()[0]
    result['service_roles_connect'] = sorted(r[0] for r in c.execute(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('larp_archive','larp_uploader','larp_runtime','larp_execution',"
        "'larp_signer') AND has_database_privilege(rolname,%s,'CONNECT')", (NEW,)).fetchall())
    result['runtime_can_insert_runs'] = c.execute(
        "SELECT has_table_privilege('larp_runtime','runs','INSERT')").fetchone()[0]
    result['runtime_cannot_insert_execution'] = not c.execute(
        "SELECT has_table_privilege('larp_runtime','execution_records','INSERT')").fetchone()[0]
    result['signer_can_connect'] = 'larp_signer' in result['service_roles_connect']
del cred
OUT.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
ok = (result['migrations_equal_release'] and result['runs'] == 0 and len(result['service_roles_connect']) == 5
      and result['runtime_can_insert_runs'] and result['runtime_cannot_insert_execution'])
print('SJ-11-D1', 'PASS' if ok else 'CHECK')
print('D1_DONE' if ok else 'no D1_DONE')
