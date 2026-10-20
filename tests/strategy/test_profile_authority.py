"""IDEA-049-C LD04-P Q1-Q3: #27 finite execution authority in the LIVE profile builder (synthetic plus committed inputs)."""
import hashlib
import json
from pathlib import Path

import pytest

from larp.contracts import ContractError, Document
from larp.strategy.profiles import build_live_profiles, main, validate_live
from larp.strategy.schema import execution_authority
from tests.strategy.live_fixtures import registry, summary

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / 'docs/build/evidence/quotes-complete-20261020'
AUTHORITY = dict(seconds=660, margin=30, decision_id='IDEA-049-C LD04-V01', data_hash='a' * 64)


def committed_inputs():
    return (Document.from_dict(json.loads((CAPTURE / 'quote-cost-summary.json').read_bytes())),
            Document.from_dict(json.loads((ROOT / 'config/intelligence/red_flags.v1.json').read_bytes())))


def test_q1_without_authority_the_committed_candidates_reproduce_byte_for_byte():
    for env, doc in build_live_profiles(*committed_inputs()).items():
        assert doc.payload + b'\n' == (CAPTURE / (env.lower() + '-live.json')).read_bytes()


def test_q2_authority_adds_exactly_two_sourced_keys():
    plain, timed = build_live_profiles(*committed_inputs()), build_live_profiles(*committed_inputs(), authority=AUTHORITY)
    for env in plain:
        a, b = plain[env].read(), timed[env].read()
        added = {'execution_authority_seconds': 660, 'submission_margin_seconds': 30}
        assert {k: v for k, v in b.items() if k != 'provenance'} == {**{k: v for k, v in a.items() if k != 'provenance'}, **added}
        for key in added:
            assert b['provenance'][key] == {'decision_id': 'IDEA-049-C LD04-V01', 'data_hash': 'a' * 64}
        assert {k: v for k, v in b['provenance'].items() if k not in added} == a['provenance']
        assert execution_authority(b) == (660, 30)
        validate_live(b)


@pytest.mark.parametrize('change', [
    dict(seconds=30, margin=30), dict(seconds=3601), dict(seconds=10), dict(seconds='660'), dict(margin=0),
    dict(decision_id=' '), dict(data_hash='xyz'), 'missing'])
def test_q3_builder_refuses_bad_or_partial_authority(change):
    authority = {k: v for k, v in AUTHORITY.items() if k != 'margin'} if change == 'missing' else {**AUTHORITY, **change}
    with pytest.raises(ContractError):
        build_live_profiles(summary(), registry(), authority=authority)


def test_q3_cli_needs_all_four_flags_and_hashes_the_evidence(tmp_path):
    s, r = tmp_path / 's.json', tmp_path / 'r.json'
    s.write_bytes(summary().payload)
    r.write_bytes(registry().payload)
    evidence = tmp_path / 'packet.json'
    evidence.write_bytes(b'{"packet": 1}\n')
    base = ['--summary', str(s), '--predicates', str(r)]
    with pytest.raises(SystemExit):
        main(base + ['--output-dir', str(tmp_path / 'partial'), '--execution-authority-seconds', '660'])
    main(base + ['--output-dir', str(tmp_path / 'out'), '--execution-authority-seconds', '660',
                 '--submission-margin-seconds', '30', '--authority-decision', 'IDEA-049-C LD04-V01',
                 '--authority-evidence', str(evidence)])
    p = json.loads((tmp_path / 'out' / 'final-live.json').read_bytes())
    assert execution_authority(p) == (660, 30)
    assert p['provenance']['execution_authority_seconds']['data_hash'] == hashlib.sha256(evidence.read_bytes()).hexdigest()


def test_authority_composes_with_initial_gas_only_scope():
    plain = build_live_profiles(*committed_inputs(), initial_gas_only=True)
    timed = build_live_profiles(*committed_inputs(), initial_gas_only=True, authority=AUTHORITY)
    for env in plain:
        a, b = plain[env].read(), timed[env].read()
        assert b['initial_gas_only'] is True and not any(k.startswith('gas_top') or k == 'gas_floor_bnb_units' for k in b)
        assert {k: v for k, v in b.items() if k not in ('provenance', 'execution_authority_seconds',
                                                         'submission_margin_seconds')} == {k: v for k, v in a.items() if k != 'provenance'}
        assert execution_authority(b) == (660, 30)
        validate_live(b)
