"""IDEA-033 R09/R11/R12: synthetic HTTP and clocks only."""

from dataclasses import replace
import json

from larp.sources.ingest import coverage
from larp.sources.parse import safe_when
from larp.sources.transport import AllowlistedClient
from tests.sources.test_sources import Harness, FakeNet, T0, fr
from tools.probe_free_sources import probe


class FollowupSources(Harness):
    def test_probe_success_and_item_truncation(self):
        source = self.register['fr-bis']
        source = replace(source, limits=dict(source.limits, max_items_per_page=1))
        for count in (0, 1, 2):
            with self.subTest(count=count):
                body = fr([{'document_number': str(i), 'title': 'Synthetic notice'} for i in range(count)])
                net = FakeNet({source.listing_url: [(200, {}, body)]})
                row = probe(source, AllowlistedClient(net))
                self.assertEqual(row['status'], 200)
                self.assertEqual(row['items'], min(count, 1))
                self.assertEqual(row['item_truncated'], count > 1)

    def test_probe_304_does_not_parse_a_missing_body(self):
        source = self.register['fr-bis']
        row = probe(source, AllowlistedClient(FakeNet({source.listing_url: [(304, {}, None)]})))
        self.assertEqual(row['status'], 304)
        self.assertEqual(row['items'], 0)
        self.assertFalse(row['item_truncated'])

    def test_availability_is_response_completion_not_request_start(self):
        source = self.register['fr-bis']
        def delayed(headers):
            self.clock.now += 5000
            return 200, {}, fr([{'document_number': 'one', 'title': 'Synthetic notice'}])
        self.ingestor(FakeNet({source.listing_url: [delayed]})).poll(source.source_id)
        [record] = self.store.records(source.source_id)
        self.assertEqual(record['available_ms'], T0 + 5000)
        self.assertEqual(record['retrieved_ms'], T0 + 5000)
        self.assertEqual(record['first_seen_ms'], T0 + 5000)
        health = self.store.cursor(source.source_id)['health']
        self.assertEqual(health['last_attempt_ms'], T0)
        self.assertEqual(health['last_success_ms'], T0 + 5000)

    def test_backward_retrieval_clock_records_failure_without_documents(self):
        source = self.register['fr-bis']
        def backwards(headers):
            self.clock.now -= 1
            return 200, {}, fr([{'document_number': 'one', 'title': 'Synthetic notice'}])
        outcome = self.ingestor(FakeNet({source.listing_url: [backwards]})).poll(source.source_id)
        self.assertEqual(outcome['status'], 'SOURCE_UNAVAILABLE')
        self.assertEqual(self.store.records(source.source_id), [])

    def test_impossible_calendar_date_is_an_unparseable_item(self):
        for date in ('2026-02-30', '2026-13-01', '0000-01-01'):
            with self.subTest(date=date):
                self.assertEqual(safe_when(date), (None, 'UNPARSEABLE'))

    def test_malformed_listing_shapes_fail_durably_and_recover(self):
        cases = [('fr-bis', json.dumps(value).encode()) for value in
                 ({}, {'results': None}, {'results': {}}, {'results': 'bad'}, {'results': [None]},
                  {'results': [{'document_number': 'one', 'title': ['bad']} ]},
                  {'results': [], 'next_page_url': 123})]
        cases += [('ec-press', b'<html><body>Service unavailable</body></html>')]
        for source_id, body in cases:
            with self.subTest(source=source_id, body=body):
                source = self.register[source_id]
                self.ingestor(FakeNet({source.listing_url: [(200, {}, body)]})).poll(source_id)
                self.assertEqual(self.store.cursor(source_id)['health']['status'], 'UNAVAILABLE')
                self.assertFalse(coverage(self.register, self.store, {'c': [source_id]}, T0, 1000)
                                 ['consumers']['c']['complete'])
                clean = fr([]) if source_id == 'fr-bis' else b'<rss><channel/></rss>'
                self.ingestor(FakeNet({source.listing_url: [(200, {}, clean)]})).poll(source_id)
                self.assertEqual(self.store.cursor(source_id)['health']['status'], 'OK')

    def test_rejected_items_impair_coverage_until_complete_rescan(self):
        source = self.register['fr-bis']
        source = replace(source, limits=dict(source.limits, max_pages=1))
        tail = source.listing_url + '&page=2'
        reg = {source.source_id: source}
        for bad in ({'title': 'No identity'},
                    {'document_number': 'bad-date', 'publication_date': 'not a date'}):
            with self.subTest(bad=bad):
                first = fr([bad, {'document_number': 'good', 'title': 'Synthetic notice'}], tail)
                net = FakeNet({source.listing_url: [(200, {'ETag': 'v1'}, first), (200, {}, fr([]))],
                               tail: [(200, {}, fr([]))]})
                self.ingestor(net, register=reg).poll(source.source_id)
                self.ingestor(net, register=reg).poll(source.source_id)
                self.assertFalse(coverage(reg, self.store, {'c': [source.source_id]}, T0, 1000)
                                 ['consumers']['c']['complete'])
                self.ingestor(net, register=reg).poll(source.source_id)
                self.assertNotIn('If-None-Match', net.requests[-1][1])
                self.assertTrue(coverage(reg, self.store, {'c': [source.source_id]}, T0, 1000)
                                ['consumers']['c']['complete'])
