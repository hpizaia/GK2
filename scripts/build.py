#!/usr/bin/env python3
"""Build the GK2 crafting-planner dataset.

Reads   data/items.en.json, data/recipes.en.json and the translation layers
        (data/names.official.pt-BR.json, data/names.pt-BR.json, data/names.machine.pt-BR.json; all optional),
writes  data/gk2.json, data/gk2.min.json, data/report-l10n.md, data/report-build.md
and builds the page:
  - default (src/manifest.json exists, no --inject): assembles src/index.html + src/css/* + src/js/* in
    manifest order, embeds the data and writes prototype/index.html (dev, with the document skeleton),
    dist/index.html (Claude Artifact, no skeleton) and dist/preview.html;
  - --inject PAGE (legacy): embeds the minified JSON into <script id="gk2-data" type="application/json">
    of an existing page.
Both embed VERSION and data/changelog.json as meta.version / meta.changelog, and CHANGELOG.md is
regenerated from data/changelog.json on every build (--release dates an unreleased top entry).

Python 3 stdlib only. Run with:  python3 -I scripts/build.py [options]
See scripts/README-build.md for the schema and options.

Exit codes: 0 ok (warnings allowed), 1 hard validation errors, 2 usage / IO error.
"""
import argparse
import datetime as _dt
import importlib.util
import json
import os
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"

SCHEMA_VERSION = 1
BASE_LANG = "en"
# Tier of a translation, best first. "missing" = no translation, English shown.
TIERS = ("official", "likely", "guess", "machine", "missing")
TIER_RANK = {t: i for i, t in enumerate(TIERS)}
# defaultRecipe preference when no recipe has calculator_default: true
TYPE_PREF = ("hand_craft", "star_craft", "auto", "factory", "building", "alchemy", "grow")
TYPE_RANK = {t: i for i, t in enumerate(TYPE_PREF)}
NOEXP_TYPES = {"grow"}   # recipes whose yield is unknown: kept, but never expanded
# Game versions of the two sources (see docs/dados.md): the wiki's recipes describe 1.010; the official texts were
# exported from 1.011 (a names file's `_meta.game_version` wins over GAME_TEXT_VERSION). Page only: meta.data.
WIKI_GAME_VERSION = "1.010"
GAME_TEXT_VERSION = "1.011"


