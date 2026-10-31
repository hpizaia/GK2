/* GK.calc: pure planning and search functions (no DOM, no state).
   Exposes: GK.calc.{plan, search, howToMake, orderStations, isBonusActive}.
*/
GK.calc = (function () {
  // a bonus line ({perks, qty, add}) is active when every perk it names is on
  const active = (b, perks) => !!(b && perks && b.perks && b.perks.length && b.perks.every((p) => perks[p]));
  // the quantity a line / output has under the active perks (null bonus qty = unknown → base)
  function boosted(base, b, perks) {
    if (!active(b, perks)) return null;
    if (b.qty != null) return b.qty;
    if (b.add != null && base != null) return base + b.add;
    return null;
  }
  /**
   * How an item is made under the user's choices:
   *   { r, yield, ins, outBonus }  expand with recipe r (yield = net output per run, ins = inputs minus self,
   *                                with perk bonuses applied: such a line is a copy with boosted: true)
   *   { leaf: reason }             "have" | "raw" | "group" | "noexp" | "free" | "refused"
   * Rules: user choice (state.choice) else item.defaultRecipe; null → leaf; a recipe needs ≥1 input
   * and noexp=false to expand; an input equal to the output is netted out, refused when net ≤ 0.
   * have[id] === true is a leaf ("Já tenho" everything); a number is partial stock, handled by plan().
   */
  function howToMake(id, D, choice, have, perks) {
    const it = D.items[id];
    if (!it) return { leaf: "raw" };
    if (have && have[id] === true) return { leaf: "have" };
    let r = null;
    const c = choice && choice[id] && D.recipeById[choice[id]];
    if (c && c.out.item === id) r = c;
    else if (it.defaultRecipe) r = D.recipeById[it.defaultRecipe] || null;
    if (!r) return { leaf: it.members ? "group" : "raw" };
    if (r.noexp) return { leaf: "noexp", r };
    if (!r.in.length) return { leaf: "free", r };
    let self = 0;
    const ins = [];
    for (const i of r.in) {
      const q = boosted(i.qty, i.bonus, perks);
      const line = q != null && q !== i.qty ? Object.assign({}, i, { qty: q, boosted: true }) : i;
      if (line.item === id) self += line.qty; else if (line.qty > 0) ins.push(line);
    }
    const oq = boosted(r.out.qty || 1, r.out.bonus, perks);
    const y = (oq != null ? oq : r.out.qty || 1) - self;
    if (y <= 0 || !ins.length) return { leaf: "refused", r };
    return { r, yield: y, ins, outBonus: oq != null ? r.out.bonus : null };
  }

  /**
   * Station cards in dependency order: no card needs an item made by a card below it.
   * One card per station when that order exists (Kahn, ties by first stage); when two stations feed each
   * other (A → B → A), a station gets a second card further down (greedy by stage).
   * steps: [{item, stage, recipe, ins}], producerOf(step) → [step].
   */
  function orderStations(steps, producersOf) {
    const mk = (st) => ({ station: st, steps: [], minStage: Infinity, maxStage: 0 });
    const add = (g, s) => { g.steps.push(s); g.minStage = Math.min(g.minStage, s.stage); g.maxStage = Math.max(g.maxStage, s.stage); };
    const finish = (cards) => {
      const seen = {};
      cards.forEach((g) => {
        g.steps.sort((a, b) => a.stage - b.stage);
        const k = g.station.id;
        seen[k] = (seen[k] || 0) + 1;
        g.repeat = seen[k];      // 1 = first card of this station, 2 = it comes back later, …
      });
      return cards;
    };
    const groups = new Map();
    for (const s of steps) {
      const k = s.recipe.station.id;
      if (!groups.has(k)) groups.set(k, mk(s.recipe.station));
      add(groups.get(k), s);
    }
    const cards = [...groups.values()];
    const key = (s) => s.recipe.station.id;
    const deps = new Map(cards.map((g) => [g, new Set()]));
    for (const g of cards) for (const s of g.steps) for (const p of producersOf(s)) if (key(p) !== g.station.id) deps.get(g).add(groups.get(key(p)));
    // Kahn, picking the ready card with the lowest first stage
    const out = [], left = new Set(cards);
    while (left.size) {
      let best = null;
      for (const g of left) {
        let ok = true;
        for (const d of deps.get(g)) if (left.has(d)) { ok = false; break; }
        if (ok && (!best || g.minStage < best.minStage || (g.minStage === best.minStage && g.maxStage < best.maxStage))) best = g;
      }
      if (!best) break;
      out.push(best); left.delete(best);
    }
    if (!left.size) return finish(out);
    // cyclic between stations: walk steps by stage; reuse the station's last card when it is not above a producer
    const byStage = steps.slice().sort((a, b) => a.stage - b.stage);
    const res = [], last = {}, cardOf = new Map();
    for (const s of byStage) {
      let p = -1;
      for (const q of producersOf(s)) if (cardOf.has(q)) p = Math.max(p, cardOf.get(q));
      const k = key(s);
      let idx = last[k];
      if (idx == null || idx < p) { idx = res.length; res.push(mk(s.recipe.station)); last[k] = idx; }
      add(res[idx], s); cardOf.set(s, idx);
    }
    return finish(res);
  }

  /**
   * plan(goals, D, {choice, have, stock, perks, groupChoice}) →
   *   raw:      [{ item, qty, have, cycle, reason, isGoal, demand, haveQty, covered, via }]   leaves (what to gather/buy)
   *             have = "Já tenho" (true, or a number that covers the whole demand: covered = true);
   *             haveQty = the number the user typed ("tenho N de M", M = demand) or null;
   *             via = [groupId] when this member stands in for a group item (state.groupChoice)
   *   steps:    [{ item, recipe, yield, ins, need, runs, produced, leftover, stage, isGoal, alts, demand, haveQty,
   *               outBonus, quality }]
   *   stations: [{ station, steps, minStage, maxStage, repeat }]   in dependency order (see orderStations)
   *   cycles:   [itemId]   reappeared on its own expansion path: that occurrence is a leaf
   *   refused:  [itemId]   the chosen recipe consumes the item itself with no net gain
   *   perks:    [{ id, active }]   perks whose bonus notes appear in this plan's recipes (UI: "Vantagens")
   * Demand is aggregated over the whole goal list in topological order before any rounding:
   * need = max(0, demand − stock − have), runs = ceil(need / yield), each input += runs × qty.
   * A group item with a chosen member (groupChoice[group] = member) is replaced by that member everywhere,
   * so its demand merges with any other demand for the member.
   * Cycle cut (AUDITORIA C5): the back edge found first by the DFS (goal order) becomes the leaf, so [A, B]
   * and [B, A] can differ on a user-made cycle. The default recipe graph has none.
   */
  function plan(goals, D, opt) {
    const o = opt || {};
    const choice = o.choice || {}, have = o.have || {}, stock0 = o.stock || {};
    const perks = o.perks || {}, gc = o.groupChoice || {};
    const haveNum = (id) => (typeof have[id] === "number" && have[id] > 0 ? have[id] : 0);
    const stockOf = (id) => (stock0[id] || 0) + haveNum(id);
    const sub = (id) => {
      const it = D.items[id], m = gc[id];
      return m && it && it.members && it.members.indexOf(m) >= 0 && D.items[m] ? m : id;
    };
    const via = {};
    const noteVia = (g, m) => { if (g !== m) (via[m] = via[m] || new Set()).add(g); };
    const how = {};
    const hw = (id) => how[id] || (how[id] = howToMake(id, D, choice, have, perks));
    const isLeaf = (id) => !!hw(id).leaf;
    const insCache = {};
    const insOf = (id) => insCache[id] || (insCache[id] = hw(id).ins.map((l) => {
      const t = sub(l.item);
      if (t === l.item) return l;
      noteVia(l.item, t);
      return Object.assign({}, l, { item: t, group: l.item });
    }));
    const roots = [];
    for (const g of goals) {
      if (!D.items[g.item] || !(g.qty > 0)) continue;
      const t = sub(g.item);
      noteVia(g.item, t);
      roots.push({ item: t, qty: g.qty });
    }

    // DFS post-order (inputs before consumers). An input already on the current expansion path
    // closes a loop: that edge is cut (its demand goes to loopDemand, a leaf) and the rest of the
    // graph stays expanded. Cutting every back-edge leaves a DAG, so `order` is topological.
    const order = [], color = {}, cut = new Set(), looped = new Set();
    const visit = (id) => {
      color[id] = 1;
      if (!isLeaf(id)) {
        for (const i of insOf(id)) {
          if (color[i.item] === 1) { cut.add(id + ">" + i.item); looped.add(i.item); }
          else if (!color[i.item]) visit(i.item);
        }
      }
      color[id] = 2;
      order.push(id);
    };
    roots.forEach((g) => { if (!color[g.item]) visit(g.item); });

    const demand = {}, loopDemand = {};
    for (const g of roots) demand[g.item] = (demand[g.item] || 0) + g.qty;
    const goalSet = new Set(roots.map((g) => g.item));
    const stepsById = {}, covered = new Set();
    for (let k = order.length - 1; k >= 0; k--) { // consumers before producers
      const id = order[k];
      if (isLeaf(id)) continue;
      const dem = demand[id] || 0;
      const need = Math.max(0, dem - stockOf(id));
      if (!need) { if (dem > 0 && haveNum(id)) covered.add(id); continue; }
      const h = hw(id), ins = insOf(id);
      const runs = Math.ceil(need / h.yield), produced = runs * h.yield;
      for (const i of ins) {
        const bucket = cut.has(id + ">" + i.item) ? loopDemand : demand;
        bucket[i.item] = (bucket[i.item] || 0) + runs * i.qty;
      }
      stepsById[id] = {
        item: id, recipe: h.r, yield: h.yield, ins, need, runs, produced, leftover: produced - need,
        stage: 0, isGoal: goalSet.has(id), alts: (D.byOut[id] || []).length,
        demand: dem, haveQty: haveNum(id) || null, outBonus: h.outBonus || null, quality: h.r.quality || null,
      };
    }
    const stage = {};
    for (const id of order) { // post-order → inputs already staged
      if (!stepsById[id]) { stage[id] = 0; continue; }
      let m = 0;
      for (const i of stepsById[id].ins) if (!cut.has(id + ">" + i.item)) m = Math.max(m, stage[i.item] || 0);
      stage[id] = m + 1;
      stepsById[id].stage = m + 1;
    }
    const refused = [];
    const raw = [];
    const viaOf = (id) => (via[id] ? [...via[id]] : null);
    for (const id of order) {
      const dem = demand[id] || 0;
      const leaf = isLeaf(id);
      const own = leaf ? Math.max(0, dem - stockOf(id)) : 0;
      const loop = loopDemand[id] || 0;
      const base = { item: id, isGoal: goalSet.has(id), demand: dem + loop, haveQty: haveNum(id) || null, via: viaOf(id) };
      if (own + loop <= 0) {
        // "tenho N de M" covering everything: listed with the things the user already has
        if (dem > 0 && haveNum(id) && (leaf || covered.has(id))) raw.push(Object.assign(base, { qty: dem, have: true, covered: true, cycle: false, reason: "have" }));
        continue;
      }
      const reason = own ? hw(id).leaf : "cycle";
      if (reason === "refused") refused.push(id);
      raw.push(Object.assign(base, { qty: own + loop, have: reason === "have", covered: false, cycle: loop > 0, reason }));
    }
    const steps = Object.values(stepsById);
    const producersOf = (s) => s.ins.filter((i) => !cut.has(s.item + ">" + i.item) && stepsById[i.item]).map((i) => stepsById[i.item]);
    const stations = orderStations(steps, producersOf);
    // perks that matter for this plan: any bonus note on a step's recipe (inputs, output, by-products)
    const pk = new Set();
    for (const s of steps) {
      const r = s.recipe;
      for (const l of r.in.concat(r.extra, [r.out])) if (l.bonus) l.bonus.perks.forEach((p) => pk.add(p));
    }
    const perkList = [...pk].sort().map((id) => ({ id, active: !!perks[id] }));
    return { raw, steps, stations, cycles: [...looped].filter((id) => loopDemand[id] > 0), refused, perks: perkList };
  }

  // a ≈ b within one edit (substitution, insertion or deletion)
  function oneEdit(a, b) {
    if (Math.abs(a.length - b.length) > 1) return false;
    let i = 0, j = 0, d = 0;
    while (i < a.length && j < b.length) {
      if (a[i] === b[j]) { i++; j++; continue; }
      if (++d > 1) return false;
      if (a.length > b.length) i++; else if (b.length > a.length) j++; else { i++; j++; }
    }
    return d + (a.length - i) + (b.length - j) <= 1;
  }
  // token ≈ start of word, one typo allowed for tokens of 4+ letters ("mestre" ~ "mestra")
  const nearPrefix = (t, w) => t.length >= 4 && (oneEdit(t, w.slice(0, t.length)) || oneEdit(t, w.slice(0, t.length + 1)) || oneEdit(t, w.slice(0, t.length - 1)));
  function scoreName(e, q, toks) {
    const n = e.n;
    if (!n) return 0;
    if (n === q) return 120;
    if (n.startsWith(q)) return 100 - Math.min(20, (n.length - q.length) * 0.5);
    if (toks.every((t) => e.w.some((w) => w.startsWith(t)))) return 80;
    if (n.includes(q)) return 60;
    if (toks.every((t) => e.w.some((w) => w.startsWith(t) || nearPrefix(t, w)))) return 50;
    const qq = q.replace(/\s+/g, "");
    if (qq.length >= 3) { // light fuzzy: in-order subsequence, fewer gaps = better
      let i = 0, gaps = 0, last = -1;
      for (let j = 0; j < n.length && i < qq.length; j++) {
        if (n[j] === qq[i]) { if (last >= 0) gaps += j - last - 1; last = j; i++; }
      }
      if (i === qq.length && gaps <= qq.length * 2) return Math.max(5, 40 - gaps * 3);
    }
    return 0;
  }
  /**
   * search(query, D, {lang, overrides, limit, showHidden}) → { results: [{id, score, hidden}], hiddenCount }
   * Matches every language (and the user's edited names) on a prebuilt index.
   */
  function search(query, D, opt) {
    const norm = GK.data.norm, words = GK.data.words;
    const q = norm(query);
    if (!q) return { results: [], hiddenCount: 0 };
    const toks = q.split(/\s+/).filter(Boolean);
    const lang = (opt && opt.lang) || "pt", ov = (opt && opt.overrides && opt.overrides[lang]) || {};
    const showHidden = !!(opt && opt.showHidden);
    const out = [];
    let hiddenCount = 0;
    for (const e of D.index) {
      let best = 0;
      for (const nm of e.names) { let sc = scoreName(nm, q, toks); if (sc > 0 && nm.l === lang) sc += 2; if (sc > best) best = sc; }
      if (ov[e.id]) { const n = norm(ov[e.id]); const sc = scoreName({ n, w: words(n) }, q, toks) + 3; if (sc > 3 && sc > best) best = sc; }
      if (best <= 0) continue;
      if (e.hidden && !showHidden) { hiddenCount++; continue; }
      out.push({ id: e.id, hidden: e.hidden, score: best + (e.craft ? 4 : 0) - (e.hidden ? 6 : 0) });
    }
    const label = (id) => ov[id] || D.items[id][lang] || D.items[id].en;
    out.sort((a, b) => b.score - a.score || label(a.id).localeCompare(label(b.id)));
    return { results: out.slice(0, (opt && opt.limit) || 10), hiddenCount };
  }
  return { plan, search, howToMake, orderStations, isBonusActive: active };
})();
