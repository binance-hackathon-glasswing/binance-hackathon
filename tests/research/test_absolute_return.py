"""IDEA-034: a treatment arm that loses money is never SUPPORTED, under any registration.

User decision 2026-10-11: the goal is maximum profit, so beating a losing baseline is not enough. A positive
absolute after-cost return for the treatment (bootstrap lower bound of its own net return above zero, under the
registered metric) is a mandatory part of every support rule. A treatment that confidently does not make money is
NOT_SUPPORTED; one whose own return is uncertain is INCONCLUSIVE. Tests marked CONTROL pass on the unfixed code.
"""

import unittest

from larp.contracts import Document
from larp.research import evaluation
from larp.research.evaluation import evaluate
from tests.redteam.test_integration_redteam import econ_outcomes, econ_registration

OPT_IN_RULE = "LOWER_BOUND_ABOVE_MARGIN_AND_TREATMENT_NET_POSITIVE"  # IDEA-033 R24 stopgap, removed by IDEA-034
CLUSTERS = 4


def outcomes(baseline, treatment, service=0):
    """Per-cluster wallet net units (opening equity 1_000_000) for the baseline and treatment arms."""
    pairs = econ_outcomes([0] * CLUSTERS, service_units=service)
    for (a, b), base, treat in zip(pairs, baseline, treatment):
        a["wallet_net_units"], b["wallet_net_units"] = base, treat
    return [Document.from_dict(o) for pair in pairs for o in pair]


def report(docs, **changes):
    return evaluate(Document.from_dict(econ_registration(CLUSTERS, **changes)), docs).read()


