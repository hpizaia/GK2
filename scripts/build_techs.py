#!/usr/bin/env python3
"""Build data/techs.json (the GK2 technology tree, pt-BR/EN) from the wikily.gg technologies dump.

    python3 -I scripts/build_techs.py                 # write data/techs.json, print the validation report
    python3 -I scripts/build_techs.py --check         # build + validate only, write nothing
    python3 -I scripts/build_techs.py --raw PATH --data PATH --out PATH [--names A B C] [--game-text PATH]

Inputs (all read-only):
    data/raw/api-technologies-all.json   {rows: [{key, data: {...}}]}, one row per technology
    data/gk2.json                        items / stations / recipes (recipes[].tech.id = technology slug)
    data/names.official.pt-BR.json       official pt-BR names (game files), keyed by English name
    data/names.pt-BR.json                GK1-wiki (likely) and machine (guess) names
    data/names.machine.pt-BR.json        machine fallback layer
    data/game-texts/gk2_textos.json   the game's own {key: {en, pt}} text table (optional);
                                         fills official names the names files lack (branch tabs, quests,
                                         NPCs, a few technologies)

pt name priority: official file > game text table (official) > likely > guess > machine > missing.
Exit codes: 0 ok, 1 validation errors, 2 usage / IO error. Python 3 stdlib only.
"""

import argparse
import datetime
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TIERS = ("official", "likely", "guess", "machine", "missing")
TIER_RANK = {t: i for i, t in enumerate(TIERS)}
COLOURS = ("red", "green", "blue")
QUALITY_RE = re.compile(r"\s*\((bronze|silver|gold)\)\s*$", re.I)
QUALITY_PT = {"bronze": "bronze", "silver": "prata", "gold": "ouro"}   # as in gk2.json derived names

# Small hand translations (tier machine) for free-text strings no layer has.
MACHINE_PT = {
    # branches / tech points, only used if no official source has them
    "Building": "Construção", "Metallurgy": "Metalurgia", "Farming": "Agricultura", "Theology": "Teologia",
    "Anatomy and Alchemy": "Anatomia e alquimia", "Cooking": "Culinária",
    # availability events that are not quests / items
    "Placing the first body on the autopsy table": "colocar o primeiro corpo na mesa de autópsia",
    "Putting the sign on the first grave in the intro": "pôr a placa no primeiro túmulo, na introdução",
    "Waking up at home in the intro": "acordar em casa, na introdução",
    "Repair Oven": "consertar o forno", "Repair Table": "consertar a mesa",
    "Clearing both Old Mine blockages (the Quarry entrance with 1 Dynamite and the passage from the Factory "
    "with 4 Building Kit I and 1 Reinforced Beam)":
        "desobstruir as duas passagens da Mina Velha (a entrada da Pedreira com 1 Dinamite e a passagem da "
        "Fábrica com 4 Kit de Construção I e 1 Viga Reforçada)",
    # notesText
    "Autopsy: Heart and Guts can now be extracted.": "Autópsia: agora é possível extrair Coração e Entranhas.",
    "Autopsy: Brain can now be extracted.": "Autópsia: agora é possível extrair o Cérebro.",
    "Autopsy: Skin and Bones can now be extracted.": "Autópsia: agora é possível extrair Pele e Ossos.",
    "Autopsy: Skull can now be extracted.": "Autópsia: agora é possível extrair a Caveira.",
    "Garden beds get 1 fertilizer slot.": "Os canteiros ganham 1 espaço para fertilizante.",
    "Garden beds get 2 fertilizer slots.": "Os canteiros ganham 2 espaços para fertilizante.",
    "Unlocks an extra look in character customization.":
        "Libera um visual extra na personalização do personagem.",
    "One of the two steps that open the Improve the Church II upgrade (the other: completing Improve the Church I).":
        "Um dos dois passos que liberam a melhoria Melhorar a Igreja II (o outro: concluir Melhorar a Igreja I).",
    "One of the two steps that open the Improve the Church III upgrade (the other: completing Improve the Church II).":
        "Um dos dois passos que liberam a melhoria Melhorar a Igreja III (o outro: concluir Melhorar a Igreja II).",
}
TP_PT = {"red": "Pontos tecnológicos vermelhos", "green": "Pontos tecnológicos verdes",
         "blue": "Pontos tecnológicos azuis"}   # "pontos tecnológicos" is the game's own term (tut_tech_1)
