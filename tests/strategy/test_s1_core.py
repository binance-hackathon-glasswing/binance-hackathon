"""IDEA-076 S01-S04, L01-L09: the S1 profile block, weight freeze, trend guard and limiter. Synthetic data only."""
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import unittest

from larp.contracts import ContractError
from larp.strategy import s1
from larp.strategy.schema import SYMBOLS

NAMES = sorted(SYMBOLS)
T0 = datetime(2026, 10, 1, 20, 0, tzinfo=timezone.utc)


def block(**changes):
    value = dict(levels=dict(high=[19, 20], mid=[3, 5], low=[3, 10]),
                 weights={s: [1, 5] for s in NAMES}, weight_cap=[3, 10], hard_name_weight=[7, 20],
                 top_up_band=[1, 20], trend_window_sessions=5, trend_band_bps=100, trend_delay_seconds=900,
                 trend_start_state="UP", llm_expiry_sessions=3, max_legs_per_symbol_session=3,
                 limiter_mode="DETERMINISTIC")
    value.update(changes)
    return value


def cfg(**changes):
    return s1.config(dict(s1=block(**changes)))


def series(closes_by_session, symbol="NVDAB"):
    """PriceSeries.v1 with one bar per session index; session k closes at T0 + k days."""
    return dict(schema="PriceSeries.v1", instrument_kind="TOKEN", quality="VALID", symbol=symbol,
                corporate_action_version="v1",
                bars=[dict(session_index=k, close_units=c, close_at=(T0 + timedelta(days=k)).isoformat(),
                           available_at=(T0 + timedelta(days=k, seconds=1)).isoformat(),
                           corporate_action_version="v1", quality="VALID")
                      for k, c in sorted(closes_by_session.items())])


def basket(path, sessions=range(10)):
    """All five names follow the same close path (index = path)."""
    return {s: series({k: path[k] for k in sessions}, s) for s in NAMES}


def after(session, minutes=30):
    return T0 + timedelta(days=session, minutes=minutes)


class ProfileBlock(unittest.TestCase):  # S01
    def test_valid_block(self):
        c = cfg()
        self.assertEqual((c["high"], c["mid"], c["low"]), (Fraction(19, 20), Fraction(3, 5), Fraction(3, 10)))
        self.assertEqual(sum(c["weights"].values()), 1)

    def test_defects_are_refused(self):
        weights = {s: [1, 5] for s in NAMES}
        cases = {
            'missing key': {k: v for k, v in block().items() if k != 'top_up_band'},
            'high above 95%': block(levels=dict(high=[24, 25], mid=[3, 5], low=[3, 10])),
            'mid not below high': block(levels=dict(high=[3, 5], mid=[3, 5], low=[3, 10])),
            'cap above 30%': block(weight_cap=[2, 5]),
            'weights sum': block(weights=dict(weights, NVDAB=[1, 4])),
            'weight above cap': block(weights={**{s: [7, 40] for s in NAMES[:4]}, NAMES[4]: [3, 10]},
                                      weight_cap=[1, 4]),
            'four names': block(weights={s: [1, 4] for s in NAMES[:4]}),
            'hard line above 35%': block(hard_name_weight=[2, 5]),
            'hard line below top position': block(hard_name_weight=[1, 4]),
            'band zero': block(top_up_band=[0, 1]),
            'band wide': block(top_up_band=[1, 5]),
            'window': block(trend_window_sessions=1),
            'trend band bps': block(trend_band_bps=0),
            'expiry': block(llm_expiry_sessions=0),
            'legs': block(max_legs_per_symbol_session=6),
            'start state': block(trend_start_state='FLAT'),
            'limiter mode': block(limiter_mode='AUTO'),
            'bool window': block(trend_window_sessions=True),
        }
        for name, value in cases.items():
            with self.subTest(name), self.assertRaises(ContractError):
                s1.config(dict(s1=value))

    def test_level_fraction_is_the_minimum(self):
        c = cfg()
        self.assertEqual(s1.level_fraction(c, "UP", "NORMAL"), Fraction(19, 20))
        self.assertEqual(s1.level_fraction(c, "DOWN", "NORMAL"), Fraction(3, 5))
        self.assertEqual(s1.level_fraction(c, "UP", "CAUTION"), Fraction(3, 5))
        self.assertEqual(s1.level_fraction(c, "DOWN", "SEVERE"), Fraction(3, 10))


