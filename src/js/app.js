/* GK.app: boot and the render loop. Must stay LAST in src/manifest.json: it boots right away.
   Mounts every panel queued with GK.app.registerPanel (see core.js) in `order`, renders them all on
   every store change and route change, and starts GK.sync.
   Exposes: GK.app.{boot, plan, registerPanel, panels}.
*/
(function () {
  let plan = null;
  const S = GK.store;
  let mounted = [];   // registry entries, in order (see GK.app.registerPanel in core.js)
  const computePlan = (st) => GK.calc.plan(st.goals, GK.data.get(),
    { choice: st.choice, have: st.have, perks: st.perks, groupChoice: st.groupChoice });
  function renderAll(state, meta) {
    if (!(meta && meta.from === "search-toggle")) plan = computePlan(state);
    const active = document.activeElement && document.activeElement.id;
    for (const p of mounted) p.module.render(state, meta || {}, plan);
    if (active && document.activeElement && document.activeElement.id !== active) {
      const el = document.getElementById(active);
      if (el) el.focus({ preventScroll: true });
    }
  }
  // the element a registered panel mounts into (null for panels that find their own nodes, like the header)
  function target(p) {
    if (p.slot) {
      const host = document.querySelector(`[data-slot="${p.slot}"]`);
      if (!host) { console.warn(`GK.app: no [data-slot="${p.slot}"] for panel ${p.id}`); return undefined; }
      const el = document.createElement("div");
      el.dataset.panel = p.id;
      host.appendChild(el);
      return el;
    }
    if (!p.panel) return null;
    const el = document.querySelector(`[data-panel="${p.panel}"]`);
    if (!el) console.warn(`GK.app: no [data-panel="${p.panel}"] for panel ${p.id}`);
    return el || undefined;
  }
  function boot() {
    GK.data.load();
    const had = S.load();
    S.actions.pruneUnknown((id) => !!GK.data.item(id));
    GK.i18n.set(S.get().lang || GK.i18n.detect());
    GK.theme.init(S.get().theme);
    const planRoot = document.querySelector('[data-screen="plan"]');
    GK.router.ensureScreens();   // registered screens without a <section> in the template get one
    mounted = [];
    for (const p of GK.app.panels()) {
      const el = target(p);
      if (el === undefined) continue;
      if (typeof p.module.mount === "function") p.module.mount(el, planRoot);
      mounted.push(p);
    }
    S.subscribe(renderAll);
    GK.router.onChange(() => renderAll(S.get(), { from: "router" }));
    // keep sticky offsets in sync with the header's real height
    const top = document.getElementById("top");
    const setH = () => document.documentElement.style.setProperty("--hdr-h", top.offsetHeight + "px");
    if (window.ResizeObserver) new ResizeObserver(setH).observe(top); else window.addEventListener("resize", setH);
    setH();
    if (!had) {
      // First visit: open on a realistic, clearly labelled example plan.
      const ex = [{ item: "crate", qty: 3 }, { item: "furnace-i", qty: 1 }, { item: "master-sword", qty: 1 }].filter((g) => GK.data.item(g.item));
      if (ex.length) S.actions.seedExample(ex);
    }
    GK.router.init(); // triggers the first render
    S.subscribe((st, meta) => GK.sync.onStore(st, meta));
    GK.sync.start();  // async: lights up account sync when (if) the db + user capabilities resolve
  }
  Object.assign(GK.app, { boot, plan: () => plan || computePlan(S.get()) });
})();

GK.app.boot();
