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
import math
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
GOLD, GOLD_D = "#ffd166", "#b8860b"
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
  <linearGradient id="arcG1" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="#7ee9ff"/>
  </linearGradient>
  <pattern id="crt" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="2" fill="#ffffff" opacity="0.03"/>
  </pattern>
</defs>"""


def panel(wd, ht, title, right, accent=CYAN):
    return f"""
<rect width="{wd}" height="{ht}" rx="14" fill="url(#panelG)" stroke="{accent}" stroke-opacity="0.35"/>
<rect x="1.5" y="1.5" width="{wd - 3}" height="{ht - 3}" rx="13" fill="url(#crt)"/>
<text x="30" y="44" font-size="14" letter-spacing="3" fill="{accent}">⌁ {title}</text>
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
def arc_point(cx, cy, r, deg):
    """SVG-space angle: 150deg = bottom-left, 270 = top, 390(=30) = bottom-right."""
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def gauge(cx, cy, r, frac, value, unit, label, col, i):
    """240° gauge: dim track + animated value arc + SMIL needle."""
    sweep = 240.0
    frac = max(0.02, min(1.0, frac))
    a0 = 150.0
    a1 = a0 + sweep * frac
    x0, y0 = arc_point(cx, cy, r, a0)
    xa, ya = arc_point(cx, cy, r, a1)
    large = 1 if (a1 - a0) > 180 else 0
    track = (f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 1 1 {arc_point(cx, cy, r, a0 + sweep)[0]:.1f} '
             f'{arc_point(cx, cy, r, a0 + sweep)[1]:.1f}" fill="none" stroke="{LINE}" stroke-width="11" '
             f'stroke-linecap="round" opacity="0.7"/>')
    val = (f'<path class="garc" style="animation-delay:-{i * 0.9:.1f}s" '
           f'd="M {x0:.1f} {y0:.1f} A {r} {r} 0 {large} 1 {xa:.1f} {ya:.1f}" fill="none" '
           f'stroke="{col}" stroke-width="11" stroke-linecap="round" pathLength="100" filter="url(#glow)"/>')
    # ticks
    ticks = []
    for k in range(9):
        ang = a0 + sweep * k / 8
        x1, y1 = arc_point(cx, cy, r - 16, ang)
        x2, y2 = arc_point(cx, cy, r - 10, ang)
        ticks.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="{DIM2}" stroke-width="1.4"/>')
    ticks = "".join(ticks)
    nx, ny = arc_point(cx, cy, r - 20, a1)
    return f"""
  <g>
    {track}{val}{ticks}
    <line class="gneedle" style="animation-delay:-{i * 0.9:.1f}s" x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}"
          stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" opacity="0.85">
      <animateTransform attributeName="transform" type="rotate"
        values="{a0} {cx} {cy};{a1:.1f} {cx} {cy};{a1:.1f} {cx} {cy};{a0} {cx} {cy}"
        keyTimes="0;0.42;0.86;1" dur="8s" repeatCount="indefinite"/>
    </line>
    <circle cx="{cx}" cy="{cy}" r="4" fill="{col}"/>
    <text x="{cx}" y="{cy + 30}" text-anchor="middle" font-size="24" font-weight="700" fill="{TXT}" filter="url(#glow)">{value}</text>
    <text x="{cx}" y="{cy + 46}" text-anchor="middle" font-size="8.5" letter-spacing="1.2" fill="{DIM}">{unit}</text>
    <text x="{cx}" y="{cy + r + 22}" text-anchor="middle" font-size="10" letter-spacing="2" fill="{col}">{label}</text>
  </g>"""


