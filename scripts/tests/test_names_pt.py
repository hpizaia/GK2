#!/usr/bin/env python3
"""The pt names: derived names, the pt notes and zones, the recipe names of the hand layer and the
approved name swaps.

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
from helpers import ROOT, BUILD, build, run, read_json  # noqa: E402


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


class RecipeNamesPt(unittest.TestCase):
    """The pt recipe names (the entries with `recipes` of the
    hand layer data/names.manual.pt-BR.json, read by default); the owner's 3 decisions: grade as "(ouro)",
    "X a partir de Y" left out of the pt card, "Canteiro de Trigorigo" fixed by a `fix` entry. (The page behaviour:
    test_calc.mjs "nomes de receita".)"""
    LAYER = ROOT / "data" / "names.manual.pt-BR.json"

    def test_layer_file(self):
        d = read_json(self.LAYER)
        rows = {k: v for k, v in d.items() if not k.startswith("_")}
        recs = {k: v for k, v in rows.items() if v.get("recipes") and not v.get("fix")}
        self.assertEqual(len(recs), 231)
        kinds = {}
        for k, v in recs.items():
            kinds[(v["source"], v["confidence"])] = kinds.get((v["source"], v["confidence"]), 0) + 1
            self.assertNotIn("qualidade", v["pt"], k)                       # decision 1
            m = re.search(r"\((bronze|silver|gold)\)$", k)
            if m:
                self.assertTrue(v["pt"].endswith("(%s)" % {"bronze": "bronze", "silver": "prata", "gold": "ouro"}[m.group(1)]), k)
            # composed by us -> guess (the "não oficial" badge)
            ours = k.startswith(("Build ", "Grown in ")) or k.endswith("(alchemy formula)")
            self.assertEqual(v["confidence"] == "guess", ours, k)
            self.assertNotIn("Trigorigo", v["pt"])
        self.assertEqual(kinds, {("wikily-pt", "likely"): 159, ("derived", "guess"): 67, ("game-files", "official"): 5})
        self.assertEqual(recs["Spices (alchemy formula)"]["pt"], "Especiarias (fórmula de alquimia)")   # official word
        self.assertEqual(recs["Wine from Grape Juice (gold)"]["pt"], "Vinho a partir de Suco de Uva (ouro)")
        fix = rows["Wheat Bed"]                                              # decision 3
        self.assertEqual((fix["pt"], fix["source"], fix["confidence"]), ("Canteiro de Trigo", "fix", "likely"))
        self.assertTrue(fix["fix"].strip())
        self.assertIn("Canteiro de Trigorigo", read_json(ROOT / "data" / "game-texts" / "gk2_textos.json")["garden_wheat"]["pt"])

    def test_fix_beats_every_tier(self):
        log = build.Log()
        off = build.Layer("o.json", {"Wheat Bed": {"pt": "Canteiro de Trigorigo", "source": "game-files", "confidence": "official"},
                                     "Log": {"pt": "Tora", "source": "game-files", "confidence": "official"}}, log, False)
        fx = build.Layer("r.json", {"Wheat Bed": {"pt": "Canteiro de Trigo", "source": "fix", "confidence": "likely", "fix": "typo"},
                                    "Log": {"pt": "Lenho", "source": "x", "confidence": "likely"}}, log, False)
        for layers in ([off, fx], [fx, off]):
            t = build.Translator("pt", layers)
            self.assertEqual(t.name("Wheat Bed"), ("Canteiro de Trigo", "likely", "fix"))
            self.assertEqual(t.name("Log")[0], "Tora")                       # without `fix`, official still wins

    def test_default_layer_and_report(self):
        self.assertEqual([p.name for p in build.default_pt(build.DATA)],
                         ["names.official.pt-BR.json", "names.manual.pt-BR.json", "names.machine.pt-BR.json"])
        rep = (ROOT / "data" / "report-l10n.md").read_text(encoding="utf-8")
        row = next(l for l in rep.splitlines() if l.startswith("| Recipe names"))
        cells = [c.strip() for c in row.strip("|").split("|")]
        self.assertEqual(cells[2:5], ["0", "0", "67"])                       # missing 0, machine 0, guess 67 (ours)
        self.assertIn("names.manual.pt-BR.json", (ROOT / "data" / "report-build.md").read_text(encoding="utf-8"))
        ds = read_json(ROOT / "data" / "gk2.json")
        self.assertEqual((ds["items"]["wheat-bed"]["pt"], ds["items"]["wheat-bed"]["tr"]), ("Canteiro de Trigo", "likely"))
        R = {r["id"]: r for r in ds["recipes"]}
        self.assertEqual(R["grow-wheat-bed-m2"]["name"]["tr"], "guess")
        self.assertNotIn("tr", R["board-sawhorse"]["name"])
        self.assertNotIn("Trigorigo", json.dumps(ds, ensure_ascii=False))

    def test_page_code(self):
        fmt = (ROOT / "src" / "js" / "ui" / "fmt.js").read_text(encoding="utf-8")
        rc = (ROOT / "src" / "js" / "ui" / "recipes-cards.js").read_text(encoding="utf-8")
        self.assertIn("function recipeName(r, it)", rc)
        self.assertIn("const PT_HIDDEN_NAME = / a partir de |^Construir .+ \\(.+\\)$/i;", rc)
        self.assertIn("PT_HIDDEN_NAME.test(name(r.name))", rc)
        self.assertIn("const rname = recipeName(r, it);", rc)
        page = ROOT / "dist" / "preview.html"
        if page.exists():
            self.assertIn("function recipeName(r, it)", page.read_text(encoding="utf-8"))


class WikiNameSwaps(unittest.TestCase):
    """The 18 name swaps approved by the owner. 9 categories in the hand
    layer data/names.manual.pt-BR.json (field `game`), "Repair (X)" derived as "Consertar (X)", 7 source names of the
    MT glossary (build_facts.py). The 4 marked "conferir no jogo" stay as they were."""
    CATS = {"Building: Garden": "Construção: jardim", "Building: Garden tablets": "Construção: placas do jardim",
            "Building: Yard": "Construção: pátio", "Building: Barracks": "Construção: casernas",
            "Building: Graves and columbaria": "Construção: túmulos e columbários",
            "Building: Assembly benches": "Construção: bancos de montagem",
            "Building: Crafting station": "Construção: estação de produção",
            "Crafting materials": "Materiais de produção", "Town supplies": "Suprimentos do Povoado"}
    SOURCES = {"swamp-mushrooms": "Cogumelos pantaneiros", "driftwood": "Madeira trazida pela maré",
               "iron-ore-deposit": "Depósito de minério de ferro", "stone-deposit": "Depósito de pedra",
               "marble-deposit": "Depósito de mármore", "sand-pit": "Buraco de areia", "broken-shelf": "Prateleira quebrada"}

    def test_layer_and_default(self):
        d = read_json(ROOT / "data" / "names.manual.pt-BR.json")
        rows = {k: v for k, v in d.items() if not k.startswith("_") and v.get("game")}
        self.assertEqual({k: v["pt"] for k, v in rows.items()}, self.CATS)
        self.assertTrue(all((v["source"], v["confidence"]) == ("wikily-pt", "likely") for v in rows.values()))
        self.assertIn("names.manual.pt-BR.json", [p.name for p in build.default_pt(build.DATA)])

    def test_dataset(self):
        ds = read_json(ROOT / "data" / "gk2.json")
        cats = {it["cat"]["en"]: it["cat"]["pt"] for it in ds["items"].values() if it.get("cat")}
        for en, pt in self.CATS.items():
            self.assertEqual(cats.get(en), pt, en)
        self.assertEqual(cats.get("Building: Metalwork"), "Construção: metalurgia")   # conferir no jogo: unchanged
        it = ds["items"]
        self.assertEqual(it["repair-resurrection-device"]["pt"], "Consertar (Dispositivo de Ressurreição)")
        self.assertEqual(it["repair-underground-well"]["pt"], "Consertar (Poço Subterrâneo)")
        self.assertFalse([k for k, v in it.items() if v["pt"].startswith("Reparar")])
        self.assertEqual(it["any-story"]["pt"], "Qualquer história")                     # conferir no jogo: unchanged
        refs = ds["meta"]["refs"]["names"]
        for k, pt in self.SOURCES.items():
            self.assertEqual(refs[k]["pt"], pt, k)
        self.assertEqual(refs["dig"]["pt"], "Dig")                                       # conferir no jogo: unchanged
        facts = (ROOT / "scripts" / "build_facts.py").read_text(encoding="utf-8")
        for old in ("Jazida de pedra", "Areal", "Estante quebrada", "Cogumelos do pântano", "Madeira flutuante"):
            self.assertNotIn('"%s"' % old, facts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
