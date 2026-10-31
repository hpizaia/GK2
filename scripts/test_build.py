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


if __name__ == "__main__":
    unittest.main(verbosity=2)
