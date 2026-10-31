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
  const q = plan([{ item: "wine", qty: 5 }], { choice: { wine: "drink-enhancement-i-from-wine-bronze" } });
  eq(q.refused, ["wine"], "refused");
  const w = q.raw.find((x) => x.item === "wine");
  check(w && w.reason === "refused" && w.qty === 5, "wine becomes a raw material");
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
  check(g.in.some((i) => i.item === "pumpkin-gold" && i.baseItem === "pumpkin"), "gold recipe uses pumpkin-gold");
  check(b.in.some((i) => i.item === "pumpkin"), "bronze recipe keeps the plain pumpkin");
  const v = D.items["pumpkin-gold"];
  check(v && v.synthetic && v.kind === "quality-variant" && v.pt === "Abóbora (ouro)", "synthetic variant named in pt");
  check(D.recipeById["wine-from-grape-juice-gold"].in[0].item === "grape-juice-gold", "real variants untouched");
  check(D.recipeById["grape-juice-from-grapes-gold"].in.some((i) => i.item === "grapes"), "output carries the grade: input untouched");
  check(D.recipeById["drink-enhancement-ii-from-wine-silver"].in.some((i) => i.item === "wine"), "self-upgrade untouched");
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
  eq(r.goals, [{ item: "crate", qty: 999 }], "goals cleaned and clamped");
  eq(r.have, { a: true, b: 3, c: 3, h: 999999 }, "have: true or a whole number ≥ 1");
  eq([r.choice, r.done, r.researched], [{ a: "r1" }, { "raw:x": true }, { t1: true }], "maps");
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
  const m = GK.store.mergeSynced(L, R);
  eq(m.goals, L.goals, "goals: local");
  eq(m.choice, { b: "L", c: "R", a: "L" }, "choice: union, local wins");
  eq(m.overrides, { pt: { b: "Lb", a: "La" }, en: { c: "Rc" } }, "overrides: union, local wins");
  eq(m.have, { x: 5, y: true, z: true }, "have: union, remote wins");
  eq(m.done, { "raw:l": true, "raw:c": true, "raw:r": true }, "done: union");
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

// ---------------------------------------------------------------- done
console.log(`\n${passed} checks passed, ${failed} failed`);
if (failed) { console.log("\n" + failures.map((f) => "  - " + f).join("\n")); process.exit(1); }
