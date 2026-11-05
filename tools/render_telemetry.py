#!/usr/bin/env python3
"""
AVANI.EXE — self-hosted telemetry renderer.

Generates assets/stats.svg and assets/snake.svg from the GitHub API using
ONLY the Python standard library (no pip, no third-party actions).

Design contract (senior-dev rules):
  * Zero runtime third-party dependencies in the README. Every image the
    profile loads lives in assets/ and is served by GitHub itself.
  * Fail-safe: on any error the script exits non-zero WITHOUT touching the
    existing SVGs, so the profile always shows the last-good render.
    (Worst case = stale data. Never a broken image.)
  * Atomic writes: SVGs are rendered to a temp file, XML-validated, then
    moved into place.

Runs in GitHub Actions with GH_TOKEN=${{ github.token }} (daily schedule,
manual dispatch, or push). Also runs locally with any token that can read
public data:  GH_TOKEN=ghp_xxx python3 tools/render_telemetry.py
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.request
import xml.dom.minidom

USER = "Avani376"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""

# ---------------------------------------------------------------- palette
BG, PANEL, PANEL2, LINE = "#05070f", "#0a101f", "#0d1526", "#1c2a44"
CYAN, VIOLET, LIME, AMBER, PINK = "#00f0ff", "#a78bfa", "#4ade80", "#fbbf24", "#f472b6"
TXT, DIM, DIM2 = "#e6f1ff", "#7c8db0", "#44536e"
FONT = "'Cascadia Code','JetBrains Mono',Consolas,'Courier New',monospace"
LEVELS = ["#14243c", "#155e75", "#0891b2", "#22d3ee", "#a5f3fc"]  # cyan ramp

GRAPHQL = "https://api.github.com/graphql"
API = "https://api.github.com"


# ---------------------------------------------------------------- fetching
def _post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "avani376-telemetry-renderer",
            "Accept": "application/vnd.github+json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _get(url):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "avani376-telemetry-renderer",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch_data():
    """One GraphQL call for everything; REST fallback for the profile totals."""
    q = """
    query {
      user(login: "%s") {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
        repositories(ownerAffiliations: OWNER, first: 100, isFork: false) {
          nodes { stargazerCount languages(first: 8) { edges { size node { name } } } }
        }
        followers { totalCount }
      }
    }""" % USER
    data, cal = {}, None
    for attempt in range(3):
        try:
            res = _post(GRAPHQL, {"query": q})["data"]["user"]
            cal = res["contributionsCollection"]["contributionCalendar"]
            langs = {}
            stars = 0
            for repo in res["repositories"]["nodes"]:
                stars += repo["stargazerCount"]
                for e in repo["languages"]["edges"]:
                    langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
            data["calendar"] = cal
            data["total_contribs"] = cal["totalContributions"]
            data["langs"] = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
            data["stars_owned"] = stars
            data["followers"] = res["followers"]["totalCount"]
            break
        except Exception as e:  # noqa: BLE001 — fail-safe by design
            print(f"graphql attempt {attempt + 1} failed: {e}", file=sys.stderr)
            if attempt == 2:
                raise
            time.sleep(3 + attempt * 4)
    # REST: canonical public numbers (matches the GitHub UI)
    try:
        u = _get(f"{API}/users/{USER}")
        data["public_repos"] = u.get("public_repos", 0)
        data["followers"] = u.get("followers", data["followers"])
    except Exception as e:  # noqa: BLE001
        print(f"rest fallback failed (non-fatal): {e}", file=sys.stderr)
        data.setdefault("public_repos", 0)
    return data


def streaks(days):
    """days: chronological [(date_str, count)]. Returns (current, longest)."""
    longest = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    current, idx = 0, len(days) - 1
    today = dt.date.today()
    # allow "today at 0" — streak still alive if yesterday counted
    while idx >= 0:
        d = dt.date.fromisoformat(days[idx][0])
        c = days[idx][1]
        if c > 0:
            current += 1
            idx -= 1
        elif d == today and current == 0:
            idx -= 1  # today not counted yet — streak can continue
        else:
            break
    return current, longest


# ---------------------------------------------------------------- svg base
def svg_head(wd, ht, extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{wd}" height="{ht}" viewBox="0 0 {wd} {ht}" font-family="{FONT}" {extra}>')


DEFS = f"""
<defs>
  <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="2.4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <linearGradient id="panelG" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{PANEL2}"/><stop offset="1" stop-color="{BG}"/>
  </linearGradient>
  <linearGradient id="scanG" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>
    <stop offset="1" stop-color="{CYAN}" stop-opacity="0.45"/>
  </linearGradient>
  <pattern id="crt" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="2" fill="#ffffff" opacity="0.03"/>
  </pattern>
</defs>"""


def panel(wd, ht, title, right):
    return f"""
