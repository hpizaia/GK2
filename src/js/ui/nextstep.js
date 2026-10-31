/* GK.ui.nextStep: planner slot panel "Próximo passo" (below "Hoje", above the goals; docs: protótipo ideia 5).
   The next step is the first unchecked row of the plan, in screen order: the raw materials still needed (not
   "Já tenho"; the list's own order, by name), then the steps of the station cards top to bottom. One line says it
   ("Agora: Juntar (matéria-prima) · 3× Pepita de Cobre", "Agora: Fornalha I · 1× Lingote de Bronze (3 Pepita de
   Cobre, 1 Estanho)") with "8 de 12"; the big "Feito" button checks that row (GK.store toggleDone, the same action
   as its checkbox) and the card moves on; "← Voltar um passo" unchecks the last row this button checked (a stack
   kept in memory only; rows unchecked by hand leave it). The current row of the list gets .is-next and an "agora"
   badge (re-applied after every summary render). Everything checked: "Plano concluído" and "Recomeçar"
   (GK.store clearDone, the action of "Limpar marcações", with a "Desfazer" toast).
   Hidden with no goals or the seeded example. Collapsible to one line ("Agora: … · 3× Pepita de Cobre"), per device
   in its own localStorage key "gk2-companion.nextstep" ({folded}), since GK.store ui keeps only its known flags.
   Owns: its <div data-panel="next-step"> in [data-slot="planner-top"], the .is-next decoration of planner rows.
   Exposes: GK.ui.nextStep.{mount, render, sequence, locate, phrase, KEY}.
   Registered via GK.app.registerPanel(..., {slot: "planner-top", order: 6}) (after "Hoje", order 5).
*/
GK.i18n.add({
  pt: {
    "next.title": "Próximo passo",
    "next.now": "Agora:",
    "next.gather": "Juntar (matéria-prima)",
    "next.count": "{n} de {total}",
    "next.countSr": "Passo {n} de {total}",
    "next.done": "✓ Feito",
    "next.doneLabel": "Feito: {text}",
    "next.back": "← Voltar um passo",
    "next.backLabel": "Voltar um passo: desmarcar {name}",
    "next.rule": "Marca a linha na lista abaixo",
    "next.uses": "usa",
    "next.usesEach": "cada uma usa",
    "next.badge": "agora",
    "next.finTitle": "Plano concluído",
    "next.finText": "Tudo marcado: {goals}.",
    "next.reset": "Recomeçar",
    "next.resetTitle": "Desmarca todas as linhas do plano",
    "next.resetToast": "Plano recomeçado: tudo desmarcado",
  },
  en: {
    "next.title": "Next step",
    "next.now": "Now:",
    "next.gather": "Gather (raw material)",
    "next.count": "{n} of {total}",
    "next.countSr": "Step {n} of {total}",
    "next.done": "✓ Done",
    "next.doneLabel": "Done: {text}",
    "next.back": "← Back one step",
    "next.backLabel": "Back one step: uncheck {name}",
    "next.rule": "Checks the row in the list below",
    "next.uses": "uses",
    "next.usesEach": "each uses",
    "next.badge": "now",
    "next.finTitle": "Plan complete",
    "next.finText": "All checked: {goals}.",
    "next.reset": "Start over",
    "next.resetTitle": "Unchecks every row of the plan",
    "next.resetToast": "Plan restarted: everything unchecked",
  },
});

