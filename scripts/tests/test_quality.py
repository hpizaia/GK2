#!/usr/bin/env python3
"""Quality grades: the dataset keeps the grade, the plain item is the bronze one, the build hands the
grades and perk bonuses ready, and the Receitas screen groups the recipes by grade.

Part of the build tests; run them all with:  python3 -I scripts/test_build.py
"""
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))   # helpers.py, next to this file (python3 -I leaves it out)
from helpers import ROOT, build, read_json, texts, recipes_src, extract_block  # noqa: E402


class GroupedRecipes(unittest.TestCase):
    """Grouped recipes: the quality star is drawn
    in one place (GK.util.slot); the Receitas detail uses GK.calc.recipeGroups; a tap on an option sets the planner's
    recipe; the circular recipes fold; pixel coins; texts in pt and en. (The rule itself: test_calc.mjs.)"""

    @classmethod
    def setUpClass(cls):
        cls.read = lambda self, f: (ROOT / "src" / f).read_text(encoding="utf-8")

    def test_star_in_one_place(self):
        util = self.read("js/util.js")
        self.assertIn("function slot(ent, label, small, grade)", util)
        self.assertIn('`<span class="qstar ${STAR[grade]}" aria-hidden="true"></span>`', util)   # GK.util.qstar
        for f in ("js/ui/summary.js", "js/ui/goals.js", "js/ui/search.js", "js/ui/today.js", "js/ui/days.js", "js/ui/fmt.js"):
            self.assertNotIn("qstar", self.read(f), f)   # they all go through GK.util.slot / GK.ui.fmt.slotButton
        self.assertNotIn('class="qstar', recipes_src())   # the grade picks of a group card: GK.util.qstar
        comp = self.read("css/components.css")
        for needle in (".slot.has-q { position: relative; }", ".slot > .qstar { position: absolute; left: 1px; top: 1px;", ".q-b {", ".q-s {", ".q-g {"):
            self.assertIn(needle, comp)

    def test_detail_groups_and_pick(self):
        js = recipes_src()
        for needle in ("GK.calc.recipeGroups(rs, D)", "function groupCard(", 'role="radiogroup"', 'role="radio"', "data-pick=",
                       "A.chooseRecipe(r.out.item, r.id === GK.data.item(r.out.item).defaultRecipe ? null : r.id)",
                       '<details class="rc-cyc" id="rc-cyc"', "GK.data.gradeSort(ids,", "const { graded, UNOFFICIAL } = GK.ui.fmt;"):   # graded: tested in node (test_calc.mjs)
            self.assertIn(needle, js)
        pt, en = texts("pt"), texts("en")
        self.assertEqual((pt["rc.cycT"], en["rc.cycT"], pt["rc.qMore"], en["rc.qMore"], pt["rc.inUseQ"]),
                         ("Melhorar a qualidade", "Improve quality", "E mais um destes", "Plus one of these", "Em uso no planejador: {what}"))
        group = js.split("function groupCard(", 1)[1].split("\n  function ", 1)[0]
        self.assertNotIn("data-use=", group)   # no "Usar esta receita" button in a group card: the options do it

    def test_coins_pixel(self):
        css = self.read("css/recipes.css")
        self.assertRegex(css, r"\.coin \{[^}]*width: 16px; height: 16px;")
        self.assertIn(".sell-max .coin { width: 14px; height: 14px;", css)
        self.assertNotIn("radial-gradient(circle at 35% 35%", css)
        self.assertIn('<span class="sr-only"> ${esc(t("rc.coin." + k))}</span>', self.read("js/ui/recipes-facts.js"))


