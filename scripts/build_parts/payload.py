"""The JSON embedded in the page (page_payload) and the project files it carries: sprite, techs, days, facts."""
import json
from pathlib import Path

from build_parts.common import GAME_TEXT_VERSION, _die


# --------------------------------------------------------------------------- page payload

def collapse_loc(v, langs):
    """{pt: s, en: s} (exactly the localized fields, all equal) -> s. Recursive; other dicts untouched.
    The page's GK.data normalizes both forms back to {pt, en}."""
    if isinstance(v, list):
        return [collapse_loc(x, langs) for x in v]
    if isinstance(v, dict):
        if set(v) == langs and all(isinstance(x, str) for x in v.values()) and len(set(v.values())) == 1:
            return next(iter(v.values()))
        return {k: collapse_loc(x, langs) for k, x in v.items()}
    return v


def load_sprite(path):
    """Sprite manifest {image: data URI, size, cols, icons: {id: [col, row]}} or SystemExit(2)."""
    try:
        sp = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(_die(f"--sprite: cannot read {path}: {e}"))
    if not (isinstance(sp, dict) and isinstance(sp.get("image"), str) and sp["image"].startswith("data:image/")
            and isinstance(sp.get("icons"), dict) and isinstance(sp.get("size"), int)):
        raise SystemExit(_die(f"--sprite: {path} is not a sprite manifest "
                              "({image: data:image/..., size, cols, icons: {id: [col, row]}})"))
    return {"image": sp["image"], "size": sp["size"], "cols": sp.get("cols"),
            "rows": sp.get("rows"), "icons": sp["icons"]}


# sprite ids outside items/stations that the page draws (data/techs.json: tech icons, point colours, branches;
# data/days.json: weekday glyphs, "day:<id>" or the day's own `sprite` id)
SPRITE_NS = {"tech", "tp", "branch", "day"}


def load_techs(path):
    """data/techs.json {meta, branches, techs} or SystemExit(2)."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(_die(f"--techs: cannot read {path}: {e}"))
    if not (isinstance(doc, dict) and isinstance(doc.get("techs"), dict) and isinstance(doc.get("branches"), dict)):
        raise SystemExit(_die(f"--techs: {path} is not a techs file ({{meta, branches, techs}}, see data/README-techs.md)"))
    return doc


def load_days(path):
    """data/days.json {meta, days: [{id, order, sin, name, events, ...}]} (scripts/build_days.py, see
    data/README-days.md) or SystemExit(2)."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(_die(f"--days: cannot read {path}: {e}"))
    days = doc.get("days") if isinstance(doc, dict) else None
    if not (isinstance(days, list) and days and all(isinstance(d, dict) and isinstance(d.get("id"), str) and d["id"]
                                                   for d in days)):
        raise SystemExit(_die(f"--days: {path} is not a days file ({{meta, days: [{{id, ...}}]}}, see data/README-days.md)"))
    ids = [d["id"] for d in days]
    if len(set(ids)) != len(ids):
        raise SystemExit(_die(f"--days: {path} has duplicate day ids"))
    return doc


def apply_facts(ds, path):
    """data/facts.json (scripts/build_facts.py, see data/README-data.md#facts): items[].where / .use / .stack (ficha do item:
    also .sell / .price / .fix / .study / .asked, the item card's "Quem compra", "Estudar" and "Pedido em") and
    the name tables in meta.refs ({names, buffs}, game keys dropped). Unknown item ids are skipped. Returns the
    number of items that got facts; a missing or malformed file changes nothing."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        facts, names, buffs = doc["items"], doc["names"], doc["buffs"]
    except (OSError, ValueError, KeyError, TypeError):
        return 0
    n = 0
    for iid, rec in facts.items():
        if iid in ds["items"] and isinstance(rec, dict):
            ds["items"][iid].update({k: rec[k] for k in ("where", "use", "stack", "sell", "price", "fix", "study", "asked")
                                     if k in rec})
            n += 1
    strip = lambda t: {k: {f: v for f, v in e.items() if f != "key"} for k, e in t.items()}
    ds["meta"]["refs"] = {"names": strip(names), "buffs": strip(buffs)}
    return n


def _drop_nulls(v):
    if isinstance(v, dict):
        return {k: _drop_nulls(x) for k, x in v.items() if x is not None and x != []}
    if isinstance(v, list):
        return [_drop_nulls(x) for x in v]
    return v


# fields of data/days.json the page never reads (every game text showing the day glyph: about 20% of the minified file)
DAYS_DROP = {"mentions"}


def days_payload(doc):
    """Page copy of data/days.json: {meta, days}. Days in `order` (then file order); every other field is kept as is,
    minus DAYS_DROP, null values and empty lists (the page reads a missing field as null / [])."""
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    days = sorted(enumerate(doc["days"]), key=lambda p: (p[1].get("order") if num(p[1].get("order")) else 1e9, p[0]))
    return _drop_nulls({"meta": meta, "days": [{k: v for k, v in d.items() if k not in DAYS_DROP} for _, d in days]})


def day_sprite_ids(doc):
    """Sprite ids the Dias screen may draw: "day:<id>" and each day's own `sprite` value."""
    out = set()
    for d in (doc or {}).get("days") or []:
        out.add("day:" + d["id"])
        if isinstance(d.get("sprite"), str) and d["sprite"]:
            out.add(d["sprite"])
    return out


