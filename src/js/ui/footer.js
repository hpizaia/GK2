/* GK.ui.footer (1.4.1: shorter): line 1 = the "Letra grande" switch (GK.store ui.bigText, per device, applied by
   GK.theme.big; here because the footer is on every screen and the header has no room at 360 px) and the sync chip,
   shown only with an account (syncing / synced) or on error; line 2 = the links with 44 px tap areas (update
   history, credits screen, project site); line 3 = one quiet version line "v1.4.0 · dados do jogo 1.011 (receitas
   1.010)" (meta.version, meta.data). The data credits and the note on amounts/names live on the Créditos screen.
   Stale data notice (meta.gameVersion = data/game-version.json, embedded by build.py): when its `latest` is newer
   than the wiki recipes (meta.data.wiki, compared as versions: 1.012 > 1.011), a line under the version with an "i"
   that opens the note, and a thin band under the tabs (#notice-band, made here, placed after #tabs-band) with a ✕.
   Closing it is kept per device with the version (localStorage "gk2-companion.notice" = {"closed": "1.011"}): a new
   `latest` brings it back.
   Owns: [data-panel="footer"], #notice-band and the sync.* texts.
   Exposes: GK.ui.footer.{mount, render, stale, cmpVersion}; registered as a panel.
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
    "footer.version": "{app} v{version}",
    "footer.history": "Histórico de atualizações",
    "footer.credits": "Créditos",
    "footer.site": "Site do projeto",
    "footer.dataTitle": "Versão do jogo descrita pelas receitas do wiki e versão de onde vieram os nomes oficiais",
    "footer.links": "Sobre o app",
    "footer.bigText": "Letra grande",
    "footer.line": "v{version} · dados do jogo {game}",
    "footer.lineMixed": "v{version} · dados do jogo {game} (receitas {wiki})",
    "footer.stale": "O jogo já está na {latest}; as receitas daqui são da {wiki}.",
    "footer.staleMore": "Mais sobre a versão do jogo",
    "footer.staleClose": "Fechar aviso",
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
    "footer.version": "{app} v{version}",
    "footer.history": "Update history",
    "footer.credits": "Credits",
    "footer.site": "Project site",
    "footer.dataTitle": "Game version described by the wiki recipes, and version the official names come from",
    "footer.links": "About the app",
    "footer.bigText": "Large text",
    "footer.line": "v{version} · game data {game}",
    "footer.lineMixed": "v{version} · game data {game} (recipes {wiki})",
    "footer.stale": "The game is on {latest}; recipes here are from {wiki}.",
    "footer.staleMore": "More about the game version",
    "footer.staleClose": "Close notice",
    "footer.bigTitle": "Makes all the app's text bigger, to read from a distance with the phone beside the game. Adds to your phone's own text size.",
  },
});

GK.ui.footer = (function () {
  const { t } = GK.i18n, esc = GK.util.esc;
  const NOTICE_KEY = "gk2-companion.notice";
  const SITE = "https://claude.ai/artifact/Bgn32T3eDPRFydxYoxgWTr";
  let root, band, noteOpen = false;
  function when(ts) {
    const min = Math.floor((Date.now() - ts) / 60000);
    if (min < 1) return t("sync.now");
    if (min < 60) return t("sync.min", { n: min });
    return t("sync.hour", { n: Math.floor(min / 60) });
  }
  // the account-sync status chip: state, not text, so it shows only with an account at work or on error
  // ("local" = no account; "loading" lasts a moment at boot and would only flash)
  const CHIP = { syncing: 1, synced: 1, error: 1 };
  function chip() {
    const el = root && root.querySelector("#sync-chip");
    if (!el) return;
    const st = GK.sync.status();
    el.hidden = !CHIP[st];
    el.dataset.state = st;
    el.textContent = st === "synced" ? t("sync.synced", { when: when(GK.sync.syncedAt()) }) : t("sync." + st);
    el.title = t("sync." + st + "Title");
  }
  // "1.012" vs "1.011": dot-separated parts compared as numbers (game versions keep 3-digit minors)
  function cmpVersion(a, b) {
    const pa = String(a).split(".").map(Number), pb = String(b).split(".").map(Number);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
      const x = pa[i] || 0, y = pb[i] || 0;
      if (x !== y) return x < y ? -1 : 1;
    }
    return 0;
  }
  // {latest, wiki, note} when the game is newer than the wiki recipes, else null
  function stale(dm) {
    dm = dm || GK.data.get().meta;
    const gv = dm.gameVersion, wiki = dm.data && dm.data.wiki;
    if (!gv || !gv.latest || !wiki || cmpVersion(gv.latest, wiki) <= 0) return null;
    const note = gv.note || {};
    return { latest: gv.latest, wiki, note: note[GK.i18n.lang()] || note.en || note.pt || "" };
  }
  function closedFor() {
    try { const v = JSON.parse(localStorage.getItem(NOTICE_KEY) || "null"); return v && v.closed; } catch (e) { return null; }
  }
  function closeBand(latest) {
    try { localStorage.setItem(NOTICE_KEY, JSON.stringify({ closed: latest })); } catch (e) { /* private mode: closed for now */ }
    if (band) { band.hidden = true; band.innerHTML = ""; }
  }
  function renderBand(st) {
    if (!band) return;
    if (!st || closedFor() === st.latest) { band.hidden = true; band.innerHTML = ""; return; }
    band.hidden = false;
    band.innerHTML = `<div class="wrap notice-in"><span class="notice-txt">${esc(t("footer.stale", st))}</span><button type="button" class="notice-x" id="notice-close" data-notice-close="${esc(st.latest)}" title="${esc(t("footer.staleClose"))}" aria-label="${esc(t("footer.staleClose"))}">✕</button></div>`;
  }
  const INFO_SVG = '<svg width="16" height="16" viewBox="0 0 9 9" aria-hidden="true" focusable="false" shape-rendering="crispEdges" fill="currentColor"><path d="M2 0h5v1H2zM1 1h1v1H1zM7 1h1v1H7zM0 2h1v5H0zM8 2h1v5H8zM1 7h1v1H1zM7 7h1v1H7zM2 8h5v1H2zM4 2h1v1H4zM4 4h1v3H4z"/></svg>';
  return {
    stale, cmpVersion,
    mount(el) {
      root = el;
      root.addEventListener("click", (e) => {
        const b = e.target.closest("#big-text");
        if (b) GK.store.actions.setUi({ bigText: b.getAttribute("aria-pressed") !== "true" });
        const i = e.target.closest("#foot-stale-i");
        if (i) {
          noteOpen = !noteOpen;
          i.setAttribute("aria-expanded", String(noteOpen));
          const n = root.querySelector("#foot-stale-note");
          if (n) n.hidden = !noteOpen;
        }
      });
      // the band under the tabs (on desktop the tab band is hidden, so it sits right under the sticky header)
      band = document.createElement("div");
      band.className = "notice-band"; band.id = "notice-band"; band.hidden = true;
      band.setAttribute("role", "note");
      const tabs = document.getElementById("tabs-band"), main = document.querySelector("main");
      if (tabs) tabs.after(band); else if (main) main.before(band);
      band.addEventListener("click", (e) => {
        const x = e.target.closest("[data-notice-close]");
        if (x) closeBand(x.dataset.noticeClose);
      });
      GK.sync.subscribe(chip);
      setInterval(() => { if (GK.sync.status() === "synced") chip(); }, 30000);
    },
    render(state, meta) {
      if (meta && meta.from === "search-toggle") return;
      const dm = GK.data.get().meta, d = dm.data || {}, st = stale(dm);
      // "v1.4.0 · dados do jogo 1.011" (one number when the wiki and the game texts agree)
      const game = d.game || d.wiki, wiki = d.wiki || d.game;
      const line = !dm.version ? "" : !game ? `v${dm.version}`
        : t(game === wiki ? "footer.line" : "footer.lineMixed", { version: dm.version, game, wiki });
      const version = line ? `<p class="foot-version" title="${esc(t("footer.dataTitle"))}">${esc(line)}</p>` : "";
      const staleLine = st ? `<p class="foot-stale"><span>${esc(t("footer.stale", st))}</span>${st.note ? `<button type="button" class="info-ico" id="foot-stale-i" aria-expanded="${noteOpen}" aria-controls="foot-stale-note" title="${esc(t("footer.staleMore"))}" aria-label="${esc(t("footer.staleMore"))}">${INFO_SVG}</button>` : ""}</p>${st.note ? `<p class="foot-stale-note" id="foot-stale-note"${noteOpen ? "" : " hidden"}>${esc(st.note)}</p>` : ""}` : "";
      // "Letra grande": a pressed-state switch (44 px); app.js puts the focus back on #big-text after the re-render
      const bigOn = !!(state.ui && state.ui.bigText);
      const big = `<button type="button" class="btn btn-sm toggle big-toggle" id="big-text" aria-pressed="${bigOn}" title="${esc(t("footer.bigTitle"))}"><span class="big-aa" aria-hidden="true">Aa</span>${esc(t("footer.bigText"))}</button>`;
      // the links: Histórico (#changelog, ui/changelog.js), Créditos (#credits, ui/credits.js), Site; 44 px each
      const links = `<nav class="foot-links" aria-label="${esc(t("footer.links"))}"><a href="#changelog" id="foot-changelog">${esc(t("footer.history"))}</a><a href="#credits" id="foot-credits">${esc(t("footer.credits"))}</a><a href="${SITE}" target="_blank" rel="noopener" id="foot-site">${esc(t("footer.site"))}</a></nav>`;
      root.innerHTML = `<div class="foot-top">${big}<span class="sync-chip" id="sync-chip" hidden></span></div>${links}${version}${staleLine}`;
      chip();
      renderBand(st);
    },
  };
})();

GK.app.registerPanel(GK.ui.footer, { id: "footer", panel: "footer", order: 90 });
