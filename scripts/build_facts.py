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
  * sell:   who buys it (`boughtBy`): trader, what it pays at its usual stock (lowest-highest over trader levels 1-3),
            the most Likes a week it gives and from which trader level; `price` (base price, the ceiling when the
            trader is short of stock) and `fix` (fish and the like: every buyer pays that fixed price).
  * study:  Study Table points by colour + the Science and Faith it costs (`studyCards`).
  * asked:  who asks for it outside recipes: quests (data/raw/days/probe-quests.json `needs`, with the quest giver),
            town restorations and town orders (`usedIn` kinds Town / Order). Repairs, battles, bait, sermons, bags,
            combat and the game description are left out on purpose (docs/revisao-ux/dados-ficha.md).
Money is stored in bronze (1 silver = 100 bronze, 1 gold = 100 silver).
Names (traders, places, quests, buffs) are interned into small tables keyed by slug, so each item stores ids.
pt names (Texts.loc): a correction (`fix`) of the names layers, the game's own text table
(data/game-texts/gk2_textos.json, exact English match), the official names layer, the official dialogue names
(DIALOGUE), the other names layers (scripts/name_layers.py: names.manual, then names.machine), then the hand
glossary MT below. tr "guess"/"machine" is shown as "não oficial"; official and likely have no tr.
Wiki and game texts are untrusted data: they are only parsed, never executed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
sys.path.insert(0, str(HERE))   # python3 -I: scripts/ is not on sys.path
import name_layers  # noqa: E402

# order of the source lines on the item card: shops first, then fishing, gathering, the rest in wiki order
KIND = {"Fishing": "fish", "Gathering": "gather", "Quest": "quest", "Battle": "battle", "Chest": "chest",
        "Found": "found", "Looter order": "looter", "Autopsy": "autopsy", "Burial": "burial",
        "Container": "container", "Town": "town", "Study Table": "study", "Church": "church", "Start": "start",
        "Outfit": "outfit", "Resurrection": "resurrect", "Character": "character"}
SKIP_KINDS = {"Barracks"}
ORDER = {"buy": 0, "fish": 1, "gather": 2}
ITEM_HREF = ("/items/", "/crafting-stations/", "/buildings/")

