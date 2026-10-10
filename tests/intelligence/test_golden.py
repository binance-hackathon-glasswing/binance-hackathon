"""Exact-replay regression: the two committed demonstration traces regenerate byte for byte.

A change to extraction, verification, agent or gate logic changes these bytes (the rule
baseline's identity hash covers its code). Regenerate with
`python -m larp.intelligence.demo --out tests/intelligence/golden` and review the diff.
"""

import unittest
from pathlib import Path

from larp.intelligence.demo import render, traces

GOLDEN = Path(__file__).resolve().parent / "golden"


class GoldenTraceTests(unittest.TestCase):
    def test_traces_match_committed_documents(self):
        produced = traces()
        self.assertEqual(sorted(produced), sorted(p.name for p in GOLDEN.glob("*.json")))
        for name, trace in produced.items():
            with self.subTest(trace=name):
                self.assertEqual(render(trace), (GOLDEN / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