class WeightFreeze(unittest.TestCase):  # S02
    def make(self, vol):
        """Alternating returns of +/- vol give a known sigma ordering."""
        closes, price = {}, 10**6
        for k in range(70):
            closes[k] = price
            price = int(price * (1 + (vol if k % 2 else -vol)))
        return closes

    def test_inverse_volatility_capped_and_exact(self):
        vols = dict(zip(NAMES, (0.01, 0.02, 0.03, 0.04, 0.05)))
        data = {s: series(self.make(v), s) for s, v in vols.items()}
        weights, basis = s1.freeze_weights(data, cutoff=after(80), cap=Fraction(3, 10))
        self.assertEqual(sum(weights.values()), 1)
        self.assertTrue(all(w <= Fraction(3, 10) for w in weights.values()))
        ordered = [weights[s] for s in NAMES]
        self.assertEqual(ordered[0], Fraction(3, 10))  # the calmest name is capped
        self.assertTrue(all(a >= b for a, b in zip(ordered, ordered[1:])))
        again, _ = s1.freeze_weights(data, cutoff=after(80), cap=Fraction(3, 10))
        self.assertEqual(weights, again)
        self.assertEqual(basis["substituted_median"], [])

    def test_short_history_takes_the_median_sigma(self):
        data = {s: series(self.make(0.02), s) for s in NAMES}
        data[NAMES[0]] = series({k: 10**6 + k for k in range(5)}, NAMES[0])
        weights, basis = s1.freeze_weights(data, cutoff=after(80), cap=Fraction(3, 10))
        self.assertEqual(basis["substituted_median"], [NAMES[0]])
        self.assertEqual(sum(weights.values()), 1)

    def test_no_history_is_refused(self):
        with self.assertRaises(ContractError):
            s1.freeze_weights({}, cutoff=after(80), cap=Fraction(3, 10))

    def test_cutoff_excludes_later_bars(self):
        data = {s: series(self.make(0.01 * (i + 1)), s) for i, s in enumerate(NAMES)}
        early, _ = s1.freeze_weights(data, cutoff=after(30), cap=Fraction(3, 10))
        late, _ = s1.freeze_weights(data, cutoff=after(80), cap=Fraction(3, 10))
        self.assertEqual(sum(early.values()), sum(late.values()))


