/* GK.ui.today: planner slot panel "Hoje" (above "Tecnologias que faltam"). With the current weekday set
   (GK.store day), open: the heading "Dia da Ira · dia 61 · 3 coisas" with the day's medallion (1.6.0: one line instead
   of "Hoje dia 61" over "Hoje: Dia da Ira · 3 coisas"; screen readers still hear "Hoje:" first), that day's events
   as a compact list (the "· Agatha (a Freira)" suffix only when the event's text does not already name that person:
   namedIn), each with a 44 px "feito hoje" checkbox (GK.store dayDone, synced; the ticks reset by themselves when
   the day changes: advance, another day picked, or a counter that lands on another day), "Tudo feito hoje ✓" once
   every event is ticked, that weekday's "Bilhete do dia" (GK.store dayNotes, synced; edited in place through GK.ui.days.noteBox),
   a smaller "Amanhã: Dia da Preguiça · 2 coisas" with tomorrow's events one line each and tomorrow's note
   (a tap opens the Dias screen on that day: GK.ui.days.open), then "Avançar dia" and "Ver semana" (→ #days).
   "Avançar dia" here shows no toast (1.6.0): the panel's own line already shows the new day (the Dias screen keeps
   its toast).
   Without a day: "Qual dia é hoje no jogo?" and the 6 day medallions as buttons (tap = set),
   plus the HUD counter field once calibrated (GK.store dayAnchor: the number alone gives the day).
   Nothing when the page has no week data. Re-renders only when (day, dayNumber, calibration, collapsed, lang,
   ticks, today's and tomorrow's notes, note editing) change.
   Collapsible (GK.store ui.todayCollapsed, per device; folded by default since 1.3.4): the toggle at the header's
   right or a tap on the header text; collapsed = one compact row "Hoje: Dia da Ira" over "3 coisas · dia 61" (or
   "2/3 feitas" once something is ticked) with the medallion, "Avançar dia" and the toggle, or, with no day set, the row
   "Marcar o dia do jogo". The day picker shows each day's sin name under its medallion (the medallion art comes
   from GK.ui.days.medal); picking a day folds the panel back to its one-line row.
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
    "today.advShort": "Avançar dia",
    "today.mark": "Marcar o dia do jogo",
    "today.doneN": "{done}/{n} feitas",
    "today.check": "Feito hoje: {text}",
    "today.allDone": "Tudo feito hoje ✓",
    "today.tomorrow": "Amanhã: {name}",
    "today.tomorrowOpen": "Ver {name} na semana",
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
    "today.advShort": "Next day",
    "today.mark": "Set the game day",
    "today.doneN": "{done}/{n} done",
    "today.check": "Done today: {text}",
    "today.allDone": "All done today ✓",
    "today.tomorrow": "Tomorrow: {name}",
    "today.tomorrowOpen": "See {name} in the week",
  },
});

GK.ui.today = (function () {
  const { t, name } = GK.i18n, { esc } = GK.util;
  const DY = () => GK.ui.days;
  let root = null, memo = "", notes = null;
  const collapsed = (state) => !!(state.ui && state.ui.todayCollapsed);
  // the 44 px fold toggle (chevron drawn in CSS: .fold-btn); same id in both states so the focus stays on it
  const foldBtn = (open, label) => `<button type="button" class="btn fold-btn" id="today-tgl" data-today-tgl aria-expanded="${open}" aria-controls="today-body" title="${esc(t(open ? "today.collapse" : "today.expand"))}" aria-label="${esc(t(open ? "today.collapseX" : "today.expandX", { name: label }))}"></button>`;
  const CONTROLS = "button, a, input, select, textarea, label";
  // ticked event indexes of today that still exist in the data
  const ticked = (state, d) => GK.store.doneToday(state).filter((i) => i < d.events.length);
  // "3 coisas", or "2/3 feitas" once something is ticked
  const countText = (state, d) => {
    const n = ticked(state, d).length;
    return n ? t("today.doneN", { done: n, n: d.events.length }) + (n === d.events.length ? " ✓" : "") : t("days.count", { n: d.events.length });
  };
  // re-render now, keeping the focus on the element (same id) that had it
  function rerender() {
    const act = document.activeElement && root && root.contains(document.activeElement) ? document.activeElement.id : null;
    memo = "";
    render(GK.store.get());
    if (act) { const el = document.getElementById(act); if (el) el.focus({ preventScroll: true }); }
  }
  function mount(el) {
    root = el;
    notes = DY().noteBox("today", rerender);
    notes.bind(root);
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
        GK.store.actions.setUi({ todayCollapsed: true });   // back to the one-line row, now with the day
        const a = GK.store.get().dayAnchor;
        if (d) GK.ui.toast(a && (!before || before.number !== a.number || before.day !== a.day) ? t("days.calToast", { n: a.number, name: name(d.name) }) : t("days.setToast", { name: name(d.name) }));
        const adv = document.getElementById("today-adv");
        if (adv) adv.focus({ preventScroll: true });
        return;
      }
      // no toast: the Hoje line under the finger already shows the new day
      if (e.target.closest("[data-today-adv]")) { GK.store.actions.advanceDay(); return; }
      const tm = e.target.closest("[data-today-tmr]");
      if (tm) { DY().open(tm.dataset.todayTmr); return; }
      const w = e.target.closest("[data-today-week]");
      if (w) { DY().open(GK.store.get().day); return; }
      const ro = e.target.closest("[data-recipe-open]");
      if (ro && GK.ui.recipes) GK.ui.recipes.open(ro.dataset.recipeOpen, { from: "plan" });
    });
    root.addEventListener("change", (e) => {
      const cb = e.target.closest && e.target.closest("[data-today-done]");
      if (cb) {
        const id = cb.id;
        GK.store.actions.toggleDayDone(+cb.dataset.todayDone, cb.checked);
        const again = document.getElementById(id);
        if (again) again.focus({ preventScroll: true });
        return;
      }
      if (e.target.id !== "today-num") return;
      const before = GK.store.get().dayAnchor;
      GK.store.actions.setDayNumber(e.target.value);
      DY().numberToast(before);
      const adv = document.getElementById("today-adv");
      if (adv) adv.focus({ preventScroll: true });
    });
  }
  // the words of a name, folded (no accents, lower case), without articles / prepositions
  const STOP = /^(a|o|as|os|da|do|das|dos|de|e|the|of|and)$/;
  const words = (s) => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().split(/[^a-z0-9]+/).filter((w) => w && !STOP.test(w));
  // "Agatha (a Freira)" is already in "A Freira do Burro Peludo: Agatha entrega…" (any word of the name, whole word)
  const namedIn = (who, text) => { const tw = new Set(words(text)); return words(who).some((w) => tw.has(w)); };
  function evRow(ev, i, done) {
    const text = DY().eventText(ev), whoAll = DY().whoText(ev), who = whoAll && !namedIn(whoAll, text) ? whoAll : "";
    return `<li class="today-ev${done ? " is-done" : ""}"${ev.source ? ` title="${esc(t("days.source", { src: ev.source }))}"` : ""}>
      <label class="tick today-tick"><input type="checkbox" id="today-done-${i}" data-today-done="${i}"${done ? " checked" : ""} aria-label="${esc(t("today.check", { text }))}"></label>
      <span class="today-ev-ico" title="${esc(t("days.kind." + ev.kind))}">${DY().kindIcon(ev.kind, 16)}<span class="sr-only">${esc(t("days.kind." + ev.kind))}: </span></span>
      <span class="today-ev-main">${esc(text)}${who ? ` <span class="today-ev-who">· ${esc(who)}</span>` : ""}${DY().confidenceBadge(ev)}</span>
    </li>`;
  }
  // "Amanhã": secondary, one button (opens the Dias screen on that day)
  function tomorrow(nx, state) {
    if (!nx) return "";
    const note = (state.dayNotes || {})[nx.id] || "";
    return `<button type="button" class="today-tmr" id="today-tmr" data-today-tmr="${esc(nx.id)}" title="${esc(t("today.tomorrowOpen", { name: name(nx.name) }))}"${nx.color ? ` style="--day:${esc(nx.color)}"` : ""}>
      <span class="today-tmr-h">${DY().tile(nx, 18, "today-tmr-tile")}<span class="today-tmr-t"><b>${esc(t("today.tomorrow", { name: name(nx.name) }))}</b> · ${esc(t("days.count", { n: nx.events.length }))}</span><span class="today-tmr-go" aria-hidden="true">›</span></span>
      ${nx.events.map((ev) => `<span class="today-tmr-ev"><span class="today-tmr-ico" aria-hidden="true">${DY().kindIcon(ev.kind, 12)}</span><span class="today-tmr-x">${esc(DY().eventText(ev))}</span></span>`).join("")}
      ${note ? `<span class="today-tmr-ev today-tmr-note"><span class="today-tmr-ico" aria-hidden="true">✎</span><span class="today-tmr-x">${esc(t("days.note.label"))}: ${esc(note)}</span></span>` : ""}
    </button>`;
  }
  function render(state) {
    if (!root) return;
    const w = DY() && DY().week();
    const d = w ? DY().current(state) : null;
    const nx = d ? DY().next(d) : null;
    const a = state.dayAnchor;
    const shut = collapsed(state);
    const sig = !w ? "none" : [d ? d.id : "", state.dayNumber, a ? a.number + a.day : "", shut, GK.i18n.lang(),
      d ? ticked(state, d).join(",") : "", d && notes ? notes.sig(d.id) : "", nx ? (state.dayNotes || {})[nx.id] || "" : ""].join("|");
    if (sig === memo) return;
    memo = sig;
    if (!w) { root.innerHTML = ""; return; }
    if (!d && shut) {
      // one quiet row: the picker opens on a tap (players who never use the week don't pay for its space)
      root.innerHTML = `<section class="today today-ask is-folded" aria-labelledby="today-h">
        <h2 class="sr-only" id="today-h">${esc(t("today.ask"))}</h2>
        <div class="card today-card today-mini today-mark">
          <div class="today-head" data-today-head>
            <p class="today-line"><b>${esc(t("today.mark"))}</b></p>
            ${foldBtn(false, t("today.title"))}
          </div>
          <div id="today-body" hidden></div>
        </div>
      </section>`;
      return;
    }
    if (!d) {
      root.innerHTML = `<section class="today today-ask" aria-labelledby="today-h">
        <div class="fold-head" data-today-head><h2 class="h2" id="today-h">${esc(t("today.ask"))}</h2>${foldBtn(!shut, t("today.title"))}</div>
        ${shut ? `<div id="today-body" hidden></div>` : `<div id="today-body">
        <p class="hint">${esc(t("today.askHint"))}</p>
        <div class="today-picks" role="group" aria-label="${esc(t("today.ask"))}">${w.days.map((x) =>
          `<div class="today-pick-cell" data-today-pick="${esc(x.id)}"><button type="button" class="today-pick" id="today-pick-${esc(x.id)}" data-today-pick="${esc(x.id)}" title="${esc(name(x.name))}" aria-label="${esc(t("today.pick", { name: name(x.name) }))}"${x.color ? ` style="--day:${esc(x.color)}"` : ""}>${DY().medal(x, 36)}</button><span class="today-pick-name" aria-hidden="true">${esc(name(x.sin || x.name))}</span></div>`).join("")}</div>
        ${a ? `<label class="today-num" for="today-num"><span>${esc(t("today.orNumber"))}</span>
          <input type="number" id="today-num" inputmode="numeric" min="1" max="99999" step="1" placeholder="${esc(t("days.numberPh"))}" value="${state.dayNumber != null ? state.dayNumber : ""}"></label>` : ""}
        </div>`}
      </section>`;
      return;
    }
    const dayStyle = d.color ? ` style="--day:${esc(d.color)}"` : "";
    if (shut) {
      // one compact row: medallion, "Hoje: X" over "N coisas · dia N", Avançar, toggle (the heading stays for screen readers)
      root.innerHTML = `<section class="today is-folded" aria-labelledby="today-h">
        <h2 class="sr-only" id="today-h">${esc(t("today.title"))}</h2>
        <div class="card today-card today-mini"${dayStyle}>
          <div class="today-head" data-today-head>
            ${DY().tile(d, 26)}
            <p class="today-line"><b>${esc(t("today.line", { name: name(d.name) }))}</b><span class="today-sub"><span class="sr-only"> · </span><span class="today-nw">${esc(countText(state, d))}</span>${state.dayNumber != null ? ` · <span class="tabnum today-nw">${esc(t("days.counter", { n: state.dayNumber }))}</span>` : ""}</span></p>
            <button type="button" class="btn btn-sm today-adv-sm" id="today-adv" data-today-adv aria-label="${esc(t("days.advance"))}" title="${esc(t("days.advance"))}">${esc(t("today.advShort"))} ›</button>
            ${foldBtn(false, t("today.title"))}
          </div>
          <div id="today-body" hidden></div>
        </div>
      </section>`;
      return;
    }
    const done = ticked(state, d), all = d.events.length > 0 && done.length === d.events.length;
    const typed = notes ? notes.keep() : () => {};
    root.innerHTML = `<section class="today" aria-labelledby="today-h">
      <div class="fold-head" data-today-head><h2 class="h2 today-h" id="today-h"${dayStyle}><span class="sr-only">${esc(t("today.title"))}: </span>${DY().tile(d, 26)}<span class="today-h-t">${esc(name(d.name))} <span class="count tabnum">${state.dayNumber != null ? `${esc(t("days.counter", { n: state.dayNumber }))} · ` : ""}<span id="today-count">${esc(countText(state, d))}</span></span></span></h2>${foldBtn(true, t("today.title"))}</div>
      <div class="card today-card" id="today-body"${dayStyle}>
        ${d.events.length ? `<ul class="today-evs">${d.events.map((ev, i) => evRow(ev, i, done.indexOf(i) >= 0)).join("")}</ul>` : `<p class="hint today-none">${esc(t("today.nothing"))}</p>`}
        ${all ? `<p class="today-all" role="status">${esc(t("today.allDone"))}</p>` : ""}
        <div class="today-note-box">${notes ? notes.html(d, state) : ""}</div>
        ${tomorrow(nx, state)}
        <div class="today-ctl">
          <button type="button" class="btn" id="today-adv" data-today-adv>${esc(t("days.advance"))} ›</button>
          <button type="button" class="btn btn-ghost" id="today-week" data-today-week>${esc(t("today.week"))}</button>
        </div>
      </div>
    </section>`;
    typed();
  }
  return { mount, render };
})();

GK.app.registerPanel(GK.ui.today, { id: "today", slot: "planner-top", order: 5 });