HOW_PT = {"Quest": "missão", "Story": "história", "Crafting": "fabricar", "Harvest": "colher",
          "Fishing": "pescar", "Repair": "consertar", "Building": "construir", "Eating or using it": "comer ou usar"}


def norm_key(s):
    s = unicodedata.normalize("NFC", str(s))
    s = s.replace("’", "'").replace("‘", "'").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().casefold()


def clean(s):
    return re.sub(r"\s+", " ", str(s)).strip() if isinstance(s, str) else ""


def sentence(s):
    s = clean(s)
    return s if not s or s[-1] in ".!?" else s + "."


# --------------------------------------------------------------------------- names

class Names:
    """English name -> (pt, tier, source), merged over the layers by tier (first layer wins a tie)."""

    def __init__(self, name_files, game_text=None):
        self.names = {}
        for i, path in enumerate(name_files):
            p = Path(path)
            if not p.exists():
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            machine_file = "machine" in p.name
            for k, v in data.items():
                if not isinstance(k, str) or k.startswith("_") or not isinstance(v, dict):
                    continue
                pt = v.get("pt")
                if not isinstance(pt, str) or not pt.strip():
                    continue
                conf = str(v.get("confidence") or "").lower()
                if machine_file or str(v.get("source") or "").lower() == "machine":
                    tier = "machine"
                elif conf in ("official", "likely", "guess"):
                    tier = conf
                else:
                    tier = "guess"
                self._add(k, pt.strip(), tier, p.stem)
        # game text table: {key: {en, pt}}; en -> list of (key, pt)
        self.game = defaultdict(list)
        if game_text and Path(game_text).exists():
            gt = json.loads(Path(game_text).read_text(encoding="utf-8"))
            for key, v in gt.items():
                if isinstance(v, dict) and isinstance(v.get("en"), str) and isinstance(v.get("pt"), str) and v["pt"].strip():
                    self.game[norm_key(v["en"])].append((key, clean(v["pt"])))

    def _add(self, en, pt, tier, source):
        nk = norm_key(en)
        prev = self.names.get(nk)
        if prev and TIER_RANK[prev[1]] <= TIER_RANK[tier]:
            return
        self.names[nk] = (pt, tier, source)

    def game_pt(self, en, prefer=()):
        """Official pt from the game text table, or None. `prefer`: key regexes tried in order;
        otherwise the most common pt among the matching keys."""
        hits = self.game.get(norm_key(en)) or []
        if not hits:
            return None
        for pat in prefer:
            for key, pt in hits:
                if re.search(pat, key):
                    return pt
        return Counter(pt for _, pt in hits).most_common(1)[0][0]

    def name(self, en, prefer=()):
        """-> (pt, tier, source); (None, 'missing', None) when nothing has it."""
        if not en:
            return None, "missing", None
        hit = self.names.get(norm_key(en))
        if hit and hit[1] == "official":
            return hit
        g = self.game_pt(en, prefer)
        if g:
            return g, "official", "game-text"
        if hit:
            return hit
        if en in MACHINE_PT:
            return MACHINE_PT[en], "machine", "build_techs"
        return None, "missing", None


# --------------------------------------------------------------------------- build

def href_parts(href):
    parts = [p for p in str(href or "").split("/") if p]
    return (parts[0], parts[-1]) if parts else ("", "")


