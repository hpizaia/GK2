"""Build data/recipes.en.json and data/items.en.json from the cached wikily.gg API responses.

Inputs (all in data/raw/, produced by scripts/fetch_dataset.py and the calculator page dump):
  api-recipes-all.json, api-items-all.json, api-buildings-all.json,
  api-crafting-stations-all.json, api-technologies-all.json,
  api-alchemy-formulas-all.json, calculator-props.json
Usage: python3 -I scripts/build_dataset.py <project_dir>
"""
import json, os, re, sys, collections

ROOT = sys.argv[1]
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data")
SITE = "https://wikily.gg"
WIKI = SITE + "/graveyard-keeper-2"


def load_rows(slug):
    return {r["key"]: r["data"] for r in json.load(open(os.path.join(RAW, f"api-{slug}-all.json")))["rows"]}


ITEMS = load_rows("items")
RECIPES = load_rows("recipes")
BUILDINGS = load_rows("buildings")
STATIONS = load_rows("crafting-stations")
TECHS = load_rows("technologies")
ALCH = load_rows("alchemy-formulas")
CALC = json.load(open(os.path.join(RAW, "calculator-props.json")))


def slugify(s):
    s = s.lower().replace("'", "-").replace("’", "-")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def to_int(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.fullmatch(r"\s*\+?(\d+)\s*", str(v))
    return int(m.group(1)) if m else None


def parse_tp(text):
    """'1 red, 2 blue' -> {'red':1,'blue':2}; '-' -> None"""
    if not text or text.strip() in ("-", ""):
        return None
    out = {}
    for part in text.split(","):
        m = re.fullmatch(r"\s*(\d+)\s+(red|green|blue)\s*", part)
        if m:
            out[m.group(2)] = int(m.group(1))
    return out or None


def href_slug(href):
    return href.rstrip("/").rsplit("/", 1)[-1] if href else None


# ---------------------------------------------------------------- items registry
items = {}  # id -> record


def add_item(iid, **kw):
    rec = items.get(iid)
    if rec is None:
        rec = {"id": iid, "name": None, "kind": None, "category": None, "icon": None,
               "is_raw": None, "obtain": None, "sources": [], "page_url": None, "listed": True}
        items[iid] = rec
    for k, v in kw.items():
        if v in (None, "", []):
            continue
        if rec.get(k) in (None, "", []):
            rec[k] = v
    return rec


USE_PREFIXES = ("It goes into", "It is used", "It is an ingredient", "It is the ingredient")


def obtain_text(summary):
    if not summary:
        return None
    sents = re.split(r"(?<=[.!?])\s+", summary.strip())
    keep = [s for s in sents if not s.startswith(USE_PREFIXES) and not re.match(r"^\d+ quests? takes?", s)
            and not s.startswith("Each hire")]
    txt = " ".join(keep).strip()
    if len(txt) > 320:
        txt = txt[:317].rsplit(" ", 1)[0] + "..."
    return txt or None


def runes_of(d):
    out = {}
    for c in d.get("runeCards") or []:
        m = re.match(r"(Red|Green|Blue) rune", c.get("subtitle", ""))
        n = to_int(c.get("title"))
        if m and n is not None:
            out[m.group(1).lower()] = n
    return out or None


for k, d in ITEMS.items():
    add_item(k, name=d["name"], kind="item", category=d.get("category") or d.get("eyebrow"),
             icon=d.get("icon"), obtain=obtain_text(d.get("summary")), sources=d.get("sources") or [],
             page_url=f"{WIKI}/items/{k}")
    items[k]["listed"] = d.get("listed") == "yes"
    if "is not obtainable" in (d.get("summary") or ""):
        items[k]["unobtainable"] = True  # wiki states no source exists in the current game version
    r = runes_of(d)
    if r:
        items[k]["alchemy_runes"] = r

for k, d in BUILDINGS.items():
    kind = "station" if d.get("category") == "Crafting station" else "building"
    rec = add_item(k, name=d["name"], category="Building: " + (d.get("category") or "?"),
                   icon=d.get("icon") or d.get("cardImage"), page_url=f"{WIKI}/{d['page']}" if d.get("page") else None,
                   obtain=d.get("lead"))
    if rec["kind"] in (None, "item"):
        # building slugs that are also item pages (e.g. beds, lanterns) keep kind "item" but get building info
        rec["kind"] = kind if rec["kind"] is None else rec["kind"]
    rec.setdefault("building", {})
    rec["building"] = {"category": d.get("category"), "zones": [z.strip() for z in (d.get("zones") or "").split(",") if z.strip() and z.strip() != "-"],
                       "listed": d.get("listed") == "yes"}
    if k not in ITEMS:
        rec["listed"] = d.get("listed") == "yes"

for k, d in STATIONS.items():
    rec = add_item(k, name=d["name"], kind="station", category="Building: Crafting station",
                   icon=d.get("icon") or d.get("cardImage"), page_url=f"{WIKI}/crafting-stations/{k}", obtain=d.get("lead"))

# lookup by display name (case-insensitive) for text-only references
name_to_id = {}
for iid, rec in items.items():
    if rec["name"]:
        name_to_id.setdefault(rec["name"].lower(), iid)


def ensure_virtual(name, icon=None, hint_kind=None):
    """Ingredient/output referenced by display name only (no wiki item page)."""
    if name.lower() in name_to_id:
        return name_to_id[name.lower()]
    iid = slugify(name)
    if iid in items and items[iid]["name"] and items[iid]["name"].lower() != name.lower():
        iid = "v-" + iid
    kind = hint_kind
    if kind is None:
        if name.startswith("Any ") or " or " in name:
            kind = "group"
        elif re.search(r"\((bronze|silver|gold)\)$", name):
            kind = "quality-variant"
        else:
            kind = "virtual"
    add_item(iid, name=name, kind=kind, icon=icon, category="(no wiki item page)")
    name_to_id[name.lower()] = iid
    return iid


def ref_item(key, name, icon=None):
    """Resolve a recipe input/output reference to an item id."""
    if key in items:
        return key
    if key and re.fullmatch(r"[a-z0-9-]+", key) and key.endswith("-bed"):
        # planted crop beds: output of the 'Plant X' star crafts
        add_item(key, name=name if name and name != key else key.replace("-", " ").title(), kind="planted-bed",
                 icon=icon, category="Farming: planted bed")
        name_to_id.setdefault(items[key]["name"].lower(), key)
        return key
    return ensure_virtual(name or key, icon)


# ---------------------------------------------------------------- quality grades (bronze / silver / gold)
# The wiki names a graded reference "Wine (silver)" but points it to the plain item page (key "wine"): ref_item()
# alone would drop the grade, and the Barrel's three recipes would all make the same Wine. graded_ref() keeps it:
#   "<X> (bronze)" -> the plain item <x> (the common item IS the bronze one: saved plans keep "wine", "cabbage");
#   "<X> (silver|gold)" -> "<x>-silver|gold", a quality-variant item (base_item <x>, the base's icon and category).
# Families without a wiki item page (Grape Juice, Story, Newspaper, Salad, Sauerkraut) already resolve by name
# to their own "<x>-<grade>" items. Recipes listed in NO_GRADE stay as before: organ improvers make "(gold)" from
# "Any <organ>" (both levels), which is not a bronze -> silver -> gold ladder.
GRADE_RX = re.compile(r"^(.*\S)\s*\((bronze|silver|gold)\)$", re.I)
NO_GRADE = ("improve-organ-",)
variant_of = {}     # variant id -> (base id, grade)


def graded_ref(key, name, icon=None):
    m = GRADE_RX.match(name or "")
    if not (m and key in items and items[key]["kind"] == "item"):
        return ref_item(key, name, icon)
    grade = m.group(2).lower()
    if grade == "bronze":
        return key
    base = items[key]
    vid = f"{key}-{grade}"
    if vid not in items:
        add_item(vid, name=f"{base['name']} ({grade})", kind="quality-variant", icon=base["icon"] or icon,
                 category=base["category"])
        items[vid]["listed"] = base["listed"]
        items[vid]["base_item"] = key
        name_to_id.setdefault(items[vid]["name"].lower(), vid)
    variant_of[vid] = (key, grade)
    return vid


def station_ref(name):
    if not name:
        return None
    for k, d in STATIONS.items():
        if d["name"] == name:
            return k
    return name_to_id.get(name.lower())


tech_by_name = {d["name"]: k for k, d in TECHS.items()}


def unlock_ref(text, requirement=None):
    if not text or text.strip() == "-":
        return None
    out = {"name": text, "type": None, "id": None, "url": None}
    href = (requirement or {}).get("href")
    if href:
        parts = href.strip("/").split("/")
        out["type"] = {"technologies": "technology", "quests": "quest", "perks": "perk"}.get(parts[0], parts[0])
        out["id"] = parts[-1]
        out["url"] = WIKI + href
    elif text in tech_by_name:
        out.update(type="technology", id=tech_by_name[text], url=f"{WIKI}/technologies/{tech_by_name[text]}")
    return out


KIND_MAP = {"Hand craft": "hand_craft", "Auto": "auto", "Factory": "factory", "Star craft": "star_craft"}

recipes = []

# ---------------------------------------------------------------- 1. regular recipes (recipes dataset)
for key, d in RECIPES.items():
    card = d.get("card") or {}
    card_inputs = card.get("inputs") or []
    card_outputs = card.get("outputs") or []
    ref = ref_item if key.startswith(NO_GRADE) else graded_ref
    inputs = []
    for idx, i in enumerate(d["inputs"]):
        iid = ref(i["key"], i["name"], i.get("icon"))
        ent = {"item": iid, "qty": i["qty"]}
        note = card_inputs[idx].get("note") if idx < len(card_inputs) else None
        if note:
            ent["note"] = note
        inputs.append(ent)
    # outputs: data outputs carry keys/qty, card outputs carry the perk/chance notes (same order)
    outs = []
    for idx, o in enumerate(d["outputs"]):
        iid = ref(o["key"], o["name"], o.get("icon"))
        ent = {"item": iid, "qty": o["qty"]}
        note = card_outputs[idx].get("note") if idx < len(card_outputs) else None
        if note:
            ent["note"] = note
        outs.append(ent)
    if outs:
        output = {"item": outs[0]["item"], "qty": outs[0]["qty"]}
        extra = outs[1:]
    else:
        # effect / repair / unlock actions with no item output (PR machine buffs, repairs, door opening)
        iid = ref_item(None, d["name"], d.get("icon"))
        items[iid]["kind"] = "action"
        items[iid]["category"] = "(action / effect, not an item)"
        output = {"item": iid, "qty": 1}
        extra = []
    meta = {m["label"]: m["value"] for m in card.get("meta") or []}
    star = None
    if "Silver at" in meta or "Gold at" in meta:
        star = {"silver_at": meta.get("Silver at"), "gold_at": meta.get("Gold at")}
    st_names = d.get("stations") or ([d["station"]] if d.get("station") else [])
    recipes.append({
        "id": key,
        "name": d["name"],
        "type": KIND_MAP.get(d["kind"], d["kind"]),
        "output": output,
        "extra_outputs": extra,
        "made_text": d.get("made") or None,
        "station": d.get("station") or None,
        "station_id": station_ref(d.get("station")),
        "alt_stations": [s for s in st_names if s != d.get("station")],
        "station_extension": d.get("extension") or None,
        "inputs": inputs,
        "unlock": unlock_ref(d.get("unlock"), card.get("requirement")),
        "mastery": {"type": d.get("mastery"), "level": d.get("masteryLevel")} if d.get("mastery") else None,
        "time_ticks": to_int(d.get("ticks")),
        "energy_per_tick": to_int(d.get("energy")),
        "tech_points_reward": parse_tp(d.get("techPoints")),
        "star_quality": star,
        "note": card.get("note") or None,
        "listed": d.get("listed") == "yes",
        "calculator_default": False,
        "source_url": f"{WIKI}/{d['link']}" if d.get("link") else f"{WIKI}/recipes",
    })

# ---------------------------------------------------------------- 2. building / construction recipes
def parse_cost_text(text):
    out = []
    for part in [p.strip() for p in (text or "").split(",") if p.strip()]:
        m = re.fullmatch(r"(\d+)\s+(.+)", part)
        if not m:
            return None
        nm = m.group(2).strip()
        iid = name_to_id.get(nm.lower())
        if not iid:
            return None
        out.append({"item": iid, "qty": int(m.group(1))})
    return out


def techs_from_chips(chips):
    for c in chips or []:
        if c.startswith("Tech: "):
            return c[len("Tech: "):]
    return None


build_unresolved = []
used_build_ids = set()
for key, d in BUILDINGS.items():
    variants = d.get("variants") or []
    base_inputs = None
    if d.get("costCalc"):
        base_inputs = [{"item": ref_item(c["key"], c["name"]), "qty": int(c["qty"])} for c in d["costCalc"]]
    elif d.get("cost"):
        base_inputs = []
        for c in d["cost"]:
            iid = href_slug(c.get("href")) if c.get("href") else None
            if iid not in items:
                iid = ref_item(iid, c.get("title"), c.get("icon"))
            base_inputs.append({"item": iid, "qty": to_int(c.get("qty"))})
    else:
        base_inputs = parse_cost_text(d.get("costText")) or []
    vlist = variants or [{"title": d.get("zone") or None, "subtitle": d.get("costText"), "chips": []}]
    unlock_names = {u["title"]: u for u in d.get("unlock") or []}
    for vi, v in enumerate(vlist):
        if vi == 0:
            inputs = base_inputs
        else:
            inputs = parse_cost_text(v.get("subtitle"))
            if inputs is None:
                build_unresolved.append((key, v.get("title"), v.get("subtitle")))
                continue
        tname = techs_from_chips(v.get("chips"))
        unlock = None
        if tname:
            u = unlock_names.get(tname)
            unlock = {"name": tname, "type": "technology", "id": href_slug(u["href"]) if u else tech_by_name.get(tname),
                      "url": WIKI + u["href"] if u else (f"{WIKI}/technologies/{tech_by_name[tname]}" if tname in tech_by_name else None)}
        elif vi == 0 and d.get("unlock"):
            u = d["unlock"][0]
            unlock = {"name": u["title"], "type": "technology", "id": href_slug(u["href"]), "url": WIKI + u["href"]}
        zone = v.get("title")
        rid = "build-" + key + ("" if vi == 0 else "--" + slugify(zone or str(vi)))
        n = 2
        base_rid = rid
        while rid in used_build_ids:
            rid = f"{base_rid}-{n}"
            n += 1
        used_build_ids.add(rid)
        recipes.append({
            "id": rid,
            "name": f"Build {d['name']}" + (f" ({zone})" if zone and len(vlist) > 1 else ""),
            "type": "building",
            "output": {"item": key, "qty": 1},
            "extra_outputs": [],
            "made_text": None,
            "station": None,
            "station_id": None,
            "alt_stations": [],
            "station_extension": None,
            "zone": zone,
            "inputs": inputs,
            "unlock": unlock,
            "mastery": None,
            "time_ticks": None,
            "energy_per_tick": None,
            "tech_points_reward": None,
            "star_quality": None,
            "note": "; ".join(c for c in (v.get("chips") or []) if not c.startswith("Tech: ")) or None,
            "listed": d.get("listed") == "yes",
            "calculator_default": False,
            "source_url": f"{WIKI}/{d['page']}" if d.get("page") else f"{WIKI}/buildings",
        })

# ---------------------------------------------------------------- 3. alchemy formulas (rune based)
FLASK = "alchemy-flasks" if "alchemy-flasks" in items else None
alch_unresolved = []
for key, d in ALCH.items():
    out_id = None
    for c in d.get("itemCards") or []:
        if c.get("href", "").startswith("/items/"):
            out_id = href_slug(c["href"])
            break
    if out_id is None or out_id not in items:
        out_id = ref_item(out_id, d["name"], d.get("icon"))
    combos = []
    for c in (d.get("best2Cards") or []) + (d.get("best3Cards") or []):
        names = [n.strip() for n in c["title"].split(" + ")]
        cnt = collections.Counter()
        ok = True
        for n in names:
            iid = name_to_id.get(n.lower())
            if not iid and n.startswith("Alchemic Powder (") and "alchemic-powder" in items:
                iid = "alchemic-powder"  # rune-specific powder grades share one wiki item page
            if not iid:
                ok = False
                alch_unresolved.append((key, n))
                break
            cnt[(iid, n if iid == "alchemic-powder" else None)] += 1
        if ok:
            combo = []
            for (i, variant), q in cnt.items():
                ent = {"item": i, "qty": q}
                if variant:
                    ent["note"] = variant
                combo.append(ent)
            combos.append(combo)
    flask = [{"item": FLASK, "qty": 1, "note": "every brew uses 1 Alchemy Flasks"}] if FLASK else []
    runes = {"red": d.get("red", 0), "green": d.get("green", 0), "blue": d.get("blue", 0)}
    recipes.append({
        "id": "alchemy-" + key,
        "name": f"{d['name']} (alchemy formula)",
        "type": "alchemy",
        "output": {"item": out_id, "qty": 1},
        "extra_outputs": [],
        "made_text": None,
        "station": d.get("minLab"),
        "station_id": station_ref(d.get("minLab")),
        "alt_stations": ["Laboratory II"] if d.get("minLab") == "Laboratory I" else [],
        "station_extension": None,
        "inputs": (combos[0] if combos else []) + flask,
        "inputs_are_example": True,
        "rune_requirement": runes,
        "example_input_combos": combos,
        "mix_count": d.get("mixCount"),
        "unlock": unlock_ref(d.get("unlockText"), {"href": (d.get("unlockCards") or [{}])[0].get("href")} if d.get("unlockCards") else None),
        "mastery": None,
        "time_ticks": None,
        "energy_per_tick": None,
        "tech_points_reward": None,
        "star_quality": None,
        "note": d.get("summary"),
        "listed": d.get("listed") == "yes",
        "calculator_default": False,
        "source_url": f"{WIKI}/{d['page']}",
    })

# ---------------------------------------------------------------- 4. grow recipes (crop beds), deduplicated
seen_grow = set()
for ik, d in ITEMS.items():
    for g in d.get("growRecipes") or []:
        meta = {m["label"]: m["value"] for m in g.get("meta") or []}
        mastery_lvl = to_int(meta.get("Farming mastery"))
        sig = (g["title"], mastery_lvl)
        if sig in seen_grow:
            continue
        seen_grow.add(sig)
        # the bed of a bronze seed gives bronze + silver, of a silver seed silver + gold, of a gold seed gold: the
        # wiki names each line "Cabbage (Silver)" on the plain page, so the grade is kept as for recipes
        ins = [{"item": graded_ref(href_slug(i["href"]), i.get("name")), "qty": to_int(i.get("count"))} for i in g["inputs"]]
        outs = []
        for o in g["outputs"]:
            ent = {"item": graded_ref(href_slug(o["href"]), o.get("name")), "qty": to_int(o.get("count"))}
            if o.get("note"):
                ent["note"] = o["note"]
            outs.append(ent)
        bed = g["title"].replace("Grown in a ", "").replace("Grown in an ", "")
        primary = outs[0]
        recipes.append({
            "id": f"grow-{slugify(bed)}-m{mastery_lvl}",
            "name": f"{g['title']} (Farming mastery {mastery_lvl})",
            "type": "grow",
            "output": {"item": primary["item"], "qty": primary["qty"]},
            "output_note": primary.get("note"),
            "extra_outputs": outs[1:],
            "made_text": None,
            "station": bed,
            "station_id": slugify(bed) if slugify(bed) in items else None,
            "alt_stations": [],
            "station_extension": None,
            "inputs": ins,
            "unlock": None,
            "mastery": {"type": "Farming", "level": mastery_lvl},
            "time_ticks": to_int(meta.get("Ticks")),
            "energy_per_tick": None,
            "tech_points_reward": None,
            "star_quality": None,
            "note": g.get("note"),
            "listed": True,
            "calculator_default": False,
            "source_url": f"{WIKI}/items/{variant_of.get(primary['item'], (primary['item'],))[0]}",
        })

# ---------------------------------------------------------------- 5. star crafts of a graded family
# Story, Newspaper ("Printing Press"), Vegetable salad and Bowl of sauerkraut are star crafts: the grade of the result
# depends on the successful ticks (star_quality: silver at N, gold at M). The wiki's recipe makes the plain item
# ("Story", hidden; the prayers ask for it), so nothing made the bronze one and the silver / gold ones only came
# from the improvement recipes. Each grade gets a copy of the star craft, id "<recipe>-<grade>", output
# "<x>-<grade>"; the original recipe stays as it was. Same inputs, yield, station, thresholds: no new numbers.
star_clones = []
for r in list(recipes):
    out = r["output"]["item"]
    if r["type"] != "star_craft" or not r["star_quality"] or out.endswith(("-bronze", "-silver", "-gold")):
        continue
    grades = [g for g in ("bronze", "silver", "gold")
              if items.get(f"{out}-{g}", {}).get("kind") == "quality-variant"]
    if len(grades) != 3:
        continue
    for g in grades:
        c = json.loads(json.dumps(r))
        c["id"] = f"{r['id']}-{g}"
        c["output"] = {"item": f"{out}-{g}", "qty": r["output"]["qty"]}
        c["star_grade"] = g
        c["calculator_default"] = False
        star_clones.append(c)
recipes.extend(star_clones)

# ---------------------------------------------------------------- quality upgrades
# A recipe whose output is a grade of a family and which takes a lower grade of the same family ("Drink enhancement
# I": Wine (bronze) + Spices -> Wine (silver); "Improve story I": 2 Story (bronze) -> 1 Story (silver)) is an upgrade:
# build.py lists it after the recipes that make that grade directly (the Barrel with silver Grape Juice, the silver
# star craft), so the planner's default is the direct one and the upgrade an alternative.
GRADE_RANK = {"bronze": 0, "silver": 1, "gold": 2}


def grade_of(iid):
    if iid in variant_of:
        return variant_of[iid]
    rec = items.get(iid) or {}
    m = GRADE_RX.match(rec.get("name") or "")
    if rec.get("kind") == "quality-variant" and m:
        base = rec.get("base_item") or name_to_id.get(m.group(1).lower()) or m.group(1).lower()
        return base, m.group(2).lower()
    return iid, None   # a plain item of a family is its bronze grade (graded_ref)


for r in recipes:
    fam, g = grade_of(r["output"]["item"])
    if g in ("silver", "gold"):
        for i in r["inputs"]:
            f2, g2 = grade_of(i["item"])
            if f2 == fam and GRADE_RANK.get(g2 or "bronze") < GRADE_RANK[g]:
                r["quality_upgrade"] = True

# ---------------------------------------------------------------- calculator default flags
by_output = collections.defaultdict(list)
for r in recipes:
    by_output[r["output"]["item"]].append(r)
calc_unmatched = []
for cid, g in CALC["graph"].items():
    iid = cid[2:] if cid.startswith("x:") else cid
    if iid not in items:
        iid = name_to_id.get((CALC["meta"].get(cid) or {}).get("name", "").lower(), iid)
    want = sorted(((i["id"][2:] if i["id"].startswith("x:") else i["id"]), i["qty"]) for i in g["inputs"])
    cands = by_output.get(iid, [])
    match = None
    for r in cands:
        have = sorted((i["item"], i["qty"]) for i in r["inputs"] if not r.get("inputs_are_example"))
        st_ok = (g["station"] or None) == r["station"] or (not g["station"] and r["type"] == "building")
        if have == want and st_ok:
            match = r
            break
    if match is None:
        for r in cands:  # fallback: inputs equal by resolved names, ignore station
            have = sorted((i["item"], i["qty"]) for i in r["inputs"])
            if have == want:
                match = r
                break
    if match:
        match["calculator_default"] = True
    else:
        calc_unmatched.append((cid, g))

# ---------------------------------------------------------------- items: raw flags, group members
for r in recipes:
    for ref in [r["output"]] + r["extra_outputs"] + r["inputs"]:
        assert ref["item"] in items, ref

# crops and seeds of the crop beds (their grades come from the seed): obtain texts of their silver / gold variants
crops = {variant_of.get(r["output"]["item"], (r["output"]["item"],))[0] for r in recipes if r["type"] == "grow"}
seeds = {variant_of.get(i["item"], (i["item"],))[0] for r in recipes if r["type"] == "grow" for i in r["inputs"]}
VARIANT_OBTAIN = {
    ("crop", "silver"): "Harvest: bronze or silver seeds.",
    ("crop", "gold"): "Harvest: silver or gold seeds.",
    ("seed", "silver"): "Harvest by-product: bronze or silver seeds.",
    ("seed", "gold"): "Harvest by-product: silver or gold seeds.",
    ("made", "silver"): "Made from ingredients of the same grade, or improved from the grade below.",
    ("made", "gold"): "Made from ingredients of the same grade, or improved from the grade below.",
}

producers = collections.defaultdict(set)
for r in recipes:
    producers[r["output"]["item"]].add(r["type"])
    for e in r["extra_outputs"]:
        producers[e["item"]].add(r["type"] + ":byproduct")

for iid, rec in items.items():
    types = producers.get(iid, set())
    # raw = nothing in the dataset crafts it from other items as its main output
    # (grow recipes and zero-input production stations do not count; crops/logs/ore stay raw)
    crafted = any(r["output"]["item"] == iid and r["type"] != "grow" and r["inputs"] for r in by_output.get(iid, []))
    rec["is_raw"] = not crafted
    rec["recipe_ids"] = [r["id"] for r in by_output.get(iid, [])]
    if rec["kind"] == "group":
        nm = rec["name"]
        members = []
        if nm.startswith("Any "):
            base = nm[4:].lower()
            members = [i for i, x in items.items() if x["name"] and x["kind"] != "group" and
                       (x["name"].lower() == base or x["name"].lower().startswith(base + " ("))]
        else:
            m = re.fullmatch(r"(.+?) \((\w+) or (\w+)\)", nm)
            if m:
                members = [name_to_id.get(f"{m.group(1)} ({q})".lower()) for q in (m.group(2), m.group(3))]
            else:
                members = [name_to_id.get(p.strip().lower()) for p in nm.split(" or ")]
        rec["group_members"] = [x for x in members if x]
        rec["obtain"] = rec["obtain"] or "Wildcard ingredient: any one of the listed group members."
    if rec["kind"] == "quality-variant" and iid in variant_of:
        # a grade kept by graded_ref(): how to get it, short and honest (the
        # grade of a crop comes from the seed; a bronze seed gives bronze + silver, silver gives silver + gold, gold gold)
        base, grade = variant_of[iid]
        rec["base_item"] = base
        if base in crops:
            rec["obtain"] = VARIANT_OBTAIN["crop", grade]
        elif base in seeds:
            rec["obtain"] = VARIANT_OBTAIN["seed", grade]
        else:
            rec["obtain"] = VARIANT_OBTAIN["made", grade]
    elif rec["kind"] == "quality-variant":
        base = re.sub(r"\s*\((bronze|silver|gold)\)$", "", rec["name"])
        rec["base_item"] = name_to_id.get(base.lower())
        rec["obtain"] = rec["obtain"] or "Quality grade of the base item (star craft result or enhancement recipe)."
    if not rec["obtain"] and rec["is_raw"] and rec["kind"] == "item":
        rec["obtain"] = None

items_out = sorted(items.values(), key=lambda x: x["id"])
recipes_out = sorted(recipes, key=lambda x: x["id"])

json.dump(items_out, open(os.path.join(OUT, "items.en.json"), "w"), ensure_ascii=False, indent=1)
json.dump(recipes_out, open(os.path.join(OUT, "recipes.en.json"), "w"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- report
ids = {i["id"] for i in items_out}
dangling = [(r["id"], ref["item"]) for r in recipes_out for ref in [r["output"]] + r["extra_outputs"] + r["inputs"] if ref["item"] not in ids]
print("items", len(items_out), collections.Counter(i["kind"] for i in items_out))
print("recipes", len(recipes_out), collections.Counter(r["type"] for r in recipes_out))
print("items with recipes", sum(1 for i in items_out if i["recipe_ids"]), "raw", sum(1 for i in items_out if i["is_raw"]))
print("calculator_default", sum(r["calculator_default"] for r in recipes_out), "of graph", len(CALC["graph"]), "unmatched", len(calc_unmatched))
for u in calc_unmatched[:20]:
    print("  unmatched calc", u)
print("dangling", dangling)
print("build variants unresolved", build_unresolved)
print("alchemy names unresolved", sorted(set(alch_unresolved)))
print("ids with duplicate recipe id", [k for k, n in collections.Counter(r["id"] for r in recipes_out).items() if n > 1])
