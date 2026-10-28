"""Build an animated daily chart from real public commit search results.

Python standard library only. API failures preserve the last valid chart.
Dates use the Git author timestamp converted to UTC. Duplicate SHAs count once.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
from html import escape
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import time as clock
import urllib.error
import urllib.parse
import urllib.request

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]


def timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def get_json(url: str, token: str = '') -> dict:
    headers = {'Accept': 'application/vnd.github+json',
               'User-Agent': 'MeazbahMehedi-profile-chart',
               'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f'GitHub API returned HTTP {error.code}; previous charts retained.') from None
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError('GitHub API unavailable; previous charts retained.') from None
        clock.sleep(2 ** attempt)
    raise RuntimeError('Unable to read GitHub data.')


def search_commits(username: str, start: datetime, end: datetime,
                   token: str = '', fetch=None) -> list[dict]:
    """Paginate results, subdividing time ranges to avoid GitHub's 1,000 cap."""
    fetch = fetch or (lambda url: get_json(url, token))
    query = f'author:{username} is:public author-date:{timestamp(start)}..{timestamp(end)}'

    def page(number):
        params = urllib.parse.urlencode({'q': query, 'per_page': 100,
                                        'page': number, 'sort': 'author-date', 'order': 'asc'})
        result = fetch('https://api.github.com/search/commits?' + params)
        if result.get('incomplete_results') is not False:
            raise RuntimeError('GitHub returned incomplete search results; previous charts retained.')
        if not isinstance(result.get('items'), list) or type(result.get('total_count')) is not int:
            raise RuntimeError('Unexpected GitHub search response; previous charts retained.')
        return result

    first = page(1)
    total = first['total_count']
    if total > 1000:
        seconds = int((end - start).total_seconds())
        if seconds < 1:
            raise RuntimeError('Too many commits in one second to count accurately.')
        middle = start + timedelta(seconds=seconds // 2)
        return (search_commits(username, start, middle, token, fetch)
                + search_commits(username, middle + timedelta(seconds=1), end, token, fetch))
    items = list(first['items'])
    for number in range(2, math.ceil(total / 100) + 1):
        following = page(number)
        if following['total_count'] != total:
            raise RuntimeError('Search index changed during pagination. Please run again.')
        items.extend(following['items'])
    if len(items) != total:
        raise RuntimeError('Search page count mismatch; previous charts retained.')
    return items


def aggregate(items: list[dict], start: date, days: int) -> list[dict]:
    counts = {start + timedelta(days=n): 0 for n in range(days)}
    seen = set()
    for item in items:
        sha = item['sha']
        if sha in seen:
            continue
        seen.add(sha)
        authored = datetime.fromisoformat(item['commit']['author']['date'].replace('Z', '+00:00'))
        if authored.tzinfo is None:
            raise ValueError('Commit date has no timezone.')
        day = authored.astimezone(UTC).date()
        if day in counts:
            counts[day] += 1
    return [{'date': day.isoformat(), 'commits': count} for day, count in counts.items()]


def text(x, y, value, size=15, color='#b6c7dd', weight=400, anchor='start', extra=''):
    return (f'<text x="{x}" y="{y}" font-family="DejaVu Sans,Arial,sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}" {extra}>{escape(str(value))}</text>')


def render_chart(rows: list[dict], username: str, updated: str, light=False) -> str:
    bg, panel, fg, muted, grid, accent = (
        ('#ffffff', '#f6f8fa', '#1f2937', '#576579', '#d8dee7', '#087f8c') if light else
        ('#0d1117', '#121e2e', '#edf4ff', '#9dacc1', '#29364a', '#67e8d3'))
    total = sum(row['commits'] for row in rows)
    active = sum(row['commits'] > 0 for row in rows)
    best = max(row['commits'] for row in rows)
    step = max(1, math.ceil(best / 4))
    maximum = step * 4
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="470" viewBox="0 0 1100 470" role="img" aria-labelledby="title desc">',
             f'<title id="title">{escape(username)}: public commits per day</title>',
             f'<desc id="desc">{escape(json.dumps(rows))}. UTC author dates. Unique public indexed commits on default branches. Updated {escape(updated)}.</desc>',
             '<style>.bar{animation:grow 1.1s ease-out both;transform-box:fill-box;transform-origin:center bottom}@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}@media(prefers-reduced-motion:reduce){.bar{animation:none}}</style>',
             f'<rect x=".5" y=".5" width="1099" height="469" rx="18" fill="{bg}" stroke="{grid}"/>',
             text(30, 42, 'PUBLIC COMMITS / DAILY', 14, accent, 700),
             text(30, 74, f'{rows[0]["date"]} — {rows[-1]["date"]}  ·  UTC', 16, muted)]
    for x, value, label in [(755, total, 'TOTAL'), (880, active, 'ACTIVE DAYS'), (1015, best, 'BEST DAY')]:
        parts += [text(x, 43, value, 26, fg, 700, 'middle'),
                  text(x, 65, label, 10, muted, 500, 'middle')]
    left, right, top, bottom = 56, 1060, 122, 342
    for tick in range(5):
        value = tick * step
        y = bottom - (value / maximum) * (bottom - top)
        parts += [f'<path d="M{left} {y}H{right}" stroke="{grid}" stroke-dasharray="3 6"/>',
                  text(left - 12, y + 4, value, 11, muted, anchor='end')]
    slot = (right - left) / len(rows)
    for index, row in enumerate(rows):
        x = left + slot * index + slot / 2
        height = row['commits'] / maximum * (bottom - top)
        title = f'{row["date"]}: {row["commits"]} public commits'
        parts.append(f'<g><title>{escape(title)}</title>')
        if row['commits']:
            parts.append(f'<rect class="bar" x="{x-slot*.30:.2f}" y="{bottom-height:.2f}" width="{slot*.60:.2f}" height="{height:.2f}" rx="3" fill="{accent}" style="animation-delay:{index*.018:.3f}s"/>')
        else:
            parts.append(f'<circle cx="{x:.2f}" cy="{bottom}" r="2" fill="{muted}"/>')
        parts += [text(f'{x:.2f}', f'{bottom-height-9:.2f}', row['commits'], 11, fg, 600, 'middle'),
                  text(f'{x:.2f}', 368, row['date'][5:], 10, muted,
                       extra=f'transform="rotate(45 {x:.2f} 368)"'), '</g>']
    parts += [text(30, 429, 'Unique public commits · indexed default branches · author timestamps in UTC', 12, muted),
              text(30, 451, 'Updated ' + updated, 11, muted), '</svg>']
    return ''.join(parts)