def build(raw, ds, names, built=None):
    rows = raw["rows"] if isinstance(raw, dict) else raw
    items, stations, recipes = ds.get("items") or {}, ds.get("stations") or {}, ds.get("recipes") or []
    item_by_name = {}
    for iid in sorted(items):
        item_by_name.setdefault(norm_key(items[iid].get("en") or ""), iid)
    station_by_name = {}
    for sid in sorted(stations):
        station_by_name.setdefault(norm_key(stations[sid].get("en") or ""), sid)
    url2items = defaultdict(list)
    for iid in sorted(items):
        if items[iid].get("icon"):
            url2items[items[iid]["icon"]].append(iid)
    for sid in sorted(stations):
        if stations[sid].get("icon") and sid not in url2items[stations[sid]["icon"]]:
            url2items[stations[sid]["icon"]].append(sid)
    recipes_by_tech = defaultdict(list)
    for r in recipes:
        t = r.get("tech")
        if isinstance(t, dict) and t.get("id") and t.get("type", "technology") == "technology":
            recipes_by_tech[t["id"]].append(r["id"])

    def item_pt(iid):
        it = items.get(iid) or stations.get(iid) or {}
        return it.get("pt"), it.get("tr") or "missing"

    branches, techs, icon_urls, tp = {}, {}, {}, {}
    for row in rows:
        d = row["data"]
        slug = d.get("slug") or row["key"]
        bkey = d.get("branchKey")
        if bkey not in branches:
            ben = clean(d.get("branch"))
            bpt, btr, _ = names.name(ben, prefer=(r"^tech_tab_",))
            if bpt is None:   # e.g. "Anatomy and Alchemy" vs the tab text "Anatomy\nand alchemy"
                bpt, btr = MACHINE_PT.get(ben), "machine"
            tl = (d.get("treeLink") or [{}])[0]
            branches[bkey] = {"pt": bpt, "en": ben, "order": d.get("branchOrder"), "tr": btr,
                              "icon": f"branch:{bkey}"}
            if tl.get("icon"):
                icon_urls[f"branch:{bkey}"] = tl["icon"]
        for c in d.get("costs") or []:
            col = next((k for k in COLOURS if k in str(c.get("label", "")).lower()), None)
            if col and col not in tp:
                tp[col] = {"en": c.get("label"), "pt": TP_PT[col], "tr": "likely", "color": c.get("color"),
                           "icon": f"tp:{col}"}
                if c.get("icon"):
                    icon_urls[f"tp:{col}"] = c["icon"]

        # name
        en = clean(d.get("name"))
        pt, tr, _ = names.name(en, prefer=(r"^tech_",))
        disp = clean(d.get("displayName"))
        if (tr not in ("official",)) and disp and disp != en:
            # "Fabric (Building)" -> in-game name "Fabric" + the branch, to tell the two apart
            dpt, dtr, _ = names.name(disp, prefer=(r"^tech_",))
            if dtr == "official":
                pt, tr = f"{dpt} ({branches[bkey]['pt']})", "likely"
        if pt is None:
            pt, tr = en, "missing"

        # unlocks
        unlocks = []
        for u in d.get("unlocks") or []:
            title = clean(u.get("title"))
            prefix, hslug = href_parts(u.get("href"))
            iid = None
            if norm_key(title) in item_by_name:            # exact name first: "Wine (gold)" is its own item
                iid = item_by_name[norm_key(title)]
            elif hslug in items:
                iid = hslug
            elif hslug in stations:
                iid = hslug
            if prefix == "items":
                kind = "item"
            elif prefix == "alchemy":
                kind = "recipe"
            elif prefix in ("buildings", "crafting-stations", "town-buildings"):
                kind = "building"
            elif iid:
                kind = "building" if (items.get(iid) or {}).get("kind") in ("building", "station") else "item"
            else:
                kind = "other"
            ien = (items.get(iid) or stations.get(iid) or {}).get("en") or "" if iid else ""
            qm = QUALITY_RE.search(title)
            if iid and norm_key(ien) == norm_key(title):
                upt, utr = item_pt(iid)
            elif iid and qm and norm_key(ien) == norm_key(title[:qm.start()]) and item_pt(iid)[0]:
                # "Wine (gold)" unlocks the gold recipe of item `wine`: keep the grade in the name
                upt, utr = item_pt(iid)
                upt = f"{upt} ({QUALITY_PT[qm.group(1).lower()]})"
                utr = utr if TIER_RANK.get(utr, 4) >= TIER_RANK["likely"] else "likely"
            else:
                upt, utr, _ = names.name(title, prefer=(r"_t1$",))
                if upt is None and iid:
                    upt, utr = item_pt(iid)
            sub = clean(u.get("subtitle"))
            unlocks.append({"item": iid, "kind": kind, "en": title, "pt": upt, "tr": utr if upt else "missing",
                            "station": station_by_name.get(norm_key(sub))})

        # icon
        url = d.get("icon")
        cands = url2items.get(url) or []
        unlock_ids = [u["item"] for u in unlocks if u["item"]]
        icon = next((i for i in unlock_ids if i in cands), cands[0] if cands else None)
        if icon is None:
            icon = f"tech:{slug}"
            if url:
                icon_urls[icon] = url

        # gates / availability / notes
        rep = None
        for gte in d.get("gates") or []:
            m = re.search(r"(\d+)", str(gte.get("subtitle", "")))
            who = clean(gte.get("title"))
            wpt, _, _ = names.name(who, prefer=(r"^npc_",))
            rep = {"who": {"en": who, "pt": wpt or who}, "level": int(m.group(1)) if m else None}
        en_lines, pt_lines = [], []
        for a in d.get("availability") or []:
            title, sub = clean(a.get("title")), clean(a.get("subtitle"))
            how = sub.split(":", 1)[1].strip() if ":" in sub else ""
            mode = sub.split(":", 1)[0].strip()
            prefix, hslug = href_parts(a.get("href"))
            obj_en, obj_pt = title, None
            if how == "Quest":
                obj_en = f"quest {title}"
                qpt = names.game_pt(title, prefer=(r"^\d+_",))
                obj_pt = f"missão {qpt or title}"
            elif prefix == "characters":
                m = re.match(r"(.+?) reaches (\d+) reputation", title)
                if m:
                    wpt, _, _ = names.name(m.group(1), prefer=(r"^npc_",))
                    obj_pt = f"{wpt or m.group(1)} chegar a {m.group(2)} de reputação"
            elif hslug and (hslug in items or hslug in stations) and how in HOW_PT:
                ipt = item_pt(hslug)[0]
                if ipt:
                    obj_pt = f"{HOW_PT[how]} {ipt}"
            if obj_pt is None:
                obj_pt = MACHINE_PT.get(title) or names.name(title)[0] or title
            if mode.startswith("Revealed by"):
                en_lines.append(f"Hidden in the tree until revealed by: {obj_en}")
                pt_lines.append(f"Oculta na árvore até ser revelada por: {obj_pt}")
            elif mode.startswith("Given for free and revealed"):
                en_lines.append(f"Given for free and revealed by: {obj_en}")
                pt_lines.append(f"Recebida de graça e revelada por: {obj_pt}")
            else:
                en_lines.append(f"Given for free: {obj_en}")
                pt_lines.append(f"Recebida de graça ao {obj_pt}" if how in ("Story",) else f"Recebida de graça: {obj_pt}")
        if rep:
            en_lines.append(f"Needs {rep['level']} reputation with {rep['who']['en']}")
            pt_lines.append(f"Requer {rep['level']} de reputação com {rep['who']['pt']}")
        note = clean(d.get("notesText"))
        if note:
            en_lines.append(note)
            pt_lines.append(MACHINE_PT.get(note) or note)
        notes = None
        if en_lines:
            notes = {"pt": " ".join(sentence(s) for s in pt_lines), "en": " ".join(sentence(s) for s in en_lines)}

        cost = {"red": d.get("costRed"), "green": d.get("costGreen"), "blue": d.get("costBlue")}
        cost = {k: int(v) if isinstance(v, (int, float)) and float(v).is_integer() else v for k, v in cost.items()}
        listed = d.get("listed")
        techs[slug] = {
            "id": slug, "pt": pt, "en": en, "tr": tr,
            "branch": bkey, "column": d.get("column"), "x": d.get("x"), "y": d.get("y"),
            "listed": listed is True or str(listed).strip().lower() in ("yes", "true", "1"),
            "hidden": clean(d.get("badge")) == "Hidden",
            "given": clean(d.get("badge")) == "Given",
            "cost": cost,
            "parents": list(d.get("parents") or []),
            "children": [],
            "rep": rep,
            "unlocks": unlocks,
            "recipes": sorted(recipes_by_tech.get(slug, [])),
            "icon": icon,
            "notes": notes,
        }
    for slug, t in techs.items():
        for p in t["parents"]:
            if p in techs:
                techs[p]["children"].append(slug)
    for t in techs.values():
        t["children"].sort(key=lambda s: (techs[s]["column"] or 0, techs[s]["y"] or 0, s))

    order = sorted(branches, key=lambda k: (branches[k]["order"] if branches[k]["order"] is not None else 99, k))
    disambiguate(techs, order)
    doc = {
        "meta": {"built": built or datetime.date.today().isoformat(), "count": len(techs), "branches": order,
                 "langs": ["pt", "en"], "sources": ["wikily.gg technologies", "data/gk2.json", "names layers",
                                                     "game text table"],
                 "tp": {k: tp[k] for k in COLOURS if k in tp}},
        "branches": {k: branches[k] for k in order},
        "techs": {k: techs[k] for k in sorted(techs, key=lambda s: (order.index(techs[s]["branch"]),
                                                                    techs[s]["column"] or 0, techs[s]["y"] or 0, s))},
        "icons": dict(sorted(icon_urls.items())),
    }
    return doc


ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")


