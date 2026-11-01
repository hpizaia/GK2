/* GK.ui.search: search box and results dropdown (debounced; only the dropdown re-renders while typing).
   ARIA combobox (APG "list autocomplete"): focus stays in the input, ↓/↑ move the active option
   (aria-activedescendant), Enter adds it (or the first one), Esc clears; the count is announced politely.
   Placeholder = the purpose ("Buscar item para fabricar…"), not the item count.
   "Recentes": focusing the box while it is empty opens the same popup with the last RECENT_SHOWN items added to goals
   (GK.store state.recents, newest first) that are not already goals of the open list, as options; typing replaces
   them with the results; tap / Enter adds (same action as a result). No recents to show = the popup stays closed.
   Right after an add the emptied box keeps the focus but the recents stay closed
   ("quiet"): they come back on the next tap on the box, an ↓, or when the focus leaves and comes back.
   Toasts: "+ Espada de Aço" for a new goal, "Espada de Aço: agora 4" for one already there. The first goal
   that replaces the example list (GK.store meta.exampleReplaced, from any screen: this module subscribes) gets ONE
   toast with "Desfazer" (GK.ui.fmt.undoToast): "+ Tábua reforçada · exemplo removido"; add() then skips
   its own, in the same "+ X" form as the plain toast (the data has no item gender, so no participle).
   A graded item (GK.data.itemGrade) reads "Suco de Uva" with "prata · …" below and the star on its icon; the
   one-line Recentes keep the full name ("Suco de Uva (prata)"): there is no line below for the word.
   The plain item of a graded family is the bronze one ("Abóbora": "bronze · …", the
   bronze star; in the Recentes "Abóbora (bronze)", GK.ui.fmt.gradedName); a family comes in one run, bronze first.
   Owns: [data-panel="search"]. Exposes: GK.ui.search.{mount, render, add}; registered as a panel.
*/
GK.ui.search = (function () {
  const { t, name } = GK.i18n, { esc, slot } = GK.util;
  let root, input, pop, list, meta, status, clearBtn;
  let active = -1;   // index of the highlighted option (aria-activedescendant), -1 = none
  let quiet = false;     // just added: the emptied box does not reopen the recents until the next tap / focus
  let replaced = false;  // set by the store subscription while addGoal runs: the first goal replaced the example
  const RECENT_SHOWN = 6;
  const options = () => [...list.querySelectorAll('[role="option"]')];
  function setOpen(open) {
    pop.hidden = !open;
    input.setAttribute("aria-expanded", open && options().length ? "true" : "false");
    if (!open) setActive(-1);
  }
  function setActive(i) {
    const opts = options();
    active = opts.length ? Math.max(-1, Math.min(i, opts.length - 1)) : -1;
    opts.forEach((o, k) => { o.classList.toggle("is-active", k === active); o.setAttribute("aria-selected", k === active ? "true" : "false"); });
    if (active >= 0) { input.setAttribute("aria-activedescendant", opts[active].id); opts[active].scrollIntoView({ block: "nearest" }); }
    else input.removeAttribute("aria-activedescendant");
  }
  function renderResults() {
    const q = input.value;
    clearBtn.hidden = !q;
    list.setAttribute("aria-labelledby", "q-label");
    if (!q.trim()) { if (!renderRecent()) { list.innerHTML = ""; meta.innerHTML = ""; status.textContent = ""; setOpen(false); } return; }
    const st = GK.store.get(), D = GK.data.get();
    const { results, hiddenCount } = GK.calc.search(q, D, { lang: GK.i18n.lang(), overrides: st.overrides, showHidden: st.showHidden });
    const toggle = (st.showHidden || hiddenCount)
      ? `<button type="button" class="hidden-toggle" id="q-hidden" data-hidden-toggle aria-pressed="${st.showHidden}">${esc(st.showHidden ? t("search.hiddenShow") : t("search.hiddenMore", { n: hiddenCount }))}</button>` : "";
    if (!results.length) {
      const msg = t(hiddenCount ? "search.noneHidden" : "search.none", { q: q.trim() });
      meta.innerHTML = `<p class="results-empty">${esc(msg)}${toggle ? `<span class="results-empty-ctl">${toggle}</span>` : ""}</p>`;
      list.innerHTML = "";
      status.textContent = msg;
      setOpen(true);
      return;
    }
    meta.innerHTML = `<div class="results-meta"><span aria-hidden="true">${esc(t("search.count", { n: results.length }))}</span>${toggle}</div>`;
    list.innerHTML = results.map((r, k) => {
      const it = D.items[r.id], nm = name(it, st.overrides), g = st.goals.find((x) => x.item === r.id);
      const hid = r.hidden ? `<span class="badge badge-hidden" title="${esc(t("search.hiddenTitle"))}">${esc(t("search.hiddenTag"))}</span>` : "";
      // a graded item: the name without "(prata)", the grade word first on the line below (the star is on the icon)
      const gn = GK.ui.fmt.graded(it, nm), shown = gn.name, word = gn.grade ? gn.word + " · " : "";
      return `<li class="result" role="option" id="q-opt-${k}" aria-selected="false" data-add="${esc(r.id)}">
        ${slot(it, nm)}
        <span><span class="result-name">${esc(shown)}${GK.ui.fmt.otherName(it)}${GK.ui.fmt.badges(it, st.overrides)}${hid}</span><span class="result-sub">${esc(word)}${esc(GK.ui.fmt.stationOf(r.id, st))}${g ? " · " + esc(t("search.inList", { n: g.qty })) : ""}</span></span>
        <span class="result-add" aria-hidden="true">${esc(t("search.add"))}</span>
      </li>`;
    }).join("");
    status.textContent = t("search.count", { n: results.length });
    setOpen(true);
    setActive(-1);
  }
  // the empty box, focused: the recents as options (icon + name, one line). false = none to show
  function renderRecent() {
    if (quiet || document.activeElement !== input) return false;
    const st = GK.store.get(), inList = new Set(st.goals.map((g) => g.item));
    const ids = (st.recents || []).filter((id) => !!GK.data.item(id) && !inList.has(id)).slice(0, RECENT_SHOWN);
    if (!ids.length) return false;
    meta.innerHTML = `<div class="results-meta"><span id="q-recent-h">${esc(t("search.recent"))}</span></div>`;
    list.setAttribute("aria-labelledby", "q-recent-h");
    list.innerHTML = ids.map((id, k) => {
      const it = GK.data.item(id), nm = name(it, st.overrides);
      return `<li class="result result-recent" role="option" id="q-opt-${k}" aria-selected="false" data-add="${esc(id)}">
        ${slot(it, nm)}<span class="result-name">${esc(GK.ui.fmt.gradedName(it, nm))}${GK.ui.fmt.otherName(it)}</span><span class="result-add" aria-hidden="true">${esc(t("search.add"))}</span>
      </li>`;
    }).join("");
    status.textContent = "";
    setOpen(true);
    setActive(-1);
    return true;
  }
  const renderSoon = GK.util.debounce(renderResults, 70);
  function add(id) {
    const before = GK.store.get().goals.find((g) => g.item === id);
    replaced = false;
    const n = GK.store.actions.addGoal(id, 1);
    const nm = name(GK.data.item(id), GK.store.get().overrides);
    if (!replaced) GK.ui.toast(before ? t("toast.bumped", { name: nm, n }) : t("toast.added", { name: nm }));
    // the box empties and keeps the focus, but the recents stay closed until the next tap
    quiet = true;
    input.value = ""; renderResults(); input.focus();
  }
  function mount(el) {
    root = el;
    root.innerHTML = `<div class="search-box">
        <svg width="18" height="18" viewBox="0 0 9 9" aria-hidden="true" shape-rendering="crispEdges"><path fill="currentColor" d="M2 0h3v1H2zM1 1h1v1H1zM5 1h1v1H5zM0 2h1v3H0zM6 2h1v3H6zM1 5h1v1H1zM5 5h1v1H5zM2 6h3v1H2zM6 6h1v1H6zM7 7h1v1H7zM8 8h1v1H8z"/></svg>
        <label class="sr-only" for="q" id="q-label"></label>
        <input id="q" class="search-input" type="search" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="q-results" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search">
        <button type="button" class="search-clear" id="q-clear" hidden>×</button>
      </div>
      <div class="results" id="q-pop" hidden><div id="q-meta"></div><ul class="results-list" id="q-results" role="listbox" aria-labelledby="q-label"></ul></div>
      <span class="sr-only" id="q-status" role="status" aria-live="polite"></span>`;
    input = root.querySelector("#q"); pop = root.querySelector("#q-pop"); list = root.querySelector("#q-results");
    meta = root.querySelector("#q-meta"); status = root.querySelector("#q-status"); clearBtn = root.querySelector("#q-clear");
    input.addEventListener("input", () => { quiet = false; clearBtn.hidden = !input.value; renderSoon(); });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        if (!input.value.trim()) {                     // the recents: Enter adds only the one picked with ↓/↑
          const o = !pop.hidden && active >= 0 && options()[active];
          if (o) { e.preventDefault(); add(o.dataset.add); }
          return;
        }
        renderResults();
        const opts = options(), o = opts[active >= 0 ? active : 0];
        if (o) { e.preventDefault(); add(o.dataset.add); }
      } else if (e.key === "Escape") { if (input.value) { e.preventDefault(); input.value = ""; renderResults(); } else setOpen(false); }
      else if (e.key === "ArrowDown") {
        if (pop.hidden) { quiet = false; renderResults(); }
        if (options().length) { e.preventDefault(); setActive(active + 1); }
      } else if (e.key === "ArrowUp") {
        if (options().length) { e.preventDefault(); setActive(active <= 0 ? -1 : active - 1); }
      } else if (e.key === "Home" && active >= 0) { e.preventDefault(); setActive(0); }
      else if (e.key === "End" && active >= 0) { e.preventDefault(); setActive(options().length - 1); }
    });
    // keep the focus in the input when an option is pressed (mouse / touch)
    list.addEventListener("mousedown", (e) => { if (e.target.closest('[role="option"]')) e.preventDefault(); });
    list.addEventListener("click", (e) => { const o = e.target.closest("[data-add]"); if (o) add(o.dataset.add); });
    meta.addEventListener("click", (e) => { if (e.target.closest("[data-hidden-toggle]")) GK.store.actions.setShowHidden(!GK.store.get().showHidden); });
    clearBtn.addEventListener("click", () => { quiet = false; input.value = ""; input.focus(); renderResults(); });
    // e.target may have been re-rendered away (detached) by the click itself: not an outside click
    document.addEventListener("click", (e) => { if (e.target.isConnected && !root.contains(e.target)) setOpen(false); });
    input.addEventListener("focus", () => renderResults());
    input.addEventListener("blur", () => { quiet = false; });
    // a tap on the box after Esc (or an add) closed the popup brings it back (results, or the recents when empty)
    input.addEventListener("click", () => { quiet = false; if (pop.hidden) renderResults(); });
    // the first goal replaced the example list (here, in Receitas, anywhere): one toast, with "Desfazer"
    GK.store.subscribe((st, m) => {
      const snap = m && m.exampleReplaced;
      if (!snap) return;
      replaced = true;
      const g = st.goals[st.goals.length - 1], it = g && GK.data.item(g.item);
      if (!it) return;
      const nm = name(it, st.overrides);
      GK.ui.fmt.undoToast(t("toast.replaced", { name: nm }), () => GK.store.actions.restoreExample(snap));
    });
  }
  function render(state, meta2) {
    input.placeholder = t("search.placeholder");
    root.querySelector("#q-label").textContent = t("search.label");
    clearBtn.setAttribute("aria-label", t("search.clear"));
    if (!pop.hidden || (meta2 && meta2.from === "search-toggle")) renderResults();
  }
  return { mount, render, add };
})();

GK.app.registerPanel(GK.ui.search, { id: "search", panel: "search", order: 20 });
