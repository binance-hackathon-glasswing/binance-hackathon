"""A-REQ-078 release obligation: explicit cross-owner negative proof, not default discovery.

Current implementation absence is recorded by DEV-20; a draft OPEN entry cannot waive a
binding declaration. Team/D/B own implementation or an approved reasoned deviation.
"""
from pathlib import Path
import json
from larp.runtime.register import load_register

root = Path(__file__).resolve().parents[3]
load_register(root)  # validate original files; the return value is manifest metadata, not rows
deviations = json.loads((root / 'config/release/deviations.v1.json').read_text())
row = next(r for r in deviations['rows'] if r['id'] == 'DEV-20')
print({'declaration': row['declared'], 'current_behaviour': row['v1_behaviour'],
       'status': row['status'], 'decided': row['decided']})
assert row['status'] == 'FINAL' and row['decided'] != 'OPEN', 'Unimplemented declared calendar needs an approved deviation or implementation'