class QualityGrades(unittest.TestCase):
    """Quality grades: build_dataset.py keeps the
    grade of "Wine (silver)" (wine-silver, base wine; bronze = the plain item), the star crafts make every grade, and
    build.py lists a quality upgrade after the recipe that makes that grade directly."""

    @classmethod
    def setUpClass(cls):
        cls.items = {i["id"]: i for i in read_json(ROOT / "data" / "items.en.json")}
        cls.recipes = {r["id"]: r for r in read_json(ROOT / "data" / "recipes.en.json")}
        cls.ds = read_json(ROOT / "data" / "gk2.json")

    def test_dataset_keeps_the_grade(self):
        I, R = self.items, self.recipes
        for g in ("silver", "gold"):
            self.assertEqual(R[f"wine-from-grape-juice-{g}"]["output"]["item"], f"wine-{g}")
            self.assertEqual(I[f"wine-{g}"]["base_item"], "wine")
            self.assertEqual(I[f"wine-{g}"]["kind"], "quality-variant")
            self.assertEqual([i["item"] for i in R[f"grape-juice-from-grapes-{g}"]["inputs"]][0], f"grapes-{g}")
        self.assertEqual(R["wine-from-grape-juice-bronze"]["output"]["item"], "wine")       # bronze = the plain item
        self.assertEqual(R["drink-enhancement-i-from-wine-bronze"]["output"]["item"], "wine-silver")
        self.assertEqual([i["item"] for i in R["drink-enhancement-i-from-wine-bronze"]["inputs"]], ["wine", "spices"])
        self.assertTrue(R["drink-enhancement-i-from-wine-bronze"]["quality_upgrade"])
        self.assertNotIn("quality_upgrade", R["wine-from-grape-juice-silver"])
        # organ improvers stay as they were (ambiguous: "(gold)" from "Any <organ>", both levels)
        self.assertEqual(R["improve-organ-i-from-any-bones"]["output"]["item"], "bones")
        self.assertNotIn("bones-gold", I)
        # crops: the seed grade gives the harvest grade; silver / gold have a short "how to get" text
        self.assertEqual(I["cabbage-silver"]["obtain"], "Harvest: bronze or silver seeds.")
        self.assertEqual(I["grapes-gold"]["obtain"], "Harvest: silver or gold seeds.")
        self.assertEqual(R["grow-grapes-bed-m16"]["inputs"][0]["item"], "grape-seeds-gold")
        self.assertEqual(R["grow-grapes-bed-m16"]["source_url"].rsplit("/", 1)[-1], "grapes")
        # Bronze Polido: no variant, no grade
        self.assertEqual(I["polished-bronze"]["kind"], "item")
        self.assertFalse(any(k.startswith("polished-bronze-") for k in I))

    def test_star_crafts_per_grade(self):
        R = self.recipes
        for rid, fam in (("story", "story"), ("printing-press", "newspaper"), ("vegetable-salad", "vegetable-salad"),
                         ("bowl-of-sauerkraut", "bowl-of-sauerkraut")):
            self.assertEqual(R[rid]["output"]["item"], fam)
            for g in ("bronze", "silver", "gold"):
                c = R[f"{rid}-{g}"]
                self.assertEqual((c["output"]["item"], c["output"]["qty"], c["inputs"], c["star_quality"], c["type"]),
                                 (f"{fam}-{g}", R[rid]["output"]["qty"], R[rid]["inputs"], R[rid]["star_quality"], "star_craft"))
        self.assertFalse(any(r["id"].startswith("basic-prayer-") for r in R.values()))   # prayers: not a graded family

    def test_page_defaults_and_base(self):
        it = self.ds["items"]
        self.assertEqual(it["wine-silver"]["recipes"], ["wine-from-grape-juice-silver", "drink-enhancement-i-from-wine-bronze"])
        self.assertEqual(it["wine-silver"]["defaultRecipe"], "wine-from-grape-juice-silver")
        self.assertEqual(it["grape-juice-gold"]["defaultRecipe"], "grape-juice-from-grapes-gold")
        self.assertEqual(it["story-silver"]["defaultRecipe"], "story-silver")
        self.assertEqual(it["story-bronze"]["defaultRecipe"], "story-bronze")
        self.assertEqual(it["newspaper-bronze"]["defaultRecipe"], "printing-press-bronze")
        self.assertEqual((it["wine-gold"]["base"], it["cabbage-silver"]["base"]), ("wine", "cabbage"))
        self.assertNotIn("base", it["grape-juice-gold"])                 # no plain Grape Juice item
        self.assertEqual(it["cabbage-silver"]["obtain"], {"pt": "Colheita: semente bronze ou prata.", "en": "Harvest: bronze or silver seeds."})
        self.assertEqual(it["wine-silver"]["pt"], "Vinho (prata)")
        self.assertFalse(any(r["cyc"] for r in self.ds["recipes"] if r["out"]["item"].startswith(("wine", "grape-juice"))))

    def test_steps_no_grade_badge(self):
        self.assertEqual(texts("pt")["steps.starGrade"], "{grade} com {n} ciclos bem-sucedidos")


