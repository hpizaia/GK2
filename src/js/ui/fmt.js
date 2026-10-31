/* GK.ui.fmt: shared bits of markup for item names, recipes and stations (badges, recipe labels,
   tech lines, the editable name block) and the "Desfazer" toast. No state, no panel.
   Exposes: GK.ui.fmt.{badges, stationOf, recipeLabel, recipeLabels, recipeTag, techLine, nameBlock, infoButton, undoToast}.
   infoButton(itemId, name): the 44 px "i" button (data-recipe-open) that opens the item in Receitas; every planner
   panel that shows one handles the click itself (GK.ui.recipes.open(id, {from: "plan"})).
   undoToast(msg, onUndo): a toast with a "Desfazer" button (its own #toast-undo element, created on first use, after
   #toast in <body>; it sits above #toast when both show). 6 s, paused while it holds the focus or the pointer.
*/
GK.i18n.add({
  pt: {
    "recipe.hidden": "oculta",
    "recipe.cyc": "circular",
    "station.build": "Construção (no local)",
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
  // station label of the recipe the planner would use for this item (for search / goals sub-lines)
  function stationOf(id, state) {
    const D = GK.data.get();
    const h = GK.calc.howToMake(id, D, state.choice, state.have, state.perks);
    const rs = GK.data.recipesFor(id);
    if (!h.r) return t("search.raw");
    const st = name(h.r.station, state.overrides);
    const label = h.r.station.build && !h.r.station.i18n ? `${t("station.build")} · ${st}` : st;
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
  // every option uses the same one. Two options never read the same: a repeat gets a short tag, then a number.
  // The tag is the recipe's own name cut before " from " (1.4.1): "Improve organ I from Any Skin" made the Pele
  // selector 440-640 px wide on a 390 px phone; the cut keeps "Improve organ I" / "Improve organ II" apart.
  function shortTag(r) {
    const n = r.name ? name(r.name) : "";
    const cut = n.split(/ from /i)[0].trim();
    return cut.length > 28 ? cut.slice(0, 27).trimEnd() + "…" : cut;
  }
  function recipeLabels(list, state, all) {
    const sid = (r) => (r.station && (r.station.id || r.station.en)) || "";
    const noStation = list.length > 1 && list.every((r) => sid(r) === sid(list[0]));
    const out = list.map((r, k) => recipeLabel(r, k, state, { noStation }));
    const dup = (k) => out.some((x, j) => j !== k && x === out[k]);
    const extra = out.map((s, k) => (dup(k) && list[k].name && !list[k].quality && shortTag(list[k]) ? " — " + shortTag(list[k]) : ""));
    extra.forEach((x, k) => { out[k] += x; });
    const nth = out.map((s, k) => (dup(k) ? " #" + (k + 1) : ""));
    nth.forEach((x, k) => { out[k] += x; });
    return out;
  }
  function techLine(r) {
    const out = [];
    if (r.tech) {
      const key = r.tech.type === "quest" ? "steps.techQuest" : r.tech.type === "perk" ? "steps.techPerk" : "steps.tech";
      out.push(t(key, { tech: name(r.tech) }));
    }
    if (r.mastery) out.push(t("steps.mastery", { type: name(r.mastery.type), level: r.mastery.level == null ? "" : r.mastery.level }));
    if (r.ext) out.push(t("steps.ext", { ext: name(r.ext) }));
    return out;
  }
  // the "i" button: opens the item's detail on the Receitas screen (only when that screen exists)
  const INFO_SVG = '<svg width="16" height="16" viewBox="0 0 9 9" aria-hidden="true" focusable="false" shape-rendering="crispEdges" fill="currentColor"><path d="M2 0h5v1H2zM1 1h1v1H1zM7 1h1v1H7zM0 2h1v5H0zM8 2h1v5H8zM1 7h1v1H1zM7 7h1v1H7zM2 8h5v1H2zM4 2h1v1H4zM4 4h1v3H4z"/></svg>';
  function infoButton(itemId, nm) {
    if (!GK.ui.recipes || typeof GK.ui.recipes.open !== "function") return "";
    return `<button type="button" class="info-ico" data-recipe-open="${esc(itemId)}" title="${esc(t("info.title"))}" aria-label="${esc(t("info.label", { name: nm }))}">${INFO_SVG}</button>`;
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
    return `<span class="row-name"><span class="row-label">${esc(nm)}</span>${pencil}${infoButton(it.id, nm)}${extraBadges || ""}${badges(it, overrides)}</span>`;
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
  return { badges, stationOf, recipeLabel, recipeLabels, recipeTag, techLine, nameBlock, infoButton, undoToast };
})();