def write_outputs(rows: list[dict], username: str, root: Path, updated: str):
    """Prepare every output before replacing a previous valid snapshot."""
    data = {'username': username, 'updated_at': updated, 'timezone': 'UTC',
            'source': 'GitHub REST commit search',
            'scope': 'Unique SHA; public indexed default-branch commits; Git author date in UTC. Includes merge commits.',
            'days': rows}
    csv_buffer = io.StringIO(newline='')
    writer = csv.DictWriter(csv_buffer, fieldnames=['date', 'commits'])
    writer.writeheader(); writer.writerows(rows)
    table = '# Public commits per day\n\nUTC author dates. Public indexed default branches; duplicate SHAs count once. Includes merge commits.\n\n'
    table += '| Date (UTC) | Commits |\n| --- | ---: |\n'
    table += ''.join(f'| {row["date"]} | {row["commits"]} |\n' for row in rows)
    table += f'\nUpdated: {updated}\n'
    outputs = {'assets/daily-commits-dark.svg': render_chart(rows, username, updated),
               'assets/daily-commits-light.svg': render_chart(rows, username, updated, True),
               'data/daily-commits.json': json.dumps(data, indent=2) + '\n',
               'data/daily-commits.csv': csv_buffer.getvalue(),
               'data/DAILY-COMMITS.md': table}
    for filename, content in outputs.items():
        target = root / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + '.tmp')
        temporary.write_text(content, encoding='utf-8')
        temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default=os.environ.get('GITHUB_USERNAME', 'MeazbahMehedi'))
    parser.add_argument('--days', type=int, default=31)
    parser.add_argument('--output', type=Path, default=ROOT)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', args.username):
        parser.error('Invalid GitHub username')
    if not 1 <= args.days <= 90:
        parser.error('Days must be between 1 and 90')
    now = datetime.now(UTC).replace(microsecond=0)
    start = datetime.combine(now.date() - timedelta(days=args.days - 1), time.min, UTC)
    token = os.environ.get('GITHUB_TOKEN', '')
    items = search_commits(args.username, start, now, token)
    rows = aggregate(items, start.date(), args.days)
    write_outputs(rows, args.username, args.output, timestamp(now))
    print(f'Refreshed {len(rows)} dates from {len(items)} search results; {sum(r["commits"] for r in rows)} unique public commits.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        print(f'::error::{error}', file=sys.stderr)
        sys.exit(1)
