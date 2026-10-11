"""IDEA-041 AC-4.2 (GAP-28 follow-up, IDEA-035 A4) and AC-4.3 (restart and replay, A2).

A statement's review attempt is counted only for a result of that statement's own review job. The review job is
the one the runtime planner schedules (`larp.integration.runtime.RuntimePlanner`, reason STATEMENT_REVIEW_DUE);
`build_request` carries its statement IDs as the request's review scope and the result echoes it.
"""

import copy
import unittest

from larp.contracts import Document
from larp.integration.runtime import RuntimePlanner
from larp.intelligence.agent import EMPTY_CONTEXT, build_request, review_scope
from larp.intelligence.gate import accept, state_document
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXSEMI, PROFILE, RUN_ID
from tests.intelligence.test_lifecycle import Harness


class ReviewScope(Harness):
    def request(self, key, state, job):
        records = [self.w.record(key)]
        cursor = self.w.store.read_cursor("sec-edgar", EXSEMI).read()
        health = {"status": cursor["health"]["status"], "last_success_ms": cursor["health"]["last_success_ms"]}
        return build_request(job=job, run_id=RUN_ID, issuer_id=EXSEMI, records=records, cutoff_ms=self.w.clock(),
                             context=state["context"], policy_profile_hash=PROFILE, allowed_tools=list(self.w.config.tools),
                             tool_calls=6, deadline_ms=60000, source_health=health)

    def run_job(self, key, state, job):
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(self.request(key, state, job))
        decision, after = accept(state, result, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual(decision, "ACCEPT")
        return result.read(), after

    def pending(self):
        _, state = self.run_one("RISKS", job="first")
        self.assertEqual({s["status"] for s in state["statements"].values()}, {"PENDING_REVIEW"})
        return state

    def review_job(self, state, n):
        """The job the runtime planner schedules for the due statements (its real job builder)."""
        due = sorted(s["statement_id"] for s in state["statements"].values() if s["status"] == "PENDING_REVIEW")
        payload = {"kind": "REASSESS_ISSUER", "issuer_id": EXSEMI, "reason": "STATEMENT_REVIEW_DUE",
                   "state_version": state["version"], "statement_ids": due}
        return RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3)._job(payload, self.w.clock() + n, 40)

    def advance_past_due(self, state):
        due = max(s["review"]["next_due_ms"] for s in state["statements"].values() if s["review"]["next_due_ms"])
        self.w.clock.now = max(self.w.clock.now, due) + 1
        self.w.ingestor.poll(EXSEMI)

    def test_unrelated_result_after_due_time_is_not_an_attempt(self):
        state = self.pending()
        self.advance_past_due(state)
        result, after = self.run_job("CLEAN", state, {"job_id": "ingest:clean"})
        self.assertIsNone(result["review_scope"])
        self.assertEqual({s["review"]["attempts"] for s in after["statements"].values()}, {0})
        self.assertEqual({s["status"] for s in after["statements"].values()}, {"PENDING_REVIEW"})

    def test_own_review_job_counts_and_exhausts(self):
        state = self.pending()
        for n in range(state["lifecycle"]["max_review_attempts"]):
            self.advance_past_due(state)
            job = self.review_job(state, n)
            self.assertEqual(review_scope(job)["statement_ids"], sorted(state["statements"]))
            result, state = self.run_job("CLEAN", state, job)  # the review job does not reread RISKS
            self.assertEqual(result["review_scope"]["job_id"], job["job_id"])
            self.assertEqual({s["review"]["attempts"] for s in state["statements"].values()}, {n + 1})
        self.assertEqual({s["status"] for s in state["statements"].values()}, {"REVIEW_EXHAUSTED"})

    def test_review_job_for_other_statements_does_not_count(self):
        state = self.pending()
        self.advance_past_due(state)
        job = self.review_job(state, 0)
        job = dict(job, payload=dict(job["payload"], statement_ids=["stmt:someone-else"]))
        _, after = self.run_job("CLEAN", state, job)
        self.assertEqual({s["review"]["attempts"] for s in after["statements"].values()}, {0})

    def test_incomplete_sighting_counts_only_inside_scope(self):
        state = self.pending()
        self.advance_past_due(state)
        # Rereading RISKS with no tool budget is incomplete (prior history unchecked) and so not an acknowledgement.
        for job, attempts in (({"job_id": "ingest:again"}, 0), (self.review_job(state, 0), 1)):
            with self.subTest(job=job["job_id"]):
                request = Document.from_dict(dict(self.request("RISKS", state, job).read(),
                                                  budget={"tool_calls": 0, "deadline_ms": 60000}))
                result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(request)
                self.assertEqual(result.read()["status"], "ASSESSED")
                _, after = accept(state, result, profile_hash=PROFILE, now_ms=self.w.clock())
                self.assertEqual({s["last_seen_ms"] for s in after["statements"].values()}, {self.w.clock()})
                self.assertEqual({s["review"]["attempts"] for s in after["statements"].values()}, {attempts})
                self.assertEqual({s["status"] for s in after["statements"].values()}, {"PENDING_REVIEW"})

    def test_malformed_scope_is_refused_at_both_ends(self):
        state = self.pending()
        bad = Document.from_dict(dict(self.request("CLEAN", state, {"job_id": "j"}).read(),
                                      review={"job_id": "other", "statement_ids": []}))
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(bad).read()
        self.assertEqual((result["status"], result["reasons"]), ("REJECTED_REQUEST", ["REVIEW_SCOPE_MALFORMED"]))
        good, _ = self.run_job("CLEAN", state, self.review_job(state, 0))
        forged = Document.from_dict(dict(good, result_id="res:forged", review_scope={"job_id": "x", "statement_ids": []}))
        decision, after = accept(state, forged, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual(decision, "REJECT_MALFORMED")
        self.assertEqual(after["statements"], state["statements"])


class RestartAndReplay(Harness):
    """AC-4.3: the evidence state survives its canonical document, and replaying accepted results reproduces it."""

    def test_replay_reproduces_state_and_duplicates_change_nothing(self):
        results, state = [], self.state
        for key, job in (("RISKS", "r1"), ("OCCURRED", "r2"), ("CLEAN", "r3")):
            request = self.w.request([key], issuer_id=EXSEMI, job_id=job, context=state["context"])
            result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(request)
            results.append((result, self.w.clock()))
            _, state = accept(state, result, profile_hash=PROFILE, now_ms=self.w.clock())
            self.w.clock.advance(1000)
        restored = Document(state_document(state).payload).read()
        self.assertEqual(restored, state)
        replayed = copy.deepcopy(self.state)
        for result, at in results:
            _, replayed = accept(replayed, result, profile_hash=PROFILE, now_ms=at)
        self.assertEqual(state_document(replayed).payload, state_document(state).payload)
        for result, at in results:
            decision, again = accept(restored, result, profile_hash=PROFILE, now_ms=at)
            self.assertEqual(decision, "DUPLICATE")
            self.assertEqual(again, restored)

    def test_legacy_result_without_scope_keeps_the_v1_rule(self):
        """Results journaled before review scopes existed replay as before (any result after the due time counts)."""
        _, state = self.run_one("RISKS", job="first")
        due = max(s["review"]["next_due_ms"] for s in state["statements"].values())
        self.w.clock.now = due + 1
        self.w.ingestor.poll(EXSEMI)
        request = self.w.request(["CLEAN"], issuer_id=EXSEMI, job_id="legacy", context=state["context"])
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(request).read()
        legacy = Document.from_dict({k: v for k, v in result.items() if k != "review_scope"})
        _, after = accept(state, legacy, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual({s["review"]["attempts"] for s in after["statements"].values()}, {1})


if __name__ == "__main__":
    unittest.main()
