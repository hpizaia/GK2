/* GK.ui.search: search box and results dropdown (debounced; only the dropdown re-renders while typing).
   ARIA combobox (APG "list autocomplete"): focus stays in the input, ↓/↑ move the active option
   (aria-activedescendant), Enter adds it (or the first one), Esc clears; the count is announced politely.
   Placeholder = the purpose ("Buscar item para fabricar…"), not the item count (1.3.4).
   Owns: [data-panel="search"]. Exposes: GK.ui.search.{mount, render, add}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "search.label": "Buscar item para fabricar",
    "search.placeholder": "Buscar item para fabricar…",
    "search.clear": "Limpar busca",
    "search.none": "Nada encontrado para “{q}”. Tente outro nome, em português ou inglês.",
    "search.noneHidden": "Nada visível para “{q}”, mas há itens ocultos que combinam.",
    "search.count.one": "{n} resultado",
    "search.count.other": "{n} resultados",
    "search.raw": "Matéria-prima",
    "search.recipes": "{station} · {n} receitas",
    "search.inList": "na lista: {n}",
    "search.add": "+ Adicionar",
    "search.hiddenShow": "Mostrar itens ocultos",
    "search.hiddenMore.one": "Mostrar itens ocultos (+{n})",
    "search.hiddenMore.other": "Mostrar itens ocultos (+{n})",
    "search.hiddenTag": "oculto",
    "search.hiddenTitle": "Oculto na wiki, sem fonte no jogo atual, ou não é um item",
    "toast.added": "Adicionado às metas: {name}",
    "toast.bumped": "{name}: agora {n}",
  },
  en: {
    "search.label": "Search for an item to craft",
    "search.placeholder": "Search for an item to craft…",
    "search.clear": "Clear search",
    "search.none": "Nothing found for “{q}”. Try another name, in English or Portuguese.",
    "search.noneHidden": "Nothing visible for “{q}”, but some hidden items match.",
    "search.count.one": "{n} result",
    "search.count.other": "{n} results",
    "search.raw": "Raw material",
    "search.recipes": "{station} · {n} recipes",
    "search.inList": "in list: {n}",
    "search.add": "+ Add",
    "search.hiddenShow": "Show hidden items",
    "search.hiddenMore.one": "Show hidden items (+{n})",
    "search.hiddenMore.other": "Show hidden items (+{n})",
    "search.hiddenTag": "hidden",
    "search.hiddenTitle": "Hidden on the wiki, unobtainable in the current game, or not an item",
    "toast.added": "Added to goals: {name}",
    "toast.bumped": "{name}: now {n}",
  },
});

GK.ui.search = (function () {
  const { t, name } = GK.i18n, { esc, slot } = GK.util;
  let root, input, pop, list, meta, status, clearBtn;
  let active = -1;   // index of the highlighted option (aria-activedescendant), -1 = none
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
    if (!q.trim()) { list.innerHTML = ""; meta.innerHTML = ""; status.textContent = ""; setOpen(false); return; }
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
      return `<li class="result" role="option" id="q-opt-${k}" aria-selected="false" data-add="${esc(r.id)}">
        ${slot(it, nm)}
        <span><span class="result-name">${esc(nm)}${GK.ui.fmt.badges(it, st.overrides)}${hid}</span><span class="result-sub">${esc(GK.ui.fmt.stationOf(r.id, st))}${g ? " · " + esc(t("search.inList", { n: g.qty })) : ""}</span></span>
        <span class="result-add" aria-hidden="true">${esc(t("search.add"))}</span>
      </li>`;
    }).join("");
    status.textContent = t("search.count", { n: results.length });
    setOpen(true);
    setActive(-1);
  }
  const renderSoon = GK.util.debounce(renderResults, 70);
  function add(id) {
    const before = GK.store.get().goals.find((g) => g.item === id);
    const n = GK.store.actions.addGoal(id, 1);
    const nm = name(GK.data.item(id), GK.store.get().overrides);
    GK.ui.toast(before ? t("toast.bumped", { name: nm, n }) : t("toast.added", { name: nm }));
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
    input.addEventListener("input", () => { clearBtn.hidden = !input.value; renderSoon(); });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        renderResults();
        const opts = options(), o = opts[active >= 0 ? active : 0];
        if (o) { e.preventDefault(); add(o.dataset.add); }
      } else if (e.key === "Escape") { if (input.value) { e.preventDefault(); input.value = ""; renderResults(); } else setOpen(false); }
      else if (e.key === "ArrowDown") {
        if (pop.hidden && input.value.trim()) renderResults();
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
    clearBtn.addEventListener("click", () => { input.value = ""; renderResults(); input.focus(); });
    // e.target may have been re-rendered away (detached) by the click itself: not an outside click
    document.addEventListener("click", (e) => { if (e.target.isConnected && !root.contains(e.target)) setOpen(false); });
    input.addEventListener("focus", () => { if (input.value.trim()) renderResults(); });
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
