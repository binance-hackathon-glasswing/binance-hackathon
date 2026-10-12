"""Paired cluster evaluation and chronology guards, never an automatic live gate.

IDEA-031 (AC-E05): registrations are structured (EconomicRegistration.v2) and evaluated exactly as registered;
IDEA-030 R12.7 found that v1 accepted text criteria (paired_metric, kill_rule, inconclusive_rule) that the
verdict ignored, so v1 now returns NOT_RUN.

IDEA-034 (user decision 2026-10-11, goal is maximum profit): a treatment that loses money is never SUPPORTED.
Every support rule also requires the bootstrap lower bound of the treatment's own net return (registered metric)
to be above zero; a treatment whose upper bound is at or below zero is NOT_SUPPORTED whatever the paired result.
IDEA-033 R26: the bounds only mean that with enough resamples, so a registration needs MIN_TAIL_DRAWS draws beyond
each percentile bound, and an interval that excludes its own observed mean never supports.

No historical dataset is supplied here. Tests use synthetic accounting examples.
EXP IDs/rights/splits must be coordinated with the integrator before a real run.
"""

from fractions import Fraction
import random

from larp.contracts import ContractError, Document
from larp.strategy.schema import instant, integer, ratio


V2_FIELDS = frozenset({
    "schema", "experiment_id", "origin", "hypothesis", "population", "dataset_hash", "rights_basis", "rights_cleared",
    "cost_model", "detection_delay_sessions", "registered_commit", "variants", "default", "metric", "margin",
    "support_rule", "kill_rule", "inconclusive_rule", "minimum_clusters", "confidence_method", "confidence_bps",
    "bootstrap_draws", "seed", "purge_sessions", "embargo_sessions", "primary_horizon_sessions",
    "secondary_horizons_sessions", "independence_basis", "windows", "fixed_parameters"})
METRICS = ("PAIRED_NET_WALLET_RETURN", "PAIRED_NET_WALLET_RETURN_AFTER_SERVICE_COSTS")
# Every support rule carries the mandatory absolute condition below (IDEA-034); IDEA-033 R24's opt-in variant
# (mean > 0) is no longer a registrable value.
SUPPORT_RULES = ("LOWER_BOUND_ABOVE_MARGIN",)
ABSOLUTE_RETURN_RULE = "TREATMENT_LOWER_BOUND_ABOVE_ZERO"
KILL_RULES = ("UPPER_BOUND_BELOW_ZERO", "UPPER_BOUND_BELOW_MARGIN")
INCONCLUSIVE_RULES = ("OTHERWISE_INCLUDING_INSUFFICIENT_OR_INCOMPLETE",)
INDEPENDENCE = ("NON_OVERLAPPING_PURGED_EMBARGOED_WINDOWS",)
# Percentile bounds need resamples beyond them: 25 per tail is 1000 draws at 95%, 500 at 90%, 5000 at 99% (R26).
MIN_TAIL_DRAWS = 25
WINDOW_FIELDS = frozenset({"cluster_id", "decision_start", "decision_end", "label_end", "first_session",
                           "last_session"})


