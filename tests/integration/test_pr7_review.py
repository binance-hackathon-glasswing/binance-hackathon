"""IDEA-033: runtime evidence validation uses the request's exact cutoff."""

import unittest

from larp.contracts import ContractError, Document
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXSEMI, build_world
from larp.runtime.schema import assessment_result


class ResultBoundaryTests(unittest.TestCase):
    def test_runtime_rejects_a_result_for_a_different_cutoff(self):
        w = build_world(["EXSEMI_402_8K"])
        request = w.request(["EXSEMI_402_8K"], issuer_id=EXSEMI, job_id="job:boundary")
        result = w.assessor(RuleBaselineModel(w.clock)).assess(request)
        assessment_result(result, request, w.clock())
        data = result.read()
        data["cutoff_ms"] -= 1
        with self.assertRaises(ContractError):
            assessment_result(Document.from_dict(data), request, w.clock())
