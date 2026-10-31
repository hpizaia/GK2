/* GK.ui.tech: the Tecnologias screen (#tech): branch chips with researched/total counts, the branch list grouped
   by column, a search box over every branch, "Já pesquisei" checkboxes, the tech detail (prerequisites, unlocks,
   what it leads to, notes, "mark prerequisites as researched") and "Limpar pesquisadas" with inline confirmation.
   Owns: [data-panel="tech"] (its section is created by GK.router.ensureScreens), the route "tech" and its tab label
   "tab.tech", the shared cost markup.
   Exposes: GK.ui.tech.{mount, render, open(techId, {from}), costHtml(cost, {big}), techSlot(tech), badges(tech)}.
   open(id, {from: "plan"}) adds a "‹ Voltar: <screen>" button that returns to that screen at its old scroll position.
   Unlocked items (data-item="<item id>") are buttons that open the item in Receitas (GK.ui.recipes.open).
*/
GK.i18n.add({
  pt: {
    "tab.tech": "Tecnologias",
    "tech.title": "Tecnologias",
    "tech.hint": "Marque o que você já pesquisou no jogo. Marcar uma tecnologia conta as anteriores como pesquisadas. O Planejador usa isso para mostrar o que falta para as suas metas.",
    "tech.count": "{done} de {total} pesquisadas",
    "tech.branchCount": "{done}/{total}",
    "tech.branches": "Ramos da árvore",
    "tech.search": "Buscar tecnologia ou o que ela desbloqueia",
    "tech.searchLabel": "Buscar nas tecnologias",
    "tech.searchClear": "Limpar busca",
    "tech.results.one": "{n} tecnologia encontrada",
    "tech.results.other": "{n} tecnologias encontradas",
    "tech.noResults": "Nenhuma tecnologia com “{q}”.",
    "tech.viaUnlock": "desbloqueia {name}",
    "tech.column": "Coluna {n}",
    "tech.researched": "Já pesquisei",
    "tech.researchedLabel": "Já pesquisei: {name}",
    "tech.implied": "pesquisada (vem antes de {name})",
    "tech.impliedTitle": "Conta como pesquisada porque {name} está marcada. Para desmarcar, desmarque {name}.",
    "tech.free": "grátis",
    "tech.cost": "Custo",
    "tech.points.red": "pontos vermelhos",
    "tech.points.green": "pontos verdes",
    "tech.points.blue": "pontos azuis",
    "tech.badge.rep": "rep. {level}",
    "tech.badge.repTitle": "Requer {level} de reputação com {who}",
    "tech.badge.hidden": "oculta",
    "tech.badge.hiddenTitle": "Fica escondida na árvore até ser revelada (veja as notas)",
    "tech.badge.given": "dada pela história",
    "tech.badge.givenTitle": "Você recebe de graça num evento da história; não precisa comprar",
    "tech.badge.unofficial": "nome não oficial",
    "tech.open": "Ver detalhes de {name}",
    "tech.back": "Voltar à lista",
    "tech.backTo": "Voltar: {name}",
    "tech.unlockOpen": "Abrir {name} em Receitas",
    "tech.close": "Fechar",
    "tech.where": "{branch} · coluna {n}",
    "tech.parents": "Pré-requisitos",
    "tech.noParents": "Nenhum: é uma das primeiras do ramo.",
    "tech.markParents": "Marcar pré-requisitos como pesquisados",
    "tech.markedParents.one": "{n} pré-requisito marcado como pesquisado",
    "tech.markedParents.other": "{n} pré-requisitos marcados como pesquisados",
    "tech.parentsDone": "Todos os pré-requisitos já estão pesquisados.",
    "tech.unlocks": "Desbloqueia",
    "tech.noUnlocks": "Nada para fabricar ou construir.",
    "tech.kind.building": "construção",
    "tech.kind.recipe": "fórmula",
    "tech.at": "em {station}",
    "tech.children": "Leva a",
    "tech.noChildren": "Nada: é o fim deste caminho.",
    "tech.notes": "Notas",
    "tech.recipes.one": "Libera {n} receita do Planejador.",
    "tech.recipes.other": "Libera {n} receitas do Planejador.",
    "tech.clear": "Limpar pesquisadas",
    "tech.clearAsk.one": "Desmarcar a {n} tecnologia pesquisada?",
    "tech.clearAsk.other": "Desmarcar as {n} tecnologias pesquisadas?",
    "tech.clearYes": "Sim, limpar",
    "tech.clearNo": "Cancelar",
    "tech.cleared": "Tecnologias desmarcadas",
    "tech.empty": "Os dados da árvore de tecnologias não estão nesta página.",
    "tech.missing": "Tecnologia não encontrada.",
  },
  en: {
    "tab.tech": "Technologies",
    "tech.title": "Technologies",
    "tech.hint": "Check what you have already researched in the game. Checking a technology counts the ones before it as researched. The Planner uses this to show what is missing for your goals.",
    "tech.count": "{done} of {total} researched",
    "tech.branchCount": "{done}/{total}",
    "tech.branches": "Tree branches",
    "tech.search": "Search a technology or what it unlocks",
    "tech.searchLabel": "Search technologies",
    "tech.searchClear": "Clear search",
    "tech.results.one": "{n} technology found",
    "tech.results.other": "{n} technologies found",
    "tech.noResults": "No technology matches “{q}”.",
    "tech.viaUnlock": "unlocks {name}",
    "tech.column": "Column {n}",
    "tech.researched": "Researched",
    "tech.researchedLabel": "Researched: {name}",
    "tech.implied": "researched (comes before {name})",
    "tech.impliedTitle": "Counts as researched because {name} is checked. To uncheck it, uncheck {name}.",
    "tech.free": "free",
    "tech.cost": "Cost",
    "tech.points.red": "red points",
    "tech.points.green": "green points",
    "tech.points.blue": "blue points",
    "tech.badge.rep": "rep. {level}",
    "tech.badge.repTitle": "Needs {level} reputation with {who}",
    "tech.badge.hidden": "hidden",
    "tech.badge.hiddenTitle": "Hidden in the tree until revealed (see the notes)",
    "tech.badge.given": "story gift",
    "tech.badge.givenTitle": "Given for free by a story event; nothing to buy",
    "tech.badge.unofficial": "unofficial name",
    "tech.open": "Show details of {name}",
    "tech.back": "Back to the list",
    "tech.backTo": "Back: {name}",
    "tech.unlockOpen": "Open {name} in Recipes",
    "tech.close": "Close",
    "tech.where": "{branch} · column {n}",
    "tech.parents": "Prerequisites",
    "tech.noParents": "None: it is one of the first in its branch.",
    "tech.markParents": "Mark prerequisites as researched",
    "tech.markedParents.one": "{n} prerequisite marked as researched",
    "tech.markedParents.other": "{n} prerequisites marked as researched",
    "tech.parentsDone": "Every prerequisite is already researched.",
    "tech.unlocks": "Unlocks",
    "tech.noUnlocks": "Nothing to craft or build.",
    "tech.kind.building": "building",
    "tech.kind.recipe": "formula",
    "tech.at": "at {station}",
    "tech.children": "Leads to",
    "tech.noChildren": "Nothing: this path ends here.",
    "tech.notes": "Notes",
    "tech.recipes.one": "Unlocks {n} Planner recipe.",
    "tech.recipes.other": "Unlocks {n} Planner recipes.",
    "tech.clear": "Clear researched",
    "tech.clearAsk.one": "Uncheck the {n} researched technology?",
    "tech.clearAsk.other": "Uncheck all {n} researched technologies?",
    "tech.clearYes": "Yes, clear",
    "tech.clearNo": "Cancel",
    "tech.cleared": "Technologies unchecked",
    "tech.empty": "The technology tree data is not in this page.",
    "tech.missing": "Technology not found.",
  },
});

