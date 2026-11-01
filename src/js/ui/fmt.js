/* GK.ui.fmt: shared bits of markup for item names, recipes and stations (badges, recipe labels,
   tech lines, the editable name block) and the "Desfazer" toast. No state, no panel.
   Exposes: GK.ui.fmt.{badges, buildLabel, stationOf, recipeLabel, recipeLabels, recipeTag, techLine, nameBlock, slotButton, undoToast}.
   slotButton(item, name): the item's icon as a 44 px button (data-recipe-open) that opens it in Receitas; every planner
   panel that shows one handles the click itself (GK.ui.recipes.open(id, {from: "plan"})).
   1.6.0: the "i" button left the planner names (corte 6: the icon opens the recipe); techLine(r, state) drops the
   words "Requer" / "Maestria:" / "Extensão:" and the technologies already researched (corte 2); stationOf reads
   "Construir no Cemitério" (buildLabel, corte 12); recipeLabels can leave out one station (corte 3).
   undoToast(msg, onUndo): a toast with a "Desfazer" button (its own #toast-undo element, created on first use, after
   #toast in <body>; it sits above #toast when both show). 6 s, paused while it holds the focus or the pointer.
*/
GK.i18n.add({
  pt: {
    "recipe.hidden": "oculta",
    "recipe.cyc": "circular",
    "station.build": "Construção (no local)",
    "station.buildIn.m": "Construir no {place}",
    "station.buildIn.f": "Construir na {place}",
    "station.buildIn.fp": "Construir nas {place}",
    "station.buildList": "Construir em: {places}",
    "station.buildAnywhere": "Construir em qualquer lugar",
    "badge.unofficial": "não oficial",
    "badge.unofficialTitle": "Tradução não oficial do nome",
    "quality.bronze": "bronze",
    "quality.silver": "prata",
    "quality.gold": "ouro",
    "badge.edited": "editado",
    "badge.editedTitle": "Nome editado por você",
    "edit.button": "editar",
    "edit.label": "Editar nome de {name}",
    "edit.input": "Novo nome para {name} ({lang})",
    "edit.save": "Salvar",
    "edit.cancel": "Cancelar",
    "edit.reset": "Restaurar original",
    "edit.saved": "Nome salvo: {name}",
    "edit.restored": "Nome original restaurado: {name}",
    "info.label": "Abrir {name} em Receitas",
    "info.title": "Ver em Receitas",
    "undo.button": "Desfazer",
  },
  en: {
    "recipe.hidden": "hidden",
    "recipe.cyc": "circular",
    "station.build": "Built in place",
    "station.buildIn.m": "Build at {place}",
    "station.buildIn.f": "Build at {place}",
    "station.buildIn.fp": "Build at {place}",
    "station.buildList": "Build at: {places}",
    "station.buildAnywhere": "Build anywhere",
    "badge.unofficial": "unofficial",
    "badge.unofficialTitle": "Unofficial name translation",
    "quality.bronze": "bronze",
    "quality.silver": "silver",
    "quality.gold": "gold",
    "badge.edited": "edited",
    "badge.editedTitle": "Name edited by you",
    "edit.button": "edit",
    "edit.label": "Edit the name of {name}",
    "edit.input": "New name for {name} ({lang})",
    "edit.save": "Save",
    "edit.cancel": "Cancel",
    "edit.reset": "Restore original",
    "edit.saved": "Name saved: {name}",
    "edit.restored": "Original name restored: {name}",
    "info.label": "Open {name} in Recipes",
    "info.title": "See in Recipes",
    "undo.button": "Undo",
  },
});

