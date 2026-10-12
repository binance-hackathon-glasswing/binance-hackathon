"""IDEA-041 AC-3.1..3.3, AC-4.1, AC-4.4: red-flag predicate records, verification fixtures and authority (B1, I8).

Each fixture filing runs through the real ingestion, assessor (rule model), verifier, evidence state and
EvidenceContext; only the filing source is a fake. Expected outcomes are frozen in
tests/intelligence/fixtures/red_flag_fixtures.v1.json (written before this test ran).
"""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from larp.integration.contract import (
    AuthorityError, authority, build_evidence_context, problem, red_flag_directives, red_flag_predicates,
)
from larp.intelligence.agent import context_hash
from larp.intelligence.common import IntelligenceError
from larp.intelligence.gate import accept, consume, initial_state, lifecycle_policy_from
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.redflags import CONFIG, load_predicates
from larp.intelligence.scenarios import EXSEMI, PROFILE, RUN_ID, build_world, doc, p, page, prior_thesis

FIXTURES = json.loads((Path(__file__).resolve().parent / "fixtures" / "red_flag_fixtures.v1.json").read_text("utf-8"))
BY_ID = {f["fixture_id"]: f for f in FIXTURES["fixtures"]}
PREDICATES, SET_SHA = load_predicates()


def spec(fixture: dict) -> dict:
    filing = fixture["filing"]
    content = page(*[p(x) for x in filing["paragraphs"]])
    return dict(cik=filing["cik"], accession=filing["accession"], form=filing["form"], items=list(filing["items"]),
                acceptance=filing["acceptance"],
                documents=[doc(f"exsm-{filing['accession'][-6:]}.htm", filing["form"], content)])


def enabled_profile(*ids) -> dict:
    return {"evidence_mode": "SHADOW",
            "red_flag_authority": {"set_sha256": SET_SHA, "enabled": list(ids or sorted(
                pid for pid, r in PREDICATES.items() if r["class"] in (1, 2)))}}


class Run:
    """One world holding the given fixtures; assess and accept them in order into one evidence state."""

    def __init__(self, *fixture_ids):
        self.extra = {fid: spec(BY_ID[fid]) for fid in fixture_ids}
        self.w = build_world(list(fixture_ids), extra_filings=self.extra)
        context = prior_thesis(self.w.config, EXSEMI)
        self.state = dict(initial_state(EXSEMI, PROFILE, lifecycle_policy=lifecycle_policy_from(self.w.config)),
                          context=context, context_hash=context_hash(context))
        self.n = 0

    def assess(self, key):
        self.n += 1
        request = self.w.request([key], issuer_id=EXSEMI, job_id=f"rf-{self.n}", context=self.state["context"])
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(request)
        decision, self.state = accept(self.state, result, profile_hash=PROFILE, now_ms=self.w.clock())
        assert decision == "ACCEPT", (decision, result.read()["status"])
        return result.read()

    def context(self):
        return build_evidence_context(consume(self.state, self.w.clock()), self.state, run_id=RUN_ID, token="EXSEMIB",
                                      underlying_id=EXSEMI, policy_profile_hash=PROFILE)


class PredicateRecords(unittest.TestCase):
    def test_records_cover_the_adopted_classes_with_every_required_field(self):
        classes = {pid: r["class"] for pid, r in PREDICATES.items()}
        self.assertEqual(classes, {"RF1-ITEM-4.02": 1, "RF2-ITEM-1.05": 2, "RF2-ITEM-2.06": 2, "RF3-STATEMENTS": 3})
        self.assertEqual({r["directive"]["kind"] for r in PREDICATES.values() if r["class"] == 2}, {"BLOCK_NEW_BUYS"})
        self.assertEqual({r["directive"]["block_sessions"] for r in PREDICATES.values() if r["class"] == 2}, {5})
        self.assertEqual(PREDICATES["RF1-ITEM-4.02"]["directive"]["kind"], "EXIT")
        self.assertEqual(PREDICATES["RF3-STATEMENTS"]["directive"]["kind"], "SHADOW")

    def test_malformed_sets_are_refused(self):
        raw = json.loads(CONFIG.read_text("utf-8"))
        for mutate in (lambda d: d["predicates"][0].pop("resolution"),
                       lambda d: d["predicates"][1]["directive"].update(kind="EXIT"),
                       lambda d: d["predicates"][1]["directive"].update(block_sessions=0),
                       lambda d: d["predicates"][2]["trigger"].update(item="1.05"),
                       lambda d: d.update(schema="Other")):
            bad = copy.deepcopy(raw)
            mutate(bad)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "set.json"
                path.write_text(json.dumps(bad), "utf-8")
                with self.subTest(mutation=mutate), self.assertRaises(IntelligenceError):
                    load_predicates(path)


