#!/usr/bin/env node
/* Tests for the planner's pure modules: GK.data, GK.calc, GK.store, GK.sync (and GK.ui.fmt's recipe labels).
   No dependencies. Run from anywhere:  node scripts/test_calc.mjs
   The modules are loaded from src/js/ in src/manifest.json order (only the ones listed in MODULES) inside a vm
   context with a fake window / document / localStorage and a fake clock; the dataset is the payload embedded
   in prototype/index.html (the "collapsed" page form), or data/gk2.json when the page has not been built. */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MODULES = ["js/core.js", "js/util.js", "js/i18n.js", "js/data.js", "js/store.js", "js/calc.js", "js/sync.js", "js/ui/fmt.js"];

// ---------------------------------------------------------------- tiny test runner
let passed = 0, failed = 0;
const failures = [];
function check(cond, msg) { if (cond) passed++; else { failed++; failures.push(msg); } }
function eq(a, b, msg) { const ok = JSON.stringify(a) === JSON.stringify(b); check(ok, `${msg}: expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`); }
async function test(name, fn) {
  const before = failed;
  try { await fn(); } catch (e) { failed++; failures.push(`${name}: threw ${e && e.stack || e}`); }
  console.log(`${failed === before ? "ok  " : "FAIL"}  ${name}`);
}

// ---------------------------------------------------------------- environment
function loadPayload() {
  const page = path.join(ROOT, "prototype/index.html");
  if (fs.existsSync(page)) {
    const html = fs.readFileSync(page, "utf8");
    const m = /<script id="gk2-data" type="application\/json">([\s\S]*?)<\/script>/.exec(html);
    if (m && m[1].trim() && !m[1].includes("@data")) return JSON.parse(m[1]);
  }
  return JSON.parse(fs.readFileSync(path.join(ROOT, "data/gk2.json"), "utf8"));
}
const PAYLOAD = loadPayload();

function makeEnv() {
  // fake clock: setTimeout / setInterval run only when the test calls clock.tick(ms)
  let now = 0, seq = 0;
  const timers = new Map();
  const clock = {
    setTimeout(fn, ms) { const id = ++seq; timers.set(id, { at: now + (ms || 0), fn, every: 0 }); return id; },
    setInterval(fn, ms) { const id = ++seq; timers.set(id, { at: now + (ms || 0), fn, every: Math.max(1, ms || 0) }); return id; },
    clearTimeout(id) { timers.delete(id); },
    async tick(ms) {
      const end = now + ms;
      for (;;) {
        let next = null;
        for (const [id, t] of timers) if (t.at <= end && (!next || t.at < next[1].at)) next = [id, t];
        if (!next) break;
        const [id, t] = next;
        now = t.at;
        if (t.every) t.at += t.every; else timers.delete(id);
        t.fn();
        await flushMicro();
      }
      now = end;
      await flushMicro();
    },
  };
  const store = new Map();
  const localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => { store.set(k, String(v)); },
    removeItem: (k) => { store.delete(k); },
    _map: store,
  };
  const listeners = {};
  const on = (t, f) => { (listeners[t] = listeners[t] || []).push(f); };
  const el = () => ({ style: {}, setAttribute() {}, appendChild() {}, addEventListener() {}, textContent: "" });
  const document = {
    addEventListener: on, removeEventListener() {}, createElement: el, head: el(), body: el(),
    documentElement: { lang: "", style: { setProperty() {} } },
    getElementById: () => null, querySelector: () => null, visibilityState: "visible",
  };
  const ctx = {
    console, Intl, JSON, Math, Date, Promise, Object, Array, String, Number, Set, Map, RegExp, Error, isFinite,
    Blob, TextEncoder,
    setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout, setInterval: clock.setInterval, clearInterval: clock.clearTimeout,
    document, navigator: { language: "pt-BR", languages: ["pt-BR"] }, localStorage,
    addEventListener: on, removeEventListener() {},
    _fire: (t, e) => (listeners[t] || []).forEach((f) => f(e || {})),
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  const src = MODULES.map((m) => `/* ${m} */\n` + fs.readFileSync(path.join(ROOT, "src", m), "utf8")).join("\n;\n");
  vm.runInContext('"use strict";\n' + src, ctx, { filename: "gk-modules.js" });
  const GK = ctx.GK;
  GK.i18n.set("pt");
  return { GK, ctx, clock, localStorage };
}
const flushMicro = () => new Promise((r) => setImmediate(r));

// one shared env for the pure parts
const { GK } = makeEnv();
const D = GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
const plan = (goals, opt) => GK.calc.plan(goals, D, opt || {});
const rawMap = (p) => Object.fromEntries(p.raw.map((r) => [r.item, r.qty]));
const stepOf = (p, id) => p.steps.find((s) => s.item === id);

// dependency invariant: no station card needs an item made by a card below it
function orderViolations(p) {
  const cardOf = new Map();
  p.stations.forEach((g, i) => g.steps.forEach((s) => cardOf.set(s.item, { i, stage: s.stage })));
  const bad = [];
  p.stations.forEach((g, i) => g.steps.forEach((s) => {
    for (const l of s.ins) {
      const c = cardOf.get(l.item);
      if (!c) continue;
      if (c.i > i || (c.i === i && c.stage >= s.stage)) bad.push(`${s.item} (card ${i}) needs ${l.item} (card ${c.i})`);
    }
  }));
  return bad;
}

// ---------------------------------------------------------------- calc: real cases (AUDITORIA §1)
await test("Caixote ×3", () => {
  const p = plan([{ item: "crate", qty: 3 }]);
  const r = rawMap(p);
  eq([r.log, r.fat, r.clay, r["iron-ore"]], [3, 1, 2, 3], "raw log/fat/clay/iron-ore");
  const crate = stepOf(p, "crate"), fuel = stepOf(p, "fuel");
  eq([crate.runs, crate.leftover], [2, 1], "crate runs/leftover");
  eq([fuel.need, fuel.runs, fuel.leftover], [50, 3, 10], "fuel need/runs/leftover");
  for (const s of p.steps) check(s.runs === Math.ceil(s.need / s.yield) && s.leftover >= 0 && s.leftover < s.yield, `invariant on ${s.item}`);
  eq(orderViolations(p), [], "station order");
});

await test("Espada Mestra ×1", () => {
  const r = rawMap(plan([{ item: "master-sword", qty: 1 }]));
  const want = { "steel-ingot": 4, sand: 3, log: 1, beeswax: 1 };
  for (const [k, v] of Object.entries(want)) eq(r[k], v, "raw " + k);
  const leaf = Object.entries(r).find(([k, v]) => D.items[k].en.toLowerCase() === "leaf");
  check(!!leaf && leaf[1] === 8, "8 Folha");
});

await test("Vinho ×5 and the cyclic refusal", () => {
  const p = plan([{ item: "wine", qty: 5 }]);
  const r = rawMap(p);
  eq([r.grapes, r.sand, r.log], [48, 6, 1], "raw grapes/sand/log");
  eq(stepOf(p, "fuel").need, 60, "fuel 60");
  // 1.9: "Wine (bronze) + Spices" makes Vinho (prata) now: chosen for "wine" it is not a recipe of that item (ignored)
  const q0 = plan([{ item: "wine", qty: 5 }], { choice: { wine: "drink-enhancement-i-from-wine-bronze" } });
  eq([q0.refused, rawMap(q0).grapes], [[], 48], "an old choice whose recipe now makes another grade is ignored");
  // the refusal itself: a recipe that consumes its own output (Aprimorar órgão I on Pele)
  const q = plan([{ item: "skin", qty: 5 }], { choice: { skin: "improve-organ-i-from-any-skin" } });
  eq(q.refused, ["skin"], "refused");
  const w = q.raw.find((x) => x.item === "skin");
  check(w && w.reason === "refused" && w.qty === 5, "skin becomes a raw material");
  eq(q.steps.length, 0, "nothing to craft");
});

await test("global aggregation before rounding (Caixote ×3 + Fornalha I + Espada, Kit de Madeira I in hand)", () => {
  const p = plan([{ item: "crate", qty: 3 }, { item: "furnace-i", qty: 1 }, { item: "master-sword", qty: 1 }], { have: { "wooden-kit-i": true } });
  const f = stepOf(p, "fuel");
  eq([f.need, f.runs], [70, 4], "fuel 70 → 4 runs");
  check(p.raw.some((r) => r.item === "wooden-kit-i" && r.have), "kit listed as had");
});

// ---------------------------------------------------------------- "tenho N de M"
await test("partial have: subtract before rounding", () => {
  const base = stepOf(plan([{ item: "crate", qty: 3 }]), "fuel");
  const p = plan([{ item: "crate", qty: 3 }], { have: { fuel: 25 } });
  const f = stepOf(p, "fuel");
  eq([f.demand, f.haveQty, f.need, f.runs], [base.need, 25, base.need - 25, Math.ceil((base.need - 25) / f.yield)], "fuel demand/have/need/runs");
  const lg = plan([{ item: "crate", qty: 3 }], { have: { log: 2 } }).raw.find((r) => r.item === "log");
  eq([lg.qty, lg.demand, lg.haveQty, lg.have], [1, 3, 2, false], "log: 1 left of 3");
  const all = plan([{ item: "crate", qty: 3 }], { have: { log: 5 } }).raw.find((r) => r.item === "log");
  eq([all.have, all.covered, all.qty, all.haveQty], [true, true, 3, 5], "log covered (5 ≥ 3)");
  const cov = plan([{ item: "crate", qty: 3 }], { have: { fuel: 999 } });
  check(!stepOf(cov, "fuel"), "fuel no longer crafted");
  const fr = cov.raw.find((r) => r.item === "fuel");
  check(fr && fr.have && fr.covered && fr.haveQty === 999, "fuel listed as covered");
  const tr = plan([{ item: "crate", qty: 3 }], { have: { fuel: true } }).raw.find((r) => r.item === "fuel");
  check(tr && tr.have && !tr.covered && tr.haveQty === null, "true still means everything");
});

// ---------------------------------------------------------------- group members
await test("group choice replaces the group and merges demand", () => {
  // Filé de peixe de rio: default recipe from a two-fish group ("Rutilo ou gróbio")
  const goal = "river-fish-fillet", rec = D.recipeById[D.items[goal].defaultRecipe];
  const G = rec.in.map((i) => i.item).find((id) => D.items[id].members), M = D.items[G].members[1];
  check(!!G && !!M, "a group input with members");
  const g0 = plan([{ item: goal, qty: 3 }]);
  const grp = g0.raw.find((r) => r.item === G);
  check(grp && grp.reason === "group", "group is a leaf by default");
  const p = plan([{ item: goal, qty: 3 }, { item: M, qty: 2 }], { groupChoice: { [G]: M } });
  check(!p.raw.some((r) => r.item === G), "group row gone");
  const m = p.raw.find((r) => r.item === M);
  eq(m && m.qty, grp.qty + 2, "member merged with the direct goal");
  eq(m && m.via, [G], "via");
  const line = stepOf(p, goal).ins.find((i) => i.item === M);
  check(line && line.group === G, "step line shows the member and remembers the group");
  const bad = plan([{ item: goal, qty: 1 }], { groupChoice: { [G]: "log" } });
  check(bad.raw.some((r) => r.item === G), "a non-member choice is ignored");
  const viaChoice = plan([{ item: goal, qty: 1 }], { choice: { [goal]: "river-fish-fillet-from-bream-or-carp" }, groupChoice: { "bream-or-carp": "carp" } });
  check(viaChoice.raw.some((r) => r.item === "carp" && r.via && r.via[0] === "bream-or-carp"), "works with a chosen recipe too (Brema ou carpa → Carpa)");
});

// ---------------------------------------------------------------- perk bonuses
await test("perk bonus notes are parsed (data load)", () => {
  const b = GK.data.parseBonus({ en: "3 (5 with Cook II)", pt: "3 (5 com Cozinheiro II)" });
  eq([b.perk, b.perks, b.qty, b.add], ["Cook II", ["cook-ii"], 5, null], "N (M with X)");
  eq(GK.data.parseBonus({ en: "1, or 2 with Cremator", pt: "1, ou 2 com Cremador" }).qty, 2, "N, or M with X");
  const c = GK.data.parseBonus({ en: "amount varies with the bed; +1 each with Farmer II and Grape Master", pt: "a quantidade varia conforme o canteiro; +1 cada com Fazendeiro II e Senhor das Uvas" });
  eq([c.perks, c.add, c.qty], [["farmer-ii", "grape-master"], 1, null], "+N each with X and Y");
  eq(GK.data.parseBonus({ en: "50% chance with Alchemist" }), null, "chance is not a quantity");
  const P = GK.data.perks();
  eq(P["heat-saver"] && P["heat-saver"].pt, "Economizador de Calor", "pt name from note.pt");
  eq(P["cremator"] && P["cremator"].pt, "Cremador", "Cremator → Cremador");
  check(P["farmer-ii"] && P["grape-master"], "both perks of an 'and' note");
});

await test("perk bonus changes the plan (Heat Saver) and the yield (synthetic Cook II)", () => {
  const r = D.recipeById["baked-apple"], fuelLine = r.in.find((i) => i.item === "fuel");
  check(fuelLine && fuelLine.bonus && fuelLine.bonus.qty === 5, "baked-apple fuel bonus 5 with Heat Saver");
  const off = plan([{ item: "baked-apple", qty: 5 }]), on = plan([{ item: "baked-apple", qty: 5 }], { perks: { "heat-saver": true } });
  const ln = (p) => stepOf(p, "baked-apple").ins.find((i) => i.item === "fuel");
  eq([ln(off).qty, ln(on).qty, !!ln(on).boosted], [10, 5, true], "fuel per craft off/on");
  eq(stepOf(on, "fuel").need, stepOf(off, "fuel").need / 2, "fuel demand halves");
  // baked-apple: "5 (7 with Cook)"; its fuel chain (firewood): "10 (15 with Axeman)"
  eq(off.perks, [{ id: "axeman", active: false }, { id: "cook", active: false }, { id: "heat-saver", active: false }], "plan.perks lists the relevant perks");
  eq(on.perks.find((p) => p.id === "heat-saver"), { id: "heat-saver", active: true }, "plan.perks active");
  // output bonus in a synthetic payload (out.note), then the real one (build.py exports made_text as out.note)
  const env = makeEnv();
  const mini = {
    meta: { schema: 1 },
    items: { stew: { pt: "Ensopado", en: "Stew", defaultRecipe: "stew" }, meat: { pt: "Carne", en: "Meat", raw: true, defaultRecipe: null } },
    stations: { pot: { pt: "Panela", en: "Pot" } },
    recipes: [{ id: "stew", out: { item: "stew", qty: 3, note: { pt: "3 (5 com Cozinheiro II)", en: "3 (5 with Cook II)" } }, station: "pot", in: [{ item: "meat", qty: 2 }] }],
  };
  const D2 = env.GK.data.load(mini);
  const a = env.GK.calc.plan([{ item: "stew", qty: 10 }], D2, {}), b = env.GK.calc.plan([{ item: "stew", qty: 10 }], D2, { perks: { "cook-ii": true } });
  eq([a.steps[0].yield, a.steps[0].runs, a.raw[0].qty], [3, 4, 8], "without Cook II");
  eq([b.steps[0].yield, b.steps[0].runs, b.raw[0].qty, b.steps[0].outBonus.perk], [5, 2, 4, "Cook II"], "with Cook II");
  eq(D2.perks["cook-ii"].pt, "Cozinheiro II", "pt perk name");
});

