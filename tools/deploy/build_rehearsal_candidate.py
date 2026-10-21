"""LD10-Q01/LD11-RH01: offline scoped rehearsal profile, no ports or installation."""
import argparse
import hashlib
import json
from pathlib import Path

from larp.contracts import Document
from larp.strategy.profiles import build_live_profiles, validate_live

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence'


def build():
    def document(path):
        return Document.from_dict(json.loads(path.read_bytes()))
    authority = dict(seconds=660, margin=30, decision_id='IDEA-049-C LD04-V01 (Keegan, 2026-10-20)',
        data_hash=hashlib.sha256((EVIDENCE / 'ld02-execution-packet-20261020.json').read_bytes()).hexdigest())
    budget = dict(action_units=384000000000000, sizing_units=80004608000000,
        decision_id='IDEA-049-C LD10-Q01 (Keegan delegation, 2026-10-21)',
        data_hash=hashlib.sha256((EVIDENCE / 'signer-numeric-ceilings-20261021.json').read_bytes()).hexdigest())
    p = build_live_profiles(document(EVIDENCE / 'quotes-complete-20261020/quote-cost-summary.json'),
        document(ROOT / 'config/intelligence/red_flags.v1.json'), initial_gas_only=True,
        authority=authority, gas_budget=budget)['REHEARSAL'].read()
    p['provenance']['gas_action_budget_units']['formula'] = '2*1200000 max signed child gas*160000000 max gas price; cleanup disabled'
    p['provenance']['gas_sizing_budget_units']['formula'] = 'ceil(1000057*5/4) independently rounded child allowance at 64000000 expected gas price'
    p['evidence_mode'] = 'SHADOW'
    p['provenance']['evidence_mode'] = dict(decision_id='IDEA-083 LD11-RH01 (Keegan, 2026-10-21)',
        formula='Scoped EQUAL_WEIGHT rehearsal; deterministic assessor, hosted models and discretionary model exits deferred')
    validate_live(p)
    return Document.from_dict(p)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = build()
    with args.output.open('xb') as stream:
        stream.write(p.payload + b'\n')
    print(p.digest('StrategyProfile.v1'))


if __name__ == '__main__':
    main()