class BronzeIsPlainItem(unittest.TestCase):
    """The plain item of a graded family ("pumpkin" next to "pumpkin-silver" / "-gold") is
    the bronze one and shows as bronze: the payload's families, the page's rule and where it is drawn. (The behaviour
    itself, list, search, detail, lines: test_calc.mjs "bronze comum".)"""

    def test_page_rule_and_display(self):
        src = lambda f: (ROOT / "src" / f).read_text(encoding="utf-8")
        data = src("js/data.js")
        for needle in ("const lineGrade = (line) =>", "function gradeSort(list, famOf, rankOf, together)"):
            self.assertIn(needle, data)
        self.assertIn("def apply_grades(items, recipes):", (ROOT / "scripts" / "build_parts" / "grades.py").read_text(encoding="utf-8"))
        self.assertIn("const g = grade === false ? null : grade || (ent && ent.grade);", src("js/util.js"))   # node: test_calc.mjs
        rc = src("js/ui/recipes.js")
        self.assertIn("GK.ui.fmt.gradedName(it, nm))}</h2>", rc)
        self.assertIn("GK.data.GRADE_RANK[D.items[id].grade], true);", rc)
        self.assertIn("GK.data.GRADE_RANK[D.items[x.id].grade], true);", src("js/calc.js"))
        page = ROOT / "dist" / "index.html"
        if page.exists():
            items = json.loads(extract_block(page.read_text(encoding="utf-8")))["items"]
            plain = sorted(k for k, it in items.items() if it.get("grade") == "bronze" and it.get("kind", "item") != "quality-variant")
            self.assertEqual(plain, ["cabbage", "cabbage-seed", "grape-seeds", "grapes", "onion", "onion-seed", "pumpkin",
                                     "pumpkin-seeds", "wine"])


