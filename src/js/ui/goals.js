/* GK.ui.goals: the goal list with steppers (press and hold − / + to repeat), the empty state and "Limpar metas"
   (not "Limpar lista": too close to "Apagar lista").
   First use: one line above the example list, "Exemplo: busque o que quer fabricar e ele substitui esta lista."; an
   empty list shows only its empty card. The first goal added replaces the example (GK.store addGoal); its "Desfazer"
   toast lives in ui/search.js. The item icon opens it in Receitas.
   "− N +" sits on the name's line at the right, its right edge on the card's 12 px line (the column of the "× N ▾" of
   Matérias-primas and Etapas), at every width; the name wraps instead. No separate ✕: at quantity 1 the "−" is a red
   ✕ that removes the goal (same id, so the focus stays on it). Removing shows "Saiu das metas: Vinho · Desfazer"
   (GK.ui.fmt.undoToast): the goal comes back at its place with its quantity (GK.store restoreGoal). "Limpar metas"
   keeps its two-tap confirmation instead.
   Lists (schema 5, css/lists.css): with two or more lists, "Lista: <nome> ▾" under the title opens a menu (each list
   with its number of goals, "Nova lista…", "Renomear", "Apagar" and a one-line note); with one list only a discreet
   "+ Criar outra lista" at the end. Create / rename use a small form in the page, delete a confirmation in the page.
   Switching goes through GK.store.actions.switchList, so every panel re-renders from the new list.
   Owns: [data-panel="goals"]. Exposes: GK.ui.goals.{mount, render}; registered as a panel.
*/
GK.ui.goals = (function () {
  const { t, name } = GK.i18n, { esc, domId } = GK.util;
  const EXAMPLES = ["crate", "master-sword", "furnace-i", "wine", "lantern-i"];
  let root, confirming = false, confirmTimer = null;
  // lists: the menu is open / the form in the page ({mode: "new" | "rename" | "delete", id})
  let menuOpen = false, form = null;
  const listName = (l) => (l && l.name) || t("lists.default");
  const S = () => GK.store;
  function closeMenu(focusBtn) {
    if (!menuOpen) return;
    menuOpen = false; render(S().get());
    if (focusBtn) { const b = document.getElementById("list-btn"); if (b) b.focus(); }
  }
  function openForm(mode) {
    const st = S().get(), cur = S().activeList(st);
    menuOpen = false;
    if (mode === "new" && st.lists.length >= S().LISTS_MAX) { GK.ui.toast(t("lists.full", { n: S().LISTS_MAX })); render(st); return; }
    form = { mode, id: cur && cur.id };
    render(st);
    const f = document.getElementById(mode === "delete" ? "list-del-ok" : "list-name");
    if (f) { f.focus(); if (f.select) f.select(); }
  }
  function submitForm() {
    const inp = document.getElementById("list-name"), A = S().actions, st = S().get();
    if (!form || !inp) return;
    if (form.mode === "new") {
      const nm = inp.value.trim() || t("lists.newDefault", { n: st.lists.length + 1 });
      form = null;
      const id = A.createList(nm);
      if (id) GK.ui.toast(t("lists.created", { name: listName(S().activeList()) }));
      else render(st);
    } else if (form.mode === "rename") {
      const id = form.id;
      form = null;
      if (inp.value.trim()) A.renameList(id, inp.value); else render(st);
    }
    const b = document.getElementById("list-btn"); if (b) b.focus();
  }
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
  // the ✕ (quantity 1): the goal goes, a toast offers "Desfazer" (same place, same quantity; only on the same list)
  function removeWithUndo(item) {
    const st = S().get(), at = st.goals.findIndex((x) => x.item === item);
    if (at < 0) return;
    const goal = { item, qty: st.goals[at].qty }, listId = (S().activeList(st) || {}).id;
    const rest = JSON.stringify(st.goals.filter((x) => x.item !== item)), wasExample = !!st.example;
    const nm = name(GK.data.get().items[item], st.overrides);
    S().actions.removeGoal(item);
    GK.ui.fmt.undoToast(t("goals.removed", { name: nm }), () => {
      const now = S().get();
      if ((S().activeList(now) || {}).id !== listId) return;
      // the example comes back as the example only if nothing else changed in between
      S().actions.restoreGoal(goal, at, wasExample && JSON.stringify(now.goals) === rest);
      const b = document.getElementById("dec-" + domId(item)); if (b) b.focus({ preventScroll: true });
    });
  }
  function mount(el) {
    root = el;
    root.addEventListener("pointerdown", startHold);
    // the buttons are re-rendered on every step, so "leaving" is checked against what is under the pointer
    document.addEventListener("pointermove", (e) => { if (hold && !(e.target.closest && e.target.closest(hold.sel))) stopHold(); });
    document.addEventListener("pointerup", endHold);
    document.addEventListener("pointercancel", endHold);
    window.addEventListener("blur", endHold);
    root.addEventListener("contextmenu", (e) => { if (e.target.closest("[data-dec],[data-inc]")) e.preventDefault(); });
    root.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (menuOpen && !(b && (b.id === "list-btn" || b.closest("#list-menu")))) { closeMenu(false); if (!b) return; }
      if (!b) return;
      const A = GK.store.actions;
      if (b.id === "list-btn") { menuOpen = !menuOpen; form = null; render(GK.store.get()); return; }
      if (b.dataset.listPick) {
        const id = b.dataset.listPick;
        menuOpen = false; form = null; confirming = false;
        if (id !== GK.store.get().legacyOf) {
          A.switchList(id);
          GK.ui.toast(t("lists.switched", { name: listName(GK.store.activeList()) }));
        } else render(GK.store.get());
        const lb = document.getElementById("list-btn"); if (lb) lb.focus();
        return;
      }
      if (b.hasAttribute("data-list-new")) { openForm("new"); return; }
      if (b.hasAttribute("data-list-rename")) { openForm("rename"); return; }
      if (b.hasAttribute("data-list-delete")) { openForm("delete"); return; }
      if (b.hasAttribute("data-list-cancel")) { form = null; render(GK.store.get()); const lb = document.getElementById("list-btn"); if (lb) lb.focus(); return; }
      if (b.hasAttribute("data-list-del-ok")) {
        const l = form && GK.store.get().lists.find((x) => x.id === form.id), nm = listName(l);
        form = null;
        if (l && A.deleteList(l.id)) GK.ui.toast(t("lists.deleted", { name: nm }));
        else render(GK.store.get());
        // one list left: no "Lista: …" button, the focus goes to "+ Criar outra lista"
        const lb = document.getElementById("list-btn") || document.getElementById("list-more"); if (lb) lb.focus();
        return;
      }
      // a hold that ran "−" down to 1 must not remove the goal: the click that ends it can land on the ✕ now there
      if ((b.dataset.dec || b.dataset.inc || b.dataset.remove) && swallowClick) { swallowClick = false; return; }
      if (b.dataset.recipeOpen) { GK.ui.recipes.open(b.dataset.recipeOpen, { from: "plan" }); return; }
      if (b.dataset.dec) A.bumpQty(b.dataset.dec, -1);
      else if (b.dataset.inc) A.bumpQty(b.dataset.inc, +1);
      else if (b.dataset.remove) removeWithUndo(b.dataset.remove);
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
    root.addEventListener("submit", (e) => { if (e.target.id === "list-form") { e.preventDefault(); submitForm(); } });
    // a tap outside the panel closes the menu (the path, not contains(): the tapped button may be re-rendered away)
    document.addEventListener("click", (e) => { if (menuOpen && root && (e.composedPath ? e.composedPath() : [e.target]).indexOf(root) < 0) closeMenu(false); });
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      if (menuOpen) closeMenu(true);
      else if (form && root.contains(document.activeElement)) { form = null; render(GK.store.get()); const lb = document.getElementById("list-btn"); if (lb) lb.focus(); }
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
  // "Lista: Igreja ▾" + its menu (two or more lists)
  function picker(state) {
    const cur = S().activeList(state);
    let h = `<div class="list-pick"><button type="button" class="btn btn-sm list-btn" id="list-btn" aria-haspopup="menu" aria-expanded="${menuOpen}" aria-controls="list-menu" aria-label="${esc(t("lists.btn", { name: listName(cur) }))}"><span class="lbl">${esc(t("lists.label"))}</span> <span class="nm">${esc(listName(cur))}</span><span class="car" aria-hidden="true">▾</span></button>`;
    if (menuOpen) {
      h += `<div class="list-menu" id="list-menu" role="menu" aria-label="${esc(t("lists.menu"))}">` + state.lists.map((l) => {
        const on = l.id === cur.id, n = on ? state.goals.length : l.goals.length;
        return `<button type="button" class="list-opt" role="menuitemradio" aria-checked="${on}" id="list-opt-${domId(l.id)}" data-list-pick="${esc(l.id)}"><span class="ck" aria-hidden="true">${on ? "✓" : ""}</span><span class="on">${esc(listName(l))}</span><span class="n">${esc(t("lists.goals", { n }))}</span></button>`;
      }).join("") +
        `<button type="button" class="list-opt list-act" role="menuitem" id="list-new" data-list-new><span class="ck" aria-hidden="true">+</span><span class="on">${esc(t("lists.new"))}</span><span></span></button>` +
        `<button type="button" class="list-opt list-act" role="menuitem" id="list-rename" data-list-rename><span class="ck" aria-hidden="true">✎</span><span class="on">${esc(t("lists.rename", { name: listName(cur) }))}</span><span></span></button>` +
        `<button type="button" class="list-opt list-act list-act-del" role="menuitem" id="list-delete" data-list-delete><span class="ck" aria-hidden="true">✕</span><span class="on">${esc(t("lists.delete", { name: listName(cur) }))}</span><span></span></button>` +
        `<p class="list-menu-note">${esc(t("lists.note"))}</p></div>`;
    }
    return h + `</div>`;
  }
  // the form in the page: new list / rename / delete confirmation
  function listForm(state) {
    if (!form) return "";
    const l = state.lists.find((x) => x.id === form.id), cur = S().activeList(state);
    if (form.mode === "delete") {
      return `<div class="card list-form" role="group" aria-labelledby="list-del-q"><p class="list-q" id="list-del-q">${esc(t("lists.deleteAsk", { name: listName(l) }))}</p>
        <p class="hint">${esc(t("lists.deleteHint"))}</p>
        <div class="row-btns"><button type="button" class="btn btn-sm btn-confirm" id="list-del-ok" data-list-del-ok>${esc(t("lists.deleteOk"))}</button><button type="button" class="btn btn-sm btn-ghost" id="list-cancel" data-list-cancel>${esc(t("lists.cancel"))}</button></div></div>`;
    }
    const isNew = form.mode === "new", multi = state.lists.length > 1;
    const value = isNew ? t("lists.newDefault", { n: state.lists.length + 1 }) : (l && l.name) || listName(l);
    return `<form class="card list-form" id="list-form"><label for="list-name">${esc(t(isNew ? "lists.newName" : "lists.renameName"))}</label>
      <input id="list-name" type="text" maxlength="${S().LIST_NAME_MAX}" value="${esc(value)}" autocomplete="off" enterkeyhint="done">
      ${isNew ? `<p class="hint">${esc(multi ? t("lists.newHint") : t("lists.newHintFirst", { name: listName(cur) }))}</p>` : ""}
      <div class="row-btns"><button type="submit" class="btn btn-sm list-ok" id="list-ok">${esc(t(isNew ? "lists.create" : "lists.save"))}</button><button type="button" class="btn btn-sm btn-ghost" id="list-cancel" data-list-cancel>${esc(t("lists.cancel"))}</button></div></form>`;
  }
  function render(state, meta) {
    if (meta && (meta.from === "goals-input" || meta.from === "search-toggle")) return; // keep the caret in the field
    const D = GK.data.get();
    // the lists UI state follows the store (a list deleted on another device, the last but one deleted)
    const multi = state.lists.length > 1;
    if (!multi) menuOpen = false;
    if (form && form.mode !== "new" && !state.lists.some((l) => l.id === form.id)) form = null;
    if (form && form.mode === "delete" && !multi) form = null;
    // a re-render while the name is being typed keeps the text and the caret
    const inp = document.getElementById("list-name"), typing = inp && root.contains(inp) ? { v: inp.value, a: inp.selectionStart, b: inp.selectionEnd, f: document.activeElement === inp } : null;
    const top = multi ? picker(state) + listForm(state) : "";
    const bottom = multi ? "" : form ? listForm(state) : `<div class="list-more"><button type="button" class="btn btn-sm btn-ghost" id="list-more" data-list-new>${esc(t("lists.more"))}</button></div>`;
    paint(state, D, top, bottom);
    const inp2 = typing && document.getElementById("list-name");
    if (inp2) { inp2.value = typing.v; if (typing.f) { inp2.focus({ preventScroll: true }); try { inp2.setSelectionRange(typing.a, typing.b); } catch (e) { /* ignore */ } } }
  }
  function paint(state, D, top, bottom) {
    const head = `<div class="section-head"><h2 class="h2">${esc(t("goals.title"))} <span class="count">${state.goals.length || ""}</span></h2>
      ${state.goals.length ? `<button type="button" id="goals-clear" class="btn btn-sm ${confirming ? "btn-confirm" : "btn-ghost btn-danger"}" data-clear>${esc(t(confirming ? "goals.confirm" : "goals.clear"))}</button>` : ""}</div>`;
    if (!state.goals.length) {
      root.innerHTML = head + top + `<div class="card empty goal-list">
        <p class="empty-title">${esc(t("goals.empty.title"))}</p>
        <p>${esc(t("goals.empty.body"))}</p>
        <p>${esc(t("goals.try"))}</p>
        <div class="try">${EXAMPLES.filter((id) => D.items[id]).map((id) => `<button type="button" class="btn btn-sm" id="try-${domId(id)}" data-try="${esc(id)}">${esc(name(D.items[id], state.overrides))}</button>`).join("")}</div>
      </div>` + bottom;
      return;
    }
    const intro = state.example ? `<p class="goals-intro">${esc(t("goals.example"))}</p>` : "";
    root.innerHTML = head + top + intro + `<div class="card list goal-list">` + state.goals.map((g) => {
      const it = D.items[g.item], nm = name(it, state.overrides), id = domId(g.item);
      return `<div class="goal">
        ${GK.ui.fmt.slotButton(it, nm)}
        <div class="goal-main"><div class="goal-name">${esc(nm)}${GK.ui.fmt.otherName(it)}${GK.ui.fmt.badges(it, state.overrides)}</div><div class="goal-sub">${esc(GK.ui.fmt.stationOf(g.item, state))}</div></div>
        <div class="stepper">
          ${g.qty <= 1
            ? `<button type="button" class="st-rm" id="dec-${id}" data-remove="${esc(g.item)}" aria-label="${esc(t("goals.remove", { name: nm }))}">✕</button>`
            : `<button type="button" id="dec-${id}" data-dec="${esc(g.item)}" aria-label="${esc(t("goals.dec", { name: nm }))}">−</button>`}
          <input id="qty-${id}" data-qty="${esc(g.item)}" type="number" inputmode="numeric" min="1" max="999" value="${g.qty}" aria-label="${esc(t("goals.qty", { name: nm }))}">
          <button type="button" id="inc-${id}" data-inc="${esc(g.item)}" aria-label="${esc(t("goals.inc", { name: nm }))}">+</button>
        </div>
      </div>`;
    }).join("") + `</div>` + bottom;
  }
  return { mount, render };
})();

GK.app.registerPanel(GK.ui.goals, { id: "goals", panel: "goals", order: 30 });
