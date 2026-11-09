"""Render the profile stats card: 31-day totals and top languages.

Totals come from data/daily-commits.json and data/contributions.json, which the
other refresh scripts write earlier in the same workflow run. Language shares
come from GitHub's repository languages API; if that request fails, the last
saved data/languages.json is reused so the card keeps its previous values.
"""
import json
import os
import re
import sys
from datetime import datetime

from profile_theme import REDUCED_MOTION, ROOT, THEMES, svg_open, text, write_atomic
from update_commits import UTC, get_json, timestamp

WIDTH, HEIGHT = 1100, 340
DIGIT_HEIGHT = 46
TOP_LANGUAGES = 5
BAR_LEFT, BAR_RIGHT = 600, 1070


def longest_streak(days, key='contributions'):
    best = current = 0
    for day in days:
        current = current + 1 if day[key] > 0 else 0
        best = max(best, current)
    return best


def summarize(commit_days, contribution_days):
    return [
        (sum(day['commits'] for day in commit_days), 'public commits'),
        (sum(day['contributions'] for day in contribution_days), 'contributions'),
        (sum(day['contributions'] > 0 for day in contribution_days), 'days with contributions'),
        (longest_streak(contribution_days), 'day contribution streak'),
    ]


def fetch_languages(username, token='', fetch=None):
    """Sum language bytes across the user's own, non-fork public repositories."""
    fetch = fetch or (lambda url: get_json(url, token))
    repos = fetch(f'https://api.github.com/users/{username}/repos?type=owner&per_page=100')
    totals = {}
    counted = 0
    for repo in repos:
        if repo.get('fork') or repo.get('name', '').lower() == username.lower():
            continue   # forks are not the user's code; the profile repository is not a project
        url = repo.get('languages_url', '')
        if not url.startswith('https://api.github.com/repos/'):
            continue
        for language, size in fetch(url).items():
            totals[language] = totals.get(language, 0) + int(size)
        counted += 1
    return totals, counted


def top_shares(totals, limit=TOP_LANGUAGES, minimum=0.01):
    """Largest languages first; anything past the limit or under 1% becomes Other."""
    total = sum(totals.values())
    if not total:
        return []
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    shown = [(name, size) for name, size in ranked[:limit] if size / total >= minimum]
    shares = [(name, size / total) for name, size in shown]
    rest = total - sum(size for _, size in shown)
    if rest:
        shares.append(('Other', rest / total))
    return shares


def _odometer(x, baseline, value, colors, key):
    """Each digit is a column of 0-9 that rolls up to its value.

    The transform attribute already holds the final position, so the number is
    correct even where CSS animation does not run.
    """
    parts = []
    digit_width = 25
    for position, digit in enumerate(str(value)):
        left = x + position * digit_width
        clip = f'{key}d{position}'
        offset = int(digit) * DIGIT_HEIGHT
        parts.append(f'<clipPath id="{clip}"><rect x="{left}" y="{baseline - 38}" '
                     f'width="{digit_width}" height="{DIGIT_HEIGHT}"/></clipPath>')
        column = ''.join(text(left, baseline + n * DIGIT_HEIGHT, n, 40, colors['fg'], 700) for n in range(10))
        parts.append(f'<g clip-path="url(#{clip})"><g class="roll r{digit}" '
                     f'style="animation-delay:{position * 0.08:.2f}s" '
                     f'transform="translate(0 -{offset})">{column}</g></g>')
    return ''.join(parts)


