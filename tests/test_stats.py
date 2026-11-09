from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from update_stats import fetch_languages, longest_streak, render, summarize, top_shares


def days(*counts, key='contributions'):
    return [{'date': f'2026-01-{n + 1:02d}', key: count} for n, count in enumerate(counts)]


class StatsTests(unittest.TestCase):
    def test_streak_and_summary(self):
        self.assertEqual(longest_streak(days(1, 2, 0, 3, 4, 5, 0)), 3)
        self.assertEqual(longest_streak(days(0, 0)), 0)
        stats = summarize(days(2, 0, 1, key='commits'), days(3, 0, 4))
        self.assertEqual([value for value, _ in stats], [3, 7, 2, 1])

    def test_languages_skip_forks_and_profile_repo(self):
        responses = {
            'https://api.github.com/users/me/repos?type=owner&per_page=100': [
                {'name': 'tool', 'fork': False, 'languages_url': 'https://api.github.com/repos/me/tool/languages'},
                {'name': 'copy', 'fork': True, 'languages_url': 'https://api.github.com/repos/me/copy/languages'},
                {'name': 'ME', 'fork': False, 'languages_url': 'https://api.github.com/repos/me/ME/languages'},
                {'name': 'odd', 'fork': False, 'languages_url': 'https://example.com/odd'},
            ],
            'https://api.github.com/repos/me/tool/languages': {'Python': 900, 'HTML': 100},
        }
        totals, counted = fetch_languages('me', fetch=responses.__getitem__)
        self.assertEqual((totals, counted), ({'Python': 900, 'HTML': 100}, 1))

    def test_small_and_extra_languages_fold_into_other(self):
        shares = top_shares({'A': 600, 'B': 300, 'C': 95, 'D': 5}, limit=2)
        self.assertEqual([name for name, _ in shares], ['A', 'B', 'Other'])
        self.assertAlmostEqual(sum(share for _, share in shares), 1)
        self.assertEqual(top_shares({}), [])

    def test_card_shows_final_values_without_animation(self):
        stats = [(91, 'public commits'), (122, 'contributions'), (14, 'days with contributions'), (9, 'day contribution streak')]
        for light in (False, True):
            svg = render(stats, [('Python', 0.75), ('Other', 0.25)], '2026-01-01T00:00:00Z', 4, light)
            ET.fromstring(svg)
            # The resting transform puts each digit in place even if CSS never runs.
            self.assertIn('class="roll r9" style="animation-delay:0.00s" transform="translate(0 -414)"', svg)
            self.assertIn('Python', svg)
            self.assertIn('prefers-reduced-motion', svg)
        self.assertIn('next refresh', render(stats, [], 'now', 0))


if __name__ == '__main__':
    unittest.main()
