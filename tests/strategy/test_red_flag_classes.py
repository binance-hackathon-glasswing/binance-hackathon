"""P04 proposed I8 registry tests; Yao's real records remain an integration gate."""

from dataclasses import replace

import pytest

from larp.contracts import ContractError, Document, TargetKind
from larp.integration.contract import context_hash
from larp.research.fixtures import changed
from larp.strategy.policy import decide
from larp.strategy.predicates import predicate_records
from tests.strategy.live_fixtures import live_snapshot, registry


def evidence(s, item, *, finding_id="finding:first", version=1):
    m = s.context.read()["markets"][0]
    now = int(s.observed_at.timestamp() * 1000)
    record = {"schema": "EvidenceContext.v1", "run_id": s.run_id, "policy_profile_hash": s.policy_profile_hash,
        "issuer_id": m["underlying_id"], "underlying_id": m["underlying_id"], "token": "NVDAB",
        "state_version": version, "as_of_ms": now, "assessed_until_ms": now + 60000,
        "status": "ADVERSE" if item else "CLEAR", "review_complete": not bool(item),
        "quality": "VERIFIED", "availability": "AVAILABLE", "statements_pending": [],
        "falsifier_findings": [] if item is None else [{"predicate_id": "F-ITEM-" + item,
            "finding_id": finding_id, "supported": True, "verifier_accepted": True,
            "supporting_spans": ["SYNTHETIC VERIFIED SPAN"], "resolution_rule": "SOURCE_CORRECTED_OR_WITHDRAWN"}]}
    record["context_hash"] = context_hash(record)
    return changed(s, assessments=[record])


def next_session(s, following, session, item="1.05", finding_id="finding:first"):
    s = replace(s, policy_state=following)
    return evidence(changed(s, session_index=session), item, finding_id=finding_id, version=session)


def target(proposal):
    return next(t for t in proposal.targets if t.symbol == "NVDAB")


def test_class1_exits_latches_without_context_and_clears_on_verified_resolution():
    s = evidence(live_snapshot(held={"NVDAB": 3000}), "4.02")
    first = decide(s, s.policy_state)
    assert target(first).kind is TargetKind.EXIT
    following = replace(changed(s, assessments=[]), policy_state=first.next_policy_state)
    assert target(decide(following, following.policy_state)).kind is TargetKind.EXIT
    cleared = evidence(following, None, version=2)
    result = decide(cleared, cleared.policy_state)
    assert not result.next_policy_state.data.read()["blocked"]
    assert target(result).kind is TargetKind.TARGET_WEIGHT


@pytest.mark.parametrize("item", ["1.05", "2.06"])
def test_class2_never_sells_expires_after_five_sessions_and_replay_cannot_renew(item):
    s = evidence(live_snapshot(held={"NVDAB": 3000}), item)
    proposal = decide(s, s.policy_state)
    assert target(proposal).kind is TargetKind.KEEP_QUANTITY
    assert proposal.next_policy_state.data.read()["blocked"]["NVDAB"]["expires_session"] == 85
    for session in range(81, 87):
        s = next_session(s, proposal.next_policy_state, session, item=item)
        proposal = decide(s, s.policy_state)
        assert (target(proposal).kind is TargetKind.KEEP_QUANTITY) == (session < 85)
    assert not proposal.next_policy_state.data.read()["blocked"]


def test_new_finding_extends_block_and_expiry_is_durable_without_context():
    s = evidence(live_snapshot(), "1.05")
    first = decide(s, s.policy_state)
    s = next_session(s, first.next_policy_state, 83, finding_id="finding:new")
    second = decide(s, s.policy_state)
    assert second.next_policy_state.data.read()["blocked"]["NVDAB"]["expires_session"] == 88
    s = replace(changed(s, session_index=88, assessments=[]), policy_state=second.next_policy_state)
    assert not decide(s, s.policy_state).next_policy_state.data.read()["blocked"]


def test_class3_statement_does_not_veto_and_bad_registry_rejects():
    s = evidence(live_snapshot(), None)
    record = s.context.read()["assessments"][0]
    record.update(status="UNKNOWN", statements_pending=[{"statement_id": "synthetic-watch"}])
    record["context_hash"] = context_hash(record)
    s = changed(s, assessments=[record])
    assert target(decide(s, s.policy_state)).kind is TargetKind.TARGET_WEIGHT
    broken = registry().read()
    broken["records"][1]["block_sessions"] = 6
    with pytest.raises(ContractError):
        predicate_records(broken)
    with pytest.raises(ContractError):
        decide(changed(s, red_flag_predicates=None), s.policy_state)