class Fixtures(unittest.TestCase):
    def test_each_fixture_maps_exactly_as_frozen(self):
        """AC-3.3: supported/amended -> one directive of the predicate's kind; every other case -> none."""
        authorizing = []
        for fixture in FIXTURES["fixtures"]:
            with self.subTest(fixture=fixture["fixture_id"]):
                run = Run(fixture["fixture_id"])
                result = run.assess(fixture["fixture_id"])
                item = PREDICATES[fixture["predicate_id"]]["trigger"]["item"]
                checks = [c for c in result["red_flag_checks"] if c["item"] == item]
                self.assertEqual(len(checks), 1)
                self.assertEqual((checks[0]["verified"], checks[0]["reason"]),
                                 (fixture["expect"]["verified"], fixture["expect"]["reason"]))
                falsifier = next(f for f in result["falsifiers"] if f["falsifier_id"] == f"F-ITEM-{item}")
                self.assertEqual(falsifier["state"] == "FIRED", fixture["expect"]["verified"])
                record = run.context()
                self.assertIsNone(problem(record))
                directives = red_flag_directives(record, enabled_profile())
                # Default authority: nothing acts, whatever the evidence says.
                self.assertEqual(red_flag_directives(record, {"evidence_mode": "SHADOW"}), [])
                if fixture["expect"]["directive"] is None:
                    self.assertEqual(directives, [])
                    self.assertFalse([f for f in record["falsifier_findings"] if f.get("red_flag")])
                    if directives:
                        authorizing.append(fixture["fixture_id"])
                else:
                    self.assertEqual(len(directives), 1, directives)
                    d = directives[0]
                    self.assertEqual((d["predicate_id"], d["kind"], d["symbol"], d["accession"]),
                                     (fixture["predicate_id"], fixture["expect"]["directive"], "EXSEMIB",
                                      fixture["filing"]["accession"]))
                    self.assertEqual(d["restarts_block"], fixture["expect"]["restarts_block"])
                    self.assertEqual(d["block_sessions"], PREDICATES[fixture["predicate_id"]]["directive"]["block_sessions"])
                    # Every finding of this disclosure carries the red flag; another listed item without a predicate
                    # (e.g. 2.05 next to 2.06) is its own ordinary finding.
                    own = [f for f in record["falsifier_findings"] if not (f["predicate_id"].startswith("ITEM:")
                                                                           and f["predicate_id"] != f"ITEM:{item}")]
                    flagged = [f for f in own if f.get("red_flag")]
                    self.assertEqual(len(flagged), len(own))
                    self.assertTrue(all(f["red_flag"]["span"]["text"] for f in flagged))
                    if fixture["expect"]["verified"] is False:
                        authorizing.append(fixture["fixture_id"])
        self.assertEqual(authorizing, [], "unsupported or ambiguous fixtures authorized action")

    def test_unverified_item_never_lets_evidence_look_clear(self):
        for fid in ("RF1-4.02-NEGATED", "RF2-2.06-UNSUPPORTED-NO-SECTION", "RF1-4.02-STALE"):
            with self.subTest(fixture=fid):
                run = Run(fid)
                result = run.assess(fid)
                self.assertTrue(any(m.startswith("EVIDENCE_RED_FLAG_UNVERIFIED:") for m in result["missingness"]))
                self.assertNotEqual(run.state["evidence_gate"], "CLEAR")
                self.assertFalse(run.context()["review_complete"])

    def test_only_enabled_predicates_act(self):
        run = Run("RF1-4.02-SUPPORTED")
        run.assess("RF1-4.02-SUPPORTED")
        record = run.context()
        self.assertEqual(red_flag_directives(record, enabled_profile("RF2-ITEM-1.05")), [])
        self.assertEqual([d["kind"] for d in red_flag_directives(record, enabled_profile("RF1-ITEM-4.02"))], ["EXIT"])


