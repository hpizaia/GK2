/* GK.data: loads and normalizes the embedded JSON (the gk2-data script block, schema 1, see
   scripts/README-build.md). Accepts collapsed localized values: a plain string stands for {pt: s, en: s}, and a
   field the build left out holds its default value (build.py drop_defaults: listed true, cd false, icon null…).
   Owns: items, stations, recipes and their indexes (byOut, usedIn, search index); meta (built, version,
   changelog, sprite); the perk list (D.perks); the payload's technology tree block as D.techs (raw; GK.tech
   normalizes it).
   Exposes: GK.data.{load, get, item, recipe, recipesFor, loc, norm, words, perks, spritePos} (+ the grade helpers below).
   loc(v): a localized value ({pt, en} or one string for every language) as {pt, en, …}, a missing language filled
   from en (else pt); null for none. Also read by GK.tech and GK.ui.days for their blocks of the payload.
   Read as the build sets them (scripts/build.py apply_grades / apply_bonuses; data/README-data.md "Quality grades"):
   - item.grade = "bronze" | "silver" | "gold": a quality variant ("wine-silver", base "wine") and the plain item of a
     family with silver / gold (the bronze one: "wine", "pumpkin", "cabbage-seed"). Shown as the star in the icon
     corner (GK.util.slot); a variant without its own icon draws its base's (meta.sprite.icons).
   - recipe.quality = the grade of the variant it makes, else the "(grade)" its name ends with ("Cabbage soup from
     Cabbage (gold)"); never read from the id alone (Bronze Polido has none). null: no grade.
   - line.grade: the plain input a "<X> from <Y> (bronze)" recipe names; line.anyGrade: the input of "<X> from Any
     <Y>" (any grade, no star). lineGrade(line) = the grade a line shows.
   - line.bonus = {perk: "X" (en), perks: [perkId], qty: M | null, add: N | null} on the input / by-product / output
     notes shaped "N (M with X)", "N, or M with X", "+N each with X" or "M with X"; D.perks = {id: {id, en, pt, uses}}.
   Still done here: the recipes of an item, by family (same id but the grade suffix), always come bronze, silver,
   gold (gradeSort keeps the positions the family holds in the list); the item lists sort by name with the family
   together (gradeSort, together = true: it depends on the language and the player's renames). A plan saved before
   the grades were kept is moved by GK.store (gradeMoves).
   Also exposes GK.data.{GRADE_RANK, itemGrade, lineGrade, family, gradeSort, stripGrade}.
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
  // together (the item lists and the search): the family also comes in one run, where its first member was
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
    return withGrade(line, x);
  }
  // the build's line.grade / line.anyGrade / line.bonus (see the header), copied onto a normalized line
  function withGrade(line, x) {
    if (x.grade) line.grade = x.grade;
    if (x.anyGrade) line.anyGrade = true;
    const b = x.bonus;
    if (b) line.bonus = { perk: b.perk, perks: b.perks, qty: b.qty != null ? b.qty : null, add: b.add != null ? b.add : null };
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
    if (typeof r.out === "object") withGrade(out, r.out);
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
      quality: GRADE_RANK[r.quality] != null ? r.quality : null,
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
    for (const [id, p] of Object.entries(j.perks || {})) D.perks[id] = { id, en: p.en, pt: p.pt != null ? p.pt : p.en, uses: p.uses || 0 };
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
  // [col, row] of a sprite id (item / station id, "tech:<slug>", "tp:<colour>", "day:<id>") in meta.sprite; null if absent
  const spritePos = (id) => {
    const sp = D.meta && D.meta.sprite;
    return sp && sp.icons && id ? sp.icons[id] : null;
  };
  return {
    load, loc, norm, words, spritePos, GRADE_RANK, itemGrade, lineGrade, family, gradeSort, stripGrade,
    get: () => D,
    perks: () => D.perks,
    item: (id) => D.items[id],
    recipe: (id) => D.recipeById[id],
    recipesFor: (id) => D.byOut[id] || [],
  };
})();