def render_stats(d):
    wd, ht = 940, 430
    cur, lng = streaks(d["days"])
    today = dt.date.today().isoformat()

    gauges = [
        gauge(120, 192, 58, d["total_contribs"] / 300, f"{d['total_contribs']:,}", "THIS YEAR",
              "CONTRIBUTIONS", CYAN, 0),
        gauge(310, 192, 58, cur / max(lng, 1), f"{cur}", "DAYS", "CURRENT STREAK", LIME, 1),
        gauge(500, 192, 58, lng / 30, f"{lng}", "DAYS", "LONGEST STREAK", VIOLET, 2),
    ]
    gauges = "".join(gauges)

    # compact stat chips under the gauges
    chips_data = [("PUBLIC REPOS", f"{d['public_repos']}", CYAN),
                  ("STARS EARNED", f"{d['stars_owned']}", GOLD),
                  ("FOLLOWERS", f"{d['followers']}", PINK),
                  ("PULL-SHARK", "✓ UNLOCKED", AMBER)]
    chips = []
    for i, (k, v, col) in enumerate(chips_data):
        x = 40 + i * 118
        chips.append(f"""
  <rect x="{x}" y="318" width="106" height="46" rx="8" fill="{PANEL2}" stroke="{LINE}"/>
  <text x="{x + 11}" y="{318 + 17}" font-size="8.5" letter-spacing="1.2" fill="{DIM}">{k}</text>
  <text x="{x + 11}" y="{318 + 36}" font-size="13" fill="{col}" class="gnum" style="animation-delay:-{i * 0.7:.1f}s">{v}</text>""")
    chips = "".join(chips)

    # languages
    langs = d["langs"]
    total_bytes = sum(v for _, v in langs) or 1
    colors = [CYAN, LIME, GOLD, VIOLET, PINK, "#60a5fa"]
    lx, ly = 640, 100
    bars = []
    for i, ((name, size), col) in enumerate(zip(langs, colors)):
        pct = size / total_bytes
        bw = max(6, int(250 * pct))
        nm = name if len(name) <= 14 else name[:13] + "…"
        bars.append(f"""
  <text x="{lx}" y="{ly + i * 42}" font-size="11.5" letter-spacing="1.5" fill="{DIM}">{nm}</text>
  <text x="{lx + 250}" y="{ly + i * 42}" text-anchor="end" font-size="11.5" fill="{col}">{pct * 100:.1f}%</text>
  <rect x="{lx}" y="{ly + i * 42 + 8}" width="250" height="6" rx="3" fill="{LINE}" opacity="0.5"/>
  <g style="transform-box:fill-box;transform-origin:left center">
    <rect class="gbar" style="animation-delay:-{i * 0.4:.1f}s" x="{lx}" y="{ly + i * 42 + 8}" width="{bw}" height="6" rx="3" fill="{col}" filter="url(#glow)"/>
  </g>""")
    bars = "".join(bars)

    body = f"""{svg_head(wd, ht)}
{DEFS}
<style>
  .garc{{stroke-dasharray:100;animation:gfill 8s cubic-bezier(.2,.7,.2,1) infinite}}
  @keyframes gfill{{0%{{stroke-dashoffset:100}}42%{{stroke-dashoffset:0}}86%{{stroke-dashoffset:0}}100%{{stroke-dashoffset:100}}}}
  .gnum{{animation:np 3s ease-in-out infinite}}
  @keyframes np{{0%,100%{{opacity:.82}}50%{{opacity:1}}}}
  .gbar{{animation:fill 7s cubic-bezier(.2,.7,.2,1) infinite}}
  @keyframes fill{{0%{{transform:scaleX(.03);opacity:.6}}42%{{transform:scaleX(1);opacity:1}}86%{{transform:scaleX(1);opacity:1}}100%{{transform:scaleX(.03);opacity:.6}}}}
  .scan{{animation:scan 5s cubic-bezier(.45,0,.55,1) infinite}}
  @keyframes scan{{0%{{transform:translateY(0)}}100%{{transform:translateY({ht - 74}px)}}}}
  .bd{{stroke-dasharray:5 7;animation:dsh 22s linear infinite}}
  @keyframes dsh{{to{{stroke-dashoffset:-600}}}}
</style>
{panel(wd, ht, "GITHUB.TELEMETRY — LIVE FROM THE API", "SELF-HOSTED · NO EXTERNAL SERVICES", GOLD)}
{gauges}
{chips}
<text x="{lx}" y="78" font-size="11" letter-spacing="2" fill="{VIOLET}" opacity="0.9">TOP.LANGUAGES — BY CODE BYTES</text>
<line x1="620" y1="90" x2="620" y2="{ht - 40}" stroke="{LINE}" stroke-dasharray="3 6"/>
{bars}
<g class="scan"><rect x="24" y="64" width="{wd - 48}" height="26" fill="url(#scanG)" opacity="0.13"/></g>
<text x="{wd}" y="{ht - 12}" text-anchor="end" font-size="9.5" letter-spacing="1.5" fill="{DIM2}">AUTO-RENDERED {today} · GITHUB ACTIONS · STALE-PROOF</text>
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
    d_attr = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in path_pts)
    body_parts = [f'<path id="snk" d="{d_attr}" fill="none" stroke="none"/>']
    # Glowing head + trailing body. CRITICAL: animated circles must NOT carry
    # base cx/cy — animateMotion ADDS the element's base position to the path
    # translation, so any base offset double-displaces the snake off the grid.
    # All circles sit at (0,0) and live entirely on the motion path.
    # begin = -(dur - i*seg) puts segment i exactly i*seg seconds of phase
    # BEHIND the head (plain negative begin runs ahead; positive begin never
    # activates on some renderers) and keeps every segment active from t=0.
    body_parts.append(
        f'<circle r="4.6" fill="#ffffff" filter="url(#glow)">'
        f'<animateMotion dur="{dur}s" repeatCount="indefinite" rotate="0"><mpath xlink:href="#snk" href="#snk"/></animateMotion></circle>')
    for i in range(1, 17):
        r = 3.8 - i * 0.14
        op = 0.9 - i * 0.042
        body_parts.append(
            f'<circle r="{r:.2f}" fill="{CYAN}" opacity="{op:.2f}">'
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
{panel(wd, ht, "CONTRIBUTION.STREAM — REAL COMMIT GRAPH", "RENDERED DAILY · SELF-HOSTED", GOLD)}
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