def disambiguate(techs, order):
    """Technologies whose pt name is shared by different English names get " I", " II", ... in tree order
    (branch, column, y). The game itself calls Bronze Works, Bronze Craft and Bronze Polishing all
    "Maestria em Bronze" (keys bronze_works, bronze_details, bronze_polishing), which makes the list, the
    search and the planner's "Tecnologias que faltam" ambiguous. The numbered name gets tier "likely" (it is
    the official name plus our numeral) and a note with the in-game name. Returns {pt: [slug, ...]}."""
    groups = defaultdict(list)
    for slug, t in techs.items():
        if t["pt"] and t["tr"] != "missing":
            groups[norm_key(t["pt"])].append(slug)
    done = {}
    for slugs in groups.values():
        if len(slugs) < 2 or len({norm_key(techs[s]["en"]) for s in slugs}) < 2 or len(slugs) > len(ROMAN):
            continue
        slugs.sort(key=lambda s: (order.index(techs[s]["branch"]) if techs[s]["branch"] in order else 99,
                                  techs[s]["column"] or 0, techs[s]["y"] or 0, s))
        base = techs[slugs[0]]["pt"]
        n = len(slugs)
        for i, s in enumerate(slugs):
            t = techs[s]
            t["pt"] = f"{base} {ROMAN[i]}"
            if t["tr"] == "official":
                t["tr"] = "likely"
            pt_note = (f"No jogo, as {n} tecnologias se chamam “{base}”; o número ({', '.join(ROMAN[:n])}) "
                       f"segue a ordem na árvore.")
            en_note = (f"In the Portuguese version these {n} technologies are all called “{base}”; the numeral "
                       f"follows the tree order.")
            notes = t.get("notes") or {"pt": "", "en": ""}
            t["notes"] = {"pt": (notes["pt"] + " " + pt_note).strip(), "en": (notes["en"] + " " + en_note).strip()}
        done[base] = slugs
    return done