def apply_tech_names(ds, techs):
    """Recipe `tech` names of type technology follow data/techs.json (official game names; e.g. the recipes said
    "Tecido (Construção)" where the tree says "Tecido (Engenharia)"). Only localized fields present in both are
    replaced. Returns the number of recipes changed."""
    recs = techs.get("techs") or {}
    langs = ds["meta"]["langs"]
    n = 0
    for r in ds["recipes"]:
        t = r.get("tech")
        if not t or t.get("type") != "technology" or t.get("id") not in recs:
            continue
        rec, changed = recs[t["id"]], False
        for l in langs:
            v = rec.get(l)
            if isinstance(v, str) and v.strip() and t.get(l) != v:
                t[l] = v
                changed = True
        n += changed
    return n


def techs_payload(doc, ds):
    """Compact page copy of data/techs.json: {tp, branches, techs}. Dropped: meta (except tp), icons (URLs: the
    sprite has them), id (the key), x (= column - 1), children and recipes (the page derives them from parents and
    recipes[].tech.id), listed. Defaults are omitted: tr "official", hidden/given false, rep/notes null, parents [],
    unlock station null; an unlock whose pt/en equal its item's (or station's) names keeps only item + kind.
    Equal {pt, en} texts inside (notes, rep.who, unlock names, branches, tp) collapse to one string, as in the rest
    of the payload; a tech's own pt/en stay explicit."""
    langs = set(ds["meta"]["langs"])
    loc = lambda v: collapse_loc(v, langs)
    ents = dict(ds.get("stations") or {}, **(ds.get("items") or {}))
    tp = {}
    for k, v in ((doc.get("meta") or {}).get("tp") or {}).items():
        tp[k] = {"pt": v.get("pt"), "en": v.get("en"), "color": v.get("color"), "icon": v.get("icon")}
    branches = {}
    for k, v in sorted((doc.get("branches") or {}).items(), key=lambda kv: kv[1].get("order", 0)):
        b = {"pt": v.get("pt"), "en": v.get("en"), "order": v.get("order", 0), "icon": v.get("icon")}
        if v.get("tr", "official") != "official":
            b["tr"] = v["tr"]
        branches[k] = loc(b)
    techs = {}
    for k, t in doc["techs"].items():
        o = {"pt": t.get("pt"), "en": t.get("en")}
        if t.get("tr", "official") != "official":
            o["tr"] = t["tr"]
        o["branch"] = t.get("branch")
        o["column"] = t.get("column")
        o["y"] = t.get("y")
        c = t.get("cost") or {}
        o["cost"] = [int(c.get("red") or 0), int(c.get("green") or 0), int(c.get("blue") or 0)]
        if t.get("parents"):
            o["parents"] = list(t["parents"])
        for f in ("hidden", "given"):
            if t.get(f):
                o[f] = True
        if t.get("listed") is False:
            o["listed"] = False
        if t.get("rep"):
            o["rep"] = {"who": loc(t["rep"].get("who")), "level": t["rep"].get("level")}
        us = []
        for u in t.get("unlocks") or []:
            e = ents.get(u.get("item")) if u.get("item") else None
            x = {"item": u.get("item"), "kind": u.get("kind")}
            if not (e and all(e.get(l) == u.get(l) for l in langs)):
                x.update({l: u.get(l) for l in sorted(langs)})
                if u.get("tr", "official") != "official":
                    x["tr"] = u["tr"]
            if u.get("station"):
                x["station"] = u["station"]
            if x["item"] is None:
                del x["item"]
            us.append(loc(x))
        if us:
            o["unlocks"] = us
        if t.get("icon"):
            o["icon"] = t["icon"]
        if t.get("notes"):
            o["notes"] = loc(t["notes"])
        techs[k] = o   # pt and en stay explicit on the tech itself
    return {"tp": loc(tp), "branches": branches, "techs": techs}