GK.ui.nextStep = (function () {
  const { t, name, num } = GK.i18n, { esc, slot, domId } = GK.util;
  const KEY = "gk2-companion.nextstep";
  let root = null, planRoot = null, memo = "", lastKey = null, current = null, observer = null;
  let back = [];   // keys checked by "Feito", newest last (memory only)
  // ---------------------------------------------------------------- per-device folded flag
  function readFolded() {
    try { const v = window.localStorage && window.localStorage.getItem(KEY); return !!(v && JSON.parse(v).folded); } catch (e) { return false; }
  }
  function writeFolded(on) {
    try { if (window.localStorage) window.localStorage.setItem(KEY, JSON.stringify({ folded: !!on })); } catch (e) { /* storage blocked */ }
  }
  let folded = null;
  const isFolded = () => (folded === null ? (folded = readFolded()) : folded);
  // ---------------------------------------------------------------- pure part (tested in scripts/test_calc.mjs)
  /**
   * The rows of the plan in screen order: [{key, kind: "raw" | "step", item, qty, raw?, step?, station?}].
   * Raw materials still needed (r.have = "Já tenho" ones sit apart, under "Você já tem") sorted by name like the
   * Matérias-primas list, then every station card's steps from top to bottom.
   */
  function sequence(plan, state, D) {
    if (!plan) return [];
    const loc = GK.i18n.meta(GK.i18n.lang()).locale;
    const nm = (id) => name(D.items[id], state.overrides);
    const out = plan.raw.filter((r) => !r.have).sort((a, b) => nm(a.item).localeCompare(nm(b.item), loc))
      .map((r) => ({ key: "raw:" + r.item, kind: "raw", item: r.item, qty: r.qty, raw: r }));
    plan.stations.forEach((g) => g.steps.forEach((s) =>
      out.push({ key: "step:" + s.item, kind: "step", item: s.item, qty: s.need, step: s, station: g.station })));
    return out;
  }
  // the first unchecked row, "n de total" (n = checked + 1 while something is left)
  function locate(list, done) {
    const d = done || {};
    const cur = list.find((e) => !d[e.key]) || null;
    const checked = list.filter((e) => d[e.key]).length;
    return { cur, n: cur ? checked + 1 : checked, total: list.length };
  }
  // where the step happens: the station, or "Juntar (matéria-prima)"
  const whereOf = (e, state) => (e.kind === "raw" ? t("next.gather") : name(e.station, state.overrides));
  // inputs of the whole step (runs × per craft): "3 Pepita de Cobre, 1 Estanho"
  function totalIns(s, state, D) {
    return s.ins.map((i) => `${i.qty == null ? "?" : num(i.qty * s.runs)} ${name(D.items[i.item], state.overrides)}`).join(", ");
  }
  // "Agora: Fornalha I · 1× Lingote de Bronze (3 Pepita de Cobre, 1 Estanho)" (plain text)
  function phrase(e, state, D) {
    const it = `${num(e.qty)}× ${name(D.items[e.item], state.overrides)}`;
    const ins = e.kind === "step" && e.step.ins.length ? ` (${totalIns(e.step, state, D)})` : "";
    return `${t("next.now")} ${whereOf(e, state)} · ${it}${ins}`;
  }
  // the smaller line under the item: how to get it, or "2 execuções · cada uma usa 3 Pepita · 1 Estanho" (HTML)
  function needHtml(e, state, D) {
    if (e.kind === "raw") {
      const it = D.items[e.item];
      if (it.members) return esc(t("raw.members", { names: it.members.filter((m) => D.items[m]).map((m) => name(D.items[m], state.overrides)).join(", ") }));
      return it.obtain ? esc(name(it.obtain)) : "";
    }
    const s = e.step;
    const per = s.ins.map((i) => `<b>${i.qty == null ? "?" : num(i.qty)}</b>&nbsp;${esc(name(D.items[i.item], state.overrides))}`).join(" · ");
    return `${esc(t("steps.runs", { n: s.runs }))}${per ? ` · ${esc(t(s.runs === 1 ? "next.uses" : "next.usesEach"))} ${per}` : ""}`;
  }
  // ---------------------------------------------------------------- the current row in the list
  const rowCb = (e) => document.getElementById((e.kind === "raw" ? "cb-raw-" : "cb-step-") + domId(e.item));
  function decorate() {
    if (!planRoot) return;
    planRoot.querySelectorAll(".row.is-next").forEach((r) => r.classList.remove("is-next"));
    planRoot.querySelectorAll(".badge-now").forEach((b) => b.remove());
    if (!current || !root || root.hidden) return;
    const cb = rowCb(current), row = cb && cb.closest(".row");
    if (!row) return;
    row.classList.add("is-next");
    const nm = row.querySelector(".row-name");
    if (nm) nm.insertAdjacentHTML("beforeend", `<span class="badge badge-goal badge-now">${esc(t("next.badge"))}</span>`);
  }
  // ---------------------------------------------------------------- actions
  function setFolded(on) {
    folded = !!on;
    writeFolded(folded);
    memo = "";
    render(GK.store.get(), {}, GK.app.plan());
    const b = document.getElementById("next-tgl");
    if (b) b.focus({ preventScroll: true });
  }
  function focusAfter() {
    const el = document.getElementById("next-done") || document.getElementById("next-reset") || document.getElementById("next-tgl");
    if (el) el.focus({ preventScroll: true });
  }
  function doDone() {
    const st = GK.store.get(), loc = locate(sequence(GK.app.plan(), st, GK.data.get()), st.done);
    if (!loc.cur) return;
    back.push(loc.cur.key);
    GK.store.actions.toggleDone(loc.cur.key, true);
    focusAfter();
  }
  function doBack() {
    const k = back.pop();
    if (k) GK.store.actions.toggleDone(k, false);
    focusAfter();
  }
  function doReset() {
    const was = Object.keys(GK.store.get().done || {});
    back = [];
    GK.store.actions.clearDone();
    focusAfter();
    GK.ui.fmt.undoToast(t("next.resetToast"), () => {
      was.forEach((k) => GK.store.actions.toggleDone(k, true));
      focusAfter();
    });
  }
  const CONTROLS = "button, a, input, select, textarea, label";
  function mount(el, plan) {
    root = el;
    planRoot = plan || document;
    root.hidden = true;
    root.addEventListener("click", (e) => {
      if (e.target.closest("#next-tgl") || (e.target.closest("[data-next-head]") && !e.target.closest(CONTROLS))) { setFolded(!isFolded()); return; }
      if (e.target.closest("#next-done")) { doDone(); return; }
      if (e.target.closest("#next-back")) { doBack(); return; }
      if (e.target.closest("#next-reset")) doReset();
    });
    // the summary re-renders its rows on its own (name editing, "tenho N de M"): mark the current row again
    const sum = document.querySelector('[data-panel="summary"]');
    if (sum && typeof MutationObserver === "function") {
      observer = new MutationObserver(decorate);
      observer.observe(sum, { childList: true });
    }
  }
  function render(state, meta, plan) {
    if (!root || (meta && meta.from === "search-toggle")) return;
    const D = GK.data.get();
    const list = !state.goals.length || state.example ? [] : sequence(plan, state, D);
    back = back.filter((k) => state.done[k] && list.some((e) => e.key === k));
    if (!list.length) {
      current = null;
      if (memo !== "none") { memo = "none"; root.hidden = true; root.innerHTML = ""; }
      queueMicrotask(decorate);
      return;
    }
    const loc = locate(list, state.done), cur = loc.cur, shut = isFolded();
    current = cur;
    const line = cur ? phrase(cur, state, D) : t("next.finTitle");
    const lastBack = back.length ? list.find((e) => e.key === back[back.length - 1]) : null;
    const sig = [GK.i18n.lang(), shut, cur ? cur.key : "", line, loc.n, loc.total, lastBack ? lastBack.key : "",
      cur ? needHtml(cur, state, D) : state.goals.map((g) => g.item + g.qty).join(",")].join("|");
    if (sig !== memo) {
      memo = sig;
      root.hidden = false;
      const fresh = cur ? cur.key !== lastKey : lastKey !== "";
      lastKey = cur ? cur.key : "";
      const count = `<span aria-hidden="true">${esc(t("next.count", { n: loc.n, total: loc.total }))}</span><span class="sr-only">${esc(t("next.countSr", { n: loc.n, total: loc.total }))}</span>`;
      const title = t("next.title");
      const tgl = `<button type="button" class="btn fold-btn" id="next-tgl" aria-expanded="${!shut}" aria-controls="next-body" title="${esc(t(shut ? "fold.expand" : "fold.collapse"))}" aria-label="${esc(t(shut ? "fold.expandX" : "fold.collapseX", { name: title }))}"></button>`;
      const lineHtml = cur ? `<b>${esc(t("next.now"))}</b> ${esc(line.slice(t("next.now").length + 1))}` : `<b>${esc(line)}</b>`;
      const backBtn = lastBack ? `<button type="button" class="btn btn-ghost btn-sm" id="next-back" aria-label="${esc(t("next.backLabel", { name: name(D.items[lastBack.item], state.overrides) }))}">${esc(t("next.back"))}</button>` : "<span></span>";
      let body = "";
      if (!shut && cur) {
        const nm = name(D.items[cur.item], state.overrides), need = needHtml(cur, state, D);
        body = `<div class="next-main${fresh ? " is-fresh" : ""}">${slot(D.items[cur.item], nm)}<div>
            <p class="next-where"><span class="next-now">${esc(t("next.now"))}</span> ${esc(whereOf(cur, state))}</p>
            <p class="next-what"><span class="q">${esc(num(cur.qty))}×</span> ${esc(nm)}</p>
            ${need ? `<p class="next-need">${need}</p>` : ""}
          </div></div>
          <button type="button" class="btn next-done" id="next-done" aria-label="${esc(t("next.doneLabel", { text: line }))}">${esc(t("next.done"))}</button>
          <div class="next-foot">${backBtn}<span class="next-rule">${esc(t("next.rule"))}</span></div>`;
      } else if (!shut) {
        const goals = state.goals.filter((g) => D.items[g.item]).map((g) => `${num(g.qty)}× ${name(D.items[g.item], state.overrides)}`).join(", ");
        body = `<div class="next-main${fresh ? " is-fresh" : ""}"><span class="next-fin-mark" aria-hidden="true">✓</span><div>
            <p class="next-fin-title">${esc(t("next.finTitle"))}</p>
            <p class="next-need">${esc(t("next.finText", { goals }))}</p>
          </div></div>
          <button type="button" class="btn" id="next-reset" title="${esc(t("next.resetTitle"))}">${esc(t("next.reset"))}</button>
          <div class="next-foot">${backBtn}</div>`;
      }
      root.innerHTML = `<section class="next${shut ? " is-folded" : ""}${cur ? "" : " is-fin"}" aria-labelledby="next-h">
        <div class="card next-card">
          <div class="next-head fold-head" data-next-head>
            <h2 class="next-title" id="next-h"><span class="next-label">${esc(title)}</span><span class="next-line">${lineHtml}</span></h2>
            <span class="next-count tabnum">${count}</span>
            ${tgl}
          </div>
          <div class="next-body" id="next-body"${shut ? " hidden" : ""} aria-live="polite">${body}</div>
        </div>
      </section>`;
    }
    queueMicrotask(decorate);   // after the summary (order 50) has rendered its rows in this same loop
  }
  return { mount, render, sequence, locate, phrase, KEY };
})();

GK.app.registerPanel(GK.ui.nextStep, { id: "next-step", slot: "planner-top", order: 6 });