await test("real data: made_text yield bonuses (out.note) and star thresholds", () => {
  const r = D.recipeById["baked-fish"];
  eq([r.out.qty, r.out.note && r.out.note.en, r.out.note && r.out.note.pt], [3, "3 (5 with Cook II)", "3 (5 com Cozinheiro II)"], "baked-fish out.note");
  eq([r.out.bonus.perks, r.out.bonus.qty], [["cook-ii"], 5], "baked-fish out.bonus");
  eq(GK.data.perks()["cook-ii"].pt, "Cozinheiro II", "Cook II has its official pt name");
  const off = plan([{ item: "baked-fish", qty: 10 }]), on = plan([{ item: "baked-fish", qty: 10 }], { perks: { "cook-ii": true } });
  eq([stepOf(off, "baked-fish").yield, stepOf(off, "baked-fish").runs], [3, 4], "without Cook II: 3 per craft");
  eq([stepOf(on, "baked-fish").yield, stepOf(on, "baked-fish").runs, stepOf(on, "baked-fish").outBonus.perks], [5, 2, ["cook-ii"]], "with Cook II: 5 per craft");
  check(off.perks.some((p) => p.id === "cook-ii" && !p.active) && on.perks.some((p) => p.id === "cook-ii" && p.active), "Cook II chip listed");
  const nOut = D.recipes.filter((x) => x.out.bonus).length;
  check(nOut >= 100, `output bonuses parsed from made_text (${nOut})`);
  check(!D.recipeById["advanced-rod"].out.note, "a plain made_text equal to the qty is not exported");
  eq(D.recipeById["basic-prayer"].star, { silver: 6, gold: 10 }, "star_quality thresholds");
  eq(D.recipeById["basic-prayer"].quality, null, "a star threshold object is not a grade");
});

// ---------------------------------------------------------------- quality recipes
await test("gold/silver recipes consume the graded input and read differently", () => {
  const g = D.recipeById["baked-pumpkin-from-pumpkin-gold"], b = D.recipeById["baked-pumpkin-from-pumpkin-bronze"];
  eq(g.quality, "gold", "quality from the name");
  check(g.in.some((i) => i.item === "pumpkin-gold"), "gold recipe uses pumpkin-gold");
  check(b.in.some((i) => i.item === "pumpkin"), "bronze recipe keeps the plain pumpkin");
  const v = D.items["pumpkin-gold"];
  // 1.9: the build keeps the grade: a real item of the data (base pumpkin), not one the page makes up
  check(v && !v.synthetic && v.kind === "quality-variant" && v.base === "pumpkin" && v.pt === "Abóbora (ouro)", "real variant named in pt");
  check(!Object.values(D.items).some((it) => it.synthetic), "no synthetic variant left");
  check(D.recipeById["wine-from-grape-juice-gold"].in[0].item === "grape-juice-gold", "Barril: Suco de Uva (ouro) in");
  const p = plan([{ item: "baked-pumpkin", qty: 7 }], { choice: { "baked-pumpkin": g.id } });
  eq(rawMap(p)["pumpkin-gold"], 2, "plan asks for gold pumpkins");
  // no item's recipe chooser shows two options with the same text (letters aside)
  const st = GK.store.get();
  let dupes = [];
  for (const it of Object.values(D.items)) {
    const list = GK.data.recipesFor(it.id).filter((r) => r.in.length && !r.noexp);
    if (list.length < 2) continue;
    const labels = GK.ui.fmt.recipeLabels(list, st, GK.data.recipesFor(it.id)).map((s) => s.replace(/^[A-Z] · /, ""));
    if (new Set(labels).size !== labels.length) dupes.push(it.id);
  }
  eq(dupes, [], "identical recipe labels");
  // 1.4.1: two same-input recipes (Pele: "Improve organ I/II from Any Skin") are told apart by a short tag, not the
  // whole English name, so the raw-row selector stays narrow on a phone
  const skin = GK.ui.fmt.recipeLabels(GK.data.recipesFor("skin").filter((r) => r.in.length && !r.noexp), st, GK.data.recipesFor("skin"));
  check(skin.length === 2 && skin[0] !== skin[1] && skin.every((l) => !/ from /i.test(l) && l.length <= 70), "short distinct Pele labels: " + skin.join(" | "));
  let longTag = [];
  for (const it of Object.values(D.items)) {
    const list = GK.data.recipesFor(it.id).filter((r) => r.in.length && !r.noexp);
    if (list.length > 1) GK.ui.fmt.recipeLabels(list, st, list).forEach((l) => { const tag = l.split(" — ")[1]; if (tag && (tag.length > 34 || / from /i.test(tag))) longTag.push(l); });
  }
  eq(longTag, [], "dedupe tags stay short");
  const lab = GK.ui.fmt.recipeLabels([g], st, GK.data.recipesFor("baked-pumpkin"))[0];
  check(/ouro/.test(lab) && /Abóbora \(ouro\)/.test(lab) && /→ 7/.test(lab), "label shows grade, graded input and yield: " + lab);
});

// ---------------------------------------------------------------- station order
await test("station cards follow dependencies (every craftable item, and pairs)", () => {
  const ids = Object.values(D.items).filter((it) => !it.hidden && it.defaultRecipe).map((it) => it.id);
  let multi = 0, bad = [];
  for (const id of ids) {
    const p = plan([{ item: id, qty: 3 }]);
    if (p.stations.length > 1) multi++;
    const v = orderViolations(p);
    if (v.length) bad.push(id + ": " + v[0]);
    for (const s of p.steps) if (!(s.runs === Math.ceil(s.need / s.yield) && s.leftover >= 0 && s.leftover < s.yield)) bad.push(id + " invariant " + s.item);
  }
  for (let k = 0; k + 1 < ids.length; k += 7) {
    const p = plan([{ item: ids[k], qty: 2 }, { item: ids[k + 1], qty: 1 }]);
    const v = orderViolations(p);
    if (v.length) bad.push(ids[k] + "+" + ids[k + 1] + ": " + v[0]);
  }
  check(multi > 100, `plans with several stations: ${multi}`);
  eq(bad.slice(0, 5), [], "order violations");
  const c = plan([{ item: "crate", qty: 3 }]).stations.map((g) => g.station.id);
  check(c.indexOf("distillation-cube") >= 0 && c.indexOf("distillation-cube") < c.indexOf("woodworking-workbench-i"), "Cubo de Destilação before the bench that uses its fat: " + c.join(", "));
  const e = plan([{ item: "master-sword", qty: 1 }]).stations.map((g) => g.station.id);
  check(e.indexOf("steel-anvil") < 0 || e.indexOf("laboratory-ii") < 0 || e.lastIndexOf("steel-anvil") > e.indexOf("laboratory-ii"), "Espada: the anvil card that needs the Lab II comes after it: " + e.join(", "));
});

await test("stations that feed each other get a second card", () => {
  const env = makeEnv();
  const mini = {
    meta: { schema: 1 },
    items: {
      ore: { pt: "Minério", en: "Ore", raw: true, defaultRecipe: null },
      a: { pt: "A", en: "A", defaultRecipe: "ra" }, b: { pt: "B", en: "B", defaultRecipe: "rb" }, c: { pt: "C", en: "C", defaultRecipe: "rc" },
    },
    stations: { x: { pt: "X", en: "X" }, y: { pt: "Y", en: "Y" } },
    recipes: [
      { id: "ra", out: { item: "a", qty: 1 }, station: "x", in: [{ item: "ore", qty: 1 }] },
      { id: "rb", out: { item: "b", qty: 1 }, station: "y", in: [{ item: "a", qty: 1 }] },
      { id: "rc", out: { item: "c", qty: 1 }, station: "x", in: [{ item: "b", qty: 1 }] },
    ],
  };
  const D2 = env.GK.data.load(mini);
  const p = env.GK.calc.plan([{ item: "c", qty: 1 }], D2, {});
  eq(p.stations.map((g) => [g.station.id, g.repeat, g.steps.map((s) => s.item)]), [["x", 1, ["a"]], ["y", 1, ["b"]], ["x", 2, ["c"]]], "X, Y, X again");
  eq(orderViolations(p), [], "valid order");
});

// ---------------------------------------------------------------- store: sanitizeRemote + merge
await test("sanitizeRemote", () => {
  const S = GK.store;
  const r = S.sanitizeRemote({
    goals: [{ item: "crate", qty: 5000 }, { qty: 1 }, "x"], choice: { a: "r1", b: 3 },
    have: { a: true, b: 3, c: 2.6, d: 0, e: -1, f: "7", g: null, h: 1e9 }, done: { "raw:x": true, "raw:y": 0 },
    researched: { t1: 1 }, groupChoice: { "bream-or-carp": "carp", bad: 5 }, perks: { "heat-saver": true, off: false },
    overrides: { pt: { crate: " Caixa " }, xx: { crate: "?" } }, example: 1, future: { keep: "me" },
  });
  const l0 = r.lists[0];   // schema 5: a flat (schema 4) plan becomes the list "main"
  eq([r.lists.length, l0.id, l0.name], [1, "main", ""], "flat plan -> one list");
  eq(l0.goals, [{ item: "crate", qty: 999 }], "goals cleaned and clamped");
  eq(l0.have, { a: true, b: 3, c: 3, h: 999999 }, "have: true or a whole number ≥ 1");
  eq([l0.choice, l0.done, r.researched], [{ a: "r1" }, { "raw:x": true }, { t1: true }], "maps");
  eq([r.groupChoice, r.perks], [{ "bream-or-carp": "carp" }, { "heat-saver": true }], "groupChoice / perks");
  eq(r.overrides, { pt: { crate: "Caixa" } }, "overrides");
  check(!("future" in r), "unknown fields are not part of the sanitized body (GK.sync keeps them)");
  eq(S.sanitizeRemote(null), null, "null"); eq(S.sanitizeRemote([1]), null, "array");
  eq(S.SYNCED.indexOf("groupChoice") >= 0 && S.SYNCED.indexOf("perks") >= 0, true, "new fields are synced");
  check(S.hasContent(Object.assign(S.sanitizeRemote({}), { perks: { x: true } })), "perks count as content");
});

await test("mergeSynced (both sides changed)", () => {
  const L = { goals: [{ item: "crate", qty: 2 }], choice: { a: "L", b: "L" }, have: { x: 2, y: true }, done: { "raw:l": true, "raw:c": true },
    overrides: { pt: { a: "La", b: "Lb" } }, example: false, researched: { t1: true }, groupChoice: { g: "m1" }, perks: { p1: true } };
  const R = { goals: [{ item: "wine", qty: 9 }], choice: { b: "R", c: "R" }, have: { x: 5, z: true }, done: { "raw:r": true },
    overrides: { pt: { b: "Rb" }, en: { c: "Rc" } }, example: false, researched: { t2: true }, groupChoice: { g: "m2", h: "m3" }, perks: { p2: true } };
  const m = GK.store.mergeSynced(L, R), ml = m.lists[0];   // both flat plans are the list "main" (changed on both sides)
  eq(m.lists.length, 1, "one list");
  eq(ml.goals, L.goals, "goals: local");
  eq(ml.choice, { b: "L", c: "R", a: "L" }, "choice: union, local wins");
  eq(m.overrides, { pt: { b: "Lb", a: "La" }, en: { c: "Rc" } }, "overrides: union, local wins");
  eq(ml.have, { x: 5, y: true, z: true }, "have: union, remote wins");
  eq(ml.done, { "raw:l": true, "raw:c": true, "raw:r": true }, "done: union");
  eq([m.researched, m.groupChoice, m.perks], [{ t1: true, t2: true }, { g: "m2", h: "m3" }, { p1: true, p2: true }], "researched / groupChoice / perks: union, remote wins");
});

await test("store migration keeps have=true, partial numbers and unknown local fields", () => {
  const env = makeEnv();
  env.localStorage.setItem("gk2-companion", JSON.stringify({ schemaVersion: 4, goals: [{ item: "crate", qty: 3 }], have: { log: true, fuel: 12 }, updatedAt: "2026-01-01T00:00:00.000Z", newerField: { a: 1 } }));
  check(env.GK.store.load(), "loaded");
  const s = env.GK.store.get();
  eq([s.have, s.groupChoice, s.perks, s.newerField], [{ log: true, fuel: 12 }, {}, {}, { a: 1 }], "migrated");
  env.GK.store.actions.setHave("log", "4"); eq(env.GK.store.get().have.log, 4, "setHave string");
  env.GK.store.actions.setHave("log", 0); eq("log" in env.GK.store.get().have, false, "setHave 0 clears");
  env.GK.store.actions.setGroupChoice("bream-or-carp", "carp"); eq(env.GK.store.get().groupChoice, { "bream-or-carp": "carp" }, "setGroupChoice");
  env.GK.store.actions.setPerk("heat-saver", true); eq(env.GK.store.get().perks, { "heat-saver": true }, "setPerk");
});

await test("removing a goal can be undone: same place, same quantity, choices kept (Metas ✕, 1.8.x)", () => {
  const env = makeEnv(), S = env.GK.store, A = S.actions;
  env.localStorage.setItem("gk2-companion", JSON.stringify({ schemaVersion: 4, goals: [{ item: "wine", qty: 1 }, { item: "steel-sword", qty: 3 }, { item: "crate", qty: 12 }],
    choice: { "steel-sword": "r-x" }, done: { "step:steel-sword": true }, updatedAt: "2026-01-01T00:00:00.000Z" }));
  check(S.load(), "loaded");
  A.removeGoal("steel-sword");
  eq(S.get().goals.map((g) => g.item), ["wine", "crate"], "removed");
  A.restoreGoal({ item: "steel-sword", qty: 3 }, 1, false);
  eq(S.get().goals, [{ item: "wine", qty: 1 }, { item: "steel-sword", qty: 3 }, { item: "crate", qty: 12 }], "back at its place with its quantity");
  eq([S.get().choice, S.get().done], [{ "steel-sword": "r-x" }, { "step:steel-sword": true }], "recipe choice and ticks kept");
  A.restoreGoal({ item: "steel-sword", qty: 9 }, 0, false);
  eq(S.get().goals.length, 3, "no duplicate when it is already there");
  A.removeGoal("crate"); A.restoreGoal({ item: "crate", qty: 2000 }, 99, false);
  eq(S.get().goals[2], { item: "crate", qty: 999 }, "index clamped to the end, quantity clamped");
  // removed from the untouched example: the undo gives the example back
  const env2 = makeEnv(), S2 = env2.GK.store;
  S2.actions.seedExample([{ item: "crate", qty: 1 }, { item: "wine", qty: 2 }]);
  S2.actions.removeGoal("crate");
  check(!S2.get().example, "a removal adopts the example");
  S2.actions.restoreGoal({ item: "crate", qty: 1 }, 0, true);
  eq([S2.get().goals.map((g) => g.item), S2.get().example], [["crate", "wine"], true], "the example is back");
});

