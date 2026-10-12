"""Services list, deviations register, manifest and version event (DR-18; IDEA-042 item 8, criteria R1-R5)."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from larp.contracts import ContractError, Document
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy, settle
from larp.runtime.preflight import release_files, verify_release
from larp.runtime.register import (DEVIATIONS, SERVICES, load_register, render, resolver, validate_deviations,
                                   validate_services)
from larp.runtime.replay import replay
from larp.runtime.supervision import Sessions
from larp.storage.postgres import doc
from tests.support import DatabaseCase, request

ROOT = Path(__file__).resolve().parents[2]
NOW = 1791590400000


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


PROPOSAL = (ROOT / 'docs/proposal/proposal_answers.md').read_text(encoding='utf-8')


class Register(unittest.TestCase):
    def test_r1_services_list(self):
        services = validate_services(load(SERVICES))
        pending = [s for s in services['services'] if s['status'] == 'PENDING_DECISION']
        self.assertEqual([s['service_id'] for s in pending], ['assessor-model'])  # B8 open, with its fallback
        broken = copy.deepcopy(services)
        del broken['services'][0]['terms_ref']
        with self.assertRaises(ContractError):
            validate_services(broken)
        broken = copy.deepcopy(services)
        del broken['services'][4]['fallback']
        with self.assertRaises(ContractError):
            validate_services(broken)

    def test_r2_rows_quote_the_proposal_and_cite_existing_evidence(self):
        register = validate_deviations(load(DEVIATIONS), PROPOSAL, resolver(ROOT))
        cited = {e for row in register['rows'] for e in row['evidence']}
        # Every decision source named in criterion R2 has at least one row.
        self.assertTrue({'IDEA-035', 'IDEA-037', 'D-08', 'D-09', 'D-11', 'GAP-51'} <= cited)
        for change, error in ((lambda r: r['rows'][0].update(declared='a decision model we never proposed'), 'quote'),
                              (lambda r: r['rows'][0]['evidence'].append('IDEA-999'), 'evidence'),
                              (lambda r: next(x for x in r['rows'] if x['decided'] == 'OPEN').update(status='FINAL'), 'open row final')):
            broken = copy.deepcopy(register)
            change(broken)
            with self.subTest(error), self.assertRaises(ContractError):
                validate_deviations(broken, PROPOSAL, resolver(ROOT))

    def test_r3_plan_shows_the_register(self):
        import tools.render_deviations as tool
        self.assertEqual(tool.main(['--check']), 0)
        self.assertIn(render(load(DEVIATIONS)), (ROOT / 'docs/skill/larp/plan.md').read_text(encoding='utf-8'))

    def test_r4_preflight_refuses_a_missing_or_changed_register(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('larp/runtime/operations.py', SERVICES, DEVIATIONS, 'docs/proposal/proposal_answers.md'):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes((ROOT / name).read_bytes())
            files = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in release_files(root)}
            evidence = dict(schema='RegistrationEvidence.v1', evidence_ref='synthetic-only', build_id='a' * 40,
                            repository='synthetic')
            manifest = dict(schema='ReleaseManifest.v1', build_id='a' * 40, repository='synthetic', remote_verified=True,
                            services=['synthetic'], files=files, registration_evidence=evidence,
                            release_register=load_register(root))
            verify_release(Document.from_dict(manifest), root)
            with self.assertRaises(ContractError):  # no register block in the manifest
                verify_release(Document.from_dict({k: v for k, v in manifest.items() if k != 'release_register'}), root)
            changed = load(DEVIATIONS)
            changed['rows'][0]['reason'] += ' (edited after the build)'
            (root / DEVIATIONS).write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaises(ContractError):
                verify_release(Document.from_dict(manifest), root)
            (root / SERVICES).unlink()
            with self.assertRaises(ContractError):
                verify_release(Document.from_dict(manifest), root)

    def test_v2_a_register_without_its_proposal_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (SERVICES, DEVIATIONS):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes((ROOT / name).read_bytes())
            with self.assertRaises(ContractError):  # the quote check cannot run, so nothing passes (IDEA-042 V2)
                load_register(root)
            changed = load(DEVIATIONS)
            changed.pop('proposal')
            (root / DEVIATIONS).write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaises(ContractError):
                load_register(root)


def manifest(build='synthetic'):
    return Document.from_dict(dict(schema='ReleaseManifest.v1', build_id=build, repository='synthetic',
                                   release_register=load_register(ROOT), files={}, services=['synthetic']))


class VersionEvent(DatabaseCase):
    def coordinator(self, require=True):
        return Coordinator(self.store, FakeAssessor(), FakePolicy(), FakePlanner(), execution=FakeExecution(),
                           run_id='run', version_id='synthetic', profile_hash='a' * 64, address='0x' + '1' * 40,
                           clock_ms=lambda: NOW, require_version=require)

    def commands(self):
        with self.store.transaction() as db:
            return db.execute("SELECT count(*) FROM commands WHERE run_id='run'").fetchone()[0]

    def test_r5_no_command_before_the_version_event(self):
        c = self.coordinator()
        c.start('r1', request('BUY', job='j1'), NOW)
        self.assertEqual(self.commands(), 0)
        with self.assertRaises(ContractError):
            c.register_version(manifest('another-build'), NOW)
        c.register_version(manifest(), NOW)
        version = self.store.load('run').read()['projection']['registered_version']
        self.assertEqual((version['build_id'], version['deviations_sha256']),
                         ('synthetic', load_register(ROOT)['deviations_sha256']))
        c.start('r2', request('BUY', job='j2'), NOW)
        self.assertEqual(self.commands(), 1)
        with self.assertRaises(ContractError):  # the process may not run another build than the registered one
            Sessions(self.store, 'run').begin(session_id='s1', build_id='another-build', now_ms=NOW)

    def test_r5_version_event_replays(self):
        c = self.coordinator()
        c.register_version(manifest(), NOW)
        c.start('r1', request('BUY'), NOW)
        tx = '0x' + 'b' * 64
        c.observe('b', doc(dict(kind='BROADCAST_ATTEMPTED', observation_id='b', round_id='r1', tx_hash=tx,
                                simulated=True)), settle)
        c.observe('f', doc(dict(kind='FINAL_SUCCESS', observation_id='f', round_id='r1', tx_hash=tx,
                                simulated=True)), settle)
        c.recover(NOW + 1)
        expected, journal = self.store.verify('run'), self.store.journal('run')
        self.assertEqual(journal[0].read()['event']['kind'], 'VERSION_REGISTERED')
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        head = replay(journal, doc(dict(balances=dict(USDT=100, BNB=10, NVDAB=0))), self.store, run_id='run',
                      wallet_id='wallet', chain_id=56, version_id='synthetic', profile_hash='a' * 64,
                      address='0x' + '1' * 40, policy=FakePolicy(), planner=FakePlanner(), execution=FakeExecution(),
                      reducer=settle, require_version=True)
        self.assertEqual(head, expected)