class Trend(unittest.TestCase):  # S03, S04
    def evaluate(self, path, at, previous=None, last=None, **changes):
        return s1.evaluate_trend(basket(path), cutoff=after(at), cfg=cfg(**changes), previous_state=previous,
                                 last_evaluated=last, max_age_seconds=4 * 86400)

    def test_rising_basket_is_up_and_falling_is_down(self):
        rising = [100 + 2 * k for k in range(10)]
        falling = [100 - 2 * k for k in range(10)]
        self.assertEqual(self.evaluate(rising, 9, previous="DOWN")["state"], "UP")
        self.assertEqual(self.evaluate(falling, 9, previous="UP")["state"], "DOWN")

    def test_signal_is_index_over_its_window_mean(self):
        path = [100, 100, 100, 100, 100, 100, 100, 100, 100, 110]
        result = self.evaluate(path, 9)
        # Index over sessions 5..9: 1,1,1,1,1.1 -> mean 1.02 -> r = 1.1/1.02 - 1
        self.assertEqual(Fraction(*result["signal"]), Fraction(11, 10) / Fraction(102, 100) - 1)
        self.assertEqual(result["evaluated_session"], 9)

    def test_dead_band_holds_and_first_start_is_up(self):
        flat = [100] * 10
        self.assertEqual(self.evaluate(flat, 9, previous="DOWN")["state"], "DOWN")
        self.assertEqual(self.evaluate(flat, 9, previous="UP")["state"], "UP")
        self.assertEqual(self.evaluate(flat, 9)["state"], "UP")
        self.assertEqual(self.evaluate(flat, 9, trend_start_state="DOWN")["state"], "DOWN")

    def test_each_session_is_evaluated_once(self):
        falling = [100 - 2 * k for k in range(10)]
        result = self.evaluate(falling, 9, previous="UP", last=9)
        self.assertEqual((result["state"], result["status"]), ("UP", "ALREADY_EVALUATED"))

    def test_bar_is_final_only_after_the_delay(self):
        falling = [100 - 2 * k for k in range(10)]
        early = self.evaluate(falling, 9, previous="UP", last=8, trend_delay_seconds=3600)
        self.assertEqual(early["status"], "ALREADY_EVALUATED")  # session 9's bar is 30 min old, delay 60 min

    def test_missing_stale_or_absent_inputs_hold_the_state(self):
        falling = [100 - 2 * k for k in range(10)]
        gap = basket(falling, sessions=[0, 1, 2, 3, 4, 5, 7, 8, 9])
        result = s1.evaluate_trend(gap, cutoff=after(9), cfg=cfg(), previous_state="UP", last_evaluated=None,
                                   max_age_seconds=4 * 86400)
        self.assertEqual((result["state"], result["status"]), ("UP", "TREND_INPUT_MISSING"))
        stale = self.evaluate(falling, 20, previous="UP")
        self.assertEqual((stale["state"], stale["status"]), ("UP", "TREND_INPUT_STALE"))
        partial = basket(falling)
        partial.pop(NAMES[2])
        result = s1.evaluate_trend(partial, cutoff=after(9), cfg=cfg(), previous_state="UP", last_evaluated=None,
                                   max_age_seconds=4 * 86400)
        self.assertEqual((result["state"], result["status"]), ("UP", "TREND_INPUT_UNAVAILABLE"))
        none = s1.evaluate_trend({}, cutoff=after(9), cfg=cfg(), previous_state=None, last_evaluated=None,
                                 max_age_seconds=4 * 86400)
        self.assertEqual((none["state"], none["status"]), ("UP", "TREND_INPUT_UNAVAILABLE"))  # S04

    def test_a_bad_bar_makes_the_input_unavailable(self):
        data = basket([100 - 2 * k for k in range(10)])
        data[NAMES[0]]["bars"][3]["quality"] = "SUSPECT"
        result = s1.evaluate_trend(data, cutoff=after(9), cfg=cfg(), previous_state="UP", last_evaluated=None,
                                   max_age_seconds=4 * 86400)
        self.assertEqual(result["status"], "TREND_INPUT_UNAVAILABLE")


def evidence(eid, cls, symbols, session, verified=True):
    return dict(evidence_id=eid, verified=verified, session_index=session, symbols=symbols, **{"class": cls})


