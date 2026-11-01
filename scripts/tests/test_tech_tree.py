#!/usr/bin/env python3
"""The technology tree in the page: build.py's techs payload on an inline 3-tech tree (FIX_TECHS),
GK.tech in node, and the real data/techs.json.

Part of the build tests; run them all with:  python3 -I scripts/test_build.py
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))   # helpers.py, next to this file (python3 -I leaves it out)
from helpers import (  # noqa: E402
    ROOT, FIX, BUILD, TESTS, build, run, fixture_args, read_json, texts, extract_block, make_project)


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

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_gk_tech_module(self):
        """src/js/tech.js (GK.tech) on the fixture tree, in node with a stub GK.data (and the real GK.data.loc)."""
        ds = {"meta": {"langs": ["pt", "en"]}, "items": {"plank": {"pt": "Tábua", "en": "Plank"}}, "stations": {}}
        payload = build.techs_payload(FIX_TECHS, ds)
        harness = r"""
const GK = {};
""" + (ROOT / "src" / "js" / "data.js").read_text(encoding="utf-8") + r"""
GK.data = { get: () => D, load: (j) => j, loc: GK.data.loc };
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
        """Every build.py run in the build tests (scripts/tests/) must pass --no-src or --src: otherwise src mode
        (the default) rewrites the real prototype/ and dist/ with test data."""
        for f in sorted(TESTS.glob("*.py")):
            text = f.read_text(encoding="utf-8")
            for m in re.finditer(r"run\(BUILD,(.*?)\)\n", text, re.S):
                call = m.group(1)
                self.assertTrue(any(k in call for k in ("--no-src", '"--src"', "fixture_args", "self.build", "build_args", "*args")),
                                (f.name, call[:120]))

    def test_real_tech_modules_registered(self):
        src = ROOT / "src" / "js"
        ui, needs = (src / "ui" / "tech.js").read_text(encoding="utf-8"), (src / "ui" / "techneeds.js").read_text(encoding="utf-8")
        self.assertRegex(ui, r'GK\.router\.register\(\{ id: "tech", labelKey: "tab\.tech", screen: "tech"')
        self.assertIn('GK.app.registerPanel(GK.ui.tech, { id: "tech", panel: "tech"', ui)
        self.assertIn('slot: "planner-extra", order: 10', needs)
        for text in (ui, needs):
            self.assertNotIn("confirm(", text)
        for lang in ("pt", "en"):
            for pre in ("tech.", "tn."):
                self.assertTrue(any(k.startswith(pre) for k in texts(lang)), (lang, pre))
        self.assertIn("GK.tech = (function", (src / "tech.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
