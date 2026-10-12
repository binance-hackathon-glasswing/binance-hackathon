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
# A gas top-up is its own round with exactly one USDT -> BNB buy (interface I7, IDEA-035 B11). Every other round
# trades only the five bStocks. The kind travels in the event envelope only when it is not a trade round, so
# existing events keep their exact bytes.
ROUND_KINDS = ('TRADE','GAS_TOP_UP')


def compact(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')


def sign(secret,method,path,timestamp,nonce,address,content):
    message = '\n'.join((method,path,str(timestamp),nonce,address.lower(),hashlib.sha256(content).hexdigest()))
    return hmac.new(secret.encode('utf-8'),message.encode('utf-8'),hashlib.sha256).hexdigest()


def _validate(log,round_kind='TRADE'):
    if type(log['timestamp']) is not int or not 0 <= log['timestamp'] < 2**63:
        raise ContractError('Invalid log timestamp')
    data = log['data']
    for key in ('input','cot','output'):
        value = data.get(key)
        if value is None or value == {} or value == [] or (isinstance(value,str) and not value.strip()):
            raise ContractError('Required audit content is empty')
    check_orders(data['orders'],round_kind)


DAY_MS = 86400000
UPLOAD_GRACE_MS = 7200000


def breach_cutoff_ms(now_ms):
    """An event is past its upload deadline (next UTC midnight + 2 h after its
    timestamp) exactly when its timestamp_ms is below this value."""
    return (now_ms - UPLOAD_GRACE_MS) // DAY_MS * DAY_MS


def event_id_for(run_id,address,round_id,head,timestamp_ms):
    """Kit SDK format evt-<ms>-<12 hex>; the server de-duplicates by event ID.

    The hash scopes the ID to this run, wallet, round and journal position, so a
    re-initialised run reusing round IDs cannot collide. It is deterministic, so a
    resend or replay of the same close reproduces the same ID.
    """
    if type(timestamp_ms) is not int or timestamp_ms < 0:
        raise ContractError('Invalid event timestamp')
    if any(type(part) is not str for part in (run_id,address,round_id,head)):
        raise ContractError('Invalid event scope')
    scope = hashlib.sha256('\x00'.join((run_id,address.lower(),round_id,head)).encode('utf-8')).hexdigest()
    return f'evt-{timestamp_ms}-{scope[:12]}'


def check_orders(orders,round_kind='TRADE'):
    """Orders the code decided to place, in the form the audit log accepts.

    BNB is accepted only in a GAS_TOP_UP round, and then only as its single BUY (I7)."""
    if type(orders) is not list:
        raise ContractError('Orders must be a list')
    if round_kind not in ROUND_KINDS:
        raise ContractError('Unknown round kind')
    if round_kind=='GAS_TOP_UP' and [(o.get('symbol'),o.get('side')) if type(o) is dict else None
                                    for o in orders]!=[('BNB','BUY')]:
        raise ContractError('A gas top-up round logs exactly one BNB buy')
    for order in orders:
        if type(order) is not dict:
            raise ContractError('Unsupported audit order')
        allowed = {'BNB'} if round_kind=='GAS_TOP_UP' else SYMBOLS
        if order.get('symbol') not in allowed or order.get('side') not in ('BUY','SELL'):
            raise ContractError('Unsupported audit order')
        if not isinstance(order.get('amount'),str) or not order['amount'].strip():
            raise ContractError('Amount must be an explicit unit-scaled string')
        if order.get('tx_hash') is not None and (
                type(order['tx_hash']) is not str or not TX.fullmatch(order['tx_hash'])):
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
                input_record,rationale,output,orders,swap_mappings=(),secrets=(),round_kind='TRADE'):
    if not EVENT_ID.fullmatch(event_id) or not ADDRESS.fullmatch(address):
        raise ContractError('Invalid event/address')
    from larp.runtime.release import redact
    log = dict(timestamp=timestamp_ms,data=dict(input=redact(input_record,secrets),cot=redact(rationale,secrets),
               output=redact(output,secrets),orders=orders))
    _validate(log,round_kind)
    raw = compact(log)
    envelope = dict(schema='AuditEvent.v1',event_id=event_id,round_id=round_id,
        version_id=version_id,decision_ids=list(decision_ids),address=address,timestamp_ms=timestamp_ms,
        log=raw.decode('utf-8'),log_sha256=hashlib.sha256(raw).hexdigest(),chunks=chunks(raw,address),
        swap_mappings=list(swap_mappings))
    if round_kind != 'TRADE':
        envelope['round_kind'] = round_kind
    event = Document.from_dict(envelope)
    verify_event(event)
    return event


def verify_event(event):
    e = event.read()
    if e['schema'] != 'AuditEvent.v1' or not EVENT_ID.fullmatch(e['event_id']) or not ADDRESS.fullmatch(e['address']):
        raise ContractError('Invalid audit envelope')
    raw = e['log'].encode('utf-8')
    log = json.loads(raw)
    if 'round_kind' in e and e['round_kind'] == 'TRADE':
        raise ContractError('Trade rounds carry no round kind')  # one byte form per event
    _validate(log,e.get('round_kind','TRADE'))
    if (hashlib.sha256(raw).hexdigest() != e['log_sha256'] or
            chunks(raw,e['address']) != e['chunks'] or log['timestamp'] != e['timestamp_ms']):
        raise ContractError('Audit bytes or chunk boundaries changed')
    hashes = [o['tx_hash'].lower() for o in log['data']['orders'] if o.get('tx_hash') is not None]
    mappings = e['swap_mappings']
    if (len(set(hashes)) != len(hashes) or sorted(hashes) != sorted(m['tx_hash'].lower() for m in mappings)
            or any(m['decision_id'] not in e['decision_ids'] or m.get('step')!='swap' for m in mappings)):
        raise ContractError('Each swap needs unique decision/round ownership')