class GradesAndBonusBuild(unittest.TestCase):
    """2026-11: the grades and the perk bonuses come ready from the build (apply_grades, apply_bonuses, note_bonus);
    GK.data reads them as they come (test_calc.mjs "payload: the grades come ready from the build")."""

    def test_note_bonus_shapes(self):
        nb = lambda en, pt=None: build.note_bonus({"en": en, "pt": pt if pt is not None else en})
        self.assertEqual(nb("3 (5 with Cook II)", "3 (5 com Cozinheiro II)"),
                         ({"perk": "Cook II", "perks": ["cook-ii"], "qty": 5}, [("cook-ii", "Cook II", "Cozinheiro II")]))
        self.assertEqual(nb("1, or 2 with Cremator", "1, ou 2 com Cremador")[0], {"perk": "Cremator", "perks": ["cremator"], "qty": 2})
        b, names = nb("amount varies with the bed; +1 each with Farmer II and Grape Master",
                      "a quantidade varia conforme o canteiro; +1 cada com Fazendeiro II e Senhor das Uvas")
        self.assertEqual(b, {"perk": "Farmer II and Grape Master", "perks": ["farmer-ii", "grape-master"], "add": 1})
        self.assertEqual([n[2] for n in names], ["Fazendeiro II", "Senhor das Uvas"])
        self.assertEqual(nb("10 with Heat Saver", "10 com Economizador de Calor")[0], {"perk": "Heat Saver", "perks": ["heat-saver"], "qty": 10})
        self.assertIsNone(nb("50% chance with Alchemist"))                 # a chance is not a quantity
        self.assertIsNone(nb("with Mason"))
        self.assertIsNone(build.note_bonus(None))
        # the pt side does not match (or names a different count): the English names stand in
        self.assertEqual(nb("2 (3 with Cook)", "dois")[1], [("cook", "Cook", "Cook")])
        self.assertEqual(build.perk_slug("Magpie’s Eye"), "magpie-s-eye")
        # one table for the pt notes and the bonuses: every bonus shape has its pt template
        self.assertEqual(len(build.BONUS_SHAPES), 4)
        self.assertEqual(len(build.NOTE_PATTERNS_PT), len(build.NOTE_SHAPES))

    def test_apply_bonuses_perk_table(self):
        rs = [{"in": [{"item": "a", "qty": 1, "note": {"en": "2 (3 with Cook)", "pt": "2 (3 with Cook)"}}], "extra": [],
               "out": {"item": "x", "qty": 1, "note": {"en": "1 (2 with Cook)", "pt": "1 (2 com Cozinheiro)"}}},
              {"in": [], "extra": [{"item": "s", "qty": 1, "note": {"en": "50% chance with Mason", "pt": "50% de chance com Pedreiro"}}],
               "out": {"item": "y", "qty": 1}}]
        perks = build.apply_bonuses(rs)
        self.assertEqual(perks, {"cook": {"pt": "Cozinheiro", "en": "Cook", "uses": 2}})   # the real pt name wins
        self.assertEqual(rs[0]["in"][0]["bonus"], {"perk": "Cook", "perks": ["cook"], "qty": 3})
        self.assertNotIn("bonus", rs[1]["extra"][0])

    def test_apply_grades(self):
        it = lambda en, **kw: dict({"en": en, "pt": en, "kind": "item"}, **kw)
        items = {
            "wine": it("Wine"), "wine-silver": it("Wine (silver)", kind="quality-variant", base="wine"),
            "wine-gold": it("Wine (gold)", kind="quality-variant", base="wine"), "spices": it("Spices"),
            "story": it("Story"), "story-bronze": it("Story (bronze)", kind="quality-variant", base="story"),
            "story-silver": it("Story (silver)", kind="quality-variant", base="story"),
            "polished-bronze": it("Polished Bronze"), "alcohol": it("Alcohol"), "soup": it("Soup"),
        }
        rec = lambda rid, out, ins, name=None: dict({"id": rid, "out": {"item": out, "qty": 1}, "extra": [],
                                                     "in": [{"item": i, "qty": 1} for i in ins]}, **({"name": {"en": name, "pt": name}} if name else {}))
        rs = [rec("up", "wine-silver", ["wine", "spices"], "Drink enhancement I from Wine (bronze)"),
              rec("alc", "alcohol", ["wine"], "Alcohol from Any Wine"),
              rec("soup-gold", "soup", ["wine-gold"], "Soup from Wine (gold)"),
              rec("pb", "polished-bronze", ["spices"])]
        build.apply_grades(items, rs)
        self.assertEqual({k: v.get("grade") for k, v in items.items() if v.get("grade")},
                         {"wine": "bronze", "wine-silver": "silver", "wine-gold": "gold", "story-bronze": "bronze", "story-silver": "silver"})
        self.assertEqual([r.get("quality") for r in rs], ["silver", None, "gold", None])   # never from the id ("polished-bronze")
        self.assertEqual(rs[0]["in"][0], {"item": "wine", "qty": 1, "grade": "bronze"})
        self.assertEqual(rs[1]["in"][0], {"item": "wine", "qty": 1, "anyGrade": True})
        self.assertNotIn("grade", rs[2]["in"][0])     # the input is the gold variant itself: no line grade

    def test_drop_defaults(self):
        page = {"items": {"a": {"pt": "A", "en": "A", "icon": None, "kind": "item", "listed": True, "unobtainable": False,
                                "raw": False, "recipes": [], "defaultRecipe": None, "tr": "official"}},
                "stations": {"s": {"pt": "S", "en": "S", "icon": None, "tr": "missing"}},
                "recipes": [{"id": "r", "out": {"item": "a", "qty": 1}, "station": "s", "type": "hand_craft", "cd": False,
                             "listed": False, "alt": [], "extra": [{"item": "b", "qty": None}], "runes": None,
                             "in": [{"item": "b", "qty": 1}, {"item": "c", "qty": 2}]}]}
        build.drop_defaults(page)
        # raw, recipes, defaultRecipe and tr "official" stay: GK.data has no default for them (or another one)
        self.assertEqual(page["items"]["a"], {"pt": "A", "en": "A", "raw": False, "recipes": [], "defaultRecipe": None, "tr": "official"})
        self.assertEqual(page["stations"]["s"], {"pt": "S", "en": "S"})
        self.assertEqual(page["recipes"][0], {"id": "r", "out": {"item": "a", "qty": 1}, "station": "s", "listed": False,
                                              "extra": [{"item": "b"}], "in": [{"item": "b"}, {"item": "c", "qty": 2}]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
