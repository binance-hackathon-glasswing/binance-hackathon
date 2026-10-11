"""Durable attempts/ACKs. Transport failures are separate from database failure."""

from datetime import datetime,timezone
import json
import secrets
import urllib.error
import urllib.request

from larp.audit.protocol import breach_cutoff_ms,sign
from larp.contracts import Document
from larp.storage.postgres import Conflict,doc

BASE_URL = 'https://api.commonservice.io/ai-seeds-event-log'


def deadline_breaches(db,run_id,now_ms):
    """Unacknowledged audit events past their upload deadline, filtered in SQL."""
    return [r[0] for r in db.execute(
        "SELECT DISTINCT a.event_id FROM audit_events a JOIN audit_chunks c USING(run_id,event_id) "
        "WHERE a.run_id=%s AND c.status<>'ACK' AND a.timestamp_ms<%s ORDER BY 1",
        (run_id,breach_cutoff_ms(now_ms)))]


def delivery_status(db,run_id):
    """Delivery proof per audit event (DR-07, IDEA-042 L7).

    An event is DELIVERED only when every chunk its document lists is ACK with the receiver's acknowledgement stored.
    FAILED: a chunk was refused permanently (4xx) or exhausted its attempts; it stays visible. PENDING otherwise.
    `pending_chunks` is a health figure only: an empty outbox never makes an event DELIVERED.
    """
    events={}
    for event_id,raw in db.execute('SELECT event_id,document FROM audit_events WHERE run_id=%s ORDER BY 1',(run_id,)):
        expected=len(Document(bytes(raw)).read()['chunks'])
        rows=db.execute('SELECT status,acknowledgement IS NOT NULL FROM audit_chunks '
                        'WHERE run_id=%s AND event_id=%s',(run_id,event_id)).fetchall()
        statuses=[r[0] for r in rows]
        if any(s in ('PERMANENT','EXHAUSTED') for s in statuses):
            events[event_id]='FAILED'
        elif len(rows)==expected>0 and all(r[0]=='ACK' and r[1] for r in rows):
            events[event_id]='DELIVERED'
        else:
            events[event_id]='PENDING'
    pending=db.execute("SELECT count(*) FROM audit_chunks WHERE run_id=%s AND status='PENDING'",(run_id,)).fetchone()[0]
    return dict(events=events,pending_chunks=pending,
                delivered=sorted(e for e,v in events.items() if v=='DELIVERED'),
                failed=sorted(e for e,v in events.items() if v=='FAILED'))


class HttpReceiver:
    """Explicitly injected uploader-only credential. No environment lookup."""
    def __init__(self,address,secret,*,timeout=15):
        self.address,self._secret,self.timeout = address,secret,timeout

    def deliver(self,event):
        e=event.read()
        path=f"/v1/events/{e['event_id']}/chunks/{e['chunk_index']}"
        body=e['body'].encode('utf-8')
        timestamp=str(int(datetime.now(timezone.utc).timestamp()*1000))
        nonce=secrets.token_hex(16)
        headers={'Content-Type':'application/json','X-AI-Seeds-Timestamp':timestamp,
                 'X-AI-Seeds-Nonce':nonce,'X-AI-Seeds-Signature':sign(
                     self._secret,'PUT',path,timestamp,nonce,self.address,body)}
        request=urllib.request.Request(BASE_URL+path,data=body,headers=headers,method='PUT')
        try:
            with urllib.request.urlopen(request,timeout=self.timeout) as response:
                raw=response.read(16385)
                if len(raw)>16384:
                    return doc(dict(status_code=502,body={}))
                body=json.loads(raw)
                return doc(dict(status_code=response.status,body=body if type(body) is dict else {}))
        except urllib.error.HTTPError as exc:
            return doc(dict(status_code=exc.code,body={}))
        except (OSError,ValueError):
            return doc(dict(status_code=0,body={}))


class DeliveryWorker:
    def __init__(self,store,receiver,*,max_attempts=8,retry_ms=30000):
        if max_attempts<1 or retry_ms<1:
            raise ValueError('Invalid delivery budget')
        self.store,self.receiver=store,receiver
        self.max_attempts,self.retry_ms=max_attempts,retry_ms

    def once(self,run_id,epoch,now_ms):
        # Persist attempt and short lease BEFORE any remote side effect. Lease
        # expiry resends identical bytes. Independent upload worker survives hangs.
        with self.store.transaction() as db:
            run=self.store._run(db,run_id)
            if run['epoch']!=epoch:
                raise Conflict('Stale uploader owner')
            row=db.execute("SELECT event_id,chunk_index,body,attempts FROM audit_chunks WHERE run_id=%s "
                "AND status='PENDING' AND next_ms<=%s ORDER BY event_id,chunk_index FOR UPDATE SKIP LOCKED LIMIT 1",
                (run_id,now_ms)).fetchone()
            if not row:
                return False
            event_id,index,raw,attempts=row
            if attempts>=self.max_attempts:
                db.execute("UPDATE audit_chunks SET status='EXHAUSTED' WHERE run_id=%s AND event_id=%s AND chunk_index=%s",
                           (run_id,event_id,index))
                return True
            attempts+=1
            db.execute('UPDATE audit_chunks SET attempts=%s,next_ms=%s WHERE run_id=%s AND event_id=%s AND chunk_index=%s',
                       (attempts,now_ms+self.retry_ms,run_id,event_id,index))
        try:
            response=self.receiver.deliver(doc(dict(event_id=event_id,chunk_index=index,body=bytes(raw).decode('utf-8'))))
            result=response.read()
        except Exception:
            result=dict(status_code=0,body={})
        code,body=result.get('status_code',0),result.get('body',{})
        if type(body) is not dict:
            body={}
        if type(code) is not int:
            code=0
        ack=code==200 and body.get('status')=='STORED' and body.get('eventId')==event_id and body.get('chunkIndex')==index
        permanent=400<=code<500 and code!=429
        status='ACK' if ack else ('PERMANENT' if permanent else 'PENDING')
        with self.store.transaction() as db:
            if self.store._run(db,run_id)['epoch']!=epoch:
                raise Conflict('Owner changed after send; retry same bytes')
            # An older failed request cannot undo a concurrently acknowledged row, and a
            # non-ACK result only counts while its attempt is still the latest lease.
            # An ACK always counts: the server stored these exact bytes.
            db.execute("UPDATE audit_chunks SET status=%s,last_code=%s,acknowledgement=%s "
                       "WHERE run_id=%s AND event_id=%s AND chunk_index=%s AND status<>'ACK' "
                       "AND (attempts=%s OR %s)",
                       (status,str(code),doc(body).payload if ack else None,run_id,event_id,index,attempts,ack))
        return True

    def status(self,run_id):
        with self.store.transaction() as db:
            return delivery_status(db,run_id)

    def deadline_breaches(self,run_id,now_ms):
        with self.store.transaction() as db:
            return deadline_breaches(db,run_id,now_ms)
