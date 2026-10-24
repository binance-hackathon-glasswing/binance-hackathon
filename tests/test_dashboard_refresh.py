"""IDEA-087 DR: the hourly private-page refresh (tools/dashboard/refresh.py), offline parts only."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from tests.test_dashboard import write_monitor
from tools.dashboard import build as b
from tools.dashboard import refresh as r


class ArtifactPage(unittest.TestCase):
    def test_dr1_the_built_page_becomes_an_artifact_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / 'site'
            b.build(write_monitor(Path(tmp) / 'monitor'), site)
            page = r.artifact_page((site / 'index.html').read_text())
        for tag in ('<!doctype', '<html', '<head>', '</head>', '<body>', '</body>', '</html>', 'name="viewport"'):
            self.assertNotIn(tag, page.lower() if tag.startswith('<!') else page)
        self.assertEqual(page.count('<title>LARP wallet dashboard</title>'), 1)
        self.assertIn('<meta name="claude:viewport-fit-sides" content="cover">', page)
        self.assertIn('padding-left: max(16px, env(safe-area-inset-left, 0px))', page)
        self.assertIn('padding-right: max(16px, env(safe-area-inset-right, 0px))', page)
        self.assertIsNone(re.search(r'0x[0-9a-fA-F]{8,}', page))

    def test_dr2_known_blocks_come_from_the_monitor_transactions(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = write_monitor(Path(tmp) / 'monitor')
            self.assertEqual(r.known_blocks(monitor), [110, 115, 190, 195])
            self.assertEqual(r.known_blocks(Path(tmp) / 'missing'), [])


if __name__ == '__main__':
    unittest.main()
