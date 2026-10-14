"""A source recovery requirements, using the real durable store and fake HTTP only."""
from dataclasses import replace
import http.client
from larp.sources.live import capture_terms
from larp.sources.ingest import coverage
from tests.sources.test_sources import Harness, FakeNet, T0, rss, fr


class FinalASources(Harness):
    def test_a_req_014_partial_terms_response_records_failure_and_continues(self):
        def fetch(url, *args):
            if 'justice.gov' in url:
                raise http.client.IncompleteRead(b'UNTRUSTED_PARTIAL_MARKER', 20)
            return 200, {}, b'synthetic permitted-source terms'
        rows = {r['source_id']: r for r in capture_terms(self.register, fetch, self.artifacts, self.clock)}
        self.assertEqual(rows['doj-press']['status'], 'FAILED')
        self.assertEqual(rows['doj-press']['error'], 'IncompleteRead')
        self.assertNotIn('sha256', rows['doj-press'])
        self.assertEqual(rows['ec-press']['status'], 'CAPTURED')
        self.assertNotIn('UNTRUSTED_PARTIAL_MARKER', str(rows))

    def test_a_req_014_policy_exclusion_does_not_make_permitted_coverage_incomplete(self):
        source = self.register['ec-press']
        items = [('Restricted', 'https://ec.europa.eu/commission/presscorner/detail/en/restricted',
                  'Fri, 09 Oct 2026 10:59:00 -0400', '<p>Copyright 2026 ThirdParty. All rights reserved.</p>'),
                 ('Permitted', 'https://ec.europa.eu/commission/presscorner/detail/en/allowed',
                  'Fri, 09 Oct 2026 10:59:00 -0400', '<p>The Commission adopted a routine rule.</p>')]
        ingest = self.ingestor(FakeNet({source.listing_url: [(200, {}, rss(items))]}))
        first = ingest.poll(source.source_id)
        self.assertTrue(first['rejected'])
        self.assertEqual(len(self.store.records(source.source_id)), 1)
        self.assertTrue(coverage({source.source_id: source}, self.store, {'c': [source.source_id]}, T0, 1000)
                        ['consumers']['c']['complete'])
        self.assertEqual(first.get('policy_rejected'), first['rejected'])
        # No raw restricted content retained; changed bytes must be reconsidered, not permanently blacklisted by ID.
        rejected = self.store.cursor(source.source_id)['rejected'][items[0][1]]
        self.assertTrue(rejected.get('item_sha256'))
        self.assertFalse(any(b'Copyright 2026 ThirdParty' in p.read_bytes() for p in
                             __import__('pathlib').Path(self.tmp.name, 'artifacts').rglob('*') if p.is_file()))
        permitted = [(t, u, d, '<p>A new permitted original release.</p>') for t, u, d, _ in items]
        ingest = self.ingestor(FakeNet({source.listing_url: [(200, {}, rss(permitted))]}))
        ingest.poll(source.source_id)
        self.assertEqual(len(self.store.records(source.source_id)), 3)

    def test_a_req_018_new_head_is_processed_before_saved_history(self):
        source = self.register['fr-bis']
        source = replace(source, limits=dict(source.limits, max_pages=2))
        tail = source.listing_url + '&page=2'
        more = source.listing_url + '&page=3'
        head = fr([{'document_number': 'old', 'title': 'Old rule'}], tail)
        changed = fr([{'document_number': 'fresh', 'title': 'New rule'}, {'document_number': 'old', 'title': 'Old rule'}], tail)
        net = FakeNet({source.listing_url: [(200, {}, head), (200, {}, changed)],
                       tail: [(200, {}, fr([{'document_number': 'tail', 'title': 'Archive'}], more))],
                       more: [(200, {}, fr([]))]})
        ingest = self.ingestor(net, register={source.source_id: source})
        ingest.poll(source.source_id)
        self.assertIsNotNone(self.store.cursor(source.source_id)['in_progress'])
        before = len(net.requests)
        ingest.poll(source.source_id)
        self.assertEqual(net.requests[before][0], source.listing_url)
        self.assertIn('fresh', [r['item_id'] for r in self.store.records(source.source_id)])

    def test_a_req_016_malformed_timestamp_still_impairs_coverage(self):
        source = self.register['fr-bis']
        net = FakeNet({source.listing_url: [(200, {}, fr([{'document_number': 'bad', 'title': 'Rule',
                                                          'publication_date': 'not-a-date'}]))]})
        self.ingestor(net).poll(source.source_id)
        self.assertFalse(coverage(self.register, self.store, {'c': [source.source_id]}, T0, 1000)
                         ['consumers']['c']['complete'])

    def test_a_req_018_live_pagination_needs_budget_for_head_and_history(self):
        from larp.sources.register import live_preflight
        source = replace(self.register['fr-bis'], limits=dict(self.register['fr-bis'].limits, max_pages=1))
        reasons = live_preflight({source.source_id: source}, {})
        self.assertIn('PAGINATION_PAGE_BUDGET_TOO_SMALL:fr-bis', reasons)

    def test_a_req_014_live_terms_hash_needs_matching_retained_bytes(self):
        from pathlib import Path
        from larp.sources.register import live_preflight, load_edgar_terms
        source = replace(self.register['fr-bis'], rights=dict(self.register['fr-bis'].rights,
                                                             terms_evidence_sha256='f' * 64))
        env = {'LARP_SEC_USER_AGENT': 'LARP test ops@larp-test.invalid', 'LARP_ARTIFACT_ROOT': self.tmp.name}
        edgar = dict(load_edgar_terms(), terms_evidence_sha256='f' * 64)
        self.assertIn('TERMS_ARTIFACT_UNAVAILABLE:fr-bis', live_preflight({source.source_id: source}, env, edgar))
        blob = b'Synthetic terms fixture, not actual source clearance.'
        sha = self.artifacts.put(blob)
        source = replace(source, rights=dict(source.rights, terms_evidence_sha256=sha))
        edgar['terms_evidence_sha256'] = sha
        self.assertEqual(live_preflight({source.source_id: source}, env, edgar), [])
        (self.artifacts.root / sha[:2] / sha).write_bytes(b'tampered')
        self.assertIn('TERMS_ARTIFACT_UNAVAILABLE:fr-bis', live_preflight({source.source_id: source}, env, edgar))
