"""First-party ai-seeds PROTOCOL 2.0 adapter; vendor files remain unchanged."""

import hashlib
import hmac
import json
import re

from larp.contracts import ContractError, Document

SYMBOLS = frozenset(('NVDAB','GOOGLB','SKHYB','TSLAB','MSFTB'))
EVENT_ID = re.compile(r'^[A-Za-z0-9._:-]{1,128}$')
ADDRESS = re.compile(r'^0x[0-9a-fA-F]{40}$')
TX = re.compile(r'^0x[0-9a-fA-F]{64}$')


def compact(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')


def sign(secret,method,path,timestamp,nonce,address,content):
    message = '\n'.join((method,path,str(timestamp),nonce,address.lower(),hashlib.sha256(content).hexdigest()))
    return hmac.new(secret.encode('utf-8'),message.encode('utf-8'),hashlib.sha256).hexdigest()


def _validate(log):
    if type(log['timestamp']) is not int or not 0 <= log['timestamp'] < 2**63:
        raise ContractError('Invalid log timestamp')
    data = log['data']
    for key in ('input','cot','output'):
        value = data.get(key)
        if value is None or value == {} or value == [] or (isinstance(value,str) and not value.strip()):
            raise ContractError('Required audit content is empty')
    if type(data['orders']) is not list:
        raise ContractError('Orders must be a list')
    for order in data['orders']:
        if order['symbol'] not in SYMBOLS or order['side'] not in ('BUY','SELL'):
            raise ContractError('Unsupported audit order')
        if not isinstance(order['amount'],str) or not order['amount'].strip():
            raise ContractError('Amount must be an explicit unit-scaled string')
        if 'tx_hash' in order and not TX.fullmatch(order['tx_hash']):
            raise ContractError('Malformed swap hash')


def chunks(log_bytes,address):
    """At most 128 chunks; also enforce escaped stored-record size.

    Use maximum 64KiB chunks, then split further if JSON escaping is large.
    Metadata has a conservative 2KiB reserve below the 256KiB record ceiling.
    """
    text = log_bytes.decode('utf-8')
    parts,current,size = [],[],0
    for char in text:
        n = len(char.encode('utf-8'))
        if size+n > 65536:
            parts.append(''.join(current)); current=[]; size=0
        current.append(char); size+=n
    if current:
        parts.append(''.join(current))
    refined = []
    while parts:
        part = parts.pop(0)
        if len(compact(part)) > 254*1024:
            middle = len(part)//2
            parts[0:0] = [part[:middle],part[middle:]]
        else:
            refined.append(part)
    if not refined or len(refined)>128 or len(log_bytes)>8*1024*1024:
        raise ContractError('Audit log exceeds protocol budget')
    return [compact(dict(protocolVersion='2.0',address=address,chunkCount=len(refined),
                         totalBytes=len(log_bytes),contentSha256=hashlib.sha256(log_bytes).hexdigest(),
                         encoding='plain',payload=p)).decode('utf-8') for p in refined]


def build_event(*,event_id,round_id,version_id,decision_ids,address,timestamp_ms,
                input_record,rationale,output,orders,swap_mappings=(),secrets=()):
    if not EVENT_ID.fullmatch(event_id) or not ADDRESS.fullmatch(address):
        raise ContractError('Invalid event/address')
    from larp.runtime.release import redact
    log = dict(timestamp=timestamp_ms,data=dict(input=redact(input_record,secrets),cot=redact(rationale,secrets),
               output=redact(output,secrets),orders=orders))
    _validate(log)
    raw = compact(log)
    event = Document.from_dict(dict(schema='AuditEvent.v1',event_id=event_id,round_id=round_id,
        version_id=version_id,decision_ids=list(decision_ids),address=address,timestamp_ms=timestamp_ms,
        log=raw.decode('utf-8'),log_sha256=hashlib.sha256(raw).hexdigest(),chunks=chunks(raw,address),
        swap_mappings=list(swap_mappings)))
    verify_event(event)
    return event


def verify_event(event):
    e = event.read()
    if e['schema'] != 'AuditEvent.v1' or not EVENT_ID.fullmatch(e['event_id']) or not ADDRESS.fullmatch(e['address']):
        raise ContractError('Invalid audit envelope')
    raw = e['log'].encode('utf-8')
    log = json.loads(raw)
    _validate(log)
    if (hashlib.sha256(raw).hexdigest() != e['log_sha256'] or
            chunks(raw,e['address']) != e['chunks'] or log['timestamp'] != e['timestamp_ms']):
        raise ContractError('Audit bytes or chunk boundaries changed')
    hashes = [o['tx_hash'].lower() for o in log['data']['orders'] if 'tx_hash' in o]
    mappings = e['swap_mappings']
    if (len(set(hashes)) != len(hashes) or sorted(hashes) != sorted(m['tx_hash'].lower() for m in mappings)
            or any(m['decision_id'] not in e['decision_ids'] for m in mappings)):
        raise ContractError('Each swap needs unique decision/round ownership')
