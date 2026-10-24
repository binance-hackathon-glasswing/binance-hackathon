"""IDEA-092 C1-C3: the Cloudflare Pages job, with a fake wrangler. No network, no Cloudflare account."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.dashboard import cloudflare as cf

FAKE = '''import json, os, sys
folder = sys.argv[sys.argv.index('deploy') + 1]
with open(os.environ['FAKE_WRANGLER_LOG'], 'a') as f:
    f.write(json.dumps(dict(argv=sys.argv[1:], files=sorted(os.listdir(folder)),
                            headers=open(os.path.join(folder, '_headers')).read())) + '\\n')
print('Deployment complete! https://larp-dashboard.pages.dev')
'''


class Job(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.log = self.root / 'wrangler.log'
        fake = self.root / 'fake_wrangler.py'
        fake.write_text(FAKE)
        self.wrangler = (sys.executable, str(fake))
        env = patch.dict(os.environ, dict(CLOUDFLARE_API_TOKEN='test-token', CLOUDFLARE_ACCOUNT_ID='0' * 32,
                                          FAKE_WRANGLER_LOG=str(self.log)))
        env.start()
        self.addCleanup(env.stop)
        self.work = self.root / 'work'
        self.refreshed = 0

    def refresher(self, work, settings=None):
        self.refreshed += 1
        self.settings = settings
        site = Path(work) / 'site'
        site.mkdir(parents=True, exist_ok=True)
        (site / 'index.html').write_text('<title>LARP wallet dashboard</title>')
        (site / 'data.json').write_text('{}')
        (site / '.nojekyll').write_text('')
        (Path(work) / 'refresh-state.json').write_text('{"blocks": [1]}')  # must never be published
        (Path(work) / 'monitor').mkdir(exist_ok=True)
        return dict(as_of_utc='2026-10-24T12:00:00Z', rounds=21, chain={}, export_error=None)

    def deployments(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_c1_c2_deploys_exactly_the_page_data_and_headers(self):
        out = cf.run(self.work, 'larp-dashboard', wrangler=self.wrangler, refresher=self.refresher)
        [d] = self.deployments()
        self.assertEqual(d['files'], ['_headers', 'data.json', 'index.html'])
        self.assertEqual(d['argv'][d['argv'].index('--project-name') + 1], 'larp-dashboard')
        self.assertEqual(d['argv'][d['argv'].index('--branch') + 1], 'main')
        self.assertIn('Cache-Control: no-store', d['headers'])
        self.assertIn('X-Robots-Tag: noindex', d['headers'])
        self.assertTrue(d['headers'].startswith('/*\n'))
        self.assertEqual(out['deployed'], 'Deployment complete! https://larp-dashboard.pages.dev')
        self.assertNotIn('test-token', json.dumps(out))

    def test_c1_a_failed_refresh_deploys_nothing(self):
        def failing(work, settings=None):
            raise RuntimeError('balance read refused')
        with self.assertRaises(RuntimeError):
            cf.run(self.work, 'larp-dashboard', wrangler=self.wrangler, refresher=failing)
        self.assertEqual(self.deployments(), [])

    def test_c1_an_overlapping_run_does_nothing(self):
        held = cf.lock(self.work)
        try:
            out = cf.run(self.work, 'larp-dashboard', wrangler=self.wrangler, refresher=self.refresher)
        finally:
            held.close()
        self.assertEqual((out, self.refreshed, self.deployments()), (dict(skipped='another run is in progress'), 0, []))

    def test_c1_missing_credentials_stop_before_any_work(self):
        for missing in cf.CREDENTIALS:
            with self.subTest(missing=missing), patch.dict(os.environ, {missing: ''}):
                with self.assertRaises(SystemExit):
                    cf.run(self.work, 'larp-dashboard', wrangler=self.wrangler, refresher=self.refresher)
        self.assertEqual((self.refreshed, self.deployments()), (0, []))

    def test_c1_a_failed_deploy_never_shows_the_token(self):
        bad = self.root / 'bad_wrangler.py'
        bad.write_text("import os, sys; sys.stderr.write('auth failed for ' + os.environ['CLOUDFLARE_API_TOKEN']); sys.exit(1)")
        with self.assertRaises(RuntimeError) as caught:
            cf.run(self.work, 'larp-dashboard', wrangler=(sys.executable, str(bad)), refresher=self.refresher)
        self.assertNotIn('test-token', str(caught.exception))
        self.assertIn('<token>', str(caught.exception))

    def test_c1_wallet_settings_reach_the_refresh(self):
        settings = dict(wallet='0x' + 'ab' * 20, start_nonce=0, start_usdt=100.0)
        cf.run(self.work, 'larp-dashboard', settings=settings, wrangler=self.wrangler, refresher=self.refresher)
        self.assertEqual(self.settings, settings)

    def test_c3_wrangler_is_pinned_exactly(self):
        self.assertRegex(cf.WRANGLER[-1], r'^wrangler@\d+\.\d+\.\d+$')


if __name__ == '__main__':
    unittest.main()
