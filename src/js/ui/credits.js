/* GK.ui.credits: the "Créditos" screen (#credits), a route-only screen (not in the tab bar) reached from the
   footer: who made the app and why (a non-profit fan project), the game's rights, where the data comes from,
   that it was made with AI, the source code, thanks, the app version (meta.version), the base-amounts note and the
   data's game versions (no build date).
   Wide screens with a mouse (min-width 900px and pointer: fine): a card beside it with a QR code of the app's link
   ("Aponte a câmera do celular…"), drawn by GK.ui.qr only then, when the screen opens; phones never get it.
   Owns: the "credits" route and its screen section (created by GK.router.ensureScreens); it shows the credits.* texts.
   Exposes: GK.ui.credits.{mount, render, APP_URL}; registered as a panel.
*/
GK.ui.credits = (function () {
  const { t } = GK.i18n, { esc } = GK.util;
  const WIKI = "https://wikily.gg/graveyard-keeper-2", REPO = "https://github.com/hpizaia/GK2";
  const APP_URL = "https://claude.ai/artifact/8hp57ZZTFoH6GyDQUdHZAn";
  const WIDE = "(min-width: 900px) and (pointer: fine)";
  let root, wasHere = false, qrSvg = "";
  const wide = () => !!(window.matchMedia && window.matchMedia(WIDE).matches);
  // the QR card: only on a wide screen with a mouse; the SVG is made the first time it is needed
  function qrCard() {
    if (!wide() || !GK.ui.qr) return "";
    if (!qrSvg) { try { qrSvg = GK.ui.qr.svg(APP_URL, t("credits.qr.alt")); } catch (e) { return ""; } }
    return `<aside class="card cr-qr" aria-labelledby="cr-qr-h">
      <h3 class="cr-head" id="cr-qr-h">${esc(t("credits.qr.h"))}</h3>
      <div class="cr-qr-box">${qrSvg}</div>
      <p class="cr-qr-say">${esc(t("credits.qr.say"))}</p>
      <p class="cr-qr-url">claude.ai/artifact/<wbr>8hp57ZZTFoH6GyDQUdHZAn</p>
    </aside>`;
  }
  const ext = (href, text) => `<a href="${esc(href)}" target="_blank" rel="noopener">${esc(text)}</a>`;
  // a text with a {link} slot: the text is escaped, then the link markup goes in
  const withLink = (key, link) => esc(t(key, { link: "\u0000" })).replace("\u0000", link);
  function section(id, paras) {
    return `<section class="cr-sec" id="cr-${id}">
      <h3 class="cr-head">${esc(t(`credits.${id}.h`))}</h3>
      ${paras.map((p) => `<p>${p}</p>`).join("")}
    </section>`;
  }
  function mount(el) {
    root = el;
    // entering the screen from the footer: start at the top, not at the old scroll position
    GK.router.onChange((id) => {
      const here = id === "credits";
      if (here && !wasHere) window.scrollTo(0, 0);
      wasHere = here;
    });
    // a window made wider or narrower while on Créditos: add or drop the QR card
    const mq = window.matchMedia && window.matchMedia(WIDE);
    if (mq) {
      const f = () => { if (GK.router.current() === "credits") render(GK.store.get(), {}); };
      if (mq.addEventListener) mq.addEventListener("change", f); else if (mq.addListener) mq.addListener(f);
    }
  }
  function render(state, meta) {
    if (meta && meta.from === "search-toggle") return;
    if (GK.router.current() !== "credits") { if (root.innerHTML) root.innerHTML = ""; return; }
    const m = GK.data.get().meta, d = m.data || {};
    const version = m.version
      ? `<p class="cr-version">${esc(t("footer.version", { app: t("app.titlePlain"), version: m.version }))}</p>` : "";
    // the data's game versions (meta.data), not the build date (it would change with every build)
    const dataDate = d.wiki ? esc(t("credits.data.p4", { wiki: d.wiki, game: d.game || d.wiki })) : "";
    const qr = qrCard();
    root.innerHTML = `<div class="cr-grid${qr ? " has-qr" : ""}"><div class="card cl-card cr-card">
      <a class="btn btn-sm btn-ghost cl-back" href="#plan" id="cr-back">${esc(t("credits.back"))}</a>
      <h2 class="h2">${esc(t("credits.title"))}</h2>
      <div class="cr-list">
        ${section("fan", [esc(t("credits.fan.p1")), esc(t("credits.fan.p2")), esc(t("credits.fan.p3"))])}
        ${section("game", [esc(t("credits.game.p1")), esc(t("credits.game.p2"))])}
        ${section("data", [withLink("credits.data.p1", ext(WIKI, t("credits.data.link"))), esc(t("credits.data.p2")), esc(t("credits.data.p3"))].concat(dataDate ? [dataDate] : []))}
        ${section("ai", [esc(t("credits.ai.p1")), esc(t("credits.ai.p2"))])}
        ${section("code", [withLink("credits.code.p", ext(REPO, "GitHub"))])}
      </div>
      <p class="cr-thanks">${esc(t("credits.thanks"))}</p>
      ${version}
    </div>${qr}</div>`;
  }
  return { mount, render, APP_URL };
})();

GK.router.register({ id: "credits", labelKey: "credits.title", screen: "credits", tab: false, order: 910 });
GK.app.registerPanel(GK.ui.credits, { id: "credits", panel: "credits", order: 75 });