class Sequences(unittest.TestCase):
    def test_corrected_releases_only_after_complete_read(self):
        """A8 with R25: a revision without the item resolves the latch only when it is read completely."""
        fid = "RF1-4.02-SUPPORTED"
        run = Run(fid)
        run.assess(fid)
        self.assertEqual([d["kind"] for d in red_flag_directives(run.context(), enabled_profile())], ["EXIT"])
        filing = BY_ID[fid]["filing"]
        source = next(s for s in run.w.source.filings[9900001] if s["accession"] == filing["accession"])
        source["items"] = ["8.01"]
        run.w.source.replace_document(filing["accession"], source["documents"][0]["name"], page(
            p("FORM 8-K"), p("Example Semiconductor Corp"), p("Item 8.01 Other Events."),
            p("The company held its annual meeting of stockholders.")))
        run.w.clock.advance(60_000)
        run.w.ingestor.poll(EXSEMI, recheck=frozenset({filing["accession"]}))
        latest = run.w.store.records(EXSEMI)[-1].read()
        self.assertEqual(latest["revision"], 1)
        primary = next(d for d in latest["documents"] if d["role"] == "PRIMARY")["text_sha256"]
        blob = run.w.artifacts.blobs.pop(primary)
        run.assess(fid)  # incomplete: the newer revision's primary document cannot be read
        self.assertEqual([d["kind"] for d in red_flag_directives(run.context(), enabled_profile())], ["EXIT"])
        run.w.artifacts.blobs[primary] = blob
        run.w.clock.advance(1_000)
        run.assess(fid)
        self.assertEqual(red_flag_directives(run.context(), enabled_profile()), [])
        self.assertTrue(any(a.get("red_flag") for a in run.state["resolved_adverse"]))

    def test_class2_leaves_a_timed_view_and_class1_does_not(self):
        run = Run("RF2-1.05-SUPPORTED")
        run.assess("RF2-1.05-SUPPORTED")
        record = run.context()
        self.assertEqual(record["status"], "ADVERSE")
        self.assertFalse(record["review_complete"])
        self.assertTrue(record["review_complete_excluding_timed_blocks"])
        self.assertTrue(all(f["red_flag"]["class"] == 2 for f in record["falsifier_findings"]))
        run = Run("RF1-4.02-SUPPORTED")
        run.assess("RF1-4.02-SUPPORTED")
        self.assertFalse(run.context()["review_complete_excluding_timed_blocks"])

    def test_amendment_after_original_never_restarts_a_block(self):
        run = Run("RF2-2.06-SUPPORTED", "RF2-2.06-AMENDED")
        run.assess("RF2-2.06-SUPPORTED")
        run.assess("RF2-2.06-AMENDED")
        directives = red_flag_directives(run.context(), enabled_profile())
        self.assertEqual([(d["amendment"], d["restarts_block"]) for d in directives], [(False, True), (True, False)])

    def test_amendment_takes_its_event_time_from_the_original_in_the_index(self):
        """R05: an 8-K/A naming no original date is dated by the original 8-K of the same item in the index."""
        original, amendment = "RF1-4.02-SUPPORTED", "RF1-4.02-AMENDED-NO-ORIGINAL"
        run = Run(original, amendment)
        run.assess(original)
        result = run.assess(amendment)
        check = next(c for c in result["red_flag_checks"] if c["accession"] == BY_ID[amendment]["filing"]["accession"])
        self.assertEqual((check["verified"], check["reason"]), (True, "VERIFIED"))
        self.assertEqual(check["event_time_basis"], "AMENDED_FILING_IN_INDEX")
        self.assertEqual(check["amends_accession"], BY_ID[original]["filing"]["accession"])
        self.assertEqual(check["event_original_ms"], run.w.record(original)["original_ms"])
        directives = red_flag_directives(run.context(), enabled_profile())
        self.assertEqual(sorted((d["accession"], d["kind"], d["amendment"]) for d in directives),
                         sorted([(BY_ID[original]["filing"]["accession"], "EXIT", False),
                                 (BY_ID[amendment]["filing"]["accession"], "EXIT", True)]))

    def test_amendment_of_a_stale_original_is_stale(self):
        """R05: the event is as old as the original filing, whatever the amendment's own acceptance time."""
        original, amendment = "RF1-4.02-STALE", "RF1-4.02-AMENDED-NO-ORIGINAL"
        run = Run(original, amendment)
        run.assess(original)
        result = run.assess(amendment)
        check = next(c for c in result["red_flag_checks"] if c["accession"] == BY_ID[amendment]["filing"]["accession"])
        self.assertEqual((check["verified"], check["reason"]), (False, "STALE_EVENT"))
        self.assertEqual(red_flag_directives(run.context(), enabled_profile()), [])

    def test_stated_original_date_is_recorded(self):
        """R05: the date the amendment gives for its original is the event time when no original is indexed."""
        run = Run("RF2-1.05-AMENDED")
        check = run.assess("RF2-1.05-AMENDED")["red_flag_checks"][0]
        self.assertEqual((check["verified"], check["event_time_basis"]), (True, "AMENDMENT_STATES_ORIGINAL_DATE"))
        self.assertEqual(check["event_original_ms"], 1_791_417_600_000)  # 2026-10-08T00:00:00Z

    def test_amendment_is_never_dated_by_an_unrelated_newer_original(self):
        """V04 (red team F1): two same-item originals and no stated date: the amendment cannot be dated."""
        stale, unrelated, amendment = "RF2-2.06-ORIGINAL-AUGUST", "RF2-2.06-UNRELATED-OCTOBER", "RF2-2.06-AMENDED-NO-DATE"
        run = Run(stale, unrelated, amendment)
        for fid in (stale, unrelated):
            run.assess(fid)
        check = run.assess(amendment)["red_flag_checks"][0]
        self.assertEqual((check["verified"], check["reason"]), (False, "AMENDED_ORIGINAL_UNKNOWN"))
        self.assertEqual(red_flag_directives(run.context(), enabled_profile()), [])

    def test_red_flag_latch_survives_a_state_round_trip(self):
        """AC-4.3 (part): the latch and its red flag survive the canonical state document."""
        from larp.contracts import Document
        from larp.intelligence.gate import state_document
        run = Run("RF1-4.02-SUPPORTED")
        run.assess("RF1-4.02-SUPPORTED")
        restored = Document(state_document(run.state).payload).read()
        self.assertEqual(restored, run.state)
        record = build_evidence_context(consume(restored, run.w.clock()), restored, run_id=RUN_ID, token="EXSEMIB",
                                        underlying_id=EXSEMI, policy_profile_hash=PROFILE)
        self.assertEqual(record, run.context())


