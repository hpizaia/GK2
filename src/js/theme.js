/* GK.theme: applies the user's theme choice to <html data-theme>.
   CSS contract: dark on bare :root; light under prefers-color-scheme: light
   (:root:not([data-theme="dark"])) and on :root[data-theme="light"].
   "auto" gives the attribute back to the host (the Claude artifact viewer may set data-theme itself);
   "light"/"dark" win, and a host change is undone by a MutationObserver (only when the value differs).
   Exposes: GK.theme.{init, set, next, mode, effective}.
*/
GK.theme = (function () {
  const root = document.documentElement;
  const mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;
  let mode = "auto";
  let host = root.getAttribute("data-theme"); // what the host set before / while we are on auto
  let mine = null;                              // the value we wrote last
  function write(v) {
    mine = v;
    if (v == null) root.removeAttribute("data-theme"); else root.setAttribute("data-theme", v);
  }
  function effective() {
    const a = root.getAttribute("data-theme");
    if (a === "light" || a === "dark") return a;
    return mq && mq.matches ? "light" : "dark";
  }
  function syncMeta() {
    const eff = effective();
    root.style.colorScheme = eff;
    const m = document.querySelector('meta[name="theme-color"]');
    if (m) {
      const c = getComputedStyle(root).getPropertyValue("--slate").trim();
      if (c) m.setAttribute("content", c);
    }
  }
  function apply() {
    if (mode === "auto") {
      const want = host === "light" || host === "dark" ? host : null;
      if (root.getAttribute("data-theme") !== want) write(want); else mine = want;
    } else if (root.getAttribute("data-theme") !== mode) write(mode);
    else mine = mode;
    syncMeta();
  }
  function set(m) {
    mode = GK.store.THEMES.indexOf(m) >= 0 ? m : "auto";
    apply();
  }
  function init(m) {
    if (window.MutationObserver) {
      new MutationObserver(() => {
        const v = root.getAttribute("data-theme");
        if (v === mine) return;            // our own write
        host = v;                          // the host changed it
        if (mode !== "auto" && v !== mode) write(mode);
        else mine = v;
        syncMeta();
      }).observe(root, { attributes: true, attributeFilter: ["data-theme"] });
    }
    if (mq) {
      const onChange = () => syncMeta();
      if (mq.addEventListener) mq.addEventListener("change", onChange); else if (mq.addListener) mq.addListener(onChange);
    }
    set(m);
  }
  const next = (m) => GK.store.THEMES[(GK.store.THEMES.indexOf(m) + 1) % GK.store.THEMES.length];
  return { init, set, next, mode: () => mode, effective };
})();
