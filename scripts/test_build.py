#!/usr/bin/env python3
"""Tests for scripts/build.py and scripts/validate.py.  Run:  python3 -I scripts/test_build.py

Uses scripts/fixtures/* only (outputs go to temp dirs). One extra test runs against the real
data/items.en.json + data/recipes.en.json when they exist (read-only; outputs to a temp dir).
"""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIX = HERE / "fixtures"
BUILD = HERE / "build.py"
VALIDATE = HERE / "validate.py"


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate = load_mod("gk2_validate_t", VALIDATE)
build = load_mod("gk2_build_t", BUILD)


def run(script, *args):
    p = subprocess.run([sys.executable, "-I", str(script), *map(str, args)],
                       capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, p.stdout, p.stderr


def fixture_args(out_dir, items=None, recipes=None, names=None):
    names = names if names is not None else [FIX / "names.pt-BR.json", FIX / "names.machine.pt-BR.json"]
    a = ["--items", items or FIX / "items.en.json", "--recipes", recipes or FIX / "recipes.en.json",
         "--out-dir", out_dir, "--built", "2026-01-01", "--quiet", "--no-src"]
    for n in names:
        a += ["--names", n]
    return a


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def expand_payload(page):
    """Undo build.page_payload (collapsed {pt, en} strings, dropped items[].id), like GK.data does."""
    langs = page["meta"]["langs"]
    loc_keys = {"cat", "obtain", "note", "ext", "zone", "name", "type"}

    def walk(v, key=None):
        if isinstance(v, list):
            return [walk(x, key) for x in v]
        if isinstance(v, dict):
            return {k: walk(x, k) for k, x in v.items()}
        if isinstance(v, str) and key in loc_keys and not (key == "type" and v in TYPES):
            return {l: v for l in langs}
        return v

    TYPES = {"hand_craft", "star_craft", "auto", "factory", "building", "alchemy", "grow",
             "technology", "quest", "perk"}
    out = walk(page)
    for iid, it in out["items"].items():
        it["id"] = iid
    out["meta"].pop("collapsed", None)
    out["meta"].pop("sprite", None)
    out["meta"].pop("version", None)
    out["meta"].pop("changelog", None)
    out["meta"].pop("data", None)
    return out


def extract_block(html):
    m = re.search(r'<script id="gk2-data" type="application/json">(.*?)</script>', html, re.S)
    return m.group(1)


class FixtureBuild(unittest.TestCase):
    """Dirty fixture: one dangling ref (glue) -> hard error; built with --allow-errors."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        shutil.copy(FIX / "page.html", cls.out / "page.html")
        cls.rc, cls.so, cls.se = run(BUILD, *fixture_args(cls.out), "--allow-errors",
                                     "--inject", cls.out / "page.html")
        cls.ds = read_json(cls.out / "gk2.json")
        cls.rep = validate.validate(cls.ds)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exit_code_and_outputs(self):
        self.assertEqual(self.rc, 1, self.se)
        for f in ("gk2.json", "gk2.min.json", "report-l10n.md", "report-build.md", "page.html.bak"):
            self.assertTrue((self.out / f).exists(), f)
        self.assertEqual(read_json(self.out / "gk2.min.json"), self.ds)

    def test_schema_shape(self):
        ds = self.ds
        self.assertEqual(set(ds), {"meta", "items", "stations", "recipes"})
        self.assertEqual(ds["meta"]["built"], "2026-01-01")
        self.assertIn("wikily.gg", ds["meta"]["sources"])
        self.assertNotIn("machine", ds["meta"]["sources"])
        self.assertEqual(ds["meta"]["counts"]["items"], 17)       # 16 + glue stub
        self.assertEqual(ds["meta"]["counts"]["recipes"], 13)
        for iid, it in ds["items"].items():
            self.assertEqual(it["id"], iid)
            for k in ("pt", "en", "cat", "icon", "tr", "raw", "obtain", "kind", "listed", "unobtainable",
                      "recipes", "defaultRecipe"):
                self.assertIn(k, it, (iid, k))
            self.assertIn(it["tr"], ("official", "likely", "guess", "machine", "missing"))
            if it["cat"] is not None:
                self.assertEqual(set(it["cat"]), {"pt", "en"})
        for sid, st in ds["stations"].items():
            self.assertEqual(sid, re.sub(r"[^a-z0-9-]", "", sid))
            self.assertTrue({"pt", "en"} <= set(st))
        for r in ds["recipes"]:
            for k in ("id", "out", "station", "in", "tech", "type", "cd", "listed", "noexp", "cyc", "alt", "ext",
                      "extra", "mastery", "ticks", "energy", "example", "runes", "zone"):
                self.assertIn(k, r, (r["id"], k))

    def test_translation_layers(self):
        it = self.ds["items"]
        self.assertEqual((it["plank"]["pt"], it["plank"]["tr"]), ("Tábua", "official"))     # beats machine "Prancha"
        self.assertEqual((it["nail"]["pt"], it["nail"]["tr"]), ("Prego", "guess"))           # sourced guess > machine
        self.assertEqual(it["beet-seed"]["tr"], "machine")                                    # machine file only
        self.assertEqual(it["fertilizer"]["tr"], "machine")                                   # source "machine" in sourced file
        self.assertEqual((it["iron-ore"]["pt"], it["iron-ore"]["tr"]), ("Minério de ferro", "likely"))  # case-insensitive key
        self.assertEqual(it["simple-coffin"]["tr"], "guess")                                  # bare string value
        self.assertEqual(it["beet"]["tr"], "guess")                                           # unknown confidence
        self.assertEqual((it["iron-ingot"]["pt"], it["iron-ingot"]["tr"]), ("Iron Ingot", "missing"))
        self.assertEqual(it["log"]["cat"], {"pt": "Madeira", "en": "Wood"})
        self.assertEqual(it["nail"]["cat"], {"pt": "Tools", "en": "Tools"})                  # category fallback
        self.assertEqual(it["log"]["obtain"], {"pt": "Cortado de árvores.", "en": "Chopped from trees."})
        self.assertEqual(it["stone"]["obtain"]["en"], "Mined from rocks; Sold by the Mason")  # list joined
        st = self.ds["stations"]
        self.assertEqual(st["smelter"], {"pt": "Smelter", "en": "Smelter", "tr": "missing", "icon": None})
        self.assertEqual(st["workbench"]["pt"], "Bancada")
        self.assertEqual(st["workbench"]["icon"], "https://example.test/workbench.png")
        self.assertIn("steel-anvil", st)                                                      # alt station

    def test_recipes_normalised(self):
        R = {r["id"]: r for r in self.ds["recipes"]}
        self.assertEqual(R["plank"]["out"], {"item": "plank", "qty": 2})
        self.assertEqual(R["iron-ingot-smelter"]["in"], [{"item": "iron-ore", "qty": 3}])     # name ref + "3"
        self.assertEqual(R["iron-ingot-smelter"]["extra"][0]["note"], {"pt": "50% de chance", "en": "50% chance"})
        self.assertEqual(R["nail"]["in"], [{"item": "iron-ingot", "qty": 1}])                 # [item, qty] pair
        self.assertEqual(R["nail"]["alt"], ["steel-anvil"])
        self.assertEqual(R["water-bucket"]["out"], {"item": "water-bucket", "qty": 1})        # string output
        self.assertEqual(R["build-workbench"]["in"], [{"item": "plank", "qty": 5}, {"item": "stone", "qty": 2}])
        self.assertIsNone(R["build-workbench"]["station"])
        self.assertNotIn("name", R["build-workbench"])                                        # "Build <output>"
        self.assertEqual(R["iron-ingot-furnace"]["name"]["en"], "Iron Ingot (Furnace)")
        self.assertEqual(R["wooden-box"]["tech"],
                         {"pt": "Carpintaria", "en": "Carpentry", "id": "carpentry", "type": "technology"})
        self.assertEqual(R["iron-ingot-furnace"]["mastery"], {"type": {"pt": "Smithing", "en": "Smithing"}, "level": 2})
        g = R["grow-beet"]
        self.assertEqual((g["out"]["qty"], g["noexp"]), (None, True))

    def test_default_recipe(self):
        it = self.ds["items"]
        self.assertEqual(it["iron-ingot"]["defaultRecipe"], "iron-ingot-smelter")  # calculator_default beats hand_craft
        self.assertEqual(it["iron-ingot"]["recipes"], ["iron-ingot-smelter", "iron-ingot-furnace"])
        self.assertIsNone(it["beet"]["defaultRecipe"])                             # raw -> leaf; grow never default
        self.assertEqual(it["beet"]["recipes"], ["fertilized-beet", "grow-beet"])
        self.assertEqual(it["beet-seed"]["defaultRecipe"], "beet-seed")            # raw beet is a leaf: no loop
        self.assertEqual(it["fertilizer"]["defaultRecipe"], "fertilizer")
        self.assertEqual(it["water-bucket"]["defaultRecipe"], "water-bucket")      # zero inputs: still a leaf in UI
        self.assertEqual([r["id"] for r in self.ds["recipes"] if r["cyc"]], ["fertilized-beet"])
        self.assertIsNone(it["log"]["defaultRecipe"])
        self.assertTrue(it["rope"]["raw"])                                          # is_raw missing -> computed

    def test_stub_for_dangling_ref(self):
        g = self.ds["items"]["glue"]
        self.assertTrue(g["stub"])
        self.assertEqual((g["tr"], g["raw"]), ("missing", True))

    def test_validation_findings(self):
        self.assertEqual(self.rep.codes("error"), {"stub-item": 1})
        self.assertEqual(self.rep.codes("warning"),
                         {"cycle": 1, "orphan": 2, "raw-with-recipe": 1, "zero-inputs": 1})
        self.assertEqual(self.rep.codes("info"), {"cycle-trapped": 1, "multi-recipe": 2})
        self.assertEqual(self.rep.cycles[0]["trapped"], ["beet"])
        self.assertEqual(len(self.rep.cycles), 1)
        cy = self.rep.cycles[0]
        self.assertEqual(cy["items"], ["beet", "beet-seed", "fertilizer"])
        self.assertEqual(cy["path"][0], cy["path"][-1])
        self.assertNotIn("grow-beet", cy["recipes"])                                # noexp edges ignored
        orphans = sorted(i.refs["item"] for i in self.rep.issues if i.code == "orphan")
        self.assertEqual(orphans, ["ancient-coin", "rope"])
        self.assertEqual(self.ds["meta"]["counts"]["errors"], 1)
        self.assertEqual(self.ds["meta"]["counts"]["cycles"], 1)

    def test_reports(self):
        b = (self.out / "report-build.md").read_text(encoding="utf-8")
        for s in ("stub-item", "beet -> beet-seed -> beet", "duplicate line merged", "ref: English name -> id",
                  "names: bare string value", "qty string -> number"):
            self.assertIn(s, b)
        l = (self.out / "report-l10n.md").read_text(encoding="utf-8")
        missing = l.split("## Items: missing")[1].split("##")[0]
        self.assertLess(missing.index("Iron Ingot"), missing.index("Ancient Coin"))  # 3 uses before 0 uses
        self.assertRegex(missing, r"\| 3 \| Iron Ingot \|")
        review = l.split("## Items: needs review")[1].split("##")[0]
        self.assertLess(review.index("| Beet |"), review.index("| Water Bucket |"))
        self.assertIn("| Smelter |", l)
        self.assertIn("| Tools |", l)                                    # category gap
        self.assertIn("| Smelting |", l)                                  # tech gap
        self.assertNotIn("| Plank |", l)                                  # official -> not a gap
        unused = l.split("matched nothing")[1]
        self.assertIn("Unicorn Horn", unused)
        self.assertNotIn("Prancha", unused)                               # shadowed by better layer != unused

    def test_inject(self):
        html = (self.out / "page.html").read_text(encoding="utf-8")
        block = extract_block(html)
        self.assertNotIn("</script", block.lower())
        self.assertNotIn("<!--", block)
        self.assertEqual(expand_payload(json.loads(block)), self.ds)
        self.assertIn("crypt </script><script>", expand_payload(json.loads(block))["items"]["ancient-coin"]["obtain"]["en"])
        self.assertIn("<main id=\"app\">Planejador</main>", html)
        self.assertIn('{"placeholder": true}', (self.out / "page.html.bak").read_text(encoding="utf-8"))

    def test_idempotent(self):
        files = ["gk2.json", "gk2.min.json", "report-l10n.md", "report-build.md", "page.html", "page.html.bak"]
        before = {f: (self.out / f).read_bytes() for f in files}
        mtimes = {f: (self.out / f).stat().st_mtime_ns for f in files}
        rc, so, se = run(BUILD, *[a for a in fixture_args(self.out) if a != "--quiet"], "--allow-errors",
                         "--inject", self.out / "page.html")
        self.assertEqual(rc, 1)
        self.assertIn("nothing (all outputs up to date)", so)
        for f in files:
            self.assertEqual((self.out / f).read_bytes(), before[f], f)
            self.assertEqual((self.out / f).stat().st_mtime_ns, mtimes[f], f)

    def test_validate_cli(self):
        rc, so, se = run(VALIDATE, self.out / "gk2.json", "--json")
        self.assertEqual(rc, 1)
        d = json.loads(so)
        self.assertEqual(d["errors"], 1)
        self.assertEqual(d["codes"]["cycle"], 1)


class OtherBuilds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def clean_recipes(self):
        rs = read_json(FIX / "recipes.en.json")
        for r in rs:
            if r["id"] == "simple-coffin":
                r["inputs"] = [i for i in r["inputs"] if i["item"] != "glue"]
        p = self.dir / "recipes.clean.json"
        p.write_text(json.dumps(rs), encoding="utf-8")
        return p

    def test_hard_error_blocks_output(self):
        out = self.dir / "out"
        rc, so, se = run(BUILD, *fixture_args(out))
        self.assertEqual(rc, 1)
        self.assertIn("NOT written", se)
        self.assertFalse((out / "gk2.json").exists())
        self.assertTrue((out / "report-build.md").exists())

    def test_clean_build_exit_0_and_inject_out(self):
        out = self.dir / "out"
        page = self.dir / "page.html"
        shutil.copy(FIX / "page.html", page)
        dst = self.dir / "dist" / "index.html"
        rc, so, se = run(BUILD, *fixture_args(out, recipes=self.clean_recipes()), "--inject", page, "--out", dst)
        self.assertEqual(rc, 0, se)
        self.assertEqual(page.read_text(encoding="utf-8"), (FIX / "page.html").read_text(encoding="utf-8"))
        self.assertFalse((self.dir / "page.html.bak").exists())
        page_data = json.loads(extract_block(dst.read_text(encoding="utf-8")))
        self.assertTrue(page_data["meta"]["collapsed"])
        self.assertNotIn("id", next(iter(page_data["items"].values())))
        self.assertEqual(expand_payload(page_data), read_json(out / "gk2.json"))
        self.assertEqual(run(VALIDATE, out / "gk2.json", "--quiet")[0], 0)

    def test_artifact_and_sprite(self):
        out = self.dir / "out"
        page = self.dir / "page.html"
        shutil.copy(FIX / "page.html", page)
        dst = self.dir / "dist" / "index.html"
        ds_ids = read_json(FIX / "items.en.json")
        some_id = ds_ids[0]["id"]
        sprite = self.dir / "sprite.json"
        sprite.write_text(json.dumps({"image": "data:image/png;base64,iVBORw0KGgo=", "size": 32, "cols": 2, "rows": 1,
                                      "icons": {some_id: [1, 0], "not-an-item": [0, 0]}}), encoding="utf-8")
        rc, so, se = run(BUILD, *fixture_args(out, recipes=self.clean_recipes()), "--inject", page, "--out", dst,
                         "--artifact", "--sprite", sprite)
        self.assertEqual(rc, 0, se)
        html = dst.read_text(encoding="utf-8")
        self.assertTrue(html.startswith("<title>"), html[:80])
        for tag in ("<!doctype", "<html", "</html", "<head>", "</head", "<body", "</body", "charset="):
            self.assertNotIn(tag, html.lower())
        self.assertIn('const DATA = JSON.parse(document.getElementById("gk2-data").textContent);', html)
        data = json.loads(extract_block(html))
        self.assertEqual(data["meta"]["sprite"]["icons"], {some_id: [1, 0]})
        self.assertTrue(all(it["icon"] is None for it in data["items"].values()))
        preview = (dst.parent / "preview.html").read_text(encoding="utf-8")
        self.assertTrue(preview.startswith("<!doctype html>"))
        self.assertIn(html, preview)
        # --artifact without --out, and a bad sprite manifest, are usage errors
        self.assertEqual(run(BUILD, *fixture_args(out, recipes=self.clean_recipes()), "--inject", page, "--artifact")[0], 2)
        sprite.write_text("{}", encoding="utf-8")
        self.assertEqual(run(BUILD, *fixture_args(out, recipes=self.clean_recipes()), "--inject", page, "--out", dst,
                             "--sprite", sprite)[0], 2)

    def test_missing_names_files(self):
        out = self.dir / "out"
        rc, so, se = run(BUILD, *fixture_args(out, recipes=self.clean_recipes(),
                                               names=[self.dir / "nope.json", self.dir / "nope.machine.json"]))
        self.assertEqual(rc, 0, se)
        ds = read_json(out / "gk2.json")
        self.assertTrue(all(i["tr"] == "missing" and i["pt"] == i["en"] for i in ds["items"].values()))
        self.assertIn("not found, skipped", (out / "report-build.md").read_text(encoding="utf-8"))

    def test_duplicate_ids(self):
        items = read_json(FIX / "items.en.json")
        items.append(dict(items[0], name="Log again"))
        rs = read_json(self.clean_recipes())
        rs.append(dict(rs[0]))
        ip, rp = self.dir / "items.json", self.dir / "recipes.json"
        ip.write_text(json.dumps(items), encoding="utf-8")
        rp.write_text(json.dumps(rs), encoding="utf-8")
        out = self.dir / "out"
        rc, so, se = run(BUILD, *fixture_args(out, items=ip, recipes=rp), "--allow-errors")
        self.assertEqual(rc, 1)
        self.assertEqual(se.count("[duplicate-id]"), 2)
        ds = read_json(out / "gk2.json")
        self.assertEqual(ds["items"]["log"]["en"], "Log")             # first wins
        self.assertEqual(len(ds["recipes"]), 13)

    def test_extra_language(self):
        es = self.dir / "names.es.json"
        es.write_text(json.dumps({"Plank": {"pt": "Tablón", "source": "x", "confidence": "official"}}),
                      encoding="utf-8")
        out = self.dir / "out"
        rc, so, se = run(BUILD, *fixture_args(out, recipes=self.clean_recipes()), "--lang", f"es={es}")
        self.assertEqual(rc, 0, se)
        ds = read_json(out / "gk2.json")
        self.assertEqual(ds["meta"]["langs"], ["pt", "es", "en"])
        p = ds["items"]["plank"]
        self.assertEqual((p["pt"], p["tr"], p["es"], p["tr_es"]), ("Tábua", "official", "Tablón", "official"))
        self.assertEqual(ds["items"]["log"]["es"], "Log")
        self.assertEqual(ds["stations"]["smelter"]["tr_es"], "missing")
        self.assertTrue((out / "report-l10n.es.md").exists())

    def test_inject_without_tag_fails(self):
        page = self.dir / "bad.html"
        page.write_text("<html><body>no data block</body></html>", encoding="utf-8")
        rc, so, se = run(BUILD, *fixture_args(self.dir / "out", recipes=self.clean_recipes()), "--inject", page)
        self.assertEqual(rc, 2)
        self.assertIn("expected exactly one", se)


class PageHelpers(unittest.TestCase):
    def test_collapse_loc(self):
        langs = {"pt", "en"}
        v = {"a": {"pt": "X", "en": "X"}, "b": {"pt": "X", "en": "Y"}, "t": {"pt": "X", "en": "X", "id": "x"},
             "l": [{"pt": "Z", "en": "Z"}]}
        self.assertEqual(build.collapse_loc(v, langs),
                         {"a": "X", "b": {"pt": "X", "en": "Y"}, "t": {"pt": "X", "en": "X", "id": "x"}, "l": ["Z"]})

    def test_strip_skeleton_keeps_script_text(self):
        html = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width">\n<title>T</title>\n</head>\n<body>\n'
                '<header>h</header>\n<script>const s = "<body></body>";</script>\n</body>\n</html>\n')
        out = build.strip_skeleton(html)
        self.assertTrue(out.startswith("<title>T</title>"))
        self.assertIn("<header>h</header>", out)
        self.assertIn('const s = "<body></body>";', out)
        self.assertNotIn("<html", out)
        self.assertNotIn("viewport", out)


class DerivedNames(unittest.TestCase):
    def test_derived_names_and_game_key(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            items = [
                {"id": "story", "name": "Story", "kind": "virtual"},
                {"id": "story-gold", "name": "Story (gold)", "kind": "quality-variant", "base_item": "story"},
                {"id": "bream", "name": "Bream"}, {"id": "carp", "name": "Carp"},
                {"id": "bream-or-carp", "name": "Bream or Carp", "kind": "group", "group_members": ["bream", "carp"]},
                {"id": "any-story", "name": "Any Story", "kind": "group", "group_members": ["story"]},
                {"id": "old-door", "name": "Old door"},
                {"id": "open-old-door", "name": "Open (Old door)", "kind": "action"},
                {"id": "repair-well", "name": "Repair (Well)", "kind": "action"},
                {"id": "pike", "name": "Pike"},
                {"id": "story-silver", "name": "Story (silver)", "kind": "quality-variant", "base_item": "story"},
            ]
            (d / "items.json").write_text(json.dumps(items), encoding="utf-8")
            (d / "recipes.json").write_text("[]", encoding="utf-8")
            (d / "names.official.pt-BR.json").write_text(json.dumps({
                "_meta": {"unmatched": []},
                "Story": {"pt": "História", "source": "game-files", "confidence": "official", "gameKey": "story"},
                "Bream": {"pt": "Brema", "source": "game-files", "confidence": "official"},
                "Carp": {"pt": "Carpa", "source": "game-files", "confidence": "official"},
                "Old door": {"pt": "Porta Antiga", "source": "game-files", "confidence": "official"},
                "Story (silver)": {"pt": "Conto (prata)", "source": "game-files", "confidence": "official"},
            }), encoding="utf-8")
            (d / "names.machine.pt-BR.json").write_text(json.dumps({
                "Pike": {"pt": "Lúcio", "source": "machine", "confidence": "guess"},
                "Repair (Well)": {"pt": "Consertar (Poço)", "source": "machine", "confidence": "guess"},
            }), encoding="utf-8")
            rc, so, se = run(BUILD, "--items", d / "items.json", "--recipes", d / "recipes.json",
                             "--names", d / "names.official.pt-BR.json", "--names", d / "names.machine.pt-BR.json",
                             "--out-dir", d / "out", "--built", "2026-01-01", "--quiet", "--allow-errors",
                             "--no-src")   # without it the default src mode rewrites the real prototype/ and dist/
            self.assertNotIn("Traceback", se)
            it = read_json(d / "out" / "gk2.json")["items"]
            got = {k: (v["pt"], v["tr"]) for k, v in it.items()}
            self.assertEqual(got["story-gold"], ("História (ouro)", "likely"))
            self.assertEqual(got["story-silver"], ("Conto (prata)", "official"))      # official full name wins
            self.assertEqual(got["bream-or-carp"], ("Brema ou carpa", "likely"))
            self.assertEqual(got["any-story"], ("Qualquer história", "likely"))
            self.assertEqual(got["open-old-door"], ("Abrir (Porta Antiga)", "likely"))
            self.assertEqual(got["repair-well"], ("Consertar (Poço)", "machine"))    # part "Well" not official
            self.assertEqual(got["pike"], ("Lúcio", "machine"))
            self.assertEqual(it["story"].get("key"), "story")
            self.assertNotIn("key", it["pike"])


class NotesAndZones(unittest.TestCase):
    NAMES = {"mason": "Pedreiro", "cremator": "Cremador", "cook ii": "Cozinheiro II", "farmer ii": "Fazendeiro II",
             "grape master": "Senhor das Uvas"}
    TEXTS = {"amount varies with the bed": "a quantidade varia conforme o canteiro", "any quality": "qualquer qualidade"}

    def tr(self, en):
        return build.translate_note_pt(en, lambda s: self.TEXTS.get(s.lower()), lambda s: self.NAMES.get(s.lower()))

    def test_note_patterns(self):
        cases = {
            "50% chance with Mason": "50% de chance com Pedreiro",
            "1, or 2 with Cremator": "1, ou 2 com Cremador",
            "4 (6 with Cook II)": "4 (6 com Cozinheiro II)",
            "4 with Cremator": "4 com Cremador",
            "with Mason": "com Pedreiro",
            "any quality": "qualquer qualidade",
            "amount varies with the bed; +1 each with Farmer II and Grape Master":
                "a quantidade varia conforme o canteiro; +1 cada com Fazendeiro II e Senhor das Uvas",
        }
        for en, pt in cases.items():
            self.assertEqual(self.tr(en), (pt, []), en)

    def test_note_unresolved_and_unknown(self):
        self.assertEqual(self.tr("10% chance with Magpie's Eye"), ("10% de chance com Magpie's Eye", ["Magpie's Eye"]))
        self.assertEqual(self.tr("used up by the burn"), (None, []))
        self.assertEqual(self.tr("any quality; something odd"), (None, []))    # every segment must translate
        self.assertEqual(self.tr(""), (None, []))

    def test_build_notes_and_zone_lists(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            items = [{"id": "stone", "name": "Stone", "is_raw": True}, {"id": "brick", "name": "Brick"},
                     {"id": "dust", "name": "Dust", "is_raw": True}, {"id": "wall", "name": "Wall", "kind": "building"}]
            recipes = [
                {"id": "brick", "output": {"item": "brick", "qty": 1}, "station": "Kiln", "type": "hand_craft",
                 "inputs": [{"item": "stone", "qty": 2, "note": "any quality"}],
                 "extra_outputs": [{"item": "dust", "qty": 1, "note": "50% chance with Mason"},
                                   {"item": "stone", "qty": 1, "note": "used up by the burn"}]},
                {"id": "wall", "output": {"item": "wall", "qty": 1}, "type": "building", "zone": "Yard, Home",
                 "inputs": [{"item": "brick", "qty": 4}]},
                {"id": "wall-2", "output": {"item": "wall", "qty": 1}, "type": "building", "zone": "Yard, Moon",
                 "inputs": [{"item": "brick", "qty": 5}]},
            ]
            (d / "items.json").write_text(json.dumps(items), encoding="utf-8")
            (d / "recipes.json").write_text(json.dumps(recipes), encoding="utf-8")
            (d / "names.official.pt-BR.json").write_text(json.dumps({
                "Yard": {"pt": "Pátio", "source": "game-files", "confidence": "official"},
                "Home": {"pt": "Casa", "source": "game-files", "confidence": "official"},
                "Mason": {"pt": "Pedreiro", "source": "game-files", "confidence": "official"},
            }), encoding="utf-8")
            (d / "names.machine.pt-BR.json").write_text(json.dumps({
                "__notes": {"any quality": "qualquer qualidade"},
            }), encoding="utf-8")
            rc, so, se = run(BUILD, "--items", d / "items.json", "--recipes", d / "recipes.json",
                             "--names", d / "names.official.pt-BR.json", "--names", d / "names.machine.pt-BR.json",
                             "--out-dir", d / "out", "--built", "2026-01-01", "--quiet", "--allow-errors",
                             "--no-src")   # without it the default src mode rewrites the real prototype/ and dist/
            self.assertNotIn("Traceback", se)
            rs = {r["id"]: r for r in read_json(d / "out" / "gk2.json")["recipes"]}
            self.assertEqual(rs["brick"]["in"][0]["note"]["pt"], "qualquer qualidade")
            self.assertEqual(rs["brick"]["extra"][0]["note"]["pt"], "50% de chance com Pedreiro")
            self.assertEqual(rs["brick"]["extra"][1]["note"]["pt"], "used up by the burn")   # left in English
            self.assertEqual(rs["wall"]["zone"]["pt"], "Pátio, Casa")
            self.assertEqual(rs["wall-2"]["zone"]["pt"], "Pátio, Moon")
            rep = (d / "out" / "report-l10n.md").read_text(encoding="utf-8")
            self.assertIn("## Recipe notes (3: 1 from a text map, 1 by pattern, 0 by pattern with an English name left, "
                          "1 untranslated)", rep)
            self.assertIn("| Zones | 2 | 1 | 0 | 0 |", rep)     # "Yard, Moon" is missing (worst part)
            self.assertNotIn("| names.official.pt-BR.json | Mason |", rep)   # used by a note: not "unused"


class ValidateUnit(unittest.TestCase):
    def test_bad_qty_self_loop_and_default(self):
        ds = {"items": {"a": {"en": "A", "raw": False, "defaultRecipe": "r2"},
                        "b": {"en": "B", "raw": True, "defaultRecipe": None}},
              "stations": {},
              "recipes": [{"id": "r1", "out": {"item": "a", "qty": 0}, "station": None, "in": [{"item": "a", "qty": 1}]},
                          {"id": "r2", "out": {"item": "b", "qty": 1}, "station": "nowhere",
                           "in": [{"item": "a", "qty": -1}]}]}
        rep = validate.validate(ds)
        self.assertEqual(rep.codes("error"), {"bad-default": 1, "bad-qty": 2, "dangling-ref": 1})
        self.assertEqual(rep.cycles[0]["items"], ["a"])
        self.assertEqual(rep.codes("warning").get("raw-with-recipe"), 1)

    def test_cyclic_default_warning(self):
        ds = {"items": {"a": {"en": "A", "raw": False, "defaultRecipe": "r1"}, "b": {"en": "B", "raw": True}},
              "stations": {},
              "recipes": [{"id": "r1", "out": {"item": "a", "qty": 1}, "station": None, "cyc": True,
                           "in": [{"item": "a", "qty": 1}, {"item": "b", "qty": 1}]}]}
        rep = validate.validate(ds)
        self.assertEqual(rep.codes("warning").get("cyclic-default"), 1)
        self.assertEqual(rep.codes("info").get("cycle-trapped"), 1)


CHANGELOG = [
    {"version": "9.9.9", "date": None, "pt": ["Novidade <b>em teste</b>"], "en": ["Test feature"]},
    {"version": "9.9.8", "date": "2026-01-02", "pt": ["Versão anterior"], "en": ["Previous version"]},
]
TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>Fixture</title>
<!-- @css -->
</head>
<body>
<script id="gk2-data" type="application/json"><!-- @data --></script>
<main id="app"></main>
<!-- @js -->
</body>
</html>
"""


def make_project(root, js=None, css=None, version="9.9.9", changelog=CHANGELOG, template=TEMPLATE):
    """A throwaway project: root/src (manifest, template, css, js), root/VERSION, root/data/changelog.json."""
    src = root / "src"
    js = js if js is not None else {"js/core.js": "window.GK = { ui: {} };\n",
                                    "js/ui/second.js": "GK.second = 2; // replacement text: \\1 $1 \\g<0>\n",
                                    "js/app.js": "GK.app = 'boot';\n"}
    css = css if css is not None else {"css/tokens.css": ":root { --a: 1; }\n", "css/z-last.css": "body { color: red; }\n"}
    for rel_path, text in {**js, **css}.items():
        (src / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (src / rel_path).write_text(text, encoding="utf-8")
    (src / "index.html").write_text(template, encoding="utf-8")
    (src / "manifest.json").write_text(json.dumps({"css": list(css), "js": list(js)}), encoding="utf-8")
    if version is not None:
        (root / "VERSION").write_text(version + "\n", encoding="utf-8")
    if changelog is not None:
        (root / "data").mkdir(exist_ok=True)
        (root / "data" / "changelog.json").write_text(json.dumps(changelog, ensure_ascii=False), encoding="utf-8")
    return src


class SrcBuild(unittest.TestCase):
    """The primary path: src/ (manifest + template + css + js) -> prototype/index.html, dist/index.html, dist/preview.html."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.proj = self.dir / "proj"
        self.src = make_project(self.proj)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, *extra, built="2026-01-01"):
        rs = read_json(FIX / "recipes.en.json")
        for r in rs:
            if r["id"] == "simple-coffin":
                r["inputs"] = [i for i in r["inputs"] if i["item"] != "glue"]
        rp = self.dir / "recipes.clean.json"
        rp.write_text(json.dumps(rs), encoding="utf-8")
        args = [a for a in fixture_args(self.dir / "out", recipes=rp) if a not in ("--no-src",)]
        args[args.index("--built") + 1] = built
        return run(BUILD, *args, "--src", self.src, *extra)

    def test_assembly_order_and_outputs(self):
        rc, so, se = self.build()
        self.assertEqual(rc, 0, se)
        dev = (self.proj / "prototype" / "index.html").read_text(encoding="utf-8")
        self.assertTrue(dev.startswith("<!doctype html>"))
        for mk in ("<!-- @css -->", "<!-- @js -->", "<!-- @data -->"):
            self.assertNotIn(mk, dev)
        order = [dev.index(x) for x in ("<title>Fixture</title>", "/* ==== src/css/tokens.css ==== */",
                                        "/* ==== src/css/z-last.css ==== */", 'id="gk2-data"', '<main id="app">',
                                        '"use strict";', "/* ==== src/js/core.js ==== */",
                                        "/* ==== src/js/ui/second.js ==== */", "/* ==== src/js/app.js ==== */")]
        self.assertEqual(order, sorted(order))
        self.assertIn(":root { --a: 1; }", dev)
        self.assertIn("GK.second = 2; // replacement text: \\1 $1 \\g<0>", dev)   # sources are copied verbatim
        self.assertEqual(dev.count("<style>"), 1)
        data = json.loads(extract_block(dev))
        self.assertEqual(data["meta"]["version"], "9.9.9")
        self.assertEqual(data["meta"]["changelog"], CHANGELOG)
        self.assertIn("log", data["items"])
        # artifact page: no skeleton, no remote icons, same code; preview wraps it
        art = (self.proj / "dist" / "index.html").read_text(encoding="utf-8")
        self.assertTrue(art.startswith("<title>Fixture</title>"), art[:80])
        for tag in ("<!doctype", "<html", "<head>", "<body", "charset="):
            self.assertNotIn(tag, art.lower())
        self.assertIn("/* ==== src/js/app.js ==== */", art)
        self.assertTrue(all(it["icon"] is None for it in json.loads(extract_block(art))["items"].values()))
        preview = (self.proj / "dist" / "preview.html").read_text(encoding="utf-8")
        self.assertTrue(preview.startswith("<!doctype html>"))
        self.assertIn(art, preview)
        # the source tree is untouched and a second run writes nothing
        self.assertIn("<!-- @data -->", (self.src / "index.html").read_text(encoding="utf-8"))
        rc, so, se = run(*[BUILD], *[a for a in self.build_args()], "--src", self.src)
        self.assertEqual(rc, 0, se)
        self.assertIn("nothing (all outputs up to date)", so)

    def build_args(self):
        rp = self.dir / "recipes.clean.json"
        return [a for a in fixture_args(self.dir / "out", recipes=rp) if a not in ("--no-src", "--quiet")]

    def test_sprite_from_project_data(self):
        sprite = {"image": "data:image/png;base64,iVBORw0KGgo=", "size": 32, "cols": 1, "rows": 1, "icons": {"log": [0, 0]}}
        (self.proj / "data" / "sprite.json").write_text(json.dumps(sprite), encoding="utf-8")
        rc, so, se = self.build()
        self.assertEqual(rc, 0, se)
        for page in ("prototype/index.html", "dist/index.html"):
            data = json.loads(extract_block((self.proj / page).read_text(encoding="utf-8")))
            self.assertEqual(data["meta"]["sprite"]["icons"], {"log": [0, 0]}, page)

    def test_changelog_md_and_release(self):
        rc, so, se = self.build()
        self.assertEqual(rc, 0, se)
        md = (self.proj / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertLess(md.index("## 9.9.9 — em desenvolvimento"), md.index("## 9.9.8 — 2026-01-02"))
        self.assertLess(md.index("# Histórico de atualizações"), md.index("# Update history"))
        self.assertIn("## 9.9.9 — in development", md)
        self.assertIn("- Novidade <b>em teste</b>", md)
        self.assertIsNone(read_json(self.proj / "data" / "changelog.json")[0]["date"])   # no --release: still a draft
        # --release dates the top entry with the build date, re-embeds it and regenerates CHANGELOG.md
        rc, so, se = self.build("--release", built="2026-02-03")
        self.assertEqual(rc, 0, se)
        cl = read_json(self.proj / "data" / "changelog.json")
        self.assertEqual(cl[0]["date"], "2026-02-03")
        self.assertEqual(cl[1], CHANGELOG[1])
        self.assertIn("## 9.9.9 — 2026-02-03", (self.proj / "CHANGELOG.md").read_text(encoding="utf-8"))
        data = json.loads(extract_block((self.proj / "prototype" / "index.html").read_text(encoding="utf-8")))
        self.assertEqual(data["meta"]["changelog"][0]["date"], "2026-02-03")
        # a released entry keeps its date
        rc, so, se = self.build("--release", built="2026-03-04")
        self.assertEqual(rc, 0, se)
        self.assertEqual(read_json(self.proj / "data" / "changelog.json")[0]["date"], "2026-02-03")

    def test_release_needs_matching_version(self):
        (self.proj / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        rc, so, se = self.build("--release")
        self.assertEqual(rc, 2)
        self.assertIn("VERSION is 1.0.0", se)
        rc, so, se = self.build()                       # without --release a mismatch is only a warning
        self.assertEqual(rc, 0, se)
        self.assertIn("differs from the top changelog entry", se)

    def test_bad_sources_are_usage_errors(self):
        (self.src / "js" / "ui" / "second.js").write_text("const s = '</script>';\n", encoding="utf-8")
        rc, so, se = self.build()
        self.assertEqual(rc, 2)
        self.assertIn("would end the page", se)
        self.assertFalse((self.proj / "prototype" / "index.html").exists())
        make_project(self.proj, template=TEMPLATE.replace("<!-- @js -->", ""))
        rc, so, se = self.build()
        self.assertEqual(rc, 2)
        self.assertIn("<!-- @js --> exactly once", se)
        make_project(self.proj)
        (self.proj / "data" / "changelog.json").write_text('[{"version": "x"}]', encoding="utf-8")
        self.assertEqual(self.build()[0], 2)
        self.assertEqual(run(BUILD, "--src", self.src, "--inject", FIX / "page.html")[0], 2)

    def test_unlisted_source_warns(self):
        (self.src / "js" / "ui" / "forgotten.js").write_text("GK.x = 1;\n", encoding="utf-8")
        rc, so, se = self.build()
        self.assertEqual(rc, 0, se)
        self.assertIn("forgotten.js is not in src/manifest.json", se)
        self.assertNotIn("GK.x = 1", (self.proj / "prototype" / "index.html").read_text(encoding="utf-8"))


# a tiny technology tree in data/techs.json shape (scripts/build_techs.py), matching the fixture recipes
FIX_TECHS = {
    "meta": {"built": "2026-01-01", "count": 3, "branches": ["building", "metallurgy"], "langs": ["pt", "en"],
             "sources": ["test"],
             "tp": {"red": {"en": "Red tech points", "pt": "Pontos vermelhos", "tr": "likely", "color": "#d0453a", "icon": "tp:red"},
                    "green": {"en": "Green tech points", "pt": "Pontos verdes", "tr": "likely", "color": "#4f9e3a", "icon": "tp:green"},
                    "blue": {"en": "Blue tech points", "pt": "Pontos azuis", "tr": "likely", "color": "#3f6fd0", "icon": "tp:blue"}}},
    "branches": {"metallurgy": {"pt": "Metalurgia", "en": "Metallurgy", "order": 1, "tr": "official", "icon": "branch:metallurgy"},
                 "building": {"pt": "Engenharia", "en": "Building", "order": 0, "tr": "official", "icon": "branch:building"}},
    "techs": {
        "woodworking": {"id": "woodworking", "pt": "Marcenaria", "en": "Woodworking", "tr": "official", "branch": "building",
                        "column": 1, "x": 0, "y": 1, "listed": True, "hidden": False, "given": True,
                        "cost": {"red": 0, "green": 0, "blue": 0}, "parents": [], "children": ["carpentry"], "rep": None,
                        "unlocks": [{"item": "plank", "kind": "item", "en": "Plank", "pt": "Tábua", "tr": "likely", "station": None}],
                        "recipes": ["plank"], "icon": "plank", "notes": {"pt": "Dada de graça.", "en": "Given for free."}},
        "carpentry": {"id": "carpentry", "pt": "Carpintaria Oficial", "en": "Carpentry", "tr": "official", "branch": "building",
                      "column": 2, "x": 1, "y": 0.5, "listed": True, "hidden": True, "given": False,
                      "cost": {"red": 20, "green": 5, "blue": 0}, "parents": ["woodworking"], "children": [],
                      "rep": {"who": {"en": "Jack", "pt": "Jailson"}, "level": 40},
                      "unlocks": [{"item": "wooden-box", "kind": "item", "en": "Wooden Box", "pt": "Caixa", "tr": "official", "station": "workbench"},
                                  {"item": None, "kind": "building", "en": "Town Hall", "pt": "Prefeitura", "tr": "official", "station": None}],
                      "recipes": ["wooden-box", "simple-coffin"], "icon": "tech:carpentry", "notes": None},
        "smelting": {"id": "smelting", "pt": "Fundição", "en": "Smelting", "tr": "likely", "branch": "metallurgy",
                     "column": 1, "x": 0, "y": 2, "listed": True, "hidden": False, "given": False,
                     "cost": {"red": 10, "green": 0, "blue": 3}, "parents": [], "children": [], "rep": None,
                     "unlocks": [], "recipes": ["iron-ingot-furnace"], "icon": "iron-ingot", "notes": None},
    },
    "icons": {"tech:carpentry": "https://media.wikily.gg/x.png", "tp:red": "https://media.wikily.gg/r.png"},
}


class TechsBuild(unittest.TestCase):
    """data/techs.json: recipe tech names follow it, the page embeds a compact copy as `techs`, and the sprite keeps
    the tech:/tp:/branch: ids."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def clean_recipes(self):
        rs = read_json(FIX / "recipes.en.json")
        for r in rs:
            if r["id"] == "simple-coffin":
                r["inputs"] = [i for i in r["inputs"] if i["item"] != "glue"]
        rp = self.dir / "recipes.clean.json"
        rp.write_text(json.dumps(rs), encoding="utf-8")
        return rp

    def write_techs(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(FIX_TECHS, ensure_ascii=False), encoding="utf-8")
        return path

    def test_apply_tech_names(self):
        ds = {"meta": {"langs": ["pt", "en"]}, "recipes": [
            {"id": "a", "tech": {"pt": "Carpintaria", "en": "Carpentry", "id": "carpentry", "type": "technology"}},
            {"id": "b", "tech": {"pt": "Missão", "en": "Quest", "id": "carpentry", "type": "quest"}},
            {"id": "c", "tech": {"pt": "Outra", "en": "Other", "id": "unknown", "type": "technology"}},
            {"id": "d", "tech": None}]}
        self.assertEqual(build.apply_tech_names(ds, FIX_TECHS), 1)
        self.assertEqual(ds["recipes"][0]["tech"], {"pt": "Carpintaria Oficial", "en": "Carpentry", "id": "carpentry",
                                                    "type": "technology"})
        self.assertEqual(ds["recipes"][1]["tech"]["pt"], "Missão")      # quests / perks keep their names
        self.assertEqual(ds["recipes"][2]["tech"]["pt"], "Outra")       # no record: untouched
        self.assertEqual(build.apply_tech_names(ds, FIX_TECHS), 0)      # idempotent

    def test_techs_payload_is_compact(self):
        ds = {"meta": {"langs": ["pt", "en"]},
              "items": {"plank": {"pt": "Tábua", "en": "Plank"}, "wooden-box": {"pt": "Caixa de madeira", "en": "Wooden Box"}},
              "stations": {}}
        out = build.techs_payload(FIX_TECHS, ds)
        self.assertEqual(set(out), {"tp", "branches", "techs"})
        self.assertEqual(list(out["branches"]), ["building", "metallurgy"])          # tab order
        self.assertEqual(out["branches"]["building"], {"pt": "Engenharia", "en": "Building", "order": 0, "icon": "branch:building"})
        self.assertEqual(out["tp"]["red"], {"pt": "Pontos vermelhos", "en": "Red tech points", "color": "#d0453a", "icon": "tp:red"})
        w, c, sm = out["techs"]["woodworking"], out["techs"]["carpentry"], out["techs"]["smelting"]
        for t in out["techs"].values():
            for k in ("id", "x", "children", "recipes", "listed"):
                self.assertNotIn(k, t)
        self.assertEqual(w, {"pt": "Marcenaria", "en": "Woodworking", "branch": "building", "column": 1, "y": 1,
                             "cost": [0, 0, 0], "given": True, "unlocks": [{"item": "plank", "kind": "item"}],
                             "icon": "plank", "notes": {"pt": "Dada de graça.", "en": "Given for free."}})
        self.assertEqual(c["parents"], ["woodworking"])
        self.assertTrue(c["hidden"])
        self.assertEqual(c["rep"], {"who": {"en": "Jack", "pt": "Jailson"}, "level": 40})
        self.assertEqual(c["unlocks"][0], {"item": "wooden-box", "kind": "item", "en": "Wooden Box", "pt": "Caixa",
                                           "station": "workbench"})                        # pt differs from the item's
        self.assertEqual(c["unlocks"][1], {"kind": "building", "en": "Town Hall", "pt": "Prefeitura"})
        self.assertEqual(sm["tr"], "likely")
        self.assertEqual(sm["cost"], [10, 0, 3])
        self.assertNotIn("unlocks", sm)
        self.assertNotIn("tr", c)
        self.assertNotIn("icons", json.dumps(out))

    def test_sprite_keeps_tech_ids(self):
        ds = {"meta": {"langs": ["pt", "en"]}, "items": {"log": {"id": "log", "pt": "Tora", "en": "Log", "icon": None}},
              "stations": {}, "recipes": []}
        sprite = {"image": "data:image/png;base64,iVBORw0KGgo=", "size": 32, "cols": 2, "rows": 2,
                  "icons": {"log": [0, 0], "tech:carpentry": [1, 0], "tp:red": [0, 1], "branch:building": [1, 1],
                            "gone": [1, 1], "other:x": [0, 0]}}
        out = build.page_payload(ds, sprite=sprite, techs=FIX_TECHS)
        self.assertEqual(set(out["meta"]["sprite"]["icons"]), {"log", "tech:carpentry", "tp:red", "branch:building"})
        self.assertIn("carpentry", out["techs"]["techs"])
        self.assertNotIn("techs", build.page_payload(ds, sprite=sprite))

    def test_src_build_embeds_techs(self):
        proj = self.dir / "proj"
        src = make_project(proj)
        self.write_techs(proj / "data" / "techs.json")
        args = [a for a in fixture_args(self.dir / "out", recipes=self.clean_recipes()) if a != "--no-src"]
        rc, so, se = run(BUILD, *args, "--src", src)
        self.assertEqual(rc, 0, se)
        for page in ("prototype/index.html", "dist/index.html"):
            data = json.loads(extract_block((proj / page).read_text(encoding="utf-8")))
            self.assertEqual(sorted(data["techs"]["techs"]), ["carpentry", "smelting", "woodworking"], page)
            box = next(r for r in data["recipes"] if r["id"] == "wooden-box")
            self.assertEqual(box["tech"]["pt"], "Carpintaria Oficial", page)
        ds = read_json(self.dir / "out" / "gk2.json")
        self.assertEqual({r["tech"]["pt"] for r in ds["recipes"] if r["tech"] and r["tech"]["id"] == "carpentry"},
                         {"Carpintaria Oficial"})
        # --no-techs: nothing embedded, names as the names layers say
        rc, so, se = run(BUILD, *args, "--src", src, "--no-techs")
        self.assertEqual(rc, 0, se)
        data = json.loads(extract_block((proj / "dist" / "index.html").read_text(encoding="utf-8")))
        self.assertNotIn("techs", data)
        self.assertEqual(next(r for r in data["recipes"] if r["id"] == "wooden-box")["tech"]["pt"], "Carpintaria")
        # usage errors: both flags, a broken file
        self.assertEqual(run(BUILD, *args, "--src", src, "--no-techs", "--techs", proj / "data" / "techs.json")[0], 2)
        bad = self.dir / "bad.json"
        bad.write_text("[]", encoding="utf-8")
        self.assertEqual(run(BUILD, *args, "--src", src, "--techs", bad)[0], 2)

    def test_inject_embeds_only_with_explicit_techs(self):
        page = self.dir / "page.html"
        shutil.copy(FIX / "page.html", page)
        out = self.dir / "out"
        rc, so, se = run(BUILD, *fixture_args(out, recipes=self.clean_recipes()), "--inject", page, "--out", self.dir / "a.html",
                         "--techs", self.write_techs(self.dir / "techs.json"))
        self.assertEqual(rc, 0, se)
        self.assertIn("techs", json.loads(extract_block((self.dir / "a.html").read_text(encoding="utf-8"))))
        rc, so, se = run(BUILD, *fixture_args(out, recipes=self.clean_recipes()), "--inject", page, "--out", self.dir / "b.html")
        self.assertEqual(rc, 0, se)
        self.assertNotIn("techs", json.loads(extract_block((self.dir / "b.html").read_text(encoding="utf-8"))))

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_gk_tech_module(self):
        """src/js/tech.js (GK.tech) on the fixture tree, in node with a stub GK.data."""
        ds = {"meta": {"langs": ["pt", "en"]}, "items": {"plank": {"pt": "Tábua", "en": "Plank"}}, "stations": {}}
        payload = build.techs_payload(FIX_TECHS, ds)
        harness = r"""
const GK = { data: { get: () => D, load: (j) => j } };
const D = { items: { plank: { id: "plank", pt: "Tábua", en: "Plank", tr: "likely", defaultRecipe: null },
                     box: { id: "box", pt: "Caixa", en: "Box", defaultRecipe: "box" },
                     ingot: { id: "ingot", pt: "Lingote", en: "Ingot", defaultRecipe: "ingot" } },
  stations: {}, byOut: {},
  recipes: [ { id: "box", out: { item: "box" }, tech: { id: "carpentry", type: "technology" } },
             { id: "ingot", out: { item: "ingot" }, tech: { id: "smelting", type: "technology" } },
             { id: "q", out: { item: "plank" }, tech: { id: "a-quest", type: "quest", pt: "Missão", en: "Quest" } } ] };
D.recipeById = Object.fromEntries(D.recipes.map((r) => [r.id, r]));
GK.calc = { howToMake: () => ({ leaf: "raw" }) };
global.document = { getElementById: () => null };
""" + (ROOT / "src" / "js" / "tech.js").read_text(encoding="utf-8") + r"""
const T = GK.tech; T.init(PAYLOAD);
const ids = (l) => l.map((t) => t.id);
const out = {
  order: ids(T.all()), branches: T.branches().map((b) => b.id),
  children: T.get("woodworking").children, recipes: T.get("carpentry").recipes, free: T.get("woodworking").free,
  unlockName: T.get("woodworking").unlocks[0].pt, unlockTr: T.get("woodworking").unlocks[0].tr,
  req: ids(T.required(["carpentry", "smelting"], {})),
  reqDone: ids(T.required(["carpentry", "smelting"], { carpentry: true })),
  reqImplied: ids(T.required(["woodworking"], { carpentry: true })),
  cost: T.costOf(T.required(["carpentry", "smelting"], {})),
  anc: ids(T.ancestors("carpentry")), set: [...T.researchedSet({ carpentry: true })].sort(),
  plan: (() => { const p = T.forPlan({ steps: [ { item: "box", recipe: D.recipes[0] }, { item: "plank", recipe: D.recipes[2] } ], raw: [], stations: [] },
                                     { researched: {}, choice: {}, have: {} });
                 return { techs: ids(p.techs), direct: p.direct, cost: p.cost, other: p.other, flags: p.flags, why: p.why }; })(),
};
console.log(JSON.stringify(out));
"""
        js = harness.replace("PAYLOAD", json.dumps(payload, ensure_ascii=False))
        f = self.dir / "t.js"
        f.write_text(js, encoding="utf-8")
        p = subprocess.run(["node", str(f)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        o = json.loads(p.stdout)
        self.assertEqual(o["order"], ["woodworking", "carpentry", "smelting"])     # branch order, column, y
        self.assertEqual(o["branches"], ["building", "metallurgy"])
        self.assertEqual(o["children"], ["carpentry"])
        self.assertEqual(o["recipes"], ["box"])
        self.assertTrue(o["free"])
        self.assertEqual((o["unlockName"], o["unlockTr"]), ("Tábua", "likely"))  # filled from the item
        self.assertEqual(o["req"], ["woodworking", "carpentry", "smelting"])
        self.assertEqual(o["reqDone"], ["smelting"])
        self.assertEqual(o["reqImplied"], [])                                      # an ancestor of a researched tech
        self.assertEqual(o["cost"], {"red": 30, "green": 5, "blue": 3})
        self.assertEqual(o["anc"], ["woodworking"])
        self.assertEqual(o["set"], ["carpentry", "woodworking"])
        self.assertEqual(o["plan"]["techs"], ["woodworking", "carpentry"])
        self.assertEqual(o["plan"]["direct"], ["carpentry"])
        self.assertEqual(o["plan"]["cost"], {"red": 20, "green": 5, "blue": 0})
        self.assertEqual(o["plan"]["other"], [{"type": "quest", "id": "a-quest", "pt": "Missão", "en": "Quest", "items": ["plank"]}])
        self.assertEqual(o["plan"]["flags"], {"rep": 1, "hidden": 1, "given": 1, "free": 1})
        self.assertEqual(o["plan"]["why"], {"carpentry": ["box"]})


# a tiny week in data/days.json shape (scripts/build_days.py), out of order on purpose
FIX_DAYS = {
    "meta": {"week_length": 2, "order_confidence": "low", "notes": {"pt": "Nota.", "en": "Note."}},
    "days": [
        {"id": "wrath", "order": 1, "sin": {"en": "Wrath", "pt": "Ira"}, "name": {"en": "Day of Wrath", "pt": "Dia da Ira"},
         "tr": "likely", "sprite": "day_wrath", "glyph": "a flame", "color": None,
         "events": [{"kind": "battle", "en": "Arena", "pt": "Arena", "tr": "likely", "who": None, "source": "test",
                     "confidence": "low", "items": []}]},
        {"id": "sloth", "order": 0, "sin": {"en": "Sloth", "pt": "Preguiça"}, "name": {"en": "Day of Sloth", "pt": "Dia da Preguiça"},
         "tr": "official", "sprite": "day_sloth", "glyph": "a closed eye", "color": "#6b7fa8",
         "mentions": [{"key": "k", "en": "Every Sloth", "pt": "Toda Preguiça"}],
         "events": [{"kind": "merchant", "en": "Merchant", "pt": "Mercador", "tr": "official", "who": "Bob", "source": "test",
                     "confidence": "high", "items": ["log"]}]},
    ],
}


class DaysBuild(unittest.TestCase):
    """data/days.json: embedded in the page as `days` when present (src mode default) and its sprite ids kept;
    absent = no `days` and no error."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_days(self, path, doc=FIX_DAYS):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return path

    def test_days_payload(self):
        out = build.days_payload(FIX_DAYS)
        self.assertEqual([d["id"] for d in out["days"]], ["sloth", "wrath"])           # wheel order
        self.assertEqual(out["meta"], FIX_DAYS["meta"])
        w = out["days"][1]
        self.assertNotIn("color", w)                                                     # nulls dropped
        self.assertNotIn("who", w["events"][0])
        self.assertNotIn("items", w["events"][0])                                        # empty lists dropped
        self.assertEqual(out["days"][0]["events"][0]["items"], ["log"])
        self.assertEqual(out["days"][0]["color"], "#6b7fa8")
        self.assertNotIn("mentions", out["days"][0])                                    # never read by the page
        self.assertEqual(build.day_sprite_ids(FIX_DAYS), {"day:wrath", "day:sloth", "day_wrath", "day_sloth"})

    def test_sprite_keeps_day_ids(self):
        ds = {"meta": {"langs": ["pt", "en"]}, "items": {"log": {"id": "log", "pt": "Tora", "en": "Log", "icon": None}},
              "stations": {}, "recipes": []}
        sprite = {"image": "data:image/png;base64,iVBORw0KGgo=", "size": 32, "cols": 2, "rows": 2,
                  "icons": {"log": [0, 0], "day_sloth": [1, 0], "day:wrath": [0, 1], "day_other": [1, 1]}}
        out = build.page_payload(ds, sprite=sprite, days=FIX_DAYS)
        self.assertEqual(set(out["meta"]["sprite"]["icons"]), {"log", "day_sloth", "day:wrath"})
        self.assertEqual(len(out["days"]["days"]), 2)
        self.assertNotIn("days", build.page_payload(ds, sprite=sprite))

    def test_load_days_rejects_bad_files(self):
        for bad in ("[]", '{"days": []}', '{"days": [{"order": 0}]}', '{"days": [{"id": "a"}, {"id": "a"}]}', "{oops"):
            f = self.dir / "bad.json"
            f.write_text(bad, encoding="utf-8")
            with self.assertRaises(SystemExit, msg=bad):
                build.load_days(f)

    def test_src_build_embeds_days_when_present(self):
        proj = self.dir / "proj"
        src = make_project(proj)
        rs = read_json(FIX / "recipes.en.json")
        for r in rs:
            if r["id"] == "simple-coffin":
                r["inputs"] = [i for i in r["inputs"] if i["item"] != "glue"]
        rp = self.dir / "recipes.clean.json"
        rp.write_text(json.dumps(rs), encoding="utf-8")
        args = [a for a in fixture_args(self.dir / "out", recipes=rp) if a != "--no-src"]
        # absent: builds fine, no `days`
        rc, so, se = run(BUILD, *args, "--src", src)
        self.assertEqual(rc, 0, se)
        self.assertNotIn("days", json.loads(extract_block((proj / "dist" / "index.html").read_text(encoding="utf-8"))))
        # present: embedded in both pages, in wheel order
        self.write_days(proj / "data" / "days.json")
        rc, so, se = run(BUILD, *args, "--src", src)
        self.assertEqual(rc, 0, se)
        for page in ("prototype/index.html", "dist/index.html"):
            data = json.loads(extract_block((proj / page).read_text(encoding="utf-8")))
            self.assertEqual([d["id"] for d in data["days"]["days"]], ["sloth", "wrath"], page)
        self.assertNotIn("days", read_json(self.dir / "out" / "gk2.json"))             # page only
        # --no-days, usage errors, a broken file
        rc, so, se = run(BUILD, *args, "--src", src, "--no-days")
        self.assertEqual(rc, 0, se)
        self.assertNotIn("days", json.loads(extract_block((proj / "dist" / "index.html").read_text(encoding="utf-8"))))
        self.assertEqual(run(BUILD, *args, "--src", src, "--no-days", "--days", proj / "data" / "days.json")[0], 2)
        bad = self.dir / "bad.json"
        bad.write_text('{"days": "x"}', encoding="utf-8")
        self.assertEqual(run(BUILD, *args, "--src", src, "--days", bad)[0], 2)

    def test_inject_embeds_only_with_explicit_days(self):
        page = self.dir / "page.html"
        shutil.copy(FIX / "page.html", page)
        out = self.dir / "out"
        rc, so, se = run(BUILD, *fixture_args(out), "--allow-errors", "--inject", page, "--out", self.dir / "a.html",
                         "--days", self.write_days(self.dir / "days.json"))
        self.assertIn(rc, (0, 1), se)
        self.assertIn("days", json.loads(extract_block((self.dir / "a.html").read_text(encoding="utf-8"))))
        rc, so, se = run(BUILD, *fixture_args(out), "--allow-errors", "--inject", page, "--out", self.dir / "b.html")
        self.assertIn(rc, (0, 1), se)
        self.assertNotIn("days", json.loads(extract_block((self.dir / "b.html").read_text(encoding="utf-8"))))

    def test_real_days_modules_registered(self):
        src = ROOT / "src" / "js"
        days, today = (src / "ui" / "days.js").read_text(encoding="utf-8"), (src / "ui" / "today.js").read_text(encoding="utf-8")
        self.assertRegex(days, r'GK\.router\.register\(\{ id: "days", labelKey: "tab\.days", screen: "days"')
        self.assertIn('GK.app.registerPanel(GK.ui.days, { id: "days", panel: "days"', days)
        self.assertIn('slot: "planner-top", order: 5', today)
        for text in (days, today):
            self.assertRegex(text, r"GK\.i18n\.add\(\{\s*pt: \{")
            self.assertIn("  en: {", text)
        if (ROOT / "data" / "days.json").exists():
            doc = build.load_days(ROOT / "data" / "days.json")
            self.assertEqual(len(doc["days"]), 6)


@unittest.skipUnless((ROOT / "data" / "techs.json").exists() and (ROOT / "data" / "gk2.json").exists(),
                     "real techs.json not present")
class RealTechs(unittest.TestCase):
    def test_real_techs_payload(self):
        techs, ds = read_json(ROOT / "data" / "techs.json"), read_json(ROOT / "data" / "gk2.json")
        out = build.techs_payload(techs, ds)
        size = len(build.dumps_min(out).encode("utf-8"))
        self.assertLess(size, 250_000, f"techs payload is {size:,} bytes")
        self.assertEqual(len(out["techs"]), len(techs["techs"]))
        self.assertEqual([b["pt"] for b in out["branches"].values()],
                         ["Engenharia", "Metalurgia", "Agricultura", "Teologia", "Anatomia e alquimia", "Culinária"])
        # gk2.json (built with techs.json) uses the tree's names for every technology recipe
        for r in ds["recipes"]:
            t = r.get("tech")
            if t and t["type"] == "technology" and t["id"] in techs["techs"]:
                self.assertEqual(t["pt"], techs["techs"][t["id"]]["pt"], r["id"])

    def test_tests_never_build_the_real_pages(self):
        """Every build.py run in this file must pass --no-src, --src or --inject: otherwise src mode (the default)
        rewrites the real prototype/ and dist/ with test data."""
        text = Path(__file__).read_text(encoding="utf-8")
        for m in re.finditer(r"run\(BUILD,(.*?)\)\n", text, re.S):
            call = m.group(1)
            self.assertTrue(any(k in call for k in ("--no-src", '"--src"', '"--inject"', "fixture_args", "self.build", "build_args", "*args")),
                            call[:120])

    def test_real_tech_modules_registered(self):
        src = ROOT / "src" / "js"
        ui, needs = (src / "ui" / "tech.js").read_text(encoding="utf-8"), (src / "ui" / "techneeds.js").read_text(encoding="utf-8")
        self.assertRegex(ui, r'GK\.router\.register\(\{ id: "tech", labelKey: "tab\.tech", screen: "tech"')
        self.assertIn('GK.app.registerPanel(GK.ui.tech, { id: "tech", panel: "tech"', ui)
        self.assertIn('slot: "planner-extra", order: 10', needs)
        for text in (ui, needs):
            self.assertRegex(text, r"GK\.i18n\.add\(\{\s*pt: \{")
            self.assertIn("  en: {", text)
            self.assertNotIn("confirm(", text)
        self.assertIn("GK.tech = (function", (src / "tech.js").read_text(encoding="utf-8"))


@unittest.skipUnless((ROOT / "src" / "manifest.json").exists(), "src/ not present")
class RealSrc(unittest.TestCase):
    """Contract of the real src/ tree (read-only: assembles in memory, writes nothing)."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.man = read_json(cls.src / "manifest.json")
        cls.html = build.assemble(cls.src, payload="{}", warn=False)
        cls.text = {f: (cls.src / f).read_text(encoding="utf-8") for f in cls.man["js"] + cls.man["css"]}

    def test_manifest_order(self):
        js = self.man["js"]
        self.assertEqual(js[0], "js/core.js")
        self.assertEqual(js[-1], "js/app.js")
        for a, b in (("js/util.js", "js/i18n.js"), ("js/i18n.js", "js/data.js"), ("js/router.js", "js/ui/header.js"),
                     ("js/ui/fmt.js", "js/ui/summary.js"), ("js/ui/changelog.js", "js/ui/footer.js"),
                     ("js/ui/changelog.js", "js/ui/credits.js"), ("js/ui/credits.js", "js/ui/footer.js")):
            self.assertLess(js.index(a), js.index(b), (a, b))
        self.assertEqual(self.man["css"][-1], "css/responsive.css")
        pos = [self.html.index(f"/* ==== src/{f} ==== */") for f in self.man["css"] + self.man["js"]]
        self.assertEqual(pos, sorted(pos))
        self.assertEqual(sorted(p.relative_to(self.src).as_posix() for p in self.src.rglob("*.js")), sorted(js))

    def test_every_module_documents_itself(self):
        for f, text in self.text.items():
            self.assertTrue(text.lstrip().startswith("/*"), f"{f} must begin with a comment (what it owns / exposes)")

    def test_i18n_per_module(self):
        i18n = self.text["js/i18n.js"]
        self.assertIn("function add(", i18n)
        self.assertNotIn('"goals.title"', i18n)            # strings live in their modules
        for f in ("js/router.js", "js/ui/header.js", "js/ui/search.js", "js/ui/goals.js", "js/ui/summary.js",
                  "js/ui/checklist.js", "js/ui/soon.js", "js/ui/changelog.js", "js/ui/credits.js", "js/ui/footer.js", "js/ui/fmt.js"):
            self.assertRegex(self.text[f], r"GK\.i18n\.add\(\{\s*pt: \{", f)
            self.assertIn("  en: {", self.text[f], f)
        keys = {}
        for f, text in self.text.items():
            for k in re.findall(r'^\s+"([a-zA-Z]+\.[\w.]+)":', text, re.M):
                keys.setdefault(k, set()).add(f)
        self.assertEqual({k: v for k, v in keys.items() if len(v) > 1}, {}, "a key is defined by two modules")
        self.assertIn("changelog.title", keys)
        self.assertIn("footer.history", keys)
        self.assertIn("footer.credits", keys)

    def test_registries(self):
        self.assertIn("GK.app = (function", self.text["js/core.js"])
        self.assertIn("registerPanel", self.text["js/core.js"])
        self.assertIn("function register(", self.text["js/router.js"])
        self.assertIn("GK.router.tabs().map", self.text["js/ui/header.js"])
        for f in ("js/ui/header.js", "js/ui/search.js", "js/ui/goals.js", "js/ui/summary.js", "js/ui/checklist.js",
                  "js/ui/soon.js", "js/ui/changelog.js", "js/ui/credits.js", "js/ui/footer.js"):
            self.assertIn("GK.app.registerPanel(", self.text[f], f)
        self.assertNotIn("GK.ui.goals.mount", self.text["js/app.js"])     # the loop reads the registry
        self.assertRegex(self.text["js/ui/changelog.js"], r'GK\.router\.register\(\{ id: "changelog".*tab: false')
        self.assertIn('href="#changelog"', self.text["js/ui/footer.js"])
        self.assertIn('<section data-slot="planner-extra" id="planner-extra">', self.html)
        # Receitas and Tecnologias own their routes; the soon module keeps no placeholder registration
        self.assertNotRegex(self.text["js/ui/soon.js"], r"(?m)^GK\.router\.register\(")
        self.assertRegex(self.text["js/ui/recipes.js"], r'GK\.router\.register\(\{ id: "recipes", labelKey: "rc\.tab", screen: "recipes"')
        self.assertRegex(self.text["js/ui/tech.js"], r'GK\.router\.register\(\{ id: "tech", labelKey: "tab\.tech", screen: "tech"')
        self.assertIn('"tab.tech": "Tecnologias"', self.text["js/ui/tech.js"])

    def test_credits_screen(self):
        """#credits: a route-only screen in the assembled page, reached from the footer's version line."""
        cr = self.text["js/ui/credits.js"]
        self.assertIn('GK.router.register({ id: "credits", labelKey: "credits.title", screen: "credits", tab: false, order: 910 });', self.html)
        self.assertIn('GK.app.registerPanel(GK.ui.credits, { id: "credits", panel: "credits"', self.html)
        self.assertIn('<a href="#credits" id="foot-credits">', self.html)
        self.assertLess(self.html.index('id="foot-changelog"'), self.html.index('id="foot-credits"'))
        self.assertIn('"footer.credits": "Créditos"', self.text["js/ui/footer.js"])
        self.assertIn('"footer.credits": "Credits"', self.text["js/ui/footer.js"])
        # every credits.* text exists in both languages
        pt, en = cr.split("\n  en: {", 1)
        keys = lambda part: set(re.findall(r'^\s+"(credits\.[\w.]+)":', part, re.M))
        self.assertTrue(keys(pt) and keys(pt) == keys(en), keys(pt) ^ keys(en))
        for url in ("https://wikily.gg/graveyard-keeper-2", "https://github.com/hpizaia/GK2"):
            self.assertIn(url, cr)
        self.assertIn('target="_blank" rel="noopener"', cr)
        self.assertIn("Graveyard Keeper 2 © Lazy Bear Games / tinyBuild", cr)
        self.assertIn('meta.from === "search-toggle"', cr)
        self.assertIn(".screen-credits", self.text["css/screens.css"])

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_js_syntax(self):
        js = re.findall(r"<script>\n(.*?)</script>", self.html, re.S)
        self.assertEqual(len(js), 1)
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "page.js"
            f.write_text(js[0], encoding="utf-8")
            p = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)

    def test_version_files(self):
        v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        cl = read_json(ROOT / "data" / "changelog.json")
        self.assertEqual(cl[0]["version"], v)
        self.assertEqual(build.load_changelog(ROOT), cl)


class MadeText(unittest.TestCase):
    """made_text -> out.note {pt, en} (perk yield bonus), star_quality -> {silver, gold}."""

    def test_made_text_and_star_quality(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            rs = read_json(FIX / "recipes.en.json")
            for r in rs:
                if r["id"] == "simple-coffin":
                    r["inputs"] = [i for i in r["inputs"] if i["item"] != "glue"]
                if r["id"] == "nail":
                    r["made_text"] = "5 (8 with Blacksmith)"
                if r["id"] == "plank":
                    r["made_text"] = "2"                       # equal to the qty: says nothing more
                if r["id"] == "coal":
                    r["made_text"] = "2-3"                     # no pattern: kept as text in both languages
                if r["id"] == "fertilized-beet":
                    r["star_quality"] = {"silver_at": "6 successful ticks", "gold_at": "10 successful ticks"}
                if r["id"] == "fertilizer":
                    r["star_quality"] = {"silver_at": "when lucky"}
            (d / "recipes.json").write_text(json.dumps(rs), encoding="utf-8")
            names = d / "names.perks.json"
            names.write_text(json.dumps({"Blacksmith": {"pt": "Ferreiro", "source": "game-files", "confidence": "official"}}),
                             encoding="utf-8")
            rc, so, se = run(BUILD, *fixture_args(d, recipes=d / "recipes.json",
                                                  names=[FIX / "names.pt-BR.json", names]))
            self.assertEqual(rc, 0, se)
            ds = read_json(d / "gk2.json")
            R = {r["id"]: r for r in ds["recipes"]}
            self.assertEqual(R["nail"]["out"], {"item": "nail", "qty": 5,
                                                "note": {"pt": "5 (8 com Ferreiro)", "en": "5 (8 with Blacksmith)"}})
            self.assertEqual(R["plank"]["out"], {"item": "plank", "qty": 2})
            self.assertEqual(R["coal"]["out"]["note"], {"pt": "2-3", "en": "2-3"})
            self.assertEqual(R["fertilized-beet"]["star_quality"], {"silver": 6, "gold": 10})
            self.assertEqual(R["fertilizer"]["star_quality"], {"silver": "when lucky"})
            self.assertNotIn("star_quality", R["plank"])
            self.assertEqual(run(VALIDATE, d / "gk2.json", "--quiet")[0], 0)
            # the page payload keeps them (a note equal in both languages collapses to one string)
            page = build.page_payload(ds)
            P = {r["id"]: r for r in page["recipes"]}
            self.assertEqual(P["nail"]["out"]["note"], {"pt": "5 (8 com Ferreiro)", "en": "5 (8 with Blacksmith)"})
            self.assertEqual(P["coal"]["out"]["note"], "2-3")
            self.assertEqual(P["fertilized-beet"]["star_quality"], {"silver": 6, "gold": 10})

    def test_data_versions(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t) / "a.json", Path(t) / "b.json"
            a.write_text(json.dumps({"x": {"pt": "y"}}), encoding="utf-8")
            b.write_text(json.dumps({"_meta": {"game_version": "9.9"}}), encoding="utf-8")
            self.assertEqual(build.data_versions([a, Path(t) / "missing.json"]),
                             {"wiki": build.WIKI_GAME_VERSION, "game": build.GAME_TEXT_VERSION})
            self.assertEqual(build.data_versions([a, b]), {"wiki": build.WIKI_GAME_VERSION, "game": "9.9"})
            self.assertEqual(build.page_payload({"meta": {"langs": ["pt", "en"]}, "items": {}, "stations": {}, "recipes": []},
                                                data={"wiki": "1", "game": "2"})["meta"]["data"], {"wiki": "1", "game": "2"})


@unittest.skipUnless((ROOT / "data" / "items.en.json").exists() and (ROOT / "data" / "recipes.en.json").exists(),
                     "real data not present")
class RealData(unittest.TestCase):
    def test_real_build(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)
            rc, so, se = run(BUILD, "--out-dir", out, "--built", "2026-01-01", "--no-src")
            self.assertIn(rc, (0, 1), se)
            self.assertNotIn("Traceback", se)
            ds = read_json(out / "gk2.json") if (out / "gk2.json").exists() else None
            if rc == 0:
                self.assertIsNotNone(ds)
                self.assertLess((out / "gk2.min.json").stat().st_size, 2_000_000)
                for r in ds["recipes"]:
                    self.assertIn(r["out"]["item"], ds["items"])
                    for i in r["in"]:
                        self.assertIn(i["item"], ds["items"])
                self.assertEqual(run(VALIDATE, out / "gk2.json", "--quiet")[0], 0)
            print(f"\n[real data] {so.strip().splitlines()[0] if so.strip() else se.strip()[:300]}", file=sys.stderr)


class RealShell(unittest.TestCase):
    """The app shell (src/index.html, header/footer CSS, router): phones keep the tabs, the page paints early."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.html = build.assemble(cls.src, payload='{"schema":1}', warn=False)
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_shell_paints_before_the_data(self):
        """UX review #9: header, tab band, footer and the "Carregando" line come before the data block; the
        modules come after it (GK.data.load reads it at boot)."""
        h = self.html
        order = [h.index(x) for x in ('<header class="top" id="top">', 'id="tabs-band"', 'id="boot-msg"',
                                      '<footer class="wrap foot"', '<script id="gk2-data" type="application/json">{"schema":1}</script>',
                                      "<script>\n")]
        self.assertEqual(order, sorted(order))
        self.assertIn('getElementById("boot-msg")', self.read("js/app.js"))
        # the build still finds the tag by id after the move (legacy --inject path)
        self.assertEqual(len(build.SCRIPT_RE.findall(h)), 1)
        self.assertIn('"schema":2', build.fill_data(h, '{"schema":2}', "test"))

    def test_tabs_sticky_mobile(self):
        """UX review #2: below 900 px only the tab band is sticky (44 px tabs); the header is sticky from 900 px."""
        hdr, resp = self.read("css/header.css"), self.read("css/responsive.css")
        band = re.search(r"\.tabs-mob-band \{(.*?)\}", hdr, re.S).group(1)
        self.assertIn("position: sticky", band)
        top = re.search(r"\n\.top \{(.*?)\}", hdr, re.S).group(1)
        self.assertNotIn("sticky", top)
        wide = resp.split("@media (min-width: 900px) {", 1)[1].split("\n}", 1)[0]
        self.assertRegex(wide, r"\.top \{ position: sticky;")
        self.assertIn(".tabs-mob-band { display: none; }", wide)
        self.assertIn("min-height: var(--tap)", re.search(r"\n\.tab \{(.*?)\}", hdr, re.S).group(1))
        # the search row sits after the band in the template; ui/header.js moves it into the header from 900 px
        self.assertLess(self.html.index('id="tabs-band"'), self.html.index('data-panel="search"'))
        hj = self.read("js/ui/header.js")
        self.assertIn('matchMedia("(min-width: 900px)")', hj)
        self.assertIn("top.appendChild(row)", hj)
        self.assertRegex(hj, r"(band|at)\.after\(row\)")   # 1.4.1: after the stale-data band when there is one

    def test_router_scroll_per_screen(self):
        """UX review #7: a screen change no longer keeps the old screen's scroll position."""
        r = self.read("js/router.js")
        apply = r.split("function apply()", 1)[1].split("function init()", 1)[0]
        self.assertIn("pos[shown] = window.scrollY", apply)
        self.assertIn("window.scrollTo(0, want)", apply)
        self.assertLess(apply.index("window.scrollTo(0, want)"), apply.index("subs.forEach"))   # modules can still place the page
        self.assertIn('GK.router.forget("days")', self.read("js/ui/days.js"))

    def test_footer_links_tap_area(self):
        css = self.read("css/components.css")
        self.assertRegex(css, r"\.foot-links a \{[^}]*min-height: var\(--tap\)")
        self.assertIn('<nav class="foot-links"', self.read("js/ui/footer.js"))

    def test_control_frame_contrast(self):
        """UX review, accessibility 2: control borders >= 3:1 against the card they sit on, both themes."""
        def lum(hx):
            c = [int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        ratio = lambda a, b: (max(lum(a), lum(b)) + .05) / (min(lum(a), lum(b)) + .05)
        tok = self.read("css/tokens.css")
        dark = dict(re.findall(r"--([\w-]+): (#[0-9a-f]{6});", tok.split("@media", 1)[0]))
        light = dict(re.findall(r"--([\w-]+): (#[0-9a-f]{6});", tok.split(':root[data-theme="light"]', 1)[1]))
        for name, t in (("dark", dark), ("light", light)):
            for ground in ("panel", "panel-2", "bg-2"):
                self.assertGreaterEqual(ratio(t["frame"], t[ground]), 3.0, (name, ground))


class PlannerUx(unittest.TestCase):
    """UX review of the Planejador (docs/revisao-ux/app.md #1, #3, #4, #5, #6, #8, #10): order on phones, compact
    goal and raw rows, first use, "Tudo" with undo, numbered station cards, short recipe labels."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_planner_order_mobile(self):
        """#1: below 900 px the progress card (perks, "Copiar lista") goes after raw materials, steps and techs."""
        css = self.read("css/planner.css")
        phone = css.split("@media (max-width: 899px) {", 1)[1].split("\n}", 1)[0]
        self.assertIn('.col-plan > [data-panel="checklist"] { order: 10; }', phone)
        main = self.read("index.html").split("<main>", 1)[1].split("</main>", 1)[0]
        order = [main.index(x) for x in ('data-slot="planner-top"', 'data-panel="goals"', 'data-panel="checklist"',
                                         'data-panel="summary"', 'data-slot="planner-extra"')]
        self.assertEqual(order, sorted(order))   # desktop keeps the DOM order; only CSS reorders the phone column
        self.assertIn("todayCollapsed: true", self.read("js/store.js"))   # #4c: Hoje starts as one line

    def test_planner_goal_rows_one_line(self):
        """#3, redone in 1.8.x (protos/metas-quantidade, opção 2): "− N +" on the name's line at every width (no more
        second line under 480 px); no separate ✕: at quantity 1 the "−" is a red ✕ that removes the goal, labelled
        "Remover <nome>" / "Remove <name>"; names wrap at whole words."""
        css, g = self.read("css/planner.css"), self.read("js/ui/goals.js")
        for gone in ("@container goals", "container: goals", ".goal-ctl"):
            self.assertNotIn(gone, css, gone)
        for gone in ("goal-ctl", 'id="rm-'):
            self.assertNotIn(gone, g, gone)
        self.assertRegex(css, r"\n\.goal \{[^}]*grid-template-columns: 40px minmax\(0, 1fr\) auto;")
        self.assertIn(".goal > .stepper { grid-column: 3; }", css)
        self.assertRegex(css, r"\.stepper button\.st-rm \{[^}]*color: var\(--blood\)")
        self.assertIn("g.qty <= 1", g)
        self.assertIn('class="st-rm" id="dec-${id}" data-remove="${esc(g.item)}" aria-label="${esc(t("goals.remove", { name: nm }))}">✕</button>', g)
        self.assertIn('id="dec-${id}" data-dec="${esc(g.item)}" aria-label="${esc(t("goals.dec", { name: nm }))}">−</button>', g)
        self.assertIn('id="inc-${id}" data-inc="${esc(g.item)}" aria-label="${esc(t("goals.inc", { name: nm }))}">+</button>', g)
        for k, pt, en in (("goals.dec", "Diminuir", "Decrease"), ("goals.inc", "Aumentar", "Increase"), ("goals.remove", "Remover {name}", "Remove {name}")):
            self.assertRegex(g, r'"%s": "%s' % (re.escape(k), re.escape(pt)))
            self.assertRegex(g, r'"%s": "%s' % (re.escape(k), re.escape(en)))
        # a hold that runs "−" down to 1 does not remove the goal with the click that ends it
        self.assertIn("(b.dataset.dec || b.dataset.inc || b.dataset.remove) && swallowClick", g)
        # the ✕ removes with "Desfazer" (the app's undo toast); "Limpar metas" keeps its two-tap confirmation
        self.assertIn("else if (b.dataset.remove) removeWithUndo(b.dataset.remove);", g)
        self.assertNotIn("A.removeGoal(", g)
        self.assertIn('GK.ui.fmt.undoToast(t("goals.removed", { name: nm }), () => {', g)
        self.assertIn("S().actions.restoreGoal(goal, at,", g)
        self.assertIn('"goals.removed": "Saiu das metas: {name}"', g)
        self.assertIn('"goals.removed": "Removed from goals: {name}"', g)
        self.assertIn("restoreGoal(goal, index, example) {", self.read("js/store.js"))
        self.assertIn('t(confirming ? "goals.confirm" : "goals.clear")', g)
        name = re.search(r"\n\.goal-name \{(.*?)\}", css).group(1)
        self.assertIn("overflow-wrap: normal", name)
        self.assertIn("hyphens: auto", name)

    def test_planner_raw_rows_compact(self):
        """#5: "como obter" on one line (full text in the title), "Já tenho" on the row, ✎ only in "Editar nomes"."""
        css, s, f = self.read("css/planner.css"), self.read("js/ui/summary.js"), self.read("js/ui/fmt.js")
        self.assertRegex(css, r"\.row-obtain \{[^}]*text-overflow: ellipsis")
        self.assertIn('class="row-line2"', s)
        self.assertIn('class="row-sub row-obtain"', s)
        self.assertIn("const pencil = canEdit ?", f)
        self.assertIn("editNames", self.read("js/store.js"))
        self.assertIn('id="edit-names"', self.read("js/ui/checklist.js"))

    def test_planner_have_all_undo(self):
        """#6: "Tudo" shows "<item>: você já tem tudo · Desfazer" and moves the focus to the next row."""
        s, f = self.read("js/ui/summary.js"), self.read("js/ui/fmt.js")
        body = s.split("function haveAll(btn) {", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn("GK.ui.fmt.undoToast(", body)
        self.assertIn("target.focus()", body)
        self.assertIn('"have.allToast": "{name}: você já tem tudo"', s)
        self.assertIn("function undoToast(msg, onUndo)", f)
        self.assertIn('"undo.button": "Desfazer"', f)
        self.assertIn(".toast-undo[hidden] { display: none; }", self.read("css/screens.css"))

    def test_planner_stations_numbered_and_labels(self):
        """#8 + #10: cards numbered in display order (no "etapa N" depth badge); recipe labels without the letter
        or the repeated "receita: …" line."""
        s, f = self.read("js/ui/summary.js"), self.read("js/ui/fmt.js")
        self.assertIn('class="station-n tabnum"', s)
        self.assertNotIn('"steps.stage"', s)
        self.assertNotIn('"steps.recipeName"', s)
        self.assertNotIn("String.fromCharCode(65", f)
        self.assertIn("today-pick-name", self.read("js/ui/today.js"))   # quick win: names under the day medallions

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_planner_example_replaced_by_first_goal(self):
        """#4b: the first goal added replaces the example list; restoreExample brings it back (goals + checks)."""
        harness = "global.window = global;\n" + self.read("js/core.js") + \
            '\nGK.i18n = { LANGS: [{ code: "pt" }, { code: "en" }] };\n' + self.read("js/store.js") + r"""
const S = GK.store, metas = [];
S.subscribe((s, m) => metas.push(m));
S.actions.seedExample([{ item: "crate", qty: 3 }, { item: "furnace-i", qty: 1 }]);
S.actions.toggleDone("raw:log", true);
S.actions.addGoal("wine", 1);
const snap = metas[metas.length - 1].exampleReplaced;
const after = { goals: S.get().goals, example: S.get().example, done: S.get().done };
S.actions.restoreExample(snap);
const back = { goals: S.get().goals, example: S.get().example, done: S.get().done };
S.actions.addGoal("wine", 1); S.actions.addGoal("wine", 1);
const twice = { goals: S.get().goals, replaced: !!metas[metas.length - 1].exampleReplaced };
console.log(JSON.stringify({ after, back, twice, ui: S.get().ui }));
"""
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "h.js"
            p.write_text(harness, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["after"], {"goals": [{"item": "wine", "qty": 1}], "example": False, "done": {}})
        self.assertEqual(out["back"], {"goals": [{"item": "crate", "qty": 3}, {"item": "furnace-i", "qty": 1}],
                                       "example": True, "done": {"raw:log": True}})
        self.assertEqual(out["twice"], {"goals": [{"item": "wine", "qty": 2}], "replaced": False})
        self.assertTrue(out["ui"]["todayCollapsed"])
        self.assertFalse(out["ui"]["editNames"])


class TodayFeatures(unittest.TestCase):
    """docs/revisao-ux/ideias.md #2-#3 in the Hoje panel and the Dias card: "feito hoje" ticks (GK.store dayDone) and
    "Bilhete do dia" (GK.store dayNotes). "Amanhã" (#1) left the Hoje panel in 1.6.0 (TodayCompact). The store / sync
    rules are tested in test_calc.mjs."""

    KEYS = {
        "js/ui/today.js": ("today.doneN", "today.check", "today.allDone", "today.note", "today.unsure"),
        "js/ui/days.js": ("days.note.label", "days.note.add", "days.note.edit", "days.note.editX", "days.note.ta",
                          "days.note.ph", "days.note.count", "days.note.saved", "days.note.cleared"),
    }

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def lang_keys(self, f):
        """{lang: {key: text}} of a module's GK.i18n.add block."""
        block = self.read(f).split("GK.i18n.add({", 1)[1].split("\n});", 1)[0]
        pt, en = block.split("\n  en: {", 1)
        grab = lambda b: dict(re.findall(r'^\s+"([a-zA-Z]+\.[\w.]+)": "((?:[^"\\]|\\.)*)",?$', b, re.M))
        return {"pt": grab(pt), "en": grab(en)}

    def test_i18n_keys_in_both_languages(self):
        for f, keys in self.KEYS.items():
            k = self.lang_keys(f)
            for key in keys:
                self.assertTrue(k["pt"].get(key), f"{f}: {key} missing in pt")
                self.assertTrue(k["en"].get(key), f"{f}: {key} missing in en")
                # same placeholders in both languages
                self.assertEqual(sorted(re.findall(r"\{\w+\}", k["pt"][key])), sorted(re.findall(r"\{\w+\}", k["en"][key])), key)
            self.assertEqual(set(k["pt"]), set(k["en"]), f"{f}: pt and en define different keys")
        self.assertEqual(self.lang_keys("js/ui/days.js")["pt"]["days.note.add"], "Deixar um bilhete para este dia")

    def test_state_and_sync(self):
        store, sync = self.read("js/store.js"), self.read("js/sync.js")
        synced = re.search(r"const SYNCED = \[(.*?)\];", store).group(1)
        self.assertIn('"dayDone"', synced)
        self.assertIn('"dayNotes"', synced)
        self.assertIn("const SCHEMA = 5;", store)   # 1.3.4 fields were additive; schema 5 = lists (migrated, test_calc.mjs)
        self.assertIn("dayDone: cleanDone(o.dayDone, day, dayNumber), dayNotes: cleanNotes(o.dayNotes)", store)
        for fn in ("toggleDayDone(", "setDayNote(", "function keepLate(", "function adoptLate("):
            self.assertIn(fn, store)
        self.assertIn("S().keepLate(", sync)
        self.assertIn("S().adoptLate(", sync)
        self.assertIn("mergeSynced(S().syncPayload(st), fields, d.updatedAt > st.updatedAt, base)", sync)
        # lists (schema 5): synced by id, the open list stays per device, the flat mirror is never an unknown field
        self.assertIn('"lists", "listsGone"', synced)
        self.assertNotIn("activeList", synced)
        self.assertIn("S().MIRROR.indexOf(k) < 0", sync)
        self.assertIn("sanitizeRemote(d.state, false, d.updatedAt)", sync)
        self.assertIn("css/lists.css", self.read("manifest.json"))

    def test_panel_markup(self):
        today, days = self.read("js/ui/today.js"), self.read("js/ui/days.js")
        self.assertIn('<label class="tick today-tick"><input type="checkbox"', today)   # 44 px target (.tick)
        self.assertIn('DY().noteBox("today"', today)
        self.assertIn('noteBox("days"', days)
        self.assertIn('maxlength="${MAX}"', days)

    def test_css_in_rem(self):
        css = self.read("css/days.css")
        for sel in (".today-ev-t", ".day-note-ta", ".day-note-add", ".today-all", ".today-tick", ".today-note-btn"):
            self.assertIn(sel, css)
        rules = [ln for ln in css.splitlines() if ".days-hub-" not in ln]   # SVG text: px are user units there
        self.assertEqual([ln for ln in rules if re.search(r"font(-size)?:[^;]*\b\d+px", ln)], [], "font sizes in rem")


class TodayCompact(unittest.TestCase):
    """The leaner Hoje panel (1.6.0, docs/revisao-ux/shots-hoje/comparacao.html): one line per event that opens in
    place, ticks only on tasks, no "Amanhã", the note as a ✎ button by the count, a short "?" for "não confirmado"."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_no_tomorrow(self):
        today, css = self.read("js/ui/today.js"), self.read("css/days.css")
        for gone in ("today-tmr", "today.tomorrow", "DY().next(", "function tomorrow("):
            self.assertNotIn(gone, today, gone)
        self.assertNotIn(".today-tmr", css)
        self.assertIn("next(day)", self.read("js/ui/days.js"))   # the week helper stays (Dias screen)

    def test_one_line_rows(self):
        today, css = self.read("js/ui/today.js"), self.read("css/days.css")
        body = today.split("function shortText(ev) {", 1)[1].split("\n  }", 1)[0]
        self.assertIn('text.indexOf(": ")', body)   # "Nome (Lugar): detalhe" -> "Nome (Lugar)"
        self.assertIn("if (ev.short) return name(ev.short);", body)   # the hand-written title wins
        self.assertIn('data-today-ev="${i}" aria-expanded="${open}" aria-controls="today-more-${i}"', today)
        self.assertIn('<div class="today-more" id="today-more-${i}"${open ? "" : " hidden"}>', today)
        self.assertIn("DY().eventMore(ev, state, true)", today)   # same detail as the Dias card, game text open
        self.assertIn("eventMore(ev, state, false)", self.read("js/ui/days.js"))
        rule = re.search(r"\.today-ev-t \{([^}]*)\}", css).group(1)
        for decl in ("white-space: nowrap", "overflow: hidden", "text-overflow: ellipsis"):
            self.assertIn(decl, rule)
        self.assertRegex(css, r"\.today-ev-btn \{[^}]*min-height: var\(--tap\)")

    def test_ticks_only_on_tasks(self):
        today, days = self.read("js/ui/today.js"), self.read("js/ui/days.js")
        self.assertIn('${ev.task ? `<label class="tick today-tick">', today)
        self.assertIn("d.events[i].task !== false", today)   # "2/3 feitas" counts the tasks
        self.assertIn("task: e.task !== false", days)        # absent = a task (older files)

    def test_note_button_and_unsure_mark(self):
        today = self.read("js/ui/today.js")
        k = TodayFeatures.lang_keys(self, "js/ui/today.js")
        self.assertEqual(k["pt"]["today.note"], "Bilhete deste dia")
        self.assertIn('id="today-note-edit" data-note-edit="${esc(d.id)}" aria-label="${esc(t("today.note"))}"', today)
        self.assertIn("${noteBtn(d, state)}", today.split('class="h2 today-h"', 1)[1].split("\n", 1)[0])
        self.assertIn('class="today-unsure"', today)
        self.assertIn('t("today.unsure")', today)   # the opened row says it in words

    @unittest.skipUnless((ROOT / "data" / "days.json").exists(), "real days.json not present")
    def test_real_days_task_marks(self):
        doc = read_json(ROOT / "data" / "days.json")
        evs = [e for d in doc["days"] for e in d["events"]]
        self.assertTrue(all(isinstance(e.get("task"), bool) for e in evs))
        info = sorted(e["pt"][:24] for e in evs if not e["task"])
        self.assertEqual(len(info), 9, info)
        for pt in ("O sino toca", "No fim do dia, o Laborat", "O limite semanal", "Fim do dia: o programa"):
            self.assertTrue(any(x.startswith(pt) for x in info), pt)
        self.assertIn('"task": bool(e["task"])', (ROOT / "scripts" / "build_days.py").read_text(encoding="utf-8"))
        # a hand-written line title (≤ 40 letters) where the automatic one is vague or the sentence has no ": "
        for e in evs:
            title = e["pt"].split(": ", 1)[0] if ": " in e["pt"] else None
            if title is None or title in ("Fim do dia", "Exceção", "Exceções", "Início da história"):
                self.assertTrue(e.get("short"), e["pt"][:40])
            if e.get("short"):
                self.assertLessEqual(max(len(e["short"]["pt"]), len(e["short"]["en"])), 40, e["short"])


class SearchRecents(unittest.TestCase):
    """"Recentes" in the search (protótipo ideia 8, variante lista): the empty box focused lists the last items added
    to goals. The store / merge rules (state.recents, synced, global) are tested in test_calc.mjs."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_strings_and_popup(self):
        js = self.read("js/ui/search.js")
        block = js.split("GK.i18n.add({", 1)[1].split("\n});", 1)[0]
        pt, en = block.split("\n  en: {", 1)
        self.assertIn('"search.recent": "Recentes"', pt)
        self.assertIn('"search.recent": "Recent"', en)
        self.assertIn("const RECENT_SHOWN = 6;", js)
        self.assertIn("function renderRecent()", js)
        self.assertIn('class="result result-recent" role="option"', js)   # same options: tap / Enter = add()
        self.assertIn('input.addEventListener("focus", () => renderResults());', js)
        self.assertIn(".result-recent .result-name", self.read("css/header.css"))

    def test_store_field(self):
        store = self.read("js/store.js")
        synced = re.search(r"const SYNCED = \[(.*?)\];", store).group(1)
        self.assertIn('"recents"', synced)
        self.assertIn('"recents"', re.search(r"const LATE = \[(.*?)\];", store).group(1))
        self.assertIn("const RECENTS_MAX = 12;", store)
        self.assertIn("recents: cleanRecents(o.recents),", store)
        self.assertIn("pushRecent(s, item);", store.split("addGoal(item, qty) {", 1)[1].split("\n    },", 1)[0])
        for page in ("prototype/index.html", "dist/index.html"):
            html = (ROOT / page).read_text(encoding="utf-8")
            self.assertIn('"search.recent": "Recentes"', html, page)


class TypeScale(unittest.TestCase):
    """Text follows the phone's text size (docs/revisao-ux/app.md, Acessibilidade 1) and the "Letra grande" switch
    (ideias.md #13): type sizes in rem, html[data-big] raises the root, ui.bigText is a per-device flag."""

    # px kept on purpose: the letter fallback fills a fixed px icon slot; the phone wordmark is a logo
    PX_OK = (".slot-letter", ".brand-name { min-width: 0")

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_type_sizes_in_rem(self):
        bad = []
        for f in sorted((self.src / "css").glob("*.css")):
            if f.name == "days.css":
                continue   # covered by TodayFeatures.test_css_in_rem
            for n, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if any(k in ln for k in self.PX_OK):
                    continue
                if re.search(r"(font(-size)?|line-height):[^;]*\b\d+(\.\d+)?px", ln):
                    bad.append(f"{f.name}:{n}: {ln.strip()[:90]}")
        self.assertEqual(bad, [], "type sizes in rem (16 px = 1 rem)")
        # icons, sprite cells and tap targets stay in px
        tokens, comp = self.read("css/tokens.css"), self.read("css/components.css")
        self.assertIn("--tap: 44px;", tokens)
        self.assertIn(".slot img { width: 32px; height: 32px;", comp)
        self.assertIn("--s: 32px;", comp)
        self.assertIn("docs/projeto/DESIGN.md", tokens.splitlines()[0])

    def test_big_text_mode(self):
        base, store = self.read("css/base.css"), self.read("js/store.js")
        self.assertRegex(base, r"html\[data-big\] \{ font-size: 12[0-5](\.\d+)?%; \}")
        flags = re.search(r"const UI_FLAGS = \[(.*?)\];", store).group(1)
        self.assertIn('"bigText"', flags)
        synced = re.search(r"const SYNCED = \[(.*?)\];", store).group(1)
        self.assertNotIn("ui", re.findall(r'"(\w+)"', synced))   # per device, never synced
        theme, app, footer = self.read("js/theme.js"), self.read("js/app.js"), self.read("js/ui/footer.js")
        self.assertIn('root.setAttribute("data-big", "")', theme)
        self.assertIn("big };", theme)
        # applied at boot before the panels mount, and again on every store change
        self.assertLess(app.index("GK.theme.big(S.get().ui"), app.index("for (const p of GK.app.panels())"))
        self.assertIn("S.subscribe((st) => GK.theme.big(st.ui && st.ui.bigText));", app)
        self.assertIn('id="big-text" aria-pressed="${bigOn}"', footer)
        self.assertIn("setUi({ bigText:", footer)
        for lang, txt in (("pt", "Letra grande"), ("en", "Large text")):
            block = footer.split("GK.i18n.add({", 1)[1].split("\n  en: {", 1)[0 if lang == "pt" else 1]
            self.assertIn(f'"footer.bigText": "{txt}"', block)
            self.assertIn('"footer.bigTitle": "', block)
        # the phone tab band shares the row and wraps instead of hiding tabs in a sideways scroll
        header = self.read("css/header.css")
        self.assertIn(".tabs-mob-band .tabs { flex-wrap: wrap; overflow-x: visible; }", header)


class FooterNoticeQr(unittest.TestCase):
    """1.4.1: the short footer (links, Letra grande, sync chip only with an account, one version line), the stale-data
    notice (data/game-version.json embedded as meta.gameVersion, footer line + band under the tabs), the QR card
    on Créditos (wide screens with a mouse) and the two phone layout fixes of the raw-material rows."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def node(self, code):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "h.js"
            p.write_text(code, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_footer_short(self):
        f, cr = self.read("js/ui/footer.js"), self.read("js/ui/credits.js")
        render = f.split("render(state, meta) {", 1)[1]
        # three links, 44 px (components.css), Letra grande kept, sync chip hidden unless account / error
        self.assertEqual(re.findall(r'id="(foot-\w+)"', render.split("const links", 1)[1].split(";\n", 1)[0]),
                         ["foot-changelog", "foot-credits", "foot-site"])
        self.assertIn('id="big-text"', render)
        self.assertIn("const CHIP = { syncing: 1, synced: 1, error: 1 };", f)
        self.assertIn("el.hidden = !CHIP[st];", f)
        self.assertIn(".sync-chip[hidden] { display: none; }", self.read("css/planner.css"))
        # the credits line and the long note left the footer; Créditos keeps the wikily credit and gets the note
        for gone in ('"footer.data"', '"footer.note"', '"footer.dataVersion"', "NX Software", "wikily"):
            self.assertNotIn(gone, f)
        self.assertIn("(© NX Software)", cr)
        self.assertIn('"credits.data.p3": "As quantidades são as de base;', cr)
        self.assertIn('"credits.data.p4": "Dados de {date}', cr)
        # one version line: one number when wiki and game agree
        self.assertIn('"footer.line": "v{version} · dados do jogo {game}"', f)
        self.assertIn('t(game === wiki ? "footer.line" : "footer.lineMixed"', f)

    def test_game_version_embedded(self):
        gv = build.load_game_version(ROOT)
        self.assertRegex(gv["latest"], r"^\d+\.\d+$")
        self.assertTrue(gv["note"]["pt"] and gv["note"]["en"])
        page = build.page_payload({"meta": {"langs": ["pt", "en"]}, "items": {}, "stations": {}, "recipes": []},
                                  game_version=gv)
        self.assertEqual(page["meta"]["gameVersion"], gv)
        with tempfile.TemporaryDirectory() as t:
            self.assertIsNone(build.load_game_version(t))
            (Path(t) / "data").mkdir()
            (Path(t) / "data" / "game-version.json").write_text('{"latest": "soon"}', encoding="utf-8")
            with self.assertRaises(SystemExit):
                build.load_game_version(t)
        dist = (ROOT / "dist" / "index.html")
        if dist.exists():
            self.assertIn('"gameVersion":{"latest":"' + gv["latest"] + '"', dist.read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_stale_notice_logic(self):
        """latest newer than the wiki recipes: notice; equal or older: nothing. Closing is per version."""
        f, h = self.read("js/ui/footer.js"), self.read("js/ui/header.js")
        self.assertIn('const NOTICE_KEY = "gk2-companion.notice";', f)
        self.assertIn("cmpVersion(gv.latest, wiki) <= 0", f)
        self.assertIn('if (!st || closedFor() === st.latest)', f)
        self.assertIn('document.getElementById("notice-band") || band', h)
        out = self.node(r"""
global.GK = { ui: {}, util: { esc: (s) => String(s) }, app: { registerPanel() {} },
  i18n: { add() {}, t: (k) => k, lang: () => "pt" } };
""" + f + r"""
const F = GK.ui.footer, note = { pt: "nota", en: "note" };
const meta = (latest, wiki, game) => ({ gameVersion: { latest, note }, data: { wiki, game } });
console.log(JSON.stringify({
  cmp: [F.cmpVersion("1.012", "1.011"), F.cmpVersion("1.011", "1.011"), F.cmpVersion("1.009", "1.010"), F.cmpVersion("1.100", "1.011"), F.cmpVersion("2.0", "1.999")],
  real: F.stale(meta("1.011", "1.010", "1.011")),
  same: F.stale(meta("1.010", "1.010", "1.011")),
  older: F.stale(meta("1.009", "1.010", "1.011")),
  none: F.stale({ data: { wiki: "1.010" } }),
}));
""")
        self.assertEqual(out["cmp"], [1, 0, -1, 1, 1])
        self.assertEqual(out["real"], {"latest": "1.011", "wiki": "1.010", "note": "nota"})
        self.assertIsNone(out["same"])
        self.assertIsNone(out["older"])
        self.assertIsNone(out["none"])
        for lang, txt in (("pt", '"footer.stale": "O jogo já está na {latest}; as receitas daqui são da {wiki}."'),
                          ("en", '"footer.stale": "The game is on {latest}; recipes here are from {wiki}."')):
            block = f.split("GK.i18n.add({", 1)[1].split("\n  en: {", 1)[0 if lang == "pt" else 1]
            self.assertIn(txt, block)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_credits_qr(self):
        cr, css = self.read("js/ui/credits.js"), self.read("css/planner.css")
        self.assertIn('const APP_URL = "https://claude.ai/artifact/8hp57ZZTFoH6GyDQUdHZAn";', cr)
        self.assertIn('const WIDE = "(min-width: 900px) and (pointer: fine)";', cr)
        self.assertIn("if (!wide() || !GK.ui.qr) return \"\";", cr)           # no SVG made on a phone
        self.assertIn('"credits.qr.say": "Aponte a câmera do celular para abrir o app lá."', cr)
        self.assertIn(".cr-qr { display: none; }", css)
        self.assertIn("@media (min-width: 900px) and (pointer: fine) {", css)
        man = read_json(self.src / "manifest.json")["js"]
        self.assertLess(man.index("js/ui/qr.js"), man.index("js/ui/credits.js"))
        # the matrix the macOS reader (CoreImage) decoded to the app URL in the 1.4.1 screenshots
        out = self.node("global.GK = { ui: {}, util: { esc: (s) => String(s) } };\n" + self.read("js/ui/qr.js") + r"""
const M = GK.ui.qr.matrix("https://claude.ai/artifact/8hp57ZZTFoH6GyDQUdHZAn");
const s = M.map((r) => r.map((c) => (c ? 1 : 0)).join("")).join("\n");
const svg = GK.ui.qr.svg("https://claude.ai/artifact/8hp57ZZTFoH6GyDQUdHZAn", "QR");
console.log(JSON.stringify({ n: M.length, sha: require("crypto").createHash("sha256").update(s).digest("hex"),
  svg: svg.slice(0, 120), long: (() => { try { GK.ui.qr.matrix("x".repeat(200)); return "ok"; } catch (e) { return "throws"; } })() }));
""")
        self.assertEqual(out["n"], 33)
        self.assertEqual(out["sha"], "1e3dd931acb6bfedb1b272a49c4536e00f2517b73c75480d6b940de5b7d5c08a")
        self.assertIn('viewBox="-4 -4 41 41"', out["svg"])
        self.assertIn('role="img" aria-label="QR"', out["svg"])
        self.assertEqual(out["long"], "throws")

    def test_raw_row_phone_fixes(self):
        """A recipe selector never widens a raw row past the screen (1.8.0: choosers and the "Tenho N de M" field
        sit on a line of their own, .row-more, under "como obter")."""
        css, f = self.read("css/planner.css"), self.read("js/ui/fmt.js")
        self.assertIn(".row-raw { padding-block: 6px; row-gap: 2px; min-height: 0; }", css)
        self.assertRegex(css, r"\.row-raw > \.row-more \{[^}]*min-width: 0; max-width: 100%;")
        self.assertIn('class="row-actions row-more"', self.read("js/ui/summary.js"))
        self.assertIn(".row-actions .select-wrap select { flex: 1 1 0; width: 0; }", css)
        self.assertRegex(css, r"\.select-wrap select \{[^}]*max-width: 100%")
        self.assertIn("n.split(/ from /i)[0].trim()", f)
        self.assertNotIn('" [" + list[k].id + "]"', f)


class FactsBuild(unittest.TestCase):
    """scripts/build_facts.py (wiki item pages -> data/facts.json) and build.apply_facts (-> gk2.json)."""

    @classmethod
    def setUpClass(cls):
        cls.facts = load_mod("gk2_facts_t", HERE / "build_facts.py")

    def mini(self):
        raw = {"rows": [
            {"key": "pie", "data": {"stack": 30, "energy": 20, "insanity": -3,
                                    "statStrip": [{"subtitle": "Energy", "chips": ["+22 with Steamed Up"]}],
                                    "buffs": [{"title": "Building spirit II", "subtitle": "For 7 min 30 s",
                                               "chips": ["+2 Building mastery", "Using another restarts the timer"]}],
                                    "soldBy": [{"title": "Baker (Bronze)", "subtitle": "Sells it", "chips": ["From trader level 3"]},
                                               {"title": "Baker (Gold)", "subtitle": "Sells it", "chips": ["From trader level 2"]},
                                               {"title": "Harold", "subtitle": "Sells it in conversation, no shop"}]}},
            {"key": "fish", "data": {"stack": 20, "otherSources": [
                {"kind": "Fishing", "title": "Village fishing spot", "href": "/locations/village",
                 "chips": ["No bait: 1% by day, 0.5% at night", "Worm Bait: 40%, day and night"]},
                {"kind": "Barracks", "title": "Tower", "href": "/buildings/tower"},
                {"kind": "Gathering", "title": "Tree", "href": "/map"},
                {"kind": "Container", "title": "Chest", "href": "/items/pie"},
                {"kind": "Quest", "title": "Sweet Dreams", "href": "/quests/sweet-dreams"}]}},
            {"key": "ghost", "data": {"stack": 5}},
        ]}
        items = [{"id": "pie"}, {"id": "fish"}, {"id": "worm-bait"}]
        game = {"Bakery_t1": {"en": "Baker", "pt": "Padeiro"}, "wz_village": {"en": "Village", "pt": "Aldeia"},
                "buff_sauna": {"en": "Steamed Up", "pt": "Aquecido"},
                "buff_talent_orange_2": {"en": "Building spirit II", "pt": "Espírito da Engenharia II"},
                "buff_talent_orange_2_d": {"en": 'You temporarily have +2 <sprite name="talent_orange">.',
                                           "pt": 'Você tem temporariamente +2 <sprite name="talent_orange">.'}}
        return self.facts.build(raw, items, self.facts.Texts(game, {}))

    def test_build_facts_shapes(self):
        doc, warnings = self.mini()
        self.assertEqual(self.facts.validate(doc), [])
        pie, fish = doc["items"]["pie"], doc["items"]["fish"]
        # trader grades collapse to one line with the lowest level; conversation-only sellers are flagged
        self.assertEqual(pie["where"], [["buy", "baker", 2], ["buy", "harold", "talk"]])
        self.assertEqual(pie["use"], {"en": 20, "enB": [22, "steamed-up"], "ins": -3,
                                      "buff": ["building-spirit-ii", 450, 1]})
        self.assertEqual(pie["stack"], 30)
        # fishing keeps the best bait of the spot; Barracks is skipped; item links become "@id"; shops first
        self.assertEqual(fish["where"], [["fish", "village", "worm-bait", 40, 40], ["gather", "tree"],
                                         ["container", "@pie"], ["quest", "sweet-dreams"]])
        self.assertNotIn("ghost", doc["items"])
        self.assertFalse(any("ghost" in w for w in warnings))   # not a known item, no sources: skipped silently
        n = doc["names"]
        self.assertEqual(n["baker"], {"en": "Baker", "pt": "Padeiro", "key": "Bakery_t1"})
        self.assertEqual(n["tree"]["tr"], "machine")                    # hand glossary
        self.assertEqual(n["sweet-dreams"]["tr"], "missing")            # nothing: English, flagged
        b = doc["buffs"]["building-spirit-ii"]
        self.assertEqual(b["d"]["pt"], "Você tem temporariamente +2 Engenharia.")
        self.assertEqual(b["d"]["en"], "You temporarily have +2 Building mastery.")
        self.assertEqual(doc["buffs"]["steamed-up"]["pt"], "Aquecido")

    def test_build_facts_sell_study_asked(self):
        """Ficha do item: who buys it (+ base / fixed price), Study Table points, quests / town uses that ask for it."""
        raw = {"rows": [
            {"key": "bronze", "data": {"price": 75, "statStrip": [{"subtitle": "Base price"}],
             "boughtBy": [{"title": "Jeweler", "chips": ["Level 1: pays 55 bronze at its usual stock", "Level 3: pays 56 bronze at its usual stock",
                                                         "Level 1: up to +10 Likes a week: +0.25 for each of 40 sold",
                                                         "Level 3: up to +40 Likes a week: +0.25 for each of 160 sold"]},
                          {"title": "Alchemist", "chips": ["From trader level 3", "Pays 1 silver 37 bronze at its usual stock",
                                                           "Up to +30 Likes a week: +3 for each of 10 sold (from trader level 2)"]},
                          {"title": "Baker", "chips": ["Pays only 1 bronze: its usual stock is 0", "Selling it earns Likes"]},
                          {"title": "Smithy"}],
             "studyCards": [{"title": "+30", "subtitle": "Red tech points"}, {"title": "+20", "subtitle": "Blue tech points"},
                            {"title": "3", "subtitle": "Science it costs"}, {"title": "7", "subtitle": "Ticks"}],
             "usedIn": [{"kind": "Town", "title": "Jeweler II", "qty": "5"}, {"kind": "Repair", "title": "Broken Ladder", "qty": "2"},
                        {"kind": "Order", "title": "Baker (level 3)", "qty": "10", "chips": ["+40 Likes (60 with Happy supplier)"]},
                        {"kind": "Order", "title": "Baker (level 3)", "qty": "10", "chips": ["+75 Likes", "Urgent"]},
                        {"kind": "Order", "title": "Jeweler", "qty": "4", "chips": ["Repeatable"]}]}},
            {"key": "fishy", "data": {"price": 72, "statStrip": [{"subtitle": "Fixed price"}], "boughtBy": [{"title": "Fish Stand"}],
                                      "studyCards": [{"title": "+50", "subtitle": "Green tech points"}, {"title": "3", "subtitle": "Science it costs"},
                                                     {"title": "2", "subtitle": "Faith it costs"}]}},
            {"key": "lonely", "data": {"price": 9, "stack": 10}},
        ]}
        quests = {"rows": [
            {"key": "yummies", "data": {"name": "Yummies", "giver": "Village guards", "storyOrder": 10,
                                        "needs": [{"href": "/items/bronze", "qty": "2", "note": "Hand over"},
                                                  {"href": "/items/fishy", "qty": "1", "note": "Given to you for this"},
                                                  {"href": "", "qty": "", "note": "Reputation needed"}]}},
            {"key": "first", "data": {"name": "First Steps", "giver": "Hans", "storyOrder": 1,
                                      "needs": [{"href": "/items/bronze", "qty": "", "note": "Have it with you"}]}},
        ]}
        items = [{"id": "bronze"}, {"id": "fishy"}, {"id": "lonely"}]
        doc, _ = self.facts.build(raw, items, self.facts.Texts({"Jewelry_t1": {"en": "Jeweler", "pt": "Joalheiro"}}, {}), quests)
        self.assertEqual(self.facts.validate(doc), [])
        b, f = doc["items"]["bronze"], doc["items"]["fishy"]
        # [trader, lo, hi, likes, likes level, level]: levels collapse to a range; silver is 100 bronze; an
        # empty-stock price counts only alone; "earns Likes" without a number is -1; no chips = just the trader
        self.assertEqual(b["sell"], [["jeweler", 55, 56, 40], ["alchemist", 137, 0, 30, 2, 3], ["baker", 1, 0, -1], ["smithy"]])
        self.assertEqual((b["price"], "fix" in b), (75, False))
        self.assertEqual((f["sell"], f["price"], f["fix"]), ([["fish-stand"]], 72, 1))
        self.assertNotIn("price", doc["items"]["lonely"])          # nobody buys it: no base price
        self.assertEqual(b["study"], [30, 0, 20, 3])
        self.assertEqual(f["study"], [0, 50, 0, 3, 2])
        # quests in story order (giver interned; "given to you" skipped; no qty = 1), town restorations, orders
        # (urgent + normal of one level merged with the most Likes); repairs left out
        self.assertEqual(b["asked"], {"q": [["first-steps", 1, "hans"], ["yummies", 2, "village-guards"]],
                                      "t": [["jeweler-ii", 5]], "o": [["baker", 10, 3, 75], ["jeweler", 4]]})
        self.assertNotIn("asked", f)
        n = doc["names"]
        self.assertEqual(n["village-guards"], {"en": "Village guards", "pt": "Guardas da vila", "tr": "machine"})
        self.assertEqual(n["hans"]["pt"], "Anselmo")                 # official game dialogue: no badge
        self.assertNotIn("tr", n["hans"])
        self.assertEqual(n["jeweler"]["pt"], "Joalheiro")
        c = doc["meta"]["counts"]
        self.assertEqual((c["sell"], c["price"], c["study"], c["asked_quest"], c["asked_town"], c["asked_order"]), (2, 2, 2, 1, 1, 1))
        # validation catches a dangling trader and a broken study row
        bad = json.loads(json.dumps(doc))
        bad["items"]["bronze"]["sell"].append(["nobody", 1])
        bad["items"]["fishy"]["study"] = [1, "x"]
        bad["items"]["fishy"]["asked"] = {"q": [["nowhere", 1]]}
        self.assertEqual(len(self.facts.validate(bad)), 3)

    def test_apply_facts(self):
        doc, _ = self.mini()
        doc["items"]["nope"] = {"stack": 1}
        ds = {"meta": {}, "items": {"pie": {"id": "pie"}, "fish": {"id": "fish"}}}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "facts.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            self.assertEqual(build.apply_facts(ds, p), 2)
            self.assertEqual(ds["items"]["pie"]["stack"], 30)
            self.assertEqual(ds["items"]["fish"]["where"][0][0], "fish")
            doc["items"]["pie"].update({"sell": [["baker", 5]], "price": 9, "study": [1, 2], "asked": {"t": [["baker", 2]]}})
            p.write_text(json.dumps(doc), encoding="utf-8")
            build.apply_facts(ds, p)
            self.assertEqual([ds["items"]["pie"][k] for k in ("sell", "price", "study", "asked")],
                             [[["baker", 5]], 9, [1, 2], {"t": [["baker", 2]]}])
            self.assertNotIn("key", ds["meta"]["refs"]["names"]["baker"])     # game keys stay in facts.json
            self.assertEqual(ds["meta"]["refs"]["buffs"]["steamed-up"]["pt"], "Aquecido")
            p.write_text("{broken", encoding="utf-8")
            ds2 = {"meta": {}, "items": {}}
            self.assertEqual(build.apply_facts(ds2, p), 0)
            self.assertNotIn("refs", ds2["meta"])
        # the page payload keeps the tables (equal pt/en collapse to one string)
        out = build.page_payload({"meta": {"langs": ["pt", "en"], "refs": {"names": {"g": {"pt": "Gunter", "en": "Gunter"}}}},
                                  "items": {}, "stations": {}, "recipes": []})
        self.assertEqual(out["meta"]["refs"]["names"]["g"], "Gunter")

    @unittest.skipUnless((ROOT / "data" / "facts.json").exists() and (ROOT / "data" / "raw" / "api-items-all.json").exists(),
                         "real data not present")
    def test_real_facts_up_to_date(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "facts.json"
            rc, so, se = run(HERE / "build_facts.py", "--out", out)
            self.assertEqual(rc, 0, se)
            self.assertEqual(out.read_text(encoding="utf-8"), (ROOT / "data" / "facts.json").read_text(encoding="utf-8"),
                             "data/facts.json is stale: run python3 -I scripts/build_facts.py")
        c = read_json(ROOT / "data" / "facts.json")["meta"]["counts"]
        self.assertGreaterEqual(c["where"], 250)
        self.assertEqual((c["buy"], c["fish"], c["energy"], c["buff"]), (176, 22, 59, 14))
        self.assertGreaterEqual(c["stack"], 540)
        # ficha do item (docs/revisao-ux/dados-ficha.md): 197 bought, 333 studied, 39 cost Faith, 81 asked by quests
        self.assertEqual((c["sell"], c["price"], c["study"], c["study_faith"]), (197, 197, 333, 39))
        self.assertGreaterEqual(c["sell_likes"], 70)
        self.assertEqual((c["asked_quest"], c["quests"], c["asked_town"], c["asked_order"]), (81, 60, 29, 22))

    def test_recipes_detail_uses_facts(self):
        """The item detail draws "Onde conseguir", the use tooltip and the stack; the planner files do not."""
        js = (ROOT / "src" / "js" / "ui" / "recipes.js").read_text(encoding="utf-8")
        for needle in ("function whereHtml(", "function tipHtml(", "function stackSlot(", "WHERE_CAP = 4", '"rc.where": "Onde conseguir"'):
            self.assertIn(needle, js)

    def test_recipes_detail_ficha_blocks(self):
        """Ficha do item: "Quem compra", "Estudar" (+ "Já estudei", synced) and "Pedido em" (folded) in the item detail
        only; each block returns "" without its data; the planner and the list rows do not read the new fields."""
        js = (ROOT / "src" / "js" / "ui" / "recipes.js").read_text(encoding="utf-8")
        for needle in ("function sellHtml(", "function studyHtml(", "function askedHtml(", '"rc.sell": "Quem compra"',
                       '"rc.study": "Estudar"', '"rc.studied": "Já estudei"', '"rc.asked": "Pedido em"', '"rc.sell": "Who buys it"',
                       "rc.askedWarn", 'id="rc-studied"', "setStudied(", 'class="card list rc-asked" id="rc-asked"${askedOpen ? " open" : ""}',
                       "GK.ui.tech.costHtml(cost, { big: true })"):
            self.assertIn(needle, js)
        for fn in ("sellHtml", "studyHtml", "askedHtml"):
            body = js.split(f"function {fn}(", 1)[1].split("\n  function ", 1)[0]
            self.assertIn('return "";', body, fn)
        # order in the card: where, obtain, runes, then sell and study; "Pedido em" after "Usado em"
        detail = js.split("function detailHtml(", 1)[1]
        self.assertLess(detail.index("whereHtml(it"), detail.index("sellHtml(it"))
        self.assertLess(detail.index("sellHtml(it"), detail.index("studyHtml(it"))
        self.assertLess(detail.index("${usedHtml}"), detail.index("${askedHtml(it, state)}"))
        row = js.split("function rowHtml(", 1)[1].split("\n  function ", 1)[0]
        for f in (".sell", ".study", ".asked"):
            self.assertNotIn(f, row)
        for f in ("summary.js", "goals.js", "fmt.js"):
            src = (ROOT / "src" / "js" / "ui" / f).read_text(encoding="utf-8")
            for k in (".sell", ".study", ".asked", "studied"):
                self.assertNotIn(k, src, f"{f} reads {k}")
        css = (ROOT / "src" / "css" / "recipes.css").read_text(encoding="utf-8")
        for needle in (".sell-list", ".study-done", ".study-done .tick { margin-left: -10px; }", ".rc-asked > summary", ".coin-s", ".coin-g"):
            self.assertIn(needle, css)
        # 1.8.0: the -10px of "Já estudei" no longer moves every checkbox of the app (Tecnologias, Hoje, Planejador)
        self.assertNotRegex(css, r"(^|\n)\.tick \{[^}]*margin-left")
        store = (ROOT / "src" / "js" / "store.js").read_text(encoding="utf-8")
        self.assertIn('"researched", "studied",', store)
        self.assertIn('const LATE = ["dayDone", "dayNotes", "recents", "studied"];', store)
        for f in ("summary.js", "goals.js", "fmt.js"):
            self.assertNotIn(".where", (ROOT / "src" / "js" / "ui" / f).read_text(encoding="utf-8"))



class Cuts160(unittest.TestCase):
    """1.6.0: the 16 approved noise cuts (docs/revisao-ux/simplificar.md §2, prototypes in protos/cortes/) and the
    "Recentes" fix (qa-2026-11 médio 1). Source-level checks on src/, plus GK.ui.fmt.buildLabel / techLine in node."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_steps_rows(self):
        """Cortes 1-4: "×2 ▾" opens "Tenho __ de 2"; short tech line; the "Por execução" line is the recipe picker;
        crafts only when they differ from the quantity."""
        s, f, css = self.read("js/ui/summary.js"), self.read("js/ui/fmt.js"), self.read("css/planner.css")
        self.assertIn('class="row-qty qty-btn"', s)
        self.assertIn('"steps.qtyLabel"', s)
        for gone in ('"steps.hint"', '"raw.hint"', '"steps.recipe":', '"steps.have"', '"fold.raw.', '"fold.steps.'):
            self.assertNotIn(gone, s, gone)
        self.assertIn("function stepPicker(", s)
        self.assertIn('class="row-in step-pick"', s)
        self.assertIn("s.runs > 1 && s.runs !== s.need", s)
        self.assertIn("function techLine(r, state)", f)
        for gone in ('"steps.tech"', '"steps.mastery"', '"steps.ext"', "infoButton("):
            self.assertNotIn(gone, f, gone)
        self.assertIn("GK.tech.researchedSet", f)
        self.assertRegex(css, r"\.step-pick select \{[^}]*opacity: 0")
        self.assertRegex(css, r"\.qty-btn \{[^}]*min-height: var\(--tap\)")

    def test_planner_spacing(self):
        """Spacing pass after 1.6.0 (docs/revisao-ux/shots-espacos): the section toggles keep 8 px above their card and
        sit on the 12 px line of the controls inside; the station toggle and "×2 ▾" end on that line too, with no
        negative margins pulling "×2 ▾" up against the station band; a row's icon and tick sit at the top, beside the
        name; 8 px between a raw row's quantity and its "Já tenho"; the 44 px targets stay."""
        css = self.read("css/planner.css")
        self.assertIn(".summary-grid .fold-head { margin-bottom: var(--s2); }", css)
        self.assertIn(".summary-grid .fold-head > .fold-btn { margin-right: calc(var(--s3) + 1px); }", css)
        self.assertRegex(css, r"\.station-h \{[^}]*padding: var\(--s2\) var\(--s3\);")
        self.assertNotRegex(css, r"\.station-h\[data-fold-head\] \{[^}]*padding-right")
        qty = re.search(r"\.row-qty\.qty-btn \{([^}]*)\}", css).group(1)
        self.assertIn("margin: 0 0 0 var(--s1);", qty)
        self.assertIn("min-height: var(--tap); min-width: var(--tap);", qty)
        self.assertIn(".station .row > .tick, .station .row > .slot { align-self: start; }", css)
        # 1.8.0 grade única: the raw rows, the steps (rows + station header) and "Tecnologias que faltam" share the
        # columns 12 px | 26 px (24 px checkbox) | 8 px | 40 px icon | text | controls on the 12 px line; the checkbox
        # label stays 44 px wide; raw rows: name and "como obter" 2 px apart, centred on the icon
        self.assertIn(".summary-grid .row, .tn-card .tn-row { grid-template-columns: 26px 40px minmax(0, 1fr) auto; padding-left: var(--s3); padding-right: var(--s3); }", css)
        self.assertIn(".summary-grid .row > .tick, .tn-card .tn-row > .tick { margin-left: calc(var(--s3) * -1); place-items: center end; padding-right: var(--s2); }", css)
        self.assertRegex(css, r"\.station-h \{[^}]*grid-template-columns: 26px 40px minmax\(0, 1fr\) auto auto;[^}]*column-gap: var\(--s2\)")
        self.assertIn(".station-h > .station-n { justify-self: start; margin-left: -2px; }", css)
        self.assertIn(".station-h > .slot { justify-self: center; }", css)
        self.assertIn(".row-raw > .tick, .row-raw > .slot { grid-row: 1 / span 2; align-self: center; }", css)
        self.assertIn(".row-raw > .row-qty { grid-column: 4; grid-row: 1 / span 2; align-self: center; line-height: 1; }", css)
        self.assertRegex(css, r"\.row-raw \{[^}]*row-gap: 2px")
        self.assertRegex(css, r"\.tick \{[^}]*width: var\(--tap\); height: var\(--tap\)")
        # the raw rows' quantity is the steps' "× N ▾"
        self.assertIn("qtyButton(r.item, nm, r.qty, open, true)", self.read("js/ui/summary.js"))
        # Metas (1.8.x, opção 2): "− N +" at the row's right end, on the same 12 px line inside the card as the "× N ▾"
        # of Matérias-primas and Etapas (x 361 at 390 px, 331 at 360 px), no margin pushing it off that line
        goal = re.search(r"\n\.goal \{([^}]*)\}", css).group(1)
        self.assertIn("padding: 6px var(--s3);", goal)
        self.assertNotRegex(css, r"\.goal[^{]*\.stepper[^{]*\{[^}]*margin")
        self.assertNotRegex(css, r"\n\.stepper \{[^}]*margin")
        self.assertRegex(css, r"\.fold-btn \{[^}]*width: var\(--tap\)")

    def test_planner_general(self):
        """Cortes 6, 8, 20, 13 (goals side): the icon opens Receitas; no stats line; perks fold; one first-use line;
        the example-replaced toast moved to search.js."""
        g, c, f, comp = self.read("js/ui/goals.js"), self.read("js/ui/checklist.js"), self.read("js/ui/fmt.js"), self.read("css/components.css")
        self.assertIn("function slotButton(", f)
        self.assertIn('class="slot slot-btn${m[1] || ""}"', f)   # 1.8.0: keeps the quality star's has-q
        self.assertIn("GK.ui.fmt.slotButton(", g)
        for gone in ("exampleGone", '"goals.intro"', "example-note", "GK.store.subscribe", "infoButton"):
            self.assertNotIn(gone, g, gone)
        self.assertIn('"goals.example": "Exemplo: busque o que quer fabricar e ele substitui esta lista."', g)
        for gone in ('class="stats"', '"stats.'):
            self.assertNotIn(gone, c, gone)
        self.assertIn('id="perks-tgl"', c)
        self.assertIn('aria-expanded="${perksOpen}"', c)
        self.assertIn(".slot.slot-btn {", comp)
        self.assertIn(".info-ico {", comp)   # the footer's stale-data "i" keeps its style
        self.assertIn('"tn.hint": "Pesquise nesta ordem; marque o que já tem."', self.read("js/ui/techneeds.js"))

    def test_days_today_search(self):
        """Cortes 7, 10, 11, 13, 14 and the Recentes fix (days.js, today.js, search.js)."""
        d, t, q = self.read("js/ui/days.js"), self.read("js/ui/today.js"), self.read("js/ui/search.js")
        for gone in ('"days.hint"', '"days.credit"', '"days.calibrated"', '"days.isToday"', "days-credit"):
            self.assertNotIn(gone, d, gone)
        self.assertIn('"days.adjust": "Ajustar o dia"', d)
        self.assertIn("data-adjust aria-expanded=", d)
        self.assertIn('"days.machineNote"', d)          # moved into "Como funciona"
        self.assertIn("function shortText(ev)", t)
        self.assertIn('class="h2 today-h"', t)
        self.assertNotIn("days.advToast", t)            # no toast from the Hoje panel; days.js keeps its own
        self.assertIn("days.advToastN", d)
        self.assertIn('"toast.added": "+ {name}"', q)
        self.assertIn('"toast.replaced": "+ {name} · exemplo removido"', q)
        self.assertIn("m && m.exampleReplaced", q)
        self.assertIn("restoreExample(snap)", q)
        self.assertIn("if (quiet || document.activeElement !== input) return false;", q)
        self.assertIn("!inList.has(id)", q)

    def test_recipes_tech_changelog(self):
        """Cortes 7, 12, 16, 17, 18 (recipes.js, tech.js, changelog.js)."""
        r, k, c, css = self.read("js/ui/recipes.js"), self.read("js/ui/tech.js"), self.read("js/ui/changelog.js"), self.read("css/screens.css")
        for gone in ('"rc.hint"', '"rc.usedInNone"'):
            self.assertNotIn(gone, r, gone)
        self.assertIn('"rc.altAll"', r)
        self.assertIn("rc-hidden-end", r)
        self.assertIn("GK.ui.fmt.buildLabel(", r)
        self.assertIn("row.n > 1", r)
        self.assertIn('"rc.placeholder": "Buscar item"', r)
        self.assertNotIn('"rc.placeholder": "Buscar entre', r)
        self.assertNotIn('"tech.recipes.', k)
        self.assertIn("missingAnc.length >= 2", k)
        self.assertIn('"tech.hint": "Marque o que já pesquisou; as anteriores contam junto."', k)
        self.assertIn("aria-expanded", c)
        self.assertIn("aria-controls", c)
        self.assertIn('"changelog.notes.one"', c)
        self.assertRegex(css, r"\.cl-toggle \{[^}]*min-height: var\(--tap\)")

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_build_label_and_tech_line(self):
        """GK.ui.fmt.buildLabel: "Construir no Cemitério" / "na Igreja" / "nas Casernas" / "em: A, B" / "Build at …";
        techLine(r, state): no prefixes, researched techs dropped, mastery level 0 = type only."""
        stub = r"""
global.window = global;
global.navigator = { language: "pt-BR" };
global.document = { addEventListener() {}, createElement() { return { style: {}, appendChild() {}, setAttribute() {} }; },
  head: { appendChild() {} }, documentElement: {}, getElementById() { return null; } };
"""
        harness = stub + self.read("js/core.js") + self.read("js/util.js") + self.read("js/i18n.js") + \
            '\nGK.i18n.add({ pt: { "search.raw": "Matéria-prima", "steps.techQuest": "Missão: {tech}", "steps.techPerk": "Vantagem: {tech}" }, en: {} });\n' + \
            'GK.tech = { available: () => true, researchedSet: (r) => new Set(Object.keys(r).filter((k) => r[k])) };\n' + \
            self.read("js/ui/fmt.js") + r"""
const F = GK.ui.fmt, z = (pt, en) => ({ id: "zone:" + en, build: true, pt, en });
const out = {};
GK.i18n.set("pt");
out.pt = [z("Cemitério", "Graveyard"), z("Igreja", "Church"), z("Casernas", "Barracks"), z("Pátio, Cemitério", "Yard, Graveyard"),
  z("Qualquer lugar", "Anywhere"), { id: "build", i18n: "station.build", build: true }, { id: "sawhorse", pt: "Cavalete", en: "Sawhorse" }].map((s) => F.buildLabel(s));
GK.i18n.set("en");
out.en = [z("Cemitério", "Graveyard"), z("Casernas", "Barracks"), z("Pátio, Cemitério", "Yard, Graveyard")].map((s) => F.buildLabel(s));
GK.i18n.set("pt");
const r = { tech: { id: "pottery-i", type: "technology", pt: "Olaria I", en: "Pottery I" }, mastery: { type: { pt: "Engenharia", en: "Building" }, level: 2 }, ext: { pt: "Foles", en: "Bellows" } };
out.line = F.techLine(r, { researched: {} });
out.lineDone = F.techLine(r, { researched: { "pottery-i": true } });
out.lineNoState = F.techLine(r);
out.level0 = F.techLine({ mastery: { type: { pt: "Anatomia", en: "Anatomy" }, level: 0 } }, { researched: {} });
out.quest = F.techLine({ tech: { id: "q", type: "quest", pt: "A missão", en: "The quest" } }, { researched: { q: true } });
console.log(JSON.stringify(out));
"""
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "h.js"
            p.write_text(harness, encoding="utf-8")
            res = subprocess.run(["node", str(p)], capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout.strip().splitlines()[-1])
        self.assertEqual(out["pt"], ["Construir no Cemitério", "Construir na Igreja", "Construir nas Casernas", "Construir em: Pátio, Cemitério",
                                     "Construir em qualquer lugar", "Construção (no local)", "Cavalete"])
        self.assertEqual(out["en"], ["Build at Graveyard", "Build at Barracks", "Build at: Yard, Graveyard"])
        self.assertEqual(out["line"], ["Olaria I", "Engenharia 2", "Foles"])
        self.assertEqual(out["lineDone"], ["Engenharia 2", "Foles"])
        self.assertEqual(out["lineNoState"], ["Olaria I", "Engenharia 2", "Foles"])
        self.assertEqual(out["level0"], ["Anatomia"])
        self.assertEqual(out["quest"], ["Missão: A missão"])

class GroupedRecipes180(unittest.TestCase):
    """1.8.0, receitas agrupadas (docs/revisao-ux/protos/receitas-agrupadas, consertos.md §10): the quality star is drawn
    in one place (GK.util.slot); the Receitas detail uses GK.calc.recipeGroups; a tap on an option sets the planner's
    recipe; the circular recipes fold; pixel coins; texts in pt and en. (The rule itself: test_calc.mjs.)"""

    @classmethod
    def setUpClass(cls):
        cls.read = lambda self, f: (ROOT / "src" / f).read_text(encoding="utf-8")

    def test_star_in_one_place(self):
        util = self.read("js/util.js")
        self.assertIn("function slot(ent, label, small, grade)", util)
        self.assertIn('<span class="qstar ${q}" aria-hidden="true"></span>', util)
        for f in ("js/ui/summary.js", "js/ui/goals.js", "js/ui/search.js", "js/ui/today.js", "js/ui/days.js", "js/ui/fmt.js"):
            self.assertNotIn("qstar", self.read(f), f)   # they all go through GK.util.slot / GK.ui.fmt.slotButton
        comp = self.read("css/components.css")
        for needle in (".slot.has-q { position: relative; }", ".slot > .qstar { position: absolute; left: 1px; top: 1px;", ".q-b {", ".q-s {", ".q-g {"):
            self.assertIn(needle, comp)

    def test_detail_groups_and_pick(self):
        js = self.read("js/ui/recipes.js")
        for needle in ("GK.calc.recipeGroups(rs, D)", "function groupCard(", 'role="radiogroup"', 'role="radio"', "data-pick=",
                       "A.chooseRecipe(r.out.item, r.id === GK.data.item(r.out.item).defaultRecipe ? null : r.id)",
                       '<details class="rc-cyc" id="rc-cyc"', '"rc.cycT": "Melhorar a qualidade"', '"rc.cycT": "Improve quality"',
                       '"rc.qMore": "E mais um destes"', '"rc.qMore": "Plus one of these"', '"rc.inUseQ": "Em uso no planejador: {what}"',
                       "GK.data.gradeSort(ids,", "GK.data.stripGrade("):
            self.assertIn(needle, js)
        group = js.split("function groupCard(", 1)[1].split("\n  function ", 1)[0]
        self.assertNotIn("data-use=", group)   # no "Usar esta receita" button in a group card: the options do it

    def test_coins_pixel(self):
        css = self.read("css/recipes.css")
        self.assertRegex(css, r"\.coin \{[^}]*width: 16px; height: 16px;")
        self.assertIn(".sell-max .coin { width: 14px; height: 14px;", css)
        self.assertNotIn("radial-gradient(circle at 35% 35%", css)
        self.assertIn('<span class="sr-only"> ${esc(t("rc.coin." + k))}</span>', self.read("js/ui/recipes.js"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
