#!/usr/bin/env python3
"""Build the GK2 crafting-planner dataset.

Reads   data/items.en.json, data/recipes.en.json and the translation layers
        (data/names.official.pt-BR.json, data/names.manual.pt-BR.json, data/names.machine.pt-BR.json; all optional;
        scripts/name_layers.py),
writes  data/gk2.json, data/report-l10n.md, data/report-build.md
and builds the page (unless --no-src): assembles src/index.html + src/css/* + src/js/* in manifest order, embeds
the data and writes prototype/index.html (dev, with the document skeleton), dist/index.html (Claude Artifact, no
skeleton) and dist/preview.html. The page embeds VERSION and data/changelog.json as meta.version / meta.changelog,
and CHANGELOG.md is regenerated from data/changelog.json on every build (--release dates an unreleased top entry).
meta.built defaults to the date of the last release in data/changelog.json, so a rebuild on another day writes
nothing; --release uses today.

Python 3 stdlib only. Run with:  python3 -I scripts/build.py [options]
See scripts/README-build.md for the schema and options.

The code lives in scripts/build_parts/ (one module per subject, see its __init__.py); this file is the command line
and re-exports every name, so `build.<name>` keeps working for the tests and the other scripts.

Exit codes: 0 ok (warnings allowed), 1 hard validation errors, 2 usage / IO error.
"""
import argparse
import datetime as _dt  # noqa: F401  (re-exported, as before the split)
import importlib.util  # noqa: F401
import json
import os  # noqa: F401
import re  # noqa: F401
import sys
import unicodedata  # noqa: F401
from collections import defaultdict  # noqa: F401
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__

HERE = Path(__file__).resolve().parent
# `python3 -I` does not put the script dir on sys.path: build_parts/ and name_layers.py live next to this file
sys.path.insert(0, str(HERE))

# Every module-level name of the build, re-exported: other scripts and the tests use build.<name>.
from build_parts.common import (  # noqa: E402,F401
    BASE_LANG, DATA, GAME_TEXT_VERSION, NOEXP_TYPES, ROOT, SCHEMA_VERSION, TIER_RANK, TIERS, TYPE_PREF, TYPE_RANK,
    Layer, Log, Translator, _die, _load_validate, as_list, default_pt, load_json, norm_key, parse_lang_specs,
    parse_qty, rel, slugify, source_host, text_or_none, validate, write_if_changed)
from build_parts.notes import (  # noqa: E402,F401
    _NUM, BONUS_SHAPES, NOTE_PATTERNS_PT, NOTE_SHAPES, _pt_shape, note_bonus, perk_slug, translate_note_pt)
from build_parts.builder import Builder  # noqa: E402,F401
from build_parts.grades import (  # noqa: E402,F401
    _FROM_ANY, _GRADE_AT_END, _GRADE_IN_NAME, GRADE_SUFFIX, apply_bonuses, apply_grades, page_norm)
from build_parts.reports import build_report, l10n_report, md, usage_counts  # noqa: E402,F401
from build_parts.payload import (  # noqa: E402,F401
    DAYS_DROP, ITEM_DEFAULTS, RECIPE_DEFAULTS, SPRITE_NS, STATION_DEFAULTS, _drop_nulls, apply_facts, apply_tech_names,
    collapse_loc, data_versions, day_sprite_ids, days_payload, drop_defaults, load_days, load_sprite, load_techs,
    page_payload, techs_payload)
from build_parts.page import (  # noqa: E402,F401
    MARKERS, PREVIEW_HEAD, RAWTEXT_RE, SCRIPT_RE, SKELETON_RE, artifact_page, assemble, dumps_min, fill_data,
    load_manifest, preview_page, strip_skeleton)
from build_parts.versions import (  # noqa: E402,F401
    DATE_RE, VERSION_RE, built_date, changelog_json, changelog_md, load_changelog, load_game_version, load_version,
    load_wiki_version)


# --------------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge GK2 items/recipes/names into data/gk2.json and validate.")
    ap.add_argument("--items", default=str(DATA / "items.en.json"))
    ap.add_argument("--recipes", default=str(DATA / "recipes.en.json"))
    ap.add_argument("--names", action="append", default=None, metavar="PATH",
                    help="pt names layer(s), repeatable, best first "
                         "(default: data/names.official.pt-BR.json data/names.manual.pt-BR.json "
                         "data/names.machine.pt-BR.json). "
                         "A file whose name contains '.machine.' is treated as the machine layer.")
    ap.add_argument("--lang", action="append", default=[], metavar="FIELD=PATH[,PATH]",
                    help="extra language, e.g. es=data/names.es.json (output field `es`, `tr_es`)")
    ap.add_argument("--out-dir", default=str(DATA), help="where gk2.json and the reports go")
    ap.add_argument("--allow-errors", action="store_true",
                    help="write gk2.json and the page even with hard errors (exit code stays 1)")
    ap.add_argument("--built", help="override meta.built (default: SOURCE_DATE_EPOCH, else the date of the last "
                                    "release in data/changelog.json, else today, UTC; with --release: today)")
    ap.add_argument("--source", action="append", default=[], help="extra meta.sources entry")
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
                         "(default: src/ when src/manifest.json exists)")
    ap.add_argument("--no-src", action="store_true", help="data only: do not build the page from src/")
    ap.add_argument("--release", action="store_true",
                    help="set the date of the top data/changelog.json entry to the build date when it is null")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    if args.src and args.no_src:
        ap.error("--src cannot be combined with --no-src")
    if args.techs and args.no_techs:
        ap.error("--techs cannot be combined with --no-techs")
    if args.days and args.no_days:
        ap.error("--days cannot be combined with --no-days")
    if args.src is None and not args.no_src and (ROOT / "src" / "manifest.json").exists():
        args.src = str(ROOT / "src")
    # the project root holds VERSION, data/changelog.json and CHANGELOG.md (src/.. in src mode)
    proj = Path(args.src).resolve().parent if args.src else ROOT
    version, changelog = load_version(proj), load_changelog(proj)
    game_version, wiki_version = load_game_version(proj), load_wiki_version(proj)
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
    names = args.names or [str(p) for p in default_pt(DATA)]
    specs = ["pt=" + ",".join(names)] + list(args.lang)
    langs = parse_lang_specs(specs, log)

    b = Builder(raw_items, raw_recipes, langs, log, extra_sources=args.source).run()
    built = built_date(args.built, changelog, args.release)
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
        if write_if_changed(out_dir / "gk2.json", pretty):
            written.append("gk2.json")
        if args.src:
            sprite_path = args.sprite or (proj / "data" / "sprite.json" if (proj / "data" / "sprite.json").exists() else None)
            sprite = load_sprite(sprite_path) if sprite_path else None
            pages = []
            for artifact in (False, True):
                payload = dumps_min(page_payload(ds, sprite=sprite, artifact=artifact, version=version,
                                                 changelog=changelog, techs=techs,
                                                 data=data_versions(names, wiki_version),
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