await test("ticks follow the quantity (1.8.0: corte 9 + C3), old ticks kept", () => {
  const C = GK.calc, S = GK.store;
  // a copy saved before 1.8.0: ticks are plain true; they stay ticked whatever the quantity (no number to compare)
  const env = makeEnv();
  env.localStorage.setItem("gk2-companion", JSON.stringify({ schemaVersion: 5, lists: [{ id: "main", name: "", createdAt: "1970-01-01T00:00:00.000Z",
    updatedAt: "2026-10-31T12:00:00.000Z", goals: [{ item: "crate", qty: 3 }], choice: {}, have: { fat: 1 },
    done: { "raw:log": true, "step:fuel": true, "raw:clay": 0 }, example: false }], listsGone: {}, ui: { activeList: "main" }, updatedAt: "2026-10-31T12:00:00.000Z" }));
  check(env.GK.store.load(), "old copy loaded");
  const A = env.GK.store.actions, st = () => env.GK.store.get();
  eq(st().done, { "raw:log": true, "step:fuel": true }, "old ticks kept (a 0 is not a tick)");
  const rowOf = (p, id) => p.raw.find((r) => r.item === id);
  let p3 = plan([{ item: "crate", qty: 3 }], { have: st().have }), p10 = plan([{ item: "crate", qty: 10 }], { have: st().have });
  check(C.rawChecked(rowOf(p3, "log"), st().have, st().done) && C.rawChecked(rowOf(p10, "log"), st().have, st().done), "old raw tick: ticked at any quantity");
  check(C.stepChecked(stepOf(p3, "fuel"), st().done) && C.stepChecked(stepOf(p10, "fuel"), st().done), "old step tick: ticked at any quantity");
  // a raw row's tick = "tenho tudo": have = the quantity asked (3 Toras); the plan asking for more makes it pending
  A.checkRaw("log", 3, true);
  eq([st().have.log, "raw:log" in st().done], [3, false], "checkRaw: have = 3, old tick gone");
  p3 = plan([{ item: "crate", qty: 3 }], { have: st().have }); p10 = plan([{ item: "crate", qty: 10 }], { have: st().have });
  const l3 = rowOf(p3, "log"), l10 = rowOf(p10, "log");
  check(C.rawChecked(l3, st().have, st().done) && l3.covered, "3 of 3: ticked (listed with what you have)");
  check(!C.rawChecked(l10, st().have, st().done), "goal ×10: the 3 Toras no longer cover it, pending again");
  eq([l10.qty, l10.haveQty, l10.demand], [l10.demand - 3, 3, l10.demand], "pending row keeps the 3 as 'tenho 3 de N'");
  A.checkRaw("log", 0, true); eq(st().have.log, true, "no quantity: true (everything)");
  A.checkRaw("log", null, false); eq(["log" in st().have, "raw:log" in st().done], [false, false], "untick forgets have and the tick");
  // a step's tick keeps its quantity
  A.toggleDone("step:fuel", true, stepOf(p3, "fuel").need);
  eq(st().done["step:fuel"], stepOf(p3, "fuel").need, "step tick = its need");
  check(C.stepChecked(stepOf(p3, "fuel"), st().done), "step ticked at its need");
  check(stepOf(p10, "fuel").need > stepOf(p3, "fuel").need && !C.stepChecked(stepOf(p10, "fuel"), st().done), "step pending when the need grows");
  A.toggleDone("step:fuel", true); eq(st().done["step:fuel"], true, "no quantity: true");
  A.toggleDone("step:fuel", false); check(!("step:fuel" in st().done), "untick");
  check(!("clearDone" in A), "no clearDone (\"Limpar marcações\" left the progress card in 1.8.x)");
  // doneCovers
  eq([C.doneCovers(true, 99), C.doneCovers(3, 3), C.doneCovers(3, 4), C.doneCovers(undefined, 1), C.doneCovers(0, 0)], [true, true, false, false, false], "doneCovers");
  // sanitize (account doc / local copy): numbers kept, other truthy values become true, falsy dropped
  const r = S.sanitizeRemote({ goals: [], done: { "step:a": 7, "step:b": 2.4, "raw:c": true, "step:d": 0, "step:e": "x", "step:f": 5e9 } });
  eq(r.lists[0].done, { "step:a": 7, "step:b": 2, "raw:c": true, "step:e": true, "step:f": 999999 }, "done sanitized");
  const m = S.mergeSynced({ goals: [], done: { "step:a": 4 } }, { goals: [{ item: "crate", qty: 1 }], done: { "step:b": 9 } }).lists[0];
  eq(m.done, { "step:a": 4, "step:b": 9 }, "merge keeps the numbers");
  // restoreExample keeps numbered ticks
  const e2 = makeEnv(); const A2 = e2.GK.store.actions;
  A2.seedExample([{ item: "crate", qty: 3 }]); A2.toggleDone("step:fuel", true, 50);
  const metas = []; e2.GK.store.subscribe((s2, mm) => metas.push(mm));
  A2.addGoal("wine", 1); A2.restoreExample(metas[metas.length - 1].exampleReplaced);
  eq(e2.GK.store.get().done, { "step:fuel": 50 }, "restoreExample keeps the quantity");
});

await test("store: current weekday (day, dayNumber)", () => {
  const S = GK.store;
  eq(S.SYNCED.indexOf("day") >= 0 && S.SYNCED.indexOf("dayNumber") >= 0 && S.SYNCED.indexOf("dayAnchor") >= 0, true, "day fields are synced");
  eq([S.sanitizeRemote({ day: "wrath", dayNumber: "60.4" }).day, S.sanitizeRemote({ day: "wrath", dayNumber: "60.4" }).dayNumber], ["wrath", 60], "valid day + counter");
  eq([S.sanitizeRemote({ day: "monday", dayNumber: 3 }).day, S.sanitizeRemote({ day: "monday", dayNumber: 3 }).dayNumber], [null, 3], "unknown id dropped (the counter stays)");
  eq(S.sanitizeRemote({ dayAnchor: { number: "60", day: "pride" } }).dayAnchor, { number: 60, day: "pride" }, "anchor");
  eq([S.sanitizeRemote({ dayAnchor: { number: 0, day: "pride" } }).dayAnchor, S.sanitizeRemote({ dayAnchor: { number: 5, day: "x" } }).dayAnchor, S.sanitizeRemote({ dayAnchor: "x" }).dayAnchor], [null, null, null], "bad anchors");
  check(S.hasContent(Object.assign(S.sanitizeRemote({}), { dayAnchor: { number: 1, day: "lust" } })), "an anchor counts as content");
  eq([S.sanitizeRemote({}).day, S.sanitizeRemote({}).dayNumber, S.sanitizeRemote({ day: "lust", dayNumber: 0 }).dayNumber], [null, null, null], "defaults / bad counter");
  check(S.hasContent(Object.assign(S.sanitizeRemote({}), { day: "pride" })), "a day counts as content");
  const L = S.sanitizeRemote({ day: "lust", dayNumber: 10 }), R = S.sanitizeRemote({ day: "pride", dayNumber: 12 });
  eq([S.mergeSynced(L, R).day, S.mergeSynced(L, R).dayNumber], ["pride", 12], "merge: higher counter wins");
  eq(S.mergeSynced(S.sanitizeRemote({ day: "lust" }), R).day, "pride", "merge: a counter beats none");
  eq(S.mergeSynced(S.sanitizeRemote({ day: "lust" }), S.sanitizeRemote({ day: "envy" })).day, "lust", "merge: else local");
  eq(S.mergeSynced(S.sanitizeRemote({}), S.sanitizeRemote({ day: "envy" })).day, "envy", "merge: local unset");
  const env = makeEnv(), A = env.GK.store.actions, st = () => env.GK.store.get();
  const W = env.GK.store.dayOrder();   // wheel order: the payload's days block, else the fallback
  eq(W.length, 6, "six days in the wheel");
  // the Hoje panel ticks only the tasks (data/days.json `task`, see data/README-days.md)
  const evs = ((PAYLOAD.days && PAYLOAD.days.days) || []).flatMap((d) => d.events || []);
  if (evs.length) {
    check(evs.every((e) => typeof e.task === "boolean"), "every day event says task true/false");
    eq(evs.filter((e) => !e.task).length, 9, "9 informative events (no tick)");
    check(!evs.find((e) => e.pt.startsWith("O sino toca")).task, "the bell is information, not a task");
    check(evs.find((e) => e.pt.startsWith("Dia de missa")).task, "the sermon is a task");
  }
  eq(A.advanceDay(), false, "advance without a day: no-op");
  A.setDay(W[4], 59); eq([st().day, st().dayNumber], [W[4], 59], "setDay");
  check(!!st().updatedAt, "setDay stamps updatedAt");
  A.advanceDay(); eq([st().day, st().dayNumber], [W[5], 60], "advance");
  A.advanceDay(); eq([st().day, st().dayNumber], [W[0], 61], "advance wraps around the wheel");
  A.setDay(W[1]); eq([st().day, st().dayNumber], [W[1], 61], "undefined keeps the counter");
  A.setDay(W[1], ""); eq(st().dayNumber, null, "empty clears the counter");
  A.advanceDay(); eq([st().day, st().dayNumber], [W[2], null], "advance without a counter");
  A.setDay(null, 5); eq([st().day, st().dayNumber], [null, null], "setDay(null) clears both");
  // calibration: day + counter once, then the counter alone gives the day
  A.clearAnchor(); eq(st().dayAnchor, null, "clearAnchor");
  eq(A.setDayNumber(10), null, "a counter without a day or an anchor stays a counter");
  eq([st().day, st().dayNumber, st().dayAnchor], [null, 10, null], "counter only");
  A.setDay(W[2], 60); eq(st().dayAnchor, { number: 60, day: W[2] }, "day + counter calibrate");
  eq(A.setDayNumber(61), W[3], "next number = next day"); eq(st().day, W[3], "day follows the counter");
  eq(A.setDayNumber(59), W[1], "previous number"); eq(A.setDayNumber(66), W[2], "a week later = same day");
  eq(A.setDayNumber(53), W[1], "earlier weeks wrap too");
  A.advanceDay(); eq([st().day, st().dayNumber, st().dayAnchor], [W[2], 54, { number: 60, day: W[2] }], "advance keeps the anchor consistent");
  A.setDay(W[5]); eq(st().dayAnchor, { number: 54, day: W[5] }, "tapping another day with a counter recalibrates");
  eq(env.GK.store.dayFromNumber(55, { number: 54, day: W[5] }), W[0], "dayFromNumber wraps the cycle");
  const M = S.mergeSynced(S.sanitizeRemote({}), S.sanitizeRemote({ dayAnchor: { number: 3, day: "lust" } }));
  eq(M.dayAnchor, { number: 3, day: "lust" }, "merge: anchor from remote when local has none");
});

await test("store: \"feito hoje\" ticks reset when the day changes", () => {
  const env = makeEnv(), S = env.GK.store, A = S.actions, st = () => S.get();
  env.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  const W = S.dayOrder();
  check(S.SYNCED.indexOf("dayDone") >= 0 && S.SYNCED.indexOf("dayNotes") >= 0, "dayDone / dayNotes are synced");
  eq([st().dayDone, st().dayNotes], [null, {}], "fresh state");
  A.toggleDayDone(0, true); eq(st().dayDone, null, "no day: no tick");
  A.setDay(W[5], 61);
  A.toggleDayDone(0, true); A.toggleDayDone("2", true); A.toggleDayDone(2, true);
  eq(st().dayDone, { day: W[5], number: 61, ids: [0, 2] }, "ticks on today (string index, double tick)");
  eq(S.doneToday(st()), [0, 2], "doneToday");
  check(!!st().updatedAt, "a tick stamps updatedAt");
  A.toggleDayDone(0); eq(S.doneToday(st()), [2], "toggle without `on` flips");
  A.toggleDayDone(-1, true); A.toggleDayDone(1.5, true); A.toggleDayDone(100, true); eq(S.doneToday(st()), [2], "bad indexes ignored");
  A.setDay(W[5]); eq(S.doneToday(st()), [2], "the same day picked again keeps the ticks");
  A.advanceDay(); eq([st().day, st().dayDone, S.doneToday(st())], [W[0], null, []], "advance resets");
  A.toggleDayDone(1, true); A.setDay(W[3]); eq(st().dayDone, null, "another day picked resets");
  A.toggleDayDone(1, true); A.setDay(null); eq(st().dayDone, null, "forgetting the day resets");
  // the counter: a tick made before it was given adopts it; a different number (a week later) is another day
  A.clearAnchor(); A.setDay(W[2], ""); A.toggleDayDone(0, true);
  eq(st().dayDone, { day: W[2], number: null, ids: [0] }, "tick without a counter");
  A.setDayNumber(30); eq(st().dayDone, { day: W[2], number: 30, ids: [0] }, "the first counter is adopted (same day)");
  A.setDayNumber(""); eq(S.doneToday(st()), [0], "clearing the counter keeps the ticks");
  A.setDayNumber(30); A.setDayNumber(36); eq([st().day, st().dayDone], [W[2], null], "counter a week later: same weekday, reset");
  A.toggleDayDone(3, true); A.setDayNumber(37); eq([st().day, st().dayDone], [W[3], null], "counter on the next day resets");
  // stale or bad ticks from untrusted input
  eq(S.sanitizeRemote({ day: "wrath", dayNumber: 61, dayDone: { day: "wrath", number: 61, ids: [3, 1, 1, "2", -1, 7.5] } }).dayDone, { day: "wrath", number: 61, ids: [1, 3] }, "sanitize ids");
  eq(S.sanitizeRemote({ day: "lust", dayDone: { day: "wrath", ids: [1] } }).dayDone, null, "ticks of another day dropped");
  eq(S.sanitizeRemote({ day: "wrath", dayNumber: 67, dayDone: { day: "wrath", number: 61, ids: [1] } }).dayDone, null, "ticks of another week dropped");
  eq([S.sanitizeRemote({ dayDone: { day: "wrath", ids: [1] } }).dayDone, S.sanitizeRemote({ day: "wrath", dayDone: [1] }).dayDone, S.sanitizeRemote({ day: "wrath", dayDone: { day: "wrath", ids: [] } }).dayDone], [null, null, null], "no day / not an object / empty");
});

await test("store: \"bilhete do dia\" notes", () => {
  const env = makeEnv(), S = env.GK.store, A = S.actions, st = () => S.get();
  env.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  eq(A.setDayNote("wrath", "  levar 3 peixes\n para o   Pescador "), "levar 3 peixes para o Pescador", "one line, trimmed");
  eq(st().dayNotes, { wrath: "levar 3 peixes para o Pescador" }, "stored by weekday");
  check(!!st().updatedAt && S.hasContent(st()), "a note stamps and counts as content");
  eq(A.setDayNote("lust", "x".repeat(250)).length, S.NOTE_MAX, "capped at NOTE_MAX");
  eq(A.setDayNote("monday", "no"), "", "unknown day ignored");
  A.setDayNote("lust", "   "); eq(Object.keys(st().dayNotes), ["wrath"], "blank removes it");
  A.advanceDay(); A.setDay("sloth"); eq(st().dayNotes.wrath, "levar 3 peixes para o Pescador", "notes do not reset with the day");
  eq(S.sanitizeRemote({ dayNotes: { wrath: " a ", x: "b", lust: 5, envy: "" } }).dayNotes, { wrath: "a" }, "sanitize notes");
  eq(S.sanitizeRemote({ dayNotes: "x" }).dayNotes, {}, "not an object");
});

