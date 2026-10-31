/* GK.router: hash routes with bare tokens (#plan, #recipes, #tech, #changelog: the artifact viewer only
   passes a plain #token). Owns the route registry and the visible screen ([data-screen]).
   Exposes: GK.router.{register, tabs, tab, TABS, init, ensureScreens, current, onChange}.
   A new screen is one call from its own module:
     GK.router.register({ id: "recipes", labelKey: "rc.tab", screen: "recipes", order: 20 })
   tab: false makes a route-only screen (no entry in the tab bar). A missing <section data-screen> is
   created in <main> by ensureScreens() (with data-panel=<screen> for GK.app.registerPanel).
*/
GK.i18n.add({
  pt: {
    "tab.plan": "Planejador",
  },
  en: {
    "tab.plan": "Planner",
  },
});

GK.router = (function () {
  const TABS = [];   // every registered route, sorted by order (tab: false ones too)
  let current = "plan";
  const subs = [];
  const DEFAULT = "plan";
  // {id, labelKey, screen = id, order = 100, tab = true, soon = false}; same id again = replace
  function register(r) {
    if (!r || !r.id) throw new Error("GK.router.register: id is required");
    const route = Object.assign({ screen: r.id, order: 100, tab: true, soon: false }, r);
    const i = TABS.findIndex((t) => t.id === route.id);
    if (i >= 0) TABS.splice(i, 1);
    TABS.push(route);
    TABS.sort((a, b) => a.order - b.order);
    return route;
  }
  const tabs = () => TABS.filter((t) => t.tab !== false);
  const tab = (id) => TABS.find((t) => t.id === id) || TABS.find((t) => t.id === DEFAULT) || TABS[0];
  function parse() {
    const h = (location.hash || "").replace(/^#/, "");
    return TABS.some((t) => t.id === h) ? h : DEFAULT;
  }
  // one <section data-screen> per registered screen; missing ones are appended to <main>
  function ensureScreens() {
    const main = document.querySelector("main");
    if (!main) return;
    for (const r of TABS) {
      if (document.querySelector(`[data-screen="${r.screen}"]`)) continue;
      const s = document.createElement("section");
      s.className = "wrap screen screen-" + r.screen;
      s.dataset.screen = r.screen;
      s.dataset.panel = r.screen;
      s.hidden = true;
      main.appendChild(s);
    }
  }
  function apply() {
    current = parse();
    const screen = tab(current).screen;
    document.querySelectorAll("[data-screen]").forEach((s) => { s.hidden = s.dataset.screen !== screen; });
    subs.forEach((f) => f(current));
  }
  function init() { ensureScreens(); window.addEventListener("hashchange", apply); apply(); }
  return { TABS, register, tabs, tab, init, ensureScreens, current: () => current, onChange: (f) => subs.push(f) };
})();

// the planner is the default route; its panels live in the template (src/index.html)
GK.router.register({ id: "plan", labelKey: "tab.plan", screen: "plan", order: 10 });