GK.ui.fmt = (function () {
  const { t, name, edited, num } = GK.i18n, { esc } = GK.util;
  const UNOFFICIAL = { guess: 1, machine: 1, missing: 1 };
  function badges(it, overrides) {
    if (edited(it, overrides)) return `<span class="badge badge-edited" title="${esc(t("badge.editedTitle"))}">${esc(t("badge.edited"))}</span>`;
    if (GK.i18n.lang() !== "en" && UNOFFICIAL[it.tr]) return `<span class="badge" title="${esc(t("badge.unofficialTitle"))}">${esc(t("badge.unofficial"))}</span>`;
    return "";
  }
  // "Construir no Cemitério" / "Build at Graveyard" (corte 12, 1.6.0): the label of a build pseudo-station
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
  // what sets a recipe apart from its siblings: the quality grade ("ouro"), else its own name ("Board (Sawhorse)").
  // "<X> from <Y>" names only restate the inputs the label already lists: left out. The selector labels show only
  // the grade (recipe names are mostly English and repeat the station); recipeLabels adds the name back when two
  // options would otherwise read the same.
  function recipeTag(r) {
    if (r.quality) return t("quality." + r.quality);
    return r.name && !/ from /i.test(r.name.en || "") ? name(r.name) : "";
  }
  // quantity of a line / the output under the viewer's perks
  function qtyOf(base, b, state) {
    if (!b || !GK.calc.isBonusActive(b, state.perks)) return base;
    if (b.qty != null) return b.qty;
    return b.add != null && base != null ? base + b.add : base;
  }
  // short, in the UI language, ingredients first (1.3.4: no letter, no English recipe name), so a closed <select>
  // cut at ~180 px still shows what goes in: "1 Tora → 4 · Cavalete",
  // "2 Abóbora (ouro) + 10 Combustível → 7 · Forno da Cozinha · ouro (oculta, circular)".
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
    return `${ins}${out ? " → " + num(out) : ""}${st}${r.quality ? " · " + t("quality." + r.quality) : ""}${tags.length ? " (" + tags.join(", ") + ")" : ""}`;
  }
  // labels for a list of options (`all` = the item's full list, kept for callers). The station is left out when
  // every option uses the same one, or (opts.omitStation = a station id) on the options made at that station: the
  // step's card already names it. Two options never read the same: a repeat gets a short tag, then a number.
  // The tag is the recipe's own name cut before " from " (1.4.1): "Improve organ I from Any Skin" made the Pele
  // selector 440-640 px wide on a 390 px phone; the cut keeps "Improve organ I" / "Improve organ II" apart.
  function shortTag(r) {
    const n = r.name ? name(r.name) : "";
    const cut = n.split(/ from /i)[0].trim();
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
  // what a recipe needs, short (1.6.0, corte 2): "Olaria I · Engenharia 2 · Foles de ferraria". No "Requer",
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
  // the item's icon as a button (1.6.0, corte 6, in place of the "i"): opens the item on the Receitas screen. Same
  // markup as GK.util.slot, in a <button> with the "Abrir X em Receitas" label; a plain icon when there is no Receitas.
  function slotButton(it, nm) {
    const s = GK.util.slot(it, nm);
    if (!it || !GK.ui.recipes || typeof GK.ui.recipes.open !== "function" || !/^<span class="slot">/.test(s)) return s;
    return `<button type="button" class="slot slot-btn" data-recipe-open="${esc(it.id)}" title="${esc(t("info.title"))}" aria-label="${esc(t("info.label", { name: nm }))}">` +
      s.slice('<span class="slot">'.length, -"</span>".length) + "</button>";
  }
  // name + pencil + inline edit form when editing. The name is plain text: only the checkbox (and its 44 px
  // .tick box) toggles "done" (AUDITORIA U3). labelFor is kept for callers; it is no longer used.
  // canEdit: show the ✎ pencil (the "Editar nomes" mode of the progress card, GK.store ui.editNames).
  function nameBlock(it, nm, labelFor, editing, extraBadges, overrides, canEdit) {
    const lang = GK.i18n.lang();
    if (editing) {
      const id = GK.util.domId(it.id);
      return `<form class="edit-form" data-edit-form="${esc(it.id)}">
        <input id="edit-${id}" name="v" value="${esc(nm)}" maxlength="80" autocomplete="off" spellcheck="false" aria-label="${esc(t("edit.input", { name: it[lang] || it.en, lang: lang.toUpperCase() }))}">
        <button type="submit" class="btn btn-sm">${esc(t("edit.save"))}</button>
        <button type="button" class="btn btn-sm btn-ghost" data-edit-cancel>${esc(t("edit.cancel"))}</button>
        ${edited(it, overrides) ? `<button type="button" class="btn btn-sm btn-ghost" data-edit-reset="${esc(it.id)}">${esc(t("edit.reset"))}</button>` : ""}
      </form>`;
    }
    const pencil = canEdit ? `<button type="button" class="edit-ico" data-edit="${esc(it.id)}" title="${esc(t("edit.button"))}" aria-label="${esc(t("edit.label", { name: nm }))}">✎</button>` : "";
    return `<span class="row-name"><span class="row-label">${esc(nm)}</span>${pencil}${extraBadges || ""}${badges(it, overrides)}</span>`;
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
  return { badges, buildLabel, stationOf, recipeLabel, recipeLabels, recipeTag, techLine, nameBlock, slotButton, undoToast };
})();
