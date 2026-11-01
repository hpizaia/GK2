#!/usr/bin/env python3
"""The approved noise cuts on src/ (less text on screen), with GK.ui.fmt.buildLabel / techLine in node.

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
from helpers import ROOT, texts, recipes_src  # noqa: E402


class ScreenNoiseCuts(unittest.TestCase):
    """The approved noise cuts (less text on screen) and the quiet "Recentes" after an add. Source-level checks on src/, plus GK.ui.fmt.buildLabel / techLine in node."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_steps_rows(self):
        """Cortes 1-4: "×2 ▾" opens "Tenho __ de 2"; short tech line; the "Por execução" line is the recipe picker;
        crafts only when they differ from the quantity."""
        s, f, css = self.read("js/ui/summary.js"), self.read("js/ui/fmt.js"), self.read("css/planner.css")
        self.assertIn('class="row-qty qty-btn"', s)
        self.assertIn('"steps.qtyLabel"', s)
        for gone in ("steps.hint", "raw.hint", "steps.recipe", "steps.have"):
            self.assertNotIn(gone, texts("pt"), gone)
        self.assertFalse([k for k in texts("pt") if k.startswith(("fold.raw.", "fold.steps."))])
        self.assertIn("function stepPicker(", s)
        self.assertIn('class="row-in step-pick"', s)
        self.assertIn("s.runs > 1 && s.runs !== s.need", s)
        self.assertIn("function techLine(r, state)", f)
        for gone in ('"steps.tech"', '"steps.mastery"', '"steps.ext"', "infoButton("):
            self.assertNotIn(gone, f, gone)
        self.assertIn("GK.tech.researchedSet", f)
        self.assertRegex(css, r"\.step-pick select \{[^}]*opacity: 0")
        self.assertRegex(css, r"\.qty-btn \{[^}]*min-height: var\(--tap\)")
        # 1.8.x: "ou: Lenheiro II · Metalurgia 1": the other stations and the tech line on one small line in the row's
        # actions (8 px above, like the tech line before), each alone when the other is empty; no separate .row-alt
        self.assertIn('if (note.length) actions.push(`<span class="tech">${esc(note.join(" · "))}</span>`);', s)
        self.assertIn('[t("steps.alt", {', s)
        self.assertIn('.concat(F.techLine(r, state)).map((x) => x.replace(/ (?=(?:\\d+|[IVX]+)(?:[ ,]|$))/g, "\\u00a0"));', s)
        self.assertNotIn("row-alt", s)
        self.assertNotIn(".row-alt", self.read("css/components.css"))
        self.assertEqual((texts("pt")["steps.alt"], texts("en")["steps.alt"]), ("ou: {names}", "or: {names}"))
        self.assertRegex(css, r"\.row-actions \{[^}]*flex-wrap: wrap;[^}]*margin-top: var\(--s2\)")
        self.assertIn(".tech { font-size: .8125rem; color: var(--ink-3); }", css)

    def test_planner_spacing(self):
        """Spacing: the section toggles keep 8 px above their card and
        sit on the 12 px line of the controls inside; the station toggle and "×2 ▾" end on that line too, with no
        negative margins pulling "×2 ▾" up against the station band; a row's icon and tick sit at the top, beside the
        name; 8 px between a raw row's quantity and its "Já tenho"; the 44 px targets stay."""
        css = self.read("css/planner.css")
        self.assertIn(".summary-grid .fold-head { margin-bottom: var(--s2); }", css)
        # 1.8.x (seta das seções, opção A): a section's toggle is no longer the 44 px box 13 px in (it fell in the
        # column of the station box under it): a thin chevron with no box at the card's right edge, its invisible
        # 44 px target reaching 10 px into the page margin; the station toggle keeps its box
        self.assertNotIn(".summary-grid .fold-head > .fold-btn", css)
        sec = re.search(r"\n\.sec-fold \{([^}]*)\}", css).group(1)
        for decl in ("width: var(--tap); height: var(--tap);", "margin: 0 -10px 0 0; padding: 0 13px 0 0;",
                     "border: 0; background: transparent; color: var(--ink-3);"):
            self.assertIn(decl, sec)
        chev = re.search(r"\n\.sec-chev \{([^}]*)\}", css).group(1)
        self.assertIn("width: 9px; height: 9px;", chev)
        self.assertIn("border-right: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor;", chev)
        self.assertIn('[aria-expanded="false"] > .sec-chev { transform: translateX(-2px) rotate(-45deg); }', css)
        self.assertRegex(css, r"\.station-h \{[^}]*padding: var\(--s2\) var\(--s3\);")
        self.assertNotRegex(css, r"\.station-h\[data-fold-head\] \{[^}]*padding-right")
        qty = re.search(r"\.row-qty\.qty-btn \{([^}]*)\}", css).group(1)
        self.assertIn("margin: 0 0 0 var(--s1);", qty)
        self.assertIn("min-height: var(--tap); min-width: var(--tap);", qty)
        self.assertIn(".station .row > .tick, .station .row > .slot { align-self: start; }", css)
        # 1.8.0 grade única: the raw rows, the steps (rows + station header) and "Tecnologias que faltam" share the
        # columns 12 px | 26 px (24 px checkbox) | 8 px | 40 px icon | text | controls on the 12 px line; the checkbox
        # label stays 44 px wide; raw rows: name and "como obter" 2 px apart, centred on the icon
        self.assertIn(".summary-grid .row, .tn-card .tn-row { grid-template-columns: 26px 40px minmax(0, 1fr) auto; padding-left: var(--s3); padding-right: var(--s3); }", css)
        self.assertIn(".summary-grid .row > .tick, .tn-card .tn-row > .tick { margin-left: calc(var(--s3) * -1); place-items: center end; padding-right: var(--s2); }", css)
        self.assertRegex(css, r"\.station-h \{[^}]*grid-template-columns: 26px 40px minmax\(0, 1fr\) auto auto;[^}]*column-gap: var\(--s2\)")
        self.assertIn(".station-h > .station-n { justify-self: start; margin-left: -2px; }", css)
        self.assertIn(".station-h > .slot { justify-self: center; }", css)
        self.assertIn(".row-raw > .tick, .row-raw > .slot { grid-row: 1 / span 2; align-self: center; }", css)
        self.assertIn(".row-raw > .row-qty { grid-column: 4; grid-row: 1 / span 2; align-self: center; line-height: 1; }", css)
        self.assertRegex(css, r"\.row-raw \{[^}]*row-gap: 2px")
        self.assertRegex(css, r"\.tick \{[^}]*width: var\(--tap\); height: var\(--tap\)")
        # the raw rows' quantity is the steps' "× N ▾"
        self.assertIn("qtyButton(r.item, nm, r.qty, open, true)", self.read("js/ui/summary.js"))
        # Metas (1.8.x, opção 2): "− N +" at the row's right end, on the same 12 px line inside the card as the "× N ▾"
        # of Matérias-primas and Etapas (x 361 at 390 px, 331 at 360 px), no margin pushing it off that line
        goal = re.search(r"\n\.goal \{([^}]*)\}", css).group(1)
        self.assertIn("padding: 6px var(--s3);", goal)
        self.assertNotRegex(css, r"\.goal[^{]*\.stepper[^{]*\{[^}]*margin")
        self.assertNotRegex(css, r"\n\.stepper \{[^}]*margin")
        self.assertRegex(css, r"\.fold-btn \{[^}]*width: var\(--tap\)")

    def test_section_fold_option_a(self):
        """Section toggles: Matérias-primas, Etapas, Tecnologias
        que faltam and the open Hoje fold with the thin chevron (.sec-fold > .sec-chev, aria-expanded, a label per
        state); the station cards and the one-line Hoje keep the boxed .fold-btn. "Tecnologias que faltam" folded
        shows only "Total de pontos: …" (GK.store ui.tnCollapsed, per device)."""
        summary, today, tn, store, fmt = (self.read("js/ui/summary.js"), self.read("js/ui/today.js"),
                                          self.read("js/ui/techneeds.js"), self.read("js/store.js"), self.read("js/ui/fmt.js"))
        # one toggle for the three panels (GK.ui.fmt.foldBtn; its markup is checked in node by test_calc.mjs)
        self.assertIn('class="${sec ? "sec-fold" : "btn fold-btn"}" ${attrs} aria-expanded="${open}"', fmt)
        self.assertIn('<span class="sec-chev" aria-hidden="true"></span>', fmt)
        self.assertIn('GK.ui.fmt.foldBtn(`id="fold-${domId(k)}" data-fold="${esc(k)}"`, open, label, bodyId, sec)', summary)
        self.assertIn("""GK.ui.fmt.foldBtn('id="today-tgl" data-today-tgl', open, label, "today-body", sec)""", today)
        self.assertIn('${foldBtn("raw", !U.rawCollapsed, t("raw.title"), "raw-body", true)}', summary)
        self.assertIn('${foldBtn("steps", !U.stepsCollapsed, t("steps.title"), "steps-body", true)}', summary)
        self.assertIn("${foldBtn(fk, open, stName, body)}", summary)   # station: boxed
        self.assertIn('${foldBtn(true, t("today.title"), true)}', today)
        self.assertIn('${foldBtn(false, t("today.title"))}', today)     # one-line Hoje card: boxed
        self.assertIn("""GK.ui.fmt.foldBtn('id="fold-tn" data-tn-fold', !shut, title, "tn-body", true)""", tn)
        self.assertIn('setUi({ tnCollapsed: !shutOf(GK.store.get()) })', tn)
        self.assertIn('<span class="tn-sum-l">${esc(t("tn.totalSum"))}</span>${GK.ui.tech.costHtml(need.cost)}', tn)
        self.assertIn('expanded + "|" + shut + "|"', tn)   # folding re-renders the memoised panel
        for lang, words in (("pt", ("Total de pontos:", "Recolher: {name}")), ("en", ("Total points:", "Collapse: {name}"))):
            self.assertEqual((texts(lang)["tn.totalSum"], texts(lang)["fold.collapseX"]), words)
        self.assertIn("tnCollapsed: false", store)
        # the tech tab's column headers: 44 px buttons with aria-expanded, chevron after the title, smaller than ›
        tech, tcss = self.read("js/ui/tech.js"), self.read("css/tech.css")
        btn = re.search(r"\n\.tc-btn \{([^}]*)\}", tcss).group(1)
        self.assertIn("min-height: var(--tap);", btn)
        chev = re.search(r"\n\.tc-chev \{([^}]*)\}", tcss).group(1)
        self.assertIn("width: 4px; height: 4px;", chev)
        self.assertIn("color: var(--ink-3);", chev)
        self.assertRegex(tcss, r"\.tech-chev \{[^}]*font-size: 1\.375rem")   # the rows' › stays the bigger one
        self.assertIn(":focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }", self.read("css/base.css"))
        self.assertNotRegex(tcss, r"\.tc-btn[^{]*\{[^}]*outline")   # the column button keeps that global ring
        # the search lists its hits by branch, with plain (never folded) headers
        search = tech.split("function searchList", 1)[1].split("function chips", 1)[0]
        self.assertNotIn("data-tcol", search)
        self.assertNotIn("hidden", search)

    def test_planner_general(self):
        """Cortes 6, 8, 20, 13 (goals side): the icon opens Receitas; no stats line; perks fold; one first-use line;
        the example-replaced toast moved to search.js."""
        g, c, f, comp = self.read("js/ui/goals.js"), self.read("js/ui/checklist.js"), self.read("js/ui/fmt.js"), self.read("css/components.css")
        self.assertIn("function slotButton(", f)
        self.assertIn('class="slot slot-btn${m[1] || ""}"', f)   # 1.8.0: keeps the quality star's has-q
        self.assertIn("GK.ui.fmt.slotButton(", g)
        for gone in ("exampleGone", "example-note", "GK.store.subscribe", "infoButton"):
            self.assertNotIn(gone, g, gone)
        self.assertNotIn("goals.intro", texts("pt"))
        self.assertEqual(texts("pt")["goals.example"], "Exemplo: busque o que quer fabricar e ele substitui esta lista.")
        self.assertNotIn('class="stats"', c)
        self.assertFalse([k for k in texts("pt") if k.startswith("stats.")])
        self.assertIn('id="perks-tgl"', c)
        self.assertIn('aria-expanded="${perksOpen}"', c)
        self.assertIn(".slot.slot-btn {", comp)
        self.assertIn(".info-ico {", self.read("css/screens.css"))   # the footer's stale-data "i" keeps its style
        self.assertEqual(texts("pt")["tn.hint"], "Pesquise nesta ordem; marque o que já tem.")

    def test_days_today_search(self):
        """Cortes 7, 10, 11, 13, 14 and the Recentes fix (days.js, today.js, search.js)."""
        d, t, q = self.read("js/ui/days.js"), self.read("js/ui/today.js"), self.read("js/ui/search.js")
        self.assertNotIn("days-credit", d)
        for gone in ("days.hint", "days.credit", "days.calibrated", "days.isToday"):
            self.assertNotIn(gone, texts("pt"), gone)
        self.assertEqual(texts("pt")["days.adjust"], "Ajustar o dia")
        self.assertIn("data-adjust aria-expanded=", d)
        self.assertIn('t("days.machineNote")', d)       # moved into "Como funciona"
        self.assertIn("function shortText(ev)", t)
        self.assertIn('class="h2 today-h"', t)
        self.assertNotIn("days.advToast", t)            # no toast from the Hoje panel; days.js keeps its own
        self.assertIn("days.advToastN", d)
        self.assertEqual((texts("pt")["toast.added"], texts("pt")["toast.replaced"]), ("+ {name}", "+ {name} · exemplo removido"))
        self.assertIn("m && m.exampleReplaced", q)
        self.assertIn("restoreExample(snap)", q)
        self.assertIn("if (quiet || document.activeElement !== input) return false;", q)
        self.assertIn("!inList.has(id)", q)

    def test_recipes_tech_changelog(self):
        """Cortes 7, 12, 16, 17, 18 (recipes.js, tech.js, changelog.js)."""
        r, k, c, css = recipes_src(), self.read("js/ui/tech.js"), self.read("js/ui/changelog.js"), self.read("css/screens.css")
        pt = texts("pt")
        for gone in ("rc.hint", "rc.usedInNone"):
            self.assertNotIn(gone, pt, gone)
        self.assertIn('t("rc.altAll"', r)
        self.assertIn("rc-hidden-end", r)
        self.assertIn("GK.ui.fmt.buildLabel(", r)
        self.assertIn("row.n > 1", r)
        self.assertEqual(pt["rc.placeholder"], "Buscar item")
        self.assertFalse([x for x in pt if x.startswith("tech.recipes.")])
        self.assertIn("missingAnc.length >= 2", k)
        self.assertEqual(pt["tech.hint"], "Marque o que já pesquisou; as anteriores contam junto.")
        self.assertIn("aria-expanded", c)
        self.assertIn("aria-controls", c)
        self.assertIn("changelog.notes.one", pt)
        self.assertRegex(css, r"\.cl-toggle \{[^}]*min-height: var\(--tap\)")

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_build_label_and_tech_line(self):
        """GK.ui.fmt.buildLabel: "Construir no Cemitério" / "na Igreja" / "nas Casernas" / "em: A, B" / "Build at …";
        techLine(r, state): no prefixes, researched techs dropped, mastery level 0 = type only."""
        stub = r"""
global.window = global;
global.navigator = { language: "pt-BR" };
global.document = { addEventListener() {}, createElement() { return { style: {}, appendChild() {}, setAttribute() {} }; },
  head: { appendChild() {} }, documentElement: {}, getElementById() { return null; } };
"""
        harness = stub + self.read("js/core.js") + self.read("js/util.js") + self.read("js/i18n.js") + \
            self.read("js/i18n/pt.js") + self.read("js/i18n/en.js") + \
            'GK.tech = { available: () => true, researchedSet: (r) => new Set(Object.keys(r).filter((k) => r[k])) };\n' + \
            self.read("js/ui/fmt.js") + r"""
const F = GK.ui.fmt, z = (pt, en) => ({ id: "zone:" + en, build: true, pt, en });
const out = {};
GK.i18n.set("pt");
out.pt = [z("Cemitério", "Graveyard"), z("Igreja", "Church"), z("Casernas", "Barracks"), z("Pátio, Cemitério", "Yard, Graveyard"),
  z("Qualquer lugar", "Anywhere"), { id: "build", i18n: "station.build", build: true }, { id: "sawhorse", pt: "Cavalete", en: "Sawhorse" }].map((s) => F.buildLabel(s));
GK.i18n.set("en");
out.en = [z("Cemitério", "Graveyard"), z("Casernas", "Barracks"), z("Pátio, Cemitério", "Yard, Graveyard")].map((s) => F.buildLabel(s));
GK.i18n.set("pt");
const r = { tech: { id: "pottery-i", type: "technology", pt: "Olaria I", en: "Pottery I" }, mastery: { type: { pt: "Engenharia", en: "Building" }, level: 2 }, ext: { pt: "Foles", en: "Bellows" } };
out.line = F.techLine(r, { researched: {} });
out.lineDone = F.techLine(r, { researched: { "pottery-i": true } });
out.lineNoState = F.techLine(r);
out.level0 = F.techLine({ mastery: { type: { pt: "Anatomia", en: "Anatomy" }, level: 0 } }, { researched: {} });
out.quest = F.techLine({ tech: { id: "q", type: "quest", pt: "A missão", en: "The quest" } }, { researched: { q: true } });
console.log(JSON.stringify(out));
"""
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "h.js"
            p.write_text(harness, encoding="utf-8")
            res = subprocess.run(["node", str(p)], capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout.strip().splitlines()[-1])
        self.assertEqual(out["pt"], ["Construir no Cemitério", "Construir na Igreja", "Construir nas Casernas", "Construir em: Pátio, Cemitério",
                                     "Construir em qualquer lugar", "Construção (no local)", "Cavalete"])
        self.assertEqual(out["en"], ["Build at Graveyard", "Build at Barracks", "Build at: Yard, Graveyard"])
        self.assertEqual(out["line"], ["Olaria I", "Engenharia 2", "Foles"])
        self.assertEqual(out["lineDone"], ["Engenharia 2", "Foles"])
        self.assertEqual(out["lineNoState"], ["Olaria I", "Engenharia 2", "Foles"])
        self.assertEqual(out["level0"], ["Anatomia"])
        self.assertEqual(out["quest"], ["Missão: A missão"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