await test("mergeSynced: dayDone and dayNotes", () => {
  const S = GK.store, san = (o) => S.sanitizeRemote(o);
  const L = san({ day: "wrath", dayNumber: 61, dayDone: { day: "wrath", number: 61, ids: [0] }, dayNotes: { wrath: "L", lust: "L" } });
  const R = san({ day: "wrath", dayNumber: 61, dayDone: { day: "wrath", number: 61, ids: [2] }, dayNotes: { lust: "R", envy: "R" } });
  eq(S.mergeSynced(L, R).dayDone, { day: "wrath", number: 61, ids: [0, 2] }, "same day: ticks by union");
  eq(S.mergeSynced(L, R).dayNotes, { lust: "L", envy: "R", wrath: "L" }, "notes: union, local wins when it is newer");
  eq(S.mergeSynced(L, R, true).dayNotes, { wrath: "L", lust: "R", envy: "R" }, "notes: union, remote wins when it is newer");
  const R2 = san({ day: "gluttony", dayNumber: 62, dayDone: { day: "gluttony", number: 62, ids: [0] } });
  eq([S.mergeSynced(L, R2).day, S.mergeSynced(L, R2).dayDone], ["gluttony", { day: "gluttony", number: 62, ids: [0] }], "the other side moved on: its ticks, ours are stale");
  const R3 = san({ day: "gluttony", dayNumber: 62 });
  eq(S.mergeSynced(L, R3).dayDone, null, "moved on with no ticks: reset");
  eq(S.mergeSynced(L, san({})).dayDone, L.dayDone, "remote without the fields keeps ours");
  eq(S.mergeSynced(L, san({})).dayNotes, L.dayNotes, "remote without notes keeps ours");
  eq(S.mergeSynced(san({}), L).dayNotes, L.dayNotes, "local without notes takes the remote ones");
  // a doc from an older page (no dayDone / dayNotes key at all)
  const raw = { goals: [], day: "wrath", dayNumber: 61 };
  eq(S.keepLate(san(raw), raw, L), Object.assign(san(raw), { dayNotes: L.dayNotes, dayDone: L.dayDone }), "keepLate: keep ours when the doc lacks the keys");
  eq(S.keepLate(san(raw), Object.assign({ dayNotes: {}, dayDone: null }, raw), L), null, "keepLate: an explicit empty value is a real clear");
  eq(S.keepLate(san({ day: "lust" }), { day: "lust" }, san({ day: "wrath", dayDone: { day: "wrath", ids: [1] } })), null, "keepLate: ticks of a day that is no longer today are not kept");
  eq(S.adoptLate(L, san({ day: "wrath", dayNumber: 61 })), Object.assign(san({ day: "wrath", dayNumber: 61 }), { dayNotes: L.dayNotes, dayDone: L.dayDone }), "adoptLate: take what the doc carried");
  eq(S.adoptLate(san({}), L), null, "adoptLate: nothing to adopt");
});

// ---------------------------------------------------------------- sync (fake db + user capabilities)
function fakeClaude(env, uid, initialDoc) {
  const db = { doc: initialDoc ? JSON.parse(JSON.stringify(initialDoc)) : null, writes: [], subs: 0, unsubs: 0, listener: null, failNext: 0, silent: false };
  const ref = {
    onSnapshot(cb, err) { db.subs++; db.listener = { cb, err }; if (!db.silent) setImmediate(() => cb(snap())); return () => { db.unsubs++; }; },
    set(doc) {
      if (db.failNext) { db.failNext--; return Promise.reject({ code: "unavailable" }); }
      db.doc = JSON.parse(JSON.stringify(doc)); db.writes.push(db.doc); return Promise.resolve();
    },
  };
  const snap = (fromCache) => ({ exists: !!db.doc, data: () => JSON.parse(JSON.stringify(db.doc)), metadata: { fromCache: !!fromCache, hasPendingWrites: false } });
  db.push = (doc) => { db.doc = JSON.parse(JSON.stringify(doc)); db.listener.cb(snap()); };
  db.kill = (code) => db.listener.err({ code: code || "unavailable" });
  const claude = {
    use: async (cap) => (cap === "db" ? { collection: (p) => { db.path = p; return { doc: () => ref }; } } : { id: async () => uid }),
  };
  return { claude, db };
}
async function bootSync(env, uid, doc) {
  env.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  env.GK.store.load();
  env.GK.store.subscribe((st, meta) => env.GK.sync.onStore(st, meta));
  const f = fakeClaude(env, uid, doc);
  await env.GK.sync.start(f.claude);
  await flushMicro(); await flushMicro();
  return f;
}

await test("sync keeps v and unknown state fields of the account doc", async () => {
  const env = makeEnv();
  const doc = { v: 9, updatedAt: "2026-05-01T00:00:00.000Z", state: { goals: [{ item: "crate", qty: 3 }], have: { log: 2 }, futureField: { x: [1, 2] }, done: {} } };
  const { db } = await bootSync(env, "u1", doc);
  eq(db.path, "data/users/u1", "doc path");
  eq(env.GK.store.get().goals, [{ item: "crate", qty: 3 }], "remote applied to an empty device");
  eq(env.GK.store.get().have, { log: 2 }, "partial have from the account");
  env.GK.store.actions.setQty("crate", 5);
  await env.clock.tick(2000);
  const w = db.writes[db.writes.length - 1];
  check(!!w, "a write happened");
  eq(w && w.v, 9, "v kept (max of ours and theirs)");
  eq(w && w.state.futureField, { x: [1, 2] }, "unknown field written back");
  eq(w && w.state.goals, [{ item: "crate", qty: 5 }], "our change written");
  eq(env.GK.store.get().syncBase, w && w.updatedAt, "syncBase = the pushed version");
});

await test("sync merges when both sides changed since the last shared version", async () => {
  const env = makeEnv();
  const base = "2026-05-01T00:00:00.000Z";
  env.localStorage.setItem("gk2-companion.account", "u2");
  env.localStorage.setItem("gk2-companion:u2", JSON.stringify({ schemaVersion: 4, goals: [{ item: "crate", qty: 4 }], done: { "raw:log": true },
    have: {}, updatedAt: "2026-05-02T00:00:00.000Z", syncBase: base }));
  const doc = { v: 4, updatedAt: "2026-05-03T00:00:00.000Z", state: { goals: [{ item: "wine", qty: 1 }], done: { "raw:clay": true }, have: { fuel: 10 }, perks: { "heat-saver": true } } };
  const { db } = await bootSync(env, "u2", doc);
  eq(env.GK.store.storageKey(), "gk2-companion:u2", "account key");
  const s = env.GK.store.get();
  eq(s.goals, [{ item: "crate", qty: 4 }], "goals: local");
  eq([s.done, s.have, s.perks], [{ "raw:log": true, "raw:clay": true }, { fuel: 10 }, { "heat-saver": true }], "maps: union");
  check(s.updatedAt > doc.updatedAt, "merged copy stamped newer than both");
  await env.clock.tick(10);
  const w = db.writes[db.writes.length - 1];
  check(w && w.updatedAt === s.updatedAt && w.state.done["raw:clay"] && w.state.goals[0].item === "crate", "merged copy pushed");
});

await test("sync: last writer wins when only one side changed", async () => {
  const env = makeEnv();
  env.localStorage.setItem("gk2-companion.account", "u3");
  env.localStorage.setItem("gk2-companion:u3", JSON.stringify({ schemaVersion: 4, goals: [{ item: "crate", qty: 4 }], updatedAt: "2026-05-01T00:00:00.000Z", syncBase: "2026-05-01T00:00:00.000Z" }));
  const { db } = await bootSync(env, "u3", { v: 4, updatedAt: "2026-05-04T00:00:00.000Z", state: { goals: [{ item: "wine", qty: 2 }] } });
  eq(env.GK.store.get().goals, [{ item: "wine", qty: 2 }], "remote wins");
  eq(env.GK.store.get().syncBase, "2026-05-04T00:00:00.000Z", "base moves to the remote version");
  await env.clock.tick(3000);
  eq(db.writes.length, 0, "nothing pushed back");
});

await test("sync re-subscribes once after the listener dies, and on `online`", async () => {
  const env = makeEnv();
  const { db } = await bootSync(env, "u4", null);
  eq(db.subs, 1, "one listener");
  db.kill("unavailable");
  eq(env.GK.sync.status(), "error", "status error");
  await env.clock.tick(5000);
  eq(db.subs, 2, "re-subscribed after backoff");
  await flushMicro();
  db.silent = true;           // the next subscriptions get no snapshot
  db.kill("unavailable"); await env.clock.tick(5000);
  eq(db.subs, 3, "the retry budget resets after a good snapshot");
  db.kill("unavailable"); await env.clock.tick(5000);
  eq(db.subs, 3, "no retry loop without a good snapshot in between");
  db.silent = false;
  env.ctx._fire("online"); await flushMicro();
  eq(db.subs, 4, "`online` brings it back");
  db.kill("revoked");
  eq(env.GK.sync.status(), "local", "terminal error disables sync");
});

await test("sync: a failed write is retried once", async () => {
  const env = makeEnv();
  const { db } = await bootSync(env, "u5", null);
  env.GK.store.actions.addGoal("crate", 2);
  db.failNext = 1;
  await env.clock.tick(1600);
  eq(db.writes.length, 0, "first write failed");
  eq(env.GK.sync.status(), "error", "status error");
  await env.clock.tick(6000);
  eq(db.writes.length, 1, "retried");
  eq(env.GK.sync.status(), "synced", "synced");
});

await test("localStorage per account: the anonymous plan moves once, another account starts clean", async () => {
  const env = makeEnv();
  env.localStorage.setItem("gk2-companion", JSON.stringify({ schemaVersion: 4, goals: [{ item: "crate", qty: 7 }], updatedAt: "2026-05-01T00:00:00.000Z", lang: "en" }));
  env.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  env.GK.store.load();
  env.GK.store.useAccount("A");
  eq(env.GK.store.storageKey(), "gk2-companion:A", "key A");
  eq(env.GK.store.get().goals, [{ item: "crate", qty: 7 }], "A adopted the anonymous plan");
  eq(env.localStorage.getItem("gk2-companion"), null, "anonymous copy removed");
  check(env.localStorage.getItem("gk2-companion:A"), "A's copy saved");
  env.GK.store.useAccount("B");
  eq([env.GK.store.get().goals, env.GK.store.get().updatedAt, env.GK.store.get().lang], [[], "", "en"], "B starts clean (device prefs kept)");
  env.GK.store.actions.addGoal("wine", 1);
  env.GK.store.useAccount("A");
  eq(env.GK.store.get().goals, [{ item: "crate", qty: 7 }], "A's plan is still A's");
  eq(env.localStorage.getItem("gk2-companion.account"), "A", "last account remembered");
  const env2 = makeEnv();
  for (const [k, v] of env.localStorage._map) env2.localStorage.setItem(k, v);
  env2.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  check(env2.GK.store.load(), "next visit loads the last account's copy");
  eq(env2.GK.store.get().goals, [{ item: "crate", qty: 7 }], "A again");
});

await test("sync: a doc from an older page does not wipe dayDone / dayNotes (and vice versa)", async () => {
  // the account doc is newer but predates the fields: ours stay and the result is pushed with a new stamp
  const env = makeEnv();
  env.localStorage.setItem("gk2-companion.account", "u6");
  env.localStorage.setItem("gk2-companion:u6", JSON.stringify({ schemaVersion: 4, goals: [], day: "wrath", dayNumber: 61,
    dayDone: { day: "wrath", number: 61, ids: [1] }, dayNotes: { wrath: "sermão" }, updatedAt: "2026-05-01T00:00:00.000Z", syncBase: "2026-05-01T00:00:00.000Z" }));
  const old = { v: 4, updatedAt: "2026-05-05T00:00:00.000Z", state: { goals: [{ item: "wine", qty: 2 }], day: "wrath", dayNumber: 61 } };
  const { db } = await bootSync(env, "u6", old);
  const s = env.GK.store.get();
  eq(s.goals, [{ item: "wine", qty: 2 }], "the account's goals win");
  eq([s.dayNotes, s.dayDone], [{ wrath: "sermão" }, { day: "wrath", number: 61, ids: [1] }], "our note and ticks stay");
  check(s.updatedAt > old.updatedAt, "stamped newer than the doc");
  await env.clock.tick(10);
  const w = db.writes[db.writes.length - 1];
  eq(w && [w.state.dayNotes, w.state.dayDone, w.state.goals], [{ wrath: "sermão" }, { day: "wrath", number: 61, ids: [1] }, [{ item: "wine", qty: 2 }]], "pushed");
  // a newer doc that clears them explicitly does clear them (the merged copy was stamped with the real clock)
  db.push({ v: 4, updatedAt: "2999-01-01T00:00:00.000Z", state: Object.assign({}, w.state, { dayNotes: {}, dayDone: null }) });
  await flushMicro();
  eq([env.GK.store.get().dayNotes, env.GK.store.get().dayDone], [{}, null], "an explicit clear from the account applies");
  // same version, but an older page carried the fields along in the doc without loading them: adopt them
  const env2 = makeEnv();
  env2.localStorage.setItem("gk2-companion.account", "u7");
  env2.localStorage.setItem("gk2-companion:u7", JSON.stringify({ schemaVersion: 4, goals: [{ item: "crate", qty: 1 }], day: "lust",
    updatedAt: "2026-05-02T00:00:00.000Z", syncBase: "2026-05-02T00:00:00.000Z" }));
  const f2 = await bootSync(env2, "u7", { v: 4, updatedAt: "2026-05-02T00:00:00.000Z", state: { goals: [{ item: "crate", qty: 1 }], day: "lust",
    dayNotes: { lust: "vender peixes" }, dayDone: { day: "lust", ids: [0] } } });
  eq([env2.GK.store.get().dayNotes, env2.GK.store.get().dayDone], [{ lust: "vender peixes" }, { day: "lust", number: null, ids: [0] }], "adopted from the doc");
  eq(env2.GK.store.get().updatedAt, "2026-05-02T00:00:00.000Z", "same version kept");
  await env2.clock.tick(3000);
  eq(f2.db.writes.length, 0, "nothing pushed back");
});

await test("sync: notes and ticks travel and merge between two devices", async () => {
  const env = makeEnv();
  const base = "2026-05-01T00:00:00.000Z";
  env.localStorage.setItem("gk2-companion.account", "u8");
  env.localStorage.setItem("gk2-companion:u8", JSON.stringify({ schemaVersion: 4, goals: [], day: "envy", dayNumber: 40,
    dayDone: { day: "envy", number: 40, ids: [0] }, dayNotes: { envy: "phone" }, updatedAt: "2026-05-02T00:00:00.000Z", syncBase: base }));
  const doc = { v: 4, updatedAt: "2026-05-03T00:00:00.000Z", state: { goals: [], day: "envy", dayNumber: 40,
    dayDone: { day: "envy", number: 40, ids: [2] }, dayNotes: { envy: "pc", pride: "pc" } } };
  const { db } = await bootSync(env, "u8", doc);
  const s = env.GK.store.get();
  eq(s.dayDone, { day: "envy", number: 40, ids: [0, 2] }, "ticks by union");
  eq(s.dayNotes, { envy: "pc", pride: "pc" }, "notes: the newer copy (the account's) wins a conflict");
  await env.clock.tick(10);
  const w = db.writes[db.writes.length - 1];
  eq(w && w.state.dayDone, { day: "envy", number: 40, ids: [0, 2] }, "merged copy pushed");
  env.GK.store.actions.advanceDay();
  await env.clock.tick(2000);
  const w2 = db.writes[db.writes.length - 1];
  eq(w2 && [w2.state.day, w2.state.dayNumber, w2.state.dayDone], ["pride", 41, null], "advancing resets the ticks on the account too");
});

