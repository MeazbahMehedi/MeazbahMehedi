"""Build the animated profile artwork from data/projects.json.

Outputs, each in a dark and a light variant:
  assets/tagline-*.svg       typing tagline cycling through the configured phrases
  assets/project-<slug>-*.svg one card per featured project
  assets/divider-*.svg       section divider with a passing shooting star
  assets/footer-*.svg        closing line with twinkling stars

Animations use SMIL so they also play in Safari. Every file carries a
prefers-reduced-motion rule that swaps the motion for a still frame.
Python standard library only; the output is deterministic.
"""
from html import escape
import json
import random
import textwrap

from profile_theme import MONO, REDUCED_MOTION, ROOT, THEMES, svg_open, text, write_atomic

TAGLINE_WIDTH, TAGLINE_HEIGHT = 1200, 64
TAGLINE_FONT = 26
CHAR_WIDTH = TAGLINE_FONT * 0.6          # monospace advance; enforced with textLength
SLOT_SECONDS = 5.0                       # time each phrase owns in the cycle
TYPE_STEP, ERASE_STEP = 0.065, 0.025     # seconds per character

CARD_WIDTH, CARD_HEIGHT = 600, 260
DESCRIPTION_CHARS = 72
MAX_DESCRIPTION_LINES = 3


def _discrete(points, duration):
    """Turn (seconds, value) pairs into SMIL keyTimes/values for calcMode=discrete."""
    times, values = [], []
    for seconds, value in sorted(points, key=lambda point: point[0]):
        key = round(seconds / duration, 5)
        if times and key <= times[-1]:
            values[-1] = value
            continue
        times.append(key)
        values.append(value)
    if times[-1] < 1:
        times.append(1)
        values.append(values[-1])
    return ';'.join(f'{t:g}' for t in times), ';'.join(f'{v:g}' for v in values)


def _animate(attribute, points, duration, extra=''):
    key_times, values = _discrete(points, duration)
    return (f'<animate attributeName="{attribute}" calcMode="discrete" dur="{duration:g}s" '
            f'repeatCount="indefinite" keyTimes="{key_times}" values="{values}" {extra}/>')


def tagline_timeline(length, start):
    """Width keyframes for one phrase: type, hold, erase, all inside its slot."""
    typed = length * TYPE_STEP
    erase_start = start + SLOT_SECONDS - 0.3 - length * ERASE_STEP
    if erase_start - (start + typed) < 1.0:
        raise ValueError('Tagline phrase is too long to read within its slot.')
    points = [(0, 0), (start, 0)]
    points += [(start + k * TYPE_STEP, k) for k in range(1, length + 1)]
    points += [(erase_start + (length - k) * ERASE_STEP, k) for k in range(length - 1, -1, -1)]
    return points


def render_tagline(phrases, theme):
    colors = THEMES[theme]
    longest = max(len(phrase) for phrase in phrases)
    block = (2 + longest) * CHAR_WIDTH
    prompt_x = (TAGLINE_WIDTH - block) / 2
    text_x = prompt_x + 2 * CHAR_WIDTH
    baseline = 42
    cycle = SLOT_SECONDS * len(phrases)
    style = f'.still{{display:none}}{REDUCED_MOTION}{{.motion{{display:none}}.still{{display:inline}}}}'
    parts = svg_open(TAGLINE_WIDTH, TAGLINE_HEIGHT, 'Tagline: ' + ' / '.join(phrases), style)
    parts.append(text(f'{prompt_x:.1f}', baseline, '>', TAGLINE_FONT, colors['accent'], 700, family=MONO))
    parts.append('<g class="motion">')
    for index, phrase in enumerate(phrases):
        start = index * SLOT_SECONDS
        steps = tagline_timeline(len(phrase), start)
        width = [(t, k * CHAR_WIDTH) for t, k in steps]
        cursor = [(t, text_x + k * CHAR_WIDTH) for t, k in steps]
        visible = [(0, 0), (start, 1), (start + SLOT_SECONDS, 0)]
        length = len(phrase) * CHAR_WIDTH
        # Static attribute values are the fallback when SMIL does not run:
        # the first phrase shows in full and the others stay hidden.
        first = index == 0
        parts += [
            f'<clipPath id="type{index}"><rect x="{text_x:.1f}" y="0" '
            f'width="{length if first else 0:.1f}" height="{TAGLINE_HEIGHT}">',
            _animate('width', width, cycle), '</rect></clipPath>',
            f'<g opacity="{1 if first else 0}">{_animate("opacity", visible, cycle)}',
            text(f'{text_x:.1f}', baseline, phrase, TAGLINE_FONT, colors['fg'], 400, family=MONO,
                 extra=f'textLength="{length:.1f}" lengthAdjust="spacingAndGlyphs" '
                       f'xml:space="preserve" clip-path="url(#type{index})"'),
            f'<rect x="{text_x + (length if first else 0):.1f}" y="{baseline - 23}" width="3" height="29" fill="{colors["accent"]}">',
            _animate('x', cursor, cycle),
            _animate('opacity', [(0, 1), (0.5, 0)], 1.0),
            '</rect></g>',
        ]
    first = phrases[0]
    parts += ['</g><g class="still">',
              text(f'{text_x:.1f}', baseline, first, TAGLINE_FONT, colors['fg'], 400, family=MONO,
                   extra=f'textLength="{len(first) * CHAR_WIDTH:.1f}" lengthAdjust="spacingAndGlyphs" '
                         'xml:space="preserve"'),
              '</g></svg>']
    return ''.join(parts)


