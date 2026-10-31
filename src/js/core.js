/* core.js: the GK namespace and the panel registry. Must stay FIRST in src/manifest.json.
   Exposes: window.GK = { ui: {}, app: { registerPanel, panels } }. app.js later adds boot() and plan()
   to the same GK.app object, so any module can register itself at load time, before app.js runs.

   GK.app.registerPanel(module, opts) queues a UI module for the render loop:
     module = { mount(el, planRoot), render(state, meta, plan) }   (mount is optional)
     opts / module fields (opts win):
       id     unique name (default: opts.panel or opts.slot + index)
       panel  mount into the existing [data-panel="<panel>"] element (null/absent: el = null)
       slot   mount into a new <div data-panel="<id>"> appended to [data-slot="<slot>"], e.g.
              "planner-extra" (the empty <section> after the planner summary)
       order  render/mount order, lower first (default: registration order x 10 + 1000)
   Register once per module: a second call with the same id replaces the first.
*/
window.GK = { ui: {} };

GK.app = (function () {
  const list = [];
  function registerPanel(module, opts) {
    if (!module || typeof module.render !== "function") throw new Error("GK.app.registerPanel: module needs render()");
    const o = Object.assign({}, { id: module.id, panel: module.panel, slot: module.slot, order: module.order }, opts || {});
    const id = o.id || o.panel || (o.slot ? o.slot + "-" + list.length : "panel-" + list.length);
    const entry = { id, module, panel: o.panel || null, slot: o.slot || null,
      order: typeof o.order === "number" ? o.order : 1000 + list.length * 10, seq: list.length };
    const i = list.findIndex((p) => p.id === id);
    if (i >= 0) list[i] = Object.assign(entry, { seq: list[i].seq }); else list.push(entry);
    return module;
  }
  const panels = () => list.slice().sort((a, b) => a.order - b.order || a.seq - b.seq);
  return { registerPanel, panels };
})();
