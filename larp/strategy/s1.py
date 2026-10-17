"""S1: trend-guarded, volatility-weighted book (IDEA-076; the team's plan of 2026-10-16, IDEA-075 §4-§6, PR #123).

Pure functions, exact arithmetic, no I/O. Every value is a profile value: the IDEA-075 §12 numbers are proposals
until the Oct 22 freeze, and nothing here chooses them.

- Target gross = min(trend level, limiter level); the planner's declared loss ladder applies on top (3% daily and
  8% drawdown block buys; 12% cuts to 40%).
- Trend level (§4.1): an equal-weight basket index of the five names' session closes, compared with its own
  `trend_window_sessions` mean, with a dead band of `trend_band_bps`. UP -> high level, DOWN -> mid level. A missing,
  stale or already evaluated input leaves the state unchanged and says why.
- Limiter (§4.2): reduce-only. It moves to CAUTION (mid) or SEVERE (low) only on verified evidence whose class
  allows that cut, and returns to NORMAL after `llm_expiry_sessions` unless new evidence renews it. A model's output
  is accepted only if every evidence ID it cites is verified and inside the window; a scheduled event alone never
  lowers the level. In DETERMINISTIC mode the evidence-class map alone sets the level (no model call).
- Weights (§5.1): w ∝ 1/sigma of session log returns, capped at `weight_cap`, frozen into the profile at the
  parameter freeze (`freeze_weights`; `python -m larp.strategy.s1 freeze-weights`).
"""

from decimal import Decimal, localcontext
from fractions import Fraction

from larp.contracts import ContractError
from .schema import SYMBOLS, fraction, instant, integer, ratio

BASELINE = "TREND_GUARDED_VOL"
LEVELS = ("NORMAL", "CAUTION", "SEVERE")
SEVERITY = {level: rank for rank, level in enumerate(LEVELS)}
TREND_STATES = ("UP", "DOWN")
EVIDENCE_CLASSES = ("CLASS_2_RED_FLAG", "TRADE_RESTRICTION", "TRADING_SUSPENSION", "SCHEDULED_EVENT")
EVIDENCE_WINDOW_SESSIONS = 5
KEYS = frozenset({"levels", "weights", "weight_cap", "hard_name_weight", "top_up_band", "trend_window_sessions",
                  "trend_band_bps", "trend_delay_seconds", "trend_start_state", "llm_expiry_sessions",
                  "max_legs_per_symbol_session", "limiter_mode"})
MAX_GROSS = Fraction(19, 20)
MAX_WEIGHT_CAP = Fraction(3, 10)
MAX_HARD_NAME = Fraction(7, 20)


def _bounded(value, low, high, what):
    if type(value) is not int or not low <= value <= high:
        raise ContractError("s1." + what + " must be an integer in [" + str(low) + ", " + str(high) + "]")
    return value


def config(p):
    """The checked `s1` block of a TREND_GUARDED_VOL profile, with exact fractions (IDEA-076 S01)."""
    s = p.get("s1")
    if type(s) is not dict or set(s) != KEYS:
        raise ContractError("s1 block needs exactly: " + ",".join(sorted(KEYS)))
    levels = s["levels"]
    if type(levels) is not dict or set(levels) != {"high", "mid", "low"}:
        raise ContractError("s1.levels needs high, mid and low")
    high, mid, low = (fraction(levels[k]) for k in ("high", "mid", "low"))
    if not 0 < low < mid < high <= MAX_GROSS:
        raise ContractError("s1.levels must satisfy 0 < low < mid < high <= 95%")
    cap = fraction(s["weight_cap"])
    if not 0 < cap <= MAX_WEIGHT_CAP:
        raise ContractError("s1.weight_cap must be in (0, 30%]")
    weights = s["weights"]
    if type(weights) is not dict or set(weights) != SYMBOLS:
        raise ContractError("s1.weights must name exactly the five eligible symbols")
    weights = {symbol: fraction(w) for symbol, w in weights.items()}
    if any(not 0 < w <= cap for w in weights.values()) or sum(weights.values()) != 1:
        raise ContractError("s1.weights must be positive, at most the cap, and sum to exactly 1")
    hard = fraction(s["hard_name_weight"])
    if not high * cap <= hard <= MAX_HARD_NAME:
        raise ContractError("s1.hard_name_weight must be in [high level x weight cap, 35%]")
    band = fraction(s["top_up_band"])
    if not 0 < band <= Fraction(1, 10):
        raise ContractError("s1.top_up_band must be in (0, 10%]")
    if s["trend_start_state"] not in TREND_STATES:
        raise ContractError("s1.trend_start_state must be UP or DOWN")
    if s["limiter_mode"] not in ("DETERMINISTIC", "MODEL"):
        raise ContractError("s1.limiter_mode must be DETERMINISTIC or MODEL")
    return dict(high=high, mid=mid, low=low, cap=cap, weights=weights, hard=hard, band=band,
                window=_bounded(s["trend_window_sessions"], 2, 20, "trend_window_sessions"),
                band_bps=_bounded(s["trend_band_bps"], 1, 1000, "trend_band_bps"),
                delay=_bounded(s["trend_delay_seconds"], 0, 86400, "trend_delay_seconds"),
                start=s["trend_start_state"],
                expiry=_bounded(s["llm_expiry_sessions"], 1, 10, "llm_expiry_sessions"),
                legs=_bounded(s["max_legs_per_symbol_session"], 1, 5, "max_legs_per_symbol_session"),
                limiter_mode=s["limiter_mode"])


