"""Asset group E: orbital skill system + featured mission cards."""
import math
import random
from common import (BG, PANEL, PANEL2, LINE, CYAN, CYAN_D, GOLD, GOLD_D, VIOLET,
                    LIME, AMBER, PINK, TXT, DIM, DIM2, FONT, R, w, esc, svg_head,
                    css, defs_common, hud_brackets, stars)


# ================================================================ SKILL ORBIT
def skill_orbit():
    wd, ht = 940, 440
    cx, cy = 470, 228

    def ellipse_path(rx, ry):
        return (f"M {cx + rx} {cy} A {rx} {ry} 0 1 1 {cx - rx} {cy} "
                f"A {rx} {ry} 0 1 1 {cx + rx} {cy} Z")

    o1, o2 = 336, 112   # outer orbit radii
    i1, i2 = 238, 76    # inner orbit radii
    dur1, dur2 = 36.0, 22.0

    outer_nodes = [("TS", CYAN), ("PY", LIME), ("JS", GOLD), ("RAG", VIOLET), ("ML", PINK)]
    inner_nodes = [("CSS", "#60a5fa"), ("HTML", AMBER), ("GIT", TXT)]

    def node(label, col):
        return (f'<g class="nd">'
                f'<rect x="-21" y="-14" width="42" height="28" rx="8" fill="{PANEL2}" stroke="{col}" stroke-opacity="0.9"/>'
                f'<text x="0" y="5" text-anchor="middle" font-size="12.5" font-weight="700" fill="{col}" filter="url(#glow)">{esc(label)}</text>'
                f'</g>')

    parts = []
    for k, (label, col) in enumerate(outer_nodes):
        parts.append(
            f'<g><animateMotion dur="{dur1}s" begin="-{k / len(outer_nodes) * dur1:.2f}s" '
            f'repeatCount="indefinite"><mpath xlink:href="#orb1" href="#orb1"/></animateMotion>{node(label, col)}</g>')
    for k, (label, col) in enumerate(inner_nodes):
        parts.append(
            f'<g><animateMotion dur="{dur2}s" begin="-{k / len(inner_nodes) * dur2:.2f}s" '
            f'repeatCount="indefinite"><mpath xlink:href="#orb2" href="#orb2"/></animateMotion>{node(label, col)}</g>')
    nodes = "".join(parts)

    dust = stars(26, wd, ht, 30, ht - 24, cls="st", seed_extra=7)

    body = f"""
{svg_head(wd, ht)}
{defs_common()}
<defs>
  <radialGradient id="coreG" cx="0.5" cy="0.42" r="0.75">
    <stop offset="0" stop-color="#e9f6ff"/><stop offset="0.45" stop-color="#38c8f0"/>
    <stop offset="0.8" stop-color="#0b5d80"/><stop offset="1" stop-color="#072a42"/>
  </radialGradient>
  <radialGradient id="haloG" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0.4"/>
    <stop offset="0.55" stop-color="{CYAN}" stop-opacity="0.08"/>
    <stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
  </radialGradient>
  <pattern id="crt5" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="2" fill="#ffffff" opacity="0.03"/>
  </pattern>
  <path id="orb1" d="{ellipse_path(o1, o1 * 0.5)}" fill="none"/>
  <path id="orb2" d="{ellipse_path(i1, i1 * 0.55)}" fill="none"/>
</defs>
{css('''
  .st{animation:twk 3.4s ease-in-out infinite alternate}
  @keyframes twk{from{opacity:.1}to{opacity:.85}}
  .core{animation:corep 4.2s ease-in-out infinite}
  @keyframes corep{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
  .sonar{animation:snr 3.6s ease-out infinite;transform-origin:center;transform-box:fill-box}
  @keyframes snr{0%{transform:scale(.5);opacity:.8}100%{transform:scale(1.55);opacity:0}}
  .nd{filter:url(#glow)}
  .flow{stroke-dasharray:4 10;animation:flw 14s linear infinite}
  @keyframes flw{to{stroke-dashoffset:-350}}
  .bd{stroke-dasharray:5 7;animation:dsh 22s linear infinite}
  @keyframes dsh{to{stroke-dashoffset:-600}}
''')}

<rect width="{wd}" height="{ht}" rx="14" fill="url(#panelG)" stroke="{GOLD_D}" stroke-opacity="0.5"/>
<rect x="1.5" y="1.5" width="{wd - 3}" height="{ht - 3}" rx="13" fill="url(#crt5)"/>
{dust}

<text x="30" y="46" font-size="14" letter-spacing="3" fill="{GOLD}">⚔ TECH.ARSENAL — ORBITAL.VIEW</text>
<text x="{wd - 30}" y="46" text-anchor="end" font-size="11" letter-spacing="2" fill="{DIM}">CORE STABILITY 99.98%</text>
<line x1="24" y1="60" x2="{wd - 24}" y2="60" stroke="{LINE}"/>

<g transform="rotate(-9 {cx} {cy})">
  <ellipse cx="{cx}" cy="{cy}" rx="{o1}" ry="{o1 * 0.5:.0f}" fill="none" stroke="{LINE}" stroke-width="1.3"/>
  <ellipse cx="{cx}" cy="{cy}" rx="{o1}" ry="{o1 * 0.5:.0f}" fill="none" stroke="{CYAN_D}" stroke-opacity="0.7" stroke-width="1.6" class="flow"/>
  <ellipse cx="{cx}" cy="{cy}" rx="{i1}" ry="{i1 * 0.55:.0f}" fill="none" stroke="{LINE}" stroke-width="1.3"/>
  <ellipse cx="{cx}" cy="{cy}" rx="{i1}" ry="{i1 * 0.55:.0f}" fill="none" stroke="{GOLD_D}" stroke-opacity="0.8" stroke-width="1.4" class="flow"/>
</g>

<circle cx="{cx}" cy="{cy}" r="120" fill="url(#haloG)"/>
<circle cx="{cx}" cy="{cy}" r="88" fill="none" stroke="{CYAN}" stroke-opacity="0.35" class="sonar"/>
<circle cx="{cx}" cy="{cy}" r="88" fill="none" stroke="{CYAN}" stroke-opacity="0.35" class="sonar" style="animation-delay:-1.8s"/>
<circle class="core" cx="{cx}" cy="{cy}" r="52" fill="url(#coreG)" filter="url(#glow)"/>
<circle cx="{cx}" cy="{cy}" r="52" fill="none" stroke="{GOLD}" stroke-opacity="0.8" stroke-width="1.6"/>
<text x="{cx}" y="{cy + 7}" text-anchor="middle" font-size="26" font-weight="700" fill="#062033" letter-spacing="2">AJ</text>
<text x="{cx}" y="{cy + 82}" text-anchor="middle" font-size="11" letter-spacing="3" fill="{DIM}">AVANI.EXE — CORE</text>

<g transform="rotate(-9 {cx} {cy})">{nodes}</g>

{hud_brackets(wd, ht, m=8, ln=18, color=GOLD, op=0.4)}
</svg>"""
    return body


