"""IDEA-032 R13/R14: corrections require actual complete reading of every support."""

import copy
import unittest

from larp.intelligence import lifecycle
from larp.intelligence.gate import accept, initial_state
from larp.intelligence.scenarios import EXSEMI, PROFILE, cover
from tests.intelligence.test_lifecycle import Harness, EXTRA
from tests.redteam.test_integration_redteam import P, adverse_state, gate_result


class UnreadCorrection(Harness):
    def test_unread_primary_cannot_clear_adverse_and_restoration_recovers(self):
        _, state = self.run_one('OCCURRED', job='before')
        spec = EXTRA['OCCURRED']
        self.w.source.replace_document(spec['accession'], spec['documents'][0]['name'], cover(
            'Example Semiconductor Corp', '8-K', ['8.01'], ['The company held a routine meeting.']))
        self.w.clock.advance(60000)
        self.w.ingestor.poll(EXSEMI, recheck=frozenset({spec['accession']}))
        latest = self.w.store.records(EXSEMI)[-1].read()
        primary = next(d for d in latest['documents'] if d['role'] == 'PRIMARY')['text_sha256']
        blob = self.w.artifacts.blobs.pop(primary)
        partial, pending = self.run_one('OCCURRED', state=state, job='unread')
        self.assertTrue(any(m.startswith('PRIMARY_UNREADABLE:') for m in partial['missingness']))
        self.assertFalse(partial['coverage']['complete'])
        self.assertIn('IMPAIRMENT', {a['type'] for a in pending['unresolved_adverse']})
        self.w.artifacts.blobs[primary] = blob
        self.w.clock.advance(1000)
        _, recovered = self.run_one('OCCURRED', state=pending, job='restored')
        self.assertNotIn('IMPAIRMENT', {a['type'] for a in recovered['unresolved_adverse']})

    def test_consumer_does_not_trust_contradictory_complete_flag(self):
        st = adverse_state()
        used = [{'record_id': 'r1', 'accession': 'A', 'revision': 1, 'content_hash': 'h1', 'quality': 'OK'}]
        for extra in ({'missingness': ['PRIMARY_UNREADABLE:A']}, {'missingness': ['FILING_INCOMPLETE:A']},
                      {'missingness': ['UNTRUSTED_INSTRUCTIONS_IN_EVIDENCE']}, {'conflicts': ['conflict']},
                      {'novelty': {'prior_not_checked': True}}):
            with self.subTest(extra=extra):
                _, after = accept(st, gate_result('R2', st, 2000, used=used, **extra),
                                  profile_hash=P, now_ms=2000)
                self.assertTrue(after['unresolved_adverse'])
                self.assertEqual(after['records_assessed'], st['records_assessed'])


class StatementCorrections(unittest.TestCase):
    def initial(self):
        st = initial_state('ISS', P)
        records = [{'accession': a, 'record_id': a+'0', 'content_hash': a+'hash0', 'revision': 0, 'quality': 'OK'}
                   for a in ('A', 'B')]
        statements = [dict(statement_id='stmt:shared', event='IMPAIRMENT', novelty='FIRST_SEEN',
                           statement='Synthetic statement', **{k: u[k] for k in ('accession','record_id','content_hash')})
                      for u in records]
        # Preserve PENDING_REVIEW: no historical lookup completed during the first observation.
        _, st = accept(st, gate_result('initial', st, 1000, used=records, event_statements=statements,
                                       coverage={'complete': True, 'prior_history': {'STATEMENTS': False}}),
                       profile_hash=P, now_ms=1000)
        return st

    def correct(self, st, accession, now, **extra):
        used = [dict(accession=accession, record_id=accession+'1', content_hash=accession+'hash1', revision=1,
                     quality='OK')]
        return accept(st, gate_result('r'+str(now), st, now, used=used, **extra),
                      profile_hash=P, now_ms=now)[1]

    def test_all_supports_corrected_in_either_order_stop_review(self):
        for first, second in (('A','B'), ('B','A')):
            with self.subTest(first=first):
                st = self.initial()
                original = copy.deepcopy(st)
                pending = self.correct(st, first, 2000)
                self.assertEqual(st, original)
                self.assertEqual(pending['statements']['stmt:shared']['status'], 'PENDING_REVIEW')
                before = copy.deepcopy(pending)
                after = self.correct(pending, second, 3000)
                self.assertEqual(pending, before)
                self.assertEqual(after['statements']['stmt:shared']['status'], 'CORRECTED')
                self.assertEqual(lifecycle.due_reviews(after['statements'], 10**12), [])

    def test_statement_in_other_filing_does_not_prevent_correction_of_this_support(self):
        st = self.initial()
        other = dict(statement_id='stmt:shared', event='IMPAIRMENT', novelty='ALREADY_SEEN',
                     statement='Synthetic statement', accession='B', record_id='B0', content_hash='Bhash0')
        pending = self.correct(st, 'A', 2000, event_statements=[other])
        after = self.correct(pending, 'B', 3000)
        self.assertEqual(after['statements']['stmt:shared']['status'], 'CORRECTED')

    def test_reobserved_support_invalidates_its_old_correction(self):
        pending = self.correct(self.initial(), 'A', 2000)
        registry = copy.deepcopy(pending['statements'])
        lifecycle.observe(registry, dict(statement_id='stmt:shared', event='IMPAIRMENT', novelty='ALREADY_SEEN',
                          statement='Synthetic statement', accession='A', record_id='A2', content_hash='Ahash2'),
                          result_id='reappeared', now_ms=2500, complete=False, policy=pending['lifecycle'])
        pending = dict(pending, statements=registry)
        after = self.correct(pending, 'B', 3000)
        self.assertNotIn(after['statements']['stmt:shared']['status'], ('CORRECTED', 'WITHDRAWN'))

    def test_newer_unread_revision_invalidates_old_correction_until_reread(self):
        pending = self.correct(self.initial(), 'A', 2000)
        used = [dict(accession='A', record_id='A2', content_hash='Ahash2', revision=2, quality='OK')]
        original = copy.deepcopy(pending)
        _, partial = accept(pending, gate_result('partial', pending, 2500, used=used, complete=False),
                            profile_hash=P, now_ms=2500)
        self.assertEqual(pending, original)
        after = self.correct(partial, 'B', 3000)
        self.assertNotIn(after['statements']['stmt:shared']['status'], ('CORRECTED', 'WITHDRAWN'))
        _, complete = accept(after, gate_result('complete', after, 3500, used=used), profile_hash=P, now_ms=3500)
        self.assertEqual(complete['statements']['stmt:shared']['status'], 'CORRECTED')
