/* GK.ui.fmt: shared bits of markup for item names, recipes and stations (badges, recipe labels,
   tech lines, the name block) and the "Desfazer" toast. No state, no panel.
   Exposes: GK.ui.fmt.{badges, buildLabel, stationOf, recipeLabel, recipeLabels, recipeTag, techLine, nameBlock, slotButton, undoToast, otherName, graded, gradedName, foldBtn, CONTROLS,
   recipeClick, UNOFFICIAL}.
   slotButton(item, name): the item's icon as a 44 px button (data-recipe-open) that opens it in Receitas; every
   panel that shows one sends the click to recipeClick(e, from) (from = "plan", "tech", "days").
   techLine(r, state) leaves out the words "Requer" / "Maestria:" / "Extensão:" and the technologies already
   researched; stationOf reads "Construir no Cemitério" (buildLabel); recipeLabels can leave out one station.
   undoToast(msg, onUndo): a toast with a "Desfazer" button (its own #toast-undo element, created on first use, after
   #toast in <body>; it sits above #toast when both show). 6 s, paused while it holds the focus or the pointer.
   "Desfazer" also hides the plain toast ("Adicionado às metas" must not stay after the undo).
   slotButton keeps the quality star of a graded item (GK.util.slot's has-q).
   otherName(item): two items with the same name in the page's language ("Tinta" = Ink and
   Paint) show the other language's name, small, beside it (search, Receitas list, goals); "" for any other item.
*/
GK.ui.fmt = (function () {
  const { t, name, edited, num } = GK.i18n, { esc } = GK.util;
  const UNOFFICIAL = { guess: 1, machine: 1, missing: 1 };   // the name's tr values that get the "não oficial" badge
  function badges(it, overrides) {
    if (edited(it, overrides)) return `<span class="badge badge-edited" title="${esc(t("badge.editedTitle"))}">${esc(t("badge.edited"))}</span>`;
    if (GK.i18n.lang() !== "en" && UNOFFICIAL[it.tr]) return `<span class="badge" title="${esc(t("badge.unofficialTitle"))}">${esc(t("badge.unofficial"))}</span>`;
    return "";
  }
  // "Construir no Cemitério" / "Build at Graveyard": the label of a build pseudo-station
  // (GK.data zoneStation: build: true + the zone's {pt, en}). pt needs the gender of the place; a zone that lists
  // several places ("Pátio, Cemitério, …") reads "Construir em: …"; the generic one (no zone) keeps "station.build".
  // A regular station returns its plain name.
  const PLACE_F = { "Fábrica": 1, "Igreja": 1, "Casa": 1, "Adega do Vinhedo": 1, "Serraria": 1, "Pedreira": 1, "Margem do Rio": 1, "Mina Antiga": 1, "Aldeia": 1 };
  const PLACE_FP = { "Casernas": 1 };
  function buildLabel(station, overrides) {
    if (!station) return "";
    if (!station.build) return name(station, overrides);
    if (station.i18n) return t("station.build");
    const nm = name(station, overrides);
    if (/anywhere|qualquer lugar/i.test(station.en || nm)) return t("station.buildAnywhere");
    if (nm.indexOf(",") >= 0) return t("station.buildList", { places: nm });
    const g = PLACE_FP[nm] ? "fp" : PLACE_F[nm] ? "f" : "m";
    return t("station.buildIn." + g, { place: nm });
  }
  // station label of the recipe the planner would use for this item (for search / goals sub-lines)
  function stationOf(id, state) {
    const D = GK.data.get();
    const h = GK.calc.howToMake(id, D, state.choice, state.have, state.perks);
    const rs = GK.data.recipesFor(id);
    if (!h.r) return t("search.raw");
    const label = buildLabel(h.r.station, state.overrides);
    return rs.length > 1 ? t("search.recipes", { station: label, n: rs.length }) : label;
  }
  // what sets a recipe apart from its siblings: its own name ("Board (Sawhorse)"). "<X> from <Y>" names only restate
  // the inputs the label already lists: left out. recipeLabels adds the name back when two options would otherwise
  // read the same. No grade word: the graded ingredient ("2 Abóbora (ouro)") already sets a quality recipe apart,
  // and the grade of the result is the item's own (its name and star).
  function recipeTag(r) {
    return r.name && !/ from /i.test(r.name.en || "") ? name(r.name) : "";
  }
  // quantity of a line / the output under the viewer's perks
  function qtyOf(base, b, state) {
    if (!b || !GK.calc.isBonusActive(b, state.perks)) return base;
    if (b.qty != null) return b.qty;
    return b.add != null && base != null ? base + b.add : base;
  }
  // short, in the UI language, ingredients first (no letter, no English recipe name), so a closed <select>
  // cut at ~180 px still shows what goes in: "1 Tora → 4 · Cavalete",
  // "2 Abóbora (ouro) + 10 Combustível → 7 · Forno da Cozinha (oculta, circular)".
  // opts.noStation: leave the station out (every option of the list uses the same one: the card already says it).
  function recipeLabel(r, idx, state, opts) {
    const D = GK.data.get();
    const ins = r.in.length ? r.in.map((i) => `${num(qtyOf(i.qty, i.bonus, state))}\u00a0${name(D.items[i.item], state.overrides)}`).join(" + ") : "—";
    const tags = [];
    if (!r.listed) tags.push(t("recipe.hidden"));
    if (r.cyc) tags.push(t("recipe.cyc"));
    if (r.example) tags.push(t("steps.example"));
    const out = qtyOf(r.out.qty, r.out.bonus, state);
    const st = opts && opts.noStation ? "" : " · " + name(r.station, state.overrides);
    return `${ins}${out ? " → " + num(out) : ""}${st}${tags.length ? " (" + tags.join(", ") + ")" : ""}`;
  }
  // labels for a list of options (`all` = the item's full list, kept for callers). The station is left out when
  // every option uses the same one, or (opts.omitStation = a station id) on the options made at that station: the
  // step's card already names it. Two options never read the same: a repeat gets a short tag, then a number.
  // The tag is the recipe's own name cut before " from ": the whole "Improve organ I from Any Skin" would make the Pele
  // selector 440-640 px wide on a 390 px phone; the cut keeps "Improve organ I" / "Improve organ II" apart.
  // A pt recipe name is cut before " a partir de " the same way: "Aprimorar Órgão I".
  function shortTag(r) {
    const n = r.name ? name(r.name) : "";
    const cut = n.split(/ from | a partir de /i)[0].trim();
    return cut.length > 28 ? cut.slice(0, 27).trimEnd() + "…" : cut;
  }
  function recipeLabels(list, state, all, opts) {
    const sid = (r) => (r.station && (r.station.id || r.station.en)) || "";
    const noStation = list.length > 1 && list.every((r) => sid(r) === sid(list[0]));
    const omit = opts && opts.omitStation;
    const out = list.map((r, k) => recipeLabel(r, k, state, { noStation: noStation || (omit != null && sid(r) === omit) }));
    const dup = (k) => out.some((x, j) => j !== k && x === out[k]);
    const extra = out.map((s, k) => (dup(k) && list[k].name && !list[k].quality && shortTag(list[k]) ? " — " + shortTag(list[k]) : ""));
    extra.forEach((x, k) => { out[k] += x; });
    const nth = out.map((s, k) => (dup(k) ? " #" + (k + 1) : ""));
    nth.forEach((x, k) => { out[k] += x; });
    return out;
  }
  // what a recipe needs, short: "Olaria I · Engenharia 2 · Foles de ferraria". No "Requer",
  // "Maestria:" or "Extensão:"; quests and perks keep "Missão:" / "Vantagem:" (their names alone read like items).
  // A technology already researched (GK.tech.researchedSet: marked + ancestors) is left out; a mastery of level 0
  // shows only its type. state is optional (no state: nothing is left out).
  // (the store edits state.researched in place: the memo key is its list of marked ids)
  let resMemo = { key: null, set: null };
  function researched(state) {
    const r = state && state.researched;
    if (!r || !GK.tech || typeof GK.tech.researchedSet !== "function" || !GK.tech.available()) return null;
    const key = Object.keys(r).filter((k) => r[k]).join(",");
    if (resMemo.key !== key) resMemo = { key, set: GK.tech.researchedSet(r) };
    return resMemo.set;
  }
  function techLine(r, state) {
    const out = [], done = researched(state);
    if (r.tech) {
      const type = r.tech.type;
      if (type === "quest") out.push(t("steps.techQuest", { tech: name(r.tech) }));
      else if (type === "perk") out.push(t("steps.techPerk", { tech: name(r.tech) }));
      else if (!(done && r.tech.id && done.has(r.tech.id))) out.push(name(r.tech));
    }
    if (r.mastery) {
      const ty = name(r.mastery.type), lv = r.mastery.level;
      out.push(lv ? `${ty} ${lv}` : ty);
    }
    if (r.ext) out.push(name(r.ext));
    return out.filter(Boolean);
  }
  // the item's icon as a button: opens the item on the Receitas screen. Same
  // markup as GK.util.slot, in a <button> with the "Abrir X em Receitas" label; a plain icon when there is no Receitas.
  function slotButton(it, nm) {
    const s = GK.util.slot(it, nm), m = /^<span class="slot( has-q)?">/.exec(s);
    if (!it || !GK.ui.recipes || typeof GK.ui.recipes.open !== "function" || !m) return s;
    return `<button type="button" class="slot slot-btn${m[1] || ""}" data-recipe-open="${esc(it.id)}" title="${esc(t("info.title"))}" aria-label="${esc(t("info.label", { name: nm }))}">` +
      s.slice(m[0].length, -"</span>".length) + "</button>";
  }
  // the 44 px fold toggle at a header's right (Matérias-primas, Etapas and their station cards, Hoje, Tecnologias que
  // faltam). attrs = its stable id and data-* hook (`id="fold-raw" data-fold="raw"`), so the focus survives a
  // re-render. sec = a section: the thin chevron with no box (.sec-fold > .sec-chev); else the boxed .fold-btn of a
  // card (chevron drawn in CSS)
  function foldBtn(attrs, open, label, bodyId, sec) {
    return `<button type="button" class="${sec ? "sec-fold" : "btn fold-btn"}" ${attrs} aria-expanded="${open}" aria-controls="${bodyId}" title="${esc(t(open ? "fold.collapse" : "fold.expand"))}" aria-label="${esc(t(open ? "fold.collapseX" : "fold.expandX", { name: label }))}">${sec ? `<span class="sec-chev" aria-hidden="true"></span>` : ""}</button>`;
  }
  // a tap on a fold header folds it, unless it lands on one of these
  const CONTROLS = "button, a, input, select, textarea, label";
  // a click on one of those icons (or any [data-recipe-open], the Dias item chips too): opens the item in Receitas,
  // with "‹ Voltar" to `from` (the route the click came from). true when it was one (the caller stops there)
  function recipeClick(e, from) {
    const ro = e.target.closest("[data-recipe-open]");
    if (!ro) return false;
    GK.ui.recipes.open(ro.dataset.recipeOpen, { from });
    return true;
  }
  // the name (plain text: only the checkbox and its 44 px .tick box toggle "done") and its badges. Renaming is in
  // the item's Receitas detail (ui/recipes.js), not here.
  function nameBlock(it, nm, extraBadges, overrides) {
    return `<span class="row-name"><span class="row-label">${esc(nm)}</span>${extraBadges || ""}${badges(it, overrides)}</span>`;
  }
  // "Areia: você já tem tudo [Desfazer]": the undo toast (see the header)
  let undoTimer = null;
  function undoToast(msg, onUndo) {
    if (typeof document === "undefined") return;
    let el = document.getElementById("toast-undo");
    const hide = () => { clearTimeout(undoTimer); if (el) { el.hidden = true; el._undo = null; } };
    const arm = () => { clearTimeout(undoTimer); undoTimer = setTimeout(hide, 6000); };
    if (!el) {
      el = document.createElement("div");
      el.id = "toast-undo"; el.className = "toast toast-undo"; el.hidden = true;
      el.setAttribute("role", "status"); el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
      el.addEventListener("click", (e) => {
        if (!e.target.closest("[data-undo]")) return;
        const f = el._undo; hide();
        const plain = document.getElementById("toast");
        if (plain) plain.hidden = true;
        if (typeof f === "function") f();
      });
      // WCAG 2.2.1: no time-out while the player is on it
      el.addEventListener("focusin", () => clearTimeout(undoTimer));
      el.addEventListener("pointerenter", () => clearTimeout(undoTimer));
      el.addEventListener("focusout", () => { if (!el.hidden) arm(); });
      el.addEventListener("pointerleave", () => { if (!el.hidden) arm(); });
    }
    el.innerHTML = `<span class="toast-msg">${esc(msg)}</span><button type="button" class="btn btn-sm toast-undo-btn" id="toast-undo-btn" data-undo>${esc(t("undo.button"))}</button>`;
    el._undo = onUndo; el.hidden = false;
    const plain = document.getElementById("toast");
    if (plain) plain.hidden = true;
    arm();
  }
  // names shared by 2+ items in a language (the data's own names; stubs left out), built on first use per language
  const dupMemo = {};
  function dupSet(lang) {
    if (dupMemo[lang]) return dupMemo[lang];
    const seen = {}, out = new Set();
    for (const it of Object.values(GK.data.get().items || {})) {
      if (it.stub) continue;
      const k = String(it[lang] || it.en || "").trim().toLowerCase();
      if (!k) continue;
      if (seen[k]) { out.add(seen[k]); out.add(it.id); } else seen[k] = it.id;
    }
    return (dupMemo[lang] = out);
  }
  function otherName(it) {
    const lang = GK.i18n.lang(), other = lang === "en" ? "pt" : "en";
    if (!it || !dupSet(lang).has(it.id) || !it[other] || it[other] === it[lang]) return "";
    return ` <span class="name-other" lang="${other === "pt" ? "pt-BR" : "en"}">${esc(it[other])}</span>`;
  }
  // a graded item in a list (search, Receitas): the name without "(prata)" and the grade word for the line below (the
  // star is on the icon; colour alone is not enough). grade = a recipe line's own grade (the bronze plain Repolho);
  // false = none (an "Any X" line). The plain item of a graded family is the bronze one (build.py apply_grades)
  function graded(it, nm, grade) {
    const g = grade === false ? null : grade || GK.data.itemGrade(it);
    return g ? { name: GK.data.stripGrade(nm) || nm, word: t("quality." + g), grade: g } : { name: nm, word: "", grade: null };
  }
  // the whole name of a graded item where it shows on one line (the Recentes, the Receitas detail title): "Abóbora
  // (prata)" is already that; the plain bronze one gets its word too, "Abóbora (bronze)"
  function gradedName(it, nm) {
    const g = GK.data.itemGrade(it);
    return g && GK.data.stripGrade(nm) === nm ? `${nm} (${t("quality." + g)})` : nm;
  }
  return { badges, buildLabel, stationOf, recipeLabel, recipeLabels, recipeTag, techLine, nameBlock, slotButton, undoToast, otherName, graded, gradedName, foldBtn, CONTROLS, recipeClick, UNOFFICIAL };
})();