GK.ui.tech = (function () {
  const { t, name, num } = GK.i18n, { esc, domId } = GK.util;
  const TK = GK.tech;
  let root = null;
  let branchSel = null;   // selected branch id
  let query = "";
  let detail = null;      // open tech id
  let asking = false;     // "Limpar pesquisadas" confirmation shown
  let dirty = true;       // a store change happened while the screen was hidden
  let pendingFocus = false;   // open() switched routes: show the detail after the route's render
  let detailFrom = null, fromScroll = 0, returnTo = null;   // the route that opened the detail (open(id, {from}))
  const isOn = () => GK.router.current() === "tech";

  // ---- shared bits (also used by ui/techneeds.js) ----
  function spritePos(id) {
    const sp = GK.data.get().meta && GK.data.get().meta.sprite;
    return sp && sp.icons && id ? sp.icons[id] : null;
  }
  // tech icon in an item slot (sprite id: item/station id or tech:<slug>)
  function techSlot(tc, small) {
    return GK.util.slot(tc.icon ? { id: tc.icon } : null, name(tc), small);
  }
  // the 9x11 point gem, scaled ×2, cut out of its 32px sprite cell
  function tpIcon(color) {
    const pos = spritePos("tp:" + color);
    return pos ? `<span class="tp-ico" aria-hidden="true"><span class="ico" style="--x:${+pos[0]};--y:${+pos[1]}"></span></span>`
      : `<span class="tp-ico tp-dot" aria-hidden="true"></span>`;
  }
  function costHtml(cost, opt) {
    const big = opt && opt.big, parts = [];
    for (const c of TK.COLORS) {
      if (!cost[c] && !(opt && opt.zeros)) continue;
      parts.push(`<span class="tp tp-${c}">${tpIcon(c)}<b class="tabnum">${num(cost[c])}</b><span class="sr-only"> ${esc(t("tech.points." + c))}</span></span>`);
    }
    if (!parts.length) return `<span class="tp-cost${big ? " tp-big" : ""}"><span class="tp-free">${esc(t("tech.free"))}</span></span>`;
    return `<span class="tp-cost${big ? " tp-big" : ""}">${parts.join("")}</span>`;
  }
  function badges(tc) {
    const out = [];
    if (tc.rep) out.push(`<span class="badge badge-rep" title="${esc(t("tech.badge.repTitle", { level: tc.rep.level, who: name(tc.rep.who) }))}">${esc(t("tech.badge.rep", { level: tc.rep.level }))}</span>`);
    if (tc.hidden) out.push(`<span class="badge badge-hidden" title="${esc(t("tech.badge.hiddenTitle"))}">${esc(t("tech.badge.hidden"))}</span>`);
    if (tc.given) out.push(`<span class="badge badge-given" title="${esc(t("tech.badge.givenTitle"))}">${esc(t("tech.badge.given"))}</span>`);
    return out.join("");
  }
  // researched state of one tech: "marked" | "implied" (by a marked descendant) | ""
  function stateOf(id, state, done) {
    if (state.researched[id]) return "marked";
    return done.has(id) ? "implied" : "";
  }
  // the nearest marked descendant that makes `id` count as researched
  function impliedBy(id, state) {
    const seen = new Set(), queue = [id];
    while (queue.length) {
      const cur = TK.get(queue.shift());
      if (!cur) continue;
      for (const c of cur.children) {
        if (seen.has(c)) continue;
        seen.add(c);
        if (state.researched[c]) return TK.get(c);
        queue.push(c);
      }
    }
    return null;
  }
  function checkbox(tc, st, state, idPrefix, withText) {
    const imp = st === "implied" ? impliedBy(tc.id, state) : null;
    const title = imp ? ` title="${esc(t("tech.impliedTitle", { name: name(imp) }))}"` : "";
    const input = `<input type="checkbox" id="${idPrefix}${domId(tc.id)}" data-research="${esc(tc.id)}"${st ? " checked" : ""}${imp ? " disabled" : ""} aria-label="${esc(t("tech.researchedLabel", { name: name(tc) }))}">`;
    if (withText) return `<label class="tech-check"${title}>${input}<span>${esc(t("tech.researched"))}</span></label>`;
    return `<label class="tick"${title}>${input}</label>`;
  }

  // ---- list ----
  function row(tc, state, done, extra) {
    const st = stateOf(tc.id, state, done);
    const imp = st === "implied" ? impliedBy(tc.id, state) : null;
    const unofficial = GK.i18n.lang() !== "en" && tc.tr !== "official" && tc.tr !== "likely"
      ? `<span class="badge">${esc(t("tech.badge.unofficial"))}</span>` : "";
    const sub = [costHtml(tc.cost)];
    if (imp) sub.push(`<span class="tech-implied">${esc(t("tech.implied", { name: name(imp) }))}</span>`);
    if (extra) sub.push(`<span class="tech-via">${esc(extra)}</span>`);
    return `<div class="row tech-row${st ? " is-researched" : ""}${detail === tc.id ? " is-sel" : ""}">
      ${checkbox(tc, st, state, "rs-", false)}
      ${techSlot(tc)}
      <button type="button" class="tech-open" data-open="${esc(tc.id)}" aria-label="${esc(t("tech.open", { name: name(tc) }))}">
        <span class="row-name">${esc(name(tc))}${badges(tc)}${unofficial}</span>
        <span class="row-sub tech-sub">${sub.join("")}</span>
      </button>
      <span class="tech-chev" aria-hidden="true">›</span>
    </div>`;
  }
  function branchList(bid, state, done) {
    const list = TK.inBranch(bid), cols = new Map();
    for (const tc of list) { if (!cols.has(tc.column)) cols.set(tc.column, []); cols.get(tc.column).push(tc); }
    return [...cols.entries()].map(([col, ts]) => {
      const nDone = ts.filter((x) => done.has(x.id)).length;
      return `<section class="tech-colgroup" aria-label="${esc(t("tech.column", { n: col }))}">
        <h3 class="tech-col"><span>${esc(t("tech.column", { n: col }))}</span><span class="count">${esc(t("tech.branchCount", { done: nDone, total: ts.length }))}</span></h3>
        <div class="card list">${ts.map((x) => row(x, state, done)).join("")}</div>
      </section>`;
    }).join("");
  }
  function searchHits(q) {
    const nq = GK.data.norm(q), toks = nq.split(/\s+/).filter(Boolean);
    if (!toks.length) return [];
    const has = (s) => { const n = GK.data.norm(s); return toks.every((k) => n.indexOf(k) >= 0); };
    const hits = [];
    for (const tc of TK.all()) {
      if (has(tc.pt) || has(tc.en)) { hits.push({ tc, score: 2 }); continue; }
      const u = tc.unlocks.find((x) => has(x.pt) || has(x.en));
      if (u) hits.push({ tc, score: 1, via: t("tech.viaUnlock", { name: name(u) }) });
    }
    return hits.sort((a, b) => b.score - a.score || a.tc.rank - b.tc.rank);
  }
  function searchList(state, done) {
    const hits = searchHits(query);
    if (!hits.length) return `<div class="card empty"><p>${esc(t("tech.noResults", { q: query.trim() }))}</p></div>`;
    const groups = new Map();
    for (const h of hits) { const b = h.tc.branch; if (!groups.has(b)) groups.set(b, []); groups.get(b).push(h); }
    return `<p class="hint tech-results" role="status">${esc(t("tech.results", { n: hits.length }))}</p>` +
      TK.branches().filter((b) => groups.has(b.id)).map((b) => `<section class="tech-colgroup">
        <h3 class="tech-col"><span>${esc(name(b))}</span></h3>
        <div class="card list">${groups.get(b.id).map((h) => row(h.tc, state, done, h.via)).join("")}</div>
      </section>`).join("");
  }
  function chips(done) {
    return `<div class="tech-branches" role="group" aria-label="${esc(t("tech.branches"))}">${TK.branches().map((b) => {
      const list = TK.inBranch(b.id), n = list.filter((x) => done.has(x.id)).length;
      const on = !query.trim() && b.id === branchSel;
      const pos = spritePos(b.icon);
      const ico = pos ? `<span class="chip-ico" aria-hidden="true"><span class="ico" style="--x:${+pos[0]};--y:${+pos[1]}"></span></span>` : "";
      return `<button type="button" class="chip${on ? " is-on" : ""}" data-branch="${esc(b.id)}" aria-pressed="${on}">${ico}<span class="chip-name">${esc(name(b))}</span><span class="chip-n tabnum">${esc(t("tech.branchCount", { done: n, total: list.length }))}</span></button>`;
    }).join("")}</div>`;
  }

  // ---- detail ----
  function techLink(tc, state, done) {
    const st = stateOf(tc.id, state, done);
    return `<li><button type="button" class="tech-link${st ? " is-researched" : ""}" data-open="${esc(tc.id)}">
      ${techSlot(tc, true)}<span class="tech-link-name">${esc(name(tc))}${badges(tc)}</span>${st ? `<span class="tech-ok" aria-label="${esc(t("tech.researched"))}">✓</span>` : ""}
    </button></li>`;
  }
  function unlockRow(u) {
    const D = GK.data.get();
    const ent = u.item ? D.items[u.item] || D.stations[u.item] : null;
    const kind = u.kind === "building" ? t("tech.kind.building") : u.kind === "recipe" ? t("tech.kind.recipe") : "";
    const st = u.station ? D.stations[u.station] : null;
    const sub = [kind, st ? t("tech.at", { station: name(st) }) : ""].filter(Boolean).join(" · ");
    const body = `${GK.util.slot(ent ? { id: ent.id } : null, name(u), true)}
      <span class="tech-unlock-main"><span class="tech-unlock-name">${esc(name(u))}</span>${sub ? `<span class="row-sub">${esc(sub)}</span>` : ""}</span>`;
    // an item the Receitas screen knows: the row opens it there
    if (u.item && D.items[u.item] && GK.ui.recipes && typeof GK.ui.recipes.open === "function") {
      return `<li class="tech-unlock" data-item="${esc(u.item)}"><button type="button" class="tech-link tech-unlock-btn" data-recipe-open="${esc(u.item)}" aria-label="${esc(t("tech.unlockOpen", { name: name(u) }))}">
        ${body}<span class="tech-chev" aria-hidden="true">›</span></button></li>`;
    }
    return `<li class="tech-unlock"${u.item ? ` data-item="${esc(u.item)}"` : ""}>${body}</li>`;
  }
  function detailHtml(tc, state, done) {
    if (!tc) return `<div class="card tech-detail-card"><p>${esc(t("tech.missing"))}</p></div>`;
    const b = TK.branch(tc.branch);
    const st = stateOf(tc.id, state, done);
    const parents = TK.order(tc.parents), children = TK.order(tc.children);
    const missingAnc = TK.ancestors(tc.id).filter((x) => !done.has(x.id));
    const anc = TK.ancestors(tc.id);
    const fromTab = detailFrom ? GK.router.TABS.find((r) => r.id === detailFrom) : null;
    return `<article class="card tech-detail-card" aria-labelledby="tech-d-h">
      <div class="tech-d-top">
        ${fromTab ? `<button type="button" class="btn btn-sm btn-ghost tech-from" data-back-route>‹ ${esc(t("tech.backTo", { name: t(fromTab.labelKey) }))}</button>`
          : `<button type="button" class="btn btn-sm btn-ghost tech-back" data-close>‹ ${esc(t("tech.back"))}</button>`}
        <button type="button" class="btn btn-sm btn-ghost tech-x" data-close aria-label="${esc(t("tech.close"))}">✕</button>
      </div>
      <header class="tech-d-head">
        ${techSlot(tc)}
        <div class="tech-d-title">
          <h2 id="tech-d-h">${esc(name(tc))}</h2>
          <span class="row-sub">${esc(t("tech.where", { branch: b ? name(b) : tc.branch, n: tc.column }))}</span>
        </div>
      </header>
      <div class="tech-d-cost"><span class="tech-d-label">${esc(t("tech.cost"))}</span>${costHtml(tc.cost, { big: true })}</div>
      ${badges(tc) ? `<div class="tech-d-badges">${badges(tc)}</div>` : ""}
      <div class="tech-d-check">${checkbox(tc, st, state, "rs-d-", true)}${st === "implied" ? `<span class="row-sub">${esc(t("tech.implied", { name: name(impliedBy(tc.id, state)) }))}</span>` : ""}</div>
      ${tc.notes ? `<section class="tech-d-sec"><h3>${esc(t("tech.notes"))}</h3><p class="tech-notes">${esc(name(tc.notes))}</p></section>` : ""}
      <section class="tech-d-sec">
        <h3>${esc(t("tech.parents"))} <span class="count">${parents.length}</span></h3>
        ${parents.length ? `<ul class="tech-links">${parents.map((x) => techLink(x, state, done)).join("")}</ul>` : `<p class="hint">${esc(t("tech.noParents"))}</p>`}
        ${anc.length ? (missingAnc.length
          ? `<button type="button" class="btn btn-sm" data-mark-parents="${esc(tc.id)}">${esc(t("tech.markParents"))} (${num(missingAnc.length)})</button>`
          : `<p class="hint">${esc(t("tech.parentsDone"))}</p>`) : ""}
      </section>
      <section class="tech-d-sec">
        <h3>${esc(t("tech.unlocks"))} <span class="count">${tc.unlocks.length}</span></h3>
        ${tc.unlocks.length ? `<ul class="tech-unlocks">${tc.unlocks.map(unlockRow).join("")}</ul>` : `<p class="hint">${esc(t("tech.noUnlocks"))}</p>`}
        ${tc.recipes.length ? `<p class="hint">${esc(t("tech.recipes", { n: tc.recipes.length }))}</p>` : ""}
      </section>
      <section class="tech-d-sec">
        <h3>${esc(t("tech.children"))} <span class="count">${children.length}</span></h3>
        ${children.length ? `<ul class="tech-links">${children.map((x) => techLink(x, state, done)).join("")}</ul>` : `<p class="hint">${esc(t("tech.noChildren"))}</p>`}
      </section>
    </article>`;
  }

  // ---- screen ----
  function listHtml(state, done) {
    return query.trim() ? searchList(state, done) : branchList(branchSel, state, done);
  }
  function clearHtml(state) {
    const n = Object.keys(state.researched).length;
    if (asking && n) {
      return `<div class="tech-ask" role="alert"><span>${esc(t("tech.clearAsk", { n }))}</span>
        <button type="button" class="btn btn-sm btn-confirm" id="tech-clear-yes" data-clear-yes>${esc(t("tech.clearYes"))}</button>
        <button type="button" class="btn btn-sm btn-ghost" id="tech-clear-no" data-clear-no>${esc(t("tech.clearNo"))}</button></div>`;
    }
    return `<button type="button" class="btn btn-sm btn-ghost btn-danger" id="tech-clear" data-clear${n ? "" : " disabled"}>${esc(t("tech.clear"))}</button>`;
  }
  function render(state, meta) {
    if (!root) return;
    if (!isOn()) { dirty = true; return; }
    if (meta && meta.from === "search-toggle" && !dirty) return;
    dirty = false;
    if (!TK.available()) { root.innerHTML = `<div class="card empty"><p>${esc(t("tech.empty"))}</p></div>`; return; }
    if (!branchSel || !TK.branch(branchSel)) branchSel = TK.branches()[0].id;
    if (detail && !TK.get(detail)) detail = null;
    const done = TK.researchedSet(state.researched);
    const total = TK.all().length;
    root.innerHTML = `<div class="tech-screen${detail ? " has-detail" : ""}">
      <div class="tech-main">
        <div class="section-head"><h2 class="h2">${esc(t("tech.title"))} <span class="count tabnum">${esc(t("tech.count", { done: done.size, total }))}</span></h2></div>
        <p class="hint">${esc(t("tech.hint"))}</p>
        <div class="tech-tools">
          <div class="search-box tech-search">
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><circle cx="7.5" cy="7.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 12l4.5 4.5" stroke="currentColor" stroke-width="2"/></svg>
            <input type="search" class="search-input" id="tech-q" value="${esc(query)}" placeholder="${esc(t("tech.search"))}" aria-label="${esc(t("tech.searchLabel"))}" autocomplete="off" spellcheck="false" enterkeyhint="search">
            <button type="button" class="search-clear" data-q-clear aria-label="${esc(t("tech.searchClear"))}"${query ? "" : " hidden"}>×</button>
          </div>
          <div class="tech-clear-box">${clearHtml(state)}</div>
        </div>
        ${chips(done)}
        <div class="tech-list" id="tech-list">${listHtml(state, done)}</div>
      </div>
      <aside class="tech-detail" id="tech-detail"${detail ? "" : " hidden"}>${detail ? detailHtml(TK.get(detail), state, done) : ""}</aside>
    </div>`;
    if (pendingFocus) { pendingFocus = false; showDetail(true); }
  }
  const rerender = () => { dirty = true; render(GK.store.get(), {}); };
  // only the list (and chips) while typing, so the input keeps its caret
  function renderList() {
    const state = GK.store.get(), done = TK.researchedSet(state.researched);
    const list = root.querySelector("#tech-list");
    if (list) list.innerHTML = listHtml(state, done);
    const ch = root.querySelector(".tech-branches");
    if (ch) ch.outerHTML = chips(done);
    const x = root.querySelector("[data-q-clear]");
    if (x) x.hidden = !query;
  }
  const narrow = () => !window.matchMedia || !window.matchMedia("(min-width: 900px)").matches;
  function scrollTopOf(el) {
    if (!el) return;
    const y = el.getBoundingClientRect().top + window.scrollY - ((parseInt(getComputedStyle(document.documentElement).getPropertyValue("--hdr-h"), 10) || 0) + 8);
    if (Math.abs(window.scrollY - y) > 4) window.scrollTo(0, Math.max(0, y));
  }
  function open(id, opts) {
    const tc = TK.get(id);
    if (!tc) return;
    detail = id;
    if (!query.trim()) branchSel = tc.branch;
    asking = false;
    if (!isOn()) {
      detailFrom = opts && opts.from && opts.from !== "tech" ? opts.from : null;
      fromScroll = window.scrollY;
      dirty = true; pendingFocus = true; location.hash = "#tech"; return;
    }
    rerender();
    showDetail(false);
  }
  // bring the open detail into view (phones: it replaces the list; wide: it is sticky beside it) and focus its title
  function showDetail(fromOtherRoute) {
    const d = root.querySelector("#tech-detail");
    if (narrow()) scrollTopOf(d);
    else if (fromOtherRoute) window.scrollTo(0, 0);
    const h = root.querySelector("#tech-d-h");
    if (h) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); }
  }
  // "‹ Voltar: Planejador": back to the screen that opened the detail, where it was, focus on the opener
  function backToOrigin() {
    const route = detailFrom, id = detail;
    detail = null; detailFrom = null; dirty = true;
    returnTo = { route, y: fromScroll, id };
    location.hash = route;
  }
  function close() {
    const id = detail;
    detail = null; detailFrom = null;
    rerender();
    const btn = id && root.querySelector(`#tech-list [data-open="${CSS.escape(id)}"]`);
    if (btn) { if (narrow()) btn.scrollIntoView({ block: "center" }); btn.focus({ preventScroll: true }); }
  }
  function mount(el) {
    root = el;
    GK.router.onChange((rid) => {
      if (!returnTo || rid !== returnTo.route) { if (rid !== "tech") returnTo = null; return; }
      const r = returnTo; returnTo = null;
      setTimeout(() => {
        window.scrollTo(0, r.y);
        const scr = document.querySelector(`[data-screen="${GK.router.tab(r.route).screen}"]`);
        const b = scr && r.id && (scr.querySelector(`[data-open="${CSS.escape(r.id)}"]`) || scr.querySelector(`[data-tech="${CSS.escape(r.id)}"]`));
        if (b) b.focus({ preventScroll: true });
      }, 0);
    });
    root.addEventListener("click", (e) => {
      const S = GK.store;
      const o = e.target.closest("[data-open]");
      if (o) { open(o.dataset.open); return; }
      if (e.target.closest("[data-close]")) { close(); return; }
      if (e.target.closest("[data-back-route]")) { backToOrigin(); return; }
      const ro = e.target.closest("[data-recipe-open]");
      if (ro) { GK.ui.recipes.open(ro.dataset.recipeOpen, { from: "tech" }); return; }
      const b = e.target.closest("[data-branch]");
      if (b) {
        branchSel = b.dataset.branch; query = "";
        if (detail && TK.get(detail) && TK.get(detail).branch !== branchSel) { detail = null; detailFrom = null; }
        rerender();
        const nb = root.querySelector(`[data-branch="${CSS.escape(branchSel)}"]`);
        if (nb) nb.focus({ preventScroll: true });
        return;
      }
      if (e.target.closest("[data-q-clear]")) { query = ""; renderList(); const q = root.querySelector("#tech-q"); if (q) { q.value = ""; q.focus(); } return; }
      if (e.target.closest("[data-clear]")) { asking = true; rerender(); const y = root.querySelector("#tech-clear-no"); if (y) y.focus(); return; }
      if (e.target.closest("[data-clear-no]")) { asking = false; rerender(); const c = root.querySelector("#tech-clear"); if (c) c.focus(); return; }
      if (e.target.closest("[data-clear-yes]")) { asking = false; S.actions.clearResearched(); GK.ui.toast(t("tech.cleared")); return; }
      const mp = e.target.closest("[data-mark-parents]");
      if (mp) {
        const st = S.get(), done = TK.researchedSet(st.researched);
        const ids = TK.ancestors(mp.dataset.markParents).filter((x) => !done.has(x.id)).map((x) => x.id);
        if (!ids.length) return;
        // one store update for the whole batch (same field and meta as actions.setResearched)
        S.update((s) => { ids.forEach((id) => { s.researched[id] = true; }); }, { from: "tech" });
        GK.ui.toast(t("tech.markedParents", { n: ids.length }));
      }
    });
    root.addEventListener("change", (e) => {
      const cb = e.target.closest("[data-research]");
      if (cb) GK.store.actions.setResearched(cb.dataset.research, cb.checked);
    });
    const onInput = GK.util.debounce((v) => { query = v; renderList(); }, 120);
    root.addEventListener("input", (e) => { if (e.target.id === "tech-q") onInput(e.target.value); });
    root.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && e.target.id === "tech-q" && query) { e.preventDefault(); query = ""; e.target.value = ""; renderList(); }
      else if (e.key === "Escape" && detail) close();
    });
  }
  return { mount, render, open, costHtml, techSlot, badges };
})();

GK.router.register({ id: "tech", labelKey: "tab.tech", screen: "tech", order: 30 });
GK.app.registerPanel(GK.ui.tech, { id: "tech", panel: "tech", order: 70 });