def _load_validate():
    # `python3 -I` does not put the script dir on sys.path, so load validate.py by path.
    spec = importlib.util.spec_from_file_location("gk2_validate", HERE / "validate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate = _load_validate()


# --------------------------------------------------------------------------- helpers

def slugify(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "x"


def norm_key(s):
    s = unicodedata.normalize("NFC", str(s))
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip().casefold()


class Log:
    """Collects coercions (things we had to fix in the inputs), counted per kind with examples."""

    def __init__(self, max_examples=8):
        self.counts = defaultdict(int)
        self.examples = defaultdict(list)
        self.max_examples = max_examples
        self.notes = []

    def coerce(self, kind, example):
        self.counts[kind] += 1
        if len(self.examples[kind]) < self.max_examples:
            self.examples[kind].append(str(example))

    def note(self, msg):
        self.notes.append(msg)


def load_json(path, what, log, required=True):
    p = Path(path)
    if not p.exists():
        if required:
            raise SystemExit(_die(f"{what}: file not found: {p}"))
        log.note(f"{what}: `{p.name}` not found, skipped")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        raise SystemExit(_die(f"{what}: invalid JSON in {p}: {e}"))


def _die(msg):
    print(f"build: {msg}", file=sys.stderr)
    return 2


def as_list(data, what, log, keys):
    """Accept a list, a {"items": [...]} wrapper, or a dict keyed by id."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in keys:
            if isinstance(data.get(k), list):
                log.coerce(f"{what}: unwrapped `{k}` key", k)
                return data[k]
        if all(isinstance(v, dict) for v in data.values()):
            log.coerce(f"{what}: dict keyed by id converted to list", len(data))
            out = []
            for k, v in data.items():
                v = dict(v)
                v.setdefault("id", k)
                out.append(v)
            return out
    raise SystemExit(_die(f"{what}: expected a JSON array"))


def parse_qty(v, ctx, log, allow_null=False):
    """Returns int/float, or None (only when allow_null and v is None). Bad values become 0 (-> bad-qty error)."""
    if v is None:
        if allow_null:
            return None
        log.coerce("qty null -> 1", ctx)
        return 1
    if isinstance(v, bool):
        log.coerce("qty boolean -> 0/1", ctx)
        return int(v)
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return v
    if isinstance(v, str):
        try:
            f = float(v.strip().replace(",", "."))
        except ValueError:
            log.coerce("qty unparseable -> 0", f"{ctx}: {v!r}")
            return 0
        log.coerce("qty string -> number", f"{ctx}: {v!r}")
        return int(f) if f.is_integer() else f
    log.coerce("qty unparseable -> 0", f"{ctx}: {v!r}")
    return 0


def text_or_none(v):
    if v is None:
        return None
    if isinstance(v, list):
        v = "; ".join(str(x).strip() for x in v if x not in (None, ""))
    elif isinstance(v, dict):
        v = v.get("en") or v.get("name") or v.get("text")
    v = str(v).strip() if v is not None else ""
    return v or None


# --------------------------------------------------------------------------- translations

class Layer:
    """One names file: { "<English>": {pt, source, confidence}, "__obtain": {"<English text>": "<pt>"} }."""

    def __init__(self, path, data, log, machine):
        self.path = Path(path)
        self.machine = machine
        self.names = {}    # norm key -> (pt, tier, source, original key)
        self.texts = {}    # norm key -> pt (free text: obtain, notes)
        self.keys = {}     # norm key -> game localisation key ("gameKey"), when the file has one
        if data is None:
            return
        if isinstance(data, dict) and isinstance(data.get("names"), dict):
            log.coerce("names: unwrapped `names` key", self.path.name)
            texts = data.get("__obtain") or data.get("obtain")
            data = dict(data["names"], __obtain=texts or {})
        if isinstance(data, list):   # [{en, pt, ...}]
            log.coerce("names: list converted to dict", self.path.name)
            data = {e.get("en") or e.get("name"): e for e in data if isinstance(e, dict)}
        if not isinstance(data, dict):
            log.note(f"names: `{self.path.name}` is not an object, ignored")
            return
        for k, v in data.items():
            if k is None:
                continue
            if k.startswith("__"):
                if isinstance(v, dict):
                    for tk, tv in v.items():
                        pt = tv.get("pt") if isinstance(tv, dict) else tv
                        if isinstance(pt, str) and pt.strip():
                            self.texts[norm_key(tk)] = pt.strip()
                else:
                    log.coerce("names: non-object special key ignored", f"{self.path.name}:{k}")
                continue
            if k.startswith("_"):
                log.coerce("names: `_` key ignored", f"{self.path.name}:{k}")
                continue
            if isinstance(v, str):
                log.coerce("names: bare string value -> confidence guess", f"{k!r}")
                v = {"pt": v, "confidence": "guess", "source": None}
            if not isinstance(v, dict):
                log.coerce("names: bad entry ignored", f"{k!r}")
                continue
            pt = v.get("pt") or v.get("name") or v.get("value")
            if not isinstance(pt, str) or not pt.strip():
                log.coerce("names: entry without pt ignored", f"{k!r}")
                continue
            conf = str(v.get("confidence") or "").strip().lower()
            source = v.get("source")
            if machine or (isinstance(source, str) and source.strip().lower() == "machine"):
                tier = "machine"
            elif conf in ("official", "likely", "guess"):
                tier = conf
            else:
                log.coerce("names: unknown confidence -> guess", f"{k!r}: {v.get('confidence')!r}")
                tier = "guess"
            nk = norm_key(k)
            gk = v.get("gameKey")
            if isinstance(gk, str) and gk.strip() and nk not in self.keys:
                self.keys[nk] = gk.strip()
            prev = self.names.get(nk)
            if prev and TIER_RANK[prev[1]] <= TIER_RANK[tier]:
                continue
            self.names[nk] = (pt.strip(), tier, source, k)


class Translator:
    """All layers of one language, merged by tier: official > likely > guess > machine."""

    def __init__(self, field, layers):
        self.field = field
        self.layers = layers
        self.looked_up = set()   # norm keys of every English string we asked for

    def name(self, en):
        """-> (text, tier, source). Falls back to English with tier 'missing'."""
        if en is None:
            return None, "missing", None
        nk = norm_key(en)
        self.looked_up.add(nk)
        best = None
        for li, layer in enumerate(self.layers):
            hit = layer.names.get(nk)
            if hit and (best is None or TIER_RANK[hit[1]] < TIER_RANK[best[1][1]]):
                best = (li, hit)
        if best is None:
            return en, "missing", None
        pt, tier, source, _ = best[1]
        return pt, tier, source

    def game_key(self, en):
        """Game localisation key for an English name (first layer that has one), or None."""
        if en is None:
            return None
        nk = norm_key(en)
        for layer in self.layers:
            if nk in layer.keys:
                return layer.keys[nk]
        return None

    def text(self, en):
        """Free text (obtain / notes): text maps first, then names. Falls back to English."""
        if en is None:
            return None
        hit = self.text_hit(en)
        return en if hit is None else hit

    def text_hit(self, en):
        """Like text(), but None when no text map or names entry has the string."""
        if en is None:
            return None
        nk = norm_key(en)
        for layer in self.layers:
            if nk in layer.texts:
                return layer.texts[nk]
        pt, tier, _ = self.name(en)
        return None if tier == "missing" else pt

    def sources(self):
        out = set()
        for layer in self.layers:
            for (_, tier, source, _) in layer.names.values():
                if isinstance(source, str) and source.strip():
                    out.add(source_host(source))
        return out

    def unused(self):
        out = []
        for li, layer in enumerate(self.layers):
            for nk, (pt, tier, source, key) in layer.names.items():
                if nk not in self.looked_up:
                    out.append((layer.path.name, key, pt, tier))
        return sorted(out, key=lambda x: (x[0], norm_key(x[1])))


# --------------------------------------------------------------------------- recipe notes (pt)

# Recurring English shapes of the recipe input / by-product notes. The last group is a perk or tech
# name ("Mason", "Farmer II and Grape Master"), resolved through the names layers.
NOTE_PATTERNS_PT = (
    (re.compile(r"^(\d+(?:\.\d+)?)% chance with (.+)$", re.I), "{0}% de chance com {1}"),
    (re.compile(r"^(\d+), or (\d+) with (.+)$", re.I), "{0}, ou {1} com {2}"),
    (re.compile(r"^(\d+) \((\d+) with (.+)\)$", re.I), "{0} ({1} com {2})"),
    (re.compile(r"^\+(\d+) each with (.+)$", re.I), "+{0} cada com {1}"),
    (re.compile(r"^(\d+) with (.+)$", re.I), "{0} com {1}"),
    (re.compile(r"^with (.+)$", re.I), "com {0}"),
)


def translate_note_pt(en, text_hit, name_hit):
    """English recipe note -> (pt or None, [unresolved names]).

    `text_hit(s)` -> pt for a literal string (the names files' `__notes` / `__obtain` maps, or a
    name), else None. `name_hit(s)` -> pt for a perk/tech name, else None. A note is split on "; "
    and every segment must be translated (literal first, then NOTE_PATTERNS_PT), or the result is
    None. A name with no translation stays in English and is reported in the second value."""
    if not en or not str(en).strip():
        return None, []
    unresolved = []

    def names(s):
        out = []
        for part in re.split(r"\s+and\s+", s.strip()):
            pt = name_hit(part)
            if pt is None:
                unresolved.append(part)
                pt = part
            out.append(pt)
        return " e ".join(out)

    segs = []
    for seg in str(en).split(";"):
        seg = seg.strip()
        if not seg:
            continue
        lit = text_hit(seg)
        if lit is not None:
            segs.append(lit)
            continue
        for rx, tpl in NOTE_PATTERNS_PT:
            m = rx.match(seg)
            if m:
                g = list(m.groups())
                g[-1] = names(g[-1])
                segs.append(tpl.format(*g))
                break
        else:
            return None, unresolved
    return ("; ".join(segs) if segs else None), unresolved


def source_host(s):
    m = re.match(r"^[a-z][a-z0-9+.-]*://([^/]+)", s.strip(), re.I)
    if m:
        h = m.group(1).lower()
        return h[4:] if h.startswith("www.") else h
    return s.strip()


def parse_lang_specs(specs, log):
    """--lang pt=data/names.pt-BR.json,data/names.machine.pt-BR.json  (repeatable)."""
    langs = []
    for spec in specs:
        if "=" not in spec:
            raise SystemExit(_die(f"--lang expects FIELD=PATH[,PATH...], got {spec!r}"))
        field, paths = spec.split("=", 1)
        field = field.strip()
        if not re.fullmatch(r"[a-z]{2,3}(_[A-Za-z]{2,4})?", field) or field == BASE_LANG:
            raise SystemExit(_die(f"--lang: bad field name {field!r}"))
        layers = []
        for p in [x for x in paths.split(",") if x.strip()]:
            p = Path(p.strip())
            if not p.is_absolute():
                p = (Path.cwd() / p)
            data = load_json(p, f"names[{field}]", log, required=False)
            layers.append(Layer(p, data, log, machine=".machine." in p.name))
        langs.append(Translator(field, layers))
    return langs


# --------------------------------------------------------------------------- build

class Builder:
    def __init__(self, raw_items, raw_recipes, langs, log, extra_sources=()):
        self.log = log
        self.langs = langs            # [Translator]; langs[0] owns the `tr` field
        self.pre = []                 # pre-validation issues (Issue objects)
        self.raw_items = raw_items
        self.raw_recipes = raw_recipes
        self.extra_sources = list(extra_sources)
        self.stub_ids = set()
        self.l10n_rows = defaultdict(dict)   # (kind) -> key -> row
        self.note_rows = defaultdict(dict)   # lang field -> norm key -> {en, loc, how, unresolved, uses}

    # ---- localisation helpers
    def loc(self, en, kind=None, key=None):
        """{pt, en, ...} for a name; records gaps for the l10n report."""
        if en is None:
            return None
        out = {}
        tiers = {}
        for t in self.langs:
            txt, tier, _ = t.name(en)
            out[t.field] = txt
            tiers[t.field] = tier
        out[BASE_LANG] = en
        if kind:
            self.l10n_rows[kind].setdefault(key or en, {"en": en, "key": key or en, "tiers": tiers, "loc": out})
        return out, tiers

    def loc_obj(self, en, kind=None, key=None):
        r = self.loc(en, kind, key)
        return None if r is None else r[0]

    def loc_text(self, en, kind=None):
        """{pt, en, ...} for free text. kind="note" (recipe input / by-product notes) also tries the
        pt pattern translator (translate_note_pt) and records the result for the l10n report."""
        if en is None:
            return None
        out = {}
        for t in self.langs:
            hit = t.text_hit(en)
            how = "text" if hit is not None else "missing"
            unresolved = []
            if hit is None and kind == "note" and t.field == "pt":
                def name_hit(s, t=t):
                    pt, tier, _ = t.name(s)
                    return None if tier == "missing" else pt
                hit, unresolved = translate_note_pt(en, t.text_hit, name_hit)
                if hit is not None:
                    how = "partial" if unresolved else "pattern"
            out[t.field] = en if hit is None else hit
            if kind == "note":
                row = self.note_rows[t.field].setdefault(norm_key(en), {"en": en, "uses": 0})
                row.update({"loc": out[t.field], "how": how, "unresolved": unresolved})
                row["uses"] += 1
        out[BASE_LANG] = en
        return out

    def loc_list(self, en, kind):
        """A comma-separated list of names ("Yard, Quarry, Home"): the whole string if a names file
        has it, else each part translated and re-joined; the tier is the worst part's."""
        if "," not in en:
            return self.loc_obj(en, kind, en)
        parts = [p.strip() for p in en.split(",") if p.strip()]
        out, tiers = {}, {}
        for t in self.langs:
            txt, tier, _ = t.name(en)
            if tier == "missing":
                res = [t.name(p) for p in parts]
                txt = ", ".join(r[0] for r in res)
                tier = max((r[1] for r in res), key=lambda x: TIER_RANK[x])
            out[t.field] = txt
            tiers[t.field] = tier
        out[BASE_LANG] = en
        self.l10n_rows[kind].setdefault(en, {"en": en, "key": en, "tiers": tiers, "loc": out})
        return out

    def tr_fields(self, tiers):
        out = {}
        for i, t in enumerate(self.langs):
            out["tr" if i == 0 else f"tr_{t.field}"] = tiers[t.field]
        return out

    # ---- main
    def run(self):
        log = self.log
        items_in = []
        seen = {}
        for idx, it in enumerate(self.raw_items):
            if not isinstance(it, dict):
                log.coerce("items: non-object entry dropped", idx)
                continue
            iid = it.get("id")
            name = text_or_none(it.get("name"))
            if not iid:
                if not name:
                    log.coerce("items: entry without id and name dropped", idx)
                    continue
                iid = slugify(name)
                log.coerce("items: missing id -> slug(name)", iid)
            iid = str(iid)
            if not name:
                name = iid
                log.coerce("items: missing name -> id", iid)
            if iid in seen:
                self.pre.append(validate.Issue("error", "duplicate-id",
                                               f"item id `{iid}` appears more than once in items.en.json "
                                               f"(#{seen[iid]} and #{idx}); kept the first", {"item": iid}))
                continue
            seen[iid] = idx
            items_in.append((iid, name, it))

        self.ids = {iid for iid, _, _ in items_in}
        self.by_name = {}
        for iid, name, _ in items_in:
            self.by_name.setdefault(norm_key(name), iid)
        self.names_of = {iid: name for iid, name, _ in items_in}
        self.derive_names(items_in)

        # ---- recipes
        recipes = []
        rseen = {}
        for idx, r in enumerate(self.raw_recipes):
            if not isinstance(r, dict):
                log.coerce("recipes: non-object entry dropped", idx)
                continue
            nr = self.norm_recipe(r, idx)
            if nr is None:
                continue
            if nr["id"] in rseen:
                self.pre.append(validate.Issue("error", "duplicate-id",
                                               f"recipe id `{nr['id']}` appears more than once in recipes.en.json "
                                               f"(#{rseen[nr['id']]} and #{idx}); kept the first",
                                               {"recipe": nr["id"]}))
                continue
            rseen[nr["id"]] = idx
            nr["_idx"] = idx
            recipes.append(nr)
        self.recipes = recipes

        # ---- stations
        self.stations = {}
        for r in recipes:
            for sid, sname in [(r["station"], r.pop("_station_name"))] + list(zip(r["alt"], r.pop("_alt_names"))):
                if sid is None or sid in self.stations:
                    continue
                en = self.names_of.get(sid) or sname or sid
                loc, tiers = self.loc(en, "station", sid)
                st = dict(loc)
                st.update(self.tr_fields(tiers))
                icon = None
                for iid, _, it in items_in:
                    if iid == sid:
                        icon = text_or_none(it.get("icon"))
                        break
                st["icon"] = icon
                self.stations[sid] = st

        # ---- per-item recipe lists + default
        produced = defaultdict(list)
        for r in recipes:
            produced[r["out"]["item"]].append(r)
        # cyc = expanding this recipe can lead back to its own output, in the expansion graph
        # (item -> inputs of its expandable recipes, where items flagged raw are leaves).
        # Catches self-references ("Improve organ I from Any Bones": bones + improver -> bones)
        # without punishing e.g. seeds crafted from a raw crop that has an optional loop.
        raw_flag = {}
        for iid, _, it in items_in:
            v = it.get("is_raw")
            raw_flag[iid] = v if isinstance(v, bool) else not any(
                (not r["noexp"]) and r["in"] for r in produced.get(iid, []))
        exp_edges = defaultdict(set)
        for r in recipes:
            if not r["noexp"] and not raw_flag.get(r["out"]["item"], False):
                for i in r["in"]:
                    exp_edges[r["out"]["item"]].add(i["item"])

        def reaches(src, dst):
            seen, todo = {src}, [src]
            while todo:
                n = todo.pop()
                if n == dst:
                    return True
                for m in exp_edges.get(n, ()):
                    if m not in seen:
                        seen.add(m)
                        todo.append(m)
            return False

        for r in recipes:
            o = r["out"]["item"]
            r["cyc"] = (not r["noexp"]) and any(reaches(i["item"], o) for i in r["in"])

        # ---- items
        items = {}
        raw_computed = 0
        for iid, name, it in items_in:
            items[iid] = self.norm_item(iid, name, it, produced.get(iid, []))
            if "is_raw" not in it or not isinstance(it.get("is_raw"), bool):
                raw_computed += 1
        if raw_computed:
            log.coerce("items: is_raw missing/non-bool -> computed from recipes", f"{raw_computed} item(s)")

        # ---- stubs for dangling references
        for sid in sorted(self.stub_ids):
            if sid in items:
                continue
            loc, tiers = self.loc(sid, "item", sid)
            stub = {"id": sid}
            stub.update(loc)
            stub.update({"cat": None, "icon": None})
            stub.update(self.tr_fields(tiers))
            stub.update({"raw": True, "obtain": None, "kind": "item", "listed": True, "unobtainable": False,
                         "recipes": [r["id"] for r in produced.get(sid, [])], "defaultRecipe": None,
                         "stub": True})
            items[sid] = stub

        for r in recipes:
            r.pop("_idx", None)
            r.pop("_up", None)

        self.items = {k: items[k] for k in sorted(items)}
        self.produced = produced
        return self

    # ---- derived pt names (quality grades, "A or B" groups, "Any X", "Open (X)", "Repair (X)")
    DERIVED_GRADE = {"bronze": "bronze", "silver": "prata", "gold": "ouro", "silver or gold": "prata ou ouro"}
    DERIVED_TIERS = ("official", "likely")   # a derived name is built only from names at these tiers

    def derive_names(self, items_in):
        """Add a synthetic lowest-precedence `derived` layer (tier likely) to the `pt` translator.

        Applied only when the full name has no official entry; an existing likely entry from a
        names file also wins (equal tier, earlier layer). Parts must resolve at official/likely."""
        t = next((x for x in self.langs if x.field == "pt"), None)
        if t is None:
            return
        layer = Layer(Path("derived"), None, self.log, machine=False)

        def part(en):
            if not en:
                return None
            nk = norm_key(en)
            t.looked_up.add(nk)   # a key used only as a part is not "unused"
            best = None
            for ly in t.layers:
                hit = ly.names.get(nk)
                if hit and (best is None or TIER_RANK[hit[1]] < TIER_RANK[best[1]]):
                    best = hit
            return best[0] if best and best[1] in self.DERIVED_TIERS else None

        def lower_first(s):
            return s[:1].lower() + s[1:] if s else s

        made = 0
        for iid, name, it in items_in:
            nk = norm_key(name)
            if any(nk in ly.names and ly.names[nk][1] == "official" for ly in t.layers):
                continue
            kind = text_or_none(it.get("kind")) or "item"
            pt = None
            m = re.match(r"^(.*\S)\s*\((bronze|silver|gold|silver or gold)\)$", name, re.I)
            if m and kind in ("quality-variant", "group"):
                base = it.get("base_item")
                base_en = self.names_of.get(base) if isinstance(base, str) else None
                b = part(base_en) or part(m.group(1))
                if b:
                    pt = f"{b} ({self.DERIVED_GRADE[m.group(2).lower()]})"
            elif kind == "group" and " or " in name and isinstance(it.get("group_members"), list):
                a, _, c = name.partition(" or ")
                pa, pc = part(a), part(c)
                if pa and pc:
                    pt = f"{pa} ou {lower_first(pc)}"
            elif name.lower().startswith("any "):
                x = part(name[4:])
                if x:
                    pt = "Qualquer " + lower_first(x)
            else:
                m = re.match(r"^(Open|Repair)\s*\((.+)\)$", name)
                if m:
                    x = part(m.group(2))
                    if x:
                        pt = ("Abrir" if m.group(1) == "Open" else "Reparar") + f" ({x})"
            if pt:
                layer.names[nk] = (pt, "likely", "derived", name)
                made += 1
        if made:
            t.layers.append(layer)
            self.log.note(f"names[pt]: {made} derived name(s) (quality grades, groups, Any/Open/Repair), tier likely")

    def resolve(self, ref, ctx):
        """Item reference -> item id. Accepts ids, {id}/{item}/{name} dicts, English names, slugs."""
        if isinstance(ref, dict):
            ref = ref.get("id") or ref.get("item") or ref.get("name")
        if ref is None or str(ref).strip() == "":
            self.log.coerce("ref: empty item reference -> `unknown`", ctx)
            ref = "unknown"
        ref = str(ref).strip()
        if ref in self.ids:
            return ref
        nk = norm_key(ref)
        if nk in self.by_name:
            self.log.coerce("ref: English name -> id", f"{ctx}: {ref!r} -> {self.by_name[nk]}")
            return self.by_name[nk]
        sl = slugify(ref)
        if sl in self.ids:
            self.log.coerce("ref: slugified -> id", f"{ctx}: {ref!r} -> {sl}")
            return sl
        self.stub_ids.add(ref)
        return ref

    def station_ref(self, sid, sname, ctx):
        """-> (station id or None, English display name or None)."""
        if isinstance(sname, dict):
            sid = sid or sname.get("id")
            sname = sname.get("name") or sname.get("en")
        sname = text_or_none(sname)
        if sid:
            return str(sid), sname
        if sname:
            nk = norm_key(sname)
            if nk in self.by_name:
                return self.by_name[nk], sname
            return slugify(sname), sname
        return None, None

    def norm_inputs(self, raw, rid, what):
        log = self.log
        if raw is None:
            return []
        if isinstance(raw, dict):   # {item: qty}
            log.coerce(f"{what}: object -> list", rid)
            raw = [{"item": k, "qty": v} for k, v in raw.items()]
        out = []
        index = {}
        for j, inp in enumerate(raw):
            if isinstance(inp, (list, tuple)) and len(inp) >= 1:
                log.coerce(f"{what}: [item, qty] pair -> object", rid)
                inp = {"item": inp[0], "qty": inp[1] if len(inp) > 1 else 1}
            elif isinstance(inp, str):
                log.coerce(f"{what}: bare string -> qty 1", f"{rid}: {inp}")
                inp = {"item": inp, "qty": 1}
            elif not isinstance(inp, dict):
                log.coerce(f"{what}: bad entry dropped", rid)
                continue
            iid = self.resolve(inp.get("item", inp.get("id", inp.get("name"))), f"{rid} {what}")
            qty = parse_qty(inp.get("qty", inp.get("count", inp.get("amount"))), f"{rid} {what} {iid}", log)
            note = text_or_none(inp.get("note"))
            if iid in index:
                prev = out[index[iid]]
                if isinstance(prev["qty"], (int, float)) and isinstance(qty, (int, float)):
                    log.coerce(f"{what}: duplicate line merged (qty summed)", f"{rid}: {iid}")
                    prev["qty"] += qty
                    continue
            entry = {"item": iid, "qty": qty}
            if note:
                entry["note"] = self.loc_text(note, "note")
            index[iid] = len(out)
            out.append(entry)
        return out

    def norm_recipe(self, r, idx):
        log = self.log
        # output
        out = r.get("output", r.get("out"))
        if out is None and ("output_item" in r or "item" in r):
            out = {"item": r.get("output_item", r.get("item")), "qty": r.get("output_qty", r.get("qty", 1))}
            log.coerce("recipes: flat output fields -> output object", r.get("id") or idx)
        if isinstance(out, (str, int)):
            log.coerce("recipes: output as string -> {item, qty: 1}", r.get("id") or idx)
            out = {"item": out, "qty": 1}
        if not isinstance(out, dict):
            log.coerce("recipes: recipe without output dropped", r.get("id") or idx)
            return None
        rid = r.get("id")
        if not rid:
            rid = f"{slugify(out.get('item'))}--r{idx}"
            log.coerce("recipes: missing id -> <output>--r<index>", rid)
        rid = str(rid)
        rtype = text_or_none(r.get("type"))
        noexp = rtype in NOEXP_TYPES
        oid = self.resolve(out.get("item", out.get("id")), f"{rid} output")
        qty = parse_qty(out.get("qty"), f"{rid} output", log, allow_null=True)
        if qty is None and not noexp:
            log.coerce("qty null on a non-grow recipe -> non-expandable", rid)
            noexp = True
        ins = self.norm_inputs(r.get("inputs", r.get("in")), rid, "inputs")

        sid, sname = self.station_ref(r.get("station_id"), r.get("station"), rid)
        alt_ids, alt_names = [], []
        for a in r.get("alt_stations") or []:
            aid, aname = self.station_ref(None, a, rid)
            if aid and aid != sid and aid not in alt_ids:
                alt_ids.append(aid)
                alt_names.append(aname)

        # tech / unlock
        unlock = r.get("unlock", r.get("tech"))
        tech = None
        if isinstance(unlock, str) and unlock.strip():
            unlock = {"name": unlock.strip(), "type": "technology", "id": slugify(unlock)}
        if isinstance(unlock, dict) and text_or_none(unlock.get("name")):
            tname = text_or_none(unlock.get("name"))
            tech = self.loc_obj(tname, "tech", tname)
            tech["id"] = unlock.get("id") or slugify(tname)
            tech["type"] = text_or_none(unlock.get("type")) or "technology"

        mastery = r.get("mastery")
        if isinstance(mastery, dict) and mastery.get("type"):
            mastery = {"type": self.loc_obj(str(mastery["type"]), "mastery", str(mastery["type"])),
                       "level": mastery.get("level")}
        else:
            mastery = None

        extra = []
        for ex in r.get("extra_outputs") or []:
            if not isinstance(ex, dict):
                continue
            eid = self.resolve(ex.get("item"), f"{rid} extra")
            e = {"item": eid, "qty": parse_qty(ex.get("qty"), f"{rid} extra {eid}", log, allow_null=True)}
            note = text_or_none(ex.get("note"))
            if note:
                e["note"] = self.loc_text(note, "note")
            extra.append(e)

        ext = text_or_none(r.get("station_extension"))
        zone = text_or_none(r.get("zone"))
        rname = text_or_none(r.get("name"))
        runes = r.get("rune_requirement") if isinstance(r.get("rune_requirement"), dict) else None
        listed = r.get("listed")
        if not isinstance(listed, bool):
            listed = True

        nr = {
            "id": rid,
            "out": {"item": oid, "qty": qty},
            "station": sid,
            "in": ins,
            "tech": tech,
            "type": rtype,
            "cd": bool(r.get("calculator_default")),
            "listed": listed,
            "noexp": noexp,
            "cyc": False,     # set in run(): an input can lead back to the output
            "alt": alt_ids,
            "ext": self.loc_obj(ext, "extension", ext) if ext else None,
            "extra": extra,
            "mastery": mastery,
            "ticks": r.get("time_ticks") if isinstance(r.get("time_ticks"), (int, float)) else None,
            "energy": r.get("energy_per_tick") if isinstance(r.get("energy_per_tick"), (int, float)) else None,
            "example": bool(r.get("inputs_are_example")),
            "runes": runes,
            "zone": self.loc_list(zone, "zone") if zone else None,
            "_station_name": sname,
            "_alt_names": alt_names,
            "_up": bool(r.get("quality_upgrade")),
        }
        # made_text: "3 (5 with Cook II)" -> out.note {pt, en} (the page reads the perk bonus from it); a plain
        # number equal to the output qty says nothing more and is dropped
        made = text_or_none(r.get("made_text"))
        if made is not None:
            made = str(made).strip()
            plain = re.fullmatch(r"\d+(?:\.\d+)?", made)
            if made and not (plain and isinstance(qty, (int, float)) and float(made) == float(qty)):
                nr["out"]["note"] = self.loc_text(made, "note")
        # star_quality: {"silver_at": "6 successful ticks", "gold_at": "10 successful ticks"} -> {silver: 6, gold: 10}
        # (a value that is not "<N> successful ticks" is kept as text)
        sq = r.get("star_quality")
        if isinstance(sq, dict):
            star = {}
            for grade in ("silver", "gold"):
                v = sq.get(grade + "_at", sq.get(grade))
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    star[grade] = v
                elif isinstance(v, str) and v.strip():
                    m = re.fullmatch(r"(\d+)(?:\s+successful\s+ticks?)?", v.strip(), re.I)
                    star[grade] = int(m.group(1)) if m else v.strip()
            if star:
                nr["star_quality"] = star
        oname = norm_key(self.names_of.get(oid) or oid)
        # keep the recipe's own name only when it says more than the output name
        # ("Board (Sawhorse)", "Alcohol from Beer"), not for "Build <output>"
        if rname and norm_key(rname) not in (oname, "build " + oname):
            nr["name"] = self.loc_obj(rname, "recipe", rname)
        return nr

    def recipe_sort_key(self, r):
        # usable first, then the direct ones before a quality upgrade (Vinho (prata): the Barril with silver Grape Juice
        # before "Wine (bronze) + Spices"; build_dataset.py quality_upgrade), calculator_default, listed, type
        # preference, input order
        return (r["noexp"], r["cyc"], r["_up"], not r["cd"], not r["listed"],
                TYPE_RANK.get(r["type"], len(TYPE_RANK)), r["_idx"])

    def norm_item(self, iid, name, it, recipes):
        log = self.log
        loc, tiers = self.loc(name, "item", iid)
        cat_en = text_or_none(it.get("category"))
        cat = self.loc_obj(cat_en, "category", cat_en) if cat_en else None
        icon = text_or_none(it.get("icon"))
        obtain_en = text_or_none(it.get("obtain"))
        ordered = sorted(recipes, key=self.recipe_sort_key)
        raw = it.get("is_raw")
        if not isinstance(raw, bool):
            raw = not any((not r["noexp"]) and r["in"] for r in recipes)
        # raw items are leaves by default (their recipes stay listed for a manual choice)
        default = None if raw else next((r["id"] for r in ordered if not r["noexp"] and not r["cyc"]), None)
        listed = it.get("listed")
        if not isinstance(listed, bool):
            listed = True
        out = {"id": iid}
        out.update(loc)
        out.update({"cat": cat, "icon": icon})
        out.update(self.tr_fields(tiers))
        out.update({
            "raw": raw,
            "obtain": self.loc_text(obtain_en),
            "kind": text_or_none(it.get("kind")) or "item",
            "listed": listed,
            "unobtainable": bool(it.get("unobtainable")),
            "recipes": [r["id"] for r in ordered],
            "defaultRecipe": default,
        })
        gkey = self.langs[0].game_key(name) if self.langs else None
        if gkey:
            out["key"] = gkey
        base = it.get("base_item")
        if out["kind"] == "quality-variant" and isinstance(base, str) and base:
            out["base"] = base   # the family's plain item ("wine" for wine-silver; GK.data.family)
        members = it.get("group_members")
        if isinstance(members, list) and members:
            out["members"] = [self.resolve(m, f"{iid} group_members") for m in members]
        runes = it.get("alchemy_runes")
        if isinstance(runes, dict) and runes:
            out["runes"] = runes
        return out

    # ---- output
    def dataset(self, built, report=None):
        tr_counts = {t.field: {k: 0 for k in TIERS} for t in self.langs}
        for it in self.items.values():
            for i, t in enumerate(self.langs):
                tr_counts[t.field][it["tr" if i == 0 else f"tr_{t.field}"]] += 1
        sources = set()
        for r in self.raw_recipes:
            if isinstance(r, dict) and isinstance(r.get("source_url"), str) and r["source_url"].strip():
                sources.add(source_host(r["source_url"]))
        sources.update(self.extra_sources)
        if not sources:
            sources.add("wikily.gg")
        for t in self.langs:
            sources.update(s for s in t.sources() if s and s != "machine")
        cats = {it["cat"]["en"] for it in self.items.values() if it.get("cat")}
        techs = {r["tech"]["id"] for r in self.recipes if r.get("tech")}
        counts = {
            "items": len(self.items),
            "recipes": len(self.recipes),
            "stations": len(self.stations),
            "categories": len(cats),
            "techs": len(techs),
            "multiRecipeItems": sum(1 for v in self.produced.values() if len(v) > 1),
            "noexpRecipes": sum(1 for r in self.recipes if r["noexp"]),
            "tr": tr_counts[self.langs[0].field] if self.langs else {},
        }
        for t in self.langs[1:]:
            counts[f"tr_{t.field}"] = tr_counts[t.field]
        if report is not None:
            counts["cycles"] = len(report.cycles)
            counts["errors"] = len(report.errors)
            counts["warnings"] = len(report.warnings)
        return {
            "meta": {
                "schema": SCHEMA_VERSION,
                "built": built,
                "langs": [t.field for t in self.langs] + [BASE_LANG],
                "counts": counts,
                "sources": sorted(sources),
            },
            "items": self.items,
            "stations": {k: self.stations[k] for k in sorted(self.stations)},
            "recipes": self.recipes,
        }


# --------------------------------------------------------------------------- reports

def usage_counts(ds):
    """How many recipes touch each item / station / category / tech / other name."""
    items = ds["items"]
    use_item = defaultdict(set)
    use_station = defaultdict(set)
    use_cat = defaultdict(set)
    use_tech = defaultdict(set)
    use_misc = defaultdict(set)
    for r in ds["recipes"]:
        rid = r["id"]
        touched = {r["out"]["item"]} | {i["item"] for i in r["in"]} | {e["item"] for e in r.get("extra") or []}
        for iid in touched:
            use_item[iid].add(rid)
            cat = (items.get(iid) or {}).get("cat")
            if cat:
                use_cat[cat["en"]].add(rid)
        for sid in [r["station"]] + list(r.get("alt") or []):
            if sid:
                use_station[sid].add(rid)
                use_item[sid].add(rid)
        if r.get("tech"):
            use_tech[r["tech"]["en"]].add(rid)
        for k in ("mastery",):
            if r.get(k):
                use_misc[r[k]["type"]["en"]].add(rid)
        for k in ("ext", "zone", "name"):
            if r.get(k):
                use_misc[r[k]["en"]].add(rid)
    return use_item, use_station, use_cat, use_tech, use_misc


def md(s):
    return "" if s is None else str(s).replace("|", "\\|").replace("\n", " ")


def l10n_report(builder, ds, tr_index=0):
    t = builder.langs[tr_index]
    f = t.field
    use_item, use_station, use_cat, use_tech, use_misc = usage_counts(ds)
    rows = builder.l10n_rows
    sections = [
        ("Items", "item", lambda key: len(use_item.get(key, ()))),
        ("Stations (same names-file key as the station item)", "station", lambda key: len(use_station.get(key, ()))),
        ("Station extensions", "extension", lambda key: len(use_misc.get(key, ()))),
        ("Categories", "category", lambda key: len(use_cat.get(key, ()))),
        ("Technologies / unlocks", "tech", lambda key: len(use_tech.get(key, ()))),
        ("Masteries", "mastery", lambda key: len(use_misc.get(key, ()))),
        ("Zones", "zone", lambda key: len(use_misc.get(key, ()))),
        ("Recipe names (when different from the output item)", "recipe", lambda key: len(use_misc.get(key, ()))),
    ]
    L = [f"# Localisation gaps: `{f}`", "",
         f"Built {ds['meta']['built']}. Names with `tr` = missing, machine or guess, most-used first "
         f"(\"uses\" = number of recipes that reference the name as output, input, by-product, station, "
         f"category, tech...). Translate from the top. Add entries to the sourced names file "
         f"(key = exact English name, value `{{\"pt\": ..., \"source\": ..., \"confidence\": \"official|likely|guess\"}}`).",
         ""]
    summary = []
    body = []
    for title, kind, uses in sections:
        entries = []
        for key, row in rows.get(kind, {}).items():
            tier = row["tiers"][f]
            if tier in ("missing", "guess", "machine"):
                entries.append((uses(key), row["en"], row["loc"][f], tier, key))
        tot = len(rows.get(kind, {}))
        cnt = defaultdict(int)
        for e in entries:
            cnt[e[3]] += 1
        summary.append(f"| {title} | {tot} | {cnt['missing']} | {cnt['machine']} | {cnt['guess']} |")
        if not entries:
            continue
        for tier_group, label in ((("missing",), "missing (English shown)"),
                                  (("machine", "guess"), "needs review (machine / guess)")):
            sel = [e for e in entries if e[3] in tier_group]
            if not sel:
                continue
            sel.sort(key=lambda e: (-e[0], norm_key(e[1]), e[4]))
            body.append(f"## {title}: {label} ({len(sel)})")
            body.append("")
            show_id = kind in ("item", "station")
            body.append("| uses | English | current " + f + " | tr |" + (" id |" if show_id else ""))
            body.append("|---:|---|---|---|" + ("---|" if show_id else ""))
            for uses_n, en, cur, tier, key in sel:
                body.append(f"| {uses_n} | {md(en)} | {md(cur if tier != 'missing' else '')} | {tier} |"
                            + (f" `{md(key)}` |" if show_id else ""))
            body.append("")
    notes = sorted(builder.note_rows.get(f, {}).values(), key=lambda r: (-r["uses"], norm_key(r["en"])))
    n_miss = [r for r in notes if r["how"] == "missing"]
    summary.append(f"| Recipe notes (input / by-product, free text) | {len(notes)} | {len(n_miss)} | "
                   f"{len(notes) - len(n_miss)} | 0 |")
    L += ["| kind | total | missing | machine | guess |", "|---|---:|---:|---:|---:|"] + summary + [""]
    L += body
    if notes:
        by_how = defaultdict(int)
        for r in notes:
            by_how[r["how"]] += 1
        L.append(f"## Recipe notes ({len(notes)}: {by_how['text']} from a text map, {by_how['pattern']} by pattern, "
                 f"{by_how['partial']} by pattern with an English name left, {by_how['missing']} untranslated)")
        L.append("")
        L.append("Literal notes go in a names file's `__notes` map (`{\"<English note>\": \"<pt>\"}`); recurring "
                 "shapes (`N% chance with X`, `N, or M with X`, `N (M with X)`, `+N each with X`, `N with X`, "
                 "`with X`) are translated by `translate_note_pt`, with X looked up in the names layers.")
        L.append("")
        L.append(f"| uses | English | {f} | how | names not found |")
        L.append("|---:|---|---|---|---|")
        for r in notes:
            L.append(f"| {r['uses']} | {md(r['en'])} | {md(r['loc'] if r['how'] != 'missing' else '')} | {r['how']} "
                     f"| {md(', '.join(r['unresolved']))} |")
        L.append("")
    unused = t.unused()
    L.append(f"## Names-file entries that matched nothing ({len(unused)})")
    L.append("")
    if unused:
        L.append("Possible typos or names not in the dataset (check spelling/case of the English key).")
        L.append("")
        L.append("| file | English key | " + f + " | tr |")
        L.append("|---|---|---|---|")
        for fname, key, pt, tier in unused[:500]:
            L.append(f"| {md(fname)} | {md(key)} | {md(pt)} | {tier} |")
        if len(unused) > 500:
            L.append(f"| ... | {len(unused) - 500} more | | |")
    else:
        L.append("_none_")
    L.append("")
    return "\n".join(L)


def build_report(builder, ds, rep, args_summary):
    c = ds["meta"]["counts"]
    L = ["# Build report", "", f"Built {ds['meta']['built']} (schema {ds['meta']['schema']}). "
         f"Result: **{rep.summary_line()}**.", "", "## Inputs", ""]
    L += [f"- {k}: `{v}`" for k, v in args_summary]
    L += ["", "## Counts", "", "| what | count |", "|---|---:|"]
    for k, v in c.items():
        if isinstance(v, dict):
            v = ", ".join(f"{kk} {vv}" for kk, vv in v.items())
        L.append(f"| {k} | {v} |")
    kinds = defaultdict(int)
    for it in ds["items"].values():
        kinds[it["kind"]] += 1
    types = defaultdict(int)
    for r in ds["recipes"]:
        types[r["type"]] += 1
    L.append(f"| items by kind | {', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))} |")
    L.append(f"| recipes by type | {', '.join(f'{k} {v}' for k, v in sorted(types.items(), key=lambda x: str(x[0])))} |")
    L.append(f"| unlisted recipes | {sum(1 for r in ds['recipes'] if not r['listed'])} |")
    L.append(f"| unobtainable items | {sum(1 for i in ds['items'].values() if i['unobtainable'])} |")
    L.append(f"| items with defaultRecipe | {sum(1 for i in ds['items'].values() if i['defaultRecipe'])} |")
    L.append(f"| obtain texts translated | {sum(1 for i in ds['items'].values() if i['obtain'] and any(i['obtain'][t.field] != i['obtain']['en'] for t in builder.langs))} / {sum(1 for i in ds['items'].values() if i['obtain'])} |")
    L += ["", "## Notes", ""]
    L += [f"- {n}" for n in builder.log.notes] or ["_none_"]
    L += ["", "## Input coercions", "",
          "Things build.py had to fix or interpret in the inputs (count, examples).", ""]
    if builder.log.counts:
        L += ["| coercion | count | examples |", "|---|---:|---|"]
        for k in sorted(builder.log.counts):
            L.append(f"| {md(k)} | {builder.log.counts[k]} | {md('; '.join(builder.log.examples[k]))} |")
    else:
        L.append("_none_")
    L += ["", "## Cycles", ""]
    if rep.cycles:
        L.append("Strongly connected components of the item graph (item -> inputs of its expandable recipes). "
                 "`trapped` = items whose every expandable recipe feeds back into the cycle.")
        L.append("")
        L += ["| # | size | items | example path | recipes | trapped |", "|---:|---:|---|---|---|---|"]
        for n, cy in enumerate(rep.cycles, 1):
            L.append(f"| {n} | {len(cy['items'])} | {md(', '.join(cy['items']))} | {md(' -> '.join(cy['path']))} "
                     f"| {md(', '.join(cy['recipes']))} | {md(', '.join(cy['trapped']))} |")
    else:
        L.append("_none_")
    L += ["", "# Validation", "", rep.to_markdown(heading_level=2)]
    return "\n".join(L)


# --------------------------------------------------------------------------- IO

def write_if_changed(path, text):
    path = Path(path)
    data = text.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return True


def dumps_min(ds):
    s = json.dumps(ds, ensure_ascii=False, separators=(",", ":"))
    # Safe inside <script>: "<" only occurs inside JSON strings, so \u003c keeps it valid JSON
    # and prevents "</script>" / "<!--" from terminating the block.
    return s.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


SCRIPT_RE = re.compile(
    r"(<script\b(?=[^>]*\bid\s*=\s*([\"'])gk2-data\2)[^>]*>)(.*?)(</script\s*>)",
    re.IGNORECASE | re.DOTALL)


def fill_data(html, payload, where):
    """html with the content of its single <script id="gk2-data" ...> replaced by payload (SystemExit(2) otherwise)."""
    matches = list(SCRIPT_RE.finditer(html))
    if len(matches) != 1:
        raise SystemExit(_die(f"--inject: expected exactly one <script id=\"gk2-data\"> in {where}, "
                              f"found {len(matches)}"))
    m = matches[0]
    if "application/json" not in m.group(1).lower():
        print(f"build: warning: gk2-data script tag in {where} has no type=\"application/json\"", file=sys.stderr)
    return html[:m.start(3)] + payload + html[m.end(3):]


def inject(html_path, out_path, payload, artifact=False):
    """Replace the content of <script id="gk2-data" ...> with payload. Returns (changed, out_path).
    artifact=True also strips the document skeleton and writes <out>/preview.html (skeleton re-added)."""
    src = Path(html_path)
    try:
        html = src.read_text(encoding="utf-8")
    except OSError as e:
        raise SystemExit(_die(f"--inject: cannot read {src}: {e}"))
    new = fill_data(html, payload, src)
    dst = Path(out_path) if out_path else src
    if artifact:
        if dst.resolve() == src.resolve():
            raise SystemExit(_die("--artifact needs --out (the source page keeps its skeleton for local dev)"))
        new = artifact_page(new)
        write_if_changed(dst.with_name("preview.html"), preview_page(new))
    if dst.exists() and dst.read_text(encoding="utf-8") == new:
        return False, dst
    if dst.resolve() == src.resolve():
        shutil.copy2(src, src.with_name(src.name + ".bak"))
    write_if_changed(dst, new)
    return True, dst


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


def data_versions(name_paths):
    """{"wiki": "1.010", "game": "1.011"}: the game version of the wiki data and of the official texts."""
    game = None
    for p in name_paths:
        try:
            m = json.loads(Path(p).read_text(encoding="utf-8")).get("_meta") or {}
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(m, dict) and isinstance(m.get("game_version"), str) and m["game_version"].strip():
            game = m["game_version"].strip()
            break
    return {"wiki": WIKI_GAME_VERSION, "game": game or GAME_TEXT_VERSION}


def page_payload(ds, sprite=None, artifact=False, version=None, changelog=None, techs=None, data=None, days=None,
                 game_version=None):
    """The JSON embedded in the page: gk2.min.json minus redundancy.

    - {pt, en} pairs with identical text collapse to one string (obtain texts, notes, zones...).
    - items[].id is dropped (it is the key).
    - with a sprite: meta.sprite carries it; icons are drawn from it.
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
        out["meta"]["sprite"] = dict(sprite, icons=icons)
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


# Skeleton tags the Artifact wrapper supplies itself. Only removed outside <script>/<style>.
SKELETON_RE = re.compile(
    r"<!doctype[^>]*>\s*|</?html\b[^>]*>\s*|</?head\b[^>]*>\s*|</?body\b[^>]*>\s*"
    r"|<meta\s+charset\s*=[^>]*>\s*|<meta\s+name\s*=\s*([\"'])viewport\1[^>]*>\s*",
    re.IGNORECASE)
RAWTEXT_RE = re.compile(r"<(script|style)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)


def strip_skeleton(html):
    """Remove doctype/html/head/body tags and the charset/viewport metas, keep everything else in order."""
    out, pos = [], 0
    for m in RAWTEXT_RE.finditer(html):
        out.append(SKELETON_RE.sub("", html[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(SKELETON_RE.sub("", html[pos:]))
    return "".join(out).lstrip()


PREVIEW_HEAD = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '<!-- local preview only: same content as index.html inside the skeleton the Artifact wrapper adds -->\n'
                '</head>\n<body>\n')


def artifact_page(html):
    out = strip_skeleton(html)
    if not out.startswith("<title"):
        print("build: warning: artifact page does not start with <title>", file=sys.stderr)
    return out


def preview_page(artifact_html):
    return PREVIEW_HEAD + artifact_html + "\n</body>\n</html>\n"


# --------------------------------------------------------------------------- page from src/

MARKERS = {"css": "<!-- @css -->", "js": "<!-- @js -->", "data": "<!-- @data -->"}


def load_manifest(src_dir):
    src = Path(src_dir)
    mp = src / "manifest.json"
    try:
        man = json.loads(mp.read_text(encoding="utf-8"))
    except OSError as e:
        raise SystemExit(_die(f"--src: cannot read {mp}: {e}"))
    except ValueError as e:
        raise SystemExit(_die(f"--src: invalid JSON in {mp}: {e}"))
    if not (isinstance(man, dict) and all(isinstance(man.get(k), list) and all(isinstance(x, str) for x in man[k])
                                          for k in ("css", "js"))):
        raise SystemExit(_die(f"--src: {mp} needs \"css\": [paths] and \"js\": [paths] (relative to {src})"))
    return man


def assemble(src_dir, payload=None, warn=True):
    """src/index.html with the data block filled (payload; None keeps the <!-- @data --> marker) and
    <!-- @css --> / <!-- @js --> replaced by the manifest's files, concatenated in order.
    The data goes in first, so text in the sources can never be mistaken for the data block."""
    src = Path(src_dir)
    man = load_manifest(src)
    tpl_path = src / man.get("template", "index.html")
    try:
        html = tpl_path.read_text(encoding="utf-8")
    except OSError as e:
        raise SystemExit(_die(f"--src: cannot read template {tpl_path}: {e}"))
    for k, mk in MARKERS.items():
        if html.count(mk) != 1:
            raise SystemExit(_die(f"--src: template {tpl_path.name} must contain {mk} exactly once "
                                  f"(found {html.count(mk)})"))
    seen = set()

    def part(kind, closer):
        chunks = []
        for f in man[kind]:
            fp = src / f
            if f in seen:
                raise SystemExit(_die(f"--src: {f} is listed twice in manifest.json"))
            seen.add(f)
            try:
                text = fp.read_text(encoding="utf-8")
            except OSError as e:
                raise SystemExit(_die(f"--src: manifest entry {f}: {e}"))
            if closer in text.lower():
                raise SystemExit(_die(f"--src: {f} contains \"{closer}\", which would end the page's <{closer[2:]}> block"))
            chunks.append(f"/* ==== src/{f} ==== */\n" + text.rstrip("\n") + "\n")
        return "\n".join(chunks)

    css = part("css", "</style")
    js = part("js", "</script")
    if warn:
        listed = {(src / f).resolve() for f in seen}
        for ext in ("css", "js"):
            for fp in sorted(src.rglob("*." + ext)):
                if fp.resolve() not in listed:
                    print(f"build: warning: {fp.relative_to(src)} is not in {src.name}/manifest.json (not built)",
                          file=sys.stderr)
    if payload is not None:
        html = fill_data(html, payload, tpl_path)
    # markers are replaced via a function, so backslashes / group refs in the sources stay literal
    html = re.sub(re.escape(MARKERS["css"]), lambda m: "<style>\n" + css + "</style>", html, count=1)
    html = re.sub(re.escape(MARKERS["js"]), lambda m: '<script>\n"use strict";\n' + js + "</script>", html, count=1)
    return html


# --------------------------------------------------------------------------- version + changelog

DATE_RE = re.compile(r"^\d{4}-\d\d-\d\d$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?$")


def load_version(root):
    """The VERSION file of the project root (one line, semver), or None when absent."""
    vp = Path(root) / "VERSION"
    if not vp.exists():
        return None
    v = vp.read_text(encoding="utf-8").strip()
    if not VERSION_RE.match(v):
        raise SystemExit(_die(f"VERSION: {vp} must hold one version like 1.2.0, found {v!r}"))
    return v


def load_changelog(root):
    """data/changelog.json of the project root: [{version, date: YYYY-MM-DD | null, pt: [..], en: [..]}],
    newest first. None when absent; SystemExit(2) when malformed."""
    cp = Path(root) / "data" / "changelog.json"
    if not cp.exists():
        return None
    try:
        cl = json.loads(cp.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(_die(f"changelog: invalid JSON in {cp}: {e}"))
    ok = isinstance(cl, list) and cl
    for e in cl if ok else []:
        ok = ok and isinstance(e, dict) and isinstance(e.get("version"), str) and VERSION_RE.match(e["version"]) \
            and (e.get("date") is None or (isinstance(e["date"], str) and DATE_RE.match(e["date"]))) \
            and all(isinstance(e.get(l), list) and all(isinstance(x, str) for x in e[l]) for l in ("pt", "en"))
    if not ok:
        raise SystemExit(_die(f"changelog: {cp} must be a non-empty list of "
                              "{version: \"1.2.0\", date: \"YYYY-MM-DD\" | null, pt: [text], en: [text]}"))
    versions = [e["version"] for e in cl]
    if len(set(versions)) != len(versions):
        raise SystemExit(_die(f"changelog: duplicate version in {cp}"))
    return cl


def load_game_version(root):
    """data/game-version.json of the project root: {latest: "1.011", date, note: {pt, en}} (the newest game version
    out there; the page warns when it is newer than the wiki recipes), or None when absent. Bad file: exit 2."""
    gp = Path(root) / "data" / "game-version.json"
    if not gp.exists():
        return None
    try:
        doc = json.loads(gp.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(_die(f"game-version: cannot read {gp}: {e}"))
    if not (isinstance(doc, dict) and isinstance(doc.get("latest"), str) and re.match(r"^\d+(\.\d+)*$", doc["latest"])):
        raise SystemExit(_die(f"game-version: {gp} needs {{\"latest\": \"1.011\", ...}}"))
    note = doc.get("note") if isinstance(doc.get("note"), dict) else {}
    return {"latest": doc["latest"], "date": doc.get("date") if isinstance(doc.get("date"), str) else None,
            "note": {k: v for k, v in note.items() if isinstance(v, str) and v.strip()}}


def changelog_json(cl):
    return json.dumps(cl, ensure_ascii=False, indent=2) + "\n"


def changelog_md(cl):
    """CHANGELOG.md text: pt first, en below. Generated, never edited by hand."""
    L = ["<!-- Gerado por scripts/build.py a partir de data/changelog.json. Não edite à mão. -->",
         "<!-- Generated by scripts/build.py from data/changelog.json. Do not edit by hand. -->", ""]
    for lang, title, unreleased in (("pt", "Histórico de atualizações — Companheiro GK2", "em desenvolvimento"),
                                    ("en", "Update history — GK2 Companion", "in development")):
        if lang == "en":
            L += ["---", ""]
        L += [f"# {title}", ""]
        for e in cl:
            L += [f"## {e['version']} — {e['date'] or unreleased}", ""]
            L += [f"- {x}" for x in e[lang]] or ["-"]
            L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def rel(p):
    p = Path(p).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return p.name


def built_date(arg):
    if arg:
        return arg
    sde = os.environ.get("SOURCE_DATE_EPOCH")
    if sde and sde.isdigit():
        return _dt.datetime.fromtimestamp(int(sde), _dt.timezone.utc).date().isoformat()
    return _dt.datetime.now(_dt.timezone.utc).date().isoformat()


# --------------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge GK2 items/recipes/names into data/gk2.json and validate.")
    ap.add_argument("--items", default=str(DATA / "items.en.json"))
    ap.add_argument("--recipes", default=str(DATA / "recipes.en.json"))
    ap.add_argument("--names", action="append", default=None, metavar="PATH",
                    help="pt names layer(s), repeatable, best first "
                         "(default: data/names.official.pt-BR.json data/names.pt-BR.json data/names.machine.pt-BR.json). "
                         "A file whose name contains '.machine.' is treated as the machine layer.")
    ap.add_argument("--lang", action="append", default=[], metavar="FIELD=PATH[,PATH]",
                    help="extra language, e.g. es=data/names.es.json (output field `es`, `tr_es`)")
    ap.add_argument("--out-dir", default=str(DATA), help="where gk2.json, gk2.min.json and reports go")
    ap.add_argument("--inject", metavar="HTML", help="embed gk2.min.json into <script id=\"gk2-data\">")
    ap.add_argument("--out", metavar="PATH", help="with --inject: output HTML (default: in place + .bak)")
    ap.add_argument("--allow-errors", action="store_true",
                    help="write gk2.json / inject even with hard errors (exit code stays 1)")
    ap.add_argument("--built", help="override meta.built (default: SOURCE_DATE_EPOCH or today, UTC)")
    ap.add_argument("--source", action="append", default=[], help="extra meta.sources entry")
    ap.add_argument("--artifact", action="store_true",
                    help="with --inject and --out: Claude Artifact page (no doctype/html/head/body, no "
                         "charset/viewport metas, no remote icon URLs) + preview.html next to it")
    ap.add_argument("--sprite", metavar="PATH.json",
                    help="icon sprite manifest (scripts/make_sprite.py) embedded as meta.sprite")
    ap.add_argument("--techs", metavar="PATH.json",
                    help="technology tree (scripts/build_techs.py): recipe tech names follow it and the page embeds "
                         "it as `techs` (default: data/techs.json in src mode or with the default --items/--recipes)")
    ap.add_argument("--no-techs", action="store_true", help="ignore data/techs.json")
    ap.add_argument("--days", metavar="PATH.json",
                    help="the 6-day week (scripts/build_days.py) embedded in the page as `days` (default: "
                         "data/days.json when it exists, in src mode or with the default --items/--recipes)")
    ap.add_argument("--no-days", action="store_true", help="ignore data/days.json")
    ap.add_argument("--src", metavar="DIR",
                    help="assemble the page from DIR (manifest.json, index.html, css/, js/) and write "
                         "DIR/../prototype/index.html, DIR/../dist/index.html and DIR/../dist/preview.html "
                         "(default: src/ when src/manifest.json exists and --inject is not given)")
    ap.add_argument("--no-src", action="store_true", help="data only: do not build the page from src/")
    ap.add_argument("--release", action="store_true",
                    help="set the date of the top data/changelog.json entry to the build date when it is null")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    if args.artifact and not (args.inject and args.out):
        ap.error("--artifact needs --inject HTML --out PATH")
    if args.src and (args.inject or args.no_src):
        ap.error("--src cannot be combined with --inject or --no-src")
    if args.techs and args.no_techs:
        ap.error("--techs cannot be combined with --no-techs")
    if args.days and args.no_days:
        ap.error("--days cannot be combined with --no-days")
    if args.src is None and not args.inject and not args.no_src and (ROOT / "src" / "manifest.json").exists():
        args.src = str(ROOT / "src")
    # the project root holds VERSION, data/changelog.json and CHANGELOG.md (src/.. in src mode)
    proj = Path(args.src).resolve().parent if args.src else ROOT
    version, changelog = load_version(proj), load_changelog(proj)
    game_version = load_game_version(proj)
    if args.release:
        if changelog is None:
            ap.error(f"--release needs {proj / 'data' / 'changelog.json'}")
        if version is not None and changelog[0]["version"] != version:
            raise SystemExit(_die(f"--release: VERSION is {version} but the top changelog entry is "
                                  f"{changelog[0]['version']}"))
    if version and changelog and changelog[0]["version"] != version:
        print(f"build: warning: VERSION {version} differs from the top changelog entry {changelog[0]['version']}",
              file=sys.stderr)
    if args.src:
        assemble(args.src)   # fail fast on a broken src/ before the data build

    log = Log()
    raw_items = as_list(load_json(args.items, "items", log), "items", log, ("items", "data"))
    raw_recipes = as_list(load_json(args.recipes, "recipes", log), "recipes", log, ("recipes", "data"))
    names = args.names or [str(DATA / "names.official.pt-BR.json"), str(DATA / "names.pt-BR.json"),
                           str(DATA / "names.machine.pt-BR.json")]
    specs = ["pt=" + ",".join(names)] + list(args.lang)
    langs = parse_lang_specs(specs, log)

    b = Builder(raw_items, raw_recipes, langs, log, extra_sources=args.source).run()
    built = built_date(args.built)
    ds = b.dataset(built)
    rep = validate.validate(ds, pre_issues=b.pre)
    ds = b.dataset(built, rep)
    # technology tree: explicit --techs, else the project's data/techs.json (src mode, or the default inputs)
    techs_path = None
    if args.techs:
        techs_path = Path(args.techs)
    elif not args.no_techs:
        default_inputs = args.items == ap.get_default("items") and args.recipes == ap.get_default("recipes")
        cand = proj / "data" / "techs.json" if args.src else (DATA / "techs.json" if default_inputs else None)
        techs_path = cand if cand is not None and cand.exists() else None
    techs = load_techs(techs_path) if techs_path else None
    if techs is not None:
        renamed = apply_tech_names(ds, techs)
        if not args.quiet:
            print(f"build: techs {rel(techs_path)} ({len(techs['techs'])} technologies; "
                  f"{renamed} recipe tech name(s) aligned)")
    # the week (Dias screen): explicit --days, else the project's data/days.json when present (absent: no `days`)
    days_path = None
    if args.days:
        days_path = Path(args.days)
    elif not args.no_days:
        default_inputs = args.items == ap.get_default("items") and args.recipes == ap.get_default("recipes")
        cand = proj / "data" / "days.json" if args.src else (DATA / "days.json" if default_inputs else None)
        days_path = cand if cand is not None and cand.exists() else None
    days = load_days(days_path) if days_path else None
    if days is not None and not args.quiet:
        print(f"build: days {rel(days_path)} ({len(days['days'])} days, "
              f"{sum(len(d.get('events') or []) for d in days['days'])} events)")

    # item facts (where to get it, energy / buff, stack): the project's data/facts.json when present
    facts_path = proj / "data" / "facts.json" if args.src else DATA / "facts.json"
    if (args.src or (args.items == ap.get_default("items") and args.recipes == ap.get_default("recipes"))) \
            and facts_path.exists():
        n = apply_facts(ds, facts_path)
        if not args.quiet:
            print(f"build: facts {rel(facts_path)} ({n} items)")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = [("items", rel(args.items)), ("recipes", rel(args.recipes))]
    for t in langs:
        for layer in t.layers:
            state = "machine layer" if layer.machine else "sourced layer"
            if not layer.names and not layer.texts:
                state += ", missing or empty"
            summary.append((f"names[{t.field}]", f"{rel(layer.path)} ({state}, {len(layer.names)} names, "
                                                 f"{len(layer.texts)} texts)"))
    written = []
    if write_if_changed(out_dir / "report-build.md", build_report(b, ds, rep, summary)):
        written.append("report-build.md")
    for i, t in enumerate(langs):
        name = "report-l10n.md" if i == 0 else f"report-l10n.{t.field}.md"
        if write_if_changed(out_dir / name, l10n_report(b, ds, i)):
            written.append(name)

    ok_to_write = not rep.errors or args.allow_errors
    if ok_to_write and args.release and changelog[0]["date"] is None:
        changelog[0]["date"] = built
        if write_if_changed(proj / "data" / "changelog.json", changelog_json(changelog)):
            written.append(rel(proj / "data" / "changelog.json"))
        if not args.quiet:
            print(f"build: release {changelog[0]['version']} dated {built}")
    if changelog is not None and write_if_changed(proj / "CHANGELOG.md", changelog_md(changelog)):
        written.append(rel(proj / "CHANGELOG.md"))
    if ok_to_write:
        pretty = json.dumps(ds, ensure_ascii=False, indent=1) + "\n"
        mini = dumps_min(ds)
        if write_if_changed(out_dir / "gk2.json", pretty):
            written.append("gk2.json")
        if write_if_changed(out_dir / "gk2.min.json", mini + "\n"):
            written.append("gk2.min.json")
        if args.src:
            sprite_path = args.sprite or (proj / "data" / "sprite.json" if (proj / "data" / "sprite.json").exists() else None)
            sprite = load_sprite(sprite_path) if sprite_path else None
            pages = []
            for artifact in (False, True):
                payload = dumps_min(page_payload(ds, sprite=sprite, artifact=artifact, version=version,
                                                 changelog=changelog, techs=techs, data=data_versions(names),
                                                 days=days, game_version=game_version))
                html = assemble(args.src, payload, warn=False)
                if artifact:
                    html = artifact_page(html)
                    pages += [(proj / "dist" / "index.html", html), (proj / "dist" / "preview.html", preview_page(html))]
                else:
                    pages.append((proj / "prototype" / "index.html", html))
            for dst, html in pages:
                if write_if_changed(dst, html):
                    written.append(rel(dst))
                if not args.quiet:
                    size = dst.stat().st_size
                    print(f"build: page {rel(dst)} = {size:,} bytes ({size / 1048576:.2f} MB)")
        if args.inject:
            sprite = load_sprite(args.sprite) if args.sprite else None
            payload = dumps_min(page_payload(ds, sprite=sprite, artifact=args.artifact, version=version,
                                             changelog=changelog, techs=techs if args.techs else None,
                                             data=data_versions(names), days=days if args.days else None))
            changed, dst = inject(args.inject, args.out, payload, artifact=args.artifact)
            if changed:
                written.append(str(dst))
            if not args.quiet:
                size = dst.stat().st_size
                print(f"build: page {rel(dst)} = {size:,} bytes ({size / 1048576:.2f} MB; data {len(payload):,} bytes"
                      f"{', sprite ' + format(len(sprite['image']), ',') + ' bytes' if sprite else ''})")
    if not args.quiet:
        c = ds["meta"]["counts"]
        print(f"build: {c['items']} items, {c['recipes']} recipes, {c['stations']} stations; "
              f"tr {c['tr']}; {rep.summary_line()}")
        print(f"build: wrote {', '.join(written) if written else 'nothing (all outputs up to date)'}")
    # errors always go to stderr, even with --quiet
    if not ok_to_write:
        print("build: hard errors, gk2.json NOT written (see report-build.md; --allow-errors to force)",
              file=sys.stderr)
    for e in rep.errors[:20]:
        print(f"  error [{e.code}] {e.message}", file=sys.stderr)
    if len(rep.errors) > 20:
        print(f"  ... {len(rep.errors) - 20} more errors", file=sys.stderr)
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