# --------------------------------------------------------------------------- validate

def validate(doc, ds, raw=None):
    """-> {"errors": [...], "warnings": [...], "counts": {...}, "missing_recipe_techs": [...]}"""
    techs = doc["techs"]
    errors, warnings = [], []
    for s, t in techs.items():
        for p in t["parents"]:
            if p not in techs:
                errors.append(f"{s}: parent {p!r} does not exist")
        for k in COLOURS:
            v = t["cost"].get(k)
            if not (isinstance(v, int) and not isinstance(v, bool) and v >= 0):
                errors.append(f"{s}: cost.{k} = {v!r} is not a non-negative int")
        if t["branch"] not in doc["branches"]:
            errors.append(f"{s}: unknown branch {t['branch']!r}")
    # DAG: Kahn
    indeg = {s: sum(1 for p in t["parents"] if p in techs) for s, t in techs.items()}
    queue = [s for s, n in indeg.items() if n == 0]
    seen = 0
    while queue:
        s = queue.pop()
        seen += 1
        for c in techs[s]["children"]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    if seen != len(techs):
        errors.append(f"prerequisite graph has a cycle among {sorted(s for s, n in indeg.items() if n > 0)}")
    # recipe techs
    missing = {}
    for r in ds.get("recipes") or []:
        tt = r.get("tech")
        if isinstance(tt, dict) and tt.get("id") and tt["id"] not in techs:
            m = missing.setdefault(tt["id"], {"id": tt["id"], "en": tt.get("en"), "pt": tt.get("pt"),
                                              "type": tt.get("type"), "recipes": []})
            m["recipes"].append(r["id"])
    for m in missing.values():
        (errors if m["type"] == "technology" else warnings).append(
            f"recipe tech {m['id']!r} ({m['type']}) has no technology record ({len(m['recipes'])} recipes)")
    # raw cross-checks
    if raw is not None:
        rows = {r["key"]: r["data"] for r in (raw["rows"] if isinstance(raw, dict) else raw)}
        for s, d in rows.items():
            t = techs.get(s)
            if t is None:
                errors.append(f"raw technology {s!r} missing from output")
                continue
            pre = sorted(href_parts(p.get("href"))[1] for p in d.get("prerequisites") or [] if isinstance(p, dict))
            if pre and pre != sorted(t["parents"]):
                warnings.append(f"{s}: prerequisites {pre} != parents {sorted(t['parents'])}")
            leads = sorted(href_parts(p.get("href"))[1] for p in d.get("leadsTo") or [])
            if leads != sorted(t["children"]):
                warnings.append(f"{s}: leadsTo {leads} != derived children {sorted(t['children'])}")
            for col in COLOURS:
                tot = sum(int(c.get("value") or 0) for c in d.get("costs") or [] if col in str(c.get("label")).lower())
                if tot != t["cost"][col]:
                    warnings.append(f"{s}: costs[] {col} {tot} != cost{col.title()} {t['cost'][col]}")
            if isinstance(d.get("costTotal"), (int, float)) and d["costTotal"] != sum(t["cost"].values()):
                warnings.append(f"{s}: costTotal {d['costTotal']} != sum {sum(t['cost'].values())}")
    for t in techs.values():
        if t["icon"].startswith("tech:") and t["icon"] not in doc["icons"]:
            errors.append(f"{t['id']}: icon {t['icon']} has no URL in icons")
    items = ds.get("items") or {}
    for s, t in techs.items():
        if not t["icon"].startswith("tech:") and t["icon"] not in items and t["icon"] not in (ds.get("stations") or {}):
            errors.append(f"{s}: icon {t['icon']!r} is not an item/station id")

    unl = [u for t in techs.values() for u in t["unlocks"]]
    counts = {
        "techs": len(techs),
        "listed": sum(t["listed"] for t in techs.values()),
        "unlisted": sum(not t["listed"] for t in techs.values()),
        "hidden": sum(t["hidden"] for t in techs.values()),
        "given": sum(t["given"] for t in techs.values()),
        "free": sum(1 for t in techs.values() if not any(t["cost"].values())),
        "roots": sum(1 for t in techs.values() if not t["parents"]),
        "per_branch": dict(Counter(t["branch"] for t in techs.values())),
        "tr": {k: v for k, v in ((k, sum(1 for t in techs.values() if t["tr"] == k)) for k in TIERS) if v},
        "unlocks": len(unl),
        "unlocks_mapped": sum(1 for u in unl if u["item"]),
        "unlocks_unmapped": sum(1 for u in unl if not u["item"]),
        "unlocks_by_kind": dict(Counter(u["kind"] for u in unl)),
        "unlocks_pt_tr": dict(Counter(u["tr"] for u in unl)),
        "unlocks_unmapped_list": sorted({(u["en"]) for u in unl if not u["item"]}),
        "recipes_linked": sum(len(t["recipes"]) for t in techs.values()),
        "techs_with_recipes": sum(1 for t in techs.values() if t["recipes"]),
        "icons_item": sum(1 for t in techs.values() if not t["icon"].startswith("tech:")),
        "icons_own": sum(1 for t in techs.values() if t["icon"].startswith("tech:")),
        "notes": sum(1 for t in techs.values() if t["notes"]),
        "cost_total": {k: sum(t["cost"][k] for t in techs.values()) for k in COLOURS},
    }
    return {"errors": errors, "warnings": warnings, "counts": counts,
            "missing_recipe_techs": sorted(missing.values(), key=lambda m: m["id"])}


