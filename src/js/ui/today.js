/* GK.ui.today: planner slot panel "Hoje" (above "Tecnologias que faltam"). With the current weekday set
   (GK.store day): "Hoje: Dia da Ira · 3 coisas", that day's events as a compact list, "Avançar dia" and
   "Ver semana" (→ #days). Without it: "Qual dia é hoje no jogo?" and the 6 day medallions as buttons (tap = set),
   plus the HUD counter field once calibrated (GK.store dayAnchor: the number alone gives the day).
   Nothing when the page has no week data. Re-renders only when (day, dayNumber, calibration, collapsed, lang) change.
   Collapsible (GK.store ui.todayCollapsed, per device): the toggle at the header's right or a tap on the header
   text; collapsed = one compact row "Hoje: Dia da Ira · 3 coisas" with the medallion, "Avançar" and the toggle.
   Owns: its <div data-panel="today"> in [data-slot="planner-top"]. Uses the week helpers of GK.ui.days.
   Exposes: GK.ui.today.{mount, render}. Registered via GK.app.registerPanel(..., {slot: "planner-top", order: 5}).
*/
GK.i18n.add({
  pt: {
    "today.title": "Hoje",
    "today.line": "Hoje: {name}",
    "today.ask": "Qual dia é hoje no jogo?",
    "today.askHint": "Toque no símbolo que a seta da roda aponta no jogo.",
    "today.pick": "Hoje é {name}",
    "today.week": "Ver semana",
    "today.nothing": "Nada especial registrado para hoje.",
    "today.orNumber": "ou o contador do jogo:",
    "today.collapse": "Recolher",
    "today.expand": "Expandir",
    "today.collapseX": "Recolher: {name}",
    "today.expandX": "Expandir: {name}",
    "today.advShort": "Avançar",
  },
  en: {
    "today.title": "Today",
    "today.line": "Today: {name}",
    "today.ask": "Which day is it in the game?",
    "today.askHint": "Tap the symbol the wheel's arrow points at in the game.",
    "today.pick": "Today is {name}",
    "today.week": "See the week",
    "today.nothing": "Nothing special recorded for today.",
    "today.orNumber": "or the game counter:",
    "today.collapse": "Collapse",
    "today.expand": "Expand",
    "today.collapseX": "Collapse: {name}",
    "today.expandX": "Expand: {name}",
    "today.advShort": "Next",
  },
});

