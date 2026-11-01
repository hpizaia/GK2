/* GK.ui.changelog: the "Histórico de atualizações" screen (#changelog), a route-only screen (not in the
   tab bar) reached from the footer. Reads meta.changelog, embedded by scripts/build.py from
   data/changelog.json: [{version, date: "YYYY-MM-DD" | null (unreleased), pt: [...], en: [...]}], newest first.
   Owns: the "changelog" route and its screen section (created by GK.router.ensureScreens).
   Exposes: GK.ui.changelog.{mount, render}; registered as a panel.
   Only the current version (the first entry) is open; each older one is a single 44 px row,
   "Versão 1.5.1 · 31 de outubro · 8 novidades ›", a button (aria-expanded / aria-controls) that opens its notes.
   Which ones are open lives in this module only (forgotten on reload).
*/
GK.ui.changelog = (function () {
  const { t } = GK.i18n, { esc } = GK.util;
  let root, wasHere = false;
  const opened = new Set();   // older versions the player opened (module state only)
  // "2026-10-30" -> "30 de outubro de 2026" / "October 30, 2026" (UTC: the date never shifts a day)
  // short = "31 de outubro" / "October 31" (the folded rows; the year only when it is not the current one's)
  function fmtDate(iso, short) {
    const d = /^\d{4}-\d\d-\d\d$/.test(iso || "") ? new Date(iso + "T00:00:00Z") : null;
    if (!d || isNaN(d)) return String(iso || "");
    try {
      const o = short ? { day: "numeric", month: "long", timeZone: "UTC" } : { dateStyle: "long", timeZone: "UTC" };
      return new Intl.DateTimeFormat(GK.i18n.meta(GK.i18n.lang()).locale, o).format(d);
    } catch (e) { return iso; }
  }
  function entry(e, current, open, year) {
    const lang = GK.i18n.lang(), id = GK.util.domId(e.version);
    const notes = Array.isArray(e[lang]) ? e[lang] : Array.isArray(e.en) ? e.en : Array.isArray(e.pt) ? e.pt : [];
    const unfolded = open || opened.has(e.version);
    const list = `<ul class="cl-notes" id="cl-notes-${id}"${unfolded ? "" : " hidden"}>${notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>`;
    const ver = `<span class="cl-version">${esc(t("changelog.version", { version: e.version }))}</span>`;
    if (!open) {
      // an older version: one tappable row; its notes open below it
      const day = e.date ? esc(fmtDate(e.date, String(e.date).slice(0, 4) === year)) : esc(t("changelog.unreleased"));
      return `<li class="cl-entry cl-old" id="cl-${id}">
      <h3 class="cl-head cl-head-old"><button type="button" class="cl-toggle" id="cl-toggle-${id}" data-cl-toggle="${esc(e.version)}" aria-expanded="${unfolded}" aria-controls="cl-notes-${id}">${ver}<span class="cl-date">${day} · ${esc(t("changelog.notes", { n: notes.length }))}</span><span class="cl-chev" aria-hidden="true">›</span></button></h3>
      ${list}
    </li>`;
    }
    const when = e.date ? `<time datetime="${esc(e.date)}">${esc(fmtDate(e.date))}</time>` : `<span class="badge badge-ex">${esc(t("changelog.unreleased"))}</span>`;
    const cur = e.version === current && e.date ? ` <span class="badge badge-goal">${esc(t("changelog.current"))}</span>` : "";
    return `<li class="cl-entry" id="cl-${id}">
      <h3 class="cl-head">${ver}${cur}<span class="cl-date">${when}</span></h3>
      ${list}
    </li>`;
  }
  function mount(el) {
    root = el;
    // an older version's row: open / close its notes in place (no re-render, the focus stays on the row)
    root.addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-cl-toggle]");
      if (!b || !root.contains(b)) return;
      const v = b.dataset.clToggle, open = !opened.has(v);
      if (open) opened.add(v); else opened.delete(v);
      b.setAttribute("aria-expanded", String(open));
      const ul = document.getElementById(b.getAttribute("aria-controls"));
      if (ul) ul.hidden = !open;
    });
    // entering the screen from the footer: start at the top, not at the old scroll position
    GK.router.onChange((id) => {
      const here = id === "changelog";
      if (here && !wasHere) window.scrollTo(0, 0);
      wasHere = here;
    });
  }
  function render(state, meta) {
    if (meta && meta.from === "search-toggle") return;
    if (GK.router.current() !== "changelog") { if (root.innerHTML) root.innerHTML = ""; return; }
    const m = GK.data.get().meta, list = Array.isArray(m.changelog) ? m.changelog : [];
    const top = list.find((e) => e.version === m.version) || list[0], year = top && top.date ? String(top.date).slice(0, 4) : "";
    root.innerHTML = `<div class="card cl-card">
      <a class="btn btn-sm btn-ghost cl-back" href="#plan" id="cl-back">${esc(t("changelog.back"))}</a>
      <h2 class="h2">${esc(t("changelog.title"))}</h2>
      ${list.length ? `<ol class="cl-list">${list.map((e, i) => entry(e, m.version, i === 0 || e.version === m.version, year)).join("")}</ol>` : `<p class="hint">${esc(t("changelog.empty"))}</p>`}
    </div>`;
  }
  return { mount, render };
})();

GK.router.register({ id: "changelog", labelKey: "changelog.title", screen: "changelog", tab: false, order: 900 });
GK.app.registerPanel(GK.ui.changelog, { id: "changelog", panel: "changelog", order: 70 });
