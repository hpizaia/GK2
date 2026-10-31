/* GK.ui.header: brand, tab bar (rendered from the GK.router registry), theme and language switches.
   Owns: the [data-slot] elements of <header class="top"> and the mobile tab band (#tabs-band), and where the
   planner search row ([data-panel="search"], content by ui/search.js) sits: phones (< 900 px) keep it after the
   sticky tab band, so it scrolls with the page while the tabs stay; from 900 px it is moved into the sticky header
   (the desktop layout). Tapping the tab of the screen already shown scrolls back to the top.
   Exposes: GK.ui.header.{mount, render}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "app.title": "Companheiro <b>GK2</b>",
    "app.titlePlain": "Companheiro GK2",
    "app.tagline": "planejador de crafting",
    "lang.label": "Idioma",
    "lang.switch": "Mudar idioma para {name}",
    "theme.label": "Tema",
    "theme.auto": "Auto",
    "theme.light": "Claro",
    "theme.dark": "Escuro",
    "theme.autoTitle": "Auto: segue o tema do sistema",
    "theme.lightTitle": "Tema claro (pergaminho)",
    "theme.darkTitle": "Tema escuro (noite)",
    "theme.cycle": "Tema: {mode}. Tocar para mudar para {next}",
    "tabs.label": "Telas",
    "tab.soon": "em breve",
  },
  en: {
    "app.title": "GK2 <b>Companion</b>",
    "app.titlePlain": "GK2 Companion",
    "app.tagline": "crafting planner",
    "lang.label": "Language",
    "lang.switch": "Switch language to {name}",
    "theme.label": "Theme",
    "theme.auto": "Auto",
    "theme.light": "Light",
    "theme.dark": "Dark",
    "theme.autoTitle": "Auto: follows the system theme",
    "theme.lightTitle": "Light theme (parchment)",
    "theme.darkTitle": "Dark theme (night)",
    "theme.cycle": "Theme: {mode}. Tap to switch to {next}",
    "tabs.label": "Screens",
    "tab.soon": "soon",
  },
});

GK.ui.header = (function () {
  const { t } = GK.i18n;
  // 9×9 pixel icons (crispEdges, currentColor)
  const ICON = {
    auto: '<path d="M2 0h5v1H2zM1 1h1v1H1zM7 1h1v1H7zM0 2h1v5H0zM8 2h1v5H8zM1 7h1v1H1zM7 7h1v1H7zM2 8h5v1H2zM2 1h2v7H2zM1 2h1v5H1z"/>',
    light: '<path d="M4 0h1v1H4zM4 8h1v1H4zM0 4h1v1H0zM8 4h1v1H8zM1 1h1v1H1zM7 1h1v1H7zM1 7h1v1H1zM7 7h1v1H7zM3 2h3v1H3zM2 3h5v3H2zM3 6h3v1H3z"/>',
    dark: '<path d="M3 0h3v1H3zM2 1h2v1H2zM1 2h2v1H1zM1 3h2v3H1zM1 6h2v1H1zM8 5h1v1H8zM2 7h2v1H2zM6 6h2v1H6zM3 8h4v1H3zM4 7h3v1H4z"/>',
  };
  const icon = (m) => `<svg width="18" height="18" viewBox="0 0 9 9" aria-hidden="true" focusable="false" shape-rendering="crispEdges" fill="currentColor">${ICON[m]}</svg>`;
  function setTheme(m) {
    GK.theme.set(m);
    GK.store.actions.setTheme(m);
  }
  // the search row: inside the sticky header on wide screens, after the tab band on phones
  function placeSearch(wide) {
    const row = document.querySelector('[data-panel="search"]'), top = document.getElementById("top"), band = document.getElementById("tabs-band");
    if (!row || !top || !band) return;
    if (wide) { if (row.parentNode !== top) top.appendChild(row); }
    else if (band.nextElementSibling !== row) band.after(row);
  }
  function mount() {
    const mq = window.matchMedia && window.matchMedia("(min-width: 900px)");
    placeSearch(!!(mq && mq.matches));
    if (mq) { const f = (e) => placeSearch(e.matches); if (mq.addEventListener) mq.addEventListener("change", f); else mq.addListener(f); }
    // a tap on the current screen's tab (no hashchange) goes back to the top of that screen
    document.addEventListener("click", (e) => {
      const a = e.target.closest && e.target.closest('.tab[aria-current="page"]');
      if (!a || e.ctrlKey || e.metaKey || e.shiftKey) return;
      e.preventDefault();
      const still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: still ? "auto" : "smooth" });
    });
    document.querySelector('[data-slot="theme"]').addEventListener("click", (e) => {
      const b = e.target.closest("[data-theme-set]");
      if (b) setTheme(b.dataset.themeSet);
    });
    document.querySelector('[data-slot="theme-cycle"]').addEventListener("click", () => setTheme(GK.theme.next(GK.store.get().theme)));
    document.querySelector('[data-slot="lang"]').addEventListener("click", (e) => {
      const b = e.target.closest("[data-lang]");
      if (!b) return;
      GK.i18n.set(b.dataset.lang);
      GK.store.actions.setLang(b.dataset.lang);
    });
  }
  function render() {
    const cur = GK.router.current(), lang = GK.i18n.lang(), esc = GK.util.esc;
    document.querySelector('[data-slot="brand"]').innerHTML = t("app.title");
    document.querySelector('[data-slot="tagline"]').textContent = t("app.tagline");
    document.getElementById("brand").setAttribute("aria-label", t("app.titlePlain"));
    document.title = t("app.titlePlain");
    const tabs = GK.router.tabs().map((tb) =>
      `<a class="tab" href="#${tb.id}"${tb.id === cur ? ' aria-current="page"' : ""}>${esc(t(tb.labelKey))}${tb.soon ? ` <span class="soon">${esc(t("tab.soon"))}</span>` : ""}</a>`
    ).join("");
    document.querySelectorAll('[data-slot="tabs"]').forEach((n) => { n.innerHTML = tabs; n.setAttribute("aria-label", t("tabs.label")); });
    const langEl = document.querySelector('[data-slot="lang"]');
    langEl.setAttribute("aria-label", t("lang.label"));
    langEl.innerHTML = GK.i18n.LANGS.map((l) =>
      `<button type="button" id="lang-${l.code}" data-lang="${l.code}" aria-pressed="${l.code === lang}" title="${esc(l.name)}" aria-label="${esc(t("lang.switch", { name: l.name }))}">${esc(l.label)}</button>`
    ).join("");
    const theme = GK.store.get().theme || "auto";
    const themeEl = document.querySelector('[data-slot="theme"]');
    themeEl.setAttribute("aria-label", t("theme.label"));
    themeEl.innerHTML = GK.store.THEMES.map((m) =>
      `<button type="button" id="theme-${m}" data-theme-set="${m}" aria-pressed="${m === theme}" title="${esc(t("theme." + m + "Title"))}">${icon(m)}<span class="theme-txt">${esc(t("theme." + m))}</span></button>`
    ).join("");
    const cyc = document.querySelector('[data-slot="theme-cycle"]');
    const nx = GK.theme.next(theme);
    cyc.id = "theme-cycle";
    cyc.innerHTML = icon(theme);
    cyc.setAttribute("aria-label", t("theme.cycle", { mode: t("theme." + theme), next: t("theme." + nx) }));
    cyc.title = t("theme." + theme + "Title");
    document.querySelector('[data-panel="search"]').hidden = GK.router.tab(cur).screen !== "plan";
  }
  return { mount, render };
})();

GK.app.registerPanel(GK.ui.header, { id: "header", order: 10 });
