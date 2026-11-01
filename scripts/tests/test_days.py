#!/usr/bin/env python3
"""The days calendar in the page: build.py's days payload on an inline file (FIX_DAYS) and the real
data/days.json.

Part of the build tests; run them all with:  python3 -I scripts/test_build.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))   # helpers.py, next to this file (python3 -I leaves it out)
from helpers import (  # noqa: E402
    ROOT, FIX, BUILD, build, run, fixture_args, read_json, texts, extract_block, make_project)


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

    def test_real_days_modules_registered(self):
        src = ROOT / "src" / "js"
        days, today = (src / "ui" / "days.js").read_text(encoding="utf-8"), (src / "ui" / "today.js").read_text(encoding="utf-8")
        self.assertRegex(days, r'GK\.router\.register\(\{ id: "days", labelKey: "tab\.days", screen: "days"')
        self.assertIn('GK.app.registerPanel(GK.ui.days, { id: "days", panel: "days"', days)
        self.assertIn('slot: "planner-top", order: 5', today)
        for lang in ("pt", "en"):
            for pre in ("days.", "today."):
                self.assertTrue(any(k.startswith(pre) for k in texts(lang)), (lang, pre))
        if (ROOT / "data" / "days.json").exists():
            doc = build.load_days(ROOT / "data" / "days.json")
            self.assertEqual(len(doc["days"]), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
