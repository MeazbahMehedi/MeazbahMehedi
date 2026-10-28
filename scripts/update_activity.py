"""Generate a local contribution graph from GitHub's real calendar data."""
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from html import escape
import json
import math
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

from update_commits import text, timestamp

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates = {}
        self.labels = {}
        self.current = None
        self.buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('data-date') and attrs.get('id'):
            self.dates[attrs['id']] = attrs['data-date']
        if tag == 'tool-tip' and attrs.get('for'):
            self.current = attrs['for']
            self.buffer = []

    def handle_data(self, data):
        if self.current:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.current:
            self.labels[self.current] = ''.join(self.buffer).strip()
            self.current = None

    def counts(self):
        result = {}
        for identifier, day in self.dates.items():
            label = self.labels.get(identifier, '')
            match = re.match(r'^(No|[\d,]+) contributions?\b', label)
            if match:
                result[day] = 0 if match[1] == 'No' else int(match[1].replace(',', ''))
        return result


def read_url(url, data=None, token=''):
    headers = {'User-Agent': 'MeazbahMehedi-profile-chart', 'Accept-Language': 'en-US'}
    if token:
        headers.update({'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode('utf-8')


def complete_rows(counts, start, days):
    rows = []
    for n in range(days):
        day = (start + timedelta(days=n)).isoformat()
        if day not in counts or type(counts[day]) is not int or counts[day] < 0:
            raise RuntimeError('Contribution calendar is incomplete; previous graph retained.')
        rows.append({'date': day, 'contributions': counts[day]})
    return rows


def fetch_rows(username, start, end, now, token=''):
    days = (end - start).days + 1
    if token:
        query = '''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'''
        payload = {'query': query, 'variables': {'login': username,
                   'from': start.isoformat() + 'T00:00:00Z', 'to': timestamp(now)}}
        try:
            data = json.loads(read_url('https://api.github.com/graphql', json.dumps(payload).encode(), token))
            if data.get('errors'):
                raise RuntimeError('GraphQL request failed')
            weeks = data['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
            counts = {day['date']: day['contributionCount'] for week in weeks for day in week['contributionDays']}
            return complete_rows(counts, start, days), 'GitHub GraphQL contribution calendar'
        except Exception:
            print('::warning::Contribution API unavailable; checking the public calendar.')
    counts = {}
    # Separate years make the fallback work across the December/January boundary.
    for year in range(start.year, end.year + 1):
        params = urllib.parse.urlencode({'from': max(start, date(year, 1, 1)).isoformat(),
                                        'to': min(end, date(year, 12, 31)).isoformat()})
        parser = CalendarParser()
        parser.feed(read_url('https://github.com/users/' + username + '/contributions?' + params))
        counts.update(parser.counts())
    return complete_rows(counts, start, days), 'GitHub public contribution calendar'


def render(rows, updated, light=False):
    bg, fg, muted, grid, accent = ('#ffffff','#1f2937','#576579','#d8dee7','#087f8c') if light else ('#0d1117','#edf4ff','#9dacc1','#29364a','#67e8d3')
    total = sum(row['contributions'] for row in rows)
    peak = max(row['contributions'] for row in rows)
    step = max(1, math.ceil(peak / 4)); maximum = 4 * step
    left, right, top, bottom = 56,1060,112,330
    points = []
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="460" viewBox="0 0 1100 460" role="img">',
             '<title>Recent GitHub contribution activity</title>',
             '<desc>' + escape(json.dumps(rows)) + '</desc>',
             '<style>.trace{stroke-dasharray:__LENGTH__;stroke-dashoffset:0;animation:draw 1.6s ease-out both}@keyframes draw{from{stroke-dashoffset:__LENGTH__}to{stroke-dashoffset:0}}@media(prefers-reduced-motion:reduce){.trace{animation:none}}</style>',
             f'<rect x=".5" y=".5" width="1099" height="459" rx="18" fill="{bg}" stroke="{grid}"/>',
             text(30,42,'CONTRIBUTION ACTIVITY / 31 DAYS',14,accent,700),
             text(30,74,rows[0]['date']+' — '+rows[-1]['date'],16,muted),
             text(1055,43,total,28,fg,700,'end'),text(1055,66,'CONTRIBUTIONS',10,muted,500,'end')]
    for i in range(5):
        y = bottom - i/4*(bottom-top)
        parts.extend([f'<path d="M{left} {y}H{right}" stroke="{grid}" stroke-dasharray="3 6"/>',text(left-12,y+4,i*step,11,muted,anchor='end')])
    for i,row in enumerate(rows):
        x = left + i*(right-left)/max(1,len(rows)-1)
        y = bottom-row['contributions']/maximum*(bottom-top)
        points.append((x,y))
    path = 'M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in points)
    area = path + f' L{right},{bottom} L{left},{bottom}Z'
    line_length = sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:]))
    parts += [f'<path d="{area}" fill="{accent}" opacity=".08"/>',f'<path class="trace" d="{path}" fill="none" stroke="{accent}" stroke-width="2.5" stroke-linejoin="round"/>']
    for row,(x,y) in zip(rows,points):
        parts.extend([f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{accent}"><title>{row["date"]}: {row["contributions"]} contributions</title></circle>',
                      text(f'{x:.2f}',f'{y-12:.2f}',row['contributions'],11,fg,500,'middle'),
                      text(f'{x:.2f}',355,row['date'][5:],10,muted,extra=f'transform="rotate(45 {x:.2f} 355)"')])
    parts += [text(30,419,'GitHub calendar counts · commits, pull requests, issues and other contributions',12,muted),text(30,442,'Updated '+updated,11,muted),'</svg>']
    return ''.join(parts).replace('__LENGTH__',f'{max(1,line_length):.2f}')


def main():
    username = os.environ.get('GITHUB_USERNAME', 'MeazbahMehedi')
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', username):
        raise RuntimeError('Invalid GitHub username')
    now = datetime.now(UTC).replace(microsecond=0)
    end = now.date(); start = end-timedelta(days=30)
    rows,source = fetch_rows(username,start,end,now,os.environ.get('GITHUB_TOKEN',''))
    updated = timestamp(now)
    outputs = {'assets/activity-dark.svg':render(rows,updated),
               'assets/activity-light.svg':render(rows,updated,True),
               'data/contributions.json':json.dumps({'username':username,'updated_at':updated,'source':source,'days':rows},indent=2)+'\n'}
    for filename,content in outputs.items():
        path = ROOT/filename
        temp = path.with_suffix(path.suffix+'.tmp')
        temp.write_text(content,encoding='utf-8'); temp.replace(path)
    print(f'Refreshed real contribution activity for {len(rows)} dates.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('::error::Could not refresh complete contribution data; previous graph retained.',file=sys.stderr)
        sys.exit(1)
