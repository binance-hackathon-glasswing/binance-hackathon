"""Independent bounded lanes; expired policy work never becomes a late trade."""

from datetime import datetime,timezone
from importlib.resources import files
from zoneinfo import ZoneInfo

from larp.contracts import ContractError,Document
from larp.storage.postgres import Conflict,doc,integer

LANES=('safety','reconcile','audit','evidence','policy')


def validate_job(job):
    for key in ('job_id','calendar_id','tzdata_version'):
        if not isinstance(job.get(key),str) or not job[key]:
            raise ContractError('Job provenance missing')
    if job['lane'] not in LANES or job['missed'] not in ('catch_up','expire'):
        raise ContractError('Invalid job lane/disposition')
    for key in ('due_ms','valid_until_ms','max_attempts'):
        integer(job[key])
    integer(job.get('priority',100))
    if job['max_attempts']<1 or job['valid_until_ms']<=job['due_ms']:
        raise ContractError('Invalid job budget/time')
    if job['lane']=='policy' and job['missed']!='expire':
        raise ContractError('Policy jobs cannot blindly catch up')


def utc_ms(local,zone,*,fold=0):
    """Resolve explicit fold; reject nonexistent civil times via round trip."""
    if local.tzinfo is not None:
        raise ContractError('Expected naive local calendar input')
    # Load the pinned wheel directly, without mutating process-global TZPATH or
    # consulting a cache that may contain host-system timezone rules.
    if not zone or any(part in ('','.','..') for part in zone.split('/')):
        raise ContractError('Invalid timezone name')
    with files('tzdata.zoneinfo').joinpath(*zone.split('/')).open('rb') as stream:
        tz=ZoneInfo.from_file(stream,key=zone)
    aware=local.replace(tzinfo=tz,fold=fold)
    utc=aware.astimezone(timezone.utc)
    if utc.astimezone(tz).replace(tzinfo=None)!=local:
        raise ContractError('Nonexistent local calendar time')
    return int(utc.timestamp()*1000)


class Scheduler:
    def __init__(self,store,*,lease_ms=1000):
        if lease_ms<1:
            raise ValueError('Invalid lease')
        self.store,self.lease_ms=store,lease_ms

    def claim(self,run_id,epoch,lane,now_ms):
        if lane not in LANES:
            raise ContractError('Unknown lane')
        with self.store.transaction() as db:
            run=self.store._run(db,run_id)
            self.store._owned(run,epoch)
            # Backward UTC never grants more budget or revives an expired job.
            if now_ms<run['clock_ms']:
                raise Conflict('Clock moved backward; synchronization required')
            db.execute('UPDATE runs SET clock_ms=%s WHERE run_id=%s',(now_ms,run_id))
            rows=db.execute("SELECT job_id,document,attempts FROM jobs WHERE run_id=%s AND lane=%s "
                "AND ((status='PENDING' AND next_ms<=%s) OR (status='RUNNING' AND lease_until_ms<=%s)) "
                'ORDER BY priority,next_ms,job_id FOR UPDATE SKIP LOCKED',(run_id,lane,now_ms,now_ms)).fetchall()
            for job_id,raw,attempts in rows:
                job=Document(bytes(raw)).read()
                if attempts>=job['max_attempts'] or (job['missed']=='expire' and now_ms>=job['valid_until_ms']):
                    status='EXHAUSTED' if attempts>=job['max_attempts'] else 'EXPIRED'
                    db.execute('UPDATE jobs SET status=%s WHERE run_id=%s AND job_id=%s',(status,run_id,job_id))
                    continue
                db.execute("UPDATE jobs SET status='RUNNING',attempts=attempts+1,lease_until_ms=%s,claimed_epoch=%s "
                           'WHERE run_id=%s AND job_id=%s',(now_ms+self.lease_ms,epoch,run_id,job_id))
                return doc(dict(job=job,attempt=attempts+1,epoch=epoch))
            return None

    def finish(self,run_id,claim,*,retry_at_ms=None):
        c=claim.read(); job=c['job']
        with self.store.transaction() as db:
            self.store._owned(self.store._run(db,run_id),c['epoch'])
            status='DONE' if retry_at_ms is None else 'PENDING'
            if retry_at_ms is not None:
                integer(retry_at_ms)
            result=db.execute('UPDATE jobs SET status=%s,next_ms=%s WHERE run_id=%s AND job_id=%s '
                "AND status='RUNNING' AND attempts=%s AND claimed_epoch=%s",
                (status,retry_at_ms if retry_at_ms is not None else job['due_ms'],run_id,job['job_id'],c['attempt'],c['epoch']))
            if result.rowcount!=1:
                raise Conflict('Stale job completion')
