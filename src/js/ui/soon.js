/* GK.ui.soon: generic placeholder screen for a tab that is not built yet. No placeholder is registered right now
   (Receitas and Tecnologias have their own screens since 1.2.0); the module stays so a future tab can start as
   one line:
     GK.router.register({ id: "<id>", labelKey: "<key>", screen: "soon", soon: true, order: 40 })
   and later take its id over with a real screen (see scripts/README-build.md, "Adding a module").
   Owns: [data-panel="soon"] (the <section data-screen="soon"> of src/index.html).
   Exposes: GK.ui.soon.{mount, render}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "soon.title": "{tab}: em breve",
    "soon.body": "Esta tela ainda está sendo construída. Por enquanto, use o Planejador.",
    "soon.back": "Voltar ao Planejador",
  },
  en: {
    "soon.title": "{tab}: coming soon",
    "soon.body": "This screen is still being built. For now, use the Planner.",
    "soon.back": "Back to the Planner",
  },
});

GK.ui.soon = (function () {
  const { t } = GK.i18n, { esc } = GK.util;
  let root;
  return {
    mount(el) { root = el; },
    render() {
      if (!root) return;
      const tb = GK.router.tab(GK.router.current());
      if (!tb.soon) { if (root.innerHTML) root.innerHTML = ""; return; }
      root.innerHTML = `<div class="card soon-card"><h2>${esc(t("soon.title", { tab: t(tb.labelKey) }))}</h2><p>${esc(t("soon.body"))}</p><a class="btn" href="#plan">${esc(t("soon.back"))}</a></div>`;
    },
  };
})();

GK.app.registerPanel(GK.ui.soon, { id: "soon", panel: "soon", order: 60 });