class LosingTreatment(unittest.TestCase):
    def test_losing_but_better_is_never_supported(self):
        """Baseline loses 5%, treatment loses 2% in every cluster: the paired difference (+3%) passes every
        margin, but the treatment loses money. Not SUPPORTED under any support rule, kill rule or metric; here it
        confidently loses, so NOT_SUPPORTED with the absolute reason."""
        docs = outcomes([-50_000] * CLUSTERS, [-20_000] * CLUSTERS)
        for support in sorted(set(evaluation.SUPPORT_RULES) | {"LOWER_BOUND_ABOVE_MARGIN"}):
            for kill in evaluation.KILL_RULES:
                for metric in evaluation.METRICS:
                    with self.subTest(support=support, kill=kill, metric=metric):
                        r = report(docs, support_rule=support, kill_rule=kill, metric=metric)
                        self.assertNotEqual(r["status"], "SUPPORTED")
                        self.assertEqual((r["status"], r["reason"]),
                                         ("NOT_SUPPORTED", "TREATMENT_ABSOLUTE_NET_NOT_POSITIVE"))
                        self.assertGreater(r["paired_mean"][0], 0)
                        self.assertLess(r["treatment_absolute_mean"][0], 0)
                        self.assertIn("TREATMENT_ABSOLUTE_NET_NOT_POSITIVE", r["warnings"])

    def test_positive_mean_with_uncertain_absolute_return_is_inconclusive(self):
        """Treatment beats the baseline by exactly +1% in every cluster and its own mean is +1%, but its own
        returns alternate -1%/+3%, so the bootstrap lower bound of its return is not above zero. A positive mean
        alone does not support it (lower-bound rule, not mean rule): INCONCLUSIVE, not SUPPORTED."""
        baseline = [-20_000, 20_000] * (CLUSTERS // 2)
        r = report(outcomes(baseline, [b + 10_000 for b in baseline]))
        self.assertEqual((r["status"], r["reason"]), ("INCONCLUSIVE", "TREATMENT_ABSOLUTE_LOWER_BOUND_NOT_POSITIVE"))
        self.assertEqual(r["confidence_interval"], [[1, 100], [1, 100]])  # paired difference is certain
        self.assertGreater(r["treatment_absolute_mean"][0], 0)
        self.assertLessEqual(r["treatment_absolute_interval"][0][0], 0)
        self.assertGreater(r["treatment_absolute_interval"][1][0], 0)
        self.assertNotIn("TREATMENT_ABSOLUTE_NET_NOT_POSITIVE", r["warnings"])

    def test_zero_mean_treatment_with_uncertain_return_is_inconclusive_and_warned(self):
        """Treatment's own return averages 0 (-2%/+2%) while beating the baseline by 1%: INCONCLUSIVE, warned."""
        baseline = [-30_000, 10_000] * (CLUSTERS // 2)
        r = report(outcomes(baseline, [b + 10_000 for b in baseline]))
        self.assertEqual((r["status"], r["reason"]), ("INCONCLUSIVE", "TREATMENT_ABSOLUTE_LOWER_BOUND_NOT_POSITIVE"))
        self.assertIn("TREATMENT_ABSOLUTE_NET_NOT_POSITIVE", r["warnings"])

    def test_profitable_and_better_is_supported(self):
        """CONTROL. Baseline +1%, treatment +3% in every cluster: SUPPORTED without warnings."""
        r = report(outcomes([10_000] * CLUSTERS, [30_000] * CLUSTERS))
        self.assertEqual(r["status"], "SUPPORTED")
        self.assertEqual(r["warnings"], [])

    def test_profitable_and_better_reports_the_absolute_interval_and_baseline(self):
        """Every bootstrapped report states the mandatory absolute rule, the treatment's own interval and the
        baseline's own mean, so a reader sees when the default itself loses money."""
        r = report(outcomes([-10_000] * CLUSTERS, [30_000] * CLUSTERS))
        self.assertEqual(r["status"], "SUPPORTED")
        self.assertEqual(r["absolute_return_rule"], "TREATMENT_LOWER_BOUND_ABOVE_ZERO")
        self.assertEqual(r["treatment_absolute_interval"], [[3, 100], [3, 100]])
        self.assertEqual(r["baseline_absolute_mean"], [-1, 100])
        self.assertEqual(r["warnings"], ["BASELINE_ABSOLUTE_NET_NOT_POSITIVE"])

    def test_profitable_but_worse_still_killed_by_the_registered_rule(self):
        """CONTROL. Baseline +3%, treatment +1%: the registered paired kill rule decides, as before."""
        r = report(outcomes([30_000] * CLUSTERS, [10_000] * CLUSTERS))
        self.assertEqual(r["status"], "NOT_SUPPORTED")


class ServiceCosts(unittest.TestCase):
    def test_service_costs_that_flip_the_sign_under_the_after_service_metric(self):
        """Treatment wallet +0.5%, baseline wallet -1%, service costs 1% on each arm. After service costs the
        treatment loses 0.5% (the paired difference is unchanged at +1.5%): never SUPPORTED."""
        docs = outcomes([-10_000] * CLUSTERS, [5_000] * CLUSTERS, service=10_000)
        r = report(docs, metric="PAIRED_NET_WALLET_RETURN_AFTER_SERVICE_COSTS")
        self.assertEqual((r["status"], r["reason"]), ("NOT_SUPPORTED", "TREATMENT_ABSOLUTE_NET_NOT_POSITIVE"))
        self.assertEqual(r["treatment_absolute_mean"], [-1, 200])
        self.assertFalse(r["service_costs_reported_separately"])

    def test_service_costs_that_flip_the_sign_are_warned_under_the_wallet_metric(self):
        """Same outcomes under the wallet-only metric: the wallet (what the competition values, F-43; model and
        infrastructure spend are not scored, F-50) makes money, so SUPPORTED, but the report warns that the
        treatment does not cover its off-wallet service costs."""
        docs = outcomes([-10_000] * CLUSTERS, [5_000] * CLUSTERS, service=10_000)
        r = report(docs)
        self.assertEqual(r["status"], "SUPPORTED")
        self.assertTrue(r["service_costs_reported_separately"])
        self.assertIn("TREATMENT_NET_NOT_POSITIVE_AFTER_SERVICE_COSTS", r["warnings"])


class SupportRules(unittest.TestCase):
    def test_opt_in_rule_is_redundant_and_rejected(self):
        """The R24 opt-in rule is now the behaviour of every rule; naming it is an unsupported value (NOT_RUN),
        so no registration can believe it chose something different from the default."""
        r = report(outcomes([10_000] * CLUSTERS, [30_000] * CLUSTERS), support_rule=OPT_IN_RULE)
        self.assertEqual(r["status"], "NOT_RUN")
        self.assertIn("Unsupported support_rule", r["reason"])
        self.assertEqual(evaluation.SUPPORT_RULES, ("LOWER_BOUND_ABOVE_MARGIN",))


if __name__ == "__main__":
    unittest.main()
