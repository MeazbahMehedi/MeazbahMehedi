import importlib.util
from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import json

path = Path(__file__).resolve().parents[1] / 'scripts/update_commits.py'
spec = importlib.util.spec_from_file_location('profile_commits', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def commit(sha, authored):
    return {'sha': sha, 'commit': {'author': {'date': authored}}}


class CommitTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)

    def test_zero_days_duplicates_and_timezone_boundaries(self):
        items = [commit('a', '2026-01-02T01:00:00+08:00'),
                 commit('a', '2026-01-02T01:00:00+08:00'),
                 commit('b', '2026-01-03T23:30:00-02:00'),
                 commit('outside', '2025-12-31T00:00:00Z')]
        rows = module.aggregate(items, date(2026, 1, 1), 31)
        self.assertEqual(len(rows), 31)
        self.assertEqual(rows[0]['commits'], 1)
        self.assertEqual(rows[1]['commits'], 0)
        self.assertEqual(rows[3]['commits'], 1)
        self.assertEqual(sum(row['commits'] for row in rows), 2)

    def test_pagination_reads_every_page(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            count = 100 if 'page=1&' in url else 1
            return {'total_count': 101, 'incomplete_results': False,
                    'items': [{'sha': str(len(calls)) + '-' + str(n)} for n in range(count)]}
        result = module.search_commits('example-user', self.start, self.end, fetch=fetch)
        self.assertEqual(len(result), 101)
        self.assertEqual(len(calls), 2)
        self.assertIn('is%3Apublic', calls[0])

    def test_over_1000_results_are_partitioned(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            if len(calls)==1:
                return {'total_count': 1001, 'incomplete_results': False, 'items': []}
            return {'total_count': 1, 'incomplete_results': False, 'items': [{'sha': str(len(calls))}]}
        self.assertEqual(len(module.search_commits('example-user', self.start, self.end, fetch=fetch)),2)
        self.assertEqual(len(calls), 3)

    def test_incomplete_results_fail(self):
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            module.search_commits('example-user', self.start, self.end,
                                  fetch=lambda url: {'total_count': 1, 'incomplete_results': True, 'items': []})

    def test_missing_pages_fail(self):
        with self.assertRaisesRegex(RuntimeError, 'mismatch'):
            module.search_commits('example-user', self.start, self.end,
                                  fetch=lambda url: {'total_count': 2, 'incomplete_results': False, 'items': []})

    def test_changed_index_fails(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            return {'total_count': 101 if len(calls)==1 else 102,
                    'incomplete_results': False, 'items': [{}]*100}
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            module.search_commits('example-user', self.start, self.end, fetch=fetch)

    def test_zero_activity_is_valid_and_chart_is_well_formed(self):
        rows=module.aggregate([],date(2026,1,1),31)
        for light in [False,True]:
            svg=module.render_chart(rows,'example-user','2026-01-31T00:00:00Z',light)
            ET.fromstring(svg)
            self.assertNotIn('nan',svg.lower())
            self.assertNotIn('inf',svg.lower())
            self.assertIn('prefers-reduced-motion',svg)

    def test_snapshot_output_matches_real_counts(self):
        rows=module.aggregate([commit('a','2026-01-01T00:00:00Z')],date(2026,1,1),31)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            module.write_outputs(rows,'example-user',root,'2026-01-31T00:00:00Z')
            data=json.loads((root/'data/daily-commits.json').read_text())
            self.assertEqual(data['days'],rows)
            self.assertIn('2026-01-01,1',(root/'data/daily-commits.csv').read_text())
            self.assertIn('| 2026-01-01 | 1 |',(root/'data/DAILY-COMMITS.md').read_text())


if __name__ == '__main__':
    unittest.main()
