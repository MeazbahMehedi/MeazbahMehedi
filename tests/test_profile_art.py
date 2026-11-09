import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_profile_art import _discrete, build, render_card, tagline_timeline

CONFIG = json.loads((ROOT / 'data/projects.json').read_text(encoding='utf-8'))


class ProfileArtTests(unittest.TestCase):
    def test_every_output_is_valid_svg_with_reduced_motion(self):
        outputs = build(CONFIG)
        self.assertEqual(len(outputs), 2 * (3 + len(CONFIG['projects'])))
        for path, svg in outputs.items():
            with self.subTest(path=path):
                ET.fromstring(svg)
                self.assertIn('prefers-reduced-motion', svg)

    def test_discrete_key_times_increase_and_end_at_one(self):
        key_times, values = _discrete([(0, 0), (1, 2), (1, 3), (2, 4)], 4)
        times = [float(t) for t in key_times.split(';')]
        self.assertEqual(times, sorted(set(times)))
        self.assertEqual(times[-1], 1)
        self.assertEqual(values.split(';'), ['0', '3', '4', '4'])

    def test_tagline_types_full_phrase_then_erases(self):
        steps = tagline_timeline(10, 5.0)
        self.assertEqual(max(k for _, k in steps), 10)
        self.assertEqual(steps[-1][1], 0)
        self.assertTrue(all(5.0 <= t < 10.0 for t, _ in steps[1:]))

    def test_overlong_tagline_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'too long'):
            tagline_timeline(80, 0)

    def test_card_escapes_text_and_rejects_overflow(self):
        project = dict(CONFIG['projects'][0], name='A & B', description='Uses <tags> & more.')
        svg = render_card(project, 'dark')
        ET.fromstring(svg)
        self.assertIn('A &amp; B', svg)
        with self.assertRaisesRegex(ValueError, 'lines'):
            render_card(dict(project, description='word ' * 80), 'dark')
        with self.assertRaisesRegex(ValueError, 'chips'):
            render_card(dict(project, stack=['Framework'] * 8), 'dark')


if __name__ == '__main__':
    unittest.main()