class RedTeamUnits(unittest.TestCase):
    """V02, V05, V06 (internal red team of the review fixes)."""

    def test_widened_non_reliance_wording_counts_only_as_the_402_trigger(self):
        from larp.intelligence.semantics import classify_event, finding_eligible
        cases = [  # (text, trigger, event): none of these is the issuer's occurred event
            ("The unaudited restated quarterly data must not be relied upon as a substitute for the audited financial "
             "statements.", "restated", "RESTATEMENT"),
            ("The restated pro forma amounts are presented for illustrative purposes only and cannot be relied upon as "
             "a substitute for audited results.", "restated", "RESTATEMENT"),
            ("Reports that we experienced a cybersecurity incident cannot be relied upon.", "cybersecurity incident",
             "CYBERSECURITY_INCIDENT"),
        ]
        for text, trigger, event in cases:
            with self.subTest(text=text[:40]):
                start = text.index(trigger)
                sem = classify_event(text, start, start + len(trigger), event=event, document_ms=1_791_590_400_000)
                self.assertFalse(finding_eligible(sem), sem)

    def test_many_headings_stay_linear(self):
        """V06: a document of repeated headings is verified in bounded time."""
        import time
        from larp.intelligence.redflags import verify_item
        text = "\n".join(["Item 2.06 Material Impairments"] * 20_000)
        record = {"accession": "a", "record_id": "r", "form": "8-K", "items": ["2.06"], "original_ms": 1_791_500_000_000,
                  "documents": [{"text_sha256": "t", "name": "d"}]}
        started = time.monotonic()
        check = verify_item(PREDICATES["RF2-ITEM-2.06"], record=record, texts={"t": text}, issuer_names=(),
                            filer_class="DOMESTIC", cutoff_ms=1_791_590_400_000, set_sha256=SET_SHA)
        self.assertLess(time.monotonic() - started, 5.0)
        self.assertFalse(check["verified"])

    def test_malformed_index_records_do_not_crash_amendment_dating(self):
        from larp.intelligence.redflags import event_time
        record = {"accession": "a", "form": "8-K/A", "original_ms": 1_791_500_000_000, "documents": []}
        prior = [{"accession": "b", "form": None, "items": ["2.06"], "original_ms": 1_791_400_000_000},
                 {"accession": "c", "items": None, "original_ms": None}]
        self.assertEqual(event_time(record, texts={}, prior_records=prior, item="2.06")[1], "AMENDED_ORIGINAL_UNKNOWN")


