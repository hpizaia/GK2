/* GK.ui.footer: the "Letra grande" switch (first line: GK.store ui.bigText, per device, applied by GK.theme.big; it is
   here because the footer is on every screen and the header has no room at 360 px), sync status chip, data credits,
   version line (app version, game versions of the data from meta.data) and a row of links with 44 px tap areas
   (update history, credits screen, project site).
   Owns: [data-panel="footer"] and the sync.* texts. Exposes: GK.ui.footer.{mount, render}; registered as a panel.
*/
GK.i18n.add({
  pt: {
    "sync.loading": "Conectando à sua conta…",
    "sync.syncing": "Sincronizando…",
    "sync.synced": "Sincronizado {when}",
    "sync.now": "agora",
    "sync.min": "há {n} min",
    "sync.hour": "há {n} h",
    "sync.local": "Só neste aparelho",
    "sync.error": "Não sincronizado",
    "sync.loadingTitle": "Procurando o plano salvo na sua conta.",
    "sync.syncedTitle": "Plano salvo na sua conta: abre igual no celular e no computador.",
    "sync.localTitle": "O plano fica salvo só neste navegador.",
    "sync.errorTitle": "Não deu para salvar na sua conta. O plano continua salvo neste aparelho; tento de novo na próxima alteração.",
    "footer.data": "Receitas: {link} (© NX Software). Jogo, ícones e nomes © Lazy Bear Games / tinyBuild.",
    "footer.note": "Quantidades base; ligue suas Vantagens no Progresso para os bônus. Nomes oficiais extraídos do jogo; os marcados “não oficial” são traduções provisórias. Dados de {date}.",
    "footer.version": "{app} v{version}",
    "footer.history": "Histórico de atualizações",
    "footer.credits": "Créditos",
    "footer.site": "Site do projeto",
    "footer.dataVersion": "dados: wiki {wiki} · textos do jogo {game}",
    "footer.dataTitle": "Versão do jogo descrita pelas receitas do wiki e versão de onde vieram os nomes oficiais",
    "footer.links": "Sobre o app",
    "footer.bigText": "Letra grande",
    "footer.bigTitle": "Aumenta todo o texto do app, para ler de longe com o celular ao lado do jogo. Soma com o tamanho de letra do celular.",
  },
  en: {
    "sync.loading": "Connecting to your account…",
    "sync.syncing": "Syncing…",
    "sync.synced": "Synced {when}",
    "sync.now": "just now",
    "sync.min": "{n} min ago",
    "sync.hour": "{n} h ago",
    "sync.local": "This device only",
    "sync.error": "Not synced",
    "sync.loadingTitle": "Looking for the plan saved in your account.",
    "sync.syncedTitle": "Plan saved in your account: it opens the same on your phone and computer.",
    "sync.localTitle": "The plan is saved in this browser only.",
    "sync.errorTitle": "Couldn't save to your account. The plan is still saved on this device; I'll try again on your next change.",
    "footer.data": "Recipes: {link} (© NX Software). Game, icons and names © Lazy Bear Games / tinyBuild.",
    "footer.note": "Base amounts; switch on your Perks in Progress for the bonuses. Official names come from the game files; names marked “unofficial” are provisional translations. Data from {date}.",
    "footer.version": "{app} v{version}",
    "footer.history": "Update history",
    "footer.credits": "Credits",
    "footer.site": "Project site",
    "footer.dataVersion": "data: wiki {wiki} · game texts {game}",
    "footer.dataTitle": "Game version described by the wiki recipes, and version the official names come from",
    "footer.links": "About the app",
    "footer.bigText": "Large text",
    "footer.bigTitle": "Makes all the app's text bigger, to read from a distance with the phone beside the game. Adds to your phone's own text size.",
  },
});

GK.ui.footer = (function () {
  const { t } = GK.i18n;
  let root;
  function when(ts) {
    const min = Math.floor((Date.now() - ts) / 60000);
    if (min < 1) return t("sync.now");
    if (min < 60) return t("sync.min", { n: min });
    return t("sync.hour", { n: Math.floor(min / 60) });
  }
  // the account-sync status chip; also refreshed on sync status changes and every 30 s
  function chip() {
    const el = root && root.querySelector("#sync-chip");
    if (!el) return;
    const st = GK.sync.status();
    el.dataset.state = st;
    el.textContent = st === "synced" ? t("sync.synced", { when: when(GK.sync.syncedAt()) }) : t("sync." + st);
    el.title = t("sync." + st + "Title");
  }
  return {
    mount(el) {
      root = el;
      root.addEventListener("click", (e) => {
        const b = e.target.closest("#big-text");
        if (b) GK.store.actions.setUi({ bigText: b.getAttribute("aria-pressed") !== "true" });
      });
      GK.sync.subscribe(chip);
      setInterval(() => { if (GK.sync.status() === "synced") chip(); }, 30000);
    },
    render(state, meta) {
      if (meta && meta.from === "search-toggle") return;
      const link = `<a href="https://wikily.gg/graveyard-keeper-2" target="_blank" rel="noopener">Graveyard Keeper 2 Wiki · Wikily</a>`;
      const dm = GK.data.get().meta, built = dm.built || "", esc = GK.util.esc;
      // version line "Companheiro GK2 v1.2.0 · dados: …", then the links row: Histórico (#changelog, ui/changelog.js),
      // Créditos (#credits, ui/credits.js), Site; each link is a 44 px tap target (UX review: they were 16 px)
      const dv = dm.data && (dm.data.wiki || dm.data.game)
        ? ` · <span title="${esc(t("footer.dataTitle"))}">${esc(t("footer.dataVersion", { wiki: dm.data.wiki || "?", game: dm.data.game || "?" }))}</span>` : "";
      const version = dm.version
        ? `<p class="foot-version"><span>${esc(t("footer.version", { app: t("app.titlePlain"), version: dm.version }))}</span>${dv}</p>
          <nav class="foot-links" aria-label="${esc(t("footer.links"))}"><a href="#changelog" id="foot-changelog">${esc(t("footer.history"))}</a><a href="#credits" id="foot-credits">${esc(t("footer.credits"))}</a><a href="https://claude.ai/artifact/Bgn32T3eDPRFydxYoxgWTr" target="_blank" rel="noopener" id="foot-site">${esc(t("footer.site"))}</a></nav>` : "";
      // "Letra grande": a pressed-state switch (44 px); app.js puts the focus back on #big-text after the re-render
      const bigOn = !!(state.ui && state.ui.bigText);
      const big = `<p class="foot-ctl"><button type="button" class="btn btn-sm toggle big-toggle" id="big-text" aria-pressed="${bigOn}" title="${esc(t("footer.bigTitle"))}"><span class="big-aa" aria-hidden="true">Aa</span>${esc(t("footer.bigText"))}</button></p>`;
      root.innerHTML = `${big}<p class="sync-line"><span class="sync-chip" id="sync-chip"></span></p><p class="foot-data">${t("footer.data", { link })}</p><p>${esc(t("footer.note", { date: built }))}</p>${version}`;
      chip();
    },
  };
})();

GK.app.registerPanel(GK.ui.footer, { id: "footer", panel: "footer", order: 90 });
