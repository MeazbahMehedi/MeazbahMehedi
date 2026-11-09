"""Shared colours and SVG helpers for the profile artwork."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

THEMES = {
    'dark': {'bg': '#0d1117', 'panel': '#111a24', 'fg': '#edf4ff', 'muted': '#9dacc1',
             'grid': '#29364a', 'accent': '#67e8d3', 'accent2': '#a78bfa'},
    'light': {'bg': '#ffffff', 'panel': '#f6f8fa', 'fg': '#1f2937', 'muted': '#576579',
              'grid': '#d8dee7', 'accent': '#087f8c', 'accent2': '#6d28d9'},
}

SANS = 'DejaVu Sans,Segoe UI,Arial,sans-serif'
MONO = 'DejaVu Sans Mono,Menlo,Consolas,monospace'
REDUCED_MOTION = '@media(prefers-reduced-motion:reduce)'


def text(x, y, value, size=15, color='#b6c7dd', weight=400, anchor='start', extra='', family=SANS):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}" {extra}>'
            f'{escape(str(value))}</text>')


def svg_open(width, height, title, style=''):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" role="img">', f'<title>{escape(title)}</title>']
    if style:
        parts.append(f'<style>{style}</style>')
    return parts


def write_atomic(relative_path, content):
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(content, encoding='utf-8')
    temp.replace(path)
