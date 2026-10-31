/* GK.ui.checklist: progress bar, perk toggles ("Vantagens"), copy as text, clear checks, export edited names.
   Owns: [data-panel="checklist"] and the change handler of every [data-done] checkbox on the planner.
   Exposes: GK.ui.checklist.{mount, render, asText, exportNames}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "progress.title": "Progresso",
    "progress.count": "{done} de {total} marcados",
    "progress.clear": "Limpar marcações",
    "progress.copy": "Copiar lista",
    "progress.copied": "Lista copiada",
    "progress.copyFail": "Não deu para copiar automaticamente. O texto está selecionado abaixo: copie com o menu do sistema.",
    "progress.cleared": "Marcações limpas",
    "stats.raw.one": "{n} matéria-prima",
    "stats.raw.other": "{n} matérias-primas",
    "stats.steps.one": "{n} etapa",
    "stats.steps.other": "{n} etapas",
    "stats.stations.one": "{n} estação",
    "stats.stations.other": "{n} estações",
    "export.button": "Exportar nomes editados ({n})",
    "export.copied": "Nomes editados copiados (JSON)",
    "export.fail": "Não deu para copiar automaticamente. O JSON está selecionado abaixo: copie com o menu do sistema.",
    "copy.header": "Graveyard Keeper 2 · lista de crafting",
    "copy.goals": "Metas",
    "copy.haveN": "tenho {n}",
    "perks.title": "Vantagens",
    "perks.hint": "Vantagens que mudam quantidades neste plano. Ligue as que você já tem no jogo.",
    "perks.toggle": "Vantagem {name}: {state}",
    "perks.on": "ligada",
    "perks.off": "desligada",
  },
  en: {
    "progress.title": "Progress",
    "progress.count": "{done} of {total} checked",
    "progress.clear": "Clear checks",
    "progress.copy": "Copy list",
    "progress.copied": "List copied",
    "progress.copyFail": "Couldn't copy automatically. The text is selected below: copy it with your system menu.",
    "progress.cleared": "Checks cleared",
    "stats.raw.one": "{n} raw material",
    "stats.raw.other": "{n} raw materials",
    "stats.steps.one": "{n} step",
    "stats.steps.other": "{n} steps",
    "stats.stations.one": "{n} station",
    "stats.stations.other": "{n} stations",
    "export.button": "Export edited names ({n})",
    "export.copied": "Edited names copied (JSON)",
    "export.fail": "Couldn't copy automatically. The JSON is selected below: copy it with your system menu.",
    "copy.header": "Graveyard Keeper 2 · crafting list",
    "copy.goals": "Goals",
    "copy.haveN": "have {n}",
    "perks.title": "Perks",
    "perks.hint": "Perks that change amounts in this plan. Turn on the ones you already have in the game.",
    "perks.toggle": "Perk {name}: {state}",
    "perks.on": "on",
    "perks.off": "off",
  },
});

GK.ui.checklist = (function () {
  const { t, name, num } = GK.i18n, { esc } = GK.util;
  let root;
  const keysOf = (plan) => plan.raw.map((r) => "raw:" + r.item).concat(plan.steps.map((s) => "step:" + s.item));
  function asText(state, plan) {
    const D = GK.data.get(), nm = (id) => name(D.items[id], state.overrides);
    const box = (k) => (state.done[k] ? "[x]" : "[ ]");
    const lines = [t("copy.header"), "", t("copy.goals") + ":"];
    state.goals.forEach((g) => lines.push(`- ${num(g.qty)}× ${nm(g.item)}`));
    lines.push("", t("raw.title") + ":");
    plan.raw.forEach((r) => lines.push(`${box("raw:" + r.item)} ${num(r.qty)} ${nm(r.item)}${r.have && !r.haveQty ? " (" + t("raw.have") + ")" : r.haveQty ? " (" + t("copy.haveN", { n: r.haveQty }) + ")" : ""}`));
    lines.push("", t("steps.title") + ":");
    plan.stations.forEach((g) => {
      lines.push(`# ${name(g.station, state.overrides)}`);
      g.steps.forEach((s) => lines.push(`${box("step:" + s.item)} ${nm(s.item)} ×${num(s.need)} (${t("steps.runs", { n: s.runs })})`));
    });
    return lines.join("\n");
  }
  // { "<English name>": { "pt": "…" } } — ready to merge into data/names.pt-BR.json
  function exportNames(state) {
    const D = GK.data.get(), out = {};
    for (const [lang, m] of Object.entries(state.overrides || {})) {
      for (const [id, v] of Object.entries(m || {})) {
        const it = D.items[id];
        if (!it || !v) continue;
        const e = (out[it.en] = out[it.en] || {});
        e[lang] = v;
        e.source = "user"; e.confidence = "guess";
      }
    }
    return JSON.stringify(out, null, 2);
  }
  const editedCount = (state) => Object.values(state.overrides || {}).reduce((n, m) => n + Object.keys(m || {}).length, 0);
  async function copyOrShow(text, okMsg, failKey) {
    if (await GK.util.copyText(text)) { GK.ui.toast(okMsg); return; }
    const box = root.querySelector("#copy-box");
    box.hidden = false;
    box.innerHTML = `<p class="hint">${esc(t(failKey))}</p><textarea class="copy-fallback" id="copy-text" readonly></textarea>`;
    const ta = box.querySelector("textarea"); ta.value = text; ta.focus(); ta.select();
  }
  function mount(el, planRoot) {
    root = el;
    planRoot.addEventListener("change", (e) => {
      const cb = e.target.closest("[data-done]");
      if (cb) GK.store.actions.toggleDone(cb.dataset.done, cb.checked);
    });
    root.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      if (b.id === "clear-done") { GK.store.actions.clearDone(); GK.ui.toast(t("progress.cleared")); }
      if (b.id === "copy-list") copyOrShow(asText(GK.store.get(), GK.app.plan()), t("progress.copied"), "progress.copyFail");
      if (b.id === "export-names") copyOrShow(exportNames(GK.store.get()), t("export.copied"), "export.fail");
      if (b.dataset.perk) GK.store.actions.setPerk(b.dataset.perk, b.getAttribute("aria-pressed") !== "true");
    });
  }
  // "Vantagens: [Economizador de Calor] [Cremador]": only the perks this plan's recipes mention
  function perkRow(plan) {
    const list = (plan.perks || []).filter((p) => GK.data.perks()[p.id]);
    if (!list.length) return "";
    const chips = list.map((p) => {
      const nm = name(GK.data.perks()[p.id]);
      return `<button type="button" class="chip" id="perk-${GK.util.domId(p.id)}" data-perk="${esc(p.id)}" aria-pressed="${p.active}" title="${esc(t("perks.toggle", { name: nm, state: t(p.active ? "perks.on" : "perks.off") }))}">${esc(nm)}</button>`;
    }).join("");
    return `<div class="perks" role="group" aria-labelledby="perks-h" aria-describedby="perks-hint"><span class="perks-label" id="perks-h">${esc(t("perks.title"))}</span>${chips}<span class="sr-only" id="perks-hint">${esc(t("perks.hint"))}</span></div>`;
  }
  function render(state, meta, plan) {
    if (meta && meta.from === "search-toggle") return;
    const nEdited = editedCount(state);
    if (!state.goals.length && !nEdited) { root.innerHTML = ""; return; }
    const keys = keysOf(plan), total = keys.length, done = keys.filter((k) => state.done[k]).length;
    const pct = total ? Math.round((done / total) * 100) : 0;
    const exportBtn = nEdited ? `<button type="button" class="btn btn-sm btn-ghost" id="export-names">${esc(t("export.button", { n: nEdited }))}</button>` : "";
    if (!state.goals.length) { root.innerHTML = `<div class="card progress"><div class="progress-actions">${exportBtn}</div><div id="copy-box" hidden></div></div>`; return; }
    root.innerHTML = `<div class="card progress">
      <div class="progress-top">
        <span class="progress-label">${esc(t("progress.title"))}</span>
        <span class="progress-num">${esc(t("progress.count", { done, total }))} · ${num(pct)}%</span>
      </div>
      <div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${done}" aria-label="${esc(t("progress.title"))}"><div class="bar-fill" style="width:${pct}%"></div></div>
      <div class="stats">${esc(t("stats.raw", { n: plan.raw.length }))} · ${esc(t("stats.steps", { n: plan.steps.length }))} · ${esc(t("stats.stations", { n: plan.stations.length }))}</div>
      ${perkRow(plan)}
      <div class="progress-actions">
        <button type="button" class="btn btn-sm" id="copy-list">${esc(t("progress.copy"))}</button>
        <button type="button" class="btn btn-sm btn-ghost" id="clear-done"${done ? "" : " disabled"}>${esc(t("progress.clear"))}</button>
        ${exportBtn}
      </div>
      <div id="copy-box" hidden></div>
    </div>`;
  }
  return { mount, render, asText, exportNames };
})();

GK.app.registerPanel(GK.ui.checklist, { id: "checklist", panel: "checklist", order: 40 });