<rect width="{wd}" height="{ht}" rx="14" fill="url(#panelG)" stroke="{CYAN}" stroke-opacity="0.35"/>
<rect x="1.5" y="1.5" width="{wd - 3}" height="{ht - 3}" rx="13" fill="url(#crt)"/>
<text x="30" y="44" font-size="14" letter-spacing="3" fill="{CYAN}">⌁ {title}</text>
<text x="{wd - 30}" y="44" text-anchor="end" font-size="10.5" letter-spacing="2" fill="{DIM}">{right}</text>
<line x1="24" y1="60" x2="{wd - 24}" y2="60" stroke="{LINE}"/>"""


def write_atomic(name, svg):
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + svg.strip() + "\n")
    xml.dom.minidom.parse(tmp)  # validate before it can ever go live
    os.replace(tmp, os.path.join(OUT, name))
    print(f"rendered assets/{name} ({os.path.getsize(os.path.join(OUT, name)) / 1024:.1f} KB)")


# ---------------------------------------------------------------- stats.svg
def render_stats(d):
    wd, ht = 940, 396
    cur, lng = streaks(d["days"])
    tiles = [
        ("TOTAL CONTRIBUTIONS", f"{d['total_contribs']:,}", CYAN),
        ("CURRENT STREAK", f"{cur}", LIME),
        ("LONGEST STREAK", f"{lng}", VIOLET),
        ("PUBLIC REPOS", f"{d['public_repos']}", CYAN),
        ("STARS EARNED", f"{d['stars_owned']}", AMBER),
        ("FOLLOWERS", f"{d['followers']}", PINK),
    ]
    cells = []
    for i, (label, val, col) in enumerate(tiles):
        x = 40 + (i % 2) * 210
        y = 96 + (i // 2) * 92
        cells.append(f"""
  <rect x="{x}" y="{y}" width="194" height="78" rx="10" fill="{PANEL2}" stroke="{LINE}"/>
  <rect x="{x}" y="{y}" width="194" height="2.5" rx="1" fill="{col}" opacity="0.7" filter="url(#glow)"/>
  <text x="{x + 14}" y="{y + 26}" font-size="10" letter-spacing="1.6" fill="{DIM}">{label}</text>
  <text x="{x + 14}" y="{y + 62}" font-size="30" font-weight="700" fill="{col}" filter="url(#glow)"
        class="num" style="animation-delay:-{i * 0.55:.2f}s">{val}</text>""")
    cells = "".join(cells)

    langs = d["langs"]
    total_bytes = sum(v for _, v in langs) or 1
    colors = [CYAN, LIME, AMBER, VIOLET, PINK, "#60a5fa"]
    bars, lx, ly = [], 480, 108
    for i, ((name, size), col) in enumerate(zip(langs, colors)):
        pct = size / total_bytes
        bw = max(6, int(360 * pct))
        nm = name if len(name) <= 16 else name[:15] + "…"
        bars.append(f"""
  <text x="{lx}" y="{ly + i * 38}" font-size="11.5" letter-spacing="1.5" fill="{DIM}">{nm}</text>
  <text x="{lx + 360}" y="{ly + i * 38}" text-anchor="end" font-size="11.5" fill="{col}">{pct * 100:.1f}%</text>
  <rect x="{lx}" y="{ly + i * 38 + 8}" width="360" height="6" rx="3" fill="{LINE}" opacity="0.5"/>
  <g style="transform-box:fill-box;transform-origin:left center">
    <rect class="bar" style="animation-delay:-{i * 0.4:.1f}s" x="{lx}" y="{ly + i * 38 + 8}" width="{bw}" height="6" rx="3" fill="{col}" filter="url(#glow)"/>
  </g>""")
    bars = "".join(bars)

    today = dt.date.today().isoformat()
    body = f"""{svg_head(wd, ht)}
{DEFS}
<style>
  .num{{animation:np 3s ease-in-out infinite}}
  @keyframes np{{0%,100%{{opacity:.82}}50%{{opacity:1}}}}
  .bar{{animation:fill 7s cubic-bezier(.2,.7,.2,1) infinite}}
  @keyframes fill{{0%{{transform:scaleX(.03);opacity:.6}}42%{{transform:scaleX(1);opacity:1}}86%{{transform:scaleX(1);opacity:1}}100%{{transform:scaleX(.03);opacity:.6}}}}
  .scan{{animation:scan 5s cubic-bezier(.45,0,.55,1) infinite}}
  @keyframes scan{{0%{{transform:translateY(0)}}100%{{transform:translateY({ht - 70}px)}}}}
  .bd{{stroke-dasharray:5 7;animation:dsh 22s linear infinite}}
  @keyframes dsh{{to{{stroke-dashoffset:-600}}}}
