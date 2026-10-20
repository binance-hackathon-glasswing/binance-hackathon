"""I6: build frozen LIVE profiles from measured costs, never trading P&L.

QuoteCostSummary.v1 is a proposed I1 input for Isaac's logger, not a fabricated
measurement. Publication of profile files awaits actual captures and owner review.
"""

from fractions import Fraction
import hashlib
import json
from larp.intelligence.redflags import CONFIG as PREDICATE_CONFIG

from larp.contracts import ContractError, Document
from .schema import AUTHORITY_KEYS, SYMBOLS, ceil, execution_authority, fraction, instant, integer
from .predicates import predicate_records

WINDOWS = {
    "REHEARSAL": ("2026-10-21T00:00:00Z", "2026-10-22T00:00:00Z",
                  "2026-10-23T00:00:00Z", "2026-10-26T14:45:00Z"),
    "FINAL": ("2026-10-29T00:00:00Z", "2026-11-09T00:00:00Z",
              "2026-11-10T00:00:00Z", "2026-11-11T14:45:00Z"),
}


EQUAL_WEIGHT_KEYS = ("operating_name_weight", "operating_gross_weight", "regime_gross_weight", "rebalance_band",
                     "top_up_below_gross_weight", "hard_name_weight", "hard_gross_weight")


