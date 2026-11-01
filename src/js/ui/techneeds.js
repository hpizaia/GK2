/* GK.ui.techneeds: planner slot panel "Tecnologias que faltam": the technologies still to research for every
   recipe of the current plan (GK.tech.forPlan), point totals per colour, the list in research order with an
   inline "Já pesquisei" checkbox, and the quests / perks the plan also needs. Hidden when nothing is missing.
   Re-renders only when the plan's tech signature, the researched set or the language changes.
   The hint is one short line, "Pesquise nesta ordem; marque o que já tem."
   The panel folds like "Matérias-primas" / "Etapas" (the same thin chevron, a tap
   on the header text too; GK.store ui.tnCollapsed, per device); folded, it shows only "Total de pontos: …".
   Owns: its <div data-panel="tech-needs"> in [data-slot="planner-extra"].
   Exposes: GK.ui.techneeds.{mount, render}. Registered via GK.app.registerPanel(..., {slot: "planner-extra"}).
*/
GK.ui.techneeds = (function () {
  const { t, name } = GK.i18n, { esc, domId } = GK.util;
  const TK = GK.tech;
  const FIRST = 8;          // rows shown before "Mostrar mais"
  let root = null, memo = "", expanded = false;
  const shutOf = (state) => !!(state.ui && state.ui.tnCollapsed);
  function mount(el) {
    root = el;
    root.addEventListener("change", (e) => {
      const cb = e.target.closest("[data-research]");
      if (!cb) return;
      const tc = TK.get(cb.dataset.research);
      GK.store.actions.setResearched(cb.dataset.research, cb.checked);
      if (tc && cb.checked) GK.ui.toast(t("tn.marked", { name: name(tc) }));
    });
    root.addEventListener("click", (e) => {
      if (e.target.closest("[data-tn-fold]") || (e.target.closest("[data-tn-head]") && !e.target.closest(GK.ui.fmt.CONTROLS))) {
        GK.store.actions.setUi({ tnCollapsed: !shutOf(GK.store.get()) });
        return;
      }
      const o = e.target.closest("[data-open]");
      if (o) { GK.ui.tech.open(o.dataset.open, { from: "plan" }); return; }
      if (e.target.closest("[data-tn-more]")) { expanded = !expanded; memo = ""; render(GK.store.get(), {}, GK.app.plan()); }
    });
  }
  function row(tc, why, state) {
    const D = GK.data.get();
    const b = TK.branch(tc.branch);
    const forItems = (why[tc.id] || []).map((id) => name(D.items[id], state.overrides));
    const sub = [b ? name(b) : ""];
    if (forItems.length) sub.push(t("tn.for", { names: forItems.slice(0, 3).join(", ") + (forItems.length > 3 ? "…" : "") }));
    return `<div class="row tech-row tn-row">
      <label class="tick"><input type="checkbox" id="tn-${domId(tc.id)}" data-research="${esc(tc.id)}" aria-label="${esc(t("tech.researchedLabel", { name: name(tc) }))}"></label>
      ${GK.ui.tech.techSlot(tc)}
      <button type="button" class="tech-open" data-open="${esc(tc.id)}" aria-label="${esc(t("tech.open", { name: name(tc) }))}">
        <span class="row-name">${esc(name(tc))}${GK.ui.tech.badges(tc)}</span>
        <span class="row-sub tech-sub">${GK.ui.tech.costHtml(tc.cost)}<span class="tech-via">${esc(sub.filter(Boolean).join(" · "))}</span></span>
      </button>
      <span class="tech-chev" aria-hidden="true">›</span>
    </div>`;
  }
  function render(state, meta, plan) {
    if (!root) return;
    if (meta && meta.from === "search-toggle") return;
    if (!TK.available() || !state.goals.length) { if (memo !== "none") { root.innerHTML = ""; memo = "none"; } return; }
    const shut = shutOf(state);
    const sig = TK.signature(plan, state) + "|" + GK.i18n.lang() + "|" + expanded + "|" + shut + "|" + JSON.stringify(state.overrides[GK.i18n.lang()] || {});
    if (sig === memo) return;
    memo = sig;
    const need = TK.forPlan(plan, state);
    if (!need.techs.length && !need.other.length) { root.innerHTML = ""; return; }
    const shown = expanded ? need.techs : need.techs.slice(0, FIRST), rest = need.techs.length - shown.length;
    const other = need.other.map((o) => t(o.type === "perk" ? "tn.perk" : "tn.quest", { name: name(o) }));
    const title = t("tn.title");
    // the same thin toggle as "Matérias-primas" / "Etapas" (GK.ui.fmt.foldBtn with sec); stable id for the focus
    const tgl = GK.ui.fmt.foldBtn('id="fold-tn" data-tn-fold', !shut, title, "tn-body", true);
    const head = `<div class="fold-head" data-tn-head><h2 class="h2" id="tn-h">${esc(title)} <span class="count">${need.techs.length}</span></h2>${tgl}</div>`;
    if (shut) {
      // folded: only the point totals (or, with no tech left, what else the plan needs)
      const sum = need.techs.length
        ? `<span class="tn-sum-l">${esc(t("tn.totalSum"))}</span>${GK.ui.tech.costHtml(need.cost)}`
        : `<b>${esc(t("tn.other"))}</b> ${esc(other.join(" · "))}`;
      root.innerHTML = `<section class="tn is-folded" aria-labelledby="tn-h">${head}
        <p class="hint fold-sum tabnum" data-tn-head>${sum}</p><div id="tn-body" hidden></div>
      </section>`;
      return;
    }
    root.innerHTML = `<section class="tn" aria-labelledby="tn-h">
      ${head}
      <div id="tn-body">
      ${need.techs.length ? `<p class="hint">${esc(t("tn.hint"))}</p>
      <div class="card tn-card">
        <div class="tn-total"><span class="tech-d-label">${esc(t("tn.total"))}</span>${GK.ui.tech.costHtml(need.cost, { big: true })}</div>
        <div class="list">${shown.map((tc) => row(tc, need.why, state)).join("")}</div>
        ${need.techs.length > FIRST ? `<div class="tn-foot"><button type="button" class="btn btn-sm btn-ghost" data-tn-more aria-expanded="${expanded}">${esc(expanded ? t("tn.less") : t("tn.more", { n: rest }))}</button></div>` : ""}
      </div>` : ""}
      ${other.length ? `<p class="tn-other"><b>${esc(t("tn.other"))}</b> ${esc(other.join(" · "))}</p>` : ""}
      <p class="tn-link"><a href="#tech">${esc(t("tn.openTab"))} ›</a></p>
      </div>
    </section>`;
  }
  return { mount, render };
})();

GK.app.registerPanel(GK.ui.techneeds, { id: "tech-needs", slot: "planner-extra", order: 10 });