def _rounded_rect_path(x, y, width, height, radius):
    return (f'M{x + radius} {y}H{x + width - radius}A{radius} {radius} 0 0 1 {x + width} {y + radius}'
            f'V{y + height - radius}A{radius} {radius} 0 0 1 {x + width - radius} {y + height}'
            f'H{x + radius}A{radius} {radius} 0 0 1 {x} {y + height - radius}'
            f'V{y + radius}A{radius} {radius} 0 0 1 {x + radius} {y}Z')


def chip_width(label, size=12):
    return round(len(label) * size * 0.6 + 22)


def render_card(project, theme, index=0):
    colors = THEMES[theme]
    lines = textwrap.wrap(project['description'], DESCRIPTION_CHARS)
    if len(lines) > MAX_DESCRIPTION_LINES:
        raise ValueError(f'Description for {project["name"]} needs more than {MAX_DESCRIPTION_LINES} lines.')
    outline = _rounded_rect_path(1, 1, CARD_WIDTH - 2, CARD_HEIGHT - 2, 16)
    # Content is never animated in: browsers may skip animations for images that load
    # off screen, and a card must stay readable even if motion never runs.
    style = f'{REDUCED_MOTION}{{.sweep{{display:none}}}}'
    parts = svg_open(CARD_WIDTH, CARD_HEIGHT, f'{project["name"]}: {project["summary"]}', style)
    summary = f'{project["description"]} Built with {", ".join(project["stack"])}.'
    parts += [f'<desc>{escape(summary)}</desc>',
              f'<path d="{outline}" fill="{colors["panel"]}" stroke="{colors["grid"]}"/>',
              f'<path class="sweep" d="{outline}" fill="none" stroke="{colors["accent"]}" stroke-width="2" '
              f'stroke-linecap="round" pathLength="1000" stroke-dasharray="120 880" opacity=".9">'
              f'<animate attributeName="stroke-dashoffset" values="0;-1000" dur="8s" '
              f'begin="-{index * 2}s" repeatCount="indefinite"/></path>',
              '<g>',
              f'<circle cx="38" cy="40" r="5" fill="{colors["accent"]}"/>',
              text(52, 45, project['category'], 12, colors['accent'], 700, extra='letter-spacing="1.5"'),
              text(CARD_WIDTH - 32, 45, 'Repository ↗', 12, colors['muted'], 500, 'end'),
              text(32, 86, project['name'], 26, colors['fg'], 700),
              text(32, 112, project['summary'], 15, colors['accent2'], 500)]
    for number, line in enumerate(lines):
        parts.append(text(32, 144 + number * 21, line, 14, colors['muted']))
    x = 32
    for label in project['stack']:
        width = chip_width(label)
        parts += [f'<rect x="{x}" y="204" width="{width}" height="26" rx="13" fill="none" stroke="{colors["grid"]}"/>',
                  text(x + width / 2, 221, label, 12, colors['fg'], 500, 'middle')]
        x += width + 8
    if x > CARD_WIDTH - 24:
        raise ValueError(f'Stack chips for {project["name"]} do not fit on one line.')
    parts.append('</g></svg>')
    return ''.join(parts)


