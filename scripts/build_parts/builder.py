"""The Builder: raw items / recipes + names layers -> the dataset of data/gk2.json (ids, stations, default recipes,
pt names, notes)."""
import re
from collections import defaultdict
from pathlib import Path

from build_parts.common import (BASE_LANG, NOEXP_TYPES, SCHEMA_VERSION, TIER_RANK, TIERS, TYPE_RANK, Layer, norm_key,
                                parse_qty, slugify, source_host, text_or_none, validate)
from build_parts.grades import apply_bonuses, apply_grades
from build_parts.notes import translate_note_pt


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
        apply_grades(self.items, recipes)
        self.perks = apply_bonuses(recipes)
        return self

    # ---- derived pt names (quality grades, "A or B" groups, "Any X", "Open (X)", "Repair (X)" -> "Consertar (X)")
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
            pt, tier, _ = t.name(en)   # also marks the key as looked up (a part only is not "unused")
            return pt if tier in self.DERIVED_TIERS else None

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
                        # "Consertar", as every concrete repair of the game ("Consertar Casa", "Consertar ponte") and
                        # the wiki PT; "Reparar" is only the generic button
                        pt = ("Abrir" if m.group(1) == "Open" else "Consertar") + f" ({x})"
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
            nm, tiers = self.loc(rname, "recipe", rname)
            # a name composed by us (data/names.manual.pt-BR.json `derived`, guess) or machine-made carries its
            # tier, so the page can show the "não oficial" badge next to it
            tier = tiers.get(self.langs[0].field) if self.langs else None
            if tier in ("guess", "machine"):
                nm = dict(nm, tr=tier)
            nr["name"] = nm
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
            "perks": self.perks,
        }

