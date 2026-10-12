"""IDEA-044: prevent malformed/unaligned inputs from becoming research support."""
from copy import deepcopy
import subprocess
from unittest.mock import patch

import pytest

from larp.contracts import ContractError, Document
from larp.research import ablation, evaluation
from larp.research.evaluation import evaluate, fusion_rows
from tests.redteam.test_integration_redteam import econ_registration, econ_outcomes


def evaluate_fixture(*, change=None, registration=None):
    rows = [o for pair in econ_outcomes([10_000] * 4) for o in pair]
    if change:
        rows[1].update(change)
    return evaluate(Document.from_dict(registration or econ_registration(4)),
                    [Document.from_dict(o) for o in rows]).read()


@pytest.mark.parametrize("change", [
    {"wallet_net_units": True}, {"wallet_net_units": "10000"},
    {"opening_equity_units": 0}, {"opening_equity_units": True},
    {"maximum_drawdown_bps": -1}, {"maximum_drawdown_bps": True},
    {"maximum_drawdown_bps": 10001}, {"first_session": False},
    {"last_session": True}, {"detection_delay_sessions": True},
])
def test_malformed_financial_outcomes_return_not_run(change):
    assert evaluate_fixture(change=change)["status"] == "NOT_RUN"


def test_different_label_end_cannot_be_paired_with_same_registered_cluster():
    registration = econ_registration(4)
    rows = [o for pair in econ_outcomes([10_000] * 4) for o in pair]
    # Both label ends lie inside the registered window, but mark different time horizons.
    from datetime import timedelta
    from larp.strategy.schema import instant
    rows[1]["label_end_at"] = (instant(rows[1]["label_end_at"]) - timedelta(hours=1)).isoformat()
    report = evaluate(Document.from_dict(registration), [Document.from_dict(o) for o in rows]).read()
    assert report["status"] == "NOT_RUN"
    assert "different evaluation horizons" in report["reason"]


def test_different_session_horizon_cannot_be_paired_inside_broad_window():
    registration = econ_registration(4)
    rows = [o for pair in econ_outcomes([10_000] * 4) for o in pair]
    registration["windows"][0]["last_session"] += 1
    rows[1]["first_session"] += 1
    rows[1]["last_session"] += 1
    report = evaluate(Document.from_dict(registration), [Document.from_dict(o) for o in rows]).read()
    assert report["status"] == "NOT_RUN"
    assert "different evaluation horizons" in report["reason"]


def test_aligned_positive_and_signed_negative_controls_keep_their_verdicts():
    assert evaluate_fixture()["status"] == "SUPPORTED"
    rows = [o for pair in econ_outcomes([-10_000] * 4) for o in pair]
    report = evaluate(Document.from_dict(econ_registration(4)), [Document.from_dict(o) for o in rows]).read()
    assert report["status"] == "NOT_SUPPORTED"


def test_positive_mean_outside_bootstrap_interval_does_not_support():
    rows = [o for pair in econ_outcomes([10_000, 30_000]) for o in pair]
    for row in rows:
        if row["variant"] == "baseline":
            row["wallet_net_units"] = 0
    with patch.object(evaluation, "MIN_TAIL_DRAWS", 0):
        report = evaluate(Document.from_dict(econ_registration(2, bootstrap_draws=1, seed=0)),
                          [Document.from_dict(o) for o in rows]).read()
    assert report["status"] == "INCONCLUSIVE"
    assert report["reason"] == "BOOTSTRAP_INTERVAL_EXCLUDES_OBSERVED_MEAN"


def test_preregistration_requires_exact_committed_bytes(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    path = tmp_path / "EXP-999.md"
    path.write_text("prospective fixture criteria")
    assert not ablation._committed(path)
    git("add", "EXP-999.md")
    assert not ablation._committed(path)  # staged is not committed
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
    assert ablation._committed(path)
    path.write_text("prospective fixture criteria\nPOST-HOC-STUDY")
    assert not ablation._committed(path)
    git("add", "EXP-999.md")
    assert not ablation._committed(path)  # staged modification still differs from HEAD


@pytest.mark.parametrize("exp_id", ["EXP-../EXP-001", "EXP-001/../EXP-002", "EXP-001.extra", "EXP-"])
def test_registration_ids_cannot_escape_the_ledger(exp_id):
    from tests.research.test_ablation import spec
    assert "NO_COMMITTED_EXP_RECORD" in ablation.validate(spec(exp_id=exp_id))


def fusion_request():
    prediction = {"origin": "CHRONOLOGICAL_OOF", "fold_id": "fixture",
        "training_label_end": "2026-01-01T00:00:00Z", "predicted_at": "2026-01-02T00:00:00Z",
        "available_at": "2026-01-02T00:00:00Z", "training_last_session": 1}
    return {"rights_cleared": True, "purge_sessions": 5, "embargo_sessions": 5,
            "rows": [{"decision_at": "2026-01-03T00:00:00Z", "session_index": 30,
                      "evidence_prediction": deepcopy(prediction), "price_prediction": deepcopy(prediction)}]}


@pytest.mark.parametrize("change", [
    {"training_label_end": "2026-01-02T12:00:00Z"},
    {"available_at": "2026-01-01T12:00:00Z"}, {"training_last_session": -1},
])
def test_prediction_must_follow_training_and_precede_availability(change):
    request = fusion_request()
    request["rows"][0]["evidence_prediction"].update(change)
    with pytest.raises(ContractError):
        fusion_rows(Document.from_dict(request))


@pytest.mark.parametrize("field", ["purge_sessions", "embargo_sessions"])
def test_negative_separation_cannot_disable_oof_embargo(field):
    request = fusion_request()
    request[field] = -1
    with pytest.raises(ContractError):
        fusion_rows(Document.from_dict(request))


def test_oof_chronology_control_and_explicit_rights():
    request = fusion_request()
    assert fusion_rows(Document.from_dict(request)).read()["status"] == "NOT_RUN"
    request["rights_cleared"] = "false"
    assert fusion_rows(Document.from_dict(request)).read()["status"] == "INCONCLUSIVE"
