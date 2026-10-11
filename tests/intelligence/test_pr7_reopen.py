"""IDEA-033 R25: a closed correction whose proof is invalidated by a newer, not completely read revision reopens.

wtvlol's PR #7 review at bf6d65e: after complete corrections of supports A and B, a statement is CORRECTED with no
due review. A newer revision A2 observed incompletely removes A's correction proof but left the statement CORRECTED,
so it never got another review job and an unrelated complete assessment could return CLEAR. Resolved adverse latches
had the same gap: invalidation only looked at unresolved latches. Tests marked CONTROL pass on the unfixed code.
"""

import copy
import unittest

from larp.intelligence import lifecycle
from larp.intelligence.gate import accept, initial_state
from tests.redteam.test_integration_redteam import P, adverse_state, gate_result

SID = 'stmt:shared'


def used(accession, revision, record_id=None):
    return [dict(accession=accession, record_id=record_id or f'{accession}{revision}',
                 content_hash=f'{accession}hash{revision}', revision=revision, quality='OK')]


def statement(record, **changes):
    return dict(dict(statement_id=SID, event='IMPAIRMENT', novelty='FIRST_SEEN', statement='Synthetic statement',
                     **{k: record[k] for k in ('accession', 'record_id', 'content_hash')}), **changes)


class ClosedStatementReopens(unittest.TestCase):
    def corrected(self):
        """SID supported by A0 and B0 and corrected by complete reads of A1, then B1."""
        st = initial_state('ISS', P)
        records = used('A', 0) + used('B', 0)
        _, st = accept(st, gate_result('initial', st, 1000, used=records, event_statements=[statement(u) for u in records],
                                       coverage={'complete': True, 'prior_history': {'STATEMENTS': False}}),
                       profile_hash=P, now_ms=1000)
        for now, accession in ((2000, 'A'), (3000, 'B')):
            _, st = accept(st, gate_result(f'r{now}', st, now, used=used(accession, 1)), profile_hash=P, now_ms=now)
        self.assertEqual(st['statements'][SID]['status'], 'CORRECTED')
        self.assertEqual(st['evidence_gate'], 'CLEAR')
        return st

    def test_r25_invalidated_correction_reopens_review_until_complete_reread(self):
        """A1 complete -> B1 complete -> A2 incomplete -> unrelated complete, then recovery by a complete A2 read."""
        st = self.corrected()
        original = copy.deepcopy(st)
        _, partial = accept(st, gate_result('partial', st, 4000, used=used('A', 2), complete=False),
                            profile_hash=P, now_ms=4000)
        self.assertEqual(st, original)  # input state is not mutated
        entry = partial['statements'][SID]
        self.assertEqual(entry['status'], 'PENDING_REVIEW')
        self.assertGreater(entry['review']['next_due_ms'], 4000)
        self.assertEqual([e['statement_id'] for e in lifecycle.due_reviews(partial['statements'], 10**12)], [SID])
        _, unrelated = accept(partial, gate_result('unrelated', partial, 5000, used=used('C', 0)),
                              profile_hash=P, now_ms=5000)
        self.assertNotEqual(unrelated['evidence_gate'], 'CLEAR')
        self.assertIn('PENDING_STATEMENT_REVIEW', unrelated['gate_reasons'])
        _, recovered = accept(unrelated, gate_result('reread', unrelated, 6000, used=used('A', 2)),
                              profile_hash=P, now_ms=6000)
        self.assertEqual(recovered['statements'][SID]['status'], 'CORRECTED')
        self.assertEqual(lifecycle.due_reviews(recovered['statements'], 10**12), [])
        self.assertEqual(recovered['evidence_gate'], 'CLEAR')

    def test_r25_invalidated_withdrawal_reopens_review(self):
        """Same sequence with both supports withdrawn: a newer unread A2 is not proof that A is still withdrawn."""
        st = initial_state('ISS', P)
        records = used('A', 0) + used('B', 0)
        _, st = accept(st, gate_result('initial', st, 1000, used=records, event_statements=[statement(u) for u in records],
                                       coverage={'complete': True, 'prior_history': {'STATEMENTS': False}}),
                       profile_hash=P, now_ms=1000)
        for now, accession in ((2000, 'A'), (3000, 'B')):
            withdrawn = [dict(used(accession, 1)[0], quality='WITHDRAWN')]
            _, st = accept(st, gate_result(f'r{now}', st, now, used=withdrawn), profile_hash=P, now_ms=now)
        self.assertEqual(st['statements'][SID]['status'], 'WITHDRAWN')
        _, partial = accept(st, gate_result('partial', st, 4000, used=used('A', 2), complete=False),
                            profile_hash=P, now_ms=4000)
        self.assertEqual(partial['statements'][SID]['status'], 'PENDING_REVIEW')

    def test_r25_control_complete_reread_keeps_the_correction(self):
        """CONTROL. A complete read of A2 that still lacks the statement keeps it CORRECTED with no due review."""
        st = self.corrected()
        _, after = accept(st, gate_result('reread', st, 4000, used=used('A', 2)), profile_hash=P, now_ms=4000)
        self.assertEqual(after['statements'][SID]['status'], 'CORRECTED')
        self.assertEqual(lifecycle.due_reviews(after['statements'], 10**12), [])

    def test_r25_control_statement_seen_again_is_acknowledged(self):
        """CONTROL. If the incomplete A2 read shows the statement again, it is live and acknowledged, as before."""
        st = self.corrected()
        again = statement(used('A', 2)[0], novelty='ALREADY_SEEN')
        _, after = accept(st, gate_result('again', st, 4000, used=used('A', 2), complete=False,
                                          event_statements=[again]), profile_hash=P, now_ms=4000)
        self.assertEqual(after['statements'][SID]['status'], 'ACKNOWLEDGED')


