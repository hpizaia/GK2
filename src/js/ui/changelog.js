/* GK.ui.changelog: the "Histórico de atualizações" screen (#changelog), a route-only screen (not in the
   tab bar) reached from the footer. Reads meta.changelog, embedded by scripts/build.py from
   data/changelog.json: [{version, date: "YYYY-MM-DD" | null (unreleased), pt: [...], en: [...]}], newest first.
   Owns: the "changelog" route and its screen section (created by GK.router.ensureScreens).
   Exposes: GK.ui.changelog.{mount, render}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "changelog.title": "Histórico de atualizações",
    "changelog.back": "← Voltar ao planejador",
    "changelog.version": "Versão {version}",
    "changelog.unreleased": "em desenvolvimento",
    "changelog.current": "versão atual",
    "changelog.empty": "Nenhuma atualização registrada.",
  },
  en: {
    "changelog.title": "Update history",
    "changelog.back": "← Back to the planner",
    "changelog.version": "Version {version}",
    "changelog.unreleased": "in development",
    "changelog.current": "current version",
    "changelog.empty": "No updates recorded.",
  },
});

GK.ui.changelog = (function () {
  const { t } = GK.i18n, { esc } = GK.util;
  let root, wasHere = false;
  // "2026-10-30" -> "30 de outubro de 2026" / "October 30, 2026" (UTC: the date never shifts a day)
  function fmtDate(iso) {
    const d = /^\d{4}-\d\d-\d\d$/.test(iso || "") ? new Date(iso + "T00:00:00Z") : null;
    if (!d || isNaN(d)) return String(iso || "");
    try {
      return new Intl.DateTimeFormat(GK.i18n.meta(GK.i18n.lang()).locale, { dateStyle: "long", timeZone: "UTC" }).format(d);
    } catch (e) { return iso; }
  }
  function entry(e, current) {
    const lang = GK.i18n.lang();
    const notes = Array.isArray(e[lang]) ? e[lang] : Array.isArray(e.en) ? e.en : Array.isArray(e.pt) ? e.pt : [];
    const when = e.date ? `<time datetime="${esc(e.date)}">${esc(fmtDate(e.date))}</time>` : `<span class="badge badge-ex">${esc(t("changelog.unreleased"))}</span>`;
    const cur = e.version === current && e.date ? ` <span class="badge badge-goal">${esc(t("changelog.current"))}</span>` : "";
    return `<li class="cl-entry" id="cl-${GK.util.domId(e.version)}">
      <h3 class="cl-head"><span class="cl-version">${esc(t("changelog.version", { version: e.version }))}</span>${cur}<span class="cl-date">${when}</span></h3>
      <ul class="cl-notes">${notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>
    </li>`;
  }
  function mount(el) {
    root = el;
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
    root.innerHTML = `<div class="card cl-card">
      <a class="btn btn-sm btn-ghost cl-back" href="#plan" id="cl-back">${esc(t("changelog.back"))}</a>
      <h2 class="h2">${esc(t("changelog.title"))}</h2>
      ${list.length ? `<ol class="cl-list">${list.map((e) => entry(e, m.version)).join("")}</ol>` : `<p class="hint">${esc(t("changelog.empty"))}</p>`}
    </div>`;
  }
  return { mount, render };
})();

GK.router.register({ id: "changelog", labelKey: "changelog.title", screen: "changelog", tab: false, order: 900 });
GK.app.registerPanel(GK.ui.changelog, { id: "changelog", panel: "changelog", order: 70 });
