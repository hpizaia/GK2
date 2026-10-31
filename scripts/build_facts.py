#!/usr/bin/env python3
"""Build data/facts.json: per-item facts from the wikily item pages that the recipe dataset leaves out.

Run from the project root (stdlib only):
    python3 -I scripts/build_facts.py            # writes data/facts.json (only when its bytes change)
    python3 -I scripts/build_facts.py --check    # builds + validates, writes nothing

Then `python3 -I scripts/build.py` copies the facts into data/gk2.json (items[].where / .use / .stack, plus the
name tables in meta.refs) and into the page. Format: data/README-data.md ("facts.json").

What comes from data/raw/api-items-all.json (the wiki's item dataset, already cached; nothing is downloaded):
  * where:  soldBy (who sells it, from which trader level) and otherSources (fishing spot + bait + day/night
            chance, gathering nodes, quests, battles, start chests, looter orders, autopsy...). "Built in the
            Barracks" sources are skipped: the build recipe already says it.
  * use:    energy restored (`energy`), insanity change (`insanity`), the value under a boosting buff (the
            "+22 with Steamed Up" chip of the Energy / Insanity stat) and the buff the item grants (`buffs`:
            name + duration).
  * stack:  stack size (`stack`, every item page).
Names (traders, places, quests, buffs) are interned into small tables keyed by slug, so each item stores ids.
pt names: the game's own text table (data/game-texts/gk2_textos.json, exact English match) first, then
data/names.official.pt-BR.json, then the hand glossary MT below (tr "machine", shown as "não oficial").
Wiki and game texts are untrusted data: they are only parsed, never executed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# order of the source lines on the item card: shops first, then fishing, gathering, the rest in wiki order
KIND = {"Fishing": "fish", "Gathering": "gather", "Quest": "quest", "Battle": "battle", "Chest": "chest",
        "Found": "found", "Looter order": "looter", "Autopsy": "autopsy", "Burial": "burial",
        "Container": "container", "Town": "town", "Study Table": "study", "Church": "church", "Start": "start",
        "Outfit": "outfit", "Resurrection": "resurrect", "Character": "character"}
SKIP_KINDS = {"Barracks"}
ORDER = {"buy": 0, "fish": 1, "gather": 2}
ITEM_HREF = ("/items/", "/crafting-stations/", "/buildings/")

# Hand glossary for source names the game text table does not have (tr "machine": the page marks them
# "não oficial"). Vocabulary follows the app's pt obtain texts ("jazidas de pedra", "pilhas de sucata"...).
MT = {
    "Tree": "Árvore", "Creepy tree": "Árvore sinistra", "Dead tree": "Árvore morta", "Driftwood": "Madeira flutuante",
    "Tree stump": "Toco de árvore", "Bush": "Arbusto", "Stone deposit": "Jazida de pedra",
    "Iron ore deposit": "Jazida de minério de ferro", "Marble deposit": "Jazida de mármore",
    "Copper vein": "Veio de cobre", "Clay spot": "Ponto de argila", "Sand pit": "Areal", "Junk pile": "Pilha de sucata",
    "Trash pile": "Pilha de lixo", "Broken barrel": "Barril quebrado", "Broken shelf": "Estante quebrada",
    "Red mushrooms": "Cogumelos vermelhos", "Brown mushrooms": "Cogumelos marrons",
    "Swamp mushrooms": "Cogumelos do pântano", "Wild beehive": "Colmeia selvagem",
    "Goddess of Nature statue": "Estátua da Deusa da Natureza", "Bodies": "Corpos",
    "Burying a corpse": "Enterrar um corpo", "Sermons": "Sermões", "The prologue": "O prólogo",
    "The Keeper's tool belt": "Cinto de ferramentas do Coveiro", "Pre-order bonus": "Bônus da pré-venda",
    "Blue Techbooks": "Livros Azuis de Tecnologia", "Green Techbooks": "Livros Verdes de Tecnologia",
    "Red Techbooks": "Livros Vermelhos de Tecnologia", "Random Techbooks": "Livros de Tecnologia aleatórios",
    "Seeds": "Sementes", "Valuables": "Objetos de valor",
    # buff descriptions the game table lacks (wiki chip, translated)
    "+2 to all five masteries": "+2 nas cinco maestrias",
}
# <sprite name="x"> tokens inside official buff descriptions -> words
SPRITE_WORDS = {
    "talent_orange": ("Engenharia", "Building mastery"), "talent_red": ("Metalurgia", "Smithing mastery"),
    "talent_green": ("Agricultura", "Farming mastery"), "talent_yellow": ("Escrita de livros", "Book writing mastery"),
    "talent_blue": ("Anatomia", "Anatomy mastery"), "energy": ("energia", "energy"), "en": ("energia", "energy"),
    "insanity": ("insanidade", "insanity"), "hp": ("saúde", "health"),
}
DURATION_RE = re.compile(r"^For (?:(\d+) min)?\s*(?:(\d+) s)?$")
LEVEL_RE = re.compile(r"^From trader level (\d+)$")
FISH_RE = re.compile(r"^(.+?): ([\d.]+)%(?: by day, ([\d.]+)% at night|, day and night)$")
BOOST_RE = re.compile(r"^([+-]\d+) with (.+)$")


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def num(s):
    v = float(s)
    return int(v) if v == int(v) else v


class Texts:
    """pt for an English name: game text table (exact, case-insensitive), official names layer, glossary."""

    def __init__(self, game_text, official):
        self.game = {}
        self.table = game_text
        for k in sorted(game_text):
            v = game_text[k]
            if isinstance(v, dict) and isinstance(v.get("en"), str) and isinstance(v.get("pt"), str) and v["pt"].strip():
                self.game.setdefault(v["en"].strip().lower(), (k, v["pt"].strip()))
        self.official = {k: v for k, v in official.items() if isinstance(v, dict) and v.get("pt")}

    def loc(self, en):
        hit = self.game.get(en.strip().lower())
        if hit:
            return {"en": en, "pt": hit[1]}, hit[0]
        o = self.official.get(en)
        if o:
            return {"en": en, "pt": o["pt"]}, o.get("gameKey")
        if en in MT:
            return {"en": en, "pt": MT[en], "tr": "machine"}, None
        return {"en": en, "pt": en, "tr": "missing"}, None

    def sprite_words(self, s, lang):
        i = 0 if lang == "pt" else 1
        s = re.sub(r'<sprite name="([^"]+)">', lambda m: " " + SPRITE_WORDS.get(m.group(1), ("", ""))[i], s)
        return re.sub(r"\s+", " ", s).replace(" .", ".").strip()


def build(raw, items_en, texts):
    known = {i["id"] for i in items_en if isinstance(i, dict) and i.get("id")}
    names, buffs, out, warnings = {}, {}, {}, []

    def intern(en):
        key = slugify(en)
        loc, gkey = texts.loc(en)
        if key in names and names[key]["en"] != en:
            warnings.append(f"name slug clash: {key!r} for {names[key]['en']!r} and {en!r}")
        if key not in names:
            names[key] = dict(loc, **({"key": gkey} if gkey else {}))
        return key

    def buff(en, desc_en=None):
        key = slugify(en)
        if key in buffs:
            return key
        loc, gkey = texts.loc(en)
        b = dict(loc)
        d = texts.table.get(gkey + "_d") if gkey else None
        if isinstance(d, dict) and d.get("en") and d.get("pt") and "Description" not in d["en"]:
            b["d"] = {"en": texts.sprite_words(d["en"], "en"), "pt": texts.sprite_words(d["pt"], "pt")}
        elif desc_en:
            dl, _ = texts.loc(desc_en)
            b["d"] = {"en": desc_en, "pt": dl["pt"]}
            if dl.get("tr"):
                b["dtr"] = dl["tr"]
        if gkey:
            b["key"] = gkey
        buffs[key] = b
        return key

    def ref(o):
        href = o.get("href") or ""
        if href.startswith(ITEM_HREF):
            iid = href.rsplit("/", 1)[-1]
            if iid in known:
                return "@" + iid
        title = o["title"]
        if o["kind"] == "Fishing":
            title = re.sub(r" fishing spot$", "", title)
        elif o["kind"] == "Looter order":
            title = re.sub(r"^Looter order: ", "", title)
        return intern(title)

    rows = raw["rows"] if isinstance(raw, dict) else raw
    for row in sorted(rows, key=lambda r: r.get("key") or ""):
        iid, D = row.get("key"), row.get("data") or {}
        if iid not in known:
            if D.get("soldBy") or D.get("otherSources"):
                warnings.append(f"item {iid!r} is not in items.en.json; skipped")
            continue
        rec = {}
        # ---- where
        where, seen = [], set()
        for s in D.get("soldBy") or []:
            en = re.sub(r"\s*\([^)]*\)$", "", s.get("title") or "").strip()
            if not en:
                continue
            key = intern(en)
            chips = s.get("chips") or []
            if "conversation" in (s.get("subtitle") or ""):
                lvl = "talk"
            elif "From the start" in chips:
                lvl = 0
            else:
                lv = [int(m.group(1)) for c in chips for m in [LEVEL_RE.match(c)] if m]
                lvl = min(lv) if lv else 0
            prev = next((w for w in where if w[1] == key), None)
            if prev is not None:       # the same trader in several grades (Bronze/Silver/Gold): lowest level
                old = prev[2] if len(prev) > 2 else 0
                if isinstance(old, int) and isinstance(lvl, int) and lvl < old:
                    prev[2:] = [lvl] if lvl else []
                continue
            where.append(["buy", key] + ([lvl] if lvl else []))
        for o in D.get("otherSources") or []:
            kind = o.get("kind")
            if kind in SKIP_KINDS or not o.get("title"):
                continue
            k = KIND.get(kind)
            if not k:
                warnings.append(f"{iid}: unknown source kind {kind!r}")
                continue
            r = ref(o)
            if k == "fish":
                best = None
                for c in o.get("chips") or []:
                    m = FISH_RE.match(c)
                    if not m:
                        continue
                    day = num(m.group(2))
                    night = num(m.group(3)) if m.group(3) else day
                    bait = slugify(m.group(1))
                    bait = bait if bait in known else None
                    if best is None or max(day, night) > max(best[1], best[2]):
                        best = (bait, day, night)
                if best is None:
                    warnings.append(f"{iid}: fishing source without a bait chip")
                    entry = ["fish", r]
                else:
                    entry = ["fish", r, best[0] or "no-bait", best[1], best[2]]
            else:
                entry = [k, r]
            sig = (entry[0], entry[1])
            if sig in seen:
                continue
            seen.add(sig)
            where.append(entry)
        where.sort(key=lambda w: ORDER.get(w[0], 9))      # stable: wiki order inside each kind
        if where:
            rec["where"] = where
        # ---- use: energy / insanity (+ the value under a buff) and the buff it grants
        use = {}
        for field, stat in (("en", "Energy"), ("ins", "Insanity")):
            v = D.get("energy" if field == "en" else "insanity")
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v:
                use[field] = num(v)
                for s in D.get("statStrip") or []:
                    if s.get("subtitle") != stat:
                        continue
                    for c in s.get("chips") or []:
                        m = BOOST_RE.match(c)
                        if m:
                            use[field + "B"] = [int(m.group(1)), buff(m.group(2))]
        for b in D.get("buffs") or []:
            m = DURATION_RE.match(b.get("subtitle") or "")
            secs = (int(m.group(1) or 0) * 60 + int(m.group(2) or 0)) if m and (m.group(1) or m.group(2)) else None
            chips = [c for c in b.get("chips") or [] if not c.startswith(("Using another", "Ends ", "The Keeper's"))]
            key = buff(b.get("title") or "", chips[0] if chips else None)
            use["buff"] = [key] + ([secs] if secs else [])
            if any(c.startswith("Using another") for c in b.get("chips") or []):
                use["buff"].append(1)
            break                                          # one buff per item in 1.010
        if use:
            rec["use"] = use
        st = D.get("stack")
        if isinstance(st, int) and not isinstance(st, bool) and st > 0:
            rec["stack"] = st
        if rec:
            out[iid] = rec
    counts = {
        "items": len(out),
        "where": sum(1 for r in out.values() if "where" in r),
        "buy": sum(1 for r in out.values() if any(w[0] == "buy" for w in r.get("where", []))),
        "fish": sum(1 for r in out.values() if any(w[0] == "fish" for w in r.get("where", []))),
        "energy": sum(1 for r in out.values() if "en" in r.get("use", {})),
        "insanity": sum(1 for r in out.values() if "ins" in r.get("use", {})),
        "buff": sum(1 for r in out.values() if "buff" in r.get("use", {})),
        "stack": sum(1 for r in out.values() if "stack" in r),
        "names": len(names),
        "names_unofficial": sum(1 for n in names.values() if n.get("tr")),
        "buffs": len(buffs),
    }
    doc = {"meta": {"source": "data/raw/api-items-all.json (wikily.gg items dataset)",
                    "counts": counts, "format": "data/README-data.md#facts"},
           "names": dict(sorted(names.items())), "buffs": dict(sorted(buffs.items())), "items": out}
    return doc, warnings


def validate(doc):
    errors = []
    for iid, r in doc["items"].items():
        for w in r.get("where", []):
            ref = w[1]
            if ref.startswith("@"):
                continue
            if ref not in doc["names"]:
                errors.append(f"{iid}: unknown name ref {ref!r}")
        for f in ("enB", "insB"):
            if f in r.get("use", {}) and r["use"][f][1] not in doc["buffs"]:
                errors.append(f"{iid}: unknown buff {r['use'][f][1]!r}")
        b = r.get("use", {}).get("buff")
        if b and b[0] not in doc["buffs"]:
            errors.append(f"{iid}: unknown buff {b[0]!r}")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build data/facts.json from the wikily item dump")
    ap.add_argument("--raw", default=str(DATA / "raw" / "api-items-all.json"))
    ap.add_argument("--items", default=str(DATA / "items.en.json"), help="ids that exist (read-only)")
    ap.add_argument("--game-text", default=str(DATA / "game-texts" / "gk2_textos.json"))
    ap.add_argument("--official", default=str(DATA / "names.official.pt-BR.json"))
    ap.add_argument("--out", default=str(DATA / "facts.json"))
    ap.add_argument("--check", action="store_true", help="build and validate, write nothing")
    args = ap.parse_args(argv)
    try:
        raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
        items_en = json.loads(Path(args.items).read_text(encoding="utf-8"))
        game = json.loads(Path(args.game_text).read_text(encoding="utf-8")) if args.game_text else {}
        official = json.loads(Path(args.official).read_text(encoding="utf-8")) if args.official else {}
    except (OSError, ValueError) as e:
        print(f"build_facts: cannot read inputs: {e}", file=sys.stderr)
        return 2
    doc, warnings = build(raw, items_en, Texts(game, official))
    errors = validate(doc)
    print(f"build_facts: {doc['meta']['counts']}")
    for w in warnings:
        print(f"build_facts: warning: {w}")
    for e in errors:
        print(f"build_facts: ERROR: {e}", file=sys.stderr)
    if not args.check and not errors:
        out = Path(args.out)
        text = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            out.write_text(text, encoding="utf-8")
            print(f"build_facts: wrote {out} ({out.stat().st_size:,} bytes)")
        else:
            print("build_facts: data/facts.json up to date")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
