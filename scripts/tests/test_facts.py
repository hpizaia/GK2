#!/usr/bin/env python3
"""The item facts: scripts/build_facts.py (wiki item pages -> data/facts.json) and build.apply_facts.

Part of the build tests; run them all with:  python3 -I scripts/test_build.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))   # helpers.py, next to this file (python3 -I leaves it out)
from helpers import HERE, ROOT, load_mod, build, run, read_json, texts, recipes_src  # noqa: E402


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
        # item facts: 197 bought, 333 studied, 39 cost Faith, 81 asked by quests
        self.assertEqual((c["sell"], c["price"], c["study"], c["study_faith"]), (197, 197, 333, 39))
        self.assertGreaterEqual(c["sell_likes"], 70)
        self.assertEqual((c["asked_quest"], c["quests"], c["asked_town"], c["asked_order"]), (81, 60, 29, 22))

    def test_recipes_detail_uses_facts(self):
        """The item detail draws "Onde conseguir", the use tooltip and the stack; the planner files do not."""
        js = recipes_src()
        for needle in ("function whereHtml(", "function tipHtml(", "function stackSlot(", "WHERE_CAP = 4"):
            self.assertIn(needle, js)
        self.assertEqual(texts("pt")["rc.where"], "Onde conseguir")

    def test_recipes_detail_ficha_blocks(self):
        """Ficha do item: "Quem compra", "Estudar" (+ "Já estudei", synced) and "Pedido em" (folded) in the item detail
        only; each block returns "" without its data; the planner and the list rows do not read the new fields."""
        js = recipes_src()
        for needle in ("function sellHtml(", "function studyHtml(", "function askedHtml(",
                       "rc.askedWarn", 'id="rc-studied"', "setStudied(", 'class="card list rc-asked" id="rc-asked"${askedOpen ? " open" : ""}',
                       "GK.ui.tech.costHtml(cost, { big: true })"):
            self.assertIn(needle, js)
        pt, en = texts("pt"), texts("en")
        self.assertEqual((pt["rc.sell"], pt["rc.study"], pt["rc.studied"], pt["rc.asked"], en["rc.sell"]),
                         ("Quem compra", "Estudar", "Já estudei", "Pedido em", "Who buys it"))
        for fn in ("sellHtml", "studyHtml", "askedHtml"):
            body = js.split(f"function {fn}(", 1)[1].split("\n  function ", 1)[0]
            self.assertIn('return "";', body, fn)
        # order in the card: where, obtain, runes, then sell and study; "Pedido em" after "Usado em"
        detail = js.split("function detailHtml(", 1)[1]
        self.assertLess(detail.index("whereHtml(it"), detail.index("sellHtml(it"))
        self.assertLess(detail.index("sellHtml(it"), detail.index("studyHtml(it"))
        self.assertLess(detail.index("${usedHtml}"), detail.index("${askedHtml(it, state, askedOpen)}"))
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
        for f in ("summary.js", "goals.js", "fmt.js"):
            self.assertNotIn(".where", (ROOT / "src" / "js" / "ui" / f).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
