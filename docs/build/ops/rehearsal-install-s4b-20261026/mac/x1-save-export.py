"""X1 (Mac, Yao; IDEA-097 S4): save run 5's exported book from results/x1-export-holdings-stdout.txt to
private/holdings-carry-over.json (0600, new file only) for M4. Prints its SHA-256 and the held units (public values).

  /opt/homebrew/bin/python3.12 -I mac/x1-save-export.py
"""
from pathlib import Path
import hashlib, json, os
here = Path(__file__).resolve().parents[1]
lines = (here / 'results/x1-export-holdings-stdout.txt').read_text().splitlines()
if lines[-1:] != ['X1_DONE'] or sum(line.startswith('CARRY_OVER ') for line in lines) != 1:
    raise SystemExit('X1 refused: the export did not finish with exactly one CARRY_OVER line')
raw = next(line for line in lines if line.startswith('CARRY_OVER ')).split(' ', 1)[1].encode() + b'\n'
value = json.loads(raw)
if (value.get('schema') != 'HoldingsCarryOver.v1' or value.get('source_run_id') != 'larp-dev-rehearsal-20261025-s4'
        or value.get('reservations') != {}):
    raise SystemExit('X1 refused: not run 5, or reservations in flight')
target = here / 'private/holdings-carry-over.json'
target.parent.mkdir(mode=0o700, exist_ok=True)
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'wb') as f:
    f.write(raw)
print(json.dumps(dict(sha256=hashlib.sha256(raw).hexdigest(), source_version=value['source_version'],
                      held={s: p['units'] for s, p in value['positions'].items() if p['units']},
                      cost_basis_units={s: p['cost_basis_units'] for s, p in value['positions'].items() if p['units']})))