# ================================================================ MISSIONS
def missions():
    wd, ht = 940, 540
    cards = [
        ("jallekha", "TYPESCRIPT", "4★ FLAGSHIP", GOLD,
         "Water delivery & consumption reconciliation for campuses —",
         "deterministic balance, full audit trail.",
         ["TS", "LEDGER", "AUDIT"]),
        ("docwise-rag-chatbot", "PYTHON", "RAG.CORE", CYAN,
         "CPU-friendly RAG chatbot for PDFs — local embeddings,",
         "page-level citations. Runs on a potato.",
         ["PY", "RAG", "PDF"]),
        ("DocuMind-AI", "TYPESCRIPT", "LLM.APP", VIOLET,
         "AI document assistant — upload any doc, ask questions,",
         "get answers with citations.",
         ["TS", "LLM", "AI"]),
        ("CoverIQ", "PYTHON · ML", "ML.LAB", LIME,
         "Interactive insurance-cost prediction with",
         "side-by-side model comparison.",
         ["PY", "ML", "STREAMLIT"]),
    ]

    def card(x, y, name, lang, tag, tagcol, l1, l2, chips, i):
        cw, ch = 442, 208
        chip_html = []
        cxp = x + 18
        for c in chips:
            cwp = w(c, 10, 1) + 18
            chip_html.append(f'<rect x="{cxp}" y="{y + ch - 40}" width="{cwp:.0f}" height="22" rx="11" fill="none" stroke="{LINE}"/>'
                             f'<text x="{cxp + 9}" y="{y + ch - 25}" font-size="10" letter-spacing="1" fill="{CYAN_D}">{esc(c)}</text>')
            cxp += cwp + 10
        chip_html = "".join(chip_html)
        return f"""
  <g class="mcard" style="animation-delay:-{i * 0.7:.1f}s">
    <rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="12" fill="url(#panelG)" stroke="{LINE}"/>
    <rect x="{x}" y="{y}" width="4" height="{ch}" rx="2" fill="{tagcol}" filter="url(#glow)"/>
    <path d="M{x + cw - 22} {y + 6} L{x + cw - 6} {y + 6} L{x + cw - 6} {y + 22}" fill="none" stroke="{tagcol}" stroke-opacity="0.6" stroke-width="1.6"/>
    <text x="{x + 20}" y="{y + 36}" font-size="16" font-weight="700" fill="{TXT}">{esc(name)}</text>
    <text x="{x + cw - 18}" y="{y + 34}" text-anchor="end" font-size="10" letter-spacing="1.5" fill="{DIM}">{esc(lang)}</text>
    <rect x="{x + 20}" y="{y + 46}" width="{w(tag, 9, 1.5) + 16:.0f}" height="20" rx="10" fill="{tagcol}" fill-opacity="0.12" stroke="{tagcol}" stroke-opacity="0.7"/>
    <text x="{x + 28}" y="{y + 60}" font-size="9.5" letter-spacing="1.5" fill="{tagcol}">{esc(tag)}</text>
    <text x="{x + 20}" y="{y + 96}" font-size="12" fill="{DIM}">{esc(l1)}</text>
    <text x="{x + 20}" y="{y + 114}" font-size="12" fill="{DIM}">{esc(l2)}</text>
    {chip_html}
    <g class="mscan"><rect x="{x}" y="{y}" width="{cw}" height="18" fill="url(#scanG)" opacity="0.2"/></g>
    <text x="{x + cw - 18}" y="{y + ch - 14}" text-anchor="end" font-size="10" letter-spacing="2" fill="{tagcol}" opacity="0.85">OPEN ▸</text>
  </g>"""

    layout = [(22, 78, 0), (478, 78, 1), (22, 300, 2), (478, 300, 3)]
    card_html = "".join(card(x, y, *cards[i], i) for (x, y, i) in layout)

    body = f"""
{svg_head(wd, ht)}
{defs_common()}
<defs>
  <pattern id="crt6" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="2" fill="#ffffff" opacity="0.03"/>
  </pattern>
</defs>
{css('''
  .mcard{animation:mp 6s ease-in-out infinite}
  @keyframes mp{0%,100%{opacity:.94}50%{opacity:1}}
  .mscan{animation:msw 5.5s cubic-bezier(.45,0,.55,1) infinite}
  @keyframes msw{0%{transform:translateY(0);opacity:0}10%{opacity:1}90%{opacity:1}100%{transform:translateY(''' + str(208) + '''px);opacity:0}}
  .bd{stroke-dasharray:5 7;animation:dsh 22s linear infinite}
  @keyframes dsh{to{stroke-dashoffset:-600}}
''')}
<rect width="{wd}" height="{ht}" rx="14" fill="url(#panelG)" stroke="{GOLD_D}" stroke-opacity="0.5" class="bd"/>
<rect x="1.5" y="1.5" width="{wd - 3}" height="{ht - 3}" rx="13" fill="url(#crt6)"/>
<text x="30" y="46" font-size="14" letter-spacing="3" fill="{GOLD}">🚀 FEATURED.MISSIONS — DEPLOYED SYSTEMS</text>
<text x="{wd - 30}" y="46" text-anchor="end" font-size="11" letter-spacing="2" fill="{DIM}">4 ACTIVE · ALL SYSTEMS NOMINAL</text>
<line x1="24" y1="60" x2="{wd - 24}" y2="60" stroke="{LINE}"/>
{card_html}
<text x="{wd / 2}" y="{ht - 18}" text-anchor="middle" font-size="11" letter-spacing="2" fill="{DIM}">▸ FULL CATALOG — <tspan fill="{CYAN}">github.com/avani376?tab=repositories</tspan></text>
{hud_brackets(wd, ht, m=8, ln=18, color=GOLD, op=0.4)}
</svg>"""
    return body
