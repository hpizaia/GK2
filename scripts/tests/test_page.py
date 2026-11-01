#!/usr/bin/env python3
"""The page build (src mode: src/ + data -> the HTML page) on a temp project, its helpers, and the real
src/ (manifest, i18n files, registries, JS syntax).

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
    ROOT, FIX, BUILD, VALIDATE, build, run, fixture_args, read_json, texts, expand_payload, extract_block,
    CHANGELOG, TEMPLATE, make_project)


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


class BuiltDate(unittest.TestCase):
    def test_default_is_the_last_release(self):
        """No --built: the date of the newest dated changelog entry, so a rebuild on another day writes nothing;
        --release (and no changelog) use today; --built wins."""
        cl = [{"version": "1.1.0", "date": None}, {"version": "1.0.0", "date": "2026-01-02"}]
        sde = build.os.environ.pop("SOURCE_DATE_EPOCH", None)
        self.addCleanup(lambda: sde is None or build.os.environ.__setitem__("SOURCE_DATE_EPOCH", sde))
        today = build.built_date(None)
        self.assertRegex(today, r"^\d{4}-\d\d-\d\d$")
        self.assertEqual(build.built_date(None, cl), "2026-01-02")
        self.assertEqual(build.built_date(None, cl, release=True), today)
        self.assertEqual(build.built_date("2026-05-06", cl), "2026-05-06")


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
        block = extract_block(dev)
        self.assertNotIn("</script", block.lower())                       # the data can never end its <script>
        self.assertNotIn("<!--", block)
        data = json.loads(block)
        self.assertIn("crypt </script><script>", expand_payload(data)["items"]["ancient-coin"]["obtain"]["en"])
        self.assertTrue(data["meta"]["collapsed"])
        self.assertNotIn("id", next(iter(data["items"].values())))
        self.assertEqual(expand_payload(data), read_json(self.dir / "out" / "gk2.json"))   # gk2.json minus redundancy
        self.assertEqual(run(VALIDATE, self.dir / "out" / "gk2.json", "--quiet")[0], 0)
        self.assertEqual(data["meta"]["version"], "9.9.9")
        self.assertEqual(data["meta"]["changelog"], CHANGELOG)
        self.assertIn("log", data["items"])
        # artifact page: no skeleton, no remote icons, same code; preview wraps it
        art = (self.proj / "dist" / "index.html").read_text(encoding="utf-8")
        self.assertTrue(art.startswith("<title>Fixture</title>"), art[:80])
        for tag in ("<!doctype", "<html", "<head>", "<body", "charset="):
            self.assertNotIn(tag, art.lower())
        self.assertIn("/* ==== src/js/app.js ==== */", art)
        self.assertTrue(all(it.get("icon") is None for it in json.loads(extract_block(art))["items"].values()))
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
        sprite = {"image": "data:image/png;base64,iVBORw0KGgo=", "size": 32, "cols": 1, "rows": 1,
                  "icons": {"log": [0, 0], "not-an-item": [0, 0]}}
        (self.proj / "data" / "sprite.json").write_text(json.dumps(sprite), encoding="utf-8")
        rc, so, se = self.build()
        self.assertEqual(rc, 0, se)
        for page in ("prototype/index.html", "dist/index.html"):
            data = json.loads(extract_block((self.proj / page).read_text(encoding="utf-8")))
            self.assertEqual(data["meta"]["sprite"]["icons"], {"log": [0, 0]}, page)
        (self.proj / "data" / "sprite.json").write_text("{}", encoding="utf-8")   # a bad manifest is a usage error
        self.assertEqual(self.build()[0], 2)

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
        make_project(self.proj, template=TEMPLATE.replace('<script id="gk2-data" type="application/json"><!-- @data --></script>',
                                                          "<!-- @data -->"))
        rc, so, se = self.build()
        self.assertEqual(rc, 2)
        self.assertIn("expected exactly one", se)
        self.assertEqual(run(BUILD, "--src", self.src, "--no-src")[0], 2)

    def test_unlisted_source_warns(self):
        (self.src / "js" / "ui" / "forgotten.js").write_text("GK.x = 1;\n", encoding="utf-8")
        rc, so, se = self.build()
        self.assertEqual(rc, 0, se)
        self.assertIn("forgotten.js is not in src/manifest.json", se)
        self.assertNotIn("GK.x = 1", (self.proj / "prototype" / "index.html").read_text(encoding="utf-8"))


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

    def test_i18n_files(self):
        """Every text is in src/js/i18n/pt.js and en.js, loaded right after js/i18n.js (before any module that uses
        them); no other module adds texts. en.js follows pt.js: the same keys in the same order, under the same
        section titles, with the same {placeholders}. (The dictionary itself, loaded: test_calc.mjs.)"""
        js = self.man["js"]
        i = js.index("js/i18n.js")
        self.assertEqual(js[i + 1:i + 3], ["js/i18n/pt.js", "js/i18n/en.js"])
        i18n = self.text["js/i18n.js"]
        self.assertIn("function add(", i18n)
        self.assertNotIn('"goals.title"', i18n)
        for f, text in self.text.items():
            if f.endswith(".js") and not f.startswith("js/i18n"):
                self.assertNotIn("GK.i18n.add(", text, f)
        for lang in ("pt", "en"):
            src = self.text[f"js/i18n/{lang}.js"]
            self.assertEqual(src.count("GK.i18n.add({ %s: {" % lang), 1, lang)
            keys = re.findall(r'"([a-zA-Z]+\.[\w.-]+)": "', src)
            self.assertEqual(len(keys), len(set(keys)), f"{lang}.js: a key is defined twice")
            self.assertEqual(len(keys), len(texts(lang)), lang)
        pt, en = texts("pt"), texts("en")
        self.assertEqual(list(en), list(pt), "en.js: the keys of pt.js, in the same order")
        section = lambda lang: re.findall(r"^  // ---- (.*) ----$", self.text[f"js/i18n/{lang}.js"], re.M)
        self.assertEqual(section("en"), section("pt"))
        self.assertGreater(len(section("pt")), 10)
        holes = lambda s: sorted(re.findall(r"\{\w+\}", s))
        self.assertEqual([k for k in pt if holes(pt[k]) != holes(en[k])], [], "different {placeholders} in pt and en")
        for k in ("changelog.title", "footer.history", "footer.credits"):
            self.assertIn(k, pt)

    def test_registries(self):
        self.assertIn("GK.app = (function", self.text["js/core.js"])
        self.assertIn("registerPanel", self.text["js/core.js"])
        self.assertIn("function register(", self.text["js/router.js"])
        self.assertIn("GK.router.tabs().map", self.text["js/ui/header.js"])
        for f in ("js/ui/header.js", "js/ui/search.js", "js/ui/goals.js", "js/ui/summary.js", "js/ui/checklist.js",
                  "js/ui/changelog.js", "js/ui/credits.js", "js/ui/footer.js"):
            self.assertIn("GK.app.registerPanel(", self.text[f], f)
        self.assertNotIn("GK.ui.goals.mount", self.text["js/app.js"])     # the loop reads the registry
        self.assertRegex(self.text["js/ui/changelog.js"], r'GK\.router\.register\(\{ id: "changelog".*tab: false')
        self.assertIn('href="#changelog"', self.text["js/ui/footer.js"])
        self.assertIn('<section data-slot="planner-extra" id="planner-extra">', self.html)
        self.assertRegex(self.text["js/ui/recipes.js"], r'GK\.router\.register\(\{ id: "recipes", labelKey: "rc\.tab", screen: "recipes"')
        self.assertEqual(texts("pt")["tab.tech"], "Tecnologias")

    def test_credits_screen(self):
        """#credits: a route-only screen in the assembled page, reached from the footer's version line."""
        cr = self.text["js/ui/credits.js"]
        self.assertIn('GK.router.register({ id: "credits", labelKey: "credits.title", screen: "credits", tab: false, order: 910 });', self.html)
        self.assertIn('GK.app.registerPanel(GK.ui.credits, { id: "credits", panel: "credits"', self.html)
        self.assertIn('<a href="#credits" id="foot-credits">', self.html)
        self.assertLess(self.html.index('id="foot-changelog"'), self.html.index('id="foot-credits"'))
        self.assertEqual((texts("pt")["footer.credits"], texts("en")["footer.credits"]), ("Créditos", "Credits"))
        # every credits.* text exists in both languages
        keys = lambda lang: {k for k, v in texts(lang).items() if k.startswith("credits.") and v.strip()}
        self.assertTrue(keys("pt") and keys("pt") == keys("en"), keys("pt") ^ keys("en"))
        for url in ("https://wikily.gg/graveyard-keeper-2", "https://github.com/hpizaia/GK2"):
            self.assertIn(url, cr)
        self.assertIn('target="_blank" rel="noopener"', cr)
        self.assertTrue(texts("pt")["credits.game.p1"].startswith("Graveyard Keeper 2 © Lazy Bear Games / tinyBuild"))
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
