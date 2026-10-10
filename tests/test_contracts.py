"""Synthetic checks only: no credentials, probes, market data or network calls."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import unittest

from larp.contracts import (
    ContractError, DecisionSnapshot, Document, PolicyState, Proposal,
    Target, TargetKind, validate_proposal,
)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 10, tzinfo=timezone.utc)
        self.state = PolicyState("fixture-run", "fixture-policy", "counter.v1", 0,
                                 Document.from_dict({"count": 0}))
        self.snapshot = DecisionSnapshot(
            "fixture-run", "fixture-wallet", "fixture-version", "a" * 64, 1,
            self.now, ("TSLAB", "MSFTB"), self.state,
            Document.from_dict({"settled_units": {"MSFTB": 123}, "reserved_units": {"MSFTB": 0}}),
        )
        self.proposal = Proposal(self.snapshot.snapshot_id, self.state.policy_id,
                                 self.now + timedelta(seconds=30), (), replace(self.state, version=1))

    def validate(self, proposal=None, snapshot=None, now=None):
        return validate_proposal(snapshot or self.snapshot, proposal or self.proposal, now=now or self.now)

    def test_canonical_order_and_utf8(self):
        a = Document.from_dict({"z": [1, {"name": "世界"}], "a": True})
        b = Document.from_dict({"a": True, "z": [1, {"name": "世界"}]})
        self.assertEqual(a.payload, b.payload)
        self.assertEqual(a.digest("v1"), b.digest("v1"))
        self.assertNotEqual(a.digest("v1"), a.digest("v2"))

    def test_documents_detach_nested_input_and_output(self):
        original = {"items": [{"value": 3}]}
        document = Document.from_dict(original)
        original["items"][0]["value"] = 4
        copy = document.read()
        copy["items"].clear()
        self.assertEqual(document.read(), {"items": [{"value": 3}]})
        with self.assertRaises(FrozenInstanceError):
            document.payload = b"{}"

    def test_reject_ambiguous_or_mutable_documents(self):
        for value in (0.1, float("nan"), float("inf"), Fraction(1, 2), {1: "bad"}, object()):
            with self.subTest(value=repr(value)), self.assertRaises(ContractError):
                Document.from_dict({"value": value})
        for payload in (b'{"x":1,"x":2}', b'{ "x": 1 }', b'[]', bytearray(b'{}'), b'{"x":NaN}'):
            with self.subTest(payload=payload), self.assertRaises(ContractError):
                Document(payload)

    def test_hash_binds_every_snapshot_version(self):
        variants = (
            replace(self.snapshot, event_sequence=2),
            replace(self.snapshot, policy_profile_hash="b" * 64),
            replace(self.snapshot, engine_version="other-version"),
            replace(self.snapshot, wallet_id="other-wallet"),
            replace(self.snapshot, policy_state=replace(self.state, version=1)),
            replace(self.snapshot, context=Document.from_dict({"settled_units": {"MSFTB": 124}})),
        )
        for snapshot in variants:
            with self.subTest(snapshot=snapshot.snapshot_id), self.assertRaises(ContractError):
                self.validate(snapshot=snapshot)

    def test_timezone_normalization_and_naive_rejection(self):
        shifted = self.now.astimezone(timezone(timedelta(hours=8)))
        self.assertEqual(self.snapshot.snapshot_id, replace(self.snapshot, observed_at=shifted).snapshot_id)
        for operation in (lambda: replace(self.snapshot, observed_at=self.now.replace(tzinfo=None)),
                          lambda: self.validate(now=self.now.replace(tzinfo=None))):
            with self.assertRaises(ContractError):
                operation()

    def test_missing_target_keeps_quantity(self):
        targets = self.validate()
        self.assertEqual([t.symbol for t in targets], ["MSFTB", "TSLAB"])
        self.assertTrue(all(t.kind is TargetKind.KEEP_QUANTITY and t.weight is None for t in targets))

    def test_exit_is_explicit_and_validation_has_no_fill_effect(self):
        old_hash = self.snapshot.snapshot_id
        proposal = replace(self.proposal, targets=(Target("MSFTB", TargetKind.EXIT, "FIXTURE_EXIT"),))
        self.assertEqual(self.validate(proposal)[0].kind, TargetKind.EXIT)
        self.assertEqual(self.snapshot.snapshot_id, old_hash)
        self.assertEqual(self.snapshot.context.read()["settled_units"]["MSFTB"], 123)
        self.assertEqual(self.state.version, 0)

    def test_invalid_weights_and_instruction_shapes(self):
        for weight in (float("nan"), float("inf"), 0.2, 1, True, Fraction(-1, 10), Fraction(11, 10)):
            with self.subTest(weight=weight), self.assertRaises(ContractError):
                Target("MSFTB", TargetKind.TARGET_WEIGHT, "FIXTURE", weight)
        for kind in (TargetKind.EXIT, TargetKind.KEEP_QUANTITY, "TARGET_WEIGHT"):
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                Target("MSFTB", kind, "FIXTURE", Fraction(1, 5))

    def test_duplicate_unknown_and_excess_total_rejected(self):
        msft = Target("MSFTB", TargetKind.TARGET_WEIGHT, "FIXTURE", Fraction(3, 5))
        for targets in ((msft, msft), (Target("UNKNOWN", TargetKind.EXIT, "FIXTURE"),),
                        (msft, Target("TSLAB", TargetKind.TARGET_WEIGHT, "FIXTURE", Fraction(3, 5)))):
            with self.subTest(targets=targets), self.assertRaises(ContractError):
                self.validate(replace(self.proposal, targets=targets))

    def test_exact_weights_and_order_independent_proposal_hash(self):
        targets = (Target("TSLAB", TargetKind.TARGET_WEIGHT, "FIXTURE", Fraction(2, 3)),
                   Target("MSFTB", TargetKind.TARGET_WEIGHT, "FIXTURE", Fraction(1, 3)))
        proposal = replace(self.proposal, targets=targets)
        self.assertEqual(sum(t.weight for t in self.validate(proposal)), Fraction(1))
        self.assertEqual(proposal.proposal_id, replace(proposal, targets=targets[::-1]).proposal_id)

    def test_expiry_boundary_and_clock_reversal(self):
        for now in (self.proposal.valid_until, self.proposal.valid_until + timedelta(seconds=1),
                    self.now - timedelta(microseconds=1)):
            with self.subTest(now=now), self.assertRaises(ContractError):
                self.validate(now=now)
        self.validate(now=self.proposal.valid_until - timedelta(microseconds=1))

    def test_wrong_policy_and_state_ownership_rejected(self):
        with self.assertRaises(ContractError):
            self.validate(replace(self.proposal, policy_id="other-policy"))
        for change in ({"run_id": "other-run"}, {"policy_id": "other-policy"},
                       {"schema": "other-schema"}, {"version": 0}, {"version": 2}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                self.validate(replace(self.proposal, next_policy_state=replace(self.state, **change)))

    def test_snapshot_cannot_retain_mutable_or_invalid_values(self):
        for change in ({"universe": ["MSFTB"]}, {"universe": ("MSFTB", "MSFTB")},
                       {"context": {}}, {"event_sequence": True}, {"policy_profile_hash": "bad"},
                       {"policy_state": replace(self.state, run_id="other-run")}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                replace(self.snapshot, **change)


if __name__ == "__main__":
    unittest.main()
