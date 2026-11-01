/* GK.data: loads and normalizes the embedded JSON (the gk2-data script block, schema 1, see
   scripts/README-build.md). Accepts collapsed localized values: a plain string stands for {pt: s, en: s}.
   Owns: items, stations, recipes and their indexes (byOut, usedIn, search index); meta (built, version,
   changelog, sprite); the perk list parsed from recipe notes (D.perks); the payload's technology tree block as
   D.techs (raw; GK.tech normalizes it).
   Exposes: GK.data.{load, get, item, recipe, recipesFor, norm, words, parseBonus, perks} (+ the grade helpers below).
   Load-time enrichments (no build change needed):
   - bonus: input / by-product / output notes shaped "N (M with X)", "N, or M with X", "+N each with X" or
     "M with X" become line.bonus = {perk: "X" (en), perks: [perkId], qty: M | null, add: N | null}; the perk
     names (en + pt, the pt one read from note.pt with the mirrored pattern) are collected in D.perks.
   - quality (1.9): recipe.quality = "bronze" | "silver" | "gold" = the grade of the graded item it makes (Barril with
     silver Grape Juice → Vinho (prata); "Wine (bronze) + Spices" → Vinho (prata) too), else the grade its name gives the
     input ("Cabbage soup from Cabbage (gold)"); never read from the id alone (Bronze Polido has none).
   - grades kept by the build (1.9, docs/revisao-ux/consertos.md "Qualidade"): "Wine (silver)" is the item wine-silver
     (base: wine) in the payload; the plain item is the bronze one. gradeMoves() moves a plan saved before that.
   - grades (1.8.0, receitas agrupadas): item.grade = "bronze" | "silver" | "gold" on a quality variant (its id ends in
     -bronze / -silver / -gold); line.grade on the input a "<X> from <Y> (grade)" recipe names, also where the item stays
     the plain one (bronze: the common <Y> is the bronze one; a circular recipe: the input is the output itself). Shown
     as the star in the icon corner (GK.util.slot). The recipes of an item, by family (same id but the grade suffix),
     always come bronze, silver, gold (gradeSort keeps the positions the family holds in the list).
   - bronze plain (2026-11, consertos.md §17): the plain item of a family the build keeps silver / gold of ("pumpkin",
     "wine", "cabbage-seed"…) is the bronze one, so it gets item.grade = "bronze" too (bronzePlain); an "Any X" input
     line takes any grade (line.anyGrade: no star on it). lineGrade(line) = the grade a line shows.
   Also exposes GK.data.{GRADE_RANK, itemGrade, lineGrade, family, gradeSort, stripGrade, gradeMoves}.
*/
GK.data = (function () {
  const D = {
    meta: {}, items: {}, stations: {}, recipes: [], recipeById: {}, byOut: {}, usedIn: {},
    index: [], visibleCount: 0, perks: {}, techs: null, days: null,
  };
  const HIDDEN_KINDS = { virtual: 1, action: 1 };
  let LANGS = ["pt", "en"];
  // {pt, en} | "same text" | null  ->  {pt, en, …} | null
  function loc(v) {
    if (v == null || v === "") return null;
    if (typeof v === "string") { const o = {}; LANGS.forEach((l) => { o[l] = v; }); return o; }
    if (typeof v !== "object") return null;
    const o = Object.assign({}, v);
    LANGS.forEach((l) => { if (o[l] == null) o[l] = o.en != null ? o.en : o.pt; });
    return o;
  }
  const num = (v) => (typeof v === "number" && isFinite(v) ? v : (v != null && v !== "" && isFinite(+v) ? +v : null));
  // pseudo-stations for buildings (built where they stand)
  const BUILD = { id: "build", i18n: "station.build", icon: null, build: true };
  function zoneStation(zone) {
    const id = "zone:" + zone.en;
    return D.stations[id] || (D.stations[id] = Object.assign({ id, icon: null, build: true }, zone));
  }
  function station(id) {
    if (id == null) return null;
    return D.stations[id] || (D.stations[id] = { id, pt: id, en: id, tr: "missing", icon: null });
  }
  function ensureItem(id) {
    if (!D.items[id]) D.items[id] = normItem(id, { pt: id, en: id, tr: "missing", stub: true });
    return D.items[id];
  }
  function normItem(id, it) {
    const o = Object.assign({}, it);
    o.id = id;
    o.en = it.en || it.pt || id;
    o.pt = it.pt || o.en;
    LANGS.forEach((l) => { if (!o[l]) o[l] = o.en; });
    o.cat = loc(it.cat);
    o.obtain = loc(it.obtain);
    o.icon = it.icon || null;
    o.tr = it.tr || "missing";
    o.kind = it.kind || "item";
    o.listed = it.listed !== false;
    o.unobtainable = !!it.unobtainable;
    o.recipes = Array.isArray(it.recipes) ? it.recipes.slice() : null; // null: derive from recipes (older JSON)
    o.defaultRecipe = it.defaultRecipe === undefined ? undefined : it.defaultRecipe || null;
    o.members = Array.isArray(it.members) ? it.members.slice() : null;
    o.hidden = !o.listed || o.unobtainable || !!HIDDEN_KINDS[o.kind];
    return o;
  }
  // ---- perk bonuses in notes ----------------------------------------------------------------------
  // [en regex, pt regex, kind]: groups are (base?, qty|add, perk)
  const BONUS = [
    [/^(\d+(?:\.\d+)?) \((\d+(?:\.\d+)?) with (.+)\)$/i, /^(\d+(?:[.,]\d+)?) \((\d+(?:[.,]\d+)?) com (.+)\)$/i, "qty"],
    [/^(\d+(?:\.\d+)?), or (\d+(?:\.\d+)?) with (.+)$/i, /^(\d+(?:[.,]\d+)?), ou (\d+(?:[.,]\d+)?) com (.+)$/i, "qty"],
    [/^()\+(\d+(?:\.\d+)?) each with (.+)$/i, /^()\+(\d+(?:[.,]\d+)?) cada com (.+)$/i, "add"],
    [/^()(\d+(?:\.\d+)?) with (.+)$/i, /^()(\d+(?:[.,]\d+)?) com (.+)$/i, "qty"],
  ];
  const slug = (s) => String(s).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  /** note {pt, en, …} → {perk, perks: [id], qty, add, names: [{id, en, pt}]} | null (first segment with a bonus) */
  function parseBonus(note) {
    if (!note || !note.en) return null;
    const en = String(note.en).split(";").map((x) => x.trim()), pt = String(note.pt || "").split(";").map((x) => x.trim());
    for (let k = 0; k < en.length; k++) {
      for (const [rx, rxPt, kind] of BONUS) {
        const m = rx.exec(en[k]);
        if (!m) continue;
        const v = +m[2];
        if (!(v >= 0)) continue;
        const enNames = m[3].split(/\s+and\s+/i).map((x) => x.trim()).filter(Boolean);
        const mp = pt[k] && rxPt.exec(pt[k]);
        const ptNames = mp ? mp[3].split(/\s+e\s+/).map((x) => x.trim()) : [];
        const names = enNames.map((e, i) => ({ id: slug(e), en: e, pt: ptNames.length === enNames.length ? ptNames[i] : e }));
        return { perk: m[3].trim(), perks: names.map((x) => x.id), qty: kind === "qty" ? v : null, add: kind === "add" ? v : null, names };
      }
    }
    return null;
  }
  function addBonus(line) {
    const b = line && line.note && parseBonus(line.note);
    if (!b) return;
    line.bonus = { perk: b.perk, perks: b.perks, qty: b.qty, add: b.add };
    for (const n of b.names) {
      const p = D.perks[n.id] || (D.perks[n.id] = { id: n.id, en: n.en, pt: n.pt, uses: 0 });
      LANGS.forEach((l) => { if (p[l] == null) p[l] = l === "pt" ? n.pt : n.en; });
      if (p.pt === p.en && n.pt !== n.en) p.pt = n.pt;   // prefer a real pt name when one note has it
      p.uses++;
    }
  }
  // a recipe's grade (1.9, qualidade): the grade of what it MAKES when the output is a graded item ("Wine (silver)" from
  // the Barrel with silver Grape Juice, and from "Wine (bronze) + Spices"); else the grade its name gives the input it
  // changes ("Cabbage soup from Cabbage (gold)"). Never from the id alone: "polished-bronze" is not a grade.
  const gradeOf = (r) => {
    const out = D.items[r.out.item];
    if (out && out.grade) return out.grade;
    const m = r.name && /\((bronze|silver|gold)\)\s*$/i.exec(r.name.en || "");
    return m ? m[1].toLowerCase() : null;
  };
  // "<X> from <Y> (bronze|silver|gold)": mark the <Y> input with the grade (line.grade, shown only)
  function qualityInputs() {
    for (const r of D.recipes) {
      if (!r.name) continue;
      const m = /^.+? from (.+?) \((bronze|silver|gold)\)\s*$/i.exec(r.name.en || "");
      if (!m) continue;
      const grade = m[2].toLowerCase(), want = norm(m[1]);
      const line = r.in.find((l) => D.items[l.item] && norm(D.items[l.item].en) === want);
      if (!line) continue;
      const base = D.items[line.item];
      if (base.kind === "quality-variant" || base.members) continue;
      // since 1.9 the build keeps the grade (silver / gold inputs are their own items): what is left here is the plain
      // item read as bronze ("Wine (bronze)" in "Drink enhancement I", "Cabbage (bronze)" in a soup)
      line.grade = grade;
    }
  }
  // ---- grades: bronze, silver, gold (see the header) ------------------------------------------------
  const GRADE_RANK = { bronze: 0, silver: 1, gold: 2 };
  const GRADE_SUFFIX = /-(bronze|silver|gold)$/;
  // an item's grade (a quality variant: "grape-juice-silver", "cabbage-gold") or null
  const itemGrade = (it) => (it && it.grade && GRADE_RANK[it.grade] != null ? it.grade : null);
  // the family of a graded item or recipe: its id without the grade ("cabbage" for cabbage-gold), else null
  function family(x) {
    if (!x) return null;
    if (x.out) return x.quality && GRADE_SUFFIX.test(x.id || "") ? x.out.item + "|" + x.id.replace(GRADE_SUFFIX, "") : null;
    return itemGrade(x) ? x.base || x.id.replace(GRADE_SUFFIX, "") : null;
  }
  // reorder, in place, the members of each family to bronze, silver, gold, in the positions the family holds
  // (everything else stays where it is). famOf(x) → family key or null; rankOf(x) → 0..2.
  // together (the item lists and the search, 2026-11): the family also comes in one run, where its first member was
  // (Abóbora, Abóbora (prata), Abóbora (ouro), with no "Abóbora assada" in between); the rest keeps its order
  function gradeSort(list, famOf, rankOf, together) {
    const fams = new Map();
    list.forEach((x, i) => {
      const k = famOf(x), g = rankOf(x);
      if (k == null || g == null) return;
      if (!fams.has(k)) fams.set(k, []);
      fams.get(k).push(i);
    });
    const moved = new Map();   // first index of a family → its members in order; the other indexes are dropped
    for (const idx of fams.values()) {
      if (idx.length < 2) continue;
      const xs = idx.map((i) => list[i]).sort((a, b) => rankOf(a) - rankOf(b));
      if (together) { moved.set(idx[0], xs); idx.slice(1).forEach((i) => moved.set(i, null)); }
      else idx.forEach((i, j) => { list[i] = xs[j]; });
    }
    if (moved.size) {
      const out = [];
      list.forEach((x, i) => { const m = moved.get(i); if (m === undefined) out.push(x); else if (m) out.push(...m); });
      out.forEach((x, i) => { list[i] = x; });
    }
    return list;
  }
  /**
   * A plan saved up to 1.8.1, when the data dropped the grade of Vinho / Uvas / Repolho…: "Vinho" had the three Barril
   * recipes and the two improvements, so a silver or gold one was planned as the goal "wine" with the recipe chosen
   * (choice.wine = "wine-from-grape-juice-silver"). Since 1.9 that recipe makes "wine-silver": the choice moves to the
   * item it makes, and a goal of the plain item planned with it becomes that grade (what the plan made), with its step
   * tick. Ids never change: "wine" is the bronze one, "wine-silver" / "cabbage-gold" the ids the page already used.
   * goals [{item, qty}], choice {item: recipe}, done {key: tick} → {goals, choice, done} (new objects) or null (no change).
   */
  function gradeMoves(goals, choice, done) {
    if (!D.recipes.length || !choice) return null;
    let gs = null, ch = null, dn = null;
    for (const [id, rid] of Object.entries(choice)) {
      const r = D.recipeById[rid], to = r && D.items[r.out.item];
      if (!to || to.id === id || !itemGrade(to) || family(to) !== id) continue;
      ch = ch || Object.assign({}, choice);
      delete ch[id];
      if (ch[to.id] == null) ch[to.id] = rid;
      gs = gs || (goals || []).map((g) => ({ item: g.item, qty: g.qty }));
      const i = gs.findIndex((g) => g.item === id);
      if (i < 0) continue;
      const j = gs.findIndex((g) => g.item === to.id);
      gs[i] = { item: to.id, qty: gs[i].qty + (j >= 0 ? gs[j].qty : 0) };   // at the old goal's place
      if (j >= 0) gs.splice(j, 1);
      const k = "step:" + id;
      if (done && done[k] != null) { dn = dn || Object.assign({}, done); if (dn["step:" + to.id] == null) dn["step:" + to.id] = dn[k]; delete dn[k]; }
    }
    return ch ? { goals: gs, choice: ch, done: dn || done } : null;
  }
  /**
   * The plain item of a family is its bronze grade (1.9, data/README-data.md "Quality grades"): "pumpkin" next to
   * "pumpkin-silver" / "pumpkin-gold" (base: pumpkin). It gets item.grade = "bronze", so it shows as bronze wherever a
   * grade shows (the star in GK.util.slot, the word under the name, the bronze / silver / gold order). Only a family
   * with a silver or gold item that names it as its base and no bronze item of its own: História has "story-bronze"
   * (the plain História is the one the prayers ask for), Suco de Uva has no plain item, and the families the build
   * leaves without grades (organs, Beer, Bronze Polido, the "Any X" groups) have no graded item at all. Ids, the data
   * and the saved plans do not change; neither does recipe.quality (set before this).
   * 2026-11: Abóbora, Sementes de Abóbora, Repolho, Semente de Repolho, Cebola, Semente de Cebola, Uvas, Sementes de
   * Uva, Vinho.
   */
  function bronzePlain() {
    const fams = {};
    for (const it of Object.values(D.items)) {
      const g = itemGrade(it);
      if (!g || !it.base) continue;
      (fams[it.base] = fams[it.base] || {})[g] = true;
    }
    for (const [id, gs] of Object.entries(fams)) {
      const it = D.items[id];
      if (gs.bronze || !(gs.silver || gs.gold) || !it || it.stub || it.grade || it.members || it.kind === "quality-variant" || it.kind === "group") continue;
      it.grade = "bronze";
    }
  }
  /**
   * "Alcohol from Any Wine", "Seed oil from Any Cabbage seed": the wiki points "Any X" to the plain item (the bronze
   * one), but the recipe takes X of any grade. The line gets anyGrade = true: no star nor grade word on it
   * (lineGrade → null), and a group card keeps it with the plain ingredients.
   */
  function anyLines() {
    for (const r of D.recipes) {
      const m = r.name && /\bfrom Any (.+?)\s*$/i.exec(r.name.en || "");
      if (!m) continue;
      const want = norm(m[1]);
      const line = r.in.find((l) => D.items[l.item] && norm(D.items[l.item].en) === want);
      if (line && !line.grade) line.anyGrade = true;
    }
  }
  // the grade a recipe line shows: its own ("… from Cabbage (bronze)"), else its item's; none on an "Any X" line
  const lineGrade = (line) => (!line || line.anyGrade ? null : line.grade || itemGrade(D.items[line.item]));
  // "Suco de Uva (prata)" → "Suco de Uva" (the grade word in either language, at the end of a shown name)
  const stripGrade = (s) => String(s == null ? "" : s).replace(/\s*\((bronze|prata|ouro|silver|gold)\)\s*$/i, "");
  function normLine(x) {
    if (!x) return null;
    const item = Array.isArray(x) ? x[0] : x.item;
    if (!item) return null;
    ensureItem(item);
    const q = num(Array.isArray(x) ? x[1] : x.qty);
    const line = { item, qty: q != null && q > 0 ? q : null };
    const note = loc(x.note);
    if (note) line.note = note;
    return line;
  }
  function normRecipe(r, idx) {
    if (!r || !r.out) return null;
    const outItem = typeof r.out === "string" ? r.out : r.out.item;
    if (!outItem) return null;
    ensureItem(outItem);
    const zone = loc(r.zone);
    const st = r.station != null ? station(typeof r.station === "object" ? r.station.id || r.station.en : r.station)
      : zone ? zoneStation(zone) : BUILD;
    if (r.station != null && typeof r.station === "object" && st.pt === st.id) Object.assign(st, loc(r.station));
    const mastery = r.mastery && typeof r.mastery === "object" ? { type: loc(r.mastery.type), level: num(r.mastery.level) } : null;
    let tech = null;
    if (r.tech) tech = typeof r.tech === "string" ? loc(r.tech) : Object.assign({}, r.tech, loc({ pt: r.tech.pt, en: r.tech.en }));
    const outNote = typeof r.out === "object" ? loc(r.out.note) || loc(r.made) : loc(r.made);
    const out = { item: outItem, qty: num(r.out.qty) };
    if (outNote) out.note = outNote;
    return {
      id: r.id || outItem + "#" + idx,
      out,
      station: st,
      alt: (Array.isArray(r.alt) ? r.alt : []).map(station).filter(Boolean),
      in: (Array.isArray(r.in) ? r.in : []).map(normLine).filter(Boolean).map((l) => (l.qty == null ? Object.assign(l, { qty: 1 }) : l)),
      tech,
      type: r.type || "hand_craft",
      cd: !!r.cd,
      listed: r.listed !== false,
      noexp: !!r.noexp,
      cyc: !!r.cyc,
      ext: loc(r.ext),
      extra: (Array.isArray(r.extra) ? r.extra : []).map(normLine).filter(Boolean),
      mastery: mastery && mastery.type ? mastery : null,
      ticks: num(r.ticks), energy: num(r.energy),
      example: !!r.example,
      runes: r.runes || null,
      zone,
      name: loc(r.name),
      star_quality: typeof r.star_quality === "string" ? r.star_quality : null,
      // star craft thresholds {silver: 6, gold: 10} (successful ticks; a value may be text)
      star: starOf(r.star_quality),
    };
  }
  function starOf(v) {
    if (!v || typeof v !== "object" || Array.isArray(v)) return null;
    const o = {};
    for (const g of ["silver", "gold"]) {
      const x = v[g] != null ? v[g] : v[g + "_at"];
      if (typeof x === "number" && isFinite(x)) o[g] = x;
      else if (typeof x === "string" && x.trim()) o[g] = isFinite(+x) ? +x : x.trim();
    }
    return Object.keys(o).length ? o : null;
  }
  const norm = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[’'`´]/g, "").trim();
  const words = (n) => n.split(/[^a-z0-9]+/).filter(Boolean);
  function load(json) {
    const j = json || JSON.parse(document.getElementById("gk2-data").textContent || "{}");
    D.meta = j.meta || { schema: j.schema || 1 };
    D.techs = j.techs || (j.meta && j.meta.techs) || null;   // the technology tree block (read by GK.tech)
    D.days = j.days || null;                                 // the week block (read by GK.ui.days / GK.ui.today)
    LANGS = Array.isArray(D.meta.langs) && D.meta.langs.length ? D.meta.langs.slice() : ["pt", "en"];
    if (LANGS.indexOf("en") < 0) LANGS.push("en");
    D.stations = {};
    for (const [k, v] of Object.entries(j.stations || {})) {
      const s = typeof v === "string" ? loc(v) : Object.assign({}, v, loc({ pt: v.pt, en: v.en || v.pt || k }));
      D.stations[k] = Object.assign({ id: k, icon: null, tr: "missing" }, s, { id: k });
    }
    D.items = {};
    for (const [id, it] of Object.entries(j.items || {})) D.items[id] = normItem(id, it || {});
    D.recipes = []; D.recipeById = {}; D.perks = {};
    (j.recipes || []).forEach((r, i) => {
      const nr = normRecipe(r, i);
      if (nr && !D.recipeById[nr.id]) { D.recipes.push(nr); D.recipeById[nr.id] = nr; }
    });
    const icons = D.meta.sprite && D.meta.sprite.icons;
    qualityInputs();
    for (const it of Object.values(D.items)) {
      const m = it.kind === "quality-variant" && GRADE_SUFFIX.exec(it.id);
      if (!m) continue;
      it.grade = m[1];
      // a grade the build kept ("wine-silver", base "wine") draws its family's icon (the star tells the grade)
      if (icons && it.base && !icons[it.id] && icons[it.base]) icons[it.id] = icons[it.base];
    }
    for (const r of D.recipes) {
      r.quality = gradeOf(r);
      r.in.forEach(addBonus); r.extra.forEach(addBonus); addBonus(r.out);
    }
    // after the recipes' quality (that stays as it was: the planner reads it), the plain bronze ones and "Any X"
    bronzePlain();
    anyLines();
    // byOut keeps each item's best-first order (item.recipes); usedIn = consumers
    D.byOut = {}; D.usedIn = {};
    const tmp = {};
    for (const r of D.recipes) {
      (tmp[r.out.item] = tmp[r.out.item] || []).push(r);
      for (const i of r.in) (D.usedIn[i.item] = D.usedIn[i.item] || []).push(r);
    }
    for (const it of Object.values(D.items)) {
      const list = it.recipes ? it.recipes.map((rid) => D.recipeById[rid]).filter((r) => r && r.out.item === it.id) : (tmp[it.id] || []);
      for (const r of tmp[it.id] || []) if (list.indexOf(r) < 0) list.push(r);
      gradeSort(list, family, (r) => GRADE_RANK[r.quality]);
      if (list.length) D.byOut[it.id] = list;
      if (it.defaultRecipe === undefined) { // older JSON: first usable recipe
        const f = list.find((r) => !r.noexp && !r.cyc && r.in.length);
        it.defaultRecipe = f ? f.id : null;
      }
      if (it.defaultRecipe && !D.recipeById[it.defaultRecipe]) it.defaultRecipe = null;
    }
    // search index: normalized names in every language, words pre-split
    D.index = Object.values(D.items).map((it) => ({
      id: it.id, hidden: it.hidden, craft: !!it.defaultRecipe,
      names: LANGS.map((l) => { const n = norm(it[l]); return { l, n, w: words(n) }; }),
    }));
    D.visibleCount = D.index.filter((e) => !e.hidden).length;
    if (D.meta.sprite) GK.util.setSprite(D.meta.sprite);
    return D;
  }
  return {
    load, norm, words, parseBonus, GRADE_RANK, itemGrade, lineGrade, family, gradeSort, stripGrade, gradeMoves,
    get: () => D,
    perks: () => D.perks,
    item: (id) => D.items[id],
    recipe: (id) => D.recipeById[id],
    recipesFor: (id) => D.byOut[id] || [],
  };
})();