def validate_registration(registration):
    """EconomicRegistration.v2 (IDEA-031 AC-E05). Every criterion is a structured value this module implements;
    unknown fields or values are rejected rather than ignored. v1 (free-text criteria) is not evaluated."""
    d = registration.read()
    if d.get("schema") == "EconomicRegistration.v1":
        raise ContractError("UNSTRUCTURED_REGISTRATION_UNSUPPORTED: v1 text criteria are not implemented")
    if d.get("schema") != "EconomicRegistration.v2":
        raise ContractError("Unknown registration schema")
    unknown, missing = set(d) - V2_FIELDS, V2_FIELDS - set(d)
    if unknown or missing:
        raise ContractError(f"Registration fields unknown {sorted(unknown)} missing {sorted(missing)}")
    if d["rights_cleared"] is not True:
        raise ContractError("Rights/registration missing")
    if type(d["registered_commit"]) is not str or len(d["registered_commit"]) != 40 or len(d["dataset_hash"]) != 64:
        raise ContractError("Commit and dataset identity required")
    for name, allowed in (("metric", METRICS), ("support_rule", SUPPORT_RULES), ("kill_rule", KILL_RULES),
                          ("inconclusive_rule", INCONCLUSIVE_RULES), ("independence_basis", INDEPENDENCE),
                          ("confidence_method", ("PAIRED_CALENDAR_CLUSTER_BOOTSTRAP",))):
        if d[name] not in allowed:
            raise ContractError(f"Unsupported {name}: {d[name]!r}")
    margin = Fraction(integer(d["margin"][0]), integer(d["margin"][1], 1)) if type(d["margin"]) is list and \
        len(d["margin"]) == 2 else None
    if margin is None:
        raise ContractError("Margin must be [numerator, denominator] of opening equity")
    if type(d["variants"]) is not list or len(d["variants"]) != 2 or len(set(d["variants"])) != 2:
        raise ContractError("Exactly one baseline and one treatment variant")
    draws = integer(d["bootstrap_draws"], 1)
    if not 0 < integer(d["confidence_bps"]) < 10000:
        raise ContractError("Confidence out of bounds")
    if draws * (10000 - d["confidence_bps"]) < MIN_TAIL_DRAWS * 20000:
        raise ContractError(f"BOOTSTRAP_DRAWS_TOO_FEW: {draws} draws leave fewer than {MIN_TAIL_DRAWS} beyond "
                            f"each bound at {d['confidence_bps']} bps")
    integer(d["minimum_clusters"], 2)
    for name in ("purge_sessions", "embargo_sessions", "detection_delay_sessions"):
        integer(d[name])
    integer(d["primary_horizon_sessions"], 1)
    if type(d["secondary_horizons_sessions"]) is not list or d["primary_horizon_sessions"] in d["secondary_horizons_sessions"]:
        raise ContractError("One frozen primary horizon; secondary horizons are diagnostics only")
    windows = []
    for w in d["windows"]:
        if set(w) != WINDOW_FIELDS:
            raise ContractError("Window fields")
        start, end, label = instant(w["decision_start"]), instant(w["decision_end"]), instant(w["label_end"])
        first, last = integer(w["first_session"]), integer(w["last_session"])
        if not start < end <= label or last < first:
            raise ContractError("Window decision/label order")
        if last - first + 1 < d["primary_horizon_sessions"]:
            raise ContractError("Window shorter than the primary horizon")
        windows.append((start, w))
    windows.sort(key=lambda x: x[0])
    gap = d["purge_sessions"] + d["embargo_sessions"]
    for (_, a), (_, b) in zip(windows, windows[1:]):
        if instant(a["label_end"]) >= instant(b["decision_start"]):
            raise ContractError("Evaluation windows overlap labels; purge/embargo required")
        if b["first_session"] - a["last_session"] <= gap:
            raise ContractError("Purge/embargo sessions not respected between windows")
    if len({w["cluster_id"] for _, w in windows}) != len(windows):
        raise ContractError("Duplicate cluster")
    return dict(d, margin_fraction=margin)


OUTCOME_FIELDS = ("variant", "cluster_id", "dataset_hash", "opening_equity_units", "wallet_net_units", "service_units",
                  "fees_units", "gas_units", "spread_slippage_units", "failed_attempts", "failed_attempt_gas_units",
                  "reentries", "turnover_units", "rejected_allocations", "missed_upside_units",
                  "maximum_drawdown_bps", "decision_at", "label_end_at", "first_session", "last_session",
                  "executable_price_basis", "detection_delay_sessions", "complete", "provenance")


