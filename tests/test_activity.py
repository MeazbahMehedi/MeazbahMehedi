from datetime import date
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from update_activity import CalendarParser, complete_rows, render


class ActivityTests(unittest.TestCase):
    def test_calendar_parser_counts_and_singular(self):
        p=CalendarParser()
        p.feed('''<td id="a" data-date="2026-01-01"></td><td id="b" data-date="2026-01-02"></td><td id="c" data-date="2026-01-03"></td><tool-tip for="b">1 contribution on January 2nd.</tool-tip><tool-tip for="a">No contributions on January 1st.</tool-tip><tool-tip for="c">1,200 contributions on January 3rd.</tool-tip>''')
        self.assertEqual(p.counts(),{'2026-01-01':0,'2026-01-02':1,'2026-01-03':1200})

    def test_unknown_markup_does_not_become_zero(self):
        p=CalendarParser();p.feed('<td id="a" data-date="2026-01-01"></td>')
        with self.assertRaisesRegex(RuntimeError,'incomplete'):
            complete_rows(p.counts(),date(2026,1,1),1)

    def test_activity_graph_uses_real_numeric_values(self):
        rows=complete_rows({'2026-01-01':0,'2026-01-02':3},date(2026,1,1),2)
        for mode in [True,False]:
            svg=render(rows,'2026-01-02T00:00:00Z',mode)
            ET.fromstring(svg)
            self.assertIn('2026-01-02: 3 contributions',svg)
            self.assertIn('prefers-reduced-motion',svg)


if __name__=='__main__': unittest.main()
