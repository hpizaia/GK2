#!/usr/bin/env python3
"""The Planejador and the Hoje panel on src/: layout, flows, "feito hoje" ticks and notes.

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
from helpers import ROOT, read_json, texts  # noqa: E402


class PlannerUx(unittest.TestCase):
    """The Planejador's layout and flows: order on phones, compact
    goal and raw rows, first use, "Tudo" with undo, numbered station cards, short recipe labels."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_planner_order_mobile(self):
        """#1: below 900 px the progress card (bar and perks) goes after raw materials, steps and techs."""
        css = self.read("css/planner.css")
        phone = css.split("@media (max-width: 899px) {", 1)[1].split("\n}", 1)[0]
        self.assertIn('.col-plan > [data-panel="checklist"] { order: 10; }', phone)
        main = self.read("index.html").split("<main>", 1)[1].split("</main>", 1)[0]
        order = [main.index(x) for x in ('data-slot="planner-top"', 'data-panel="goals"', 'data-panel="checklist"',
                                         'data-panel="summary"', 'data-slot="planner-extra"')]
        self.assertEqual(order, sorted(order))   # desktop keeps the DOM order; only CSS reorders the phone column
        self.assertIn("todayCollapsed: true", self.read("js/store.js"))   # #4c: Hoje starts as one line

    def test_planner_goal_rows_one_line(self):
        """Goal rows: "− N +" on the name's line at every width (no more
        second line under 480 px); no separate ✕: at quantity 1 the "−" is a red ✕ that removes the goal, labelled
        "Remover <nome>" / "Remove <name>"; names wrap at whole words."""
        css, g = self.read("css/planner.css"), self.read("js/ui/goals.js")
        for gone in ("@container goals", "container: goals", ".goal-ctl"):
            self.assertNotIn(gone, css, gone)
        for gone in ("goal-ctl", 'id="rm-'):
            self.assertNotIn(gone, g, gone)
        self.assertRegex(css, r"\n\.goal \{[^}]*grid-template-columns: 40px minmax\(0, 1fr\) auto;")
        self.assertIn(".goal > .stepper { grid-column: 3; }", css)
        self.assertRegex(css, r"\.stepper button\.st-rm \{[^}]*color: var\(--blood\)")
        self.assertIn("g.qty <= 1", g)
        self.assertIn('class="st-rm" id="dec-${id}" data-remove="${esc(g.item)}" aria-label="${esc(t("goals.remove", { name: nm }))}">✕</button>', g)
        self.assertIn('id="dec-${id}" data-dec="${esc(g.item)}" aria-label="${esc(t("goals.dec", { name: nm }))}">−</button>', g)
        self.assertIn('id="inc-${id}" data-inc="${esc(g.item)}" aria-label="${esc(t("goals.inc", { name: nm }))}">+</button>', g)
        for k, pt, en in (("goals.dec", "Diminuir", "Decrease"), ("goals.inc", "Aumentar", "Increase"), ("goals.remove", "Remover {name}", "Remove {name}")):
            self.assertTrue(texts("pt")[k].startswith(pt), k)
            self.assertTrue(texts("en")[k].startswith(en), k)
        # a hold that runs "−" down to 1 does not remove the goal with the click that ends it
        self.assertIn("(b.dataset.dec || b.dataset.inc || b.dataset.remove) && swallowClick", g)
        # the ✕ removes with "Desfazer" (the app's undo toast); "Limpar metas" keeps its two-tap confirmation
        self.assertIn("else if (b.dataset.remove) removeWithUndo(b.dataset.remove);", g)
        self.assertNotIn("A.removeGoal(", g)
        self.assertIn('GK.ui.fmt.undoToast(t("goals.removed", { name: nm }), () => {', g)
        self.assertIn("S().actions.restoreGoal(goal, at,", g)
        self.assertEqual((texts("pt")["goals.removed"], texts("en")["goals.removed"]), ("Saiu das metas: {name}", "Removed from goals: {name}"))
        self.assertIn('t(confirming ? "goals.confirm" : "goals.clear")', g)
        name = re.search(r"\n\.goal-name \{(.*?)\}", css).group(1)
        self.assertIn("overflow-wrap: normal", name)
        self.assertIn("hyphens: auto", name)

    def test_planner_raw_rows_compact(self):
        """#5: "como obter" on one line (full text in the title), "Já tenho" on the row. 1.8.x: no ✎ pencils on the
        planner rows (renaming is in the Receitas detail; test_calc.mjs "renomear no detalhe")."""
        css, s, f = self.read("css/planner.css"), self.read("js/ui/summary.js"), self.read("js/ui/fmt.js")
        self.assertRegex(css, r"\.row-obtain \{[^}]*text-overflow: ellipsis")
        self.assertIn('class="row-line2"', s)
        self.assertIn('class="row-sub row-obtain"', s)
        for gone in ("const pencil", "data-edit", "edit-form", "canEdit"):
            self.assertNotIn(gone, f + s, gone)
        self.assertIn("function nameBlock(it, nm, extraBadges, overrides)", f)
        self.assertNotIn("editNames", self.read("js/store.js"))

    def test_progress_card_bar_and_perks_only(self):
        """1.8.x (pedido do dono): the Progresso card is the bar and the "Vantagens" line; no "Copiar lista",
        "Limpar marcações", "Editar nomes" or "Exportar nomes editados" there (the export moved to the rename field
        in the Receitas detail); their strings, store action and CSS are gone; "Limpar metas" stays."""
        c, st = self.read("js/ui/checklist.js"), self.read("js/store.js")
        css = self.read("css/planner.css") + self.read("css/components.css")
        for gone in ("copy-list", "clear-done", "edit-names", "export-names", "progress.copy", "progress.clear",
                     "names.edit", "export.button", "copy.header", "asText", "exportNames", "copyText"):
            self.assertNotIn(gone, c, gone)
        self.assertIn("return { mount, render };", c)
        self.assertIn('class="bar" role="progressbar"', c)
        self.assertIn("${perkRow(plan)}", c)
        self.assertNotIn("clearDone", st)
        for gone in (".progress-actions", ".names-toggle", ".edit-ico", ".copy-fallback"):
            self.assertNotIn(gone, css, gone)
        for gone in ("progress.copy", "progress.clear", "names.edit", "export.button", "copy.header"):
            self.assertFalse([k for k in texts("pt") if k.startswith(gone)], gone)
        self.assertEqual(texts("pt")["goals.clear"], "Limpar metas")

    def test_rename_in_recipes_detail(self):
        """1.8.x: the detail's "não oficial" / "editado" tag is the rename button ("Renomear <nome>", 44 px hit area);
        Salvar / Cancelar / "Voltar ao nome original" write GK.store overrides (behaviour: test_calc.mjs)."""
        css = self.read("css/recipes.css")
        for k, pt, en in (("rc.rename", "Renomear {name}", "Rename {name}"), ("rc.renameReset", "Voltar ao nome original", "Back to the original name"),
                          ("rc.exportNames", "Exportar nomes editados ({n})", "Export edited names ({n})")):
            self.assertEqual((texts("pt")[k], texts("en")[k]), (pt, en))
        self.assertRegex(css, r"\.badge-btn::after \{[^}]*inset: -14px -4px")
        self.assertIn(".copy-fallback {", css)

    def test_planner_have_all_undo(self):
        """#6: "Tudo" shows "<item>: você já tem tudo · Desfazer" and moves the focus to the next row."""
        s, f = self.read("js/ui/summary.js"), self.read("js/ui/fmt.js")
        body = s.split("function haveAll(btn) {", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn("GK.ui.fmt.undoToast(", body)
        self.assertIn("target.focus()", body)
        self.assertEqual(texts("pt")["have.allToast"], "{name}: você já tem tudo")
        self.assertIn("function undoToast(msg, onUndo)", f)
        self.assertEqual(texts("pt")["undo.button"], "Desfazer")
        self.assertIn(".toast-undo { display: flex;", self.read("css/screens.css"))
        self.assertIn("[hidden] { display: none !important; }", self.read("css/base.css"))   # wins over that display: flex

    def test_planner_stations_numbered_and_labels(self):
        """#8 + #10: cards numbered in display order (no "etapa N" depth badge); recipe labels without the letter
        or the repeated "receita: …" line."""
        s, f = self.read("js/ui/summary.js"), self.read("js/ui/fmt.js")
        self.assertIn('class="station-n tabnum"', s)
        for gone in ("steps.stage", "steps.recipeName"):
            self.assertNotIn(gone, texts("pt"), gone)
        self.assertNotIn("String.fromCharCode(65", f)
        self.assertIn("today-pick-name", self.read("js/ui/today.js"))   # quick win: names under the day medallions

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_planner_example_replaced_by_first_goal(self):
        """#4b: the first goal added replaces the example list; restoreExample brings it back (goals + checks)."""
        harness = "global.window = global;\n" + self.read("js/core.js") + \
            '\nGK.i18n = { LANGS: [{ code: "pt" }, { code: "en" }] };\n' + self.read("js/store.js") + r"""
const S = GK.store, metas = [];
S.subscribe((s, m) => metas.push(m));
S.actions.seedExample([{ item: "crate", qty: 3 }, { item: "furnace-i", qty: 1 }]);
S.actions.toggleDone("raw:log", true);
S.actions.addGoal("wine", 1);
const snap = metas[metas.length - 1].exampleReplaced;
const after = { goals: S.get().goals, example: S.get().example, done: S.get().done };
S.actions.restoreExample(snap);
const back = { goals: S.get().goals, example: S.get().example, done: S.get().done };
S.actions.addGoal("wine", 1); S.actions.addGoal("wine", 1);
const twice = { goals: S.get().goals, replaced: !!metas[metas.length - 1].exampleReplaced };
console.log(JSON.stringify({ after, back, twice, ui: S.get().ui }));
"""
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "h.js"
            p.write_text(harness, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["after"], {"goals": [{"item": "wine", "qty": 1}], "example": False, "done": {}})
        self.assertEqual(out["back"], {"goals": [{"item": "crate", "qty": 3}, {"item": "furnace-i", "qty": 1}],
                                       "example": True, "done": {"raw:log": True}})
        self.assertEqual(out["twice"], {"goals": [{"item": "wine", "qty": 2}], "replaced": False})
        self.assertTrue(out["ui"]["todayCollapsed"])


class TodayFeatures(unittest.TestCase):
    """The Hoje panel and the Dias card: "feito hoje" ticks (GK.store dayDone) and
    "Bilhete do dia" (GK.store dayNotes). No "Amanhã" in the Hoje panel (TodayCompact). The store / sync
    rules are tested in test_calc.mjs."""

    KEYS = {
        "js/ui/today.js": ("today.doneN", "today.check", "today.allDone", "today.note", "today.unsure"),
        "js/ui/days.js": ("days.note.label", "days.note.add", "days.note.edit", "days.note.editX", "days.note.ta",
                          "days.note.ph", "days.note.count", "days.note.saved", "days.note.cleared"),
    }

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def lang_keys(self, f):
        """{lang: {key: text}}: the texts of src/js/i18n (f, the module that uses them, only names the group)."""
        return {"pt": texts("pt"), "en": texts("en")}

    def test_i18n_keys_in_both_languages(self):
        for f, keys in self.KEYS.items():
            k = self.lang_keys(f)
            for key in keys:
                self.assertTrue(k["pt"].get(key), f"{f}: {key} missing in pt")
                self.assertTrue(k["en"].get(key), f"{f}: {key} missing in en")
                # same placeholders in both languages
                self.assertEqual(sorted(re.findall(r"\{\w+\}", k["pt"][key])), sorted(re.findall(r"\{\w+\}", k["en"][key])), key)
        self.assertEqual(set(k["pt"]), set(k["en"]), "pt and en define different keys")
        self.assertEqual(self.lang_keys("js/ui/days.js")["pt"]["days.note.add"], "Deixar um bilhete para este dia")

    def test_state_and_sync(self):
        store, sync = self.read("js/store.js"), self.read("js/sync.js")
        self.assertIn("const SCHEMA = 5;", store)   # 1.3.4 fields were additive; schema 5 = lists (migrated, test_calc.mjs)
        self.assertIn("dayDone: cleanDone(o.dayDone, day, dayNumber), dayNotes: cleanNotes(o.dayNotes)", store)
        for fn in ("toggleDayDone(", "setDayNote(", "function keepLate(", "function adoptLate("):
            self.assertIn(fn, store)
        self.assertIn("S().keepLate(", sync)
        self.assertIn("S().adoptLate(", sync)
        self.assertIn("mergeSynced(S().syncPayload(st), fields, d.updatedAt > st.updatedAt, base)", sync)
        # lists (schema 5): synced by id, the open list stays per device, the flat mirror is never an unknown field
        synced = re.search(r"const SYNCED = \[(.*?)\];", store).group(1)
        self.assertIn('"lists", "listsGone"', synced)
        self.assertNotIn("activeList", synced)
        self.assertIn("S().MIRROR.indexOf(k) < 0", sync)
        self.assertIn("sanitizeRemote(d.state, false, d.updatedAt)", sync)
        self.assertIn("css/lists.css", self.read("manifest.json"))

    def test_panel_markup(self):
        today, days = self.read("js/ui/today.js"), self.read("js/ui/days.js")
        self.assertIn('<label class="tick today-tick"><input type="checkbox"', today)   # 44 px target (.tick)
        self.assertIn('DY().noteBox("today"', today)
        self.assertIn('noteBox("days"', days)
        self.assertIn('maxlength="${MAX}"', days)

    def test_css_in_rem(self):
        css = self.read("css/days.css")
        for sel in (".today-ev-t", ".day-note-ta", ".day-note-add", ".today-all", ".today-tick", ".today-note-btn"):
            self.assertIn(sel, css)
        rules = [ln for ln in css.splitlines() if ".days-hub-" not in ln]   # SVG text: px are user units there
        self.assertEqual([ln for ln in rules if re.search(r"font(-size)?:[^;]*\b\d+px", ln)], [], "font sizes in rem")


class TodayCompact(unittest.TestCase):
    """The compact Hoje panel: one line per event that opens in
    place, ticks only on tasks, no "Amanhã", the note as a ✎ button by the count, a short "?" for "não confirmado"."""

    @classmethod
    def setUpClass(cls):
        cls.src = ROOT / "src"
        cls.read = lambda self, f: (self.src / f).read_text(encoding="utf-8")

    def test_no_tomorrow(self):
        today, css = self.read("js/ui/today.js"), self.read("css/days.css")
        for gone in ("today-tmr", "today.tomorrow", "DY().next(", "function tomorrow("):
            self.assertNotIn(gone, today, gone)
        self.assertNotIn(".today-tmr", css)
        self.assertRegex(self.read("js/ui/days.js"), r"return \{[^}]*\bnext\b")   # the week helper stays exported (Dias screen)

    def test_one_line_rows(self):
        today, css = self.read("js/ui/today.js"), self.read("css/days.css")
        body = today.split("function shortText(ev) {", 1)[1].split("\n  }", 1)[0]
        self.assertIn('text.indexOf(": ")', body)   # "Nome (Lugar): detalhe" -> "Nome (Lugar)"
        self.assertIn("if (ev.short) return name(ev.short);", body)   # the hand-written title wins
        self.assertIn('data-today-ev="${i}" aria-expanded="${open}" aria-controls="today-more-${i}"', today)
        self.assertIn('<div class="today-more" id="today-more-${i}"${open ? "" : " hidden"}>', today)
        self.assertIn("DY().eventMore(ev, state, true)", today)   # same detail as the Dias card, game text open
        self.assertIn("eventMore(ev, state, false)", self.read("js/ui/days.js"))
        rule = re.search(r"\.today-ev-t \{([^}]*)\}", css).group(1)
        for decl in ("white-space: nowrap", "overflow: hidden", "text-overflow: ellipsis"):
            self.assertIn(decl, rule)
        self.assertRegex(css, r"\.today-ev-btn \{[^}]*min-height: var\(--tap\)")

    def test_ticks_only_on_tasks(self):
        today, days = self.read("js/ui/today.js"), self.read("js/ui/days.js")
        self.assertIn('${ev.task ? `<label class="tick today-tick">', today)
        self.assertIn("d.events[i].task !== false", today)   # "2/3 feitas" counts the tasks
        self.assertIn("task: e.task !== false", days)        # absent = a task (older files)

    def test_note_button_and_unsure_mark(self):
        today = self.read("js/ui/today.js")
        k = TodayFeatures.lang_keys(self, "js/ui/today.js")
        self.assertEqual(k["pt"]["today.note"], "Bilhete deste dia")
        self.assertIn('id="today-note-edit" data-note-edit="${esc(d.id)}" aria-label="${esc(t("today.note"))}"', today)
        self.assertIn("${noteBtn(d, state)}", today.split('class="h2 today-h"', 1)[1].split("\n", 1)[0])
        self.assertIn('class="today-unsure"', today)
        self.assertIn('t("today.unsure")', today)   # the opened row says it in words

    @unittest.skipUnless((ROOT / "data" / "days.json").exists(), "real days.json not present")
    def test_real_days_task_marks(self):
        doc = read_json(ROOT / "data" / "days.json")
        evs = [e for d in doc["days"] for e in d["events"]]
        self.assertTrue(all(isinstance(e.get("task"), bool) for e in evs))
        info = sorted(e["pt"][:24] for e in evs if not e["task"])
        self.assertEqual(len(info), 9, info)
        for pt in ("O sino toca", "No fim do dia, o Laborat", "O limite semanal", "Fim do dia: o programa"):
            self.assertTrue(any(x.startswith(pt) for x in info), pt)
        self.assertIn('"task": bool(e["task"])', (ROOT / "scripts" / "build_days.py").read_text(encoding="utf-8"))
        # a hand-written line title (≤ 40 letters) where the automatic one is vague or the sentence has no ": "
        for e in evs:
            title = e["pt"].split(": ", 1)[0] if ": " in e["pt"] else None
            if title is None or title in ("Fim do dia", "Exceção", "Exceções", "Início da história"):
                self.assertTrue(e.get("short"), e["pt"][:40])
            if e.get("short"):
                self.assertLessEqual(max(len(e["short"]["pt"]), len(e["short"]["en"])), 40, e["short"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