// ---------------------------------------------------------------- lists (schema 5, "listas separadas")
await test("lists: a schema 4 copy becomes the one list \"Minha lista\" with nothing lost", () => {
  const env = makeEnv(), S = env.GK.store;
  env.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  const v4 = { schemaVersion: 4, lang: "pt", theme: "dark", goals: [{ item: "crate", qty: 3 }, { item: "wine", qty: 2 }],
    choice: { fuel: "fuel-from-log" }, have: { log: true, clay: 4 }, done: { "raw:log": true, "step:crate": true }, example: false,
    overrides: { pt: { crate: "Caixa" } }, researched: { t1: true }, groupChoice: { g: "m" }, perks: { p: true }, day: "wrath", dayNumber: 61,
    ui: { todayCollapsed: false }, updatedAt: "2026-10-31T12:00:00.000Z", syncBase: "2026-10-30T00:00:00.000Z" };
  env.localStorage.setItem("gk2-companion", JSON.stringify(v4));
  check(S.load(), "loaded");
  const st = S.get(), l = st.lists[0];
  eq([st.schemaVersion, st.lists.length, l.id, l.name, l.createdAt, l.updatedAt], [5, 1, "main", "", "1970-01-01T00:00:00.000Z", v4.updatedAt], "one list, dated with the copy");
  eq([l.goals, l.choice, l.have, l.done, l.example], [v4.goals, v4.choice, v4.have, v4.done, false], "the plan moved into the list");
  eq([st.goals, st.choice, st.have, st.done], [v4.goals, v4.choice, v4.have, v4.done], "working copy = the open list (other modules read it)");
  eq([st.overrides, st.researched, st.groupChoice, st.perks, st.day, st.updatedAt, st.syncBase, st.ui.todayCollapsed],
    [v4.overrides, v4.researched, v4.groupChoice, v4.perks, "wrath", v4.updatedAt, v4.syncBase, false], "global fields kept");
  eq([st.ui.activeList, st.legacyOf], ["main", "main"], "open list");
  S.actions.toggleDone("raw:clay", true);
  env.clock.tick(200);
  const saved = JSON.parse(env.localStorage.getItem("gk2-companion"));
  eq([saved.schemaVersion, saved.lists[0].done["raw:clay"], saved.done["raw:clay"], saved.legacyOf], [5, true, true, "main"], "saved as schema 5 (with the flat mirror)");
  const fr = env.GK.store.sanitizeRemote({ lists: [] });
  eq(fr.lists, [], "an explicit empty lists stays empty");
});

await test("lists: create, switch, rename, delete; plan per list, techs / Vantagens global", () => {
  const env = makeEnv(), S = env.GK.store, A = S.actions, st = () => S.get();
  env.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  A.addGoal("crate", 3); A.setHave("log", 2); A.toggleDone("raw:clay", true); A.setPerk("heat-saver", true); A.setResearched("t1", true);
  const id = A.createList("  Igreja   da\nvila ");
  check(!!id && id !== "main", "new id");
  eq([st().lists.length, st().ui.activeList, st().lists[1].name], [2, id, "Igreja da vila"], "created, opened, name on one line");
  eq([st().goals, st().have, st().done], [[], {}, {}], "starts empty");
  eq([st().perks, st().researched], [{ "heat-saver": true }, { t1: true }], "Vantagens / techs are global");
  A.addGoal("wine", 2); A.setHave("grapes", true);
  eq(st().lists[1].goals, [{ item: "wine", qty: 2 }], "edits land in the open list");
  eq(st().lists[0].goals, [{ item: "crate", qty: 3 }], "the other list is untouched");
  const at = st().updatedAt;
  A.switchList("main");
  eq([st().goals, st().have, st().done], [[{ item: "crate", qty: 3 }], { log: 2 }, { "raw:clay": true }], "switching brings its plan back");
  eq(st().updatedAt, at, "switching is not a synced change (no stamp)");
  A.switchList(id);
  eq([st().goals, st().have], [[{ item: "wine", qty: 2 }], { grapes: true }], "and the other one");
  eq(A.renameList(id, "x".repeat(40)).length, 30, "names capped at 30");
  eq(A.renameList(id, "   "), "x".repeat(30), "a blank rename is ignored");
  A.renameList("main", "Fábrica");
  eq(st().lists[0].name, "Fábrica", "renamed");
  check(A.deleteList(id), "deleted");
  eq([st().lists.length, st().ui.activeList, st().goals], [1, "main", [{ item: "crate", qty: 3 }]], "deleting the open list opens the first");
  check(!!st().listsGone[id], "tombstone kept");
  check(!A.deleteList("main"), "the last list cannot be deleted");
  A.clearGoals();
  eq([st().lists.length, st().lists[0].goals], [1, []], "Limpar lista clears only the open list");
});

await test("lists: sanitizeRemote validates lists and folds an older page's edit", () => {
  const S = GK.store, at = "2026-11-02T00:00:00.000Z";
  const r = S.sanitizeRemote({ lists: [
    { id: "b", name: "B", createdAt: "2026-11-01T00:00:00.000Z", updatedAt: "2026-11-01T00:00:00.000Z", goals: [{ item: "wine", qty: 0 }] },
    { id: "main", name: 5, goals: "x", have: { log: -1 } }, { id: "b", name: "dup" }, { id: "bad id!" }, null, "x",
  ], listsGone: { z: "2026-01-01T00:00:00.000Z", "bad id": "2026", y: "nope" } });
  eq(r.lists.map((l) => [l.id, l.name]), [["main", ""], ["b", "B"]], "valid ones, first of each id, creation order");
  eq([r.lists[0].goals, r.lists[0].have, r.lists[1].goals], [[], {}, [{ item: "wine", qty: 1 }]], "content cleaned");
  eq(r.listsGone, { z: "2026-01-01T00:00:00.000Z" }, "tombstones cleaned");
  check(!("goals" in r) && !("example" in r), "no flat plan in the sanitized body");
  // a schema 4 page saved its single plan over a schema 5 copy: the list it mirrored (legacyOf) takes it
  const base = { lists: [{ id: "main", updatedAt: "2026-11-01T00:00:00.000Z", goals: [{ item: "crate", qty: 1 }] }, { id: "b", createdAt: "2026-11-01T00:00:00.000Z", goals: [] }], legacyOf: "b" };
  const f = S.sanitizeRemote(Object.assign({}, base, { goals: [{ item: "wine", qty: 4 }], done: { "raw:log": true } }), false, at);
  eq([f.lists[1].goals, f.lists[1].done, f.lists[1].updatedAt, f.lists[0].goals], [[{ item: "wine", qty: 4 }], { "raw:log": true }, at, [{ item: "crate", qty: 1 }]], "folded into legacyOf");
  const same = S.sanitizeRemote(Object.assign({}, base, { goals: [] }), false, at);
  eq(same.lists[1].updatedAt, "1970-01-01T00:00:00.000Z", "an unchanged mirror changes nothing");
  eq(S.sanitizeRemote({ lists: [{ id: "a", updatedAt: "2026-01-01T00:00:00.000Z" }], listsGone: { a: "2026-02-01T00:00:00.000Z" } }).lists, [], "a deleted list is dropped");
});

await test("lists: mergeSynced by id (union, tombstones, one-sided changes win whole)", () => {
  const S = GK.store, base = "2026-11-01T00:00:00.000Z";
  const T = (d) => "2026-11-0" + d + "T00:00:00.000Z";
  const list = (id, upd, o) => Object.assign({ id, name: id, createdAt: id === "main" ? "1970-01-01T00:00:00.000Z" : T(1), updatedAt: upd, goals: [], choice: {}, have: {}, done: {}, example: false }, o);
  const L = { lists: [list("main", T(1), { goals: [{ item: "crate", qty: 1 }], done: { "raw:a": true } }), list("onlyL", T(2)), list("both", T(3), { goals: [{ item: "wine", qty: 1 }], have: { x: 1 }, name: "L" })], listsGone: {} };
  const R = { lists: [list("main", T(4), { goals: [{ item: "crate", qty: 9 }] }), list("onlyR", T(2)), list("both", T(4), { goals: [{ item: "ink", qty: 1 }], have: { x: 2, y: true }, name: "R" })], listsGone: { gone: T(3) } };
  const m = S.mergeSynced(L, R, true, base), by = Object.fromEntries(m.lists.map((l) => [l.id, l]));
  eq(m.lists.map((l) => l.id).sort(), ["both", "main", "onlyL", "onlyR"], "union by id");
  eq(by.main.goals, [{ item: "crate", qty: 9 }], "main changed only on the account (local is at base): the account copy wins whole");
  eq(by.main.done, {}, "a one-sided change wins whole (an unticked mark stays unticked)");
  eq([by.both.goals, by.both.have, by.both.name], [[{ item: "wine", qty: 1 }], { x: 2, y: true }, "R"], "changed on both: goals local, have union remote wins, name from the newer");
  // a list deleted on one side does not come back from the other
  const L2 = { lists: [list("main", T(1))], listsGone: { onlyR: T(3) } };
  const m2 = S.mergeSynced(L2, R, false, base);
  eq(m2.lists.map((l) => l.id).sort(), ["both", "main"], "tombstone wins over an older copy");
  eq(Object.keys(m2.listsGone).sort(), ["gone", "onlyR"], "tombstones by union");
  const R3 = { lists: [list("onlyR", T(5))] };
  eq(S.mergeSynced(L2, R3, true, base).lists.map((l) => l.id).sort(), ["main", "onlyR"], "a list changed after its deletion stays");
});

await test("sync: a schema 4 doc from another device migrates on arrival and keeps this device's lists", async () => {
  const env = makeEnv();
  const base = "2026-11-01T00:00:00.000Z";
  env.localStorage.setItem("gk2-companion.account", "u9");
  env.localStorage.setItem("gk2-companion:u9", JSON.stringify({ schemaVersion: 5, updatedAt: "2026-11-02T00:00:00.000Z", syncBase: base,
    lists: [{ id: "main", name: "", createdAt: "1970-01-01T00:00:00.000Z", updatedAt: "2026-10-01T00:00:00.000Z", goals: [{ item: "crate", qty: 1 }] },
            { id: "igreja", name: "Igreja", createdAt: "2026-11-02T00:00:00.000Z", updatedAt: "2026-11-02T00:00:00.000Z", goals: [{ item: "wine", qty: 2 }] }],
    ui: { activeList: "igreja" } }));
  const old = { v: 4, updatedAt: "2026-11-03T00:00:00.000Z", state: { goals: [{ item: "crate", qty: 5 }], have: { log: true }, done: {}, perks: { "heat-saver": true } } };
  const { db } = await bootSync(env, "u9", old);
  const s = env.GK.store.get(), by = Object.fromEntries(s.lists.map((l) => [l.id, l]));
  eq(s.lists.map((l) => l.id), ["main", "igreja"], "both lists");
  eq([by.main.goals, by.main.have], [[{ item: "crate", qty: 5 }], { log: true }], "the old device's plan is the main list");
  eq([s.ui.activeList, s.goals, s.perks], ["igreja", [{ item: "wine", qty: 2 }], { "heat-saver": true }], "this device's open list stays open");
  await env.clock.tick(10);
  const w = db.writes[db.writes.length - 1];
  check(!!w, "merged copy pushed");
  eq(w && [w.v, w.state.lists.length, w.state.legacyOf, w.state.goals], [5, 2, "igreja", [{ item: "wine", qty: 2 }]], "doc: lists + the open list flat");
  // switching lists writes nothing (the open list is per device)
  const n = db.writes.length;
  env.GK.store.actions.switchList("main");
  await env.clock.tick(3000);
  eq(db.writes.length, n, "no write on switch");
  // that older page edits the mirror it reads (lists kept as an unknown field): folded into "igreja"
  db.push(Object.assign({}, w, { updatedAt: "2026-11-05T00:00:00.000Z", state: Object.assign({}, w.state, { goals: [{ item: "wine", qty: 7 }] }) }));
  await flushMicro();
  const s2 = env.GK.store.get();
  eq([s2.lists[1].goals, s2.goals, s2.ui.activeList], [[{ item: "wine", qty: 7 }], [{ item: "crate", qty: 5 }], "main"], "older page's edit folded into its list");
});

await test("sync: lists made on two devices meet (union by id)", async () => {
  const env = makeEnv();
  const base = "2026-11-01T00:00:00.000Z";
  env.localStorage.setItem("gk2-companion.account", "u10");
  env.localStorage.setItem("gk2-companion:u10", JSON.stringify({ schemaVersion: 5, updatedAt: base, syncBase: base,
    lists: [{ id: "main", updatedAt: base, goals: [{ item: "crate", qty: 1 }] }] }));
  const doc = { v: 5, updatedAt: "2026-11-03T00:00:00.000Z", state: { lists: [{ id: "main", updatedAt: base, goals: [{ item: "crate", qty: 1 }] },
    { id: "pc", name: "Do PC", createdAt: "2026-11-03T00:00:00.000Z", updatedAt: "2026-11-03T00:00:00.000Z", goals: [{ item: "ink", qty: 1 }] }] } };
  const { db } = await bootSync(env, "u10", doc);
  eq(env.GK.store.get().lists.map((l) => l.name), ["", "Do PC"], "the account's new list arrives");
  env.GK.store.actions.createList("Do celular");
  db.push({ v: 5, updatedAt: "2026-12-01T00:00:00.000Z", state: { lists: doc.state.lists.concat([{ id: "pc2", name: "Outra do PC", createdAt: "2026-11-04T00:00:00.000Z", updatedAt: "2026-11-04T00:00:00.000Z" }]) } });
  await flushMicro();
  const names = env.GK.store.get().lists.map((l) => l.name);
  check(names.indexOf("Do celular") >= 0 && names.indexOf("Outra do PC") >= 0 && names.length === 4, "both new lists kept: " + names.join(", "));
  eq(env.GK.store.get().lists.find((l) => l.id === env.GK.store.get().ui.activeList).name, "Do celular", "still on the list just made");
});

// ---------------------------------------------------------------- "Recentes" na busca (state.recents, synced, global)
const RIDS = ["crate", "wine", "ink", "log", "fuel", "iron-ore", "clay", "sand", "master-sword", "steel-ingot", "beeswax", "grapes", "fat", "leaf"];
await test("recents: addGoal records them, newest first, capped, global across lists", () => {
  const env = makeEnv(), S = env.GK.store, A = S.actions, st = () => S.get();
  env.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  eq(st().recents, [], "fresh: none");
  check(S.SYNCED.indexOf("recents") >= 0, "synced field");
  A.addGoal("crate", 1); A.addGoal("wine", 2); A.addGoal("ink", 1);
  eq(st().recents, ["ink", "wine", "crate"], "newest first");
  const at = st().updatedAt;
  A.addGoal("crate", 1);
  eq(st().recents, ["crate", "ink", "wine"], "adding again moves it to the front (no duplicate)");
  check(st().updatedAt > at, "a synced change (stamped)");
  A.addRecent("wine");
  eq(st().recents, ["wine", "crate", "ink"], "addRecent");
  const at2 = st().updatedAt;
  A.addRecent("wine"); A.addRecent("no-such-item"); A.addRecent(5);
  eq([st().recents, st().updatedAt], [["wine", "crate", "ink"], at2], "already first / unknown: no change");
  for (const id of RIDS) A.addGoal(id, 1);
  eq(st().recents, RIDS.slice().reverse().slice(0, S.RECENTS_MAX), "capped at RECENTS_MAX (12)");
  A.createList("Outra");
  eq(st().recents[0], "leaf", "recents are global: a new list keeps them");
  A.addGoal("crate", 1);
  A.switchList("main");
  eq(st().recents[0], "crate", "and an add in another list counts too");
  env.clock.tick(200);
  eq(JSON.parse(env.localStorage.getItem("gk2-companion")).recents[0], "crate", "saved locally");
});

