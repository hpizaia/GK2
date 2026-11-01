"""The Markdown reports: data/report-l10n.md (localisation gaps) and data/report-build.md."""
from collections import defaultdict

from build_parts.common import norm_key


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
