/* GK.ui.summary: raw totals and steps grouped by station (+ inline name editing, recipe choice, "Já tenho" /
   "tenho N de M", the member choice of group items).
   Raw rows are two lines (1.3.4): name + "i" | quantity, then "como obter" cut to one line (full text in the row's
   title and in the "i" detail) beside "Já tenho". The ✎ rename pencils show only in the "Editar nomes" mode
   (GK.store ui.editNames, toggled in the progress card). "Tudo" shows an undo toast ("Areia: você já tem tudo ·
   Desfazer") and moves the focus to the next row. Station cards are numbered 1, 2, 3… in display order.
   Collapsible (GK.store ui, per device): "Matérias-primas" (rawCollapsed), "Etapas por estação" (stepsCollapsed)
   and each station card (ui.stationCollapsed[stationKey], key = station id, "#<repeat>" for a card that comes back);
   a folded part keeps its header (with counts) and skips rendering its rows.
   1.6.0 (cortes 1-4, 6, 7, 8): a step's "×2 ▾" quantity is the button that opens "Tenho __ de 2" (no "Já tenho" line;
   goal steps keep a plain number); the tech line is short and drops researched techs (GK.ui.fmt.techLine(r, state));
   with other recipes, the "Por execução: 1 Tora → 3 ▾" line itself is the recipe <select>; the number of crafts
   shows only when it is more than 1 and differs from the quantity; the item icon opens Receitas (no "i"); no fixed hints above the
   two sections; a folded section says only "0/20 marcados" ("26 estações · 0/41 marcados" for the steps).
   1.8.0 (corte 9 + C3): a raw row's checkbox is "tenho tudo" (GK.store checkRaw: have = the quantity it asks for), the
   row goes to "Você já tem" with an undo toast; its quantity "20 ▾" opens "Tenho __ de 20" for a partial number (no
   "Já tenho" button, no "Tudo" there). Grade única: name and "como obter" as one block centred on the icon; the
   quantity is the steps' "× 20 ▾"; choosers and the field go on a line of their own (.row-more). Ticks follow the quantity (GK.calc rawChecked / stepChecked): a row ticked at 3
   is pending again when the plan asks for 10. A step's tick keeps its quantity (toggleDone(key, on, need)).
   Corte 19: no "Fabricar com" when every recipe left is circular (Pele).
   Owns: [data-panel="summary"]. Exposes: GK.ui.summary.{mount, render, stationKey}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "raw.title": "Matérias-primas",
    "raw.haveGroup": "Você já tem",
    "raw.cycle": "receita circular",
    "raw.refused": "receita sem ganho",
    "raw.noexp": "colheita: rendimento varia",
    "raw.members": "Serve qualquer um: {names}",
    "raw.asRaw": "Matéria-prima (não fabricar)",
    "raw.recipe": "Fabricar com",
    "raw.use": "Usar:",
    "raw.useLabel": "Qual item usar para {name}",
    "raw.useAny": "Qualquer um ({names})",
    "raw.group": "(grupo) {name}",
    "have.label": "Tenho",
    "have.of": "de {n}",
    "have.inputLabel": "Quantos {name} você já tem (de {n})",
    "have.all": "Tudo",
    "have.allLabel": "Já tenho todos os {n} de {name}",
    "have.ok": "OK",
    "have.cancel": "Fechar",
    "have.allToast": "{name}: você já tem tudo",
    "have.clear": "Limpar",
    "have.clearLabel": "Esquecer quantos {name} eu tenho",
    "steps.title": "Etapas por estação",
    "steps.order": "Estação {n} de {total}",
    "steps.runs.one": "{n}\u00a0execução",
    "steps.runs.other": "{n}\u00a0execuções",
    "steps.yield": "rende\u00a0{n} cada",
    "steps.yieldPerk": "rende\u00a0{n} com {perk}",
    "steps.withPerk": "com {perk}",
    "steps.yieldIf": "{n} com {perk}",
    "steps.groupLine": "grupo: {name}",
    "steps.again": "de novo",
    "steps.againTitle": "Esta estação aparece de novo: estas etapas dependem de outra estação acima.",
    "steps.left": "sobra\u00a0{n}",
    "steps.per": "Por execução:",
    "steps.recipeLabel": "Receita de {name}",
    "steps.qtyLabel": "{name}: {n}. Tocar para dizer quantos você já tem",
    "steps.techQuest": "Missão: {tech}",
    "steps.techPerk": "Vantagem: {tech}",
    "steps.alt": "ou: {names}",
    "steps.extra": "Também rende (não somado):",
    "steps.example": "mistura de exemplo",
    "steps.exampleTitle": "Alquimia: qualquer combinação de ingredientes com as mesmas runas funciona",
    "steps.goal": "meta",
    "steps.check": "Marcar {name} como feito",
    "fold.collapse": "Recolher",
    "fold.expand": "Expandir",
    "fold.collapseX": "Recolher: {name}",
    "fold.expandX": "Expandir: {name}",
    "fold.done": "{done}/{total} marcados",
    "fold.doneSr": "{done} de {total} marcados",
    "fold.stations.one": "{n} estação",
    "fold.stations.other": "{n} estações",
    "plan.empty": "Adicione uma meta para ver os ingredientes e as etapas.",
    "cycle.warn": "Receita circular em {names}. Esses itens foram tratados como matéria-prima.",
    "refused.warn": "A receita escolhida para {names} consome o próprio item sem ganho líquido; foi tratada como matéria-prima. Escolha outra receita na lista.",
  },
  en: {
    "raw.title": "Raw materials",
    "raw.haveGroup": "You already have",
    "raw.cycle": "circular recipe",
    "raw.refused": "no net gain",
    "raw.noexp": "harvest: yield varies",
    "raw.members": "Any of: {names}",
    "raw.asRaw": "Raw material (don't craft)",
    "raw.recipe": "Craft with",
    "raw.use": "Use:",
    "raw.useLabel": "Which item to use for {name}",
    "raw.useAny": "Any ({names})",
    "raw.group": "(group) {name}",
    "have.label": "I have",
    "have.of": "of {n}",
    "have.inputLabel": "How many {name} you already have (of {n})",
    "have.all": "All",
    "have.allLabel": "I have all {n} {name}",
    "have.ok": "OK",
    "have.cancel": "Close",
    "have.allToast": "{name}: you have it all",
    "have.clear": "Clear",
    "have.clearLabel": "Forget how many {name} I have",
    "steps.title": "Steps by station",
    "steps.order": "Station {n} of {total}",
    "steps.runs.one": "{n}\u00a0craft",
    "steps.runs.other": "{n}\u00a0crafts",
    "steps.yield": "makes\u00a0{n} each",
    "steps.yieldPerk": "makes\u00a0{n} with {perk}",
    "steps.withPerk": "with {perk}",
    "steps.yieldIf": "{n} with {perk}",
    "steps.groupLine": "group: {name}",
    "steps.again": "again",
    "steps.againTitle": "This station comes back: these steps need another station above.",
    "steps.left": "{n}\u00a0left over",
    "steps.per": "Per craft:",
    "steps.recipeLabel": "Recipe for {name}",
    "steps.qtyLabel": "{name}: {n}. Tap to say how many you already have",
    "steps.techQuest": "Quest: {tech}",
    "steps.techPerk": "Perk: {tech}",
    "steps.alt": "or: {names}",
    "steps.extra": "Also yields (not counted):",
    "steps.example": "example mix",
    "steps.exampleTitle": "Alchemy: any mix of ingredients with the same runes works",
    "steps.goal": "goal",
    "steps.check": "Mark {name} as done",
    "fold.collapse": "Collapse",
    "fold.expand": "Expand",
    "fold.collapseX": "Collapse: {name}",
    "fold.expandX": "Expand: {name}",
    "fold.done": "{done}/{total} checked",
    "fold.doneSr": "{done} of {total} checked",
    "fold.stations.one": "{n} station",
    "fold.stations.other": "{n} stations",
    "plan.empty": "Add a goal to see the ingredients and steps.",
    "cycle.warn": "Circular recipe in {names}. Those items were treated as raw materials.",
    "refused.warn": "The recipe chosen for {names} consumes the item itself with no net gain, so it was treated as a raw material. Pick another recipe from the list.",
  },
});

GK.ui.summary = (function () {
  const { t, name, num } = GK.i18n, { esc, slot, domId } = GK.util;
  const F = GK.ui.fmt;
  let root, editing = null; // item id whose name is being edited
  let haveOpen = null;      // item id whose "tenho N de M" field was just opened from "Já tenho"
  const focusId = (id) => { const el = document.getElementById(id); if (el) { el.focus(); if (el.select) el.select(); } };
  function applyHave(id, raw) {
    const A = GK.store.actions, v = String(raw == null ? "" : raw).trim();
    haveOpen = null;
    const n = Math.round(+v.replace(",", "."));
    if (!v || !(n > 0)) A.setHave(id, null); else A.setHave(id, n);
  }
  // folding: "raw" | "steps" | "st:<station key>"; the toggle and its header carry the same data-fold value
  const ui = (state) => state.ui || {};
  const canEdit = (state) => !!ui(state).editNames || !!editing;
  const stationKey = (g) => g.station.id + (g.repeat > 1 ? "#" + g.repeat : "");
  const FOLD_CONTROLS = "button, a, input, select, textarea, label";
  function toggleFold(k) {
    const A = GK.store.actions, u = ui(GK.store.get());
    if (k === "raw") A.setUi({ rawCollapsed: !u.rawCollapsed });
    else if (k === "steps") A.setUi({ stepsCollapsed: !u.stepsCollapsed });
    else if (k.indexOf("st:") === 0) A.toggleStation(k.slice(3));
  }
  // the 44 px toggle at a header's right (chevron drawn in CSS: .fold-btn); stable id so focus survives re-renders
  function foldBtn(k, open, label, bodyId) {
    return `<button type="button" class="btn fold-btn" id="fold-${domId(k)}" data-fold="${esc(k)}" aria-expanded="${open}" aria-controls="${bodyId}" title="${esc(t(open ? "fold.collapse" : "fold.expand"))}" aria-label="${esc(t(open ? "fold.collapseX" : "fold.expandX", { name: label }))}"></button>`;
  }
  function mount(el) {
    root = el;
    root.addEventListener("click", (e) => {
      const A = GK.store.actions;
      const fb = e.target.closest("[data-fold]");
      if (fb) { toggleFold(fb.dataset.fold); return; }
      const fh = e.target.closest("[data-fold-head]");
      if (fh && !e.target.closest(FOLD_CONTROLS)) { toggleFold(fh.dataset.foldHead); return; }
      const ro = e.target.closest("[data-recipe-open]");
      if (ro) { GK.ui.recipes.open(ro.dataset.recipeOpen, { from: "plan" }); return; }
      const ed = e.target.closest("[data-edit]");
      if (ed) { editing = ed.dataset.edit; rerender(); focusId("edit-" + domId(editing)); return; }
      if (e.target.closest("[data-edit-cancel]")) { editing = null; rerender(); return; }
      const rs = e.target.closest("[data-edit-reset]");
      if (rs) {
        const id = rs.dataset.editReset; editing = null;
        A.setOverride(GK.i18n.lang(), id, "");
        GK.ui.toast(t("edit.restored", { name: name(GK.data.item(id)) }));
        return;
      }
      const ho = e.target.closest("[data-have-open]");
      if (ho) {
        // a step's "×2 ▾" toggles the field it opened (a kept "tenho N" field only takes the focus)
        const id = ho.dataset.haveOpen;
        if (haveOpen === id && ho.classList.contains("qty-btn")) { haveOpen = null; rerender(); focusId("have-" + domId(id)); return; }
        haveOpen = id; rerender(); focusId("have-n-" + domId(id)); return;
      }
      const ha = e.target.closest("[data-have-all]");
      if (ha) { haveAll(ha); return; }
      const hc = e.target.closest("[data-have-cancel]");
      if (hc) { const id = hc.dataset.haveCancel; haveOpen = null; rerender(); focusId("have-" + domId(id)); return; }
      const hx = e.target.closest("[data-have-clear]");
      if (hx) { haveOpen = null; A.setHave(hx.dataset.haveClear, null); }
    });
    root.addEventListener("submit", (e) => {
      const hf = e.target.closest("[data-have-form]");
      if (hf) { e.preventDefault(); applyHave(hf.dataset.haveForm, hf.elements.n.value); return; }
      const f = e.target.closest("[data-edit-form]");
      if (!f) return;
      e.preventDefault();
      const id = f.dataset.editForm, it = GK.data.item(id), v = f.elements.v.value.trim();
      const original = it[GK.i18n.lang()] || it.en;
      editing = null;
      GK.store.actions.setOverride(GK.i18n.lang(), id, v && v !== original ? v : "");
      GK.ui.toast(t(v && v !== original ? "edit.saved" : "edit.restored", { name: v || original }));
    });
    root.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && e.target.closest("[data-edit-form]")) { editing = null; rerender(); }
      if (e.key === "Escape" && e.target.closest("[data-have-form]")) { const id = e.target.closest("[data-have-form]").dataset.haveForm; haveOpen = null; rerender(); focusId("have-" + domId(id)); }
    });
    root.addEventListener("change", (e) => {
      const rc = e.target.closest("[data-raw-check]");
      if (rc) { rawTick(rc); return; }
      const s = e.target.closest("[data-choice]");
      if (s) { GK.store.actions.chooseRecipe(s.dataset.choice, s.value); return; }
      const g = e.target.closest("[data-group]");
      if (g) { GK.store.actions.setGroupChoice(g.dataset.group, g.value || null); return; }
      // a field that stays on the row ("tenho [3] de 10"): apply on change; a freshly opened one waits for OK / Enter
      const n = e.target.closest("[data-have-n]");
      if (n && n.dataset.haveLive) applyHave(n.dataset.haveN, n.value);
    });
  }
  const rerender = () => render(GK.store.get(), {}, GK.app.plan());
  // "Tudo": the row leaves the list (or moves to "Você já tem"), so the focus goes to the row that followed it
  // (its checkbox; else the item's own "↺" button), and a toast offers "Desfazer" (the previous have value back)
  // the checkboxes of the rows after this one (ids: they survive the re-render)
  const nextTicks = (el) => {
    const rows = [...root.querySelectorAll(".row")], at = rows.indexOf(el.closest(".row"));
    return rows.slice(at + 1).map((r) => r.querySelector(".tick input")).filter(Boolean).map((cb) => cb.id);
  };
  function haveAll(btn) {
    const A = GK.store.actions, id = btn.dataset.haveAll, d = domId(id);
    const prev = GK.store.get().have[id];
    const next = nextTicks(btn);
    haveOpen = null;
    A.setHave(id, true);
    const target = next.map((x) => document.getElementById(x)).find((el) => el && el.id !== "cb-raw-" + d && el.id !== "cb-step-" + d) ||
      document.getElementById("cb-raw-" + d);
    if (target) target.focus();
    GK.ui.fmt.undoToast(t("have.allToast", { name: name(GK.data.item(id), GK.store.get().overrides) }), () => {
      A.setHave(id, prev === undefined ? null : prev);
      const back = document.getElementById("have-" + d) || document.getElementById("have-n-" + d);
      if (back) back.focus();
    });
  }
  // a raw row's checkbox = "tenho tudo" (corte 9): ticked, the row moves to "Você já tem", so the focus goes to the
  // row that followed it and a toast offers "Desfazer"; unticked, it comes back to the list (focus stays on it)
  function rawTick(cb) {
    const A = GK.store.actions, st = GK.store.get(), id = cb.dataset.rawCheck, d = domId(id);
    if (!cb.checked) { haveOpen = null; A.checkRaw(id, null, false); return; }
    const prev = { have: st.have[id], done: st.done["raw:" + id] };
    const next = nextTicks(cb);
    haveOpen = null;
    A.checkRaw(id, +cb.dataset.qty, true);
    const target = next.map((x) => document.getElementById(x)).find((el) => el && el.id !== "cb-raw-" + d && !el.checked);
    if (target) target.focus();
    GK.ui.fmt.undoToast(t("have.allToast", { name: name(GK.data.item(id), GK.store.get().overrides) }), () => {
      GK.store.update((s) => {
        if (prev.have === undefined) delete s.have[id]; else s.have[id] = prev.have;
        if (prev.done === undefined) delete s.done["raw:" + id]; else s.done["raw:" + id] = prev.done;
      });
      const back = document.getElementById("cb-raw-" + d);
      if (back) back.focus();
    });
  }
  // recipes that can actually expand (≥1 input, not noexp); zero-input "zombie production" and
  // grow recipes only describe where a raw material comes from
  const expandable = (r) => r.in.length > 0 && !r.noexp;
  // "Fabricar com [ … ▾]" (raw rows; the steps use stepPicker)
  function chooser(itemId, current, state, withRaw, labelKey) {
    const id = domId(itemId), D = GK.data.get(), nm = name(D.items[itemId], state.overrides);
    const all = GK.data.recipesFor(itemId);
    const shown = all.filter((r) => expandable(r) || (current && r.id === current.id));
    // corte 19: as a raw material, with only circular recipes to offer (Pele), the selector has nothing to give
    if (withRaw && !current && shown.every((r) => r.cyc)) return "";
    const labels = F.recipeLabels(shown, state, all);
    const opts = (withRaw ? `<option value=""${current ? "" : " selected"}>${esc(t("raw.asRaw"))}</option>` : "") +
      shown.map((r, k) => `<option value="${esc(r.id)}"${current && r.id === current.id ? " selected" : ""}>${esc(labels[k])}</option>`).join("");
    return `<span class="select-wrap"><label for="choice-${id}">${esc(t(labelKey))}</label><select id="choice-${id}" data-choice="${esc(itemId)}" aria-label="${esc(t("steps.recipeLabel", { name: nm }))}">${opts}</select></span>`;
  }
  // a step with other recipes (1.6.0, corte 3): the "Por execução: 1 Tora → 3 ▾" line is the recipe <select>
  // (transparent, over the whole line: a tap anywhere on it opens the native list). The options leave out the card's
  // own station ("1 Tora → 4 · Serra Circular" names only another one).
  function stepPicker(s, state, D, ins) {
    const r = s.recipe, nm = name(D.items[s.item], state.overrides);
    const all = GK.data.recipesFor(s.item);
    const shown = all.filter((x) => expandable(x) || x.id === r.id);
    const sid = r.station && (r.station.id || r.station.en);
    const labels = F.recipeLabels(shown, state, all, { omitStation: sid });
    const opts = shown.map((x, k) => `<option value="${esc(x.id)}"${x.id === r.id ? " selected" : ""}>${esc(labels[k])}</option>`).join("");
    return `<label class="row-in step-pick"><span class="step-pick-txt">${esc(t("steps.per"))} ${ins} → <b>${num(s.yield)}</b></span><span class="step-pick-chev" aria-hidden="true">▾</span>` +
      `<select id="choice-${domId(s.item)}" data-choice="${esc(s.item)}" aria-label="${esc(t("steps.recipeLabel", { name: nm }))}">${opts}</select></label>`;
  }
  // "Usar: [Carpa ▾]" for a group item (group = the group's id, current = chosen member or null)
  function groupChooser(groupId, current, state, D) {
    const g = D.items[groupId], nm = name(g, state.overrides), id = domId(groupId);
    const members = (g.members || []).filter((m) => D.items[m]);
    const any = t("raw.useAny", { names: members.map((m) => name(D.items[m], state.overrides)).join(", ") });
    const opts = `<option value=""${current ? "" : " selected"}>${esc(any)}</option>` +
      members.map((m) => `<option value="${esc(m)}"${m === current ? " selected" : ""}>${esc(name(D.items[m], state.overrides))}</option>`).join("");
    return `<span class="select-wrap"><label for="group-${id}">${esc(t("raw.use"))}</label><select id="group-${id}" data-group="${esc(groupId)}" aria-label="${esc(t("raw.useLabel", { name: nm }))}">${opts}</select></span>`;
  }
  // "Tenho [ 3 ] de 10": opened from the quantity (with Tudo / OK / Fechar) or kept on the row (live, with Limpar).
  // A raw row has no "Tudo" (its checkbox is "tenho tudo"): noAll
  function haveField(itemId, nm, total, value, live, noAll) {
    const id = domId(itemId), max = 999999;
    // empty field (no "0" placeholder that reads like a value); "Tudo" first (the common case), Fechar as a small ✕
    const input = `<input id="have-n-${id}" name="n" data-have-n="${esc(itemId)}"${live ? ' data-have-live="1"' : ""} type="number" inputmode="numeric" min="0" max="${max}" step="1" value="${value == null ? "" : esc(value)}" aria-label="${esc(t("have.inputLabel", { name: nm, n: total }))}">`;
    const all = live || noAll ? "" : `<button type="button" class="btn btn-sm" id="have-all-${id}" data-have-all="${esc(itemId)}" aria-label="${esc(t("have.allLabel", { name: nm, n: total }))}">${esc(t("have.all"))}</button>`;
    const btns = live
      ? `<button type="button" class="btn btn-sm btn-ghost" id="have-x-${id}" data-have-clear="${esc(itemId)}" aria-label="${esc(t("have.clearLabel", { name: nm }))}">${esc(t("have.clear"))}</button>`
      : `<button type="submit" class="btn btn-sm" id="have-ok-${id}">${esc(t("have.ok"))}</button>` +
        `<button type="button" class="btn btn-sm btn-ghost have-close" id="have-c-${id}" data-have-cancel="${esc(itemId)}" title="${esc(t("have.cancel"))}" aria-label="${esc(t("have.cancel"))}">✕</button>`;
    return `<form class="have-form" data-have-form="${esc(itemId)}">${all}<label for="have-n-${id}">${esc(t("have.label"))}</label>${input}<span class="have-of tabnum">${esc(t("have.of", { n: num(total) }))}</span>${btns}</form>`;
  }
  // the "tenho N de M" field of a row: kept (a number) or just opened from the quantity; else nothing
  function haveControls(itemId, nm, total, state, noAll) {
    const v = state.have[itemId];
    if (typeof v === "number") return haveField(itemId, nm, total, v, true);
    if (haveOpen === itemId) return haveField(itemId, nm, total, null, false, noAll);
    return "";
  }
  // the quantity as the button that opens "Tenho __ de M" (steps: "×2 ▾"; raw rows: "20 ▾")
  function qtyButton(itemId, nm, n, open, times) {
    return `<button type="button" class="row-qty qty-btn" id="have-${domId(itemId)}" data-have-open="${esc(itemId)}" aria-expanded="${open}" aria-label="${esc(t("steps.qtyLabel", { name: nm, n: num(n) }))}">${times ? "<small>×</small>" : ""}${num(n)}<span class="qty-chev" aria-hidden="true">▾</span></button>`;
  }
  function rawRow(r, state, D) {
    const it = D.items[r.item], nm = name(it, state.overrides), cb = "cb-raw-" + domId(r.item);
    const done = GK.calc.rawChecked(r, state.have, state.done), total = r.demand || r.qty;
    const craftable = GK.data.recipesFor(r.item).some(expandable);
    const sub = [];
    if (r.via) sub.push(`<span class="row-group">${esc(r.via.map((g) => t("raw.group", { name: name(D.items[g], state.overrides) })).join(" · "))}</span>`);
    let full = "";   // "como obter": cut to one line on the row, the whole text in its title (and in the item's detail)
    if (r.cycle) sub.push(`<span class="badge badge-warn">${esc(t("raw.cycle"))}</span>`);
    else if (r.reason === "refused") sub.push(`<span class="badge badge-warn">${esc(t("raw.refused"))}</span>`);
    else if (r.reason === "noexp") sub.push(`<span class="badge badge-ex">${esc(t("raw.noexp"))}</span>`);
    else if (it.members && r.reason !== "group") sub.push(esc(t("raw.members", { names: it.members.map((m) => name(D.items[m], state.overrides)).join(", ") })));
    else if (it.obtain && !r.via) { full = name(it.obtain); sub.push(esc(full)); }
    const actions = [];
    if (!done) {
      if (r.reason === "group" && it.members) actions.push(groupChooser(r.item, null, state, D));
      if (r.via) r.via.forEach((g) => actions.push(groupChooser(g, r.item, state, D)));
      if (!r.have && craftable && state.have[r.item] !== true) {
        const h = GK.calc.howToMake(r.item, D, state.choice, state.have, state.perks);
        const cur = h.r && (h.leaf !== "free" && h.leaf !== "noexp") ? h.r : null;
        actions.push(chooser(r.item, cur, state, !it.defaultRecipe, "raw.recipe"));
      }
    }
    // choosers and "Tenho [ 3 ] de 10": a line of their own under "como obter", as wide as the name and the quantity
    if (!done) actions.push(haveControls(r.item, nm, total, state, true));
    const more = actions.join("");
    const goal = r.isGoal ? `<span class="badge badge-goal">${esc(t("steps.goal"))}</span>` : "";
    // unticked: the quantity "× 20 ▾" (the same button as the steps') opens "Tenho __ de 20"; ticked: "× 20"
    const open = haveOpen === r.item || typeof state.have[r.item] === "number";
    const qty = done ? `<span class="row-qty"><small>×</small>${num(r.qty)}</span>` : qtyButton(r.item, nm, r.qty, open, true);
    return `<div class="row row-raw${done ? " is-done" : ""}">
      <label class="tick"><input type="checkbox" id="${cb}" data-raw-check="${esc(r.item)}" data-qty="${total}"${done ? " checked" : ""} aria-label="${esc(t("have.allLabel", { name: nm, n: num(total) }))}"></label>
      ${F.slotButton(it, nm)}
      <div class="row-main">${F.nameBlock(it, nm, cb, editing === r.item, goal, state.overrides, canEdit(state))}</div>
      ${qty}
      <div class="row-line2">${sub.length ? `<span class="row-sub row-obtain"${full ? ` title="${esc(full)}"` : ""}>${sub.join(" ")}</span>` : ""}</div>
      ${more ? `<div class="row-actions row-more">${more}</div>` : ""}
    </div>`;
  }
  const perkName = (b) => (b && b.perks ? b.perks.map((p) => name(GK.data.perks()[p] || { en: p })).join(" + ") : "");
  function lineList(lines, state, D) {
    return lines.map((i) => {
      const note = i.boosted ? ` <i class="perk-on">(${esc(t("steps.withPerk", { perk: perkName(i.bonus) }))})</i>` : i.note ? ` <i>(${esc(name(i.note))})</i>` : "";
      const grp = i.group ? ` <i>(${esc(t("steps.groupLine", { name: name(D.items[i.group], state.overrides) }))})</i>` : "";
      return `<b>${i.qty == null ? "?" : num(i.qty)}</b>&nbsp;${esc(name(D.items[i.item], state.overrides))}${grp}${note}`;
    }).join(" · ");
  }
  function stepRow(s, state, D) {
    const it = D.items[s.item], nm = name(it, state.overrides), key = "step:" + s.item, cb = "cb-step-" + domId(s.item);
    const done = GK.calc.stepChecked(s, state.done), r = s.recipe;
    // crafts only when they say something the quantity does not: no "1 execução", no "24 execuções" beside "×24"
    const meta = s.runs > 1 && s.runs !== s.need ? [t("steps.runs", { n: s.runs })] : [];
    if (s.outBonus) meta.push(t("steps.yieldPerk", { n: s.yield, perk: perkName(s.outBonus) }));
    else if (r.out.bonus && r.out.bonus.qty != null) meta.push(t("steps.yield", { n: s.yield }) + ` (${t("steps.yieldIf", { n: r.out.bonus.qty, perk: perkName(r.out.bonus) })})`);
    else if (r.out.bonus && r.out.bonus.add != null) meta.push(t("steps.yield", { n: s.yield }) + ` (${t("steps.yieldIf", { n: "+" + num(r.out.bonus.add), perk: perkName(r.out.bonus) })})`);
    else if (s.yield > 1 || r.out.note) meta.push(t("steps.yield", { n: s.yield }) + (r.out.note ? ` (${name(r.out.note)})` : ""));
    if (s.leftover > 0) meta.push(t("steps.left", { n: s.leftover }));
    // "×2 ▾" opens "Tenho __ de 2" (the field shows under the row while open or while a number is kept); a goal step
    // has no "Já tenho": a plain number. "Tenho tudo" makes the item a raw material, so no step row shows it.
    const actions = [], v = state.have[s.item];
    let qty = `<span class="row-qty"><small>×</small>${num(s.need)}</span>`;
    if (!s.isGoal) {
      const open = haveOpen === s.item || typeof v === "number";
      qty = qtyButton(s.item, nm, s.need, open, true);
      if (open) actions.push(haveControls(s.item, nm, s.demand, state, false));
    }
    const tech = F.techLine(r, state);
    if (tech.length) actions.push(`<span class="tech">${esc(tech.join(" · "))}</span>`);
    const ins = lineList(s.ins, state, D);
    const perRun = s.alts > 1 ? stepPicker(s, state, D, ins) : `<span class="row-in">${esc(t("steps.per"))} ${ins}</span>`;
    const extraBadges = (s.isGoal ? `<span class="badge badge-goal">${esc(t("steps.goal"))}</span>` : "") +
      (r.quality && s.alts > 1 ? ` <span class="badge badge-q" title="${esc(name(r.name || {}) || "")}">${esc(t("quality." + r.quality))}</span>` : "") +
      (r.example ? ` <span class="badge badge-ex" title="${esc(t("steps.exampleTitle"))}">${esc(t("steps.example"))}</span>` : "");
    const alt = r.alt.length ? `<span class="row-alt">${esc(t("steps.alt", { names: r.alt.map((a) => name(a, state.overrides)).join(", ") }))}</span>` : "";
    const extra = r.extra.length ? `<span class="row-extra">${esc(t("steps.extra"))} ${extraList(r.extra, state, D)}</span>` : "";
    return `<div class="row${done ? " is-done" : ""}">
      <label class="tick"><input type="checkbox" id="${cb}" data-done="${esc(key)}" data-qty="${s.need}"${done ? " checked" : ""} aria-label="${esc(t("steps.check", { name: nm }))}"></label>
      ${F.slotButton(it, nm)}
      <div class="row-main">
        ${F.nameBlock(it, nm, cb, editing === s.item, extraBadges, state.overrides, canEdit(state))}
        ${meta.length ? `<span class="row-sub tabnum">${esc(meta.join(" · "))}</span>` : ""}
        ${perRun}
        ${extra}${alt}
      </div>
      ${qty}
      ${actions.length ? `<div class="row-actions">${actions.join("")}</div>` : ""}
    </div>`;
  }
  // by-products: an active perk replaces the note with "4 Cinzas (com Cremador)"
  function extraList(lines, state, D) {
    return lines.map((i) => {
      const on = i.bonus && GK.calc.isBonusActive(i.bonus, state.perks);
      const q = on && i.bonus.qty != null ? i.bonus.qty : on && i.bonus.add != null && i.qty != null ? i.qty + i.bonus.add : i.qty;
      const note = on ? ` <i class="perk-on">(${esc(t("steps.withPerk", { perk: perkName(i.bonus) }))})</i>` : i.note ? ` <i>(${esc(name(i.note))})</i>` : "";
      return `<b>${q == null ? "?" : num(q)}</b>&nbsp;${esc(name(D.items[i.item], state.overrides))}${note}`;
    }).join(" · ");
  }
  function render(state, meta, plan) {
    if (meta && meta.from === "search-toggle") return;
    const D = GK.data.get();
    if (!state.goals.length) { root.innerHTML = `<div class="card empty plan-empty"><p>${esc(t("plan.empty"))}</p></div>`; return; }
    const loc = GK.i18n.meta(GK.i18n.lang()).locale;
    const byName = (a, b) => name(D.items[a.item], state.overrides).localeCompare(name(D.items[b.item], state.overrides), loc);
    const ticked = (r) => GK.calc.rawChecked(r, state.have, state.done);
    const plain = plan.raw.filter((r) => !ticked(r)).sort(byName), had = plan.raw.filter(ticked).sort(byName);
    const nmList = (ids) => ids.map((id) => name(D.items[id], state.overrides)).join(", ");
    const warn = (plan.cycles.length ? `<div class="warn" role="note">${esc(t("cycle.warn", { names: nmList(plan.cycles) }))}</div>` : "") +
      (plan.refused.length ? `<div class="warn" role="note">${esc(t("refused.warn", { names: nmList(plan.refused) }))}</div>` : "");
    const U = ui(state), shut = U.stationCollapsed || {};
    const doneOf = (steps) => steps.filter((s) => GK.calc.stepChecked(s, state.done)).length;
    const doneBadge = (done, total, cls) => `<span class="${cls} tabnum"><span aria-hidden="true">${num(done)}/${num(total)}</span><span class="sr-only">${esc(t("fold.doneSr", { done, total }))}</span></span>`;
    const nSt = plan.stations.length;
    const stations = U.stepsCollapsed ? "" : plan.stations.map((g, gi) => {
      // cards numbered in display order (the old depth badge "etapa N" collided with "Etapas" = rows)
      const numBox = `<span class="station-n tabnum" aria-hidden="true">${num(gi + 1)}</span>`;
      const numSr = `<span class="sr-only">${esc(t("steps.order", { n: gi + 1, total: nSt }))}: </span>`;
      const stName = name(g.station, state.overrides);
      const sub = g.station.build && !g.station.i18n ? `<span class="station-sub">${esc(t("station.build"))}</span>` : "";
      const again = g.repeat > 1 ? ` <span class="badge badge-again" title="${esc(t("steps.againTitle"))}">${esc(t("steps.again"))}</span>` : "";
      const k = stationKey(g), fk = "st:" + k, open = !shut[k], body = "st-body-" + domId(k);
      const nDone = doneOf(g.steps);
      return `<article class="card list station${open ? "" : " is-folded"}">
        <header class="station-h" data-fold-head="${esc(fk)}">${numBox}${slot(g.station, stName, true)}<h3>${numSr}${sub}${esc(stName)}${again}</h3><span class="station-meta">${doneBadge(nDone, g.steps.length, "station-done" + (nDone === g.steps.length ? " is-all" : ""))}</span>${foldBtn(fk, open, stName, body)}</header>
        ${open ? `<div class="station-rows" id="${body}">${g.steps.map((s) => stepRow(s, state, D)).join("")}</div>` : `<div id="${body}" hidden></div>`}
      </article>`;
    }).join("");
    const rawDone = had.length, stepDone = doneOf(plan.steps);
    // folded: the count is in the title already ("Matérias-primas 20"), the line says only what is checked
    const rawSum = t("fold.done", { done: rawDone, total: plan.raw.length });
    const stepSum = `${t("fold.stations", { n: plan.stations.length })} · ${t("fold.done", { done: stepDone, total: plan.steps.length })}`;
    root.innerHTML = `${warn}<div class="summary-grid">
      <section aria-labelledby="raw-h"${U.rawCollapsed ? ' class="is-folded"' : ""}>
        <div class="fold-head" data-fold-head="raw"><h2 class="h2" id="raw-h">${esc(t("raw.title"))} <span class="count">${plan.raw.length}</span></h2>${foldBtn("raw", !U.rawCollapsed, t("raw.title"), "raw-body")}</div>
        ${U.rawCollapsed ? `<p class="hint fold-sum tabnum" data-fold-head="raw">${esc(rawSum)}</p><div id="raw-body" hidden></div>` : `<div class="card list" id="raw-body">${plain.map((r) => rawRow(r, state, D)).join("")}
          ${had.length ? `<div class="raw-group-label">${esc(t("raw.haveGroup"))}</div>` + had.map((r) => rawRow(r, state, D)).join("") : ""}
        </div>`}
      </section>
      <section aria-labelledby="steps-h"${U.stepsCollapsed ? ' class="is-folded"' : ""}>
        <div class="fold-head" data-fold-head="steps"><h2 class="h2" id="steps-h">${esc(t("steps.title"))} <span class="count">${plan.steps.length}</span></h2>${foldBtn("steps", !U.stepsCollapsed, t("steps.title"), "steps-body")}</div>
        ${U.stepsCollapsed ? `<p class="hint fold-sum tabnum" data-fold-head="steps">${esc(stepSum)}</p><div class="stations" id="steps-body" hidden></div>` : `<div class="stations" id="steps-body">${stations}</div>`}
      </section>
    </div>`;
  }
  return { mount, render, stationKey };
})();

GK.app.registerPanel(GK.ui.summary, { id: "summary", panel: "summary", order: 50 });
