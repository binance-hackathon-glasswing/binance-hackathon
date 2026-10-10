"""AblationStudy.v1: reproducible baseline / EDGAR / free-news / uncertain-event comparisons (IDEA-030 T03-T05,
IDEA-031 AC-E06). This module validates a study specification and runs the registered paired evaluation per arm;
it supplies no data and never promotes anything live.

Arms share one sizing rule, one risk profile, one execution/cost model, starting cash and one frozen primary
horizon; only their evidence inputs differ. Each arm is compared with the executable no-news baseline under its
own EconomicRegistration.v2 (research/evaluation.py), so costs (gas, spread/slippage, failed attempts),
re-entry, missed upside, drawdown, turnover and incomplete outcomes are all required outcome fields. Without a
committed EXP record and a rights-cleared point-in-time dataset the study is NOT_RUN; too few cases stay
INCONCLUSIVE with the registered default (fallback) unchanged.
"""

from pathlib import Path

from larp.contracts import ContractError, Document
from larp.research.evaluation import evaluate

ARMS = ("BASELINE", "EDGAR_EVIDENCE", "FREE_NEWS", "UNCERTAIN_EVENTS")
EVIDENCE = {"BASELINE": [], "EDGAR_EVIDENCE": ["EDGAR"], "FREE_NEWS": ["EDGAR", "FREE_OFFICIAL_SOURCES"],
            "UNCERTAIN_EVENTS": ["EDGAR", "FREE_OFFICIAL_SOURCES", "EVENT_STATEMENTS"]}
SHARED = ("sizing_rule", "risk_profile_hash", "execution_model", "cost_model", "starting_cash_units",
          "primary_horizon_sessions", "entry_exit_reentry_policy_hash", "correction_policy")
LEDGER = Path(__file__).resolve().parents[2] / "docs" / "ledger"


def validate(spec: dict) -> list:
    """Reasons the study cannot run as specified (empty = runnable)."""
    reasons = []
    if spec.get("schema") != "AblationStudy.v1":
        return ["SCHEMA"]
    exp = spec.get("exp_id")
    if type(exp) is not str or not exp.startswith("EXP-") or not (LEDGER / f"{exp}.md").exists():
        reasons.append("NO_COMMITTED_EXP_RECORD")
    data = spec.get("dataset") or {}
    if data.get("rights_cleared") is not True or data.get("point_in_time") is not True or len(data.get("sha256", "")) != 64:
        reasons.append("NO_RIGHTS_CLEARED_POINT_IN_TIME_DATA")
    arms = spec.get("arms") or {}
    if set(arms) != set(ARMS):
        reasons.append("ARMS_MUST_BE_" + "_".join(ARMS))
    shared = [{k: arm.get(k) for k in SHARED} for arm in arms.values()]
    if shared and any(s != shared[0] for s in shared):
        reasons.append("ARMS_DIFFER_BEYOND_EVIDENCE_INPUTS")
    if shared and any(v is None for v in shared[0].values()):
        reasons.append("SHARED_ASSUMPTION_MISSING")
    for name, arm in arms.items():
        if arm.get("evidence_inputs") != EVIDENCE.get(name):
            reasons.append(f"EVIDENCE_INPUTS_{name}")
        if arm.get("authority") not in ("SHADOW_EVALUATION",):
            reasons.append(f"ARM_AUTHORITY_{name}")
    if spec.get("secondary_horizons_are_diagnostics_only") is not True:
        reasons.append("PRIMARY_HORIZON_NOT_FROZEN")
    return sorted(set(reasons))


def run(spec: dict, registrations: dict, outcomes: dict) -> Document:
    """registrations/outcomes per non-baseline arm (EconomicRegistration.v2 / PortfolioOutcome.v2 documents)."""
    reasons = validate(spec)
    if reasons:
        return Document.from_dict({"schema": "AblationReport.v1", "status": "NOT_RUN", "reasons": reasons,
                                   "promotion_authorized": False})
    results = {}
    for arm in ARMS[1:]:
        registration = registrations.get(arm)
        if registration is None:
            raise ContractError(f"Missing registration for {arm}")
        if registration.read().get("variants") != ["BASELINE", arm]:
            raise ContractError("Each registration pairs its arm with the baseline")
        results[arm] = evaluate(registration, outcomes.get(arm, [])).read()
    status = "COMPLETE_NO_PROMOTION"
    return Document.from_dict({"schema": "AblationReport.v1", "status": status, "arms": results,
                               "promotion_authorized": False,
                               "note": "Results never change live authority; adoption is a separate team decision."})
