/* GK.ui.recipes: the Receitas screen (#recipes). Browse every item (own search box, category and station
   chips with counts, hidden-items toggle, 60 rows per page) and an item detail (recipes with inputs, unlock,
   mastery, time/energy, by-products; group members; how to obtain; "Usado em"; add to goals; pick the
   recipe the planner uses). Only the bare #recipes hash reaches the page, so the open item lives in module
   state and in sessionStorage (gk2-recipes-view).
   Owns: [data-panel="recipes"] and the "recipes" route.
   Exposes: GK.ui.recipes.{mount, render, open(itemId, {from})}; registered as a panel. open(id, {from: "plan"})
   (the planner's item icons, the Tecnologias unlock rows) shows the detail with a "← Voltar: <screen>" button that
   returns to that screen at its old scroll position and focuses the button that opened the detail.
   Here: the view state, the list and its filters, the detail page, navigation, clicks, renaming. The recipe cards are
   GK.ui.rcCards (ui/recipes-cards.js), the item facts GK.ui.rcFacts (ui/recipes-facts.js); the texts are the rc.*
   keys of src/js/i18n/pt.js and en.js.
   List: rows say "Construir no Cemitério" (GK.ui.fmt.buildLabel) and the recipe count only when > 1; "Mostrar itens
   ocultos" at the end of the list; a row with no recipe says "Coleta ou compra" (rc.raw); a name shared by two items
   shows the other language's name small (GK.ui.fmt.otherName).
   Detail: "Também em" once when every recipe shares it; no "Usado em" section when empty; mastery level 0 shows no
   "0"; no plain toast when the first goal replaces the example (search.js shows it). "Quem compra" (items[].sell /
   .price / .fix), "Estudar" (items[].study + the global "Já estudei", state.studied) and "Pedido em" (items[].asked:
   quests, town restorations and orders), folded by default (spoiler); each block only when the item has the data.
   The phone's back gesture closes the detail (GK.router.detailHistory: an entry per item opened on this screen;
   "← Voltar" and "Ver lista" drop them).
   "Como fabricar" follows GK.calc.recipeGroups: one card for
   the recipes that differ only in one ingredient (its grade picked in the card: bronze / prata / ouro, or "E mais um
   destes" rows); a tap on an option sets the planner's recipe (no "Usar" button there); the circular recipes fold at
   the end ("Melhorar a qualidade · N"). A graded item shows its name without "(prata)", the star on its icon
   (GK.util.slot) and the grade word on the line below (list rows, ingredient lines, "Usado em"); bronze, prata, ouro
   in that order (GK.data.gradeSort). "Quem compra": pixel coins (recipes.css).
   The plain item of a graded family is the bronze one (Abóbora, Vinho, Uvas, the seeds…):
   the bronze star and word like the others, the list and the search keep the family in one run (bronze, prata, ouro),
   the detail title reads "Abóbora (bronze)" (GK.ui.fmt.gradedName). An "Any X" line ("Álcool de Qualquer Vinho") and
   a row of "E mais um destes" (it stands for the whole ingredient) show no star.
   Renaming: the detail's "não oficial" / "editado" tag is a button ("Renomear <nome>") that opens the name's field
   under the header (Salvar / Cancelar, "Voltar ao nome original" once edited). It writes GK.store overrides
   (lang -> {itemId: name}, synced). The open form also offers "Exportar nomes editados (N)": the JSON a player pastes
   into an issue (CONTRIBUTING.md), keyed by the English wiki name like the name files in data/.
*/
GK.ui.recipes = (function () {
  const { t, name, num, edited } = GK.i18n, { esc, slot } = GK.util;
  const PAGE = 60, CHIPS = 8, LIST_CAP = 40, SKEY = "gk2-recipes-view";
  const { graded, UNOFFICIAL } = GK.ui.fmt;
  const { expandable } = GK.calc;
  const { hiddenTag, stationLabel, runes, itemLine, altNames, sharedAlt, recipeCard, groupCard } = GK.ui.rcCards;
  const { whereHtml, tipHtml, stackSlot, stackCap, sellHtml, studyHtml, askedHtml } = GK.ui.rcFacts;
  const BUILD = { id: "build", i18n: "station.build" }, NONE = { id: "none", i18n: "rc.noRecipe" }, NOCAT = { i18n: "rc.noCat" };

  let root, browseEl, detailEl, input, clearBtn, listEl, chipsEl, metaEl, moreEl, filtersEl, hiddenEl;
  let IX = null;                 // lazy index, built on the first visit
  // view state (also in sessionStorage)
  const V = { item: null, stack: [], q: "", cat: null, st: null, from: null };   // from: route that opened the detail
  let fromScroll = 0, returnTo = null, pendingFocus = false;
  let shown = PAGE, results = [], expanded = { cat: false, st: false };
  let addQty = 1, usedAll = false, hereAll = false, whereAll = false, listScroll = 0, sortCache = { key: "", ids: [] };
  let askedOpen = false;         // "Pedido em" unfolded (folded again when another item opens)
  let cycOpen = false;           // "Melhorar a qualidade" unfolded (idem)
  let renaming = false, renameDraft = null;   // the name's field is open (closed when another item opens); its text
  let hist = null;               // GK.router.detailHistory: the back gesture closes the detail (mount)

  /* ---------- persistence ---------- */
  function save() {
    try { window.sessionStorage.setItem(SKEY, JSON.stringify(V)); } catch (e) { /* storage blocked */ }
  }
  function restore() {
    try {
      const o = JSON.parse(window.sessionStorage.getItem(SKEY) || "null");
      if (!o || typeof o !== "object") return;
      const D = GK.data.get();
      if (typeof o.q === "string") V.q = o.q.slice(0, 80);
      if (typeof o.cat === "string") V.cat = o.cat;
      if (typeof o.st === "string") V.st = o.st;
      if (typeof o.item === "string" && D.items[o.item]) V.item = o.item;
      if (Array.isArray(o.stack)) V.stack = o.stack.filter((id) => typeof id === "string" && D.items[id]).slice(-30);
      if (typeof o.from === "string" && o.from !== "recipes" && GK.router.TABS.some((r) => r.id === o.from) && V.item) V.from = o.from;
    } catch (e) { /* corrupt or blocked */ }
  }
  const saveSoon = GK.util.debounce(save, 300);

  /* ---------- index (lazy) ---------- */
  const stKey = (s) => (!s ? "none" : s.build ? "build" : s.id);
  function buildIndex() {
    const D = GK.data.get();
    IX = { rows: {}, cats: {}, stations: { build: BUILD, none: NONE }, byStation: {}, memberOf: {} };
    for (const it of Object.values(D.items)) {
      if (it.stub) continue;
      const rs = GK.data.recipesFor(it.id), st = new Set();
      for (const r of rs) { st.add(stKey(r.station)); r.alt.forEach((a) => st.add(stKey(a))); }
      if (!rs.length) st.add("none");
      for (const k of st) if (!IX.stations[k]) IX.stations[k] = D.stations[k] || { id: k, pt: k, en: k };
      const cat = it.cat ? it.cat.en : "";
      if (!(cat in IX.cats)) IX.cats[cat] = it.cat || NOCAT;
      const main = (it.defaultRecipe && D.recipeById[it.defaultRecipe]) || rs[0] || null;
      IX.rows[it.id] = { id: it.id, cat, st: [...st], n: rs.length, main: main ? main.station : null, hidden: it.hidden };
      if (it.members) for (const m of it.members) (IX.memberOf[m] = IX.memberOf[m] || []).push(it.id);
    }
    for (const r of D.recipes) {
      const ids = new Set([r.station.id].concat(r.alt.map((a) => a.id)));
      for (const id of ids) (IX.byStation[id] = IX.byStation[id] || []).push(r);
    }
  }

  /* ---------- browse ---------- */
  function sortedIds(state) {
    const lang = GK.i18n.lang(), ov = state.overrides && state.overrides[lang];
    const key = lang + "|" + (ov ? JSON.stringify(ov) : "");
    if (sortCache.key === key) return sortCache.ids;
    const D = GK.data.get(), coll = new Intl.Collator(GK.i18n.meta(lang).locale, { sensitivity: "base", numeric: true });
    const label = {};
    for (const id in IX.rows) label[id] = name(D.items[id], state.overrides);
    const ids = Object.keys(IX.rows).sort((a, b) => coll.compare(label[a], label[b]));
    GK.data.gradeSort(ids, (id) => GK.data.family(D.items[id]), (id) => GK.data.GRADE_RANK[D.items[id].grade], true);
    sortCache = { key, ids };
    return sortCache.ids;
  }
  function compute(state) {
    const D = GK.data.get(), q = V.q.trim();
    const base = q
      ? GK.calc.search(q, D, { lang: GK.i18n.lang(), overrides: state.overrides, showHidden: true, limit: 100000 }).results.map((r) => r.id)
      : sortedIds(state);
    const catN = {}, stN = {}, out = [];
    let hiddenN = 0;
    for (const id of base) {
      const row = IX.rows[id];
      if (!row) continue;
      const okCat = !V.cat || row.cat === V.cat, okSt = !V.st || row.st.indexOf(V.st) >= 0;
      if (row.hidden && !state.showHidden) { if (okCat && okSt) hiddenN++; continue; }
      if (okSt) catN[row.cat] = (catN[row.cat] || 0) + 1;
      if (okCat) for (const k of row.st) stN[k] = (stN[k] || 0) + 1;
      if (okCat && okSt) out.push(row);
    }
    return { rows: out, catN, stN, hiddenN };
  }
  function chips(kind, counts, labels, selected, state) {
    const lbl = (k) => name(labels[k] || { pt: k, en: k }, state.overrides);
    let list = Object.keys(counts).filter((k) => counts[k] > 0 || k === selected);
    if (selected != null && list.indexOf(selected) < 0) list.push(selected);
    list.sort((a, b) => (b === selected) - (a === selected) || (counts[b] || 0) - (counts[a] || 0) || lbl(a).localeCompare(lbl(b)));
    const total = list.length, open = expanded[kind];
    if (!open) list = list.slice(0, CHIPS);
    const html = list.map((k) => `<button type="button" class="chip" data-chip="${kind}" data-key="${esc(k)}" aria-pressed="${k === selected}">${esc(lbl(k))} <span class="chip-n">${num(counts[k] || 0)}</span></button>`).join("");
    const more = total > CHIPS ? `<button type="button" class="chip chip-more" data-chip-more="${kind}" aria-expanded="${open}">${esc(open ? t("rc.less") : t("rc.all", { n: total }))}</button>` : "";
    return `<div class="chip-group" role="group" aria-labelledby="rc-${kind}-h"><h3 class="chip-h" id="rc-${kind}-h">${esc(t(kind === "cat" ? "rc.cat" : "rc.station"))}</h3><div class="chips">${html}${more}</div></div>`;
  }
  function rowHtml(row, state) {
    const D = GK.data.get(), it = D.items[row.id], nm = name(it, state.overrides);
    let sub;
    if (!row.n) sub = t("rc.raw");
    else {
      // with a station filter on, name that station (it may be an alternative, not the default one)
      const s = V.st && V.st !== "none" && stKey(row.main) !== V.st && IX.stations[V.st] ? IX.stations[V.st] : row.main;
      sub = GK.ui.fmt.buildLabel(s, state.overrides) + (row.n > 1 ? " · " + t("rc.recipes", { n: row.n }) : "");
    }
    const hid = row.hidden ? hiddenTag(it) : "";
    const g = graded(it, nm);
    return `<button type="button" class="rc-row" id="rc-row-${GK.util.domId(row.id)}" data-open="${esc(row.id)}" aria-label="${esc(t("rc.open", { name: nm }))}">
      ${slot(it, nm)}<span class="rc-row-main"><span class="rc-row-name">${esc(g.name)}${GK.ui.fmt.otherName(it)}${hid}</span><span class="rc-row-sub">${esc(g.word ? g.word + " · " + sub : sub)}</span></span><span class="rc-chev" aria-hidden="true">›</span></button>`;
  }
  function renderMore() {
    const left = results.length - shown;
    moreEl.hidden = left <= 0;
    if (left > 0) moreEl.textContent = t("rc.more", { n: left });
  }
  function updateList(reset) {
    const state = GK.store.get(), D = GK.data.get();
    if (reset) shown = PAGE;
    const c = compute(state);
    results = c.rows;
    chipsEl.innerHTML = chips("cat", c.catN, IX.cats, V.cat, state) + chips("st", c.stN, IX.stations, V.st, state);
    const nOn = (V.cat != null ? 1 : 0) + (V.st != null ? 1 : 0);
    filtersEl.querySelector(".rc-filters-n").textContent = nOn ? t("rc.filtersOn", { n: nOn }) : "";
    const active = [];
    if (V.cat != null) active.push(["cat", name(IX.cats[V.cat] || NOCAT, state.overrides)]);
    if (V.st != null) active.push(["st", name(IX.stations[V.st] || { pt: V.st, en: V.st }, state.overrides)]);
    const hiddenBtn = state.showHidden || c.hiddenN
      ? `<button type="button" class="hidden-toggle" id="rc-hidden" data-rc-hidden aria-pressed="${state.showHidden}">${esc(state.showHidden ? t("rc.hiddenShow") : t("rc.hiddenMore", { n: c.hiddenN }))}</button>` : "";
    metaEl.innerHTML = `<span class="rc-count tabnum" aria-live="polite">${esc(t("rc.count", { n: results.length }))}</span>` +
      active.map(([k, l]) => `<button type="button" class="chip chip-active" data-unfilter="${k}" aria-label="${esc(t("rc.removeFilter", { name: l }))}">${esc(l)} <span aria-hidden="true">×</span></button>`).join("") +
      (active.length > 1 ? `<button type="button" class="btn btn-sm btn-ghost" data-clear-filters>${esc(t("rc.clearFilters"))}</button>` : "");
    hiddenEl.innerHTML = hiddenBtn;   // a power-user switch: at the end of the list, after "Mostrar mais"
    hiddenEl.hidden = !hiddenBtn;
    listEl.innerHTML = results.length ? results.slice(0, shown).map((r) => rowHtml(r, state)).join("")
      : `<p class="rc-empty">${esc(V.q.trim() ? t("rc.noneQ", { q: V.q.trim() }) : t("rc.none"))}</p>`;
    renderMore();
  }
  function showMore() {
    const state = GK.store.get();
    listEl.insertAdjacentHTML("beforeend", results.slice(shown, shown + PAGE).map((r) => rowHtml(r, state)).join(""));
    const first = listEl.children[shown];
    shown += PAGE;
    renderMore();
    if (first) first.focus({ preventScroll: true });
  }
  function staticLabels() {
    input.placeholder = t("rc.placeholder");
    root.querySelector("#rc-q-label").textContent = t("rc.searchLabel");
    clearBtn.setAttribute("aria-label", t("rc.clear"));
    clearBtn.hidden = !input.value;
    root.querySelector(".rc-title").textContent = t("rc.title");
    filtersEl.querySelector(".rc-filters-t").textContent = t("rc.filters");
  }

  /* ---------- detail ---------- */
  const current = (id, state) => GK.calc.recipeFor(id, GK.data.get(), state.choice);
  // the detail header's tags; "não oficial" / "editado" is the rename button (see the header)
  function badges(it, state) {
    const b = [], ed = edited(it, state.overrides);
    if (ed || (GK.i18n.lang() !== "en" && UNOFFICIAL[it.tr])) {
      const title = t(ed ? "rc.editedTitle" : "rc.unofficialTitle") + " · " + t("rc.renameHint");
      b.push(`<button type="button" class="badge${ed ? " badge-edited" : ""} badge-btn" id="rc-rename" data-rename aria-expanded="${renaming}"${renaming ? ' aria-controls="rc-rename-box"' : ""} title="${esc(title)}" aria-label="${esc(t("rc.rename", { name: name(it, state.overrides) }))}">${esc(t(ed ? "rc.edited" : "rc.unofficial"))}<span class="badge-pen" aria-hidden="true">✎</span></button>`);
    }
    if (it.unobtainable) b.push(`<span class="badge badge-warn" title="${esc(t("rc.unobtTitle"))}">${esc(t("rc.unobt"))}</span>`);
    else if (it.hidden) b.push(`<span class="badge badge-hidden" title="${esc(t("rc.hiddenTitle"))}">${esc(t("rc.hidden"))}</span>`);
    return b.join("");
  }
  // the name's field, under the header, while renaming
  const editedCount = (state) => Object.values(state.overrides || {}).reduce((n, m) => n + Object.keys(m || {}).length, 0);
  function renameBox(it, nm, state) {
    if (!renaming) return "";
    const lang = GK.i18n.lang(), n = editedCount(state);
    return `<form class="edit-form rc-rename" id="rc-rename-box" data-rename-form>
        <input id="rc-rename-in" name="v" value="${esc(renameDraft == null ? nm : renameDraft)}" maxlength="80" autocomplete="off" spellcheck="false" aria-label="${esc(t("rc.renameInput", { name: it[lang] || it.en, lang: lang.toUpperCase() }))}">
        <button type="submit" class="btn btn-sm">${esc(t("rc.renameSave"))}</button>
        <button type="button" class="btn btn-sm btn-ghost" data-rename-cancel>${esc(t("rc.renameCancel"))}</button>
        ${edited(it, state.overrides) ? `<button type="button" class="btn btn-sm btn-ghost" id="rc-rename-reset" data-rename-reset>${esc(t("rc.renameReset"))}</button>` : ""}
        ${n ? `<p class="rc-rename-more"><button type="button" class="btn btn-sm btn-ghost" id="rc-export-names" data-export-names>${esc(t("rc.exportNames", { n: num(n) }))}</button></p>` : ""}
        <div class="rc-copy-box" id="rc-copy-box" hidden></div>
      </form>`;
  }
  // { "<English name>": { "pt": "…", source, confidence } }: keyed like the name files in data/
  function namesJson(state) {
    const D = GK.data.get(), out = {};
    for (const [lang, m] of Object.entries(state.overrides || {})) {
      for (const [id, v] of Object.entries(m || {})) {
        const it = D.items[id];
        if (!it || !v) continue;
        const e = (out[it.en] = out[it.en] || {});
        e[lang] = v;
        e.source = "user"; e.confidence = "guess";
      }
    }
    return JSON.stringify(out, null, 2);
  }
  function detailHtml(id, state) {
    const D = GK.data.get(), it = D.items[id], nm = name(it, state.overrides), lang = GK.i18n.lang();
    const other = lang === "en" ? it.pt : it.en;
    const prev = V.stack.length ? D.items[V.stack[V.stack.length - 1]] : null;
    const fromTab = V.from ? GK.router.TABS.find((r) => r.id === V.from) : null;
    const backTxt = prev ? t("rc.backTo", { name: name(prev, state.overrides) }) : fromTab ? t("rc.backTo", { name: t(fromTab.labelKey) }) : t("rc.back");
    const nav = `<nav class="rc-nav">
      <button type="button" class="btn btn-ghost rc-back" id="rc-back" data-back>${esc(backTxt)}</button>
      ${prev || fromTab ? `<button type="button" class="btn btn-sm btn-ghost" id="rc-tolist" data-tolist>${esc(t("rc.toList"))}</button>` : ""}</nav>`;
    const catTxt = [it.cat ? name(it.cat) : "", it.kind !== "item" ? t("rc.kind." + it.kind) : ""].filter(Boolean).join(" · ");
    const g = state.goals.find((x) => x.item === id);
    const goal = `<div class="rc-goal">
      <div class="stepper">
        <button type="button" id="rc-dec" data-qty-d="-1" aria-label="${esc(t("rc.dec"))}">−</button>
        <input id="rc-qty" type="number" inputmode="numeric" min="1" max="999" value="${addQty}" aria-label="${esc(t("rc.qty", { name: nm }))}">
        <button type="button" id="rc-inc" data-qty-d="1" aria-label="${esc(t("rc.inc"))}">+</button>
      </div>
      <button type="button" class="btn rc-add" id="rc-add" data-add-goal>${esc(t("rc.addGoal"))}</button>
      ${g ? `<a class="rc-ingoals" href="#plan">${esc(t("rc.inGoals", { n: g.qty }))} · ${esc(t("rc.toPlan"))}</a>` : ""}
    </div>`;
    const info = [];
    const rs = GK.data.recipesFor(id);
    const where = whereHtml(it, rs, state, whereAll);
    if (where) info.push(where);
    if (it.obtain && (!rs.length || it.raw || it.unobtainable)) info.push(`<div class="rc-info"><h3 class="rc-k">${esc(t("rc.obtain"))}</h3><p>${esc(name(it.obtain))}</p></div>`);
    if (it.runes) info.push(`<div class="rc-info"><h3 class="rc-k">${esc(t("rc.runes"))}</h3><div class="rc-runes">${runes(it.runes)}</div></div>`);
    const sell = sellHtml(it, state), study = studyHtml(it, state, id);
    if (sell) info.push(sell);
    if (study) info.push(study);
    if (it.members && it.members.length) info.push(`<div class="rc-info"><h3 class="rc-k">${esc(t("rc.members"))}</h3><ul class="rc-lines">${it.members.map((m) => itemLine(m, state)).join("")}</ul></div>`);
    const groups = IX.memberOf[id] || [];
    if (groups.length) info.push(`<div class="rc-info"><h3 class="rc-k">${esc(t("rc.memberOf"))}</h3><ul class="rc-lines">${groups.map((gid) => itemLine(gid, state)).join("")}</ul></div>`);

    const head = `<article class="card rc-item">
      <header class="rc-item-h">${stackSlot(it, nm)}<div class="rc-item-t">
        <h2 class="rc-name" id="rc-detail-h" tabindex="-1">${esc(GK.ui.fmt.gradedName(it, nm))}</h2>
        ${other && other !== nm ? `<p class="rc-other" lang="${lang === "en" ? "pt-BR" : "en"}">${esc(other)}</p>` : ""}
        ${catTxt ? `<p class="rc-cat">${esc(catTxt)}</p>` : ""}
        ${badges(it, state) ? `<div class="rc-badges">${badges(it, state)}</div>` : ""}
        ${stackCap(it)}
      </div></header>
      ${renameBox(it, nm, state)}${tipHtml(it)}${goal}${info.join("")}
    </article>`;

    const cur = current(id, state), many = rs.filter(expandable).length > 1;
    const chosen = state.choice[id] && cur && cur.id === state.choice[id] && cur.id !== it.defaultRecipe;
    // grouped cards (GK.calc.recipeGroups); the circular ones folded at the end; a letter only with 2+ cards;
    // "Todas também em" above the cards only with 2+ cards (one card says it inside)
    const G = GK.calc.recipeGroups(rs, D), nCards = G.cards.length;
    const shared = nCards > 1 ? sharedAlt(rs) : null;
    const cards = G.cards.map((c, i) => (c.group ? groupCard(c, nCards > 1 ? i : null, it, state, cur, !!shared)
      : recipeCard(c.r, nCards > 1 ? i : null, it, state, cur, many, !!shared))).join("");
    const cyc = G.cyc.length ? `<details class="rc-cyc" id="rc-cyc"${cycOpen ? " open" : ""}>
        <summary><span class="rc-cyc-t">${esc(t("rc.cycT"))} <span class="count">${G.cyc.length}</span></span><span class="rc-cyc-d">${esc(t("rc.cycD", { name: nm }))}</span><span class="rc-chev" aria-hidden="true">›</span></summary>
        <div class="rc-recipes">${G.cyc.map((r) => recipeCard(r, null, it, state, cur, many, !!shared, true)).join("")}</div>
      </details>` : "";
    // a group with no recipe of its own: its members (in the header card) already say how to get it
    const recipes = !rs.length && it.members ? "" : `<section class="rc-sec" aria-labelledby="rc-recipes-h">
      <div class="section-head"><h3 class="h2" id="rc-recipes-h">${esc(t("rc.recipesTitle"))} <span class="count">${nCards > 1 ? nCards : ""}</span></h3>
        ${chosen ? `<button type="button" class="btn btn-sm btn-ghost" id="rc-use-default" data-use-default>${esc(t("rc.useDefault"))}</button>` : ""}</div>
      ${shared ? `<p class="hint rc-alt-all">${esc(t("rc.altAll", { names: altNames(shared, state) }))}</p>` : ""}
      ${rs.length ? `<div class="rc-recipes">${cards}</div>${cyc}` : `<p class="hint">${esc(t("rc.noRecipes"))}</p>`}
    </section>`;

    // used in: direct consumers, then recipes that take a group this item belongs to
    const used = [];
    const seen = new Map();
    // one row per output + station + amount (eleven "Supplies: Vegetables" recipes collapse into one)
    const push = (r, qty, via) => {
      const k = [r.out.item, r.station.id, qty, via || ""].join("|");
      if (seen.has(k)) { seen.get(k).n++; return; }
      const u = { r, qty, via, n: 1 }; seen.set(k, u); used.push(u);
    };
    for (const r of D.usedIn[id] || []) push(r, r.in.find((l) => l.item === id).qty);
    for (const gid of groups) for (const r of D.usedIn[gid] || []) push(r, r.in.find((l) => l.item === gid).qty, gid);
    const loc = GK.i18n.meta(lang).locale;
    used.sort((a, b) => (D.items[a.r.out.item].hidden - D.items[b.r.out.item].hidden) ||
      name(D.items[a.r.out.item], state.overrides).localeCompare(name(D.items[b.r.out.item], state.overrides), loc));
    const outFam = (r) => GK.data.family(D.items[r.out.item]), outRank = (r) => GK.data.GRADE_RANK[D.items[r.out.item].grade];
    GK.data.gradeSort(used, (u) => outFam(u.r), (u) => outRank(u.r), true);
    const usedShow = usedAll ? used : used.slice(0, LIST_CAP);
    // nothing uses it: no section at all
    const usedHtml = !used.length ? "" : `<section class="rc-sec" aria-labelledby="rc-used-h">
      <h3 class="h2" id="rc-used-h">${esc(t("rc.usedIn"))} <span class="count">${used.length}</span></h3>
      <div class="card list"><ul class="rc-lines rc-lines-card">${usedShow.map((u) => itemLine(u.r.out.item, state,
        [stationLabel(u.r.station, state), t("rc.uses", { n: u.qty }), u.via ? t("rc.via", { group: name(D.items[u.via], state.overrides) }) : "", u.n > 1 ? t("rc.recipes", { n: u.n }) : ""].filter(Boolean).join(" · "))).join("")}</ul>
        ${used.length > usedShow.length ? `<button type="button" class="btn btn-ghost rc-more" id="rc-used-more" data-used-more>${esc(t("rc.showAll", { n: used.length }))}</button>` : ""}</div>
    </section>`;

    // a station item: what is made there
    let here = "";
    // bronze, prata, ouro together (Canteiro de Repolho: Repolho, Repolho (prata), Repolho (ouro))
    const made = D.stations[id] ? GK.data.gradeSort((IX.byStation[id] || []).slice(), outFam, outRank, true) : [];
    if (made.length) {
      const list = hereAll ? made : made.slice(0, LIST_CAP);
      here = `<section class="rc-sec" aria-labelledby="rc-here-h">
        <h3 class="h2" id="rc-here-h">${esc(t("rc.madeHere"))} <span class="count">${made.length}</span></h3>
        <div class="card list"><ul class="rc-lines rc-lines-card">${list.map((r) => itemLine(r.out.item, state,
          r.in.map((l) => `${num(l.qty)} ${name(D.items[l.item], state.overrides)}`).join(" + ") + (r.out.qty ? " → " + num(r.out.qty) : ""))).join("")}</ul>
          ${made.length > list.length ? `<button type="button" class="btn btn-ghost rc-more" id="rc-here-more" data-here-more>${esc(t("rc.showAll", { n: made.length }))}</button>` : ""}</div>
      </section>`;
    }
    return nav + `<div class="rc-detail-grid"><div class="rc-detail-a">${head}</div><div class="rc-detail-b">${recipes}${usedHtml}${askedHtml(it, state, askedOpen)}${here}</div></div>`;
  }
  function renderDetail(state) {
    if (!V.item || !GK.data.item(V.item)) { V.item = null; return false; }
    // a re-render while typing a new name (a sync, say) keeps the field's text (renameDraft) and its focus
    const typing = renaming && document.activeElement && document.activeElement.id === "rc-rename-in";
    detailEl.innerHTML = detailHtml(V.item, state);
    if (typing) { const i = document.getElementById("rc-rename-in"); if (i) i.focus({ preventScroll: true }); }
    return true;
  }

  /* ---------- navigation ---------- */
  // another item opens: quantity 1, the long lists short, "Pedido em" and the circular recipes folded, no rename field
  function resetItemView() {
    addQty = 1; usedAll = false; hereAll = false; whereAll = false; askedOpen = false; cycOpen = false; renaming = false; renameDraft = null;
  }
  const visible = () => GK.router.tab(GK.router.current()).screen === "recipes";
  function showView(state, focusDetail) {
    const hasDetail = V.item && renderDetail(state);
    browseEl.hidden = !!hasDetail;
    detailEl.hidden = !hasDetail;
    if (!hasDetail) { detailEl.innerHTML = ""; updateList(false); }
    if (hasDetail && focusDetail) {
      window.scrollTo(0, 0);
      const h = document.getElementById("rc-detail-h"); if (h) h.focus({ preventScroll: true });
    }
  }
  function openItem(id, fromList) {
    if (!GK.data.item(id)) return;
    if (!IX) buildIndex();
    if (V.item === id) return;
    if (fromList || !V.item) { listScroll = browseEl.hidden ? listScroll : window.scrollY; V.stack = []; V.from = null; }
    else { V.stack.push(V.item); if (V.stack.length > 30) V.stack.shift(); }
    V.item = id; resetItemView();
    save();
    if (hist) hist.push();
    showView(GK.store.get(), true);
  }
  // back to the screen that opened the detail (GK.ui.recipes.open(id, {from})), where it was
  function backToOrigin() {
    const route = V.from, item = V.item;
    V.item = null; V.stack = []; V.from = null;
    save();
    returnTo = { route, y: fromScroll, item };
    location.hash = route;
  }
  function back(toList) {
    const from = V.item;
    if (!toList && !V.stack.length && V.from) { backToOrigin(); return; }
    if (toList) V.from = null;
    if (!toList && V.stack.length) {
      V.item = V.stack.pop(); resetItemView();
      save(); showView(GK.store.get(), true);
      return;
    }
    V.item = null; V.stack = []; renaming = false; renameDraft = null;
    save();
    showView(GK.store.get(), false);
    window.scrollTo(0, listScroll);
    const row = from && document.getElementById("rc-row-" + GK.util.domId(from));
    if (row) row.focus({ preventScroll: true });
  }
  // deep link from other modules: GK.ui.recipes.open("crate", {from: "plan"})
  function open(itemId, opts) {
    if (!GK.data.item(itemId)) return false;
    if (!IX) buildIndex();
    const cur = GK.router.current();
    const from = opts && opts.from && opts.from !== "recipes" && cur !== "recipes" ? opts.from : null;
    if (from) fromScroll = window.scrollY;
    if (V.item !== itemId || from || V.stack.length) {
      V.stack = []; V.item = itemId; resetItemView();
      V.from = from;
      save();
    }
    if (cur !== "recipes") { pendingFocus = true; location.hash = "recipes"; }
    else showView(GK.store.get(), true);
    return true;
  }

  /* ---------- events ---------- */
  function onClick(e) {
    const A = GK.store.actions;
    const el = e.target.closest("button, a");
    if (!el || !root.contains(el)) return;
    const d = el.dataset;
    if (d.open) { openItem(d.open, !!el.closest(".rc-browse")); return; }
    if ("back" in d) { back(false); if (hist) hist.pop(false); return; }
    if ("tolist" in d) { back(true); if (hist) hist.pop(true); return; }
    if (d.chip) {
      const k = d.key, f = d.chip === "cat" ? "cat" : "st";
      V[f] = V[f] === k ? null : k;
      save(); updateList(true);
      const again = chipsEl.querySelector(`[data-chip="${d.chip}"][data-key="${CSS.escape(k)}"]`);
      if (again) again.focus({ preventScroll: true });
      return;
    }
    if (d.chipMore) { expanded[d.chipMore] = !expanded[d.chipMore]; updateList(false); const b = chipsEl.querySelector(`[data-chip-more="${d.chipMore}"]`); if (b) b.focus({ preventScroll: true }); return; }
    if (d.unfilter) { V[d.unfilter] = null; save(); updateList(true); input.focus({ preventScroll: true }); return; }
    if ("clearFilters" in d) { V.cat = null; V.st = null; save(); updateList(true); return; }
    if ("rcHidden" in d) { A.setShowHidden(!GK.store.get().showHidden); const b = document.getElementById("rc-hidden"); if (b) b.focus({ preventScroll: true }); return; }
    if (el === moreEl) { showMore(); return; }
    if (el === clearBtn) { input.value = ""; V.q = ""; save(); clearBtn.hidden = true; updateList(true); input.focus(); return; }
    if (d.qtyD) { const i = document.getElementById("rc-qty"); addQty = GK.store.clampQty((+i.value || 1) + +d.qtyD); i.value = addQty; return; }
    if ("addGoal" in d) {
      const i = document.getElementById("rc-qty"); addQty = GK.store.clampQty(i ? i.value : addQty);
      const s0 = GK.store.get(), before = s0.goals.find((g) => g.item === V.item);
      // the first goal replaces the seeded example: search.js shows one toast with "Desfazer" (meta.exampleReplaced)
      const replacesExample = !!(s0.example && s0.goals.length);
      const n = A.addGoal(V.item, addQty);
      const nm = name(GK.data.item(V.item), GK.store.get().overrides);
      if (!replacesExample) GK.ui.toast(before ? t("rc.bumped", { name: nm, n }) : t("rc.added", { name: nm, n }));
      const b = document.getElementById("rc-add"); if (b) b.focus({ preventScroll: true });
      return;
    }
    if (d.use) {
      const r = GK.data.recipe(d.use); if (!r) return;
      A.chooseRecipe(r.out.item, r.id === GK.data.item(r.out.item).defaultRecipe ? null : r.id);
      GK.ui.toast(t("rc.used", { station: name(r.station, GK.store.get().overrides), name: name(GK.data.item(r.out.item), GK.store.get().overrides) }));
      return;
    }
    // a grade / ingredient option of a group card: the planner uses it from now on (the "✓ Em uso" line says so)
    if (d.pick) {
      const r = GK.data.recipe(d.pick); if (!r || el.getAttribute("aria-checked") === "true") return;
      A.chooseRecipe(r.out.item, r.id === GK.data.item(r.out.item).defaultRecipe ? null : r.id);
      const b = document.getElementById(el.id); if (b) b.focus({ preventScroll: true });
      return;
    }
    if ("useDefault" in d) { A.chooseRecipe(V.item, null); GK.ui.toast(t("rc.usedDefault", { name: name(GK.data.item(V.item), GK.store.get().overrides) })); return; }
    if ("usedMore" in d) { usedAll = true; renderDetail(GK.store.get()); return; }
    if ("hereMore" in d) { hereAll = true; renderDetail(GK.store.get()); return; }
    if ("whereMore" in d) { whereAll = true; renderDetail(GK.store.get()); const l = root.querySelector(".rc-where-list li:nth-child(5)"); if (l) { l.tabIndex = -1; l.focus({ preventScroll: true }); } return; }
    if (d.tech && GK.ui.tech && typeof GK.ui.tech.open === "function") { GK.ui.tech.open(d.tech, { from: "recipes" }); return; }
    if ("rename" in d) { renaming = !renaming; renameDraft = null; renderDetail(GK.store.get()); if (renaming) focusEl("rc-rename-in", true); else focusEl("rc-rename"); return; }
    if ("renameCancel" in d) { closeRename(); return; }
    if ("renameReset" in d) { saveName(""); return; }
    if ("exportNames" in d) { exportNames(); return; }
  }
  const focusEl = (id, select) => { const el = document.getElementById(id); if (el) { el.focus({ preventScroll: true }); if (select && el.select) el.select(); } return !!el; };
  // back to the tag (or the heading, when the name is official again)
  function closeRename() {
    renaming = false; renameDraft = null; renderDetail(GK.store.get());
    if (!focusEl("rc-rename")) focusEl("rc-detail-h");
  }
  // the field's text: blank or the original = the original name back; the same name = nothing to do
  function saveName(raw) {
    const it = GK.data.item(V.item); if (!it) return;
    const lang = GK.i18n.lang(), st = GK.store.get(), v = String(raw || "").trim(), original = it[lang] || it.en;
    const cur = name(it, st.overrides), wasEdited = edited(it, st.overrides), keep = v && v !== original;
    renaming = false; renameDraft = null;
    if (v !== cur && (keep || wasEdited)) {
      GK.store.actions.setOverride(lang, V.item, keep ? v : "");
      GK.ui.toast(t(keep ? "rc.renamed" : "rc.renameRestored", { name: keep ? v : original }));
    }
    renderDetail(GK.store.get());
    if (!focusEl("rc-rename")) focusEl("rc-detail-h");
  }
  async function exportNames() {
    const txt = namesJson(GK.store.get());
    if (await GK.util.copyText(txt)) { GK.ui.toast(t("rc.exportCopied")); return; }
    const box = document.getElementById("rc-copy-box"); if (!box) return;
    box.hidden = false;
    box.innerHTML = `<p class="hint">${esc(t("rc.exportFail"))}</p><textarea class="copy-fallback" readonly aria-label="${esc(t("rc.exportCopied"))}"></textarea>`;
    const ta = box.querySelector("textarea"); ta.value = txt; ta.focus(); ta.select();
  }

  function mount(el) {
    root = el;
    root.classList.add("rc-screen");
    root.innerHTML = `<div class="rc-browse">
        <div class="rc-top">
          <h2 class="h2 rc-title"></h2>
          <div class="search-box rc-search">
            <svg width="18" height="18" viewBox="0 0 9 9" aria-hidden="true" shape-rendering="crispEdges"><path fill="currentColor" d="M2 0h3v1H2zM1 1h1v1H1zM5 1h1v1H5zM0 2h1v3H0zM6 2h1v3H6zM1 5h1v1H1zM5 5h1v1H5zM2 6h3v1H2zM6 6h1v1H6zM7 7h1v1H7zM8 8h1v1H8z"/></svg>
            <label class="sr-only" for="rc-q" id="rc-q-label"></label>
            <input id="rc-q" class="search-input" type="search" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search">
            <button type="button" class="search-clear" id="rc-q-clear" hidden>×</button>
          </div>
        </div>
        <div class="rc-layout">
          <details class="card rc-filters" id="rc-filters"><summary><span class="rc-filters-t"></span> <span class="rc-filters-n"></span></summary><div class="rc-chips"></div></details>
          <div class="rc-results">
            <div class="rc-meta-row"></div>
            <div class="card list rc-list"></div>
            <button type="button" class="btn rc-more" id="rc-more" hidden></button>
            <div class="rc-hidden-end" hidden></div>
          </div>
        </div>
      </div>
      <div class="rc-detail" hidden></div>`;
    browseEl = root.querySelector(".rc-browse"); detailEl = root.querySelector(".rc-detail");
    input = root.querySelector("#rc-q"); clearBtn = root.querySelector("#rc-q-clear");
    listEl = root.querySelector(".rc-list"); chipsEl = root.querySelector(".rc-chips"); metaEl = root.querySelector(".rc-meta-row");
    moreEl = root.querySelector("#rc-more"); filtersEl = root.querySelector("#rc-filters"); hiddenEl = root.querySelector(".rc-hidden-end");
    restore();
    input.value = V.q;
    // filters open beside the list on wide screens, folded on phones
    const wide = window.matchMedia ? window.matchMedia("(min-width: 900px)") : null;
    if (wide) {
      filtersEl.open = wide.matches;
      const onWide = () => { if (wide.matches) filtersEl.open = true; };
      if (wide.addEventListener) wide.addEventListener("change", onWide); else if (wide.addListener) wide.addListener(onWide);
    }
    const typed = GK.util.debounce(() => { V.q = input.value; saveSoon(); updateList(true); }, 90);
    input.addEventListener("input", () => { clearBtn.hidden = !input.value; typed(); });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && input.value) { input.value = ""; V.q = ""; save(); clearBtn.hidden = true; updateList(true); }
      else if (e.key === "Enter") { e.preventDefault(); V.q = input.value; save(); updateList(true); input.blur(); }
    });
    root.addEventListener("click", onClick);
    hist = GK.router.detailHistory("recipes", () => { if (V.item && !detailEl.hidden) back(false); });
    // back on the screen that opened the detail: its old scroll position, focus on the opener (after its render)
    GK.router.onChange((id) => {
      if (!returnTo || id !== returnTo.route) { if (id !== "recipes") returnTo = null; return; }
      const r = returnTo; returnTo = null;
      setTimeout(() => {
        window.scrollTo(0, r.y);
        const scr = document.querySelector(`[data-screen="${GK.router.tab(r.route).screen}"]`);
        const b = scr && r.item && scr.querySelector(`[data-recipe-open="${CSS.escape(r.item)}"]`);
        if (b) b.focus({ preventScroll: true });
      }, 0);
    });
    root.addEventListener("submit", (e) => {
      const f = e.target.closest("[data-rename-form]");
      if (f) { e.preventDefault(); saveName(f.elements.v.value); }
    });
    root.addEventListener("input", (e) => {
      if (e.target.id === "rc-rename-in") renameDraft = e.target.value;
      if (e.target.id === "rc-qty" && e.target.value !== "") addQty = GK.store.clampQty(e.target.value);
    });
    root.addEventListener("change", (e) => {
      if (e.target.id === "rc-qty") { addQty = GK.store.clampQty(e.target.value); e.target.value = addQty; }
      // "Já estudei": the store re-renders the detail; the box gets the focus back
      if (e.target.id === "rc-studied" && e.target.dataset.studied) {
        GK.store.actions.setStudied(e.target.dataset.studied, e.target.checked);
        const b = document.getElementById("rc-studied"); if (b) b.focus({ preventScroll: true });
      }
    });
    // "Pedido em" stays open across re-renders of the same item (toggle does not bubble: capture)
    root.addEventListener("toggle", (e) => { if (e.target.id === "rc-asked") askedOpen = e.target.open; if (e.target.id === "rc-cyc") cycOpen = e.target.open; }, true);
    // the price "i": one open at a time; a tap anywhere else closes it
    document.addEventListener("click", (e) => {
      if (!root) return;
      root.querySelectorAll("details.rc-i[open]").forEach((d) => { if (!d.contains(e.target)) d.open = false; });
    });
    root.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.id === "rc-qty") { e.preventDefault(); const b = document.getElementById("rc-add"); if (b) b.click(); }
      if (e.key === "Escape" && e.target.closest("[data-rename-form]")) { e.preventDefault(); closeRename(); return; }
      // the grade options: the arrows move between them (a radio group); Enter / Space picks
      const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
      if (step && e.target.getAttribute && e.target.getAttribute("role") === "radio" && e.target.closest(".qpick")) {
        const all = [...e.target.closest(".qpick").querySelectorAll('[role="radio"]')], i = all.indexOf(e.target);
        const next = all[(i + step + all.length) % all.length];
        if (next) { e.preventDefault(); next.focus(); }
      }
    });
  }
  let wasHere = false;
  function render(state, meta) {
    const here = visible();
    if (!here) { wasHere = false; return; }
    if (!IX) buildIndex();
    staticLabels();
    const entering = !wasHere;
    wasHere = true;
    showView(state, false);
    // entering: an open detail starts at its top; the list is where GK.router left it (its per-screen scroll memory)
    if (entering && meta && meta.from === "router" && V.item) window.scrollTo(0, 0);
    if (pendingFocus) {
      pendingFocus = false;
      const h = V.item && document.getElementById("rc-detail-h");
      if (h) h.focus({ preventScroll: true });
    }
  }
  return { mount, render, open };
})();

GK.router.register({ id: "recipes", labelKey: "rc.tab", screen: "recipes", order: 20, tab: true });
GK.app.registerPanel(GK.ui.recipes, { id: "recipes", panel: "recipes", order: 62 });