class Authority(unittest.TestCase):
    def test_default_is_shadow_and_profile_must_name_this_set(self):
        rights = authority({"evidence_mode": "SHADOW"})["red_flags"]
        self.assertEqual(set(rights["predicates"].values()), {"SHADOW"})
        self.assertEqual(rights["set_sha256"], red_flag_predicates()[1])
        enabled = authority(enabled_profile())["red_flags"]["predicates"]
        self.assertEqual(enabled, {"RF1-ITEM-4.02": "EXIT", "RF2-ITEM-1.05": "BLOCK_NEW_BUYS",
                                   "RF2-ITEM-2.06": "BLOCK_NEW_BUYS", "RF3-STATEMENTS": "SHADOW"})
        for bad in ({"set_sha256": "0" * 64, "enabled": ["RF1-ITEM-4.02"]},
                    {"set_sha256": SET_SHA, "enabled": ["RF9-UNKNOWN"]},
                    {"set_sha256": SET_SHA, "enabled": ["RF1-ITEM-4.02", "RF1-ITEM-4.02"]},
                    {"set_sha256": SET_SHA},
                    ["RF1-ITEM-4.02"]):
            with self.subTest(spec=bad), self.assertRaises(AuthorityError):
                authority({"evidence_mode": "SHADOW", "red_flag_authority": bad})

    def test_profiles_without_red_flag_authority_never_need_the_predicate_set(self):
        """R14: a set that cannot be loaded leaves profiles without red_flag_authority as before (all SHADOW)."""
        from unittest import mock
        from larp.integration import contract
        run = Run("RF1-4.02-SUPPORTED")
        run.assess("RF1-4.02-SUPPORTED")
        record = run.context()
        broken = mock.Mock(side_effect=IntelligenceError("malformed set"))
        with mock.patch.object(contract, "red_flag_predicates", broken):
            rights = authority({"evidence_mode": "SHADOW"})
            self.assertEqual(rights["falsifier"], "SHADOW")
            self.assertEqual(set(rights["red_flags"]["predicates"].values()) - {"SHADOW"}, set())
            self.assertEqual(red_flag_directives(record, {"evidence_mode": "SHADOW"}), [])
            with self.assertRaises(AuthorityError):
                authority(enabled_profile())

    def test_tampered_red_flag_in_a_record_is_rejected_or_inert(self):
        run = Run("RF1-4.02-SUPPORTED")
        run.assess("RF1-4.02-SUPPORTED")
        record = run.context()
        tampered = copy.deepcopy(record)
        for finding in tampered["falsifier_findings"]:
            finding["red_flag"]["class"] = 2
        self.assertEqual(problem(tampered), "HASH_MISMATCH")
        from larp.integration.contract import context_hash as record_hash
        tampered["context_hash"] = record_hash(tampered)
        # A class that does not match the predicate's record yields no directive.
        self.assertEqual(red_flag_directives(tampered, enabled_profile()), [])
        forged = copy.deepcopy(record)
        for finding in forged["falsifier_findings"]:
            finding["red_flag"]["set_sha256"] = "0" * 64
        forged["context_hash"] = record_hash(forged)
        self.assertEqual(red_flag_directives(forged, enabled_profile()), [])


if __name__ == "__main__":
    unittest.main()