GK.ui.today = (function () {
  const { t, name } = GK.i18n, { esc } = GK.util;
  const DY = () => GK.ui.days;
  let root = null, memo = "";
  const collapsed = (state) => !!(state.ui && state.ui.todayCollapsed);
  // the 44 px fold toggle (chevron drawn in CSS: .fold-btn); same id in both states so the focus stays on it
  const foldBtn = (open, label) => `<button type="button" class="btn fold-btn" id="today-tgl" data-today-tgl aria-expanded="${open}" aria-controls="today-body" title="${esc(t(open ? "today.collapse" : "today.expand"))}" aria-label="${esc(t(open ? "today.collapseX" : "today.expandX", { name: label }))}"></button>`;
  const CONTROLS = "button, a, input, select, textarea, label";
  function mount(el) {
    root = el;
    root.addEventListener("click", (e) => {
      const tg = e.target.closest("[data-today-tgl]");
      if (tg || (e.target.closest("[data-today-head]") && !e.target.closest(CONTROLS))) {
        GK.store.actions.setUi({ todayCollapsed: !collapsed(GK.store.get()) });
        return;
      }
      const p = e.target.closest("[data-today-pick]");
      if (p) {
        const d = DY().day(p.dataset.todayPick), before = GK.store.get().dayAnchor;
        GK.store.actions.setDay(p.dataset.todayPick);
        const a = GK.store.get().dayAnchor;
        if (d) GK.ui.toast(a && (!before || before.number !== a.number || before.day !== a.day) ? t("days.calToast", { n: a.number, name: name(d.name) }) : t("days.setToast", { name: name(d.name) }));
        const adv = document.getElementById("today-adv");
        if (adv) adv.focus({ preventScroll: true });
        return;
      }
      if (e.target.closest("[data-today-adv]")) {
        if (!GK.store.actions.advanceDay()) return;
        const st = GK.store.get(), d = DY().current(st);
        if (d) GK.ui.toast(st.dayNumber != null ? t("days.advToastN", { name: name(d.name), n: st.dayNumber }) : t("days.advToast", { name: name(d.name) }));
        return;
      }
      const w = e.target.closest("[data-today-week]");
      if (w) { DY().open(GK.store.get().day); return; }
      const ro = e.target.closest("[data-recipe-open]");
      if (ro && GK.ui.recipes) GK.ui.recipes.open(ro.dataset.recipeOpen, { from: "plan" });
    });
    root.addEventListener("change", (e) => {
      if (e.target.id !== "today-num") return;
      const before = GK.store.get().dayAnchor;
      GK.store.actions.setDayNumber(e.target.value);
      DY().numberToast(before);
      const adv = document.getElementById("today-adv");
      if (adv) adv.focus({ preventScroll: true });
    });
  }
  function evRow(ev) {
    const who = DY().whoText(ev);
    return `<li class="today-ev"${ev.source ? ` title="${esc(t("days.source", { src: ev.source }))}"` : ""}>
      <span class="today-ev-ico" title="${esc(t("days.kind." + ev.kind))}">${DY().kindIcon(ev.kind, 16)}<span class="sr-only">${esc(t("days.kind." + ev.kind))}: </span></span>
      <span class="today-ev-main">${esc(DY().eventText(ev))}${who ? ` <span class="today-ev-who">· ${esc(who)}</span>` : ""}${DY().confidenceBadge(ev)}</span>
    </li>`;
  }
  function render(state) {
    if (!root) return;
    const w = DY() && DY().week();
    const d = w ? DY().current(state) : null;
    const a = state.dayAnchor;
    const shut = collapsed(state);
    const sig = !w ? "none" : [d ? d.id : "", state.dayNumber, a ? a.number + a.day : "", shut, GK.i18n.lang()].join("|");
    if (sig === memo) return;
    memo = sig;
    if (!w) { root.innerHTML = ""; return; }
    if (!d) {
      root.innerHTML = `<section class="today today-ask" aria-labelledby="today-h">
        <div class="fold-head" data-today-head><h2 class="h2" id="today-h">${esc(t("today.ask"))}</h2>${foldBtn(!shut, t("today.title"))}</div>
        ${shut ? `<div id="today-body" hidden></div>` : `<div id="today-body">
        <p class="hint">${esc(t("today.askHint"))}</p>
        <div class="today-picks" role="group" aria-label="${esc(t("today.ask"))}">${w.days.map((x) =>
          `<button type="button" class="today-pick" id="today-pick-${esc(x.id)}" data-today-pick="${esc(x.id)}" title="${esc(name(x.name))}" aria-label="${esc(t("today.pick", { name: name(x.name) }))}"${x.color ? ` style="--day:${esc(x.color)}"` : ""}>${DY().medal(x, 36)}</button>`).join("")}</div>
        ${a ? `<label class="today-num" for="today-num"><span>${esc(t("today.orNumber"))}</span>
          <input type="number" id="today-num" inputmode="numeric" min="1" max="99999" step="1" placeholder="${esc(t("days.numberPh"))}" value="${state.dayNumber != null ? state.dayNumber : ""}"></label>` : ""}
        </div>`}
      </section>`;
      return;
    }
    const counter = state.dayNumber != null ? ` <span class="count tabnum">${esc(t("days.counter", { n: state.dayNumber }))}</span>` : "";
    const dayStyle = d.color ? ` style="--day:${esc(d.color)}"` : "";
    if (shut) {
      // one compact row: medallion, "Hoje: X · N coisas", Avançar, toggle (the heading stays for screen readers)
      root.innerHTML = `<section class="today is-folded" aria-labelledby="today-h">
        <h2 class="sr-only" id="today-h">${esc(t("today.title"))}</h2>
        <div class="card today-card today-mini"${dayStyle}>
          <div class="today-head" data-today-head>
            ${DY().tile(d, 26)}
            <p class="today-line"><b>${esc(t("today.line", { name: name(d.name) }))}</b> · ${esc(t("days.count", { n: d.events.length }))}${state.dayNumber != null ? ` · <span class="tabnum">${esc(t("days.counter", { n: state.dayNumber }))}</span>` : ""}</p>
            <button type="button" class="btn btn-sm today-adv-sm" id="today-adv" data-today-adv aria-label="${esc(t("days.advance"))}" title="${esc(t("days.advance"))}">${esc(t("today.advShort"))} ›</button>
            ${foldBtn(false, t("today.title"))}
          </div>
          <div id="today-body" hidden></div>
        </div>
      </section>`;
      return;
    }
    root.innerHTML = `<section class="today" aria-labelledby="today-h">
      <div class="fold-head" data-today-head><h2 class="h2" id="today-h">${esc(t("today.title"))}${counter}</h2>${foldBtn(true, t("today.title"))}</div>
      <div class="card today-card" id="today-body"${dayStyle}>
        <div class="today-head">
          ${DY().tile(d, 26)}
          <p class="today-line"><b>${esc(t("today.line", { name: name(d.name) }))}</b> · ${esc(t("days.count", { n: d.events.length }))}</p>
        </div>
        ${d.events.length ? `<ul class="today-evs">${d.events.map(evRow).join("")}</ul>` : `<p class="hint today-none">${esc(t("today.nothing"))}</p>`}
        <div class="today-ctl">
          <button type="button" class="btn" id="today-adv" data-today-adv>${esc(t("days.advance"))} ›</button>
          <button type="button" class="btn btn-ghost" id="today-week" data-today-week>${esc(t("today.week"))}</button>
        </div>
      </div>
    </section>`;
  }
  return { mount, render };
})();

GK.app.registerPanel(GK.ui.today, { id: "today", slot: "planner-top", order: 5 });
