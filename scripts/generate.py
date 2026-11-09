#!/usr/bin/env python3
"""Generate a self-contained animated GitHub contribution SVG (stdlib only)."""
import argparse
import datetime as dt
import json
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

QUERY = '''query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar { weeks { contributionDays { date contributionCount contributionLevel } } } } } }'''

def fetch(login, token):
    payload = json.dumps({'query': QUERY, 'variables': {'login': login}}).encode()
    request = urllib.request.Request('https://api.github.com/graphql', data=payload,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'nagi-cyber-ship/0.1'})
    with urllib.request.urlopen(request, timeout=25) as response:
        data = json.load(response)
    if data.get('errors') or not data.get('data', {}).get('user'):
        raise RuntimeError(f'GitHub GraphQL failed: {data.get("errors", "user not found")}')
    return data['data']['user']['contributionsCollection']['contributionCalendar']['weeks']

def demo_weeks():
    today = dt.date.today()
    start = today - dt.timedelta(days=364 + (today.weekday() + 1) % 7)
    result = []
    for w in range(53):
        days = []
        for d in range(7):
            date = start + dt.timedelta(days=w*7+d)
            count = (w * 13 + d * 17) % 11 if date <= today else 0
            days.append({'date': date.isoformat(), 'contributionCount': count})
        result.append({'contributionDays': days})
    return result

def generate(weeks, login):
    cell, gap, left, top = 11, 4, 35, 45
    step = cell + gap
    count = len(weeks)
    width = left + count * step + 30
    height = 185
    colors = ['#162337','#174665','#146c91','#189bc4','#55dfff']
    cells = []
    path = []
    timeline = []
    for x, week in enumerate(weeks):
        for y, day in enumerate(week['contributionDays']):
            if y > 6: continue
            cx, cy = left + x*step, top + y*step
            level = min(4, max(0, int(day.get('contributionCount', 0)) // 3 + (1 if day.get('contributionCount', 0) else 0)))
            cells.append((cx, cy, level, day.get('date','')))
    # Serpentine flight, spanning every week and day, with one trail pulse per cell.
    for x in range(count):
        for y in (range(7) if x % 2 == 0 else range(6, -1, -1)):
            cx, cy = left + x*step + cell/2, top + y*step + cell/2
            path.append((cx, cy))
    total = len(path)
    duration = 28
    # Each cell gets a brief cyan afterglow when the ship reaches it.
    order = {}
    for idx, (px, py) in enumerate(path):
        order[(round(px, 1), round(py, 1))] = idx
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Nagi Cyber Ship flying across {escape(login)} GitHub contributions">',
      '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#07111f"/><stop offset="1" stop-color="#0d2440"/></linearGradient><filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3"/></filter></defs>',
      f'<rect width="{width}" height="{height}" rx="16" fill="url(#bg)"/>',
      '<text x="22" y="25" fill="#8edcff" font-family="monospace" font-size="13" font-weight="bold">NAGI // CYBER SHIP</text>',
      '<text x="22" y="167" fill="#63829e" font-family="monospace" font-size="10">CONTRIBUTION FLIGHT • ICE BLUE TRAIL</text>']
    for x,y,level,date in cells:
        t = order.get((round(x+cell/2,1),round(y+cell/2,1)),0)/total
        # loop-safe glow with begin offset and repeat cycle
        parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{colors[level]}"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="#a4f3ff" opacity="0"><animate attributeName="opacity" values="0;0;0.95;0.55;0" keyTimes="0;{max(0,t-0.0001):.5f};{t:.5f};{min(1,t+0.045):.5f};1" dur="{duration}s" repeatCount="indefinite"/></rect>')
    d = 'M ' + ' L '.join(f'{x:g} {y:g}' for x,y in path)
    parts += [f'<path id="flight" d="{d}" fill="none" stroke="none"/>',
      '<g><ellipse cx="-8" cy="0" rx="16" ry="5" fill="#29b6f6" opacity=".55" filter="url(#glow)"/>',
      '<path d="M -13 -6 L 10 0 L -13 6 L -7 0 Z" fill="#4bdcff" stroke="#c2f7ff" stroke-width="1"/>',
      '<path d="M -10 -3 L -3 0 L -10 3" fill="none" stroke="#07395d" stroke-width="2"/>',
      '<circle cx="-8" cy="0" r="2" fill="#e0ffff"/>',
      f'<animateMotion dur="{duration}s" repeatCount="indefinite" rotate="auto"><mpath href="#flight" xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="#flight"/></animateMotion></g>',
      '</svg>']
    return '\n'.join(parts)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--login', default=os.getenv('GITHUB_REPOSITORY_OWNER', 'seraphforge'))
    parser.add_argument('--output', default='dist/nagi-cyber-ship.svg')
    parser.add_argument('--demo', action='store_true', help='Generate sample data without network access')
    args = parser.parse_args()
    token = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
    if not args.demo and not token:
        parser.error('GH_TOKEN or GITHUB_TOKEN required for live contributions; use --demo for offline preview')
    weeks = demo_weeks() if args.demo else fetch(args.login, token)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generate(weeks, args.login), encoding='utf-8')
    print(f'Generated {output} ({len(weeks)} weeks, {"demo" if args.demo else "live"} data)')

if __name__ == '__main__': main()