def level_fraction(cfg, trend_state, limiter_level):
    """Target gross = min(trend level, limiter level). NORMAL equals the high level, so it never raises exposure."""
    trend = cfg["high"] if trend_state == "UP" else cfg["mid"]
    limiter = {"NORMAL": cfg["high"], "CAUTION": cfg["mid"], "SEVERE": cfg["low"]}[limiter_level]
    return min(trend, limiter)


# --- session closes -------------------------------------------------------------------------------------------------

def _closes(series, *, cutoff, delay_seconds):
    """session_index -> close_units of one PriceSeries.v1, bars final `delay_seconds` after their close."""
    if (type(series) is not dict or series.get("schema") != "PriceSeries.v1"
            or series.get("instrument_kind") != "TOKEN" or series.get("quality") != "VALID"):
        return None
    closes = {}
    for bar in series.get("bars", []):
        try:
            if bar.get("quality") != "VALID" or bar.get("corporate_action_version") != series.get(
                    "corporate_action_version"):
                return None
            close_at, available_at = instant(bar["close_at"]), instant(bar["available_at"])
            sid, units = integer(bar["session_index"]), integer(bar["close_units"], 1)
        except (KeyError, TypeError, AttributeError, ContractError):
            return None
        if available_at < close_at:
            return None
        if (cutoff - close_at).total_seconds() < delay_seconds or available_at > cutoff:
            continue
        if sid in closes:
            return None
        closes[sid] = (units, close_at)
    return closes


def evaluate_trend(series, *, cutoff, cfg, previous_state, last_evaluated, max_age_seconds):
    """One trend evaluation (IDEA-076 S03/S04). Returns a record; `state` is the state to keep.

    `series` maps symbol -> PriceSeries.v1 dict. The state changes only on a fresh, complete window."""
    state = previous_state if previous_state in TREND_STATES else cfg["start"]
    record = dict(state=state, evaluated_session=last_evaluated, signal=None, basket=None)
    if type(series) is not dict or not series:
        return dict(record, status="TREND_INPUT_UNAVAILABLE")
    closes = {}
    for symbol in sorted(SYMBOLS):
        c = _closes(series.get(symbol), cutoff=cutoff, delay_seconds=cfg["delay"])
        if not c:
            return dict(record, status="TREND_INPUT_UNAVAILABLE", symbol=symbol)
        closes[symbol] = c
    latest = min(max(c) for c in closes.values())
    if any((cutoff - c[latest][1]).total_seconds() > max_age_seconds for c in closes.values() if latest in c):
        return dict(record, status="TREND_INPUT_STALE")
    if last_evaluated is not None and latest <= last_evaluated:
        return dict(record, status="ALREADY_EVALUATED")
    sessions = list(range(latest - cfg["window"] + 1, latest + 1))
    if any(s not in c for c in closes.values() for s in sessions):
        return dict(record, status="TREND_INPUT_MISSING", session=latest)
    index = [Fraction(1)]
    for previous, current in zip(sessions, sessions[1:]):
        returns = [Fraction(closes[s][current][0], closes[s][previous][0]) - 1 for s in sorted(SYMBOLS)]
        index.append(index[-1] * (1 + sum(returns) / len(returns)))
    signal = index[-1] / (sum(index) / len(index)) - 1
    band = Fraction(cfg["band_bps"], 10000)
    if signal > band:
        state = "UP"
    elif signal < -band:
        state = "DOWN"
    elif previous_state not in TREND_STATES:
        state = cfg["start"]
    return dict(state=state, evaluated_session=latest, signal=ratio(signal), basket=[ratio(v) for v in index],
                status="EVALUATED")


