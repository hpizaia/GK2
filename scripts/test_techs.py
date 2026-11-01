#!/usr/bin/env python3
"""Tests for scripts/build_techs.py, run on the real inputs (data/raw/api-technologies-all.json, data/gk2.json).

    python3 -I scripts/test_techs.py          # or: python3 -I -m unittest scripts/test_techs.py
"""

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_techs as B  # noqa: E402

ROOT = HERE.parent
DATA = ROOT / "data"


class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = DATA / "raw" / "api-technologies-all.json"
        if not raw.exists():
            # data/raw/ is not in git (fresh clone, contributor): skip everything, loudly, instead of crashing
            raise unittest.SkipTest(f"missing {raw.relative_to(ROOT)} (data/raw/ is not in git; "
                                    "download it with scripts/fetch_dataset.py technologies data/raw)")
        args = B.argparse.Namespace(
            raw=str(raw), data=str(DATA / "gk2.json"),
            names=[str(DATA / "names.official.pt-BR.json"), str(DATA / "names.pt-BR.json"),
                   str(DATA / "names.machine.pt-BR.json")],
            game_text=str(ROOT / "data" / "game-texts" / "gk2_textos.json"))
        cls.raw, cls.ds, names = B.load_inputs(args)
        cls.doc = B.build(cls.raw, cls.ds, names, built="2000-01-01")
        cls.rep = B.validate(cls.doc, cls.ds, cls.raw)
        cls.techs = cls.doc["techs"]

    def test_no_validation_errors(self):
        self.assertEqual(self.rep["errors"], [])

    def test_every_raw_row_is_a_tech(self):
        self.assertEqual(set(self.techs), {r["key"] for r in self.raw["rows"]})
        self.assertEqual(self.doc["meta"]["count"], len(self.raw["rows"]))

    def test_parents_exist_and_children_mirror_parents(self):
        for s, t in self.techs.items():
            for p in t["parents"]:
                self.assertIn(p, self.techs, s)
                self.assertIn(s, self.techs[p]["children"])
            for c in t["children"]:
                self.assertIn(s, self.techs[c]["parents"])

    def test_dag(self):
        state = {}

        def visit(s, path=()):
            if state.get(s) == 1:
                self.fail(f"cycle: {' -> '.join(path + (s,))}")
            if state.get(s) == 2:
                return
            state[s] = 1
            for p in self.techs[s]["parents"]:
                visit(p, path + (s,))
            state[s] = 2

        for s in self.techs:
            visit(s)

    def test_costs_non_negative_ints(self):
        for s, t in self.techs.items():
            self.assertEqual(set(t["cost"]), {"red", "green", "blue"})
            for k, v in t["cost"].items():
                self.assertIsInstance(v, int, f"{s}.{k}")
                self.assertNotIsInstance(v, bool)
                self.assertGreaterEqual(v, 0, f"{s}.{k}")

    def test_recipe_techs(self):
        """Every recipe tech of type technology has a record; the others are quests/perks (reported)."""
        missing = self.rep["missing_recipe_techs"]
        self.assertTrue(all(m["type"] != "technology" for m in missing), missing)
        for r in self.ds["recipes"]:
            t = r.get("tech")
            if t and t.get("type") == "technology":
                self.assertIn(r["id"], self.techs[t["id"]]["recipes"])
        linked = [rid for t in self.techs.values() for rid in t["recipes"]]
        self.assertEqual(len(linked), len(set(linked)), "a recipe is linked to two techs")

    def test_branches(self):
        self.assertEqual(set(self.doc["meta"]["branches"]), set(self.doc["branches"]))
        for k, b in self.doc["branches"].items():
            self.assertTrue(b["pt"] and b["en"], k)
            self.assertIsInstance(b["order"], int)
        self.assertEqual(self.doc["branches"]["building"]["pt"], "Engenharia")   # official tech tab text

    def test_names(self):
        tiers = set(B.TIERS)
        for s, t in self.techs.items():
            self.assertIn(t["tr"], tiers, s)
            self.assertTrue(t["pt"], s)
        self.assertEqual(self.techs["market-stalls-i"]["pt"], "Barracas de Mercado I")
        self.assertNotEqual(self.techs["fabric-building"]["pt"], self.techs["fabric-farming"]["pt"])

    def test_shared_pt_names_are_numbered(self):
        # the game calls Bronze Works / Bronze Craft / Bronze Polishing all "Maestria em Bronze"
        self.assertEqual([self.techs[s]["pt"] for s in ("bronze-works", "bronze-craft", "bronze-polishing")],
                         ["Maestria em Bronze I", "Maestria em Bronze II", "Maestria em Bronze III"])
        self.assertTrue(all(self.techs[s]["tr"] == "likely" for s in ("bronze-works", "bronze-craft", "bronze-polishing")))
        self.assertIn("Maestria em Bronze", self.techs["bronze-works"]["notes"]["pt"])
        pts = [t["pt"] for t in self.techs.values()]
        dup = {p for p in pts if pts.count(p) > 1}
        self.assertEqual(dup, set(), "two technologies still share a pt name")

    def test_disambiguate_unit(self):
        techs = {s: {"pt": pt, "en": en, "tr": "official", "branch": "b", "column": c, "y": 0, "notes": None}
                 for s, pt, en, c in (("z", "Mesmo", "Zed", 1), ("a", "Mesmo", "Alpha", 3), ("u", "Outro", "Other", 2),
                                      ("s1", "Igual", "Same", 1), ("s2", "Igual", "Same", 2))}
        B.disambiguate(techs, ["b"])
        self.assertEqual((techs["z"]["pt"], techs["a"]["pt"]), ("Mesmo I", "Mesmo II"))     # column order
        self.assertEqual(techs["u"]["pt"], "Outro")
        self.assertEqual((techs["s1"]["pt"], techs["s2"]["pt"]), ("Igual", "Igual"))       # same English name: untouched

    def test_unlocks(self):
        items, stations = self.ds["items"], self.ds["stations"]
        for s, t in self.techs.items():
            for u in t["unlocks"]:
                self.assertIn(u["kind"], ("item", "building", "recipe", "other"), s)
                if u["item"] is not None:
                    self.assertTrue(u["item"] in items or u["item"] in stations, (s, u))
                if u["station"] is not None:
                    self.assertIn(u["station"], stations, (s, u))
                self.assertTrue(u["en"], s)
        c = self.rep["counts"]
        self.assertGreaterEqual(c["unlocks_mapped"] / c["unlocks"], 0.95)
        wine = next(u for u in self.techs["alchemy-advanced"]["unlocks"] if u["en"] == "Wine (gold)")
        self.assertEqual((wine["item"], wine["pt"]), ("wine-gold", "Vinho (ouro)"))   # 1.9: the grade is its own item

    def test_icons(self):
        items, stations = self.ds["items"], self.ds["stations"]
        for s, t in self.techs.items():
            ic = t["icon"]
            if ic.startswith("tech:"):
                self.assertEqual(ic, f"tech:{s}")
                self.assertTrue(self.doc["icons"][ic].startswith("https://media.wikily.gg/"))
            else:
                self.assertTrue(ic in items or ic in stations, s)
                raw = next(r["data"] for r in self.raw["rows"] if r["key"] == s)
                self.assertEqual((items.get(ic) or stations.get(ic))["icon"], raw["icon"], s)
        for col in ("red", "green", "blue"):
            self.assertIn(f"tp:{col}", self.doc["icons"])
            self.assertEqual(self.doc["meta"]["tp"][col]["icon"], f"tp:{col}")

    def test_notes(self):
        for s, t in self.techs.items():
            if t["notes"] is not None:
                self.assertTrue(t["notes"]["pt"] and t["notes"]["en"], s)
        self.assertIn("Jailson", self.techs["steel-smithing"]["notes"]["pt"])
        self.assertTrue(self.techs["battle-potions-i"]["hidden"])

    def test_written_file_matches_build(self):
        path = DATA / "techs.json"
        if not path.exists():
            self.skipTest("data/techs.json not built yet")
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        on_disk["meta"]["built"] = "2000-01-01"
        self.assertEqual(on_disk, self.doc, "data/techs.json is stale: re-run scripts/build_techs.py")


if __name__ == "__main__":
    unittest.main(verbosity=1)