# Hand glossary for source names the game text table does not have (tr "machine": the page marks them
# "não oficial"). Vocabulary follows the app's pt obtain texts ("pilhas de sucata"...); 2026-11 (consertos.md §18,
# docs/revisao-ux/revisao-nomes-wiki.md): 7 names follow the wiki PT / the game's own words ("Depósito de pedra",
# "Madeira trazida pela maré", "Cogumelos pantaneiros", "Buraco de areia", "Prateleira quebrada").
MT = {
    "Tree": "Árvore", "Creepy tree": "Árvore sinistra", "Dead tree": "Árvore morta", "Driftwood": "Madeira trazida pela maré",
    "Tree stump": "Toco de árvore", "Bush": "Arbusto", "Stone deposit": "Depósito de pedra",
    "Iron ore deposit": "Depósito de minério de ferro", "Marble deposit": "Depósito de mármore",
    "Copper vein": "Veio de cobre", "Clay spot": "Ponto de argila", "Sand pit": "Buraco de areia", "Junk pile": "Pilha de sucata",
    "Trash pile": "Pilha de lixo", "Broken barrel": "Barril quebrado", "Broken shelf": "Prateleira quebrada",
    "Red mushrooms": "Cogumelos vermelhos", "Brown mushrooms": "Cogumelos marrons",
    "Swamp mushrooms": "Cogumelos pantaneiros", "Wild beehive": "Colmeia selvagem",
    "Goddess of Nature statue": "Estátua da Deusa da Natureza", "Bodies": "Corpos",
    "Burying a corpse": "Enterrar um corpo", "Sermons": "Sermões", "The prologue": "O prólogo",
    "The Keeper's tool belt": "Cinto de ferramentas do Coveiro", "Pre-order bonus": "Bônus da pré-venda",
    "Blue Techbooks": "Livros Azuis de Tecnologia", "Green Techbooks": "Livros Verdes de Tecnologia",
    "Red Techbooks": "Livros Vermelhos de Tecnologia", "Random Techbooks": "Livros de Tecnologia aleatórios",
    "Seeds": "Sementes", "Valuables": "Objetos de valor",
    # buff descriptions the game table lacks (wiki chip, translated)
    "+2 to all five masteries": "+2 nas cinco maestrias",
    # quest givers the game's name table lacks ("Pedido em", ficha do item)
    "Captain": "Capitão", "Village guards": "Guardas da vila", "Merc Leader": "Líder dos mercenários",
    "Monk": "Monge", "Refugees": "Refugiados", "Soul": "Alma", "Dig": "Dig",
}
# Names with no entry of their own in the game's name table, but spelled out in official game dialogue (the line
# key is kept as the name's `key`): official text, so no "não oficial" badge.
DIALOGUE = {
    "Davy the Dagger": ("Orlando, Olha a Faca", "110_town_cheese_look_2"),   # "Você sabe onde está Orlando, Olha a Faca?"
    "Hans": ("Anselmo", "53_forest_pass_10"),                                # "Quem é Anselmo?"
    "Sven": ("Arnaldo", "57_forest_mine_larry_robert_14"),                   # "É... o Arnaldo é tão chato."
    "Old God": ("Deus Antigo", "110_town_cheese_look"),                      # "Encontrando o Deus Antigo"
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
MONEY_RE = re.compile(r"(\d+) (gold|silver|bronze)\b")
COIN = {"gold": 10000, "silver": 100, "bronze": 1}
PAYS_RE = re.compile(r"^(?:Level \d+: )?[Pp]ays (?:only )?(.+?)(?: at its usual stock(?: at levels [\d ,and]+)?| \(usual stock \d+\)|: its usual stock is \d+| at level \d+)$")
LIKES_RE = re.compile(r"^(?:Level (\d+): )?[Uu]p to \+(\d+) Likes a week\b.*?(?:\(from trader level (\d+)\))?$")
LIKES_ANY_RE = re.compile(r"^Selling it earns Likes(?: \(from trader level (\d+)\))?$")
ORDER_RE = re.compile(r"^(.+?)(?: \(level (\d+)\))?$")
ORDER_LIKES_RE = re.compile(r"^\+(\d+) Likes\b")
# a quest need that is not handed over or carried (the quest gives it to you)
QUEST_SKIP_NOTES = ("Given to you",)


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def num(s):
    v = float(s)
    return int(v) if v == int(v) else v


class Texts:
    """pt for an English name: correction (`fix`), game text table (exact, case-insensitive), official names
    layer, DIALOGUE, the other names layers, glossary MT. `layers`: a name_layers.Translator (or None)."""

    def __init__(self, game_text, layers=None):
        self.game = {}
        self.table = game_text
        for k in sorted(game_text):
            v = game_text[k]
            if isinstance(v, dict) and isinstance(v.get("en"), str) and isinstance(v.get("pt"), str) and v["pt"].strip():
                self.game.setdefault(v["en"].strip().lower(), (k, v["pt"].strip()))
        self.layers = layers or name_layers.Translator("pt", [])

    def loc(self, en):
        fixed = self.layers.fix(en)
        if fixed is not None:
            return {"en": en, "pt": fixed[0]}, self.layers.game_key(en)
        hit = self.game.get(en.strip().lower())
        if hit:
            return {"en": en, "pt": hit[1]}, hit[0]
        pt, tier, _ = self.layers.name(en)
        if tier == "official":
            return {"en": en, "pt": pt}, self.layers.game_key(en)
        if en in DIALOGUE:
            return {"en": en, "pt": DIALOGUE[en][0]}, DIALOGUE[en][1]
        if tier != "missing":
            return dict({"en": en, "pt": pt}, **({} if tier == "likely" else {"tr": tier})), self.layers.game_key(en)
        if en in MT:
            return {"en": en, "pt": MT[en], "tr": "machine"}, None
        return {"en": en, "pt": en, "tr": "missing"}, None

    def sprite_words(self, s, lang):
        i = 0 if lang == "pt" else 1
        s = re.sub(r'<sprite name="([^"]+)">', lambda m: " " + SPRITE_WORDS.get(m.group(1), ("", ""))[i], s)
        return re.sub(r"\s+", " ", s).replace(" .", ".").strip()


def money(s):
    """'1 silver 37 bronze' -> 137 (bronze); None when no amount is found."""
    parts = MONEY_RE.findall(s or "")
    return sum(int(n) * COIN[u] for n, u in parts) if parts else None


def sell_entry(b, key):
    """One wiki "Buys it" card -> [trader, lo, hi, likes, likesLevel, level] (trailing zeros trimmed).
    lo/hi: what it pays at its usual stock over the trader levels (0 = the wiki gives no number); a price that only
    holds at an empty usual stock ("pays only 1 bronze") counts only when it is the only one. likes: the most Likes a
    week (-1 = "earns Likes", no amount); likesLevel: the first trader level that gives them (0 = from level 1);
    level: the first trader level that buys it."""
    full, empty, likes, like_lv, lvl = [], [], 0, 0, 0
    for c in b.get("chips") or []:
        m = LEVEL_RE.match(c)
        if m:
            lvl = int(m.group(1))
            continue
        m = PAYS_RE.match(c)
        if m:
            v = money(m.group(1))
            if v is not None:
                (full if "at its usual stock" in c and "only" not in c else empty).append(v)
            continue
        m = LIKES_RE.match(c)
        if m:
            n, lv = int(m.group(2)), int(m.group(1) or m.group(3) or 1)
            likes = max(likes, n) if likes >= 0 else n
            like_lv = lv if not like_lv else min(like_lv, lv)
            continue
        m = LIKES_ANY_RE.match(c)
        if m:
            if not likes:
                likes = -1
            lv = int(m.group(1) or 1)
            like_lv = lv if not like_lv else min(like_lv, lv)
    pays = full or empty
    lo, hi = (min(pays), max(pays)) if pays else (0, 0)
    row = [key, lo, hi if hi != lo else 0, likes, like_lv if like_lv > 1 else 0, lvl if lvl > 1 else 0]
    while len(row) > 2 and row[-1] == 0:
        row.pop()
    if len(row) == 2 and row[1] == 0:
        row.pop()
    return row


def build(raw, items_en, texts, quests=None):
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

    # quests that ask for an item (probe-quests `needs`): item id -> [(story order, quest key, qty, giver key)]
    asked_q = {}
    qrows = (quests.get("rows") if isinstance(quests, dict) else quests) or []
    for qr in sorted(qrows, key=lambda r: r.get("key") or ""):
        Q = qr.get("data") or {}
        if not Q.get("name"):
            continue
        for n in Q.get("needs") or []:
            href = n.get("href") or ""
            iid = href.rsplit("/", 1)[-1]
            if not href.startswith("/items/") or iid not in known or (n.get("note") or "").startswith(QUEST_SKIP_NOTES):
                continue
            qty = int(n["qty"]) if str(n.get("qty") or "").isdigit() else 1
            giver = intern(Q["giver"]) if Q.get("giver") else ""
            order = Q.get("storyOrder") if isinstance(Q.get("storyOrder"), int) else 10 ** 6
            asked_q.setdefault(iid, []).append((order, intern(Q["name"]), qty, giver))

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
        # ---- sell: who buys it, base price, fixed price
        sell = []
        for b in D.get("boughtBy") or []:
            en = re.sub(r"\s*\([^)]*\)$", "", b.get("title") or "").strip()
            if not en:
                continue
            e = sell_entry(b, intern(en))
            prev = next((x for x in sell if x[0] == e[0]), None)
            if prev is None:
                sell.append(e)
            else:
                warnings.append(f"{iid}: trader {en!r} listed twice under boughtBy; first kept")
        if sell:
            rec["sell"] = sell
        pr = D.get("price")
        # the base price only matters to a seller: items nobody buys keep none (it would show nowhere)
        if sell and isinstance(pr, int) and not isinstance(pr, bool) and pr > 0:
            rec["price"] = pr
            if any(s.get("subtitle") == "Fixed price" for s in D.get("statStrip") or []):
                rec["fix"] = 1
        # ---- study: [red, green, blue, science, faith], trailing zeros trimmed
        sc = {s.get("subtitle"): s.get("title") for s in D.get("studyCards") or []}
        if sc:
            val = lambda k: int(m.group(1)) if (m := re.match(r"^\+?(\d+)$", str(sc.get(k) or ""))) else 0
            study = [val("Red tech points"), val("Green tech points"), val("Blue tech points"),
                     val("Science it costs"), val("Faith it costs")]
            while study and study[-1] == 0:
                study.pop()
            if study:
                rec["study"] = study
        # ---- asked: {q: quests (story order), t: town restorations, o: town orders}
        quest = [[q, n, g] if g else [q, n] for _, q, n, g in sorted(asked_q.get(iid, []))]
        town, order = [], []
        for u in D.get("usedIn") or []:
            kind = u.get("kind")
            qty = int(u["qty"]) if str(u.get("qty") or "").isdigit() else 1
            if kind == "Town" and u.get("title"):
                town.append([intern(u["title"]), qty])
            elif kind == "Order" and u.get("title"):
                m = ORDER_RE.match(u["title"])
                likes = next((int(x.group(1)) for c in u.get("chips") or [] for x in [ORDER_LIKES_RE.match(c)] if x), 0)
                e = [intern(m.group(1)), qty, int(m.group(2) or 0), likes]
                # the urgent and the normal order of one trader level: one line, the most Likes
                prev = next((a for a in order if a[:3] == e[:3]), None)
                if prev is not None:
                    prev[3] = max(prev[3], likes)
                    continue
                order.append(e)
        for e in order:
            while len(e) > 2 and e[-1] == 0:
                e.pop()
        asked = {k: v for k, v in (("q", quest), ("t", town), ("o", order)) if v}
        if asked:
            rec["asked"] = asked
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
        "sell": sum(1 for r in out.values() if "sell" in r),
        "sell_priced": sum(1 for r in out.values() if any(len(e) > 1 and e[1] for e in r.get("sell", []))),
        "sell_likes": sum(1 for r in out.values() if any(len(e) > 3 and e[3] for e in r.get("sell", []))),
        "price": sum(1 for r in out.values() if "price" in r),
        "study": sum(1 for r in out.values() if "study" in r),
        "study_faith": sum(1 for r in out.values() if len(r.get("study", [])) > 4),
        "asked_quest": sum(1 for r in out.values() if "q" in r.get("asked", {})),
        "asked_quest_lines": sum(len(r.get("asked", {}).get("q", [])) for r in out.values()),
        "quests": len({a[0] for r in out.values() for a in r.get("asked", {}).get("q", [])}),
        "asked_town": sum(1 for r in out.values() if "t" in r.get("asked", {})),
        "asked_order": sum(1 for r in out.values() if "o" in r.get("asked", {})),
        "asked": sum(1 for r in out.values() if "asked" in r),
        "names": len(names),
        "names_unofficial": sum(1 for n in names.values() if n.get("tr")),
        "buffs": len(buffs),
    }
    doc = {"meta": {"source": "data/raw/api-items-all.json (wikily.gg items dataset)"
                              + (" + data/raw/days/probe-quests.json (quests)" if qrows else ""),
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
        for e in r.get("sell", []):
            if e[0] not in doc["names"]:
                errors.append(f"{iid}: unknown trader {e[0]!r}")
            if not all(isinstance(x, int) for x in e[1:]):
                errors.append(f"{iid}: sell entry {e!r} is not [trader, ints...]")
        for k, rows in r.get("asked", {}).items():
            for a in rows:
                refs = a[:1] + (a[2:3] if k == "q" else [])
                if k not in ("q", "t", "o") or len(a) < 2 or not isinstance(a[1], int) \
                        or any(x not in doc["names"] for x in refs):
                    errors.append(f"{iid}: bad asked.{k} entry {a!r}")
        st = r.get("study")
        if st is not None and not (isinstance(st, list) and 0 < len(st) <= 5 and all(isinstance(x, int) and x >= 0 for x in st)):
            errors.append(f"{iid}: bad study {st!r}")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build data/facts.json from the wikily item dump")
    ap.add_argument("--raw", default=str(DATA / "raw" / "api-items-all.json"))
    ap.add_argument("--items", default=str(DATA / "items.en.json"), help="ids that exist (read-only)")
    ap.add_argument("--game-text", default=str(DATA / "game-texts" / "gk2_textos.json"))
    ap.add_argument("--names", nargs="+", default=[str(p) for p in name_layers.default_pt(DATA)],
                    help="pt names layers, best first (default: the three data/names.*.pt-BR.json)")
    ap.add_argument("--quests", default=str(DATA / "raw" / "days" / "probe-quests.json"),
                    help="wiki quest dataset (needs + giver), for items[].asked; '' to skip")
    ap.add_argument("--out", default=str(DATA / "facts.json"))
    ap.add_argument("--check", action="store_true", help="build and validate, write nothing")
    args = ap.parse_args(argv)
    try:
        raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
        items_en = json.loads(Path(args.items).read_text(encoding="utf-8"))
        game = json.loads(Path(args.game_text).read_text(encoding="utf-8")) if args.game_text else {}
        quests = json.loads(Path(args.quests).read_text(encoding="utf-8")) if args.quests else None
    except (OSError, ValueError) as e:
        print(f"build_facts: cannot read inputs: {e}", file=sys.stderr)
        return 2
    doc, warnings = build(raw, items_en, Texts(game, name_layers.load(args.names)), quests)
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