def _outcome_window(o, w, d):
    """Outcome provenance must sit inside its registered decision/label window and the frozen horizon."""
    decided, labelled = instant(o["decision_at"]), instant(o["label_end_at"])
    if not decided < labelled:
        raise ContractError("Outcome label ends before its decision")
    if not instant(w["decision_start"]) <= decided <= instant(w["decision_end"]) or labelled > instant(w["label_end"]):
        raise ContractError("Outcome decision/label times outside the registered window")
    if o["detection_delay_sessions"] != d["detection_delay_sessions"]:
        raise ContractError("Outcome used a detection delay other than the registered one")
    if not w["first_session"] <= o["first_session"] <= o["last_session"] <= w["last_session"]:
        raise ContractError("Outcome sessions outside the registered window")
    if o["last_session"] - o["first_session"] + 1 != d["primary_horizon_sessions"]:
        raise ContractError("Outcome horizon differs from the frozen primary horizon")
    if o["executable_price_basis"] != "POST_ASSESSMENT_EXECUTABLE_QUOTE":
        raise ContractError("Outcome not priced at post-assessment executable quotes")
    p = o["provenance"]
    if type(p) is not dict or p.get("dataset_hash") != d["dataset_hash"] or \
            p.get("generated_by_commit") != d["registered_commit"]:
        raise ContractError("Outcome provenance missing or not produced by the registered commit")