await test("recents: sanitizeRemote and mergeSynced", () => {
  const S = GK.store, san = (o) => S.sanitizeRemote(o);
  eq(san({ recents: ["wine", "nope", "wine", 3, null, "", "crate"] }).recents, ["wine", "crate"], "only known item ids, no duplicates");
  eq([san({}).recents, san({ recents: "wine" }).recents, san({ recents: { a: 1 } }).recents], [[], [], []], "absent / not an array");
  eq(san({ recents: RIDS }).recents.length, 12, "at most 12 kept");
  const L = san({ recents: ["crate", "wine", "ink"] }), R = san({ recents: ["log", "wine", "fuel"] });
  eq(S.mergeSynced(L, R).recents, ["crate", "wine", "ink", "log", "fuel"], "union, local order first when local is newer");
  eq(S.mergeSynced(L, R, true).recents, ["log", "wine", "fuel", "crate", "ink"], "union, remote order first when the account is newer");
  eq(S.mergeSynced(san({ recents: RIDS.slice(0, 8) }), san({ recents: RIDS.slice(6) })).recents, RIDS.slice(0, 12), "merged list capped");
  eq(S.mergeSynced(L, san({})).recents, L.recents, "remote without recents keeps ours");
  // a doc from a page older than recents (no key at all): ours stay
  const raw = { goals: [] };
  eq(S.keepLate(san(raw), raw, L).recents, L.recents, "keepLate: keep ours when the doc lacks the key");
  eq(S.keepLate(san(raw), Object.assign({ recents: [] }, raw), L), null, "keepLate: an explicit empty value is a real clear");
  eq(S.adoptLate(L, san({})).recents, L.recents, "adoptLate: take the doc's when we have none");
  eq(S.adoptLate(san({}), L), null, "adoptLate: nothing to adopt");
});

await test("recents: a schema 5 copy without the field loads with none; sync merges both sides", async () => {
  const env = makeEnv();
  const base = "2026-11-01T00:00:00.000Z";
  env.localStorage.setItem("gk2-companion.account", "u11");
  env.localStorage.setItem("gk2-companion:u11", JSON.stringify({ schemaVersion: 5, updatedAt: base, syncBase: base,
    lists: [{ id: "main", updatedAt: base, goals: [{ item: "crate", qty: 1 }] }] }));
  const doc = { v: 5, updatedAt: base, state: { lists: [{ id: "main", updatedAt: base, goals: [{ item: "crate", qty: 1 }] }] } };
  const { db } = await bootSync(env, "u11", doc);
  eq(env.GK.store.get().recents, [], "no recents yet");
  env.GK.store.actions.addGoal("wine", 1);   // this device adds; meanwhile the account got another device's recents
  db.push({ v: 5, updatedAt: "2026-12-01T00:00:00.000Z", state: { lists: doc.state.lists, recents: ["ink", "crate"] } });
  await flushMicro();
  eq(env.GK.store.get().recents, ["ink", "crate", "wine"], "merged (the account is newer: its order first)");
  await env.clock.tick(3000);
  const w = db.writes[db.writes.length - 1];
  eq(w && w.state.recents, ["ink", "crate", "wine"], "merged copy pushed");
});

await test("item facts reach the page (where / use / stack, meta.refs)", () => {
  const refs = D.meta.refs || {};
  check(refs.names && refs.buffs, "meta.refs has the name and buff tables");
  const pk = D.items["pumpkin"], soup = D.items["pumpkin-soup"], bream = D.items["bream"];
  eq(pk.where && pk.where[0], ["buy", "vegetable-stand", 2], "Abóbora: bought at the Vegetable Stand from level 2");
  eq(soup.use, { en: 20, enB: [22, "steamed-up"], buff: ["building-spirit-ii", 450, 1] }, "Sopa de abóbora: energy, boost, buff");
  eq(soup.stack, 30, "Sopa de abóbora stacks 30");
  eq(bream.where && bream.where[0], ["fish", "village", "breadcrumb-bait", 50, 33.3], "Brema: spot, bait, day/night chance");
  const vs = refs.names["vegetable-stand"];
  eq(typeof vs === "string" ? vs : vs.pt, "Banca de Vegetais", "trader name: official pt");
  eq(refs.names.tree && refs.names.tree.tr, "machine", "gathering node without official text is marked machine");
  eq(refs.buffs["building-spirit-ii"].pt, "Espírito da Engenharia II", "buff name: official pt");
  for (const it of Object.values(D.items)) {
    for (const w of it.where || []) {
      if (w[1][0] === "@") check(D.items[w[1].slice(1)], `${it.id}: source item ${w[1]} exists`);
      else check(refs.names[w[1]] != null, `${it.id}: source name ${w[1]} is in meta.refs.names`);
    }
  }
});

// ---------------------------------------------------------------- ficha do item: "Já estudei" (state.studied, synced, global)
await test("studied: setStudied, global across lists, saved, no-op changes ignored", () => {
  const env = makeEnv(), S = env.GK.store, A = S.actions, st = () => S.get();
  env.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  eq(st().studied, [], "fresh: none");
  check(S.SYNCED.indexOf("studied") >= 0 && S.LATE.indexOf("studied") >= 0, "synced, and a late field");
  check(S.PER_LIST.indexOf("studied") < 0, "not per list");
  A.setStudied("wine", true); A.setStudied("beer", true); A.setStudied("wine", true);
  eq(st().studied, ["beer", "wine"], "sorted, no duplicates");
  const at = st().updatedAt;
  A.setStudied("no-such-item", true); A.setStudied("crate", false);
  eq([st().studied, st().updatedAt], [["beer", "wine"], at], "unknown id / unchecking an unchecked one: no change");
  A.createList("Outra");
  eq(st().studied, ["beer", "wine"], "global: a new list keeps them");
  A.setStudied("beer", false);
  check(st().updatedAt > at, "a synced change (stamped)");
  eq(st().studied, ["wine"], "unchecked");
  check(S.hasContent({ studied: ["wine"] }), "counts as content");
  env.clock.tick(200);
  eq(JSON.parse(env.localStorage.getItem("gk2-companion")).studied, ["wine"], "saved locally");
});

await test("studied: sanitizeRemote, mergeSynced (union), keepLate / adoptLate", () => {
  const S = GK.store, san = (o) => S.sanitizeRemote(o);
  eq(san({ studied: ["wine", "nope", "wine", 3, null, "", "beer"] }).studied, ["beer", "wine"], "only known item ids, sorted, no duplicates");
  eq([san({}).studied, san({ studied: "wine" }).studied, san({ studied: { wine: true } }).studied], [[], [], []], "absent / not an array");
  const L = san({ studied: ["wine", "beer"] }), R = san({ studied: ["crate", "wine"] });
  eq(S.mergeSynced(L, R).studied, ["beer", "crate", "wine"], "union");
  eq(S.mergeSynced(L, R, true).studied, ["beer", "crate", "wine"], "union whichever side is newer");
  eq(S.mergeSynced(L, san({})).studied, L.studied, "remote without studied keeps ours");
  const raw = { goals: [] };
  eq(S.keepLate(san(raw), raw, L).studied, L.studied, "keepLate: keep ours when the doc lacks the key");
  eq(S.keepLate(san(raw), Object.assign({ studied: [] }, raw), L), null, "keepLate: an explicit empty list is a real clear");
  eq(S.adoptLate(L, san({})).studied, L.studied, "adoptLate: take the doc's when we have none");
  eq(S.adoptLate(san({}), L), null, "adoptLate: nothing to adopt");
});

await test("ficha do item: sell / price / study / asked reach the page", () => {
  const names = D.meta.refs.names, nm = (k) => { const e = names[k]; return typeof e === "string" ? e : e && e.pt; };
  const pb = D.items["polished-bronze"], gf = D.items["goldfish"], beer = D.items["beer"];
  eq(pb.sell, [["furniture-maker", 54, 56, 20], ["jeweler", 55, 56, 40], ["smithy", 54, 55]], "Bronze Polido: three buyers, usual-stock range, Likes");
  eq([pb.price, pb.fix, pb.study], [75, undefined, [30, 0, 20, 3]], "Bronze Polido: base price 75; 30 red, 20 blue, 3 Science");
  eq([gf.sell, gf.price, gf.fix, gf.study], [[["fish-stand"]], 72, 1, [50, 50, 50, 3, 3]], "Peixinho-dourado: fixed 72; 50/50/50, 3 Science + 3 Faith");
  eq(beer.asked && beer.asked.q, [["yummies", 2, "village-guards"], ["comrade-donkey", 2, "larry"], ["tales-for-ales", 2, "captain"]], "Cerveja: three quests, two each");
  eq([nm("yummies"), nm("larry"), nm("furniture-maker"), nm("jeweler-ii")], ["Festa das Guloseimas", "Lauro", "Marceneiro", "Joalheiro II"], "official pt names");
  check(names.captain && names.captain.tr === "machine", "Capitão: no official name, marked");
  for (const it of Object.values(D.items)) {
    for (const e of it.sell || []) check(names[e[0]] != null, `${it.id}: buyer ${e[0]} is in meta.refs.names`);
    for (const k of Object.keys(it.asked || {})) for (const e of it.asked[k]) {
      check(names[e[0]] != null, `${it.id}: asked ${k} ${e[0]} is in meta.refs.names`);
      if (k === "q" && e[2]) check(names[e[2]] != null, `${it.id}: quest giver ${e[2]} is in meta.refs.names`);
    }
  }
});

await test("grades: the star's grade on items and lines, always bronze, silver, gold (1.8.0)", () => {
  const G = GK.data, R = G.GRADE_RANK;
  eq(["grape-juice-bronze", "grape-juice-silver", "grape-juice-gold", "cabbage-silver", "cabbage", "wine", "wine-gold"].map((id) => G.itemGrade(D.items[id])),
    ["bronze", "silver", "gold", "silver", null, null, "gold"], "item grades (the plain item has none: its lines carry bronze)");
  const lineOf = (rid, item) => D.recipeById[rid].in.find((l) => l.item === item);
  eq(lineOf("supply-vegetables-from-cabbage-bronze", "cabbage").grade, "bronze", "bronze keeps the plain Repolho, with the bronze star");
  check(!!lineOf("supply-vegetables-from-cabbage-gold", "cabbage-gold"), "gold points to the variant");
  eq(lineOf("drink-enhancement-i-from-wine-bronze", "wine").grade, "bronze", "melhoria I: the plain Vinho in, read as bronze");
  check(!!lineOf("drink-enhancement-ii-from-wine-silver", "wine-silver"), "melhoria II: Vinho (prata) in");
  eq(lineOf("grape-juice-from-grapes-bronze", "grapes").grade, "bronze", "Prensa bronze: the plain Uvas, read as bronze");
  // every list of recipes of an item: a family (same id but the grade) in bronze, silver, gold order
  let fams = 0;
  for (const [id, rs] of Object.entries(D.byOut)) {
    const seen = {};
    for (const r of rs) {
      const f = G.family(r); if (!f) continue;
      if (seen[f] != null) { check(R[r.quality] > seen[f], `${id}: ${r.id} after a higher grade`); fams++; }
      seen[f] = R[r.quality];
    }
  }
  check(fams > 20, "families checked: " + fams);
  eq(D.byOut["supply-wine"].map((r) => r.quality), ["bronze", "silver", "gold"], "Suprimento: Vinho: bronze, prata, ouro");
  eq(GK.calc.search("suco de uva", D, { lang: "pt" }).results.map((r) => r.id).filter((id) => /^grape-juice-/.test(id)),
    ["grape-juice-bronze", "grape-juice-silver", "grape-juice-gold"], "search: bronze, prata, ouro (alphabetical would be bronze, ouro, prata)");
  eq(GK.calc.search("uva", D, { lang: "en" }).results.map((r) => r.id).filter((id) => /^grape-juice-/.test(id)),
    ["grape-juice-bronze", "grape-juice-silver", "grape-juice-gold"], "search en: bronze, silver, gold");
  const list = ["x", "a-gold", "y", "a-bronze", "a-silver"];
  G.gradeSort(list, (k) => (k.startsWith("a-") ? "a" : null), (k) => R[k.slice(2)]);
  eq(list, ["x", "a-bronze", "y", "a-silver", "a-gold"], "gradeSort keeps the family's positions and the others in place");
  eq([G.stripGrade("Suco de Uva (prata)"), G.stripGrade("Grape Juice (gold)"), G.stripGrade("Bronze Polido")], ["Suco de Uva", "Grape Juice", "Bronze Polido"], "stripGrade");
});

await test("receitas agrupadas: GK.calc.recipeGroups (1.8.0, consertos.md §10)", () => {
  const groups = (id) => GK.calc.recipeGroups(GK.data.recipesFor(id), D);
  // Suprimento: Vinho: the three recipes in one card (mode q: same ingredient, grades), the amount per grade (8 / 6 / 4).
  // (Up to 1.8.1 the example was Vinho itself, whose three Barril recipes all made the same item: 1.9 gives each grade
  // its own Vinho.)
  const w = groups("supply-wine");
  eq(w.cards.length, 1, "Suprimento: Vinho: one card");
  const g = w.cards[0];
  eq([g.group, g.mode, g.masteryEach, g.qtyEach], [true, "q", false, true], "Suprimento: Vinho: grades of one ingredient, amount per grade");
  eq(g.options.map((o) => [o.grade, o.line.qty, o.line.item]), [["bronze", 8, "wine"], ["silver", 6, "wine-silver"], ["gold", 4, "wine-gold"]], "bronze/prata/ouro 8 / 6 / 4 Vinho");
  eq(g.fixed, [], "Suprimento: Vinho: no shared line");
  eq(w.cyc, [], "nothing circular");
  eq(groups("wine-silver").cards.map((c) => c.r && c.r.id), ["wine-from-grape-juice-silver", "drink-enhancement-i-from-wine-bronze"], "Vinho (prata): Barril first, the melhoria a card of its own");
  eq(groups("wine-silver").cyc, [], "Vinho (prata): the melhoria is not circular");
  // Suprimentos: Vegetais: 11 recipes, one card, mode alt, rows: plain ones first, then the graded ones
  const s = groups("supply-vegetables"), sg = s.cards[0];
  eq([s.cards.length, sg.mode, sg.recipes.length, sg.masteryEach], [1, "alt", 11, false], "Suprimentos: Vegetais: one card of 11");
  eq(sg.fixed.map((l) => [l.item, l.qty]), [["crate", 1]], "shared line: 1 Caixote");
  eq(sg.rows.map((r) => r.item.id + ":" + r.options.map((o) => (o.grade || "-") + o.line.qty).join(",")),
    ["beet:-12", "carrot:-16", "cabbage:bronze10,silver8,gold6", "onion:bronze8,silver6,gold4", "pumpkin:bronze3,silver2,gold1"], "rows and options");
  // yield differs (Sopa de repolho 4 / 7 / 10): three cards; a mastery-only difference with the same input (Canteiro): three cards
  eq(groups("cabbage-soup").cards.map((c) => !!c.group), [false, false, false], "Sopa de repolho: yields differ, separate");
  eq(groups("cabbage-bed").cards.filter((c) => c.group).length, 0, "Canteiro de Repolho: same input, separate");
  eq(groups("cabbage-bed").cyc.length, 0, "no circular: nothing folded");
  // all recipes circular (Pele): nothing folded, they stay cards
  const skin = groups("skin");
  check(skin.cyc.length === 0 && skin.cards.length === GK.data.recipesFor("skin").length, "Pele: every recipe circular, none folded");
  // synthetic cases: one line changes but so does the tech / the yield / a second line → no group; two grades with
  // different mastery in mode alt → no group
  const base = D.recipeById["supply-vegetables-from-cabbage-bronze"];
  const mk = (id, patch) => Object.assign({}, base, { id, name: null }, patch);
  const a = mk("t-a", {}), b = mk("t-b", { in: [{ item: "crate", qty: 1 }, { item: "carrot", qty: 16 }] });
  eq(GK.calc.recipeGroups([a, b], D).cards.length, 1, "one line differs: grouped");
  eq(GK.calc.recipeGroups([a, mk("t-c", { in: b.in, tech: { id: "other", en: "Other", pt: "Outra" } })], D).cards.length, 2, "tech differs: separate");
  eq(GK.calc.recipeGroups([a, mk("t-d", { in: b.in, out: { item: base.out.item, qty: 2 } })], D).cards.length, 2, "yield differs: separate");
  eq(GK.calc.recipeGroups([a, mk("t-e", { in: [{ item: "log", qty: 1 }, { item: "carrot", qty: 16 }] })], D).cards.length, 2, "two lines differ: separate");
  eq(GK.calc.recipeGroups([a, mk("t-f", { in: b.in, ticks: 9 })], D).cards.length, 2, "time differs: separate");
  eq(GK.calc.recipeGroups([a, mk("t-g", { in: b.in, mastery: { type: base.mastery.type, level: 9 } })], D).cards.length, 2, "mode alt with different mastery: separate");
  // counts over the whole data (the report's numbers)
  let items = 0, recipes = 0;
  for (const id of Object.keys(D.byOut)) {
    const gs = GK.calc.recipeGroups(D.byOut[id], D).cards.filter((c) => c.group);
    if (gs.length) { items++; recipes += gs.reduce((n, c) => n + c.recipes.length, 0); }
  }
  // 1.9: Vinho left the count (its three Barril recipes now make three items): 7 items, 39 recipes
  eq([items, recipes], [7, 39], "7 items have a group card; 39 recipes in them");
});