# --------------------------------------------------------------------------- CLI

def load_inputs(args):
    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    ds = json.loads(Path(args.data).read_text(encoding="utf-8"))
    names = Names(args.names, args.game_text)
    return raw, ds, names


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build data/techs.json from the wikily technologies dump")
    ap.add_argument("--raw", default=str(DATA / "raw" / "api-technologies-all.json"))
    ap.add_argument("--data", default=str(DATA / "gk2.json"), help="merged dataset (read-only)")
    ap.add_argument("--names", nargs="+", default=[str(DATA / "names.official.pt-BR.json"),
                                                    str(DATA / "names.pt-BR.json"),
                                                    str(DATA / "names.machine.pt-BR.json")])
    ap.add_argument("--game-text", default=str(ROOT / "data" / "game-texts" / "gk2_textos.json"),
                    help="game text table {key: {en, pt}} (optional; '' to skip)")
    ap.add_argument("--out", default=str(DATA / "techs.json"))
    ap.add_argument("--check", action="store_true", help="build and validate, write nothing")
    args = ap.parse_args(argv)
    try:
        raw, ds, names = load_inputs(args)
    except (OSError, ValueError) as e:
        print(f"build_techs: cannot read inputs: {e}", file=sys.stderr)
        return 2
    doc = build(raw, ds, names)
    rep = validate(doc, ds, raw)
    c = rep["counts"]
    print(f"build_techs: {c['techs']} techs ({c['listed']} listed, {c['unlisted']} unlisted, {c['hidden']} hidden, "
          f"{c['given']} given, {c['free']} free, {c['roots']} roots); per branch {c['per_branch']}")
    print(f"build_techs: tr {c['tr']}; unlocks {c['unlocks']} ({c['unlocks_mapped']} mapped to items, "
          f"{c['unlocks_unmapped']} unmapped) by kind {c['unlocks_by_kind']}, pt {c['unlocks_pt_tr']}")
    print(f"build_techs: {c['recipes_linked']} recipes linked to {c['techs_with_recipes']} techs; icons "
          f"{c['icons_item']} item / {c['icons_own']} own; {len(doc['icons'])} non-item icon URLs; {c['notes']} notes")
    if c["unlocks_unmapped_list"]:
        print(f"build_techs: unmapped unlocks: {', '.join(c['unlocks_unmapped_list'])}")
    for m in rep["missing_recipe_techs"]:
        print(f"build_techs: recipe tech without technology record: {m['id']} ({m['type']}, {m['en']!r}, "
              f"{len(m['recipes'])} recipes)")
    for w in rep["warnings"]:
        if not w.startswith("recipe tech"):
            print(f"build_techs: warning: {w}")
    for e in rep["errors"]:
        print(f"build_techs: ERROR: {e}", file=sys.stderr)
    if not args.check:
        out = Path(args.out)
        try:   # same tree as on disk: keep its meta.built (a rerun on another day writes nothing)
            old = json.loads(out.read_text(encoding="utf-8"))
            if dict(old, meta=dict(old["meta"], built=doc["meta"]["built"])) == doc:
                print(f"build_techs: {out} up to date (nothing written)")
                return 1 if rep["errors"] else 0
        except (OSError, ValueError, KeyError, TypeError):
            pass
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.name + ".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, out)
        print(f"build_techs: wrote {out} ({out.stat().st_size:,} bytes)")
    return 1 if rep["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
