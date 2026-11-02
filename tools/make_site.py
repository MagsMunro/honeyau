"""Turn the rebuilt Equity Pull Lookup page into the honeyau.com copy.

Usage: python3 -I tools/make_site.py <rebuilt page.html> <output index.html> <AS_OF>

The rebuilt page is the claude.ai artifact page (template + seed data, made by
rebuild.py). This adds the honeyau.com title and share tags, and swaps the
request box text for viewers who are not signed in to claude.ai. Each change
must apply exactly once, or the script stops without writing anything.
"""
import json, re, sys

src, out, as_of = sys.argv[1:4]
html = open(src, encoding="utf-8").read()

DESC = ("See where someone's hire-grant stock likely stands today, how much is still "
        "vesting and when, and what that suggests about whether to reach out and how "
        "to shape the conversation.")
META = (
    '<title>Equity intelligence on talent</title>\n'
    f'<meta name="description" content="Equity intelligence on talent. {DESC}">\n'
    '<meta property="og:type" content="website">\n'
    '<meta property="og:url" content="https://honeyau.com/">\n'
    '<meta property="og:title" content="Equity intelligence on talent">\n'
    f'<meta property="og:description" content="{DESC}">\n'
    '<meta name="twitter:card" content="summary">\n'
)
EDITS = [
    ('<title>Equity Pull Lookup</title>\n', META),
    ('    if (!state.db) el("req-status").textContent = "Sign in to claude.ai to send a request.";\n',
     '    document.querySelector(".req-row").hidden = !state.db;\n'
     '    if (!state.db) el("req-status").textContent = "To have it added, ask the person who shared this link with you.";\n'),
]
for old, new in EDITS:
    n = html.count(old)
    if n != 1:
        sys.exit(f"STOP: expected 1 match, found {n}: {old.strip()[:70]}")
    html = html.replace(old, new)

m = re.search(r'<script type="application/json" id="seed">(.*?)</script>', html, re.S)
if not m:
    sys.exit("STOP: seed block not found")
seed = json.loads(m.group(1))
if seed.get("as_of") != as_of or not seed.get("companies"):
    sys.exit(f"STOP: seed as_of is {seed.get('as_of')!r}, expected {as_of!r}, or no companies")

open(out, "w", encoding="utf-8").write(html)
print(f"site page built: as_of {as_of}, {len(seed['companies'])} companies")