// ---------------------------------------------------------------- 1.9: qualidade (docs/revisao-ux/consertos.md "Qualidade")
await test("qualidade: Vinho (prata) has its own recipe, the Barril with Suco (prata) makes it, the melhoria is not circular", () => {
  const ws = D.items["wine-silver"], wg = D.items["wine-gold"];
  check(ws && !ws.synthetic && ws.base === "wine" && ws.grade === "silver" && wg && wg.grade === "gold", "Vinho (prata) / (ouro) are items of the data");
  eq(ws.defaultRecipe, "wine-from-grape-juice-silver", "Vinho (prata): default = Barril with Suco de Uva (prata)");
  eq(wg.defaultRecipe, "wine-from-grape-juice-gold", "Vinho (ouro): default = Barril with Suco de Uva (ouro)");
  eq(GK.data.recipesFor("wine-silver").map((r) => r.id), ["wine-from-grape-juice-silver", "drink-enhancement-i-from-wine-bronze"], "the melhoria stays an alternative");
  const b = D.recipeById["wine-from-grape-juice-silver"];
  eq([b.out.item, b.out.qty, b.in.map((l) => [l.item, l.qty]), b.quality], ["wine-silver", 4, [["grape-juice-silver", 4]], "silver"], "Barril: 4 Suco de Uva (prata) → 4 Vinho (prata)");
  eq(["bronze", "silver", "gold"].map((g) => D.recipeById["wine-from-grape-juice-" + g].out.item), ["wine", "wine-silver", "wine-gold"], "each Barril grade makes its own Vinho");
  const m1 = D.recipeById["drink-enhancement-i-from-wine-bronze"], m2 = D.recipeById["drink-enhancement-ii-from-wine-silver"];
  eq([m1.out.item, m1.in.map((l) => l.item), m1.cyc, m1.quality], ["wine-silver", ["wine", "spices"], false, "silver"], "melhoria I: Vinho + Especiarias → Vinho (prata)");
  eq([m2.out.item, m2.in.map((l) => l.item), m2.cyc, m2.quality], ["wine-gold", ["wine-silver", "umami"], false, "gold"], "melhoria II: Vinho (prata) + Umami → Vinho (ouro)");
  for (const id of ["wine-silver", "wine-gold", "grape-juice-silver", "grape-juice-gold", "vegetable-salad-gold", "bowl-of-sauerkraut-silver", "story-gold", "newspaper-silver"])
    check(GK.data.recipesFor(id).every((r) => !r.cyc && !r.in.some((l) => l.item === id)), id + ": no recipe consumes what it makes");
  const p = plan([{ item: "wine-silver", qty: 6 }]);
  eq([p.refused, stepOf(p, "wine-silver") && stepOf(p, "wine-silver").recipe.id, stepOf(p, "grape-juice-silver") && stepOf(p, "grape-juice-silver").need, rawMap(p)["grapes-silver"]],
    [[], "wine-from-grape-juice-silver", 8, 48], "meta Vinho (prata) ×6: Barril, 8 Suco (prata), 48 Uvas (prata)");
  check(!p.raw.some((r) => r.item === "wine-silver"), "Vinho (prata) is no longer a raw material");
  const p2 = plan([{ item: "wine-gold", qty: 1 }], { choice: { "wine-gold": "drink-enhancement-ii-from-wine-silver" } });
  eq([stepOf(p2, "wine-gold").recipe.id, stepOf(p2, "wine-silver").recipe.id, stepOf(p2, "wine") && stepOf(p2, "wine").recipe.id],
    ["drink-enhancement-ii-from-wine-silver", "wine-from-grape-juice-silver", undefined], "Vinho (ouro) by the melhoria: Vinho (prata) + Umami, the prata from its Barril");
  // rendimentos por grau (dados por receita): Suprimento: Vinho 8 / 6 / 4; Sopa de repolho 4 / 7 / 10
  eq(["bronze", "silver", "gold"].map((g) => D.recipeById["supply-wine-from-wine-" + g].in[0].qty), [8, 6, 4], "Suprimento: Vinho 8 / 6 / 4");
  eq(["bronze", "silver", "gold"].map((g) => D.recipeById["cabbage-soup-from-cabbage-" + g].out.qty), [4, 7, 10], "Sopa de repolho 4 / 7 / 10");
});

await test("qualidade: the Prensa asks for Uvas of the juice's grade; crops tell how to get them", () => {
  eq(["bronze", "silver", "gold"].map((g) => D.recipeById["grape-juice-from-grapes-" + g].in.find((l) => /^grapes/.test(l.item)).item), ["grapes", "grapes-silver", "grapes-gold"], "6 Uvas of the same grade");
  eq(["grape-juice-silver", "grape-juice-gold"].map((id) => D.items[id].defaultRecipe), ["grape-juice-from-grapes-silver", "grape-juice-from-grapes-gold"], "Suco (prata/ouro): default = the Prensa");
  for (const id of ["grapes", "cabbage", "onion", "pumpkin"]) for (const g of ["silver", "gold"]) {
    const it = D.items[id + "-" + g];
    check(it && it.base === id && !it.defaultRecipe && it.obtain && it.obtain.pt === (g === "silver" ? "Colheita: semente bronze ou prata." : "Colheita: semente prata ou ouro."), `${id}-${g}: no craft recipe, "como obter" says the seed`);
    check(it && it.obtain.en === (g === "silver" ? "Harvest: bronze or silver seeds." : "Harvest: silver or gold seeds."), `${id}-${g}: en text`);
  }
  // the bed of each seed grade: a silver seed gives silver + gold (Canteiro de Repolho, Agricultura 10)
  const bed = D.recipeById["grow-cabbage-bed-m10"];
  eq([bed.in[0].item, bed.out.item, bed.extra.slice(0, 3).map((l) => l.item)], ["cabbage-seed-silver", "cabbage-silver", ["cabbage-gold", "cabbage-seed-silver", "cabbage-seed-gold"]], "Canteiro: semente prata → prata + ouro");
  eq(D.recipeById["plant-cabbage-seed-gold"].in[0].item, "cabbage-seed-gold", "Plantar semente (ouro) takes the gold seed");
  const p = plan([{ item: "cabbage-soup", qty: 7 }], { choice: { "cabbage-soup": "cabbage-soup-from-cabbage-silver" } });
  const r = p.raw.find((x) => x.item === "cabbage-silver");
  check(r && r.qty === 2, "Repolho (prata) is a raw material of the plan");
});

await test("qualidade: star crafts make every grade (História, Jornal, Salada, Chucrute)", () => {
  for (const [rid, fam] of [["story", "story"], ["printing-press", "newspaper"], ["vegetable-salad", "vegetable-salad"], ["bowl-of-sauerkraut", "bowl-of-sauerkraut"]]) {
    const o = D.recipeById[rid];
    eq(o.out.item, fam, rid + ": the original recipe keeps its output (the prayers ask for the plain História)");
    for (const g of ["bronze", "silver", "gold"]) {
      const c = D.recipeById[rid + "-" + g];
      check(c && c.out.item === fam + "-" + g && c.out.qty === o.out.qty && JSON.stringify(c.in) === JSON.stringify(o.in) && JSON.stringify(c.star) === JSON.stringify(o.star) && c.type === "star_craft",
        `${rid}-${g}: same star craft, makes ${fam}-${g}`);
      eq(D.items[fam + "-" + g].defaultRecipe, rid + "-" + g, `${fam}-${g}: default = the star craft`);
    }
  }
  eq(GK.data.recipesFor("story-silver").map((r) => r.id), ["story-silver", "improve-story-i"], "História (prata): escrever, or 2 bronze → 1 prata");
  eq(GK.data.recipesFor("newspaper-gold").map((r) => r.id), ["printing-press-gold", "improve-newspaper-ii"], "Jornal (ouro): imprimir, or 20 prata + 1 História (ouro)");
  // a goal that asks for História (bronze) / Jornal (bronze): made at the Escrivaninha / Prensa, not "Coleta ou compra"
  const p = plan([{ item: "primer", qty: 1 }, { item: "20-zombie-limit-for-2-weeks", qty: 1 }], { groupChoice: { "any-newspaper": "newspaper-bronze" } });
  check(!p.raw.some((r) => r.item === "story-bronze" || r.item === "newspaper-bronze"), "História / Jornal (bronze) are not raw materials");
  eq([stepOf(p, "story-bronze") && stepOf(p, "story-bronze").recipe.id, stepOf(p, "newspaper-bronze") && stepOf(p, "newspaper-bronze").recipe.id], ["story-bronze", "printing-press-bronze"], "their steps");
});

await test("qualidade: Bronze Polido has no grade; no grade word in the recipe labels; no grade badge in the steps", () => {
  const pb = D.recipeById["polished-bronze"];
  eq([pb.quality, GK.data.itemGrade(D.items["polished-bronze"]), GK.data.family(pb), GK.data.family(D.items["polished-bronze"])], [null, null, null, null], "Bronze Polido: no quality");
  eq(Object.values(D.items).filter((it) => it.grade && !/-(bronze|silver|gold)$/.test(it.id)).length, 0, "a grade only on graded ids");
  const st = GK.store.get();
  const labs = GK.ui.fmt.recipeLabels(GK.data.recipesFor("grape-juice-silver"), st, GK.data.recipesFor("grape-juice-silver"));
  eq(labs.length, 2, "Suco de Uva (prata): two options");
  check(/^6 Uvas \(prata\) \+ 1 Garrafa/.test(labs[0]) && /^1 Suco de Uva \(bronze\) \+ 1 Especiarias → 1/.test(labs[1]) && labs.every((l) => !/ · (bronze|prata|ouro)\b/.test(l)),
    "labels: the ingredients tell them apart, no grade word: " + labs.join(" | "));
  eq([GK.ui.fmt.recipeTag(D.recipeById["drink-enhancement-ii-from-grape-juice-silver"]), GK.ui.fmt.recipeTag(D.recipeById["cabbage-soup-from-cabbage-gold"])], ["", ""], "recipeTag: no grade word");
  const src = fs.readFileSync(path.join(ROOT, "src/js/ui/summary.js"), "utf8");
  check(!/badge-q/.test(src), "Etapas: no grade badge (badge-q) left");
  check(/badge-goal/.test(src), "Etapas: the META badge stays");
});

await test("qualidade: a plan saved up to 1.8.1 opens (goal wine + the Barril prata chosen; goal wine-silver)", () => {
  const env = makeEnv(), S = env.GK.store;
  env.GK.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  env.localStorage.setItem("gk2-companion", JSON.stringify({ schemaVersion: 5, updatedAt: "2026-10-30T00:00:00.000Z", ui: { activeList: "main" },
    lists: [{ id: "main", name: "", createdAt: "1970-01-01T00:00:00.000Z", updatedAt: "2026-10-30T00:00:00.000Z",
      goals: [{ item: "wine", qty: 4 }, { item: "supply-wine", qty: 1 }, { item: "wine-silver", qty: 2 }],
      choice: { wine: "wine-from-grape-juice-silver", "supply-wine": "supply-wine-from-wine-silver", "grape-juice-silver": "drink-enhancement-i-from-grape-juice-bronze" },
      have: { "wine-silver": 1, "cabbage-silver": true }, done: { "step:wine": 4, "raw:grapes": true } },
    { id: "l2", name: "Ouro", createdAt: "2026-10-01T00:00:00.000Z", updatedAt: "2026-10-01T00:00:00.000Z",
      goals: [{ item: "wine", qty: 1 }], choice: { wine: "drink-enhancement-ii-from-wine-silver" }, have: {}, done: {} }] }));
  check(S.load(), "loaded");
  const s = S.get();
  eq(s.goals, [{ item: "wine-silver", qty: 6 }, { item: "supply-wine", qty: 1 }], "goal wine planned with the Barril prata → Vinho (prata), merged with the one there");
  const sorted = (o) => Object.fromEntries(Object.entries(o).sort());
  eq(sorted(s.choice), sorted({ "wine-silver": "wine-from-grape-juice-silver", "supply-wine": "supply-wine-from-wine-silver", "grape-juice-silver": "drink-enhancement-i-from-grape-juice-bronze" }), "choices kept (the Vinho one moved to Vinho (prata))");
  eq([s.have, sorted(s.done)], [{ "wine-silver": 1, "cabbage-silver": true }, sorted({ "step:wine-silver": 4, "raw:grapes": true })], "have and ticks kept (the step tick moved with its goal)");
  const l2 = s.lists.find((l) => l.id === "l2");
  eq([l2.goals, l2.choice], [[{ item: "wine-gold", qty: 1 }], { "wine-gold": "drink-enhancement-ii-from-wine-silver" }], "the other list too: melhoria II → Vinho (ouro)");
  let p;
  try { p = env.GK.calc.plan(s.goals, env.GK.data.get(), { choice: s.choice, have: s.have }); } catch (e) { check(false, "plan threw " + e); }
  check(p && !p.refused.length && p.steps.some((x) => x.item === "wine-silver" && x.recipe.id === "wine-from-grape-juice-silver"), "the plan makes Vinho (prata) at the Barril");
  check(p && p.steps.some((x) => x.item === "grape-juice-silver" && x.recipe.id === "drink-enhancement-i-from-grape-juice-bronze"), "the saved Suco (prata) choice still applies");
  // nothing to move: the same object comes back untouched (no stamp, no push)
  eq(env.GK.data.gradeMoves([{ item: "crate", qty: 1 }], { "steel-sword": "r-x" }, {}), null, "a plan without an old grade choice is left alone");
  // the account doc (sanitizeRemote) goes through the same move
  const f = S.sanitizeRemote({ goals: [{ item: "wine", qty: 2 }], choice: { wine: "wine-from-grape-juice-gold" } });
  eq([f.lists[0].goals, f.lists[0].choice], [[{ item: "wine-gold", qty: 2 }], { "wine-gold": "wine-from-grape-juice-gold" }], "account doc: moved as well");
});

