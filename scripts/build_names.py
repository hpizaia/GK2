"""Build data/names.pt-BR.json keyed by the exact English names in data/items.en.json + data/recipes.en.json.
Order: (1) listed, obtainable items  (2) stations  (3) categories  (4) technologies  (5) everything else.
Sources: GK1 pt-BR Fandom interwiki pairs (likely) > Claude machine translation (guess).
Also attaches gameKey (GK2 locale key, from the English locale export in the GK2Thai mod repo)."""
import json, re, sys, csv, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mt_glossary import MT, CROPS, SEEDS, QUAL, SUPPLY, SINS, CATS
D = sys.argv[1]; L = D + "/raw/l10n"
items = json.load(open(f"{D}/items.en.json")); recs = json.load(open(f"{D}/recipes.en.json"))
entries = collections.OrderedDict()   # en -> {"kinds":set, "prio":int}
def add(name, kind, prio):
    if not isinstance(name, str) or not name.strip(): return
    e = entries.setdefault(name.strip(), {"kinds": set(), "prio": 9}); e["kinds"].add(kind); e["prio"] = min(e["prio"], prio)
for i in items:
    k = i.get("kind") or "item"
    if k == "item": p = 1 if (i.get("listed") and not i.get("unobtainable")) else 5
    elif k == "station": p = 2
    else: p = 5
    add(i["name"], k, p)
for r in recs:
    add(r.get("station"), "station", 2)
    for s in r.get("alt_stations") or []: add(s, "station", 2)
for i in items: add(i.get("category"), "category", 3)
for r in recs:
    if isinstance(r.get("mastery"), dict): add(r["mastery"].get("type"), "category", 3)
    if isinstance(r.get("unlock"), dict): add(r["unlock"].get("name"), "technology", 4)
# game keys
en2key = {}
with open(f"{L}/thai_source_en.csv", encoding="utf-8-sig", newline="") as fh:
    for row in csv.DictReader(fh): en2key.setdefault(row["source"].strip(), row["key"])
# GK1 pairs
ll = json.load(open(f"{L}/gk1_langlinks_merged.json")); gk1 = {}
for en, pt in ll["en_to_pt"].items():
    if pt: gk1.setdefault(en.lower(), pt)
for pt, en in ll["pt_to_en"].items():
    if en: gk1.setdefault(en.lower(), pt)
GK1_BAD = {"ash", "pike", "story", "stone block", "snake", "quality fish fillet", "coins", "perch", "work stations", "horadric"}
ROMAN = re.compile(r"^(.*?)(\s+(?:I|II|III|IV|V|VI))$")
def mt(en):
    if en in MT: return MT[en]
    if en in CATS: return CATS[en]
    m = re.match(r"^Building: (.+)$", en)
    if m:
        b = CATS.get(m.group(1)) or MT.get(m.group(1))
        if b: return "Construção: " + b[0].lower() + b[1:] if not b.isupper() else "Construção: " + b
    m = ROMAN.match(en)
    if m and m.group(1) in MT: return MT[m.group(1)] + m.group(2)
    m = re.match(r'^Tablet "(.+)"$', en)
    if m and m.group(1) in CROPS: return f'Placa "{CROPS[m.group(1)].capitalize()}"'
    m = re.match(r"^(\w+) Bed$", en)
    if m and m.group(1) in CROPS: return f"Canteiro de {CROPS[m.group(1)]}"
    m = re.match(r"^Plant (.+?)(?: \((bronze|silver|gold)\))?$", en)
    if m and m.group(1) in SEEDS: return "Plantar " + SEEDS[m.group(1)] + (f" ({QUAL[m.group(2)]})" if m.group(2) else "")
    m = re.match(r"^(.+?) \((bronze|silver|gold)\)$", en)
    if m and mt(m.group(1)): return mt(m.group(1)) + f" ({QUAL[m.group(2)]})"
    m = re.match(r"^(.+?) or (.+)$", en)
    if m and ptname(m.group(1)) and ptname(m.group(2)): return ptname(m.group(1)) + " ou " + ptname(m.group(2)).lower()
    m = re.match(r"^(Open|Repair) \((.+)\)$", en)
    if m and ptname(m.group(2)): return ("Abrir" if m.group(1) == "Open" else "Consertar") + " (" + ptname(m.group(2)).lower() + ")"
    m = re.match(r"^Supply: (.+?)(\s+(?:I|II|III))?$", en)
    if m and m.group(1) in SUPPLY: return "Suprimentos: " + SUPPLY[m.group(1)] + (m.group(2) or "")
    m = re.match(r"^Portal fragment (\w+)$", en)
    if m and m.group(1) in SINS: return "Fragmento de portal: " + SINS[m.group(1)]
    m = re.match(r"^\+(\d+) zombie limit for (\d+) weeks?$", en)
    if m: n, w = m.groups(); return f"+{n} no limite de zumbis por {w} semana" + ("s" if w != "1" else "")
    return None
def ptname(en):
    g = gk1.get(en.lower())
    if g and en.lower() not in GK1_BAD and g.lower() != en.lower(): return g[0].upper() + g[1:]
    return mt(en)
res, stats, missing = collections.OrderedDict(), collections.Counter(), []
for en, e in sorted(entries.items(), key=lambda kv: (kv[1]["prio"], kv[0].lower())):
    rec = None; g = gk1.get(en.lower())
    if g and en.lower() not in GK1_BAD and g.lower() != en.lower():
        rec = {"pt": g[0].upper() + g[1:], "source": "gk1-wiki", "confidence": "likely"}
    else:
        t = mt(en)
        if t: rec = {"pt": t, "source": "machine", "confidence": "guess"}
    if not rec: missing.append(en); continue
    rec["kind"] = sorted(e["kinds"]); rec["priority"] = e["prio"]
    if en in en2key: rec["gameKey"] = en2key[en]
    res[en] = rec; stats[f'{rec["source"]}/{rec["confidence"]}'] += 1
pc = collections.Counter(v["priority"] for v in res.values())
meta = {"generated": "2026-10-30", "keys": "exact English names from data/items.en.json (name), data/recipes.en.json (station, alt_stations, unlock.name, mastery.type) and item categories",
        "priority": {"1": "listed obtainable item", "2": "station", "3": "category", "4": "technology", "5": "other (buildings, actions, unlisted items...)"},
        "sources": {"gk1-wiki": "Graveyard Keeper 1 pt-BR Fandom page title linked from the EN page; GK2 may word it differently",
                    "machine": "translated by Claude, not from the game"},
        "note": "No official GK2 pt-BR text is publicly available. gameKey = the GK2 locale key, so official strings exported from the player's own copy (lng_pt-br) can replace these later.",
        "counts": dict(stats), "byPriority": {str(k): v for k, v in sorted(pc.items())}, "missing": missing}
json.dump({"_meta": meta, **res}, open(f"{D}/names.pt-BR.json", "w"), ensure_ascii=False, indent=1)
print(dict(stats), "total", len(res), "byPrio", dict(pc), "withKey", sum(1 for v in res.values() if "gameKey" in v))
print("MISSING", len(missing)); print(" | ".join(missing))
