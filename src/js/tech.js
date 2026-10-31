/* GK.tech: pure functions over the technologies graph (no DOM besides reading the data block once).
   Source: the payload's `techs` block ({tp, branches, techs}, compact copy of data/techs.json written by
   scripts/build.py), kept raw by GK.data as GK.data.get().techs and normalized here on first use.
   Owns: the normalized tree (techs by id with derived children / recipes, branches in tab order, point colours).
   Exposes: GK.tech.{available, get, all, branches, branch, inBranch, tp, COLORS, ancestors, researchedSet,
   required, costOf, order, forPlan, isFree, init}.

   A tech = {id, pt, en, tr, branch, column, y, cost: {red, green, blue}, parents[], children[], hidden, given,
             free (cost 0), rep: {who: {pt, en}, level} | null, unlocks: [{item, kind, pt, en, tr, station}],
             icon (sprite id), notes: {pt, en} | null, recipes: [recipe ids], rank (research order index)}
   "Researched" = state.researched {id: true}; researching a tech implies all of its ancestors, so every
   function that takes `researched` uses researchedSet() (marked + their ancestors).
*/
GK.tech = (function () {
  const COLORS = ["red", "green", "blue"];
  let raw = null;   // the payload's techs block (GK.data.get().techs, or GK.tech.init(src))
  let injected = false;   // init(src) was called: keep that source
  let T = null;     // normalized tree (lazy, after GK.data.load)

  let seen = undefined;   // the GK.data block `raw` was read from (a new GK.data.load() rebuilds the tree)

  const loc = (v) => {
    if (v == null || v === "") return null;
    if (typeof v === "string") return { pt: v, en: v };
    const o = Object.assign({}, v);
    if (o.pt == null) o.pt = o.en;
    if (o.en == null) o.en = o.pt;
    return o;
  };
  const num = (v) => (typeof v === "number" && isFinite(v) ? v : 0);

  function build(src) {
    const D = (GK.data && GK.data.get()) || { items: {}, stations: {}, recipes: [] };
    const out = { tp: {}, branches: [], branchById: {}, byId: {}, list: [] };
    if (!src || !src.techs) return out;
    for (const c of COLORS) {
      const v = (src.tp && src.tp[c]) || {};
      out.tp[c] = Object.assign({ id: c, icon: "tp:" + c, color: null }, loc(v) || { pt: c, en: c }, { id: c });
    }
    Object.entries(src.branches || {}).forEach(([id, v], i) => {
      const b = Object.assign({ id, order: i, icon: "branch:" + id, tr: "official" }, loc(v), { id });
      out.branches.push(b);
      out.branchById[id] = b;
    });
    out.branches.sort((a, b) => a.order - b.order);
    for (const [id, t] of Object.entries(src.techs)) {
      const c = Array.isArray(t.cost) ? t.cost : t.cost ? COLORS.map((k) => t.cost[k]) : [0, 0, 0];
      const cost = { red: num(c[0]), green: num(c[1]), blue: num(c[2]) };
      if (!out.branchById[t.branch]) {
        const b = { id: t.branch, pt: t.branch, en: t.branch, order: 99, icon: null, tr: "missing" };
        out.branches.push(b); out.branchById[t.branch] = b;
      }
      out.byId[id] = {
        id, pt: t.pt || t.en || id, en: t.en || t.pt || id, tr: t.tr || "official",
        branch: t.branch, column: num(t.column), y: num(t.y), cost,
        parents: (t.parents || []).slice(), children: [],
        hidden: !!t.hidden, given: !!t.given, free: !cost.red && !cost.green && !cost.blue,
        listed: t.listed !== false,
        rep: t.rep ? { who: loc(t.rep.who), level: t.rep.level } : null,
        unlocks: (t.unlocks || []).map((u0) => {
          const u = typeof u0 === "string" ? { pt: u0, en: u0 } : u0;
          const ent = u.item ? D.items[u.item] || D.stations[u.item] : null;
          const nm = u.pt || u.en ? loc({ pt: u.pt, en: u.en }) : ent ? { pt: ent.pt, en: ent.en } : { pt: "?", en: "?" };
          return { item: u.item || null, kind: u.kind || "item", pt: nm.pt, en: nm.en,
            tr: u.tr || (u.pt || u.en ? "official" : (ent && ent.tr) || "official"), station: u.station || null };
        }),
        icon: t.icon || null,
        notes: loc(t.notes),
        recipes: [],
        rank: 0,
      };
    }
    // drop dangling parents, derive children
    for (const t of Object.values(out.byId)) {
      t.parents = t.parents.filter((p) => out.byId[p]);
      for (const p of t.parents) out.byId[p].children.push(t.id);
    }
    for (const r of D.recipes || []) {
      if (r.tech && r.tech.type === "technology" && out.byId[r.tech.id]) out.byId[r.tech.id].recipes.push(r.id);
    }
    const bOrder = (t) => (out.branchById[t.branch] ? out.branchById[t.branch].order : 99);
    const cmp = (a, b) => bOrder(a) - bOrder(b) || a.column - b.column || a.y - b.y || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    out.list = Object.values(out.byId).sort(cmp);
    out.list.forEach((t, i) => { t.rank = i; });
    for (const t of out.list) t.children.sort((a, b) => out.byId[a].rank - out.byId[b].rank);
    return out;
  }
  function tree() {
    const D = GK.data && GK.data.get ? GK.data.get() : null;
    if (!injected && D && D.techs !== seen) { seen = D.techs; raw = D.techs || null; T = null; }
    return T || (T = build(raw));
  }

  const get = (id) => tree().byId[id] || null;
  const all = () => tree().list.slice();
  const branches = () => tree().branches.slice();
  const branch = (id) => tree().branchById[id] || null;
  const inBranch = (id) => tree().list.filter((t) => t.branch === id);
  const tp = () => tree().tp;
  const isFree = (t) => !!t && t.free;
  // research order: (branch order, column, y). Parents always come first: no edge crosses branches and
  // every parent sits in a lower column.
  const order = (list) => (list || []).map((x) => (typeof x === "string" ? get(x) : x)).filter(Boolean).sort((a, b) => a.rank - b.rank);

  // every ancestor of the given ids (not the ids themselves), in research order
  function ancestors(ids) {
    const seen = new Set(), stack = [];
    for (const id of [].concat(ids || [])) { const t = get(id); if (t) stack.push(...t.parents); }
    while (stack.length) {
      const id = stack.pop();
      if (seen.has(id)) continue;
      seen.add(id);
      const t = get(id);
      if (t) stack.push(...t.parents);
    }
    return order([...seen]);
  }
  // marked techs + every ancestor of a marked tech
  function researchedSet(researched) {
    const marked = Object.keys(researched || {}).filter((id) => researched[id] && get(id));
    const s = new Set(marked);
    for (const t of ancestors(marked)) s.add(t.id);
    return s;
  }
  /** required(techIds, researched) → techs still to research for those ids (ids + their missing ancestors),
   *  in research order, each once. Walk up the parents with a seen-set; stop at researched ones. */
  function required(techIds, researched) {
    const done = researched instanceof Set ? researched : researchedSet(researched);
    const seen = new Set(), stack = [].concat(techIds || []).filter((id) => get(id));
    while (stack.length) {
      const id = stack.pop();
      if (seen.has(id) || done.has(id)) continue;
      seen.add(id);
      stack.push(...get(id).parents);
    }
    return order([...seen]);
  }
  function costOf(list) {
    const c = { red: 0, green: 0, blue: 0 };
    for (const x of list || []) {
      const t = typeof x === "string" ? get(x) : x;
      if (t) COLORS.forEach((k) => { c[k] += t.cost[k]; });
    }
    return c;
  }

  /**
   * forPlan(plan, state) → {
   *   techs:  [tech]   still to research for the plan, in research order (ancestors included)
   *   direct: [id]     techs named by a recipe of the plan (subset of techs, researched ones dropped)
   *   cost:   {red, green, blue}
   *   other:  [{type: "quest" | "perk", id, pt, en, items: [itemId]}]   non-technology unlocks
   *   why:    {techId: [itemId]}   plan items (steps, gathered/grown leaves, stations) whose recipe names it
   *   flags:  {rep, hidden, given, free}   counts among techs
   *   signature: string             changes only when the result can change (memo key)
   * }
   * Recipes looked at: every plan step's recipe; leaves made by a zero-input or grow recipe (state.choice /
   * defaultRecipe, via GK.calc.howToMake); the build recipe of every station the steps use.
   */
  function planRecipes(plan, state) {
    const D = GK.data.get(), out = [];
    if (!plan) return out;
    const st = state || {};
    for (const s of plan.steps || []) if (s.recipe) out.push([s.recipe, s.item]);
    for (const r of plan.raw || []) {
      if (r.have) continue;
      const h = GK.calc.howToMake(r.item, D, st.choice || {}, st.have || {});
      if (h.r && (h.leaf === "free" || h.leaf === "noexp")) out.push([h.r, r.item]);
    }
    for (const g of plan.stations || []) {
      const sid = g.station && g.station.id, it = sid && D.items[sid];
      if (!it || (st.have && st.have[sid])) continue;
      const r = (it.defaultRecipe && D.recipeById[it.defaultRecipe]) || (D.byOut[sid] || [])[0];
      if (r) out.push([r, sid]);
    }
    return out;
  }
  function signature(plan, state) {
    const ids = planRecipes(plan, state).map(([r, item]) => (r.tech ? r.tech.type + ":" + (r.tech.id || r.tech.en) + "@" + item : "")).filter(Boolean);
    const res = Object.keys((state && state.researched) || {}).filter((k) => state.researched[k]).sort();
    return [...new Set(ids)].sort().join(",") + "|" + res.join(",");
  }
  function forPlan(plan, state) {
    const why = {}, others = new Map();
    for (const [r, item] of planRecipes(plan, state)) {
      const tc = r.tech;
      if (!tc) continue;
      if (tc.type === "technology" || !tc.type) {
        if (!get(tc.id)) continue;
        const w = (why[tc.id] = why[tc.id] || []);
        if (w.indexOf(item) < 0) w.push(item);
      } else {
        const key = tc.type + ":" + (tc.id || tc.en);
        if (!others.has(key)) others.set(key, { type: tc.type, id: tc.id || null, pt: tc.pt || tc.en, en: tc.en || tc.pt, items: [] });
        const o = others.get(key);
        if (o.items.indexOf(item) < 0) o.items.push(item);
      }
    }
    const done = researchedSet(state && state.researched);
    const techs = required(Object.keys(why), done);
    const flags = { rep: 0, hidden: 0, given: 0, free: 0 };
    for (const t of techs) {
      if (t.rep) flags.rep++;
      if (t.hidden) flags.hidden++;
      if (t.given) flags.given++;
      if (t.free) flags.free++;
    }
    return {
      techs, direct: Object.keys(why).filter((id) => !done.has(id)), cost: costOf(techs), why,
      other: [...others.values()].sort((a, b) => (a.type < b.type ? -1 : a.type > b.type ? 1 : 0)),
      flags, signature: signature(plan, state),
    };
  }

  return {
    available: () => tree().list.length > 0,
    init(src) { injected = src !== undefined; raw = src || null; T = null; return tree(); },   // tests / another data source
    get, all, branches, branch, inBranch, tp, COLORS, isFree, order,
    ancestors, researchedSet, required, costOf, forPlan, signature,
  };
})();
