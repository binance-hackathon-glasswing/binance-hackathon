"""Paired cluster evaluation and chronology guards, never an automatic live gate.

No historical dataset is supplied here. Tests use synthetic accounting examples.
EXP IDs/rights/splits must be coordinated with the integrator before a real run.
"""

from fractions import Fraction
import random

from larp.contracts import ContractError, Document
from larp.strategy.schema import instant, integer, ratio


def validate_registration(registration):
    d = registration.read()
    fields = ("experiment_id", "hypothesis", "population", "dataset_hash", "rights_basis",
              "cost_model", "detection_delay", "windows", "purge_sessions", "embargo_sessions",
              "fixed_parameters", "paired_metric", "confidence_method", "kill_rule",
              "inconclusive_rule", "default", "registered_commit", "variants")
    if any(d.get(k) is None or d.get(k) == "" for k in fields):
        raise ContractError("Incomplete prospective registration")
    if d["schema"] != "EconomicRegistration.v1" or d["rights_cleared"] is not True:
        raise ContractError("Rights/registration missing")
    if len(d["registered_commit"]) != 40 or len(d["dataset_hash"]) != 64:
        raise ContractError("Commit and dataset identity required")
    if d["confidence_method"] != "PAIRED_CALENDAR_CLUSTER_BOOTSTRAP":
        raise ContractError("Unsupported confidence method")
    windows = sorted(d["windows"], key=lambda w: instant(w["start"]))
    for a, b in zip(windows, windows[1:]):
        if instant(a["label_end"]) >= instant(b["start"]):
            raise ContractError("Evaluation windows overlap labels; purge/embargo required")
    integer(d["bootstrap_draws"], 1)
    if not 0 < integer(d["confidence_bps"]) < 10000:
        raise ContractError("Confidence out of bounds")
    integer(d["minimum_clusters"], 2)
    return d


def evaluate(registration: Document, outcomes):
    try:
        d = validate_registration(registration)
    except (ContractError, KeyError, TypeError) as exc:
        return Document.from_dict({"schema": "EconomicReport.v1", "status": "NOT_RUN",
                                   "reason": str(exc)})
    groups = {}
    summary = {name: {"wallet_net_units": 0, "service_units": 0, "fees_units": 0,
                      "gas_units": 0, "turnover_units": 0, "rejected_allocations": 0,
                      "missed_upside_units": 0, "maximum_drawdown_bps": 0}
               for name in d["variants"]}
    windows = {w["cluster_id"] for w in d["windows"]}
    for document in outcomes:
        o = document.read()
        if o["schema"] != "PortfolioOutcome.v1" or o["cluster_id"] not in windows:
            raise ContractError("Outcome not in registered window")
        if o["variant"] not in summary or o["dataset_hash"] != d["dataset_hash"]:
            raise ContractError("Variant/data mismatch")
        group = groups.setdefault(o["cluster_id"], {})
        if o["variant"] in group:
            raise ContractError("Expected one portfolio outcome per common-market cluster")
        group[o["variant"]] = o
        for k in summary[o["variant"]]:
            if k == "maximum_drawdown_bps":
                summary[o["variant"]][k] = max(summary[o["variant"]][k], o[k])
            else:
                summary[o["variant"]][k] += o[k]
    paired, absolute = [], []
    baseline, treatment = d["variants"]
    for group in groups.values():
        if set(group) != {baseline, treatment}:
            continue
        a, b = group[baseline], group[treatment]
        if a["opening_equity_units"] != b["opening_equity_units"]:
            raise ContractError("Paired portfolios differ in initial capital")
        E = integer(a["opening_equity_units"], 1)
        a_net = a["wallet_net_units"] - a["service_units"]
        b_net = b["wallet_net_units"] - b["service_units"]
        paired.append(Fraction(b_net - a_net, E))
        absolute.append(Fraction(b_net, E))
    result = {"schema": "EconomicReport.v1", "status": "INCONCLUSIVE",
              "paired_clusters": len(paired), "unpaired_clusters": len(groups) - len(paired),
              "summary": summary, "promotion_authorized": False,
              "origin": d["origin"], "default": d["default"]}
    if len(paired) < d["minimum_clusters"] or len(paired) != len(windows):
        result["reason"] = "INSUFFICIENT_ALIGNED_INDEPENDENT_WINDOWS"
        return Document.from_dict(result)
    rng = random.Random(d["seed"])
    draws = sorted(sum((paired[rng.randrange(len(paired))] for _ in paired), Fraction(0)) / len(paired)
                   for _ in range(d["bootstrap_draws"]))
    tail = Fraction(10000 - d["confidence_bps"], 20000)
    low = draws[int(tail * len(draws))]
    high = draws[min(len(draws) - 1, int((1 - tail) * len(draws)))]
    absolute_mean = sum(absolute, Fraction(0)) / len(absolute)
    result.update(paired_mean=ratio(sum(paired, Fraction(0)) / len(paired)),
                  confidence_interval=[ratio(low), ratio(high)],
                  treatment_absolute_mean=ratio(absolute_mean))
    result["status"] = ("SUPPORTED" if low > 0 and absolute_mean > 0 else
                        "NOT_SUPPORTED" if high < 0 or absolute_mean <= 0 else "INCONCLUSIVE")
    return Document.from_dict(result)


def fusion_rows(request: Document):
    """Guard chronological OOF upstream features; no model/checkpoint is trained."""
    d = request.read()
    if not d.get("rights_cleared") or not d.get("rows"):
        return Document.from_dict({"schema": "FusionDataset.v1", "status": "INCONCLUSIVE",
                                   "reason": "NO_RIGHTS_CLEARED_ALIGNED_DATA", "rows": []})
    rows = []
    for row in d["rows"]:
        decision = instant(row["decision_at"])
        for upstream in (row["evidence_prediction"], row["price_prediction"]):
            if (upstream.get("origin") != "CHRONOLOGICAL_OOF" or not upstream.get("fold_id")
                    or instant(upstream["training_label_end"]) >= decision
                    or instant(upstream["predicted_at"]) > decision
                    or instant(upstream["available_at"]) > decision
                    or upstream["training_last_session"] + d["purge_sessions"] + d["embargo_sessions"] >= row["session_index"]):
                raise ContractError("Leaky/non-OOF upstream prediction")
        rows.append(row)
    return Document.from_dict({"schema": "FusionDataset.v1", "status": "NOT_RUN",
                               "reason": "ALIGNED_OOF_ROWS_VALIDATED_NO_TRAINING", "rows": rows})
