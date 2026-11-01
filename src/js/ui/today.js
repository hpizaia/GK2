/* GK.ui.today: planner slot panel "Hoje" (above "Tecnologias que faltam"). With the current weekday set
   (GK.store day), open: the heading "Dia da Ira · dia 61 · 5 coisas" with the day's medallion (screen readers hear "Hoje:"
   first) and, beside the count,
   a small ✎ button "Bilhete deste dia" that opens that weekday's note field (GK.store dayNotes, synced; edited in
   place through GK.ui.days.noteBox). Then that day's events, ONE line each: the short part of the sentence
   (shortText: the event's hand-written `short` title, else the title before ": ", else the whole sentence; ellipsis
   when it does not fit), the kind icon and, for a
   medium/low-confidence event, a small "?" mark (title and screen-reader text "não confirmado"). A tap on the line
   (outside the tick) opens it in place: the whole sentence, "Não confirmado" in words when it applies, with whom,
   the longer detail, the items and the official game text (GK.ui.days.eventMore, as in the Dias card); a second tap
   closes it. Only events with `task` (data/days.json: something to do or buy) carry the 44 px "feito hoje" checkbox
   (GK.store dayDone, synced; the ticks reset by themselves when the day changes: advance, another day picked, or a
   counter that lands on another day); "Tudo feito hoje ✓" once every task is ticked. A written note shows as one
   line under the events (a tap edits it); with no note only the ✎ button is there. Then "Avançar dia" and
   "Ver semana" (→ #days); tomorrow is in "Ver semana" and the Dias tab. "Avançar dia" here shows no toast: the
   panel's own line already shows the new day (the Dias screen keeps its toast).
   Without a day: "Qual dia é hoje no jogo?" and the 6 day medallions as buttons (tap = set),
   plus the HUD counter field once calibrated (GK.store dayAnchor: the number alone gives the day).
   Nothing when the page has no week data. Re-renders only when (day, dayNumber, calibration, collapsed, lang,
   ticks, today's note, note editing, opened rows) change.
   Collapsible (GK.store ui.todayCollapsed, per device; folded by default): the toggle at the header's
   right or a tap on the header text; collapsed = one compact row "Hoje: Dia da Ira" over "3 coisas · dia 61" (or
   "2/3 feitas" once a task is ticked: counted over the tasks) with the medallion, "Avançar dia" and the toggle, or,
   with no day set, the row "Marcar o dia do jogo". The day picker shows each day's sin name under its medallion (the
   medallion art comes from GK.ui.days.medal); picking a day folds the panel back to its one-line row.
   Owns: its <div data-panel="today"> in [data-slot="planner-top"]. Uses the week helpers of GK.ui.days.
   Exposes: GK.ui.today.{mount, render, shortText}. Registered via GK.app.registerPanel(..., {slot: "planner-top", order: 5}).
*/
GK.ui.today = (function () {
  const { t, name } = GK.i18n, { esc } = GK.util;
  const DY = () => GK.ui.days;
  let root = null, memo = "", notes = null;
  let opened = new Set(), openedDay = null;   // event rows opened by a tap (forgotten when the day changes)
  const collapsed = (state) => !!(state.ui && state.ui.todayCollapsed);
  // the 44 px fold toggle; same id in both states so the focus stays on it. Open (a section heading): the thin
  // chevron with no box of the planner's sections (.sec-fold); folded (the one-line card): the boxed
  // .fold-btn of the station cards, inside its card
  const foldBtn = (open, label, sec) => GK.ui.fmt.foldBtn('id="today-tgl" data-today-tgl', open, label, "today-body", sec);
  // the events that carry a "feito hoje" tick (data/days.json `task`: something to do or buy)
  const tasks = (d) => d.events.filter((ev) => ev.task !== false).length;
  // ticked event indexes of today that still exist in the data and are tasks
  const ticked = (state, d) => GK.store.doneToday(state).filter((i) => i < d.events.length && d.events[i].task !== false);
  // "3 coisas", or "2/3 feitas" (over the tasks) once something is ticked
  const countText = (state, d) => {
    const n = ticked(state, d).length, k = tasks(d);
    return n ? t("today.doneN", { done: n, n: k }) + (n === k ? " ✓" : "") : t("days.count", { n: d.events.length });
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
      if (tg || (e.target.closest("[data-today-head]") && !e.target.closest(GK.ui.fmt.CONTROLS))) {
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
      const ev = e.target.closest("[data-today-ev]");
      if (ev) {
        const i = +ev.dataset.todayEv;
        if (opened.has(i)) opened.delete(i); else opened.add(i);
        rerender();
        return;
      }
      const w = e.target.closest("[data-today-week]");
      if (w) { DY().open(GK.store.get().day); return; }
      if (GK.ui.recipes) GK.ui.fmt.recipeClick(e, "plan");
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
  // the one-line text: the event's hand-written `short` title (data/days.json, ≤ 40 letters) when it has one, else
  // "Linda (Clube do Cais) recebe Pergaminhos Verdes: mais moradores…" → the title before ": "; a sentence with no
  // title stays whole (without its final period) and is cut with an ellipsis by the CSS
  function shortText(ev) {
    if (ev.short) return name(ev.short);
    const text = DY().eventText(ev), i = text.indexOf(": ");
    return (i > 0 ? text.slice(0, i) : text).replace(/\.$/, "");
  }
  function evRow(ev, i, done, open, state) {
    const text = DY().eventText(ev), short = shortText(ev), kind = t("days.kind." + ev.kind);
    const unsure = ev.confidence === "medium" || ev.confidence === "low";
    const tip = unsure ? [t("days.conf." + ev.confidence), ev.source ? t("days.source", { src: ev.source }) : ""].filter(Boolean).join(" · ") : "";
    return `<li class="today-ev${done ? " is-done" : ""}${open ? " is-open" : ""}${ev.task ? "" : " is-info"}">
      ${ev.task ? `<label class="tick today-tick"><input type="checkbox" id="today-done-${i}" data-today-done="${i}"${done ? " checked" : ""} aria-label="${esc(t("today.check", { text }))}"></label>` : `<span class="today-tick-x" aria-hidden="true"></span>`}
      <button type="button" class="today-ev-btn" id="today-ev-${i}" data-today-ev="${i}" aria-expanded="${open}" aria-controls="today-more-${i}">
        <span class="today-ev-ico" title="${esc(kind)}">${DY().kindIcon(ev.kind, 16)}<span class="sr-only">${esc(kind)}: </span></span>
        <span class="today-ev-t">${esc(short)}</span>
        ${unsure ? `<span class="today-unsure" title="${esc(t("days.unconfirmed") + " · " + tip)}"><span aria-hidden="true">?</span><span class="sr-only"> · ${esc(t("days.unconfirmed"))}</span></span>` : ""}
        <span class="today-ev-chev" aria-hidden="true"></span>
      </button>
      <div class="today-more" id="today-more-${i}"${open ? "" : " hidden"}>
        <span class="today-more-text">${esc(text)}</span>
        ${unsure ? `<span class="today-more-unsure">${esc(t("today.unsure"))} · ${esc(tip)}</span>` : ""}
        ${open ? DY().eventMore(ev, state, true) : ""}
      </div>
    </li>`;
  }
  // the note: the ✎ button beside the count (opens the field), the note's own line under the events once written
  function noteBtn(d, state) {
    const has = !!(state.dayNotes || {})[d.id];
    return `<button type="button" class="today-note-btn${has ? " has-note" : ""}" id="today-note-edit" data-note-edit="${esc(d.id)}" aria-label="${esc(t("today.note"))}" title="${esc(t("today.note"))}"><span aria-hidden="true">✎</span></button>`;
  }
  function noteBody(d, state) {
    if (notes && notes.editing() === d.id) return `<div class="today-note-box">${notes.html(d, state)}</div>`;
    const txt = (state.dayNotes || {})[d.id] || "";
    return txt ? `<button type="button" class="today-note-line" data-note-edit="${esc(d.id)}"><span class="today-note-ic" aria-hidden="true">✎</span><span class="today-note-txt"><span class="sr-only">${esc(t("days.note.label"))}: </span>${esc(txt)}</span></button>` : "";
  }
  function render(state) {
    if (!root) return;
    const w = DY() && DY().week();
    const d = w ? DY().current(state) : null;
    const a = state.dayAnchor;
    const shut = collapsed(state);
    if (!d || d.id !== openedDay) { opened = new Set(); openedDay = d ? d.id : null; }
    const sig = !w ? "none" : [d ? d.id : "", state.dayNumber, a ? a.number + a.day : "", shut, GK.i18n.lang(),
      d ? ticked(state, d).join(",") : "", d && notes ? notes.sig(d.id) : "", [...opened].join(","),
      JSON.stringify(state.overrides && state.overrides[GK.i18n.lang()] || {})].join("|");
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
        <div class="fold-head" data-today-head><h2 class="h2" id="today-h">${esc(t("today.ask"))}</h2>${foldBtn(!shut, t("today.title"), true)}</div>
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
    const done = ticked(state, d), all = tasks(d) > 0 && done.length === tasks(d);
    const typed = notes ? notes.keep() : () => {};
    root.innerHTML = `<section class="today" aria-labelledby="today-h">
      <div class="fold-head" data-today-head><h2 class="h2 today-h" id="today-h"${dayStyle}><span class="sr-only">${esc(t("today.title"))}: </span>${DY().tile(d, 26)}<span class="today-h-t">${esc(name(d.name))} <span class="count tabnum">${state.dayNumber != null ? `${esc(t("days.counter", { n: state.dayNumber }))} · ` : ""}<span id="today-count">${esc(countText(state, d))}</span></span></span></h2>${noteBtn(d, state)}<span class="today-rule" aria-hidden="true"></span>${foldBtn(true, t("today.title"), true)}</div>
      <div class="card today-card" id="today-body"${dayStyle}>
        ${d.events.length ? `<ul class="today-evs">${d.events.map((ev, i) => evRow(ev, i, done.indexOf(i) >= 0, opened.has(i), state)).join("")}</ul>` : `<p class="hint today-none">${esc(t("today.nothing"))}</p>`}
        ${all ? `<p class="today-all" role="status">${esc(t("today.allDone"))}</p>` : ""}
        ${noteBody(d, state)}
        <div class="today-ctl">
          <button type="button" class="btn" id="today-adv" data-today-adv>${esc(t("days.advance"))} ›</button>
          <button type="button" class="btn btn-ghost" id="today-week" data-today-week>${esc(t("today.week"))}</button>
        </div>
      </div>
    </section>`;
    typed();
  }
  return { mount, render, shortText };
})();

GK.app.registerPanel(GK.ui.today, { id: "today", slot: "planner-top", order: 5 });