class Limiter(unittest.TestCase):  # L01-L09
    def step(self, previous=None, *, session=10, items=(), assessment=None, mode="MODEL"):
        return s1.limiter_step(previous, session=session, cfg=cfg(limiter_mode=mode), evidence=list(items),
                               assessment=assessment)

    def assess(self, level, ids):
        return dict(level=level, evidence_ids=ids, reason="synthetic", falsifier="synthetic")

    def two_class_2(self, session=10):
        return [evidence("e1", "CLASS_2_RED_FLAG", ["NVDAB"], session),
                evidence("e2", "CLASS_2_RED_FLAG", ["MSFTB"], session)]

    def test_l01_unverified_or_missing_evidence_is_rejected(self):
        caution, _ = self.step(items=self.two_class_2(), assessment=self.assess("CAUTION", ["e1", "e2"]))
        for items, ids in ((self.two_class_2(), ["e1", "missing"]),
                           ([evidence("e1", "CLASS_2_RED_FLAG", ["NVDAB"], 10, verified=False)], ["e1"]),
                           (self.two_class_2(session=2), ["e1", "e2"])):
            state, record = self.step(caution, session=11, items=items, assessment=self.assess("SEVERE", ids))
            self.assertEqual(state["level"], "CAUTION")
            self.assertFalse(record["accepted"])
            self.assertIsNotNone(record["rejected"])

    def test_l02_accepted_caution_sets_the_mid_level(self):
        state, record = self.step(items=self.two_class_2(), assessment=self.assess("CAUTION", ["e1", "e2"]))
        self.assertTrue(record["accepted"])
        self.assertEqual(s1.level_fraction(cfg(), "UP", state["level"]), Fraction(3, 5))

    def test_l03_normal_never_raises_above_the_trend_level(self):
        state, _ = self.step(assessment=self.assess("NORMAL", []))
        self.assertEqual(s1.level_fraction(cfg(), "DOWN", state["level"]), Fraction(3, 5))
        caution, _ = self.step(items=self.two_class_2(), assessment=self.assess("CAUTION", ["e1", "e2"]))
        still, _ = self.step(caution, session=11, assessment=self.assess("NORMAL", []))
        self.assertEqual(still["level"], "CAUTION")  # no early lift

    def test_l04_caution_expires_without_renewal(self):
        # Expiry counts healthy sessions (L09): here sessions 12, 13 and 14 each have a well-formed assessment.
        caution, _ = self.step(items=self.two_class_2(), assessment=self.assess("CAUTION", ["e1", "e2"]))
        same, _ = self.step(caution, session=12, items=self.two_class_2(), assessment=self.assess("CAUTION", ["e1", "e2"]))
        self.assertEqual((same["level"], same["healthy_sessions"]), ("CAUTION", 1))  # old evidence does not renew
        still, _ = self.step(same, session=13, items=self.two_class_2(), assessment=self.assess("NORMAL", []))
        self.assertEqual((still["level"], still["healthy_sessions"]), ("CAUTION", 2))
        expired, record = self.step(still, session=14, items=self.two_class_2(), assessment=self.assess("NORMAL", []))
        self.assertEqual(expired["level"], "NORMAL")
        self.assertTrue(record["expired"])
        renewed, record = self.step(same, session=13, items=self.two_class_2() + [
            evidence("e3", "CLASS_2_RED_FLAG", ["TSLAB"], 13)], assessment=self.assess("CAUTION", ["e1", "e3"]))
        self.assertTrue(record["accepted"])
        self.assertEqual((renewed["healthy_sessions"], renewed["counted_session"]), (0, 13))

    def test_l05_model_outage_keeps_the_level(self):
        # Superseded "until expiry" by L09: sessions without a usable output do not count toward expiry.
        caution, _ = self.step(items=self.two_class_2(), assessment=self.assess("CAUTION", ["e1", "e2"]))
        kept, record = self.step(caution, session=11, assessment=None)
        self.assertEqual((kept["level"], record["rejected"], record["healthy"]), ("CAUTION", "NO_ASSESSMENT", False))
        still, _ = self.step(kept, session=13, assessment=None)
        self.assertEqual((still["level"], still["healthy_sessions"]), ("CAUTION", 0))

    def test_l06_severe_on_caution_evidence_is_capped(self):
        state, record = self.step(items=self.two_class_2(), assessment=self.assess("SEVERE", ["e1", "e2"]))
        self.assertEqual(state["level"], "CAUTION")
        self.assertTrue(record["capped_by_evidence_class"])
        one, _ = self.step(items=self.two_class_2()[:1], assessment=self.assess("CAUTION", ["e1"]))
        self.assertEqual(one["level"], "NORMAL")  # one name's Class 2 allows no market-wide cut

    def test_l07_a_scheduled_event_alone_cannot_lower_the_level(self):
        items = [evidence("cal", "SCHEDULED_EVENT", [], 10)]
        state, _ = self.step(items=items, assessment=self.assess("SEVERE", ["cal"]))
        self.assertEqual(state["level"], "NORMAL")
        state, _ = self.step(items=items, mode="DETERMINISTIC")
        self.assertEqual(state["level"], "NORMAL")
        caution, _ = self.step(items=self.two_class_2(), mode="DETERMINISTIC")
        renewed, _ = self.step(caution, session=12, items=self.two_class_2() + [
            evidence("cal2", "SCHEDULED_EVENT", [], 12)], mode="DETERMINISTIC")
        self.assertEqual(renewed["healthy_sessions"], 1)  # counted, not reset: a new calendar entry does not renew

    def test_l08_deterministic_map(self):
        caution, _ = self.step(items=self.two_class_2(), mode="DETERMINISTIC")
        self.assertEqual(caution["level"], "CAUTION")
        restriction, _ = self.step(items=[evidence("r", "TRADE_RESTRICTION", ["NVDAB", "SKHYB"], 10)],
                                   mode="DETERMINISTIC")
        self.assertEqual(restriction["level"], "CAUTION")
        narrow, _ = self.step(items=[evidence("r", "TRADE_RESTRICTION", ["NVDAB"], 10)], mode="DETERMINISTIC")
        self.assertEqual(narrow["level"], "NORMAL")
        severe, _ = self.step(items=[evidence("x", "TRADING_SUSPENSION", ["TSLAB"], 10)], mode="DETERMINISTIC")
        self.assertEqual(severe["level"], "SEVERE")
        foreign, _ = self.step(items=[evidence("x", "TRADING_SUSPENSION", ["AAPL"], 10)], mode="DETERMINISTIC")
        self.assertEqual(foreign["level"], "NORMAL")

    def test_malformed_assessment_is_rejected(self):
        for bad in ({"level": "PANIC", "evidence_ids": [], "reason": "", "falsifier": ""},
                    {"level": "CAUTION", "evidence_ids": "e1", "reason": "", "falsifier": ""}, "CAUTION"):
            state, record = self.step(items=self.two_class_2(), assessment=bad)
            self.assertEqual((state["level"], record["rejected"]), ("NORMAL", "MALFORMED_ASSESSMENT"))


    # --- L09 (IDEA-076 R2, review TRV-01): an assessor outage never raises exposure -------------------------------

    def outage(self, state, sessions):
        """Unhealthy sessions in turn: no output, a malformed one, and one citing unverified evidence."""
        bad = (None, {"level": "CAUTION"},
               self.assess("SEVERE", ["e9"]))
        for k, session in enumerate(sessions):
            state, record = self.step(state, session=session, items=self.two_class_2(),
                                      assessment=bad[k % len(bad)])
            self.assertFalse(record["accepted"])
            self.assertIsNotNone(record["rejected"])
        return state

    def healthy(self, state, sessions, level="NORMAL"):
        """Well-formed assessments citing only verified in-window evidence, renewing nothing."""
        for session in sessions:
            state, record = self.step(state, session=session, items=self.two_class_2(session=session - 1),
                                      assessment=self.assess(level, []))
            self.assertIsNone(record["rejected"])
            self.assertFalse(record["accepted"])
        return state

    def test_l09_an_outage_never_expires_a_caution(self):
        caution, _ = self.step(items=self.two_class_2(), assessment=self.assess("CAUTION", ["e1", "e2"]))
        kept = self.outage(caution, range(11, 20))  # three times the expiry
        self.assertEqual(kept["level"], "CAUTION")
        self.assertEqual(s1.level_fraction(cfg(), "UP", kept["level"]), Fraction(3, 5))

    def test_l09_caution_expires_after_expiry_healthy_sessions(self):
        caution, _ = self.step(items=self.two_class_2(), assessment=self.assess("CAUTION", ["e1", "e2"]))
        kept = self.outage(caution, range(11, 20))
        two = self.healthy(kept, (20, 21))
        self.assertEqual(two["level"], "CAUTION")  # two healthy sessions of three
        gone, record = self.step(two, session=22, items=self.two_class_2(session=21),
                                 assessment=self.assess("NORMAL", []))
        self.assertEqual(gone["level"], "NORMAL")
        self.assertTrue(record["expired"])

    def test_l09_severe_holds_through_an_outage_and_expires_when_healthy(self):
        items = [evidence("x", "TRADING_SUSPENSION", ["TSLAB"], 10)]
        severe, _ = self.step(items=items, assessment=self.assess("SEVERE", ["x"]))
        self.assertEqual(severe["level"], "SEVERE")
        kept = self.outage(severe, range(11, 20))
        self.assertEqual(kept["level"], "SEVERE")
        self.assertEqual(self.healthy(kept, (20, 21))["level"], "SEVERE")
        self.assertEqual(self.healthy(kept, (20, 21, 22))["level"], "NORMAL")

    def test_l09_deterministic_mode_counts_only_sessions_with_an_evidence_input(self):
        caution, _ = self.step(items=self.two_class_2(), mode="DETERMINISTIC")
        state = caution
        for session in range(11, 20):
            state, _ = s1.limiter_step(state, session=session, cfg=cfg(limiter_mode="DETERMINISTIC"), evidence=None,
                                       assessment=None)
        self.assertEqual(state["level"], "CAUTION")
        for session in (20, 21, 22):
            state, _ = self.step(state, session=session, mode="DETERMINISTIC")  # an empty list is an input
        self.assertEqual(state["level"], "NORMAL")

    def test_l09_model_mode_accepts_suspension_and_restriction_evidence(self):
        # Found while writing L09: the evidence-class map read its input once, so in MODEL mode a cited suspension
        # or a two-name restriction was never accepted (only the Class 2 rule saw the evidence).
        severe, record = self.step(items=[evidence("x", "TRADING_SUSPENSION", ["TSLAB"], 10)],
                                   assessment=self.assess("SEVERE", ["x"]))
        self.assertEqual((severe["level"], record["accepted"]), ("SEVERE", True))
        caution, record = self.step(items=[evidence("r", "TRADE_RESTRICTION", ["NVDAB", "SKHYB"], 10)],
                                    assessment=self.assess("CAUTION", ["r"]))
        self.assertEqual((caution["level"], record["accepted"]), ("CAUTION", True))

    def test_l09_a_session_is_counted_once(self):
        caution, _ = self.step(items=self.two_class_2(), assessment=self.assess("CAUTION", ["e1", "e2"]))
        state = self.healthy(caution, (10, 10))  # the acceptance session itself does not count
        state = self.healthy(state, (11, 11, 11, 12, 12))
        self.assertEqual(state["level"], "CAUTION")  # sessions 11 and 12: two of three
        self.assertEqual(self.healthy(state, (13,))["level"], "NORMAL")

    def test_l09_a_state_stored_before_the_rule_still_loads(self):
        # A state written with only `expires_session` reads as a cut accepted at expires_session - expiry with no
        # healthy session counted yet: it no longer lapses on the clock alone.
        old = {"level": "CAUTION", "expires_session": 13, "used_evidence_ids": ["e1", "e2"]}
        self.assertEqual(self.outage(old, (13, 14, 15))["level"], "CAUTION")
        self.assertEqual(self.healthy(old, (13, 14))["level"], "CAUTION")
        self.assertEqual(self.healthy(old, (13, 14, 15))["level"], "NORMAL")
        self.assertEqual(self.healthy({"level": "NORMAL", "expires_session": None, "used_evidence_ids": []},
                                      (13,))["level"], "NORMAL")


if __name__ == "__main__":
    unittest.main()