def render_divider(theme):
    colors = THEMES[theme]
    width, height, middle = 1200, 28, 14
    style = f'{REDUCED_MOTION}{{.star{{display:none}}}}'
    parts = svg_open(width, height, 'Section divider', style)
    parts += ['<defs>',
              f'<linearGradient id="rule" x2="1"><stop offset="0" stop-color="{colors["grid"]}" stop-opacity="0"/>'
              f'<stop offset=".5" stop-color="{colors["grid"]}"/>'
              f'<stop offset="1" stop-color="{colors["grid"]}" stop-opacity="0"/></linearGradient>',
              f'<linearGradient id="tail" x2="1"><stop offset="0" stop-color="{colors["accent"]}" stop-opacity="0"/>'
              f'<stop offset="1" stop-color="{colors["accent"]}"/></linearGradient>',
              '</defs>',
              f'<rect x="0" y="{middle - 0.5}" width="{width}" height="1" fill="url(#rule)"/>',
              '<g class="star"><g transform="translate(-200 0)">',
              '<animateTransform attributeName="transform" type="translate" dur="7s" repeatCount="indefinite" '
              'calcMode="spline" keyTimes="0;.4;1" values="-200 0;1400 0;1400 0" keySplines=".45 0 .55 1;0 0 1 1"/>',
              f'<rect x="-150" y="{middle - 1}" width="150" height="2" rx="1" fill="url(#tail)"/>',
              f'<circle cx="0" cy="{middle}" r="5" fill="{colors["accent"]}" opacity=".25"/>',
              f'<circle cx="0" cy="{middle}" r="2.2" fill="{colors["accent"]}"/>',
              '</g></g></svg>']
    return ''.join(parts)


def render_footer(theme, message='Always learning. Always building.'):
    colors = THEMES[theme]
    width, height = 1200, 96
    rng = random.Random(7)   # fixed seed keeps the output stable between runs
    # CSS keyframes rather than SMIL here, so the reduced-motion rule can stop them.
    style = ('.star{opacity:.5;animation:twinkle ease-in-out infinite}'
             '@keyframes twinkle{0%,100%{opacity:.12}50%{opacity:.9}}'
             f'{REDUCED_MOTION}{{.star{{animation:none}}}}')
    parts = svg_open(width, height, message, style)
    parts.append(f'<path d="M0 1H{width}" stroke="{colors["grid"]}"/>')
    for _ in range(26):
        x = rng.choice([rng.uniform(20, 380), rng.uniform(820, 1180)])
        y = rng.uniform(14, height - 10)
        duration = rng.uniform(2.4, 5.0)
        parts.append(f'<circle class="star" cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(0.7, 1.7):.2f}" '
                     f'fill="{colors["fg"]}" style="animation-duration:{duration:.2f}s;'
                     f'animation-delay:-{rng.uniform(0, duration):.2f}s"/>')
    parts += [text(width / 2, 56, message, 17, colors['muted'], 400, 'middle'), '</svg>']
    return ''.join(parts)


def build(config):
    outputs = {}
    for theme in THEMES:
        outputs[f'assets/tagline-{theme}.svg'] = render_tagline(config['taglines'], theme)
        outputs[f'assets/divider-{theme}.svg'] = render_divider(theme)
        outputs[f'assets/footer-{theme}.svg'] = render_footer(theme)
        for index, project in enumerate(config['projects']):
            outputs[f'assets/project-{project["slug"]}-{theme}.svg'] = render_card(project, theme, index)
    return outputs


def main():
    config = json.loads((ROOT / 'data/projects.json').read_text(encoding='utf-8'))
    outputs = build(config)
    for path, content in outputs.items():
        write_atomic(path, content)
    print(f'Built {len(outputs)} profile artwork files.')


if __name__ == '__main__':
    main()