</style>
{panel(wd, ht, "TELEMETRY.CORE — LIVE FROM THE GITHUB API", "SELF-HOSTED · NO EXTERNAL SERVICES")}
{cells}
<text x="480" y="86" font-size="11" letter-spacing="2" fill="{VIOLET}" opacity="0.9">TOP.LANGUAGES — BY CODE BYTES</text>
{bars}
<g class="scan"><rect x="24" y="64" width="{wd - 48}" height="26" fill="url(#scanG)" opacity="0.14"/></g>
<rect x="480" y="{ly + len(langs) * 38 + 2}" width="150" height="26" rx="13" fill="none" stroke="{AMBER}" stroke-opacity="0.8"/>
<text x="555" y="{ly + len(langs) * 38 + 19}" text-anchor="middle" font-size="11" letter-spacing="1" fill="{AMBER}">★ PULL-SHARK ✓</text>
<text x="{wd}" y="{ht - 10}" text-anchor="end" font-size="9.5" letter-spacing="1.5" fill="{DIM2}">AUTO-RENDERED {today} · GITHUB ACTIONS · STALE-PROOF</text>
</svg>"""
    write_atomic("stats.svg", body)


# ---------------------------------------------------------------- snake.svg
def render_snake(d):
    wd, ht = 940, 244
    weeks = d["calendar"]["weeks"]
    step, cell = 15, 12
    ncols = len(weeks)
    x0 = (wd - ncols * step) // 2
    y0 = 80

    days = d["days"]
    rects = []
    path_pts = []
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week["contributionDays"]):
            x = x0 + wi * step
            y = y0 + di * step
            c = day["contributionCount"]
            lvl = 0 if c == 0 else 1 if c <= 2 else 2 if c <= 5 else 3 if c <= 9 else 4
            rects.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[lvl]}"/>')
            path_pts.append((x + cell / 2, y + cell / 2))
    rects = "".join(rects)

    n = len(path_pts)
    dur = max(24.0, round(n * 0.08, 1))
    seg = 0.06  # seconds between body segments -> spacing ~= one grid cell
    sx, sy = path_pts[0]
    d_attr = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in path_pts)
    body_parts = [f'<path id="snk" d="{d_attr}" fill="none" stroke="none"/>']
    # Glowing head + trailing body. begin = -(dur - i*seg) puts segment i
    # exactly i*seg seconds of phase BEHIND the head (a plain negative begin
    # runs ahead; a positive begin never activates on some renderers), and
    # keeps every segment active from t=0.
    body_parts.append(
        f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="4.6" fill="#ffffff" filter="url(#glow)">'
        f'<animateMotion dur="{dur}s" repeatCount="indefinite" rotate="0"><mpath xlink:href="#snk" href="#snk"/></animateMotion></circle>')
    for i in range(1, 17):
        r = 3.8 - i * 0.14
        op = 0.9 - i * 0.042
        body_parts.append(
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r:.2f}" fill="{CYAN}" opacity="{op:.2f}">'
            f'<animateMotion dur="{dur}s" begin="-{dur - i * seg:.3f}s" repeatCount="indefinite"><mpath xlink:href="#snk" href="#snk"/></animateMotion></circle>')
    body = "".join(body_parts)

    total = d["total_contribs"]
    legend = "".join(
        f'<rect x="{x0 + i * 44}" y="{ht - 26}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[i]}"/>'
        f'<text x="{x0 + i * 44 + 16}" y="{ht - 16}" font-size="9.5" fill="{DIM2}">{lbl}</text>'
        for i, lbl in enumerate(["0", "1-2", "3-5", "6-9", "10+"]))
    today = dt.date.today().isoformat()
    out = f"""{svg_head(wd, ht)}
{DEFS}
<style>
  .ttl{{animation:subp 3.2s ease-in-out infinite}}
  @keyframes subp{{0%,100%{{opacity:.6}}50%{{opacity:1}}}}
  .bd{{stroke-dasharray:5 7;animation:dsh 22s linear infinite}}
  @keyframes dsh{{to{{stroke-dashoffset:-600}}}}
</style>
{panel(wd, ht, "CONTRIBUTION.STREAM — REAL COMMIT GRAPH", "RENDERED DAILY · SELF-HOSTED")}
{rects}
{body}
<text class="ttl" x="{x0}" y="76" font-size="11" letter-spacing="1.5" fill="{DIM}">◼ {total:,} CONTRIBUTIONS THIS YEAR — THE SNAKE EATS CHRONOLOGICALLY</text>
{legend}
<text x="{wd - 30}" y="{ht - 16}" text-anchor="end" font-size="9.5" letter-spacing="1.5" fill="{DIM2}">AUTO-RENDERED {today}</text>
</svg>"""
    write_atomic("snake.svg", out)


# ---------------------------------------------------------------- main
def main():
    if not TOKEN:
        print("GH_TOKEN/GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    d = fetch_data()
    # flatten calendar to chronological day list
    days = []
    for week in d["calendar"]["weeks"]:
        for day in week["contributionDays"]:
            days.append((day["date"], day["contributionCount"]))
    d["days"] = days
    render_stats(d)
    render_snake(d)
    print("telemetry render complete — last-good assets in place.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 — never leave a half-broken asset
        print(f"FATAL: keeping last-good assets ({e})", file=sys.stderr)
        sys.exit(1)
