#!/usr/bin/env python3
"""The app shell on src/: header, tabs, footer, search "Recentes", type scale (rem, "Letra grande"),
the stale-data notice and the QR card.

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
from helpers import ROOT, build, read_json, texts  # noqa: E402


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
        # the build still finds the tag by id after the move (assemble() fills it with build.fill_data)
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
        self.assertIn("band.after(row)", hj)   # 1.8.x: the stale-data band is gone, the row goes right after the tabs

    def test_router_scroll_per_screen(self):
        """UX review #7: a screen change no longer keeps the old screen's scroll position."""
        r = self.read("js/router.js")
        apply = r.split("function apply()", 1)[1].split("function init()", 1)[0]
        self.assertIn("pos[shown] = window.scrollY", apply)
        self.assertIn("window.scrollTo(0, want)", apply)
        self.assertLess(apply.index("window.scrollTo(0, want)"), apply.index("subs.forEach"))   # modules can still place the page
        self.assertIn('GK.router.forget("days")', self.read("js/ui/days.js"))

    def test_footer_links_tap_area(self):
        css = self.read("css/screens.css")
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


class SearchRecents(unittest.TestCase):
    """"Recentes" in the search (protótipo ideia 8, variante lista): the empty box focused lists the last items added
    to goals. The store / merge rules (state.recents, synced, global) are tested in test_calc.mjs."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_strings_and_popup(self):
        js = self.read("js/ui/search.js")
        self.assertEqual((texts("pt")["search.recent"], texts("en")["search.recent"]), ("Recentes", "Recent"))
        self.assertIn("const RECENT_SHOWN = 3;", js)
        self.assertIn("function renderRecent()", js)
        self.assertIn('class="result result-recent" role="option"', js)   # same options: tap / Enter = add()
        self.assertIn('input.addEventListener("focus", () => renderResults());', js)
        # the popup closes when the box loses the focus (iOS keyboard ✓); pressing the popup or the × keeps it
        self.assertIn('pop.addEventListener("mousedown", (e) => e.preventDefault());', js)
        self.assertIn('clearBtn.addEventListener("mousedown", (e) => e.preventDefault());', js)
        self.assertIn("if (a !== input && !root.contains(a)) setOpen(false);", js)
        self.assertIn("else input.blur();", js)   # Enter on the empty box, nothing picked: the keyboard goes down
        self.assertIn(".result-recent .result-name", self.read("css/header.css"))


class TypeScale(unittest.TestCase):
    """Text follows the phone's text size and the "Letra grande" switch: type sizes in rem, html[data-big] raises the root, ui.bigText is a per-device flag."""

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
        theme, app, footer = self.read("js/theme.js"), self.read("js/app.js"), self.read("js/ui/footer.js")
        self.assertIn('root.setAttribute("data-big", "")', theme)
        self.assertIn("big };", theme)
        # applied at boot before the panels mount, and again on every store change
        self.assertLess(app.index("GK.theme.big(S.get().ui"), app.index("for (const p of GK.app.panels())"))
        self.assertIn("S.subscribe((st) => GK.theme.big(st.ui && st.ui.bigText));", app)
        self.assertIn('id="big-text" aria-pressed="${bigOn}"', footer)
        self.assertIn("setUi({ bigText:", footer)
        for lang, txt in (("pt", "Letra grande"), ("en", "Large text")):
            self.assertEqual(texts(lang)["footer.bigText"], txt)
            self.assertTrue(texts(lang)["footer.bigTitle"])
        # the phone tab band shares the row and wraps instead of hiding tabs in a sideways scroll
        header = self.read("css/header.css")
        self.assertIn(".tabs-mob-band .tabs { flex-wrap: wrap; overflow-x: visible; }", header)


class FooterNoticeQr(unittest.TestCase):
    """1.4.1: the short footer (links, Letra grande, sync chip only with an account, one version line), the stale-data
    notice (data/game-version.json embedded as meta.gameVersion, footer line only since 1.8.x), the QR card
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
        # three links, 44 px (screens.css), Letra grande kept, sync chip hidden unless account / error
        self.assertEqual(re.findall(r'id="(foot-\w+)"', render.split("const links", 1)[1].split(";\n", 1)[0]),
                         ["foot-changelog", "foot-credits", "foot-site"])
        self.assertIn('id="big-text"', render)
        self.assertIn("const CHIP = { syncing: 1, synced: 1, error: 1 };", f)
        self.assertIn("el.hidden = !CHIP[st];", f)
        self.assertIn("[hidden] { display: none !important; }", self.read("css/base.css"))   # hides the chip over its display: inline-flex
        # the credits line and the long note left the footer; Créditos keeps the wikily credit and gets the note
        for gone in ("NX Software", "wikily"):
            self.assertNotIn(gone, f)
        for gone in ("footer.data", "footer.note", "footer.dataVersion"):
            self.assertNotIn(gone, texts("pt"))
        pt, en = texts("pt"), texts("en")
        self.assertFalse([k for k, v in pt.items() if "NX Software" in v and not k.startswith("credits.")])
        self.assertIn("(© NX Software)", pt["credits.data.p1"])
        self.assertTrue(pt["credits.data.p3"].startswith("As quantidades são as de base;"))
        # the data's game versions, no build date (QA 2026-11 #8)
        self.assertEqual(pt["credits.data.p4"], "Receitas da wiki (jogo {wiki}) · textos do jogo {game}.")
        self.assertEqual(en["credits.data.p4"], "Wiki recipes (game {wiki}) · game texts {game}.")
        self.assertNotIn("m.built", cr)
        # one version line: one number when wiki and game agree
        self.assertEqual(pt["footer.line"], "v{version} · dados do jogo {game}")
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
        """latest newer than the wiki recipes: notice (the footer line); equal or older: nothing. 1.8.x: the band under
        the tabs (with its ✕ and the "gk2-companion.notice" key) is gone; the old key is only dropped, never read."""
        f, h = self.read("js/ui/footer.js"), self.read("js/ui/header.js")
        self.assertIn("cmpVersion(gv.latest, wiki) <= 0", f)
        for gone in ("NOTICE_KEY", "notice-band", "closedFor", "closeBand", "renderBand", '"footer.staleClose"', "data-notice-close"):
            self.assertNotIn(gone, f)
        self.assertNotIn("notice-band", h)
        self.assertNotIn(".notice-", self.read("css/planner.css"))
        self.assertIn('try { localStorage.removeItem("gk2-companion.notice"); } catch (e)', f)
        self.assertNotIn('getItem("gk2-companion.notice")', f)
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
        for lang, txt in (("pt", "O jogo já está na {latest}; as receitas daqui são da {wiki}."),
                          ("en", "The game is on {latest}; recipes here are from {wiki}.")):
            self.assertEqual(texts(lang)["footer.stale"], txt)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_credits_qr(self):
        cr, css = self.read("js/ui/credits.js"), self.read("css/screens.css")
        self.assertIn('const APP_URL = "https://claude.ai/artifact/8hp57ZZTFoH6GyDQUdHZAn";', cr)
        self.assertIn('const WIDE = "(min-width: 900px) and (pointer: fine)";', cr)
        self.assertIn("if (!wide() || !GK.ui.qr) return \"\";", cr)           # no SVG made on a phone
        self.assertEqual(texts("pt")["credits.qr.say"], "Aponte a câmera do celular para abrir o app lá.")
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
        self.assertIn("n.split(/ from | a partir de /i)[0].trim()", f)
        self.assertNotIn('" [" + list[k].id + "]"', f)


if __name__ == "__main__":
    unittest.main(verbosity=2)
