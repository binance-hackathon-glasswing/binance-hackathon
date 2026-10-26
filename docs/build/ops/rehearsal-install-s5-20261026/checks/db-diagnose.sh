# Read-only (primary): why the services cannot reach the database. Unit restart history, when the failures began,
# clock sync (IAM tokens need it), instance-role credentials, DNS/TCP to the DB port, and one direct connection attempt
# as larp_execution with the error's class, SQLSTATE and message (database host, IPs and token removed). Changes nothing.
#   python3.12 -I ssm_run.py checks/db-diagnose.sh            (then read results/db-diagnose-stdout.txt)
set -u
echo "== now $(date -u +%FT%TZ)"
for u in larp-runtime larp-execution larp-uploader larp-evidence; do
  echo "$u $(systemctl is-active $u) restarts=$(systemctl show $u -p NRestarts --value)" \
    "since=$(systemctl show $u -p ActiveEnterTimestamp --value)" "last_exit=$(systemctl show $u -p ExecMainStatus --value)"
done
for u in larp-runtime larp-execution larp-uploader; do
  echo "== $u: first and last scheduled restarts since P5"
  journalctl -u $u --since "2026-10-22 14:00:00" --no-pager -o short-iso | grep -E 'Scheduled restart job' | sed -n '1p;$p'
  echo "== $u: fixed JSON lines (first 3 and last 3 since P5)"
  journalctl -u $u --since "2026-10-22 14:00:00" --no-pager -o short-iso | grep -E ' \{' | sed -n '1,3p' | cut -c1-400
  journalctl -u $u --since "2026-10-22 14:00:00" --no-pager -o short-iso | grep -E ' \{' | tail -3 | cut -c1-400
  echo "== $u: exception names seen (count)"
  journalctl -u $u --since "2026-10-22 14:00:00" --no-pager -o cat | grep -oE '^[a-zA-Z_.]+(Error|Exception|Unavailable|Refused|Blocked)\b' | sort | uniq -c | head
done
echo "== clock"
chronyc tracking 2>/dev/null | grep -E 'System time|Leap status' || timedatectl | grep -i synchron
echo "== disk"
df -h / /var 2>/dev/null | tail -n +2
cd /opt/larp/current
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import json, re, socket, time
from pathlib import Path
c = json.loads(Path('/etc/larp/execution.json').read_text())
host = c['database_host']
def clean(s):
    s = s.replace(host, '<db>')
    s = re.sub(r'\b\d{1,3}(\.\d{1,3}){3}\b', '<ip>', s)
    return re.sub(r'(password|token|X-Amz-[A-Za-z]+)=\S+', r'\1=<redacted>', s)[:600]
r = {}
try:
    import boto3
    ident = boto3.client('sts', region_name=c['region']).get_caller_identity()
    r['instance_role'] = ident['Arn'].split('/')[-2] if '/' in ident['Arn'] else 'ok'
except Exception as e:
    r['instance_role'] = 'ERROR ' + type(e).__name__
try:
    addrs = {a[4][0] for a in socket.getaddrinfo(host, 5432, proto=socket.IPPROTO_TCP)}
    r['dns'] = f'ok ({len(addrs)} address)'
except Exception as e:
    r['dns'] = 'ERROR ' + type(e).__name__
t = time.monotonic()
try:
    socket.create_connection((host, 5432), timeout=5).close()
    r['tcp_5432'] = f'ok {time.monotonic() - t:.2f}s'
except Exception as e:
    r['tcp_5432'] = f'ERROR {type(e).__name__} after {time.monotonic() - t:.1f}s'
try:
    import psycopg
    from psycopg.conninfo import make_conninfo
    from larp.runtime.database import rds_client
    token = rds_client(c['region']).generate_db_auth_token(DBHostname=host, Port=5432, DBUsername=c['database_user'],
                                                            Region=c['region'])
    dsn = make_conninfo(host=host, port=5432, user=c['database_user'], password=token, dbname=c['database_name'],
                        sslmode='verify-full', sslrootcert=c['database_ca_file'])
    with psycopg.connect(dsn, connect_timeout=5) as db:
        row = db.execute("SELECT now(), current_user, (SELECT count(*) FROM pg_stat_activity), "
                         "current_setting('max_connections')").fetchone()
    r['db_connect'] = 'ok'
    r['db'] = dict(server_time=str(row[0]), user=row[1], connections=row[2], max_connections=row[3])
except Exception as e:
    r['db_connect'] = 'ERROR ' + type(e).__name__
    r['sqlstate'] = getattr(e, 'sqlstate', None)
    r['message'] = clean(str(e))
print(json.dumps(r, indent=1, sort_keys=True))
PY
echo DIAG_DONE
