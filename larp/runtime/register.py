"""Release register: services list (F-61) and deviations register (GAP-62, G-11). IDEA-042 item 8, DR-18.

Both live in `config/release/` and are hashed into every release manifest (`release_register`). Release preflight
refuses a build whose register is missing, invalid or changed. plan.md §6.5 shows the register as `render` prints it.
"""

import hashlib
import json
from pathlib import Path
import re

from larp.contracts import ContractError

SERVICES = 'config/release/services.v1.json'
DEVIATIONS = 'config/release/deviations.v1.json'
SERVICE_STATUSES = ('ACTIVE', 'PENDING_DECISION', 'PROVISIONING')
ROW_STATUSES = ('DRAFT', 'FINAL')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
EVIDENCE = re.compile(r'^(IDEA|EXP|GAP|[DGIHFQ])-\d{2,3}$')
BEGIN, END = '<!-- deviations:begin (tools/render_deviations.py) -->', '<!-- deviations:end -->'


def _text(value, name):
    if type(value) is not str or not value.strip():
        raise ContractError(f'{name} must be non-empty text')
    return value


def validate_services(doc):
    if type(doc) is not dict or doc.get('schema') != 'ServicesList.v1' or not doc.get('services'):
        raise ContractError('Expected a non-empty ServicesList.v1')
    seen = set()
    for s in doc['services']:
        for key in ('service_id', 'provider', 'purpose', 'scope', 'terms_ref'):
            _text(s.get(key), 'services.' + key)
        if s['service_id'] in seen or s.get('status') not in SERVICE_STATUSES:
            raise ContractError('Duplicate service or unknown status: ' + s['service_id'])
        if s['status'] == 'PENDING_DECISION' and not (s.get('candidates') and s.get('fallback')):
            raise ContractError('A pending service names its candidates and fallback')
        seen.add(s['service_id'])
    return doc


def validate_deviations(doc, proposal_text=None, resolve=None):
    """`proposal_text`: every declared quote must occur in it verbatim. `resolve(id) -> bool`: evidence must exist."""
    if type(doc) is not dict or doc.get('schema') != 'DeviationsRegister.v1' or not doc.get('rows'):
        raise ContractError('Expected a non-empty DeviationsRegister.v1')
    seen = set()
    for row in doc['rows']:
        for key in ('id', 'area', 'declared', 'v1_behaviour', 'reason'):
            _text(row.get(key), 'deviations.' + key)
        if row['id'] in seen or row.get('status') not in ROW_STATUSES:
            raise ContractError('Duplicate row or unknown status: ' + row['id'])
        if row.get('decided') != 'OPEN' and not DATE.fullmatch(str(row.get('decided'))):
            raise ContractError('Decided must be a date or OPEN: ' + row['id'])
        if row['status'] == 'FINAL' and row['decided'] == 'OPEN':
            raise ContractError('An OPEN row cannot be FINAL: ' + row['id'])
        evidence = row.get('evidence')
        if not evidence or any(type(e) is not str or not EVIDENCE.fullmatch(e) for e in evidence):
            raise ContractError('Evidence IDs required: ' + row['id'])
        if proposal_text is not None and row['declared'] not in proposal_text:
            raise ContractError('Declared text is not a verbatim quote of the proposal: ' + row['id'])
        if resolve is not None and not all(resolve(e) for e in evidence):
            raise ContractError('Unknown evidence ID in ' + row['id'])
        seen.add(row['id'])
    return doc


def resolver(root):
    """True if an ID is defined in the repository: a ledger file, a backlog item, or a SKILL.md/plan.md item."""
    root = Path(root)
    texts = {name: (root / name).read_text(encoding='utf-8') for name in
             ('docs/INCOMPLETE_WORK.md', 'docs/skill/SKILL.md', 'docs/skill/larp/plan.md')}

    def resolve(identity):
        if identity.startswith(('IDEA-', 'EXP-')):
            return (root / 'docs/ledger' / (identity + '.md')).is_file()
        if identity.startswith('GAP-'):
            return re.search(rf'^- \[ \] {identity} —', texts['docs/INCOMPLETE_WORK.md'], re.M) is not None
        pattern = rf'^\s*(?:- |\d+\. )(?:\*\*)?{re.escape(identity)}\b'
        return any(re.search(pattern, texts[n], re.M) for n in ('docs/skill/SKILL.md', 'docs/skill/larp/plan.md'))
    return resolve


def _load(root, name):
    path = Path(root) / name
    if not path.is_file():
        raise ContractError('Release register file missing: ' + name)
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def load_register(root):
    """Validate the register in `root` and return the manifest block (file hashes and row counts)."""
    services, services_sha = _load(root, SERVICES)
    deviations, deviations_sha = _load(root, DEVIATIONS)
    validate_services(services)
    proposal = Path(root) / deviations.get('proposal', '')
    validate_deviations(deviations, proposal.read_text(encoding='utf-8') if proposal.is_file() else None)
    return dict(schema='ReleaseRegister.v1', services_sha256=services_sha, deviations_sha256=deviations_sha,
                services=len(services['services']), deviations=len(deviations['rows']),
                open_deviations=sorted(r['id'] for r in deviations['rows'] if r['decided'] == 'OPEN'))


def render(doc):
    """plan.md §6.5 table (one source: the JSON register)."""
    cell = lambda text: text.replace('|', '\\|').replace('\n', ' ')
    lines = [BEGIN, '', '| ID | Area | Declared (proposal) | v1.0 | Reason | Evidence | Decided | Status |',
             '|---|---|---|---|---|---|---|---|']
    for r in doc['rows']:
        lines.append(f"| {r['id']} | {cell(r['area'])} | \"{cell(r['declared'])}\" | {cell(r['v1_behaviour'])} | "
                     f"{cell(r['reason'])} | {', '.join(r['evidence'])} | {r['decided']} | {r['status']} |")
    return '\n'.join(lines + ['', END])
