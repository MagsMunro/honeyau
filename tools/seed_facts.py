"""Update and check the vesting and pay-timing facts in index.html's seed block.

The live Honeyau site (Lovable, www.honeyau.com) gets prices live from Yahoo
Finance. It reads only the researched facts below from the
<script type="application/json" id="seed"> block in this repo's index.html.
This script is the only thing that should change that block.

Usage:
  python3 -I tools/seed_facts.py todo   <index.html> [N]
      List up to N rows (default 8) that most need facts, best first.
  python3 -I tools/seed_facts.py apply  <index.html> <facts.json> <AS_OF>
      facts.json = {"TICKER": {field: value, ...}, ...} using FACT_FIELDS only.
      Writes the facts and sets the seed's top-level "as_of" to AS_OF.
      Changes nothing else in the file. Writes nothing if any input is invalid.
  python3 -I tools/seed_facts.py verify <old index.html> <new index.html> [AS_OF]
      Exit 0 only if the new file is a safe update of the old one.
"""
import json, re, sys

FACT_FIELDS = [
    "vest_schedule", "vest_frequency", "vest_cliff", "vest_note", "vest_source",
    "vest_events", "bonus_timing", "refresh_timing", "timing_source",
    "timing_source_type",
]
SEED_RE = re.compile(r'(<script type="application/json" id="seed">)(.*?)(</script>)', re.S)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load(path):
    html = open(path, encoding="utf-8").read()
    found = SEED_RE.findall(html)
    if len(found) != 1:
        sys.exit(f"ERROR: expected exactly 1 seed block in {path}, found {len(found)}")
    m = SEED_RE.search(html)
    seed = json.loads(m.group(2))
    if not isinstance(seed, dict) or not isinstance(seed.get("companies"), list) or not seed["companies"]:
        sys.exit("ERROR: seed has no companies list")
    return html, m, seed


def dump(seed):
    # Same format as the original: compact, ASCII-escaped, '<' escaped.
    return json.dumps(seed, separators=(",", ":"), ensure_ascii=True).replace("<", "\\u003c")


def missing(v):
    return v in (None, "", "unverified", "not stated", "Not verified")


def need_score(r):
    # Lower = needs facts more.
    src = r.get("vest_source") or ""
    if missing(r.get("vest_schedule")):
        return 0
    if missing(r.get("vest_frequency")):
        return 1
    if "sec.gov" not in src:
        return 2
    if missing(r.get("bonus_timing")):
        return 3 if r.get("segment") == "Tech giant" else 4
    return 9


def cmd_todo(path, n=8):
    _, _, seed = load(path)
    rows = sorted(seed["companies"], key=lambda r: (need_score(r), r.get("rank", 999)))
    for r in rows[: int(n)]:
        if need_score(r) == 9:
            break
        print(json.dumps({"ticker": r["ticker"], "company": r["company"], "segment": r.get("segment"),
                          **{k: r.get(k) for k in FACT_FIELDS}}))


def cmd_apply(path, facts_path, as_of):
    if not DATE_RE.match(as_of):
        sys.exit("ERROR: AS_OF must be YYYY-MM-DD")
    html, m, seed = load(path)
    facts = json.load(open(facts_path, encoding="utf-8"))
    if not isinstance(facts, dict):
        sys.exit("ERROR: facts.json must be an object keyed by ticker")
    by_t = {r["ticker"]: r for r in seed["companies"]}
    for t, f in facts.items():
        if t not in by_t:
            sys.exit(f"ERROR: unknown ticker {t} (this script never adds rows)")
        bad = [k for k in f if k not in FACT_FIELDS]
        if bad:
            sys.exit(f"ERROR: {t}: not a fact field: {bad}")
        for k, v in f.items():
            if not (v is None or isinstance(v, str)):
                sys.exit(f"ERROR: {t}.{k} must be a string or null")
    for t, f in facts.items():
        by_t[t].update(f)
    seed["as_of"] = as_of
    new = html[: m.start(2)] + dump(seed) + html[m.end(2):]
    open(path, "w", encoding="utf-8").write(new)
    print(f"applied facts for {len(facts)} tickers; as_of={as_of}")


def cmd_verify(old_path, new_path, as_of=None):
    oh, om, os_ = load(old_path)
    nh, nm, ns = load(new_path)
    errs = []
    if oh[: om.start(2)] != nh[: nm.start(2)] or oh[om.end(2):] != nh[nm.end(2):]:
        errs.append("page outside the seed block changed")
    if set(os_) != set(ns):
        errs.append(f"seed keys changed: {sorted(os_)} -> {sorted(ns)}")
    if not DATE_RE.match(str(ns.get("as_of"))):
        errs.append("as_of missing or not YYYY-MM-DD")
    if as_of and ns.get("as_of") != as_of:
        errs.append(f"as_of is {ns.get('as_of')}, expected {as_of}")
    for k in os_:
        if k not in ("as_of", "companies") and os_[k] != ns.get(k):
            errs.append(f"seed '{k}' changed")
    oc, nc = os_["companies"], ns["companies"]
    if [r["ticker"] for r in oc] != [r["ticker"] for r in nc]:
        errs.append(f"company list changed ({len(oc)} -> {len(nc)} rows)")
    changed = []
    for o, n in zip(oc, nc):
        for k in set(o) | set(n):
            if o.get(k) != n.get(k):
                if k not in FACT_FIELDS:
                    errs.append(f"{o['ticker']}: non-fact field '{k}' changed")
                else:
                    changed.append(f"{o['ticker']}.{k}")
        for k in ("vest_schedule", "vest_frequency", "vest_cliff"):
            if k in o and k in n and not missing(o.get(k)) and missing(n.get(k)):
                errs.append(f"{o['ticker']}: {k} was filled and is now empty")
    print(json.dumps({"ok": not errs, "rows": len(nc), "as_of": ns.get("as_of"),
                      "changed_facts": changed, "errors": errs}, indent=1))
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["todo"] and len(a) in (2, 3):
        cmd_todo(*a[1:])
    elif a[:1] == ["apply"] and len(a) == 4:
        cmd_apply(*a[1:])
    elif a[:1] == ["verify"] and len(a) in (3, 4):
        cmd_verify(*a[1:])
    else:
        sys.exit(__doc__)
