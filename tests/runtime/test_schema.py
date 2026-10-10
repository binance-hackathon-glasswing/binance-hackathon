import unittest

from larp.contracts import ContractError
from larp.runtime.schema import assessment_request,assessment_result,fact
from larp.runtime.fixtures import assess
from larp.storage.postgres import doc
from tests.support import request


class Schemas(unittest.TestCase):
    def test_stale_context_future_evidence_and_excess_budget(self):
        base=request().read(); now=base['cutoff_ms']
        assessment_request(doc(base),'run','a'*64,now)
        for change in ('future','budget','profile'):
            r=request().read()
            if change=='future': r['evidence_refs'][0]['available_ms']=now+1
            if change=='budget': r['budget']['tool_calls']=7
            if change=='profile': r['policy_profile_hash']='b'*64
            with self.assertRaises(ContractError): assessment_request(doc(r),'run','a'*64,now)
        result=assess(request()).read(); result['context_hash']='b'*64
        with self.assertRaises(ContractError): assessment_result(doc(result),request(),now)
        result=assess(request()).read(); result['orders']=[]
        with self.assertRaises(ContractError): assessment_result(doc(result),request(),now)

    def test_missing_stale_unknown_remain_distinct(self):
        base=request().read()['evidence_refs'][0]
        values=[]
        for quality in ('MISSING','STALE','UNKNOWN','VALID'):
            values.append(fact(doc(dict(base,quality=quality)),1791590400000).payload)
        self.assertEqual(4,len(set(values)))