def data_versions(name_paths, wiki=None):
    """{"wiki": "1.010", "game": "1.011"}: the game version of the wiki data (`wiki`, from load_wiki_version()) and of
    the official texts (the first names file with `_meta.game_version`, else GAME_TEXT_VERSION)."""
    game = None
    for p in name_paths:
        try:
            m = json.loads(Path(p).read_text(encoding="utf-8")).get("_meta") or {}
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(m, dict) and isinstance(m.get("game_version"), str) and m["game_version"].strip():
            game = m["game_version"].strip()
            break
    return {"wiki": wiki, "game": game or GAME_TEXT_VERSION}


# Fields the page payload leaves out when they hold the value GK.data (src/js/data.js normItem / normRecipe / normLine
# / the stations in load) gives a missing one: the loaded data is the same, about 140 KB less to embed. gk2.json keeps
# them all (the public file says every field). A test (test_build.py, expand_payload) puts them back and compares.
ITEM_DEFAULTS = {"cat": None, "obtain": None, "icon": None, "tr": "missing", "kind": "item", "listed": True,
                 "unobtainable": False}
STATION_DEFAULTS = {"icon": None, "tr": "missing"}
RECIPE_DEFAULTS = {"station": None, "in": [], "tech": None, "type": "hand_craft", "cd": False, "listed": True,
                   "noexp": False, "cyc": False, "alt": [], "ext": None, "extra": [], "mastery": None, "ticks": None,
                   "energy": None, "example": False, "runes": None, "zone": None}


def drop_defaults(page):
    """Remove, in place, the default-valued fields of page["items" | "stations" | "recipes"] (ITEM_DEFAULTS…), the
    qty of an input when it is 1 or null (GK.data reads a missing one as 1) and a null qty elsewhere."""
    def strip(o, defaults):
        for k, v in defaults.items():
            if k in o and o[k] == v and type(o[k]) is type(v):
                del o[k]

    for it in page["items"].values():
        strip(it, ITEM_DEFAULTS)
    for st in page["stations"].values():
        strip(st, STATION_DEFAULTS)
    for r in page["recipes"]:
        strip(r, RECIPE_DEFAULTS)
        for ln in r.get("in", []):
            if ln.get("qty", 1) in (1, None) and type(ln.get("qty", 1)) is not bool:
                ln.pop("qty", None)
        for ln in r.get("extra", []) + [r["out"]]:
            if "qty" in ln and ln["qty"] is None:
                del ln["qty"]


def page_payload(ds, sprite=None, artifact=False, version=None, changelog=None, techs=None, data=None, days=None,
                 game_version=None):
    """The JSON embedded in the page: gk2.json minus redundancy.

    - {pt, en} pairs with identical text collapse to one string (obtain texts, notes, zones...).
    - items[].id is dropped (it is the key), and the fields holding their default value (drop_defaults()).
    - with a sprite: meta.sprite carries it; icons are drawn from it (a quality variant without its own: the base's).
    - artifact mode: remote icon URLs are dropped (the Artifact CSP blocks external images).
    - meta.version / meta.changelog: the VERSION file and data/changelog.json, when given.
    - meta.data: {wiki, game} game versions of the sources (data_versions()), when given.
    - meta.gameVersion: data/game-version.json {latest, date, note} (load_game_version()), when given (src mode).
    - techs: data/techs.json (scripts/build_techs.py) in compact form, see techs_payload().
    - days: data/days.json (scripts/build_days.py), see days_payload(); its sprite ids are kept in meta.sprite."""
    langs = set(ds["meta"]["langs"])
    out = collapse_loc(ds, langs)
    out["meta"] = dict(out["meta"], collapsed=True)
    for iid, it in out["items"].items():
        it.pop("id", None)
        if artifact:
            it["icon"] = None
    if artifact:
        for st in out["stations"].values():
            st["icon"] = None
    if sprite:
        known = set(out["items"]) | set(out["stations"]) | day_sprite_ids(days)
        icons = {k: v for k, v in sprite["icons"].items() if k in known or k.split(":", 1)[0] in SPRITE_NS}
        # a grade the dataset kept ("wine-silver", base "wine") draws its family's icon (the star tells the grade)
        for iid, it in out["items"].items():
            base = it.get("base")
            if it.get("kind") == "quality-variant" and it.get("grade") and base and iid not in icons and base in icons:
                icons[iid] = icons[base]
        out["meta"]["sprite"] = dict(sprite, icons=icons)
    drop_defaults(out)
    if techs is not None:
        out["techs"] = techs_payload(techs, ds)
    if days is not None:
        out["days"] = days_payload(days)
    if version is not None:
        out["meta"]["version"] = version
    if changelog is not None:
        out["meta"]["changelog"] = changelog
    if data is not None:
        out["meta"]["data"] = data
    if game_version is not None:
        out["meta"]["gameVersion"] = game_version
    return out
