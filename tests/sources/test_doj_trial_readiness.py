"""PC-FIX01: synthetic oversized images, anchored heads and honest report scopes."""
from dataclasses import replace
import json

from larp.sources.live import gap_report, LiveRunner, PollLog
from larp.sources.transport import AllowlistedClient, SourceError
from tests.sources.test_sources import Harness, FakeNet, T0, fr, doj
from larp.sources.store import SQLiteSourceStore


class Readiness(Harness):
    def test_doj_inline_image_removed_with_all_items_and_text_preserved(self):
        source=self.register['doj-press']
        source=replace(source,limits=dict(source.limits,max_response_bytes=2000))
        html='<p>Issuer adverse statement.</p><img src="image/jpeg;base64,'+'A'*6000+'"><p>Still retained.</p>'
        body=doj([('one','Release',html,1791500000,1791500000),
                  ('two','Release','<p>Other permitted text.</p>',1791500000,1791500000)])
        net=FakeNet({source.listing_url:[(200,{},body)]})
        out=self.ingestor(net,register={source.source_id:source}).poll(source.source_id)
        self.assertEqual(out['status'],'OK')
        records=self.store.records(source.source_id)
        self.assertEqual({r['item_id'] for r in records},{'one','two'})
        one=next(r for r in records if r['item_id']=='one')
        self.assertIn('MEDIA_REMOVED_AT_TRANSPORT:1',one['exclusions'])
        self.assertIn('wire_sha256',one['listing'])
        self.assertEqual(net.requests[0][0],source.listing_url)  # no offset/page-size change

    def test_large_permitted_text_and_other_publishers_still_refuse(self):
        for ident in ('doj-press','fr-bis'):
            source=self.register[ident];source=replace(source,limits=dict(source.limits,max_response_bytes=100))
            raw=doj([('x','Title','<p>'+'A'*3000+'</p>',1791500000,1791500000)])
            with self.subTest(source=ident),self.assertRaisesRegex(SourceError,'RESPONSE_TOO_LARGE'):
                AllowlistedClient(FakeNet({source.listing_url:[(200,{},raw)]})).get(source,source.listing_url)

    def test_head_success_does_not_reset_failed_history_retry_counter(self):
        source=self.register['fr-bis'];source=replace(source,limits=dict(source.limits,max_pages=2))
        tail=source.listing_url+'&page=2';more=source.listing_url+'&page=3'
        head=fr([{'document_number':'old','title':'Rule'}],tail)
        net=FakeNet({source.listing_url:[(200,{},head)],tail:[(200,{},fr([],more))],
                     more:[(500,{},None)]})
        ingest=self.ingestor(net,register={source.source_id:source})
        ingest.poll(source.source_id)
        for n in (1,2,3):
            out=ingest.poll(source.source_id)
            self.assertEqual(out['head_coverage']['complete'],True)
            self.assertEqual(self.store.cursor(source.source_id)['in_progress']['failures'],n)
        self.assertIn('abandoned_continuation',ingest.poll(source.source_id))

    def test_complete_head_is_logged_while_archive_stays_incomplete(self):
        source=self.register['fr-bis'];source=replace(source,limits=dict(source.limits,max_pages=2))
        tail=source.listing_url+'&page=2';more=source.listing_url+'&page=3'
        net=FakeNet({source.listing_url:[(200,{},fr([{'document_number':'old','title':'Rule'}],tail))],
                     tail:[(200,{},fr([],more))],more:[(200,{},fr([],more))]})
        ingest=self.ingestor(net,register={source.source_id:source})
        first=ingest.poll(source.source_id)
        self.assertFalse(first['head_coverage']['complete'])
        out=ingest.poll(source.source_id)
        self.assertTrue(out['head_coverage']['complete'])
        self.assertTrue(out['truncated'])
        self.assertEqual(out['head_coverage']['anchor_item_id'],'old')
        from pathlib import Path
        runner=LiveRunner(register={source.source_id:source},issuers=[],source_ingestor=ingest,
                          edgar_ingestor=None,log=PollLog(Path(self.tmp.name)/'polls'),clock_ms=self.clock,
                          sleep=lambda s:None,commit='pushed-test')
        line=runner.poll(runner.targets[0])
        self.assertTrue(line['head_coverage']['complete'])

    def test_current_scope_needs_new_explicit_head_proof_and_preserves_history_counts(self):
        cadence=600_000;end=T0+86_400_000
        lines=[dict(target='source:doj-press',started_ms=t,finished_ms=t+1,status='OK',
                    cadence_ms=cadence,truncated=True,rejected=0,
                    head_coverage=dict(schema='SourceHeadCoverage.v1',complete=True,checked_ms=t+1,
                                       anchor_item_id='old',basis='DURABLE_OVERLAP'))
               for t in range(T0,end,cadence)]
        args=dict(cadences={'source:doj-press':cadence},start_ms=T0,end_ms=end)
        historical=gap_report(lines,**args)
        self.assertEqual(historical['verdict'],'FAIL')
        current=gap_report(lines,coverage_scope='current',**args)
        self.assertEqual(current['verdict'],'PASS')
        self.assertEqual(current['historical_report'],historical)
        self.assertEqual(current['targets']['source:doj-press']['history_incomplete_polls'],144)
        for line in lines:line.pop('head_coverage')
        self.assertEqual(gap_report(lines,coverage_scope='current',**args)['verdict'],'FAIL')

    def test_head_failure_or_missing_anchor_cannot_qualify_current_scope(self):
        end=T0+86_400_000
        lines=[dict(target='source:doj-press',started_ms=t,finished_ms=t+1,status='OK',cadence_ms=600_000,
                    head_coverage=dict(schema='SourceHeadCoverage.v1',complete=False,checked_ms=t+1,
                                       anchor_item_id=None,basis='UNANCHORED'))
               for t in range(T0,end,600_000)]
        self.assertEqual(gap_report(lines,cadences={'source:doj-press':600_000},start_ms=T0,end_ms=end,
                                    coverage_scope='current')['verdict'],'FAIL')

    def test_unanchored_head_does_not_become_its_own_checkpoint_after_restart(self):
        source=self.register['fr-bis'];source=replace(source,limits=dict(source.limits,max_pages=2))
        tail=source.listing_url+'&page=2';archive=source.listing_url+'&page=3'
        initial=fr([{'document_number':'baseline','title':'Old head'}],tail)
        moved=fr([{'document_number':'new-head','title':'New head'}],tail)
        middle=fr([{'document_number':'new-middle','title':'More new rows'}],archive)
        net=FakeNet({source.listing_url:[(200,{},initial),(200,{},moved)],
                     tail:[(200,{},fr([],archive)),(200,{},middle)],
                     archive:[(200,{},fr([],archive))]})
        ingest=self.ingestor(net,register={source.source_id:source})
        ingest.poll(source.source_id)
        self.assertFalse(ingest.poll(source.source_id)['head_coverage']['complete'])
        restarted=SQLiteSourceStore(self.db_path);self.addCleanup(restarted.close)
        out=self.ingestor(net,register={source.source_id:source},store=restarted).poll(source.source_id)
        self.assertFalse(out['head_coverage']['complete'])  # baseline has still never been reached

    def test_transport_wire_bound_and_embedded_rights_notice_remain_fail_closed(self):
        from unittest.mock import patch
        from larp.sources import transport
        source=self.register['doj-press'];source=replace(source,limits=dict(source.limits,max_response_bytes=300))
        body=doj([('x','Release','<img alt="not covered under third-party terms" src="'+'A'*2000+'">',1791500000,1791500000)])
        with self.assertRaises(SourceError):
            AllowlistedClient(FakeNet({source.listing_url:[(200,{},body)]})).get(source,source.listing_url)
        with patch.object(transport,'DOJ_WIRE_CAP',100),self.assertRaises(SourceError):
            AllowlistedClient(FakeNet({source.listing_url:[(200,{},body)]})).get(source,source.listing_url)
