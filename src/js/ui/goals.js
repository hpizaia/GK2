/* GK.ui.goals: the goal list with steppers (press and hold − / + to repeat), the empty state and "Limpar lista".
   First use (1.3.4): one line saying what the app does above the list while it is empty or the example; the first
   goal added replaces the example (GK.store addGoal) and this module shows "Exemplo removido · Desfazer"
   (GK.ui.fmt.undoToast → GK.store.actions.restoreExample). Phones (< 480 px of list width): the stepper and ✕ go on
   a second line under the name (planner.css, container query on .goal-list).
   Owns: [data-panel="goals"]. Exposes: GK.ui.goals.{mount, render}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "goals.title": "Metas",
    "goals.clear": "Limpar lista",
    "goals.confirm": "Confirmar limpeza",
    "goals.intro": "Diga o que quer fabricar; o app soma tudo o que você precisa juntar.",
    "goals.example": "Lista de exemplo: a primeira meta que você buscar substitui estas.",
    "goals.exampleGone": "Exemplo removido",
    "goals.empty.title": "Nada planejado ainda",
    "goals.empty.body": "Busque acima, em português ou inglês, e toque no item para adicioná-lo.",
    "goals.try": "Experimente:",
    "goals.dec": "Diminuir quantidade de {name}",
    "goals.inc": "Aumentar quantidade de {name}",
    "goals.qty": "Quantidade de {name}",
    "goals.remove": "Remover {name}",
  },
  en: {
    "goals.title": "Goals",
    "goals.clear": "Clear list",
    "goals.confirm": "Confirm clear",
    "goals.intro": "Say what you want to craft; the app adds up everything you need to gather.",
    "goals.example": "Example list: the first goal you search for replaces these.",
    "goals.exampleGone": "Example removed",
    "goals.empty.title": "Nothing planned yet",
    "goals.empty.body": "Search above, in English or Portuguese, and tap an item to add it.",
    "goals.try": "Try:",
    "goals.dec": "Decrease amount of {name}",
    "goals.inc": "Increase amount of {name}",
    "goals.qty": "Amount of {name}",
    "goals.remove": "Remove {name}",
  },
});

GK.ui.goals = (function () {
  const { t, name } = GK.i18n, { esc, slot, domId } = GK.util;
  const EXAMPLES = ["crate", "master-sword", "furnace-i", "wine", "lantern-i"];
  let root, confirming = false, confirmTimer = null;
  // press and hold − / +: a tap is one step (the click); held, it repeats after 400 ms, every 80 ms, and stops on
  // release, cancel (a scroll) or when the pointer leaves the button
  const HOLD_DELAY = 400, HOLD_EVERY = 80;
  let hold = null;          // { item, d, sel, t1, t2 }
  let swallowClick = false; // the click that ends a repeating hold was already counted
  function stopHold() {
    if (!hold) return;
    clearTimeout(hold.t1); clearInterval(hold.t2);
    hold = null;
  }
  function bump(item, d) {
    const g = GK.store.get().goals.find((x) => x.item === item);
    if (!g || (d < 0 && g.qty <= 1) || (d > 0 && g.qty >= 999)) { stopHold(); return; }
    GK.store.actions.bumpQty(item, d);
  }
  function startHold(e) {
    const b = e.target.closest("[data-dec],[data-inc]");
    if (!b || (e.button != null && e.button !== 0)) return;
    stopHold();
    const item = b.dataset.dec || b.dataset.inc, d = b.dataset.dec ? -1 : +1;
    const q = window.CSS && CSS.escape ? CSS.escape(item) : item;
    hold = { item, d, sel: `[data-${d < 0 ? "dec" : "inc"}="${q}"]` };
    hold.t1 = setTimeout(() => {
      if (!hold) return;
      swallowClick = true;
      bump(hold.item, hold.d);
      if (hold) hold.t2 = setInterval(() => { if (hold) bump(hold.item, hold.d); }, HOLD_EVERY);
    }, HOLD_DELAY);
  }
  function endHold() { stopHold(); setTimeout(() => { swallowClick = false; }, 0); }
  function mount(el) {
    root = el;
    // the first goal replaced the example list: offer it back
    GK.store.subscribe((st, meta) => {
      const snap = meta && meta.exampleReplaced;
      if (snap) GK.ui.fmt.undoToast(t("goals.exampleGone"), () => GK.store.actions.restoreExample(snap));
    });
    root.addEventListener("pointerdown", startHold);
    // the buttons are re-rendered on every step, so "leaving" is checked against what is under the pointer
    document.addEventListener("pointermove", (e) => { if (hold && !(e.target.closest && e.target.closest(hold.sel))) stopHold(); });
    document.addEventListener("pointerup", endHold);
    document.addEventListener("pointercancel", endHold);
    window.addEventListener("blur", endHold);
    root.addEventListener("contextmenu", (e) => { if (e.target.closest("[data-dec],[data-inc]")) e.preventDefault(); });
    root.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      const A = GK.store.actions;
      if ((b.dataset.dec || b.dataset.inc) && swallowClick) { swallowClick = false; return; }
      if (b.dataset.recipeOpen) { GK.ui.recipes.open(b.dataset.recipeOpen, { from: "plan" }); return; }
      if (b.dataset.dec) A.bumpQty(b.dataset.dec, -1);
      else if (b.dataset.inc) A.bumpQty(b.dataset.inc, +1);
      else if (b.dataset.remove) A.removeGoal(b.dataset.remove);
      else if (b.dataset.try) GK.ui.search.add(b.dataset.try);
      else if (b.hasAttribute("data-clear")) {
        if (!confirming) {
          confirming = true; render(GK.store.get());
          const c = document.getElementById("goals-clear"); if (c) c.focus();
          clearTimeout(confirmTimer);
          confirmTimer = setTimeout(() => { confirming = false; render(GK.store.get()); }, 3500);
        } else { confirming = false; clearTimeout(confirmTimer); A.clearGoals(); }
      }
    });
    root.addEventListener("input", (e) => {
      const i = e.target.closest("[data-qty]");
      if (i && i.value !== "") GK.store.actions.setQty(i.dataset.qty, i.value, { from: "goals-input" });
    });
    root.addEventListener("change", (e) => {
      const i = e.target.closest("[data-qty]");
      if (i) GK.store.actions.setQty(i.dataset.qty, i.value);
    });
  }
  function render(state, meta) {
    if (meta && (meta.from === "goals-input" || meta.from === "search-toggle")) return; // keep the caret in the field
    const D = GK.data.get();
    const head = `<div class="section-head"><h2 class="h2">${esc(t("goals.title"))} <span class="count">${state.goals.length || ""}</span></h2>
      ${state.goals.length ? `<button type="button" id="goals-clear" class="btn btn-sm ${confirming ? "btn-confirm" : "btn-ghost btn-danger"}" data-clear>${esc(t(confirming ? "goals.confirm" : "goals.clear"))}</button>` : ""}</div>`;
    const intro = !state.goals.length || state.example ? `<p class="goals-intro">${esc(t("goals.intro"))}</p>` : "";
    if (!state.goals.length) {
      root.innerHTML = head + intro + `<div class="card empty goal-list">
        <p class="empty-title">${esc(t("goals.empty.title"))}</p>
        <p>${esc(t("goals.empty.body"))}</p>
        <p>${esc(t("goals.try"))}</p>
        <div class="try">${EXAMPLES.filter((id) => D.items[id]).map((id) => `<button type="button" class="btn btn-sm" id="try-${domId(id)}" data-try="${esc(id)}">${esc(name(D.items[id], state.overrides))}</button>`).join("")}</div>
      </div>`;
      return;
    }
    root.innerHTML = head + intro + `<div class="card list goal-list">` + state.goals.map((g) => {
      const it = D.items[g.item], nm = name(it, state.overrides), id = domId(g.item);
      return `<div class="goal">
        ${slot(it, nm)}
        <div class="goal-main"><div class="goal-name">${esc(nm)}${GK.ui.fmt.infoButton(g.item, nm)}${GK.ui.fmt.badges(it, state.overrides)}</div><div class="goal-sub">${esc(GK.ui.fmt.stationOf(g.item, state))}</div></div>
        <div class="goal-ctl">
          <div class="stepper">
            <button type="button" id="dec-${id}" data-dec="${esc(g.item)}" aria-label="${esc(t("goals.dec", { name: nm }))}">−</button>
            <input id="qty-${id}" data-qty="${esc(g.item)}" type="number" inputmode="numeric" min="1" max="999" value="${g.qty}" aria-label="${esc(t("goals.qty", { name: nm }))}">
            <button type="button" id="inc-${id}" data-inc="${esc(g.item)}" aria-label="${esc(t("goals.inc", { name: nm }))}">+</button>
          </div>
          <button type="button" class="btn btn-ghost btn-danger" id="rm-${id}" data-remove="${esc(g.item)}" aria-label="${esc(t("goals.remove", { name: nm }))}">✕</button>
        </div>
      </div>`;
    }).join("") + `</div>` + (state.example ? `<p class="example-note">${esc(t("goals.example"))}</p>` : "");
  }
  return { mount, render };
})();

GK.app.registerPanel(GK.ui.goals, { id: "goals", panel: "goals", order: 30 });