await test("renomear no detalhe (Receitas): the \"não oficial\" tag opens the name's field; Salvar / Voltar ao nome original", () => {
  const env = makeEnv(), G = env.GK, ctx = env.ctx;
  G.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  // a small fake DOM: the module only writes innerHTML and listens on its root
  const fake = () => {
    const kids = {}, ls = {};
    return { hidden: false, innerHTML: "", value: "", open: false, classList: { add() {} }, ls,
      querySelector: (q) => (kids[q] = kids[q] || fake()), querySelectorAll: () => [], addEventListener: (t, f) => { (ls[t] = ls[t] || []).push(f); },
      contains: () => true, focus() {}, setAttribute() {}, appendChild() {} };
  };
  const toasts = [], copied = [];
  ctx.sessionStorage = { getItem: () => null, setItem() {} };
  ctx.scrollTo = () => {}; ctx.scrollY = 0; ctx.location = { hash: "recipes" }; ctx.CSS = { escape: (x) => x };
  G.router = { current: () => "recipes", tab: () => ({ screen: "recipes" }), TABS: [], register() {}, onChange() {}, detailHistory: () => ({ push() {}, pop() {} }) };
  G.app = { registerPanel() {} };
  G.ui.toast = (m) => toasts.push(m);
  G.util.copyText = async (txt) => { copied.push(txt); return true; };
  vm.runInContext(fs.readFileSync(path.join(ROOT, "src/js/ui/recipes.js"), "utf8"), ctx, { filename: "recipes.js" });
  const R = G.ui.recipes, root = fake();
  R.mount(root);
  const detail = root.querySelector(".rc-detail");
  const fire = (type, data, extra) => root.ls[type].forEach((f) => f(Object.assign({ preventDefault() {}, target: { closest: () => ({ dataset: data, elements: { v: { value: extra } }, getAttribute: () => null }) } }, {})));
  const click = (data) => fire("click", data);
  const id = "village-toilet", it = G.data.item(id);
  eq(it && it.tr, "machine", "fixture: Banheiro da vila is an unofficial (machine) name");
  R.open(id);
  let h = detail.innerHTML;
  check(/<button type="button" class="badge badge-btn" id="rc-rename" data-rename aria-expanded="false"[^>]*aria-label="Renomear Banheiro da vila">não oficial<span class="badge-pen" aria-hidden="true">✎<\/span><\/button>/.test(h), "the tag is a button labelled \"Renomear Banheiro da vila\"");
  check(!/data-rename-form/.test(h), "no field until the tag is tapped");
  click({ rename: "" });
  h = detail.innerHTML;
  check(/<form class="edit-form rc-rename" id="rc-rename-box" data-rename-form>/.test(h) && /id="rc-rename-in" name="v" value="Banheiro da vila"/.test(h), "tap: the field opens with the name");
  check(/aria-expanded="true" aria-controls="rc-rename-box"/.test(h) && />Salvar</.test(h) && />Cancelar</.test(h), "Salvar / Cancelar; the tag says it is open");
  check(!/data-rename-reset/.test(h), "no \"Voltar ao nome original\" before an edit");
  click({ renameCancel: "" });
  check(!/data-rename-form/.test(detail.innerHTML), "Cancelar closes it");
  click({ rename: "" });
  fire("submit", {}, "  Privada da vila ");
  eq(G.store.get().overrides, { pt: { [id]: "Privada da vila" } }, "Salvar writes GK.store overrides (the synced edited names)");
  eq(toasts.pop(), "Nome salvo: Privada da vila", "toast");
  h = detail.innerHTML;
  check(/class="rc-name" id="rc-detail-h" tabindex="-1">Privada da vila</.test(h) && /class="badge badge-edited badge-btn"[^>]*aria-label="Renomear Privada da vila">editado</.test(h) && !/data-rename-form/.test(h), "the new name, the \"editado\" tag (still the rename button), the field closed");
  click({ rename: "" });
  h = detail.innerHTML;
  check(/id="rc-rename-reset" data-rename-reset>Voltar ao nome original</.test(h), "edited: \"Voltar ao nome original\"");
  check(/data-export-names>Exportar nomes editados \(1\)</.test(h), "the contributor's export sits in the open field");
  click({ exportNames: "" });
  eq(JSON.parse(copied.pop() || "{}"), { "Village toilet": { pt: "Privada da vila", source: "user", confidence: "guess" } }, "export: JSON keyed by the English name");
  click({ renameReset: "" });
  eq(G.store.get().overrides, {}, "Voltar ao nome original: the edit is gone");
  check(/>Banheiro da vila</.test(detail.innerHTML) && /aria-label="Renomear Banheiro da vila">não oficial</.test(detail.innerHTML), "back to the original name and the \"não oficial\" tag");
  // the same name saved again is a no-op; an official name has no tag, so nothing to rename
  click({ rename: "" }); fire("submit", {}, "Banheiro da vila");
  eq([G.store.get().overrides, toasts.length], [{}, 1], "saving the same name changes nothing");
  R.open("crate");
  check(!/data-rename/.test(detail.innerHTML), "an official name (Caixote): no rename tag");
  G.i18n.set("en"); R.open(id);
  check(!/data-rename/.test(detail.innerHTML), "English: no \"unofficial\" tag, no rename");
});

// ---------------------------------------------------------------- seta das seções, opção A (1.8.x)
// Tecnologias tab: only the first column with something left starts open; the player's choice is kept per branch
function techEnv() {
  const env = makeEnv(), G = env.GK, ctx = env.ctx;
  G.data.load(JSON.parse(JSON.stringify(PAYLOAD)));
  vm.runInContext(fs.readFileSync(path.join(ROOT, "src/js/tech.js"), "utf8"), ctx, { filename: "tech.js" });
  return env;
}
// Engenharia as in the owner's capture: columns 1-3 done, part of 4-6 (marking the last tech of a column implies
// every tech before it)
function engineeringAt12(G) {
  const TK = G.tech, bid = TK.branches()[0].id, cols = TK.columns(bid);
  const mark = {};
  for (const g of cols.slice(0, 3)) for (const t of g.techs) mark[t.id] = true;
  return { TK, bid, cols, mark };
}

await test("Tecnologias: only the next column opens by default (columns 1-3 done, 4 has techs left)", () => {
  const { GK: G } = techEnv();
  const { TK, bid, cols, mark } = engineeringAt12(G);
  check(cols.length >= 6, "Engenharia has many columns (" + cols.length + ")");
  eq(cols.map((g) => g.column), [...cols.map((g) => g.column)].sort((a, b) => a - b), "columns in order");
  eq(TK.nextColumn(bid, new Set()), cols[0].column, "nothing researched: column 1 is the next one");
  const done = TK.researchedSet(mark);
  const nxt = TK.nextColumn(bid, done);
  eq(nxt, cols[3].column, "columns 1-3 done: column 4 is the next one");
  const open = cols.filter((g) => TK.columnOpen(g.column, nxt, {})).map((g) => g.column);
  eq(open, [cols[3].column], "only column 4 starts open (done ones and later ones folded)");
  // everything researched: no column opens
  const all = {}; for (const t of TK.inBranch(bid)) all[t.id] = true;
  eq(TK.nextColumn(bid, TK.researchedSet(all)), null, "whole branch researched: no next column");
  check(cols.every((g) => !TK.columnOpen(g.column, null, {})), "…and every column starts folded");
  // implied research counts: marking a column-4 tech implies its parents
  const c4 = cols[3].techs[0];
  check(TK.researchedSet({ [c4.id]: true }).has(c4.parents[0] || c4.id), "a marked tech implies its parents");
  // the player's choice wins over the rule, in both directions
  const choice = { [cols[1].column]: true, [nxt]: false };
  eq(cols.filter((g) => TK.columnOpen(g.column, nxt, choice)).map((g) => g.column), [cols[1].column], "choice: 2 opened, 4 folded by hand");
});

await test("Tecnologias: the opened / folded columns are kept per branch (ui.techCols, per device, cleaned, not synced)", async () => {
  const env = techEnv(), G = env.GK, S = G.store, A = S.actions;
  const b0 = G.tech.branches()[0].id, b1 = G.tech.branches()[1].id;
  eq(S.get().ui.techCols, {}, "fresh: no choice");
  A.setTechCol(b0, 2, true); A.setTechCol(b0, 4, false); A.setTechCol(b1, 1, true);
  eq(S.get().ui.techCols, { [b0]: { 2: true, 4: false }, [b1]: { 1: true } }, "kept per branch");
  A.setTechCol(b1, 1, null);
  eq(S.get().ui.techCols, { [b0]: { 2: true, 4: false } }, "null forgets the choice (and the empty branch)");
  A.setTechCol("bad id!", 2, true); A.setTechCol(b0, 0, true); A.setTechCol(b0, "x", true); A.setTechCol(b0, 100, true);
  eq(S.get().ui.techCols, { [b0]: { 2: true, 4: false } }, "bad branch / column ignored");
  await env.clock.tick(500);
  const saved = JSON.parse(env.localStorage.getItem("gk2-companion"));
  eq(saved.ui.techCols, { [b0]: { 2: true, 4: false } }, "saved on this device");
  // a reload keeps it; junk in a saved copy is dropped
  saved.ui.techCols[b0]["7"] = "yes"; saved.ui.techCols["<x>"] = { 1: true }; saved.ui.techCols[b1] = [true];
  saved.ui.tnCollapsed = 1;
  const env2 = techEnv();
  env2.localStorage.setItem("gk2-companion", JSON.stringify(saved));
  check(env2.GK.store.load(), "reloaded");
  eq(env2.GK.store.get().ui.techCols, { [b0]: { 2: true, 4: false } }, "reload: kept, junk dropped");
  eq(env2.GK.store.get().ui.tnCollapsed, true, "\"Tecnologias que faltam\" folded is kept too");
  // the account doc never carries ui (per device)
  check(!("ui" in env2.GK.store.syncPayload(env2.GK.store.get())) && env2.GK.store.SYNCED.indexOf("ui") < 0, "not synced");
});

await test("Tecnologias tab (ui/tech.js): headers fold, the next column stays put while ticking, ✓ on done columns", async () => {
  const env = techEnv(), G = env.GK, ctx = env.ctx;
  const { TK, bid, cols, mark } = engineeringAt12(G);
  const fake = () => {
    const kids = {}, ls = {};
    return { hidden: false, innerHTML: "", value: "", ls, querySelector: (q) => (kids[q] = kids[q] || fake()), querySelectorAll: () => [],
      addEventListener: (t, f) => { (ls[t] = ls[t] || []).push(f); }, focus() {}, setAttribute() {}, scrollIntoView() {}, getBoundingClientRect: () => ({ top: 0 }) };
  };
  ctx.CSS = { escape: (x) => x }; ctx.location = { hash: "tech" }; ctx.scrollTo = () => {}; ctx.scrollY = 0;
  ctx.getComputedStyle = () => ({ getPropertyValue: () => "" });
  G.router = { current: () => "tech", tab: () => ({ screen: "tech" }), register() {}, onChange() {}, detailHistory: () => ({ push() {}, pop() {} }) };
  G.app = { registerPanel() {} };
  G.ui.toast = () => {};
  vm.runInContext(fs.readFileSync(path.join(ROOT, "src/js/ui/tech.js"), "utf8"), ctx, { filename: "ui/tech.js" });
  const T = G.ui.tech, root = fake(), S = G.store;
  T.mount(root);
  S.update((s) => { s.researched = Object.assign({}, mark); }, { from: "tech" });
  const draw = (meta) => { T.render(S.get(), meta || {}); return root.innerHTML; };
  const heads = (h) => [...h.matchAll(/<button type="button" class="tc-btn" id="tcol-[^"]+-(\d+)" data-tcol="\d+" aria-expanded="(true|false)" aria-controls="([^"]+)" aria-label="([^"]+)">(.*?)<\/button>/g)]
    .map((m) => ({ col: +m[1], open: m[2] === "true", ctl: m[3], label: m[4], inner: m[5] }));
  let h = draw({ from: "router" }), hs = heads(h);
  eq(hs.length, cols.length, "one header button per column");
  eq(hs.filter((x) => x.open).map((x) => x.col), [cols[3].column], "only column 4 open");
  check(hs.slice(0, 3).every((x) => /class="tc-ok"/.test(x.inner)) && !hs.slice(3).some((x) => /class="tc-ok"/.test(x.inner)), "✓ only on the done columns");
  check(/aria-label="Expandir: Coluna 1, 1 de 1 pesquisadas"|aria-label="Expandir: Coluna 1, \d+ de \d+ pesquisadas"/.test(h), "label: Expandir: Coluna 1, n de n pesquisadas");
  check(/<span class="tc-t">Coluna 4<\/span><span class="tc-chev" aria-hidden="true"><\/span><span class="tc-r"><span class="count">/.test(h), "the chevron right after the title, the count after it");
  check(new RegExp(`<div class="card list" id="${hs[3].ctl}">`).test(h) && new RegExp(`<div id="${hs[0].ctl}" hidden></div>`).test(h), "aria-controls points at the rows (folded: empty and hidden)");
  // ticking every tech of column 4 does not fold it under the finger (the next column is kept for this visit)
  S.update((s) => { for (const t of cols[3].techs) s.researched[t.id] = true; }, { from: "tech" });
  hs = heads(draw());
  eq(hs.filter((x) => x.open).map((x) => x.col), [cols[3].column], "column 4 done while on the screen: still open");
  check(/class="tc-ok"/.test(hs[3].inner), "…with its ✓");
  // the next visit opens the new next column
  hs = heads(draw({ from: "router" }));
  eq(hs.filter((x) => x.open).map((x) => x.col), [cols[4].column], "next visit: column 5 open, 4 folded");
  // a tap on a header: the choice is kept (and wins over the rule)
  const click = (sel, data) => root.ls.click.forEach((f) => f({ target: { closest: (q) => (q === sel ? { dataset: data } : null) } }));
  click("[data-tcol]", { tcol: String(cols[1].column) });
  click("[data-tcol]", { tcol: String(cols[4].column) });
  eq(S.get().ui.techCols, { [bid]: { [cols[1].column]: true, [cols[4].column]: false } }, "taps saved per branch");
  hs = heads(draw({ from: "router" }));
  eq(hs.filter((x) => x.open).map((x) => x.col), [cols[1].column], "after a new visit: column 2 open (by hand), 5 folded (by hand)");
  // opening a tech of a folded column opens that column (the list comes back to its row)
  const t7 = cols[6].techs[0];
  T.open(t7.id);
  eq(S.get().ui.techCols[bid][cols[6].column], true, "open(id): its column opens");
  // a search lists its hits whatever is folded
  const q = G.i18n.name(cols[0].techs[0]);
  root.ls.input.forEach((f) => f({ target: { id: "tech-q", value: q } }));
  await env.clock.tick(200);
  h = root.querySelector("#tech-list").innerHTML;
  check(h.includes('class="hint tech-results"') && !h.includes("data-tcol") && h.includes(`data-open="${cols[0].techs[0].id}"`), "search: hits listed from a folded column, no fold headers");
});

// ---------------------------------------------------------------- done
console.log(`\n${passed} checks passed, ${failed} failed`);
if (failed) { console.log("\n" + failures.map((f) => "  - " + f).join("\n")); process.exit(1); }
