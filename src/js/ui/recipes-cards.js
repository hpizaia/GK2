/* GK.ui.rcCards: the recipe cards of the Receitas detail (GK.ui.recipes) and the item lines they are made of.
   No state, no panel: each function takes the store state and returns markup.
   Exposes: GK.ui.rcCards.{hiddenTag, stationLabel, runes, itemLine, altNames, sharedAlt,
   recipeCard, groupCard}.
   recipeCard: one recipe (tags, its own name, inputs, yield / unlock lines, runes, by-products, "Usar").
   groupCard: the recipes GK.calc.recipeGroups joins into one card (the grade of one ingredient, or "E mais um destes").
   The cards' texts are the rc.* keys of src/js/i18n/pt.js and en.js.
*/
GK.ui.rcCards = (function () {
  const { t, name, num } = GK.i18n, { esc, slot } = GK.util;
  const { graded, UNOFFICIAL } = GK.ui.fmt;
  const { expandable } = GK.calc;
  // "Construir no Cemitério" for a build pseudo-station, the plain name otherwise
  const stationLabel = (s, state) => GK.ui.fmt.buildLabel(s, state.overrides);
  function runes(o) {
    return Object.keys(o || {}).map((k) => `<span class="rune rune-${esc(k)}">${esc(t("rune." + k))} <b>${num(o[k])}</b></span>`).join("");
  }
  // "oculta" / "impossível de obter" after a hidden item's name (the Receitas list and its item lines)
  const hiddenTag = (it) => `<span class="badge badge-hidden">${esc(t(it.unobtainable ? "rc.unobt" : "rc.hidden"))}</span>`;
  // one tappable line: icon, qty, name, note
  // opts.noWord: the grade is picked right below (a group card): no grade word under the name
  function line(l, state, sub, opts) {
    const D = GK.data.get(), it = D.items[l.item], nm = name(it, state.overrides);
    const lg = l.anyGrade ? false : l.grade;   // "Alcohol from Any Wine": any grade, no star
    const q = l.qty == null ? "?" : num(l.qty), g = graded(it, nm, lg);
    const full = g.grade ? `${g.name} (${g.word})` : nm;
    const word = g.word && !(opts && opts.noWord) ? `<span class="rc-line-note">${esc(g.word)}</span>` : "";
    return `<li><button type="button" class="rc-line"${opts && opts.id ? ` id="${esc(opts.id)}"` : ""} data-open="${esc(l.item)}" aria-label="${esc(q + " × " + full + " · " + t("rc.open", { name: nm }))}">
      ${slot(it, nm, true, lg)}<span class="rc-line-q tabnum">${esc(q)}<small>×</small></span>
      <span class="rc-line-main"><span class="rc-line-name">${esc(g.name)}</span>${word}${l.note ? `<span class="rc-line-note">${esc(name(l.note))}</span>` : ""}${sub ? `<span class="rc-line-note">${esc(sub)}</span>` : ""}</span>
      <span class="rc-chev" aria-hidden="true">›</span></button></li>`;
  }
  function itemLine(id, state, sub) {
    const D = GK.data.get(), it = D.items[id], nm = name(it, state.overrides), g = graded(it, nm);
    if (g.word) sub = sub ? g.word + " · " + sub : g.word;
    return `<li><button type="button" class="rc-line" data-open="${esc(id)}" aria-label="${esc(t("rc.open", { name: nm }))}">
      ${slot(it, nm, true)}<span class="rc-line-main"><span class="rc-line-name">${esc(g.name)}${it.hidden ? hiddenTag(it) : ""}</span>${sub ? `<span class="rc-line-note">${esc(sub)}</span>` : ""}</span>
      <span class="rc-chev" aria-hidden="true">›</span></button></li>`;
  }
  // "Rende 5 com Cozinheiro II" (made_text, exported as out.note; the perk chip lives in the planner's Progresso)
  function yieldLines(r, state) {
    const out = [], b = r.out.bonus;
    if (b && (b.qty != null || b.add != null)) {
      const perk = b.perks.map((p) => name(GK.data.perks()[p] || { en: p })).join(" + ");
      const on = GK.calc.isBonusActive(b, state.perks);
      const txt = b.qty != null ? t("rc.bonusYield", { n: b.qty, perk }) : t("rc.bonusAdd", { n: b.add, perk });
      out.push(`<span class="${on ? "perk-on" : ""}">${esc(txt)}${on ? ` · ✓ ${esc(t("rc.bonusOn"))}` : ""}</span>`);
    } else if (r.out.note) out.push(esc(t("rc.makesNote", { note: name(r.out.note) })));
    if (r.star && (r.star.silver != null || r.star.gold != null)) {
      out.push(esc(t("rc.star", { silver: r.star.silver != null ? r.star.silver : "?", gold: r.star.gold != null ? r.star.gold : "?" })));
    }
    return out;
  }
  function unlockLines(r, noMastery) {
    const out = [];
    if (r.tech) {
      const key = r.tech.type === "quest" ? "rc.quest" : r.tech.type === "perk" ? "rc.perk" : "rc.tech";
      const canLink = r.tech.id && r.tech.type === "technology" && GK.ui.tech && typeof GK.ui.tech.open === "function";
      const tn = esc(name(r.tech));
      const txt = esc(t(key, { tech: "\u0000" })).replace("\u0000", canLink ? `<button type="button" class="rc-link" data-tech="${esc(r.tech.id)}">${tn}</button>` : `<b>${tn}</b>`);
      out.push(txt);
    }
    if (r.mastery && !noMastery) out.push(esc(masteryTxt(r)));
    if (r.ext) out.push(esc(t("rc.ext", { ext: name(r.ext) })));
    if (r.ticks != null) out.push(esc(t("rc.time", { n: r.ticks })));
    if (r.energy != null) out.push(esc(r.ticks != null ? t("rc.energyTotal", { n: r.energy, total: num(r.energy * r.ticks) }) : t("rc.energy", { n: r.energy })));
    return out;
  }
  const masteryTxt = (r) => t("rc.mastery", { type: name(r.mastery.type), level: r.mastery.level ? r.mastery.level : "" }).trim();
  const altNames = (r, state) => r.alt.map((a) => name(a, state.overrides)).join(", ");
  // "Todas também em: Forno da Cozinha II" once above the cards when every recipe (2+) has the same alternatives
  function sharedAlt(rs) {
    if (rs.length < 2 || !rs[0].alt.length) return null;
    const key = (r) => r.alt.map((a) => a.id).sort().join("|"), k0 = key(rs[0]);
    return rs.every((r) => key(r) === k0) ? rs[0] : null;
  }
  // the recipe's own name under the card's tags ("Placa (Cavalete)"), when it says more than the item. pt: never an
  // untranslated English name; a "X a partir de Y" name is left out (it only restates the ingredients listed right
  // below) and so is a "Construir X (Zona)" one (the card's header already says where: "Construir no Pátio"); en keeps
  // "X from Y" / "Build X (Yard)". A name composed by the build (the `derived` layer of scripts/build.py, or a
  // machine-made one) gets the "não oficial" badge.
  const PT_HIDDEN_NAME = / a partir de |^Construir .+ \(.+\)$/i;
  function recipeName(r, it) {
    if (!r.name || name(r.name) === name(it)) return "";
    const en = GK.i18n.lang() === "en";
    if (!en && (r.name.pt === r.name.en || PT_HIDDEN_NAME.test(name(r.name)))) return "";
    const badge = !en && UNOFFICIAL[r.name.tr] ? `<span class="badge" title="${esc(t("rc.unofficialTitle"))}">${esc(t("rc.unofficial"))}</span>` : "";
    return `<p class="rc-rname">${esc(name(r.name))}${badge}</p>`;
  }
  // idx: the card's letter ("Receita B"), null = no letter (one card only, or a folded circular one); folded: inside
  // "Melhorar a qualidade" (its title already says circular: no badge)
  // what a recipe card and a group card share: the tags, "Também em", the yield / unlock lines, runes, by-products.
  // opts: isDefault (the "padrão" tag first), folded (no "circular" tag), noMastery (each option says its mastery)
  function cardParts(r, state, altShared, opts) {
    const tags = [];
    if (opts.isDefault) tags.push(`<span class="badge badge-goal">${esc(t("rc.default"))}</span>`);
    if (r.example) tags.push(`<span class="badge badge-ex" title="${esc(t("rc.exampleTitle"))}">${esc(t("rc.example"))}</span>`);
    if (r.noexp) tags.push(`<span class="badge badge-ex">${esc(t("rc.noexp"))}</span>`);
    if (!r.listed) tags.push(`<span class="badge badge-hidden">${esc(t("rc.hiddenRecipe"))}</span>`);
    if (r.cyc && !opts.folded) tags.push(`<span class="badge badge-warn">${esc(t("rc.cyc"))}</span>`);
    const meta = yieldLines(r, state).concat(unlockLines(r, opts.noMastery)).map((h) => `<li>${h}</li>`).join("");
    return {
      tags: tags.length ? `<div class="rc-tags">${tags.join("")}</div>` : "",
      alt: r.alt.length && !altShared ? `<p class="rc-meta-line">${esc(t("rc.alt", { names: altNames(r, state) }))}</p>` : "",
      meta: meta ? `<ul class="rc-meta">${meta}</ul>` : "",
      rn: r.runes ? `<div class="rc-runes"><span class="rc-k">${esc(t("rc.runesNeed"))}</span> ${runes(r.runes)}</div>` : "",
      extra: r.extra.length ? `<div class="rc-extra"><span class="rc-k">${esc(t("rc.extra"))}</span><ul class="rc-lines">${r.extra.map((l) => line(l, state)).join("")}</ul></div>` : "",
    };
  }
  function recipeCard(r, idx, it, state, cur, many, altShared, folded) {
    const p = cardParts(r, state, altShared, { isDefault: r.id === it.defaultRecipe, folded });
    const rname = recipeName(r, it);
    const ins = r.in.length ? `<ul class="rc-lines">${r.in.map((l) => line(l, state)).join("")}</ul>` : `<p class="rc-meta-line">${esc(t("rc.noInputs"))}</p>`;
    let act = "";
    if (cur && cur.id === r.id) act = `<span class="rc-inuse">✓ ${esc(t("rc.inUse"))}</span>`;
    else if (expandable(r) && (many || !it.defaultRecipe)) act = `<button type="button" class="btn btn-sm" id="rc-use-${GK.util.domId(r.id)}" data-use="${esc(r.id)}">${esc(t("rc.use"))}</button>`;
    return `<article class="card list rc-recipe">
      ${cardHead(r, idx, state)}
      <div class="rc-recipe-body">
        ${p.tags}${rname}${p.alt}${ins}
        ${p.meta}${p.rn}${p.extra}
        ${act ? `<div class="rc-act">${act}</div>` : ""}
      </div>
    </article>`;
  }
  function cardHead(r, idx, state) {
    const stName = stationLabel(r.station, state);
    const yieldTxt = r.out.qty == null ? t("rc.makesVar") : t("rc.makes", { n: r.out.qty });
    const letter = idx == null ? "" : `<span class="station-sub">${esc(t("rc.recipeN", { l: String.fromCharCode(65 + (idx % 26)) }))}</span>`;
    return `<header class="station-h">${slot(r.station, stName, true)}<h4>${letter}${esc(stName)}</h4><span class="rc-yield tabnum">${esc(yieldTxt)}</span></header>`;
  }
  // a group card (GK.calc.recipeGroups): the shared lines, then the pick: mode "q" = the grade of one ingredient
  // (bronze / prata / ouro, each with its own amount or mastery when they differ), mode "alt" = "E mais um destes",
  // one row per ingredient with its grades. The option in use is checked; a tap sets it in the planner.
  function groupCard(g, idx, it, state, cur, altShared) {
    const D = GK.data.get(), r0 = g.recipes[0];
    const inUse = g.options.find((o) => cur && o.r.id === cur.id) || null;
    const shown = inUse || g.options[0];
    const pid = (o) => "rc-pick-" + GK.util.domId(o.r.id);
    const word = (o) => (o.grade ? t("quality." + o.grade) : "");
    const baseName = (o) => graded(o.item, name(o.item, state.overrides), o.grade).name;
    const say = (o) => `${num(o.line.qty)}× ${baseName(o)}${o.grade ? " " + word(o) : ""}`;
    const radio = (o, cls, inner, label) => `<button type="button" class="qopt${cls}" role="radio" id="${esc(pid(o))}" data-pick="${esc(o.r.id)}" aria-checked="${o === inUse}"${label ? ` aria-label="${esc(label)}"` : ""}>${inner}</button>`;
    const star = (o) => GK.util.qstar(o.grade);
    const hid = "rc-q-" + GK.util.domId(r0.id);
    const fixed = (g.fixed || []).map((l) => line(l, state));
    let pick;
    if (g.mode === "q") {
      fixed.push(line(shown.line, state, "", { noWord: true }));
      const opts = g.options.map((o) => {
        const d = [g.qtyEach ? num(o.line.qty) + "×" : "", g.masteryEach && o.r.mastery ? `${name(o.r.mastery.type)}${o.r.mastery.level ? " " + o.r.mastery.level : ""}` : ""].filter(Boolean).join(" · ");
        return radio(o, "", `<span class="qopt-t">${star(o)}${esc(word(o))}</span>${d ? `<span class="qopt-d">${esc(d)}</span>` : ""}`);
      }).join("");
      pick = `<div class="qpick" role="radiogroup" aria-labelledby="${esc(hid)}"><p class="qpick-h" id="${esc(hid)}">${esc(t("rc.qPick"))}</p>
        <div class="qopts">${opts}</div>`;
    } else {
      const rows = g.rows.map((row) => {
        const nm = name(row.item, state.overrides), bn = graded(row.item, nm).name;
        const os = row.options.map((o) => radio(o, " qopt-sm", `${star(o)}<span class="tabnum">${esc(num(o.line.qty))}×</span>`,
          `${num(o.line.qty)} ${bn}${o.grade ? " (" + word(o) + ")" : ""}`)).join("");
        return `<li><button type="button" class="qalt-it" data-open="${esc(row.item.id)}" aria-label="${esc(t("rc.open", { name: nm }))}">${slot(row.item, nm, true, false)}<span class="qalt-n">${esc(bn)}</span></button><span class="qalt-o">${os}</span></li>`;
      }).join("");
      pick = `<div class="qpick" role="radiogroup" aria-labelledby="${esc(hid)}"><p class="qpick-h" id="${esc(hid)}">${esc(t("rc.qMore"))}</p>
        <ul class="qalt">${rows}</ul>`;
    }
    const what = inUse ? (g.mode === "q" ? word(inUse) : say(inUse)) : "";
    pick += `<p class="rc-inuse qpick-use" aria-live="polite">${inUse ? `✓ ${esc(t("rc.inUseQ", { what }))}` : ""}</p></div>`;
    const p = cardParts(r0, state, altShared, { noMastery: g.masteryEach });
    return `<article class="card list rc-recipe rc-group">
      ${cardHead(r0, idx, state)}
      <div class="rc-recipe-body">
        ${p.tags}${p.alt}${fixed.length ? `<ul class="rc-lines">${fixed.join("")}</ul>` : ""}
        ${pick}
        ${p.meta}${p.rn}${p.extra}
      </div>
    </article>`;
  }
  return { hiddenTag, stationLabel, runes, itemLine, altNames, sharedAlt, recipeCard, groupCard };
})();
