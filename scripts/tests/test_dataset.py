#!/usr/bin/env python3
"""The dataset build (build.py --no-src -> gk2.json) on scripts/fixtures/, validate.py, and a read-only
smoke build of the real data/items.en.json + data/recipes.en.json when they exist.

Part of the build tests; run them all with:  python3 -I scripts/test_build.py
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))   # helpers.py, next to this file (python3 -I leaves it out)
from helpers import ROOT, FIX, BUILD, VALIDATE, validate, build, run, fixture_args, read_json  # noqa: E402


class FixtureBuild(unittest.TestCase):
    """Dirty fixture: one dangling ref (glue) -> hard error; built with --allow-errors."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.rc, cls.so, cls.se = run(BUILD, *fixture_args(cls.out), "--allow-errors")
        cls.ds = read_json(cls.out / "gk2.json")
        cls.rep = validate.validate(cls.ds)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exit_code_and_outputs(self):
        self.assertEqual(self.rc, 1, self.se)
        for f in ("gk2.json", "report-l10n.md", "report-build.md"):
            self.assertTrue((self.out / f).exists(), f)

    def test_schema_shape(self):
        ds = self.ds
        self.assertEqual(set(ds), {"meta", "items", "stations", "recipes", "perks"})
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

    def test_idempotent(self):
        files = ["gk2.json", "report-l10n.md", "report-build.md"]
        before = {f: (self.out / f).read_bytes() for f in files}
        mtimes = {f: (self.out / f).stat().st_mtime_ns for f in files}
        rc, so, se = run(BUILD, *[a for a in fixture_args(self.out) if a != "--quiet"], "--allow-errors")
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
                                                "note": {"pt": "5 (8 com Ferreiro)", "en": "5 (8 with Blacksmith)"},
                                                "bonus": {"perk": "Blacksmith", "perks": ["blacksmith"], "qty": 8}})
            self.assertEqual(ds["perks"]["blacksmith"], {"pt": "Ferreiro", "en": "Blacksmith", "uses": 1})
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
            self.assertEqual(build.data_versions([a, Path(t) / "missing.json"], "1.010"),
                             {"wiki": "1.010", "game": build.GAME_TEXT_VERSION})
            self.assertEqual(build.data_versions([a, b], "1.010"), {"wiki": "1.010", "game": "9.9"})
            # the wiki version is the `wiki` field of data/game-version.json
            self.assertRegex(build.load_wiki_version(ROOT), r"^\d+\.\d+$")
            self.assertIsNone(build.load_wiki_version(t))
            (Path(t) / "data").mkdir()
            (Path(t) / "data" / "game-version.json").write_text('{"latest": "1.011"}', encoding="utf-8")
            with self.assertRaises(SystemExit):
                build.load_wiki_version(t)
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
                self.assertLess(len(build.dumps_min(ds)), 2_000_000)
                for r in ds["recipes"]:
                    self.assertIn(r["out"]["item"], ds["items"])
                    for i in r["in"]:
                        self.assertIn(i["item"], ds["items"])
                self.assertEqual(run(VALIDATE, out / "gk2.json", "--quiet")[0], 0)
            print(f"\n[real data] {so.strip().splitlines()[0] if so.strip() else se.strip()[:300]}", file=sys.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