# --- limiter ---------------------------------------------------------------------------------------------------------

def _verified(evidence, session):
    """evidence_id -> item, for verified items of a known class inside the 5-session window."""
    result = {}
    for item in evidence if type(evidence) is list else ():
        try:
            if (type(item) is not dict or item.get("verified") is not True or item.get("class") not in EVIDENCE_CLASSES
                    or type(item.get("evidence_id")) is not str or not item["evidence_id"]
                    or type(item.get("symbols")) is not list or not set(item["symbols"]) <= SYMBOLS):
                continue
            sid = integer(item["session_index"])
        except (ContractError, KeyError):
            continue
        if session - EVIDENCE_WINDOW_SESSIONS < sid <= session and item["evidence_id"] not in result:
            result[item["evidence_id"]] = item
    return result


def allowed_severity(items):
    """The deepest cut a set of verified evidence allows (IDEA-075 §4.2 table)."""
    severity = 0
    class_2 = {s for i in items if i["class"] == "CLASS_2_RED_FLAG" for s in i["symbols"]}
    if len(class_2) >= 2:
        severity = max(severity, SEVERITY["CAUTION"])
    if any(i["class"] == "TRADE_RESTRICTION" and len(set(i["symbols"])) >= 2 for i in items):
        severity = max(severity, SEVERITY["CAUTION"])
    if any(i["class"] == "TRADING_SUSPENSION" and i["symbols"] for i in items):
        severity = max(severity, SEVERITY["SEVERE"])
    return severity


CUT_CLASSES = {SEVERITY["CAUTION"]: ("CLASS_2_RED_FLAG", "TRADE_RESTRICTION"),
               SEVERITY["SEVERE"]: ("TRADING_SUSPENSION",)}


def limiter_step(previous, *, session, cfg, evidence, assessment):
    """One limiter round (IDEA-076 L01-L08). Returns (new state, record). Never raises exposure early."""
    prev = previous if type(previous) is dict else {}
    level = prev.get("level", "NORMAL") if prev.get("level") in LEVELS else "NORMAL"
    expires = prev.get("expires_session")
    used = list(prev.get("used_evidence_ids", []))
    record = dict(previous_level=level, accepted=False, rejected=None, cited=[])
    if level != "NORMAL" and (type(expires) is not int or session >= expires):
        level, expires = "NORMAL", None
        record["expired"] = True
    verified = _verified(evidence, session)
    if cfg["limiter_mode"] == "DETERMINISTIC":
        cited = sorted(verified)
        proposed = allowed_severity(verified.values())
    elif assessment is None:
        cited, proposed = [], 0
        record["rejected"] = "NO_ASSESSMENT"
    else:
        ids = assessment.get("evidence_ids") if type(assessment) is dict else None
        if (type(assessment) is not dict or assessment.get("level") not in LEVELS or type(ids) is not list
                or any(type(i) is not str for i in ids) or type(assessment.get("reason")) is not str
                or type(assessment.get("falsifier")) is not str):
            cited, proposed = [], 0
            record["rejected"] = "MALFORMED_ASSESSMENT"
        elif any(i not in verified for i in ids):
            cited, proposed = [], 0
            record["rejected"] = "UNVERIFIED_OR_OUT_OF_WINDOW_EVIDENCE"
        else:
            cited = sorted(set(ids))
            proposed = min(SEVERITY[assessment["level"]], allowed_severity(verified[i] for i in cited))
            if proposed < SEVERITY[assessment["level"]]:
                record["capped_by_evidence_class"] = True
    # Only new evidence of a class that can give this cut accepts or renews it; a new calendar entry cannot.
    supporting = [i for i in cited if proposed > 0 and verified[i]["class"] in CUT_CLASSES[proposed]]
    fresh = sorted(set(supporting) - set(used))
    if proposed > 0 and fresh and proposed >= SEVERITY[level]:
        level, expires = LEVELS[proposed], session + cfg["expiry"]
        used = sorted(set(used) | set(cited))
        record.update(accepted=True, cited=cited)
    state = dict(level=level, expires_session=expires if level != "NORMAL" else None, used_evidence_ids=used)
    return state, dict(record, level=level, expires_session=state["expires_session"])


