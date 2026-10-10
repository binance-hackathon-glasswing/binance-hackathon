"""Durable attempts/ACKs. Transport failures are separate from database failure."""

from datetime import datetime,timezone
import json
import secrets
import urllib.error
import urllib.request

from larp.audit.protocol import sign
from larp.contracts import Document
from larp.storage.postgres import Conflict,doc

BASE_URL = 'https://api.commonservice.io/ai-seeds-event-log'


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
                return doc(dict(status_code=response.status,body=json.loads(raw)))
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
        ack=code==200 and body.get('status')=='STORED' and body.get('eventId')==event_id and body.get('chunkIndex')==index
        permanent=400<=code<500 and code!=429
        status='ACK' if ack else ('PERMANENT' if permanent else 'PENDING')
        with self.store.transaction() as db:
            if self.store._run(db,run_id)['epoch']!=epoch:
                raise Conflict('Owner changed after send; retry same bytes')
            # An older failed request cannot undo a concurrently acknowledged row.
            db.execute("UPDATE audit_chunks SET status=%s,last_code=%s,acknowledgement=%s "
                       "WHERE run_id=%s AND event_id=%s AND chunk_index=%s AND status<>'ACK'",
                       (status,str(code),doc(body).payload if ack else None,run_id,event_id,index))
        return True

    def deadline_breaches(self,run_id,now_ms):
        with self.store.transaction() as db:
            rows=db.execute("SELECT DISTINCT a.event_id,a.document FROM audit_events a JOIN audit_chunks c "
                "USING(run_id,event_id) WHERE a.run_id=%s AND c.status<>'ACK'",(run_id,)).fetchall()
        return [event_id for event_id,raw in rows if now_ms >=
                ((Document(bytes(raw)).read()['timestamp_ms']//86400000+1)*86400000+7200000)]