def _hash(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def quote_summary(summary):
    try:
        return _quote_summary(summary)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ContractError("Malformed measured quote-cost summary") from exc


def _quote_summary(summary):
    if (summary.get("schema") != "QuoteCostSummary.v1" or summary.get("origin") != "RECORDED_WEB3"
            or not _hash(summary.get("capture_hash")) or set(summary.get("symbols", {})) != SYMBOLS
            or any("pnl" in k.lower() or "profit" in k.lower() for k in summary)):
        raise ContractError("Complete measured quote-cost summary required; no P&L inputs")
    instant(summary["observed_at"])
    integer(summary["bnb_price_units"], 1)
    integer(summary["bnb_decimals"], 1)
    if summary["bnb_decimals"] > 30:
        raise ContractError("Unsupported BNB decimals")
    for row in summary["symbols"].values():
        integer(row["samples"], 1)
        for field in ("median_impact_bps", "spread_bps", "fee_bps"):
            integer(row[field], 1 if field == "median_impact_bps" else 0)
        for field in ("approve_gas_bnb_units", "swap_gas_bnb_units", "slippage_bps", "quote_ttl_seconds"):
            integer(row[field], 1)
        if row["spread_bps"] + min(50, 2 * row["median_impact_bps"]) + row["fee_bps"] >= 50:
            raise ContractError("Measured costs leave no positive gas budget under 50 bp")
    return summary


def validate_live(p):
    try:
        if p.get("values_origin") != "MEASURED_AND_DECIDED" or p.get("environment") not in WINDOWS:
            raise ContractError("LIVE values must be measured and decided")
        provenance = p.get("provenance")
        if type(provenance) is not dict:
            raise ContractError("Per-value provenance required")
        for key, value in p.items():
            if key in ("schema", "mode", "values_origin", "provenance"):
                continue
            proof = provenance.get(key)
            if value is None or type(proof) is not dict or not proof.get("decision_id"):
                raise ContractError("Unset/unsourced live value: " + key)
            if not proof.get("formula") and not _hash(proof.get("data_hash")):
                raise ContractError("Formula or measured hash required: " + key)
            if "data_hash" in proof and not _hash(proof["data_hash"]):
                raise ContractError("Invalid source hash: " + key)
        s1 = p.get("baseline") == "TREND_GUARDED_VOL"
        required = ("minimum_trade_units", "per_trade_cap_units", "cost_reserve_units",
                    "exit_gas_reserve_units", "dust_units", "quote_age_seconds", "feature_age_seconds",
                    "proposal_seconds", "slippage_bps", "impact_bps", "price_threshold_bps",
                    "review_sessions", "minimum_remaining_sessions", "trade_after", "new_risk_end",
                    "flatten_start", "signing_end", "baseline",
                    *(("s1",) if s1 else EQUAL_WEIGHT_KEYS),
                    "policy_id", "evidence_mode", "falsifier_authority", "statement_authority",
                    "falsifier_ids", "assessment_required", "evidence_max_age_ms", "environment",
                    "expected_equity_units", "impact_median_bps", "series_kind", "red_flag_policy",
                    "predicate_registry_hash", "gas_floor_bnb_units", "gas_top_up_cash_units",
                    "gas_top_up_min_receive_units", "gas_top_up_max_gas_bnb_units", "quote_cost_summary")
        if any(key not in p for key in required):
            raise ContractError("Missing required live value")
        summary = quote_summary(p["quote_cost_summary"])
        for field in ("expected_equity_units", "gas_floor_bnb_units", "gas_top_up_cash_units",
                      "gas_top_up_min_receive_units", "gas_top_up_max_gas_bnb_units"):
            integer(p[field], 1)
        if (p["baseline"] not in ("EQUAL_WEIGHT", "TREND_GUARDED_VOL") or p["series_kind"] != "TOKEN"
                or p["red_flag_policy"] != "IDEA-035-B1" or not _hash(p["predicate_registry_hash"])
                or p["statement_authority"] != "SHADOW"
                or p["falsifier_authority"] != "DISCRETIONARY_EXIT"
                or p["assessment_required"] is not False):
            raise ContractError("Live profile differs from decided v1 scope")
        # IDEA-035/037 fix these values; provenance alone cannot adopt a new policy.
        # A separate stress budget may still tighten regime_gross_weight.
        decided_weights = {"operating_name_weight": Fraction(1, 5),
                           "operating_gross_weight": Fraction(4, 5),
                           "hard_name_weight": Fraction(1, 4),
                           "hard_gross_weight": Fraction(9, 10),
                           "top_up_below_gross_weight": Fraction(3, 4)}
        if s1:
            # IDEA-076: the S1 block carries its own levels and weights; one full top position per trade.
            from .s1 import config
            cfg = config(p)
            top = p["expected_equity_units"] * cfg["high"] * max(cfg["weights"].values())
            smallest = p["expected_equity_units"] * cfg["high"] * min(cfg["weights"].values())
            if p["per_trade_cap_units"] < ceil(top) + p["cost_reserve_units"]:
                raise ContractError("Per-trade cap cannot complete a full top-level position")
        elif any(fraction(p[key]) != expected for key, expected in decided_weights.items()):
            raise ContractError("Live allocation thresholds differ from IDEA-035/037 decisions")
        elif p["per_trade_cap_units"] < ceil(Fraction(p["expected_equity_units"], 5)) + p["cost_reserve_units"]:
            raise ContractError("Per-trade cap cannot complete a full 20% position")
        if not 0 < p["slippage_bps"] <= 50 or not 0 < p["quote_age_seconds"] <= 30:
            raise ContractError("Unbounded live slippage/freshness")
        if not 0 <= p["impact_bps"] <= 50 or p["feature_age_seconds"] <= 0:
            raise ContractError("Unbounded live impact/feature freshness")
        if set(p["impact_median_bps"]) != SYMBOLS or any(
                p["impact_median_bps"][s] != summary["symbols"][s]["median_impact_bps"] for s in SYMBOLS):
            raise ContractError("Impact medians must match measured summary")
        if instant(summary["observed_at"]) > instant(p["trade_after"]):
            raise ContractError("Future quote measurements")
        pair = max(r["approve_gas_bnb_units"] + r["swap_gas_bnb_units"] for r in summary["symbols"].values())
        gas_value = ceil(Fraction(pair * summary["bnb_price_units"], 10**summary["bnb_decimals"]))
        minimum = max(ceil(Fraction(gas_value * 10000,
            50 - row["spread_bps"] - min(50, 2 * row["median_impact_bps"]) - row["fee_bps"]))
            for row in summary["symbols"].values())
        largest_minimum = int(smallest) if s1 else p["expected_equity_units"] // 5
        if not minimum <= p["minimum_trade_units"] <= largest_minimum:
            raise ContractError("Live minimum does not satisfy measured costs/full-position feasibility")
        if p["exit_gas_reserve_units"] < (5 if s1 else 4) * pair:
            raise ContractError("Insufficient exit gas reserve for every position")
        if p["gas_floor_bnb_units"] < pair or p["gas_top_up_min_receive_units"] <= p["gas_floor_bnb_units"]:
            raise ContractError("Insufficient two-transaction gas floor/top-up size")
        if p["gas_top_up_max_gas_bnb_units"] > p["gas_floor_bnb_units"]:
            raise ContractError("Top-up cannot be paid below trigger floor")
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("Malformed or incomplete live profile") from exc


def build_live_profiles(summary: Document, registry: Document, *, s1=None,
                        s1_decision="IDEA-075 S1 plan (PR #123), proposed", authority=None):
    """Return rehearsal/final candidate profiles; caller freezes hashes in manifest.

    Conservative budgets are algebraic policy choices requiring Yao/team review.
    This function neither runs a market experiment nor grants signer authority.
    With `s1` (the profile's `s1` block, weights frozen by `python -m larp.strategy.s1 freeze-weights`), the
    profiles are TREND_GUARDED_VOL (IDEA-076); `s1_decision` names the decision behind those values.
    With `authority` = {seconds, margin, decision_id, data_hash}, both profiles also carry the #27 finite execution
    authority L and submission margin m (IDEA-049-C LD04-V01/LD04-P); without it the output is unchanged.
    """
    if authority is not None:
        if (type(authority) is not dict or set(authority) != {"seconds", "margin", "decision_id", "data_hash"}
                or type(authority["decision_id"]) is not str or not authority["decision_id"].strip()
                or not _hash(authority["data_hash"])):
            raise ContractError("Execution authority needs seconds, margin, a decision ID and an evidence hash")
    s, reg = quote_summary(summary.read()), registry.read()
    published = reg.get("schema") == "RedFlagPredicateSet.v1"
    if published:
        from larp.integration.contract import red_flag_predicates
        records, set_sha = red_flag_predicates()
        if reg != json.loads(PREDICATE_CONFIG.read_text()):
            raise ContractError("Published predicate set differs from this build")
    else:
        records = predicate_records(reg)
    pairs = [r["approve_gas_bnb_units"] + r["swap_gas_bnb_units"] for r in s["symbols"].values()]
    pair = max(pairs)
    gas_value = ceil(Fraction(pair * s["bnb_price_units"], 10**s["bnb_decimals"]))
    impact = {name: r["median_impact_bps"] for name, r in s["symbols"].items()}
    minimum = max(ceil(Fraction(gas_value * 10000,
        50 - r["spread_bps"] - min(50, 2 * r["median_impact_bps"]) - r["fee_bps"]))
        for r in s["symbols"].values())
    # Four exits plus a top-up and next entry, each approve+swap; no single-tx assumption.
    floor_bnb = pair * 6
    top_up_receive = floor_bnb * 2
    top_up_cash = ceil(Fraction(top_up_receive * s["bnb_price_units"], 10**s["bnb_decimals"]))
    top_up_cash = ceil(Fraction(top_up_cash * 10000, 9950))
    base = {"schema": "StrategyProfile.v1", "mode": "LIVE", "values_origin": "MEASURED_AND_DECIDED",
        "baseline": "EQUAL_WEIGHT", "evidence_mode": "BOUNDED_FALSIFIER",
        "falsifier_authority": "DISCRETIONARY_EXIT", "statement_authority": "SHADOW",
        "falsifier_ids": sorted(records), "assessment_required": False, "evidence_max_age_ms": 3_600_000,
        "red_flag_policy": "IDEA-035-B1", "predicate_registry_hash": registry.digest("RedFlagRegistry.v1"),
        "operating_name_weight": [1, 5], "operating_gross_weight": [4, 5], "regime_gross_weight": [4, 5],
        "hard_name_weight": [1, 4], "hard_gross_weight": [9, 10], "top_up_below_gross_weight": [3, 4],
        "rebalance_band": [0, 1], "minimum_trade_units": minimum,
        "exit_gas_reserve_units": pair * 4, "dust_units": 0,
        "quote_age_seconds": min(30, min(r["quote_ttl_seconds"] for r in s["symbols"].values())),
        "feature_age_seconds": 4 * 86400, "proposal_seconds": 15,
        "slippage_bps": min(50, max(r["slippage_bps"] for r in s["symbols"].values())),
        "impact_bps": min(50, max(2 * v for v in impact.values())), "impact_median_bps": impact,
        "price_threshold_bps": 0, "review_sessions": 5, "minimum_remaining_sessions": 0,
        "series_kind": "TOKEN", "gas_floor_bnb_units": floor_bnb, "gas_top_up_cash_units": top_up_cash,
        "gas_top_up_min_receive_units": top_up_receive, "gas_top_up_max_gas_bnb_units": pair,
        "quote_cost_summary": s}
    if published:
        base["red_flag_authority"] = {"set_sha256": set_sha, "enabled": sorted(
            pid for pid, r in records.items() if r["class"] in (1, 2))}
        base["falsifier_ids"] = ["F-ITEM-" + r["trigger"]["item"] for r in records.values() if r["class"] in (1, 2)]
    cfg = None
    if s1 is not None:
        from .s1 import BASELINE, config
        cfg = config({"s1": s1})
        for key in EQUAL_WEIGHT_KEYS:
            base.pop(key)
        base.update(baseline=BASELINE, s1=s1, exit_gas_reserve_units=pair * 5)
    profiles = {}
    for env, window in WINDOWS.items():
        capital = 100_000_000 if env == "REHEARSAL" else 200_000_000
        reserve = ceil(Fraction(capital, 1000))
        top = ceil(capital * cfg["high"] * max(cfg["weights"].values())) if cfg else capital // 5
        p = {**base, "environment": env, "expected_equity_units": capital,
             "policy_id": ("larp-s1-" if cfg else "larp-equal-weight-") + env.lower() + "-v1",
             "cost_reserve_units": reserve, "per_trade_cap_units": top + reserve,
             **dict(zip(("trade_after", "new_risk_end", "flatten_start", "signing_end"), window))}
        smallest = int(capital * cfg["high"] * min(cfg["weights"].values())) if cfg else capital // 5
        if minimum > smallest:
            raise ContractError("Measured minimum cannot fit a full position at " + env)
        p["proposal_seconds"] = min(15, p["quote_age_seconds"])
        p["provenance"] = {key: {"decision_id": "IDEA-035 B6 / IDEA-037 / IDEA-040",
            "data_hash": summary.digest("QuoteCostSummary.v1"),
            "formula": "Frozen B6 policy budget; see config/strategy/LIVE.md and IDEA-040"}
            for key in p if key not in ("schema", "mode", "values_origin")}
        for key in ("red_flag_policy", "predicate_registry_hash", "falsifier_ids"):
            p["provenance"][key] = {"decision_id": "IDEA-035 B1", "data_hash": registry.digest("RedFlagRegistry.v1")}
        if cfg:
            for key in ("baseline", "s1", "policy_id"):
                p["provenance"][key] = {"decision_id": s1_decision,
                                        "formula": "IDEA-075 §4-§5, §12 values; weights from s1 freeze-weights"}
        formulas = {"minimum_trade_units": "max_symbol ceil(10000*pair_gas_value/(50-spread-min(50,2*median_impact)-fee_bp))",
            "cost_reserve_units": "ceil(expected_equity_units/1000): 50 bp of 20% position",
            "per_trade_cap_units": ("ceil(expected_equity_units*s1.high*max(s1.weights)) + cost_reserve_units" if cfg
                                    else "expected_equity_units/5 + cost_reserve_units"),
            "gas_floor_bnb_units": "6*max_symbol(approve_gas_bnb_units+swap_gas_bnb_units)",
            "exit_gas_reserve_units": ("5" if cfg else "4") + "*max_symbol(approve_gas_bnb_units+swap_gas_bnb_units)",
            "gas_top_up_min_receive_units": "2*gas_floor_bnb_units",
            "gas_top_up_cash_units": "ceil(ceil(min_receive_bnb*bnb_price/10**bnb_decimals)/0.995)",
            "gas_top_up_max_gas_bnb_units": "max_symbol(approve_gas_bnb_units+swap_gas_bnb_units)",
            "quote_age_seconds": "min(30,min_symbol quote_ttl_seconds)",
            "slippage_bps": "min(50,max_symbol measured_slippage_bps)",
            "impact_bps": "min(50,max_symbol(2*median_impact_bps))",
            "impact_median_bps": "measured median per symbol in pinned quote summary",
            "proposal_seconds": "min(15,quote_age_seconds)",
            "feature_age_seconds": "4*86400; calendar adjacency separately required"}
        for key, formula in formulas.items():
            p["provenance"][key]["formula"] = formula
        if authority is not None:
            p["execution_authority_seconds"], p["submission_margin_seconds"] = authority["seconds"], authority["margin"]
            for key in AUTHORITY_KEYS:
                p["provenance"][key] = {"decision_id": authority["decision_id"], "data_hash": authority["data_hash"]}
            if execution_authority(p) != (authority["seconds"], authority["margin"]):
                raise ContractError("Execution authority was not adopted as given")
        validate_live(p)
        profiles[env] = Document.from_dict(p)
    return profiles


def main(argv=None):
    """Offline profile construction from caller-owned recorded inputs (no ports)."""
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--predicates", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--s1-config", help="JSON s1 block with reviewed/frozen weights; default is EQUAL_WEIGHT")
    parser.add_argument("--s1-decision", help="decision ID for the supplied S1 block; required with --s1-config")
    parser.add_argument("--execution-authority-seconds", type=int, help="#27 L; all four authority flags together")
    parser.add_argument("--submission-margin-seconds", type=int, help="#27 m")
    parser.add_argument("--authority-decision", help="decision ID behind L and m")
    parser.add_argument("--authority-evidence", help="evidence file whose SHA-256 becomes the provenance data_hash")
    args = parser.parse_args(argv)
    flags = (args.execution_authority_seconds, args.submission_margin_seconds, args.authority_decision,
             args.authority_evidence)
    if any(f is not None for f in flags) and not all(f is not None for f in flags):
        parser.error("--execution-authority-seconds, --submission-margin-seconds, --authority-decision and "
                     "--authority-evidence must be supplied together")
    authority = None if flags[0] is None else dict(
        seconds=args.execution_authority_seconds, margin=args.submission_margin_seconds,
        decision_id=args.authority_decision,
        data_hash=hashlib.sha256(Path(args.authority_evidence).read_bytes()).hexdigest())
    if bool(args.s1_config) != bool(args.s1_decision):
        parser.error("--s1-config and --s1-decision must be supplied together")
    if args.s1_decision is not None and not args.s1_decision.strip():
        parser.error("--s1-decision must name a decision")
    raw_s1 = Path(args.s1_config).read_bytes() if args.s1_config else None
    s1_block = json.loads(raw_s1) if raw_s1 is not None else None
    if raw_s1 is not None and type(s1_block) is not dict:
        raise ContractError("S1 configuration must be a JSON object")
    profiles = build_live_profiles(Document.from_dict(json.loads(Path(args.summary).read_text())),
                                   Document.from_dict(json.loads(Path(args.predicates).read_text())),
                                   authority=authority,
                                   **(dict(s1=s1_block, s1_decision=args.s1_decision) if raw_s1 is not None else {}))
    if raw_s1 is not None:
        for env, document in profiles.items():
            profile_data = document.read()
            profile_data["provenance"]["s1"]["data_hash"] = hashlib.sha256(raw_s1).hexdigest()
            profiles[env] = Document.from_dict(profile_data)
    out = Path(args.output_dir)
    paths = {env: out / (env.lower() + "-live.json") for env in profiles}
    if any(path.exists() for path in paths.values()):
        raise ContractError("Refusing to overwrite a frozen profile; choose a new output directory")
    out.mkdir(parents=True, exist_ok=True)
    for env, profile_doc in profiles.items():
        paths[env].write_bytes(profile_doc.payload + b"\n")
        print(env, profile_doc.digest("StrategyProfile.v1"))


if __name__ == "__main__":
    main()