# --- weight freeze (§5.1) ---------------------------------------------------------------------------------------------

def _sigma(series, cutoff, window, minimum):
    closes = _closes(series, cutoff=cutoff, delay_seconds=0)
    if not closes:
        return None
    sids = sorted(closes)
    pairs = [(a, b) for a, b in zip(sids, sids[1:]) if b == a + 1][-window:]
    if len(pairs) < minimum:
        return None
    with localcontext() as ctx:
        ctx.prec = 50
        returns = [(Decimal(closes[b][0]) / Decimal(closes[a][0])).ln() for a, b in pairs]
        mean = sum(returns) / Decimal(len(returns))
        sigma = (sum((r - mean) ** 2 for r in returns) / Decimal(len(returns) - 1)).sqrt()
    return sigma if sigma > 0 else None


def freeze_weights(series, *, cutoff, cap, window=60, minimum=20, scale=1_000_000):
    """symbol -> Fraction weights, inverse-volatility, capped, summing exactly to 1 (IDEA-076 S02).

    A name with fewer than `minimum` consecutive-session returns takes the median sigma of the others."""
    cap = Fraction(cap)
    if not 0 < cap <= MAX_WEIGHT_CAP or cap * len(SYMBOLS) < 1:
        raise ContractError("Weight cap must allow the five weights to sum to 1")
    sigmas = {s: _sigma((series or {}).get(s), cutoff, window, minimum) for s in sorted(SYMBOLS)}
    known = sorted(v for v in sigmas.values() if v is not None)
    if not known:
        raise ContractError("No name has enough session history to freeze weights")
    median = known[len(known) // 2] if len(known) % 2 else (known[len(known) // 2 - 1] + known[len(known) // 2]) / 2
    substituted = sorted(s for s, v in sigmas.items() if v is None)
    with localcontext() as ctx:
        ctx.prec = 50
        inverse = {s: 1 / (v if v is not None else median) for s, v in sigmas.items()}
        capped, weights = set(), {}
        while True:
            free = [s for s in inverse if s not in capped]
            remaining = Decimal(1) - Decimal(cap.numerator) / Decimal(cap.denominator) * len(capped)
            total = sum(inverse[s] for s in free)
            weights = {s: (Decimal(cap.numerator) / Decimal(cap.denominator) if s in capped
                           else remaining * inverse[s] / total) for s in inverse}
            over = [s for s in free if weights[s] > Decimal(cap.numerator) / Decimal(cap.denominator)]
            if not over:
                break
            capped |= set(over)
        units = {s: int(weights[s] * scale) for s in weights}  # floor
        limit = cap * scale
        for s in sorted(weights, key=lambda s: (-(weights[s] * scale - units[s]), s)):
            if sum(units.values()) == scale:
                break
            if units[s] + 1 <= limit:
                units[s] += 1
    if sum(units.values()) != scale:
        raise ContractError("Weights could not be rounded within the cap")
    result = {s: Fraction(u, scale) for s, u in units.items()}
    return result, dict(sigmas={s: (str(v) if v is not None else None) for s, v in sigmas.items()},
                        substituted_median=substituted, window=window, minimum=minimum, cutoff=cutoff.isoformat())


def main(argv=None):
    """Freeze weights from saved PriceSeries.v1 files (one per symbol) for the profile's `s1.weights`."""
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=main.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze-weights")
    freeze.add_argument("--series-dir", required=True, help="directory of <SYMBOL>.json PriceSeries.v1 files")
    freeze.add_argument("--cutoff", required=True, help="UTC time of the last close to use (Oct 21 close)")
    freeze.add_argument("--cap", default="3/10")
    freeze.add_argument("--window", type=int, default=60)
    freeze.add_argument("--minimum", type=int, default=20)
    args = parser.parse_args(argv)
    directory = Path(args.series_dir)
    series = {s: json.loads((directory / (s + ".json")).read_text()) for s in sorted(SYMBOLS)
              if (directory / (s + ".json")).is_file()}
    weights, basis = freeze_weights(series, cutoff=instant(args.cutoff), cap=Fraction(args.cap),
                                    window=args.window, minimum=args.minimum)
    print(json.dumps(dict(weights={s: ratio(w) for s, w in weights.items()}, basis=basis), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