class ResolvedLatchReopens(unittest.TestCase):
    def resolved(self):
        """adverse_state's IMPAIRMENT latch (A revision 0) resolved by a complete clean read of A1."""
        st = adverse_state()
        _, st = accept(st, gate_result('R2', st, 2000, used=used('A', 1, 'r1')), profile_hash=P, now_ms=2000)
        self.assertEqual(st['unresolved_adverse'], [])
        self.assertEqual([a['finding_id'] for a in st['resolved_adverse']], ['f1'])
        return st

    def test_r25_newer_unread_revision_reopens_a_resolved_latch(self):
        st = self.resolved()
        original = copy.deepcopy(st)
        _, partial = accept(st, gate_result('R3', st, 3000, used=used('A', 2, 'r2'), complete=False),
                            profile_hash=P, now_ms=3000)
        self.assertEqual(st, original)
        self.assertEqual([a['finding_id'] for a in partial['unresolved_adverse']], ['f1'])
        self.assertEqual(partial['resolved_adverse'], [])
        self.assertEqual(partial['unresolved_adverse'][0]['source_resolutions'], {})
        _, unrelated = accept(partial, gate_result('R4', partial, 4000, used=used('C', 0)), profile_hash=P, now_ms=4000)
        self.assertEqual(unrelated['evidence_gate'], 'ADVERSE')
        _, recovered = accept(unrelated, gate_result('R5', unrelated, 5000, used=used('A', 2, 'r2')),
                              profile_hash=P, now_ms=5000)
        self.assertEqual(recovered['unresolved_adverse'], [])
        self.assertEqual([a['finding_id'] for a in recovered['resolved_adverse']], ['f1'])
        self.assertEqual(recovered['evidence_gate'], 'CLEAR')

    def test_r25_control_unrelated_record_leaves_a_resolved_latch_resolved(self):
        """CONTROL. A partial read of another filing says nothing about A's correction."""
        st = self.resolved()
        _, after = accept(st, gate_result('R3', st, 3000, used=used('C', 0), complete=False), profile_hash=P, now_ms=3000)
        self.assertEqual(after['unresolved_adverse'], [])
