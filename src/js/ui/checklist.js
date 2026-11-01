/* GK.ui.checklist: progress bar and the perk toggles ("Vantagens"). On phones this card comes last in the planner
   (planner.css, CSS order).
   1.6.0 (corte 8): no "20 matérias-primas · 41 etapas · 26 estações" line (the section titles count them); the perks
   fold into one line "Vantagens: 0 de 10 ligadas ›" that opens the toggles (folded by default; this module's state).
   1.8.0 (C3): ticks follow the quantity (GK.calc rawChecked / stepChecked); a step's tick saves its quantity; a raw
   row's tick is "tenho tudo" (ui/summary.js).
   1.8.x: no "Copiar lista", "Limpar marcações" or "Editar nomes" here any more: the card is the bar and the perks.
   Renaming an item lives in its Receitas detail (tap the "não oficial" / "editado" tag; ui/recipes.js).
   Owns: [data-panel="checklist"] and the change handler of the steps' [data-done] checkboxes on the planner.
   Exposes: GK.ui.checklist.{mount, render}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "progress.title": "Progresso",
    "progress.count": "{done} de {total} marcados",
    "perks.title": "Vantagens",
    "perks.sumLabel": "Vantagens:",
    "perks.sum": "{on} de {total} ligadas",
    "perks.hint": "Vantagens que mudam quantidades neste plano. Ligue as que você já tem no jogo.",
    "perks.toggle": "Vantagem {name}: {state}",
    "perks.on": "ligada",
    "perks.off": "desligada",
  },
  en: {
    "progress.title": "Progress",
    "progress.count": "{done} of {total} checked",
    "perks.title": "Perks",
    "perks.sumLabel": "Perks:",
    "perks.sum": "{on} of {total} on",
    "perks.hint": "Perks that change amounts in this plan. Turn on the ones you already have in the game.",
    "perks.toggle": "Perk {name}: {state}",
    "perks.on": "on",
    "perks.off": "off",
  },
});

GK.ui.checklist = (function () {
  const { t, name, num } = GK.i18n, { esc } = GK.util;
  let root, perksOpen = false;   // "Vantagens: 0 de 10 ligadas ›" opened (this device, this session)
  const C = GK.calc;
  // ticked rows of the plan: raw rows ("tenho tudo") and steps, each still covering what the plan asks for now
  const rawTicked = (plan, state) => plan.raw.filter((r) => C.rawChecked(r, state.have, state.done));
  const stepTicked = (plan, state) => plan.steps.filter((s) => C.stepChecked(s, state.done));
  function mount(el, planRoot) {
    root = el;
    planRoot.addEventListener("change", (e) => {
      const cb = e.target.closest("[data-done]");
      if (cb) GK.store.actions.toggleDone(cb.dataset.done, cb.checked, +cb.dataset.qty);
    });
    root.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      if (b.id === "perks-tgl") { perksOpen = !perksOpen; render(GK.store.get(), {}, GK.app.plan()); const tg = document.getElementById("perks-tgl"); if (tg) tg.focus(); return; }
      if (b.dataset.perk) GK.store.actions.setPerk(b.dataset.perk, b.getAttribute("aria-pressed") !== "true");
    });
  }
  // "Vantagens: 0 de 2 ligadas ›", then (opened) "Vantagens: [Economizador de Calor] [Cremador]": only the perks
  // this plan's recipes mention
  function perkRow(plan) {
    const list = (plan.perks || []).filter((p) => GK.data.perks()[p.id]);
    if (!list.length) return "";
    const on = list.filter((p) => p.active).length;
    const tgl = `<button type="button" class="perks-sum" id="perks-tgl" aria-expanded="${perksOpen}" aria-controls="perks-body"><span class="perks-label">${esc(t("perks.sumLabel"))}</span> <b class="tabnum">${esc(t("perks.sum", { on: num(on), total: num(list.length) }))}</b><span class="perks-chev" aria-hidden="true">›</span></button>`;
    const chips = list.map((p) => {
      const nm = name(GK.data.perks()[p.id]);
      return `<button type="button" class="chip" id="perk-${GK.util.domId(p.id)}" data-perk="${esc(p.id)}" aria-pressed="${p.active}" title="${esc(t("perks.toggle", { name: nm, state: t(p.active ? "perks.on" : "perks.off") }))}">${esc(nm)}</button>`;
    }).join("");
    return `<div class="perks-fold">${tgl}<div class="perks" id="perks-body" role="group" aria-labelledby="perks-h" aria-describedby="perks-hint"${perksOpen ? "" : " hidden"}><span class="perks-label" id="perks-h">${esc(t("perks.title"))}</span>${chips}<span class="sr-only" id="perks-hint">${esc(t("perks.hint"))}</span></div></div>`;
  }
  function render(state, meta, plan) {
    if (meta && meta.from === "search-toggle") return;
    if (!state.goals.length) { root.innerHTML = ""; return; }
    const total = plan.raw.length + plan.steps.length, done = rawTicked(plan, state).length + stepTicked(plan, state).length;
    const pct = total ? Math.round((done / total) * 100) : 0;
    root.innerHTML = `<div class="card progress">
      <div class="progress-top">
        <span class="progress-label">${esc(t("progress.title"))}</span>
        <span class="progress-num">${esc(t("progress.count", { done, total }))} · ${num(pct)}%</span>
      </div>
      <div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${done}" aria-label="${esc(t("progress.title"))}"><div class="bar-fill" style="width:${pct}%"></div></div>
      ${perkRow(plan)}
    </div>`;
  }
  return { mount, render };
})();

GK.app.registerPanel(GK.ui.checklist, { id: "checklist", panel: "checklist", order: 40 });