def render(stats, shares, updated, repo_count, light=False):
    colors = THEMES['light' if light else 'dark']
    rolls = ''.join(f'@keyframes r{d}{{from{{transform:translateY(0)}}to{{transform:translateY(-{d * DIGIT_HEIGHT}px)}}}}'
                    f'.r{d}{{animation:r{d} 1.4s cubic-bezier(.2,.8,.2,1) both}}' for d in range(10))
    span = BAR_RIGHT - BAR_LEFT - 8
    lengths = [max(1.0, span * share) for _, share in shares]
    # One keyframe per bar with a literal length; CSS variables inside @keyframes
    # are not supported by every browser that renders README images.
    grows = ''.join(f'@keyframes g{i}{{from{{stroke-dashoffset:{length:.1f}}}to{{stroke-dashoffset:0}}}}'
                    f'.g{i}{{animation:g{i} 1.4s cubic-bezier(.2,.8,.2,1) {i * 0.1:.1f}s both}}'
                    for i, length in enumerate(lengths))
    style = rolls + grows + f'{REDUCED_MOTION}{{.roll,.fill{{animation:none}}}}'
    parts = svg_open(WIDTH, HEIGHT, 'Profile stats for the last 31 days and top languages', style)
    parts += [f'<desc>{"; ".join(f"{value} {label}" for value, label in stats)}. Languages: '
              f'{"; ".join(f"{name} {share:.1%}" for name, share in shares) or "unavailable"}.</desc>',
              f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="18" fill="{colors["bg"]}" stroke="{colors["grid"]}"/>',
              text(30, 42, 'PROFILE STATS / 31 DAYS', 14, colors['accent'], 700),
              text(BAR_LEFT, 42, 'TOP LANGUAGES', 14, colors['accent'], 700)]
    for index, (value, label) in enumerate(stats):
        x = 30 + (index % 2) * 275
        y = 66 + (index // 2) * 124
        parts += [f'<rect x="{x}" y="{y}" width="255" height="108" rx="12" fill="{colors["panel"]}" stroke="{colors["grid"]}"/>',
                  _odometer(x + 22, y + 58, value, colors, f's{index}'),
                  text(x + 22, y + 88, label, 13, colors['muted'], 500)]
    if shares:
        for index, ((name, share), length) in enumerate(zip(shares, lengths)):
            y = 84 + index * 38
            color = colors['muted'] if name == 'Other' else (colors['accent'] if index % 2 == 0 else colors['accent2'])
            parts += [text(BAR_LEFT, y, name, 14, colors['fg'], 500),
                      text(BAR_RIGHT, y, f'{share:.1%}', 13, colors['muted'], 500, 'end'),
                      f'<line x1="{BAR_LEFT + 4}" y1="{y + 12}" x2="{BAR_RIGHT - 4}" y2="{y + 12}" '
                      f'stroke="{colors["grid"]}" stroke-width="8" stroke-linecap="round"/>',
                      f'<line class="fill g{index}" x1="{BAR_LEFT + 4}" y1="{y + 12}" x2="{BAR_LEFT + 4 + length:.1f}" '
                      f'y2="{y + 12}" stroke="{color}" stroke-width="8" stroke-linecap="round" '
                      f'stroke-dasharray="{length:.1f} {length + 20:.1f}"/>']
        note = f'Share of code bytes across {repo_count} public repositories'
    else:
        parts.append(text(BAR_LEFT, 96, 'Language data appears after the next refresh.', 14, colors['muted']))
        note = 'Language data unavailable'
    parts += [text(30, HEIGHT - 20, f'Public default-branch commits and GitHub calendar contributions · {note} · Updated {updated}',
                   11, colors['muted']), '</svg>']
    return ''.join(parts)


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding='utf-8'))


def main():
    username = os.environ.get('GITHUB_USERNAME', 'MeazbahMehedi')
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', username):
        raise RuntimeError('Invalid GitHub username')
    now = timestamp(datetime.now(UTC).replace(microsecond=0))
    stats = summarize(load_json('data/daily-commits.json')['days'], load_json('data/contributions.json')['days'])
    try:
        totals, repo_count = fetch_languages(username, os.environ.get('GITHUB_TOKEN', ''))
        if not totals:
            raise RuntimeError('No language data returned')
        languages = {'username': username, 'updated_at': now, 'source': 'GitHub repository languages API',
                     'repositories': repo_count, 'bytes': dict(sorted(totals.items()))}
        write_atomic('data/languages.json', json.dumps(languages, indent=2) + '\n')
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        print(f'::warning::Language refresh failed ({error}); keeping the last saved language data.')
        path = ROOT / 'data/languages.json'
        languages = load_json('data/languages.json') if path.exists() else {'bytes': {}, 'repositories': 0}
    shares = top_shares(languages['bytes'])
    for theme, light in (('dark', False), ('light', True)):
        write_atomic(f'assets/stats-{theme}.svg', render(stats, shares, now, languages['repositories'], light))
    print(f'Refreshed stats card: {", ".join(f"{v} {label}" for v, label in stats)}; {len(shares)} language rows.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        print(f'::error::{error}', file=sys.stderr)
        sys.exit(1)