def evaluate(registration: Document, outcomes):
    """Paired, after-cost, cluster-bootstrap comparison evaluated exactly as registered (never a live gate).

    Net wallet return and off-wallet service costs are reported separately; service costs enter the metric only
    when the registered metric says so, in the paired and the absolute check alike. Beating the baseline is not
    enough: the treatment's own net return must be confidently positive (IDEA-034), and the report flags a
    baseline that loses money. Incomplete outcomes are retained and keep the verdict INCONCLUSIVE.
    An aligned cluster count is reported, but independence is a property of the registered design, not the count.
    """
    try:
        d = validate_registration(registration)
    except (ContractError, KeyError, TypeError) as exc:
        return Document.from_dict({"schema": "EconomicReport.v2", "status": "NOT_RUN", "reason": str(exc),
                                   "promotion_authorized": False})
    windows = {w["cluster_id"]: w for w in d["windows"]}
    sums = ("wallet_net_units", "service_units", "fees_units", "gas_units", "spread_slippage_units",
            "failed_attempts", "failed_attempt_gas_units", "reentries", "turnover_units", "rejected_allocations",
            "missed_upside_units")
    summary = {name: dict({k: 0 for k in sums}, maximum_drawdown_bps=0, incomplete=0) for name in d["variants"]}
    groups = {}
    try:
        for document in outcomes:
            o = document.read()
            if o.get("schema") != "PortfolioOutcome.v2" or any(k not in o for k in OUTCOME_FIELDS):
                raise ContractError("Outcome schema")
            if o["cluster_id"] not in windows or o["variant"] not in summary or o["dataset_hash"] != d["dataset_hash"]:
                raise ContractError("Outcome not in registered window/variant/data")
            _outcome_window(o, windows[o["cluster_id"]], d)
            group = groups.setdefault(o["cluster_id"], {})
            if o["variant"] in group:
                raise ContractError("Expected one portfolio outcome per common-market cluster")
            group[o["variant"]] = o
            s = summary[o["variant"]]
            for k in sums:
                s[k] += integer(o[k]) if k != "wallet_net_units" else o[k]
            s["maximum_drawdown_bps"] = max(s["maximum_drawdown_bps"], o["maximum_drawdown_bps"])
            s["incomplete"] += 0 if o["complete"] is True else 1
    except (ContractError, KeyError, TypeError) as exc:
        return Document.from_dict({"schema": "EconomicReport.v2", "status": "NOT_RUN", "reason": str(exc),
                                   "promotion_authorized": False})
    baseline, treatment = d["variants"]
    after_service = d["metric"] == "PAIRED_NET_WALLET_RETURN_AFTER_SERVICE_COSTS"
    paired, absolute, baseline_absolute, serviced, incomplete = [], [], [], [], 0
    for _, group in sorted(groups.items()):  # canonical order: the bootstrap must not depend on input order
        if set(group) != {baseline, treatment}:
            continue
        a, b = group[baseline], group[treatment]
        if a["opening_equity_units"] != b["opening_equity_units"]:
            return Document.from_dict({"schema": "EconomicReport.v2", "status": "NOT_RUN",
                                       "reason": "Paired portfolios differ in initial capital",
                                       "promotion_authorized": False})
        incomplete += (a["complete"] is not True) + (b["complete"] is not True)
        E = integer(a["opening_equity_units"], 1)
        net = lambda o: o["wallet_net_units"] - (o["service_units"] if after_service else 0)
        paired.append(Fraction(net(b) - net(a), E))
        absolute.append(Fraction(net(b), E))
        baseline_absolute.append(Fraction(net(a), E))
        serviced.append(Fraction(b["wallet_net_units"] - b["service_units"], E))
    margin = d["margin_fraction"]
    result = {"schema": "EconomicReport.v2", "status": "INCONCLUSIVE", "metric": d["metric"],
              "margin": ratio(margin), "absolute_return_rule": ABSOLUTE_RETURN_RULE,
              "paired_clusters": len(paired), "registered_clusters": len(windows),
              "unpaired_clusters": len(groups) - len(paired), "incomplete_outcomes": incomplete,
              "summary": summary, "service_costs_reported_separately": not after_service,
              "independence": {"basis": d["independence_basis"], "note": "cluster count alone is not independence"},
              "primary_horizon_sessions": d["primary_horizon_sessions"],
              "promotion_authorized": False, "origin": d["origin"], "default": d["default"]}
    if len(paired) < d["minimum_clusters"] or len(paired) != len(windows):
        result["reason"] = "INSUFFICIENT_ALIGNED_REGISTERED_WINDOWS"
        return Document.from_dict(result)
    # One set of resampled clusters serves the paired and the absolute intervals (drawn in the same order as before,
    # so paired intervals are unchanged by IDEA-034).
    rng = random.Random(d["seed"])
    samples = [[rng.randrange(len(paired)) for _ in paired] for _ in range(d["bootstrap_draws"])]
    tail = Fraction(10000 - d["confidence_bps"], 20000)
    mean = lambda values: sum(values, Fraction(0)) / len(values)

    def interval(values):
        draws = sorted(mean([values[i] for i in sample]) for sample in samples)
        return draws[int(tail * len(draws))], draws[min(len(draws) - 1, int((1 - tail) * len(draws)))]

    low, high = interval(paired)
    absolute_low, absolute_high = interval(absolute)
    treatment_mean = mean(absolute)
    warnings = [] if treatment_mean > 0 else ["TREATMENT_ABSOLUTE_NET_NOT_POSITIVE"]
    if treatment_mean > 0 and not after_service and mean(serviced) <= 0:
        warnings.append("TREATMENT_NET_NOT_POSITIVE_AFTER_SERVICE_COSTS")
    if mean(baseline_absolute) <= 0:
        warnings.append("BASELINE_ABSOLUTE_NET_NOT_POSITIVE")
    result.update(paired_mean=ratio(mean(paired)), confidence_interval=[ratio(low), ratio(high)],
                  treatment_absolute_mean=ratio(treatment_mean),
                  treatment_absolute_interval=[ratio(absolute_low), ratio(absolute_high)],
                  baseline_absolute_mean=ratio(mean(baseline_absolute)), warnings=warnings)
    kill_bound = Fraction(0) if d["kill_rule"] == "UPPER_BOUND_BELOW_ZERO" else margin
    bounds_support = low > margin and absolute_low > 0
    if incomplete:
        result["reason"] = "INCOMPLETE_OUTCOMES_RETAINED"
    elif absolute_high <= 0:
        # Confidently does not make money: not worth adopting whatever the paired difference (IDEA-034).
        result.update(status="NOT_SUPPORTED", reason="TREATMENT_ABSOLUTE_NET_NOT_POSITIVE")
    elif bounds_support and mean(paired) > margin and treatment_mean > 0:
        result["status"] = "SUPPORTED"
    elif high < kill_bound:
        result["status"] = "NOT_SUPPORTED"
    elif bounds_support:
        # A bound beyond its own observed mean is a resampling artefact, not evidence (R26).
        result["reason"] = "BOOTSTRAP_INTERVAL_EXCLUDES_OBSERVED_MEAN"
    elif low > margin:
        result["reason"] = "TREATMENT_ABSOLUTE_LOWER_BOUND_NOT_POSITIVE"
    else:
        result["reason"] = "INTERVAL_SPANS_REGISTERED_RULES"
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
