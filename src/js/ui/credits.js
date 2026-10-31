/* GK.ui.credits: the "Créditos" screen (#credits), a route-only screen (not in the tab bar) reached from the
   footer: who made the app and why (a non-profit fan project), the game's rights, where the data comes from,
   that it was made with AI, the source code, thanks, and the app version (meta.version). Since 1.4.1 it also holds
   what left the footer: the base-amounts note and the data date / game versions (the wikily credit was already here).
   Wide screens with a mouse (min-width 900px and pointer: fine): a card beside it with a QR code of the app's link
   ("Aponte a câmera do celular…"), drawn by GK.ui.qr only then, when the screen opens; phones never get it.
   Owns: the "credits" route and its screen section (created by GK.router.ensureScreens), the credits.* texts.
   Exposes: GK.ui.credits.{mount, render, APP_URL}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "credits.title": "Créditos",
    "credits.back": "← Voltar ao planejador",
    "credits.fan.h": "Um projeto de fã",
    "credits.fan.p1": "Feito por Hugo Pizaia, um fã brasileiro de Graveyard Keeper, para deixar o jogo ainda mais divertido de jogar.",
    "credits.fan.p2": "É gratuito: sem anúncios, sem compras, nada à venda e nenhum dado vendido. Ninguém lucra com ele, de forma nenhuma.",
    "credits.fan.p3": "Não tem afiliação, apoio nem qualquer ligação com a Lazy Bear Games ou a tinyBuild.",
    "credits.game.h": "O jogo",
    "credits.game.p1": "Graveyard Keeper 2 © Lazy Bear Games / tinyBuild. Os ícones, a arte dos itens, os nomes e os textos são deles e aparecem aqui como conteúdo de fã, sem fins comerciais e com o devido crédito.",
    "credits.game.p2": "Se você tem direitos sobre algo mostrado aqui e quer que seja retirado ou alterado, é só avisar pelo GitHub que será feito.",
    "credits.data.h": "Dados",
    "credits.data.p1": "Receitas, itens, estações e tecnologias vêm do {link} (© NX Software).",
    "credits.data.link": "Graveyard Keeper 2 Wiki no Wikily",
    "credits.data.p2": "Os nomes oficiais em português do Brasil saem dos próprios arquivos de texto do jogo; os marcados “não oficial” são traduções provisórias.",
    "credits.data.p3": "As quantidades são as de base; ligue suas Vantagens no Progresso para somar os bônus.",
    "credits.data.p4": "Dados de {date}: receitas do wiki da versão {wiki} do jogo, nomes oficiais da versão {game}.",
    "credits.qr.h": "Abrir no celular",
    "credits.qr.say": "Aponte a câmera do celular para abrir o app lá.",
    "credits.qr.alt": "QR code do endereço do app",
    "credits.ai.h": "Feito com IA",
    "credits.ai.p1": "Este app foi feito com o Claude Code, da Anthropic. Código, visual, cálculos e traduções foram produzidos com a IA, sob a direção do fã, que testou no jogo.",
    "credits.ai.p2": "Os erros são responsabilidade do fã, não do estúdio.",
    "credits.code.h": "Código aberto",
    "credits.code.p": "Código e documentação no {link}.",
    "credits.thanks": "Obrigado à Lazy Bear Games pelo jogo e a todo mundo que contribui com o wiki no Wikily.",
  },
  en: {
    "credits.title": "Credits",
    "credits.back": "← Back to the planner",
    "credits.fan.h": "A fan project",
    "credits.fan.p1": "Made by Hugo Pizaia, a Brazilian fan of Graveyard Keeper, to make playing the game even more fun.",
    "credits.fan.p2": "It's free: no ads, no purchases, nothing for sale and no data sold. Nobody profits from it in any way.",
    "credits.fan.p3": "Not affiliated with, endorsed by or connected to Lazy Bear Games or tinyBuild.",
    "credits.game.h": "The game",
    "credits.game.p1": "Graveyard Keeper 2 © Lazy Bear Games / tinyBuild. The icons, item art, names and texts belong to them and appear here as fan content, non-commercial and with credit.",
    "credits.game.p2": "If you hold rights to something shown here and want it removed or changed, say so on GitHub and it will be done.",
    "credits.data.h": "Data",
    "credits.data.p1": "Recipes, items, stations and technologies come from the {link} (© NX Software).",
    "credits.data.link": "Graveyard Keeper 2 Wiki on Wikily",
    "credits.data.p2": "Official Brazilian Portuguese names come from the game's own text files; names marked “não oficial” (unofficial) are provisional translations.",
    "credits.data.p3": "Amounts are the base ones; switch on your Perks in Progress to add the bonuses.",
    "credits.data.p4": "Data from {date}: wiki recipes from game version {wiki}, official names from version {game}.",
    "credits.qr.h": "Open on your phone",
    "credits.qr.say": "Point your phone's camera here to open the app there.",
    "credits.qr.alt": "QR code of the app's address",
    "credits.ai.h": "Made with AI",
    "credits.ai.p1": "This app was built with Claude Code, by Anthropic. The code, design, calculations and translations were produced with the AI under the fan's direction, and the fan tested it in the game.",
    "credits.ai.p2": "Any mistakes are the fan's responsibility, not the studio's.",
    "credits.code.h": "Open source",
    "credits.code.p": "Code and documentation on {link}.",
    "credits.thanks": "Thanks to Lazy Bear Games for the game, and to everyone who contributes to the wiki on Wikily.",
  },
});

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
    const dataDate = m.built || d.wiki ? esc(t("credits.data.p4", { date: m.built || "?", wiki: d.wiki || "?", game: d.game || d.wiki || "?" })) : "";
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
