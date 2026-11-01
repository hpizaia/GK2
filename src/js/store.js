/* GK.store: the single serializable app state, persistence in localStorage and schema migrations.
   Owns: state {schemaVersion, lang, theme, lists, listsGone, goals, choice, have, done, example, legacyOf, overrides,
   showHidden, researched, studied, groupChoice, perks, day, dayNumber, dayAnchor, dayDone, dayNotes, recents, ui, updatedAt, syncBase}.
   Lists (schema 5, "listas separadas"): state.lists = [{id, name, createdAt, updatedAt, goals, choice, have, done,
   example}] holds every plan; ui.activeList (per device, never synced) says which one is open. The top-level goals /
   choice / have / done / example are the WORKING COPY of the open list: every module reads and edits them exactly as
   before schema 5, and update() writes them back into that list after every change (stamping the list's updatedAt).
   legacyOf = the id of the list the working copy belongs to; written with it, so a page older than schema 5 that
   saved its single plan on top (localStorage or the account doc) is folded back into that list (sanitizeRemote).
   Global (shared by every list): overrides, researched, studied, groupChoice, perks, the day fields, recents, theme, lang, ui.
   Exposes: GK.store.{get, load, subscribe, actions, update, clampQty, SCHEMA, THEMES, ISO, SYNCED, PER_LIST, MIRROR,
   syncPayload, syncKey, legacyMirror, sanitizeRemote, hasContent, mergeSynced, stamp, useAccount, setSyncBase, storageKey,
   activeList, LIST_NAME_MAX, LISTS_MAX, RECENTS_MAX, DAY_IDS, dayOrder, dayFromNumber, doneToday, NOTE_MAX, LATE, keepLate, adoptLate}.
   Every change goes through an action (or update(fn, meta) for module-owned fields); subscribers get (state, meta).
   localStorage: "gk2-companion" (no account) or "gk2-companion:<user id>" once GK.sync knows the account
   (useAccount); the anonymous copy moves into the first account that opens it, once, and is then removed, so a
   shared browser never hands one account's plan to another. "gk2-companion.account" remembers the last account
   so the next visit renders its plan before the account resolves.
*/
GK.store = (function () {
  const KEY = "gk2-companion", LAST = "gk2-companion.account";
  let key = KEY;
  const SCHEMA = 5;
  const THEMES = ["auto", "light", "dark"];
  const ISO = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z$/;
  const EPOCH = "1970-01-01T00:00:00.000Z";
  // Fields that travel to the viewer's account (GK.sync). lang, theme, showHidden and ui (with the open list) stay per
  // device. Schema 5: the plan fields live in `lists` (listsGone = {listId: ISO time} of deleted lists, so a merge
  // does not bring them back).
  const SYNCED = ["lists", "listsGone", "overrides", "researched", "studied", "groupChoice", "perks", "day", "dayNumber", "dayAnchor", "dayDone", "dayNotes", "recents"];
  // what each list holds (= the schema ≤ 4 top-level plan fields, still the working copy of the open list)
  const PER_LIST = ["goals", "choice", "have", "done", "example"];
  // written next to SYNCED in the account doc (GK.sync, legacyMirror): the open list, flat, for a page older than
  // schema 5 still open on another device; never kept as an unknown field
  const MIRROR = PER_LIST.concat(["legacyOf"]);
  const MAIN = "main";                       // id of the list a schema ≤ 4 plan becomes (same on every device)
  const LIST_NAME_MAX = 30, LISTS_MAX = 30, GONE_MAX = 100;
  // synced fields added after schema 4 (1.3.4, optional, no migration): a doc written by an older page has no such
  // key at all, which GK.sync must not read as "cleared" (keepLate / adoptLate below)
  const LATE = ["dayDone", "dayNotes", "recents", "studied"];
  // "Recentes" (ui/search.js): the items last added to goals, newest first, at most RECENTS_MAX ids (the search shows
  // the first 6). Global and synced. Only ids of items the page knows (when its data is loaded), no duplicates.
  const RECENTS_MAX = 12;
  function cleanRecents(a) {
    const its = GK.data && GK.data.get && GK.data.get().items, known = its && Object.keys(its).length ? (id) => !!its[id] : () => true;
    const out = [];
    for (const id of Array.isArray(a) ? a : []) {
      if (typeof id === "string" && id && id.length <= 200 && known(id) && out.indexOf(id) < 0) out.push(id);
      if (out.length >= RECENTS_MAX) break;
    }
    return out;
  }
  const pushRecent = (s, id) => { s.recents = cleanRecents([id].concat(Array.isArray(s.recents) ? s.recents : [])); };
  // "Já estudei" (item card in Receitas): ids of the items studied at the Study Table, sorted, no duplicates.
  // Global and synced. Only ids of items the page knows (when its data is loaded). Merge: union.
  const STUDIED_MAX = 2000;
  function cleanStudied(a) {
    const its = GK.data && GK.data.get && GK.data.get().items, known = its && Object.keys(its).length ? (id) => !!its[id] : () => true;
    const out = new Set();
    for (const id of Array.isArray(a) ? a : []) {
      if (typeof id === "string" && id && id.length <= 200 && known(id)) out.add(id);
      if (out.size >= STUDIED_MAX) break;
    }
    return Array.from(out).sort();
  }
  // The 6-day week (Dias tab): the cycle comes from the payload's `days` block (data/days.json: meta.order, else the
  // days in their `order`) when the page has one; DAY_IDS is the fallback cycle (its first six) and the whitelist
  // (any of the seven sins, so a week that swaps one sin for another still validates).
  const DAY_IDS = ["gluttony", "sloth", "lust", "envy", "pride", "wrath", "greed"];
  function dayOrder() {
    const D = GK.data && GK.data.get && GK.data.get(), W = D && D.days;
    const ok = (a) => (Array.isArray(a) ? a.filter((id) => typeof id === "string" && id) : []);
    let list = W && W.meta ? ok(W.meta.order) : [];
    if (!list.length && W && Array.isArray(W.days)) list = ok(W.days.slice().sort((a, b) => ((a && a.order) || 0) - ((b && b.order) || 0)).map((d) => d && d.id));
    return list.length ? list : DAY_IDS.slice(0, 6);
  }
  const validDay = (id) => typeof id === "string" && (DAY_IDS.indexOf(id) >= 0 || dayOrder().indexOf(id) >= 0) ? id : null;
  // the HUD day counter: a whole number 1..99999, else null
  const clampDayNumber = (v) => { const n = typeof v === "string" && v.trim() ? +v : v; return typeof n === "number" && isFinite(n) && n >= 1 ? Math.min(99999, Math.round(n)) : null; };
  // calibration: {number, day} = "HUD day <number> was <day>" (set when the player gives both); null = not calibrated
  const cleanAnchor = (a) => { const n = a && clampDayNumber(a.number), d = a && validDay(a.day); return n != null && d ? { number: n, day: d } : null; };
  // "Feito hoje" (planner panel Hoje): {day, number, ids} = the event indexes (in data/days.json order) ticked on that
  // day. It only counts while it is still that day: same weekday and, when both sides have a counter, the same HUD
  // number (a week later is another day); a tick made before the counter was given adopts it. Else null (= reset).
  function cleanDone(o, day, num) {
    if (!o || typeof o !== "object" || Array.isArray(o) || !day || validDay(o.day) !== day) return null;
    const n = clampDayNumber(o.number);
    if (n != null && num != null && n !== num) return null;
    const ids = Array.from(new Set((Array.isArray(o.ids) ? o.ids : []).filter((i) => Number.isInteger(i) && i >= 0 && i < 100))).sort((a, b) => a - b);
    return ids.length ? { day, number: n != null ? n : num, ids } : null;
  }
  // "Bilhete do dia": one short note per weekday, one line (whitespace collapsed), at most NOTE_MAX characters
  const NOTE_MAX = 200;
  const cleanNote = (v) => (typeof v === "string" ? v.replace(/\s+/g, " ").trim().slice(0, NOTE_MAX).trim() : "");
  function cleanNotes(o) {
    const out = {};
    if (!o || typeof o !== "object" || Array.isArray(o)) return out;
    for (const [k, v] of Object.entries(o)) { const s = validDay(k) && cleanNote(v); if (s) out[k] = s; }
    return out;
  }
  // weekday of HUD day n from an anchor: order[(anchorIdx + (n - anchor.number)) mod 6]; null when it cannot tell
  function dayFromNumber(n, anchor) {
    const a = cleanAnchor(anchor), num = clampDayNumber(n), order = dayOrder();
    const i = a ? order.indexOf(a.day) : -1;
    if (i < 0 || num == null) return null;
    const L = order.length;
    return order[(((i + num - a.number) % L) + L) % L];
  }
  // ui: which planner panels are collapsed. stationCollapsed keys come from ui/summary.js ("<station id>[#repeat]").
  // "Hoje" starts folded (one line) until the player opens it (1.3.4); editNames = the ✎ rename pencils are shown
  // (a contributor mode, off by default).
  const UI_FLAGS = ["todayCollapsed", "stepsCollapsed", "rawCollapsed", "editNames", "bigText"]; // bigText = "Letra grande" (ui/footer.js, GK.theme.big; absent = off)
  // activeList (schema 5): id of the list open on this device (null = the first one); per device, never synced
  const freshUi = () => ({ todayCollapsed: true, stepsCollapsed: false, rawCollapsed: false, editNames: false, stationCollapsed: {}, activeList: null });
  const validId = (v) => typeof v === "string" && /^[A-Za-z0-9_-]{1,40}$/.test(v);
  function cleanUi(o) {
    const u = freshUi(), src = o && typeof o === "object" && !Array.isArray(o) ? o : {};
    for (const k of UI_FLAGS) if (k in src) u[k] = !!src[k];
    if (validId(src.activeList)) u.activeList = src.activeList;
    const m = src.stationCollapsed && typeof src.stationCollapsed === "object" && !Array.isArray(src.stationCollapsed) ? src.stationCollapsed : {};
    for (const [k, v] of Object.entries(m)) if (v && k && k.length <= 200) u.stationCollapsed[k] = true;
    return u;
  }
  const EMPTY_LIST = () => ({ goals: [], choice: {}, have: {}, done: {}, example: false });
  // the first list of a fresh device or of a schema ≤ 4 plan: name "" = shown as "Minha lista" / "My list"
  const defaultList = () => Object.assign({ id: MAIN, name: "", createdAt: EPOCH, updatedAt: EPOCH }, EMPTY_LIST());
  const fresh = () => ({
    schemaVersion: SCHEMA,
    lang: null,          // "pt" | "en" | null (auto)
    theme: "auto",       // "auto" (system / host decides) | "light" | "dark"   (added in schema 3)
    lists: [defaultList()], // [{id, name, createdAt, updatedAt, goals, choice, have, done, example}] (schema 5, synced)
    listsGone: {},       // listId -> ISO time it was deleted (schema 5, synced; at most GONE_MAX)
    // working copy of the open list (ui.activeList); written back into it by update():
    goals: [],           // [{ item, qty }]
    choice: {},          // itemId -> recipeId (absent = item.defaultRecipe)
    have: {},            // itemId -> true ("Já tenho": don't expand) | number ("tenho N de M": N subtracted from demand)
    done: {},            // "raw:<id>" | "step:<id>" -> true
    example: false,      // goals are the seeded example
    legacyOf: MAIN,      // the list the working copy belongs to
    overrides: {},       // lang -> { itemId: "nome editado" }
    showHidden: false,   // search also lists hidden / unobtainable / virtual items
    researched: {},      // techId -> true ("Já pesquisei", Tecnologias tab; schema 4, synced)
    studied: [],         // [itemId] sorted: "Já estudei" on the item card (Receitas; synced)
    groupChoice: {},     // groupItemId -> memberItemId ("Brema ou carpa" → "Usar: Carpa"; synced)
    perks: {},           // perkId -> true (yield bonuses from recipe notes, "Vantagens"; synced)
    day: null,           // current weekday id as set by the player ("wrath"; Dias tab, synced)
    dayNumber: null,     // the HUD day counter (e.g. 60), optional; null = not given (synced)
    dayAnchor: null,     // {number, day}: calibration "HUD day N was <day>"; a counter alone then gives the day (synced)
    dayDone: null,       // {day, number, ids: [event index]}: "Feito hoje" ticks; reset when the day changes (synced, 1.3.4)
    dayNotes: {},        // dayId -> "levar 3 peixes para o Pescador": "Bilhete do dia", ≤ NOTE_MAX chars (synced, 1.3.4)
    recents: [],         // [itemId]: last added to goals, newest first, ≤ RECENTS_MAX ("Recentes" in the search; synced)
    ui: freshUi(),       // planner panels the player collapsed + the rename mode (per device, never synced; 1.3.1)
    updatedAt: "",       // ISO time of the last change to a SYNCED field ("" = never touched; schema 4)
    syncBase: "",        // updatedAt of the last version both this device and the account held (GK.sync; local)
  });
  let state = fresh();
  const subs = [];
  let timer = null;
  const clampQty = (q) => Math.min(999, Math.max(1, Math.round(+q) || 1));
  const obj = (v) => (v && typeof v === "object" && !Array.isArray(v) ? v : {});
  const LANG_CODES = () => GK.i18n.LANGS.map((l) => l.code);

  // v1 overrides were itemId -> {pt: "..."}; v2 is lang -> {itemId: "..."}
  function migrateOverrides(o, fromV1) {
    const out = {};
    for (const [k, v] of Object.entries(obj(o))) {
      if (fromV1) {
        for (const [l, s] of Object.entries(obj(v))) if (typeof s === "string" && s.trim()) (out[l] = out[l] || {})[k] = s.trim();
      } else if (LANG_CODES().indexOf(k) >= 0) {
        for (const [id, s] of Object.entries(obj(v))) if (typeof s === "string" && s.trim()) (out[k] = out[k] || {})[id] = s.trim();
      }
    }
    return out;
  }
  const nonEmpty = (o) => !!o && Object.keys(o).length > 0;
  // something the user made: in any list (schema 5) or in the flat plan of an older copy
  const listHas = (l) => !!l && ((!l.example && Array.isArray(l.goals) && l.goals.length > 0) || nonEmpty(l.done) || nonEmpty(l.have) || nonEmpty(l.choice));
  const hasContent = (s) => (Array.isArray(s.lists) ? s.lists.length > 1 || s.lists.some(listHas) : listHas(s)) ||
    nonEmpty(s.overrides) || nonEmpty(s.researched) || (Array.isArray(s.studied) && s.studied.length > 0) || nonEmpty(s.groupChoice) || nonEmpty(s.perks) || !!s.day || !!s.dayAnchor || nonEmpty(s.dayNotes);
  const trueMap = (o) => { const out = {}; for (const [k, v] of Object.entries(obj(o))) if (v) out[k] = true; return out; };
  // have: true (everything) or a whole number ≥ 1 (partial); anything else is dropped
  const clampHave = (v) => (v === true ? true : typeof v === "number" && isFinite(v) && v >= 1 ? Math.min(999999, Math.round(v)) : null);
  const haveMap = (o) => { const out = {}; for (const [k, v] of Object.entries(obj(o))) { const c = clampHave(v); if (c != null) out[k] = c; } return out; };
  const strMap = (o) => { const out = {}; for (const [k, v] of Object.entries(obj(o))) if (typeof v === "string" && v) out[k] = v; return out; };
  const cleanGoals = (g) => (Array.isArray(g) ? g : []).filter((x) => x && typeof x.item === "string").slice(0, 500)
    .map((x) => ({ item: x.item, qty: clampQty(x.qty) }));
  // the synced part of a state, as plain data (also the body of the account doc)
  function syncPayload(s) {
    const out = {};
    for (const k of SYNCED) out[k] = s[k];
    return out;
  }
  const syncKey = (s) => JSON.stringify(syncPayload(s));
  // the open list, flat (MIRROR), for the account doc: what a page older than schema 5 reads as its plan
  function legacyMirror(s) {
    const out = {};
    for (const k of PER_LIST) out[k] = s[k];
    out.legacyOf = s.legacyOf;
    return out;
  }
  // ---- lists (schema 5)
  // a list name: one line, at most LIST_NAME_MAX characters ("" = the default name, shown translated)
  const cleanName = (v) => (typeof v === "string" ? Array.from(v.replace(/\s+/g, " ").trim()).slice(0, LIST_NAME_MAX).join("").trim() : "");
  const isoOr = (v, d) => (typeof v === "string" && ISO.test(v) ? v : d);
  const listContent = (o) => ({ goals: cleanGoals(o.goals), choice: strMap(o.choice), have: haveMap(o.have), done: trueMap(o.done), example: !!o.example });
  const contentKey = (l) => JSON.stringify([l.goals, l.choice, l.have, l.done, !!l.example]);
  function cleanList(o) {
    if (!o || typeof o !== "object" || Array.isArray(o) || !validId(o.id)) return null;
    return Object.assign({ id: o.id, name: cleanName(o.name), createdAt: isoOr(o.createdAt, EPOCH), updatedAt: isoOr(o.updatedAt, EPOCH) }, listContent(o));
  }
  // creation order (the main list, created at EPOCH, first), id on a tie: the same order on every device
  const byCreated = (a, b) => (a.createdAt < b.createdAt ? -1 : a.createdAt > b.createdAt ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  function cleanLists(a) {
    const seen = new Set(), out = [];
    for (const x of Array.isArray(a) ? a : []) {
      const l = cleanList(x);
      if (l && !seen.has(l.id) && out.length < LISTS_MAX) { seen.add(l.id); out.push(l); }
    }
    return out.sort(byCreated);
  }
  function cleanGone(o) {
    const e = Object.entries(obj(o)).filter(([k, v]) => validId(k) && typeof v === "string" && ISO.test(v));
    e.sort((a, b) => (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0));
    return Object.fromEntries(e.slice(0, GONE_MAX));
  }
  const hasLegacy = (o) => PER_LIST.some((k) => has(o, k));
  /**
   * Untrusted input (the account doc, or a local copy): rebuild every synced field from scratch, or null.
   * at = the doc's updatedAt (the time of its flat plan). Older copies:
   *   - no `lists` (schema ≤ 4)          its goals / choice / have / done / example become the list MAIN ("Minha lista")
   *   - `lists` + a flat plan that differs from the list named by legacyOf: a page older than schema 5 edited it
   *                                      on top of a schema 5 copy, so that list takes it (dated at, or just after)
   */
  function sanitizeRemote(o, fromV1, at) {
    if (!o || typeof o !== "object" || Array.isArray(o)) return null;
    const day = validDay(o.day), dayNumber = clampDayNumber(o.dayNumber), when = isoOr(at, EPOCH);
    const gone = cleanGone(o.listsGone);
    let lists = cleanLists(o.lists);
    if (!Array.isArray(o.lists)) {
      if (hasLegacy(o)) lists = [Object.assign({ id: MAIN, name: "", createdAt: EPOCH, updatedAt: when }, listContent(o))];
    } else if (hasLegacy(o) && validId(o.legacyOf)) {
      const i = lists.findIndex((l) => l.id === o.legacyOf), flat = listContent(o);
      if (i >= 0 && contentKey(flat) !== contentKey(lists[i])) {
        const prev = lists[i].updatedAt;
        lists[i] = Object.assign({}, lists[i], flat, { updatedAt: when > prev ? when : stamp(prev) });
      }
    }
    lists = lists.filter((l) => !(gone[l.id] && gone[l.id] >= l.updatedAt));
    return {
      lists, listsGone: gone,
      overrides: migrateOverrides(o.overrides, !!fromV1),
      researched: trueMap(o.researched), studied: cleanStudied(o.studied), groupChoice: strMap(o.groupChoice), perks: trueMap(o.perks),
      day, dayNumber, dayAnchor: cleanAnchor(o.dayAnchor),
      dayDone: cleanDone(o.dayDone, day, dayNumber), dayNotes: cleanNotes(o.dayNotes),
      recents: cleanRecents(o.recents),
    };
  }
  // the open list of a state (ui.activeList, else the first)
  function activeList(s) {
    const ls = s && Array.isArray(s.lists) ? s.lists : [];
    const id = s && s.ui && s.ui.activeList;
    return ls.find((l) => l.id === id) || ls[0] || null;
  }
  function ensureLists(s) {
    if (!Array.isArray(s.lists) || !s.lists.length) s.lists = [defaultList()];
    s.listsGone = obj(s.listsGone);
  }
  // open the active list: copy it into the working fields
  function loadActive(s) {
    ensureLists(s);
    const l = activeList(s);
    s.ui = s.ui && typeof s.ui === "object" && !Array.isArray(s.ui) ? s.ui : freshUi();
    s.ui.activeList = l.id;
    const c = JSON.parse(JSON.stringify({ goals: l.goals, choice: l.choice, have: l.have, done: l.done }));
    s.goals = c.goals; s.choice = c.choice; s.have = c.have; s.done = c.done; s.example = !!l.example;
    s.legacyOf = l.id;
  }
  // write the working fields back into their list (legacyOf); a real change stamps the list unless stampIt is false
  function commit(s, stampIt) {
    const l = Array.isArray(s.lists) && s.lists.find((x) => x.id === s.legacyOf);
    if (!l) return;
    const c = { goals: (s.goals || []).map((g) => ({ item: g.item, qty: g.qty })), choice: Object.assign({}, s.choice),
      have: Object.assign({}, s.have), done: Object.assign({}, s.done), example: !!s.example };
    if (contentKey(c) === contentKey(l)) return;
    Object.assign(l, c);
    if (stampIt) l.updatedAt = stamp(l.updatedAt);
  }
  // the event indexes ticked "feito hoje" for the state's current day ([] when none / another day)
  const doneToday = (s) => { const d = s && cleanDone(s.dayDone, validDay(s.day), s.dayNumber); return d ? d.ids : []; };
  const has = (o, k) => !!o && typeof o === "object" && Object.prototype.hasOwnProperty.call(o, k);
  /**
   * The account doc wins (GK.sync), but it was written by a page older than LATE (no dayDone / dayNotes key at all)
   * while this device has some: keep ours for those fields. raw = the doc's unsanitized `state`, fields = its
   * sanitized copy, local = our synced payload. Returns the fields to apply (then pushed, with a new stamp) or null.
   */
  function keepLate(fields, raw, local) {
    const out = Object.assign({}, fields);
    let kept = false;
    if (!has(raw, "dayNotes") && nonEmpty(cleanNotes(local.dayNotes))) { out.dayNotes = cleanNotes(local.dayNotes); kept = true; }
    if (!has(raw, "dayDone")) { const dd = cleanDone(local.dayDone, out.day, out.dayNumber); if (dd) { out.dayDone = dd; kept = true; } }
    if (!has(raw, "recents") && cleanRecents(local.recents).length) { out.recents = cleanRecents(local.recents); kept = true; }
    if (!has(raw, "studied") && cleanStudied(local.studied).length) { out.studied = cleanStudied(local.studied); kept = true; }
    return kept ? out : null;
  }
  /**
   * Same version on both sides, but the doc carries LATE fields this copy lacks (an older page kept them in the doc
   * as unknown fields without ever loading them): adopt them. Returns the payload to apply (same stamp) or null.
   */
  function adoptLate(fields, local) {
    const out = Object.assign({}, local);
    let got = false;
    if (!nonEmpty(cleanNotes(local.dayNotes)) && nonEmpty(fields.dayNotes)) { out.dayNotes = fields.dayNotes; got = true; }
    if (!cleanDone(local.dayDone, validDay(local.day), local.dayNumber)) {
      const dd = cleanDone(fields.dayDone, validDay(local.day), local.dayNumber);
      if (dd) { out.dayDone = dd; got = true; }
    }
    if (!cleanRecents(local.recents).length && fields.recents && fields.recents.length) { out.recents = cleanRecents(fields.recents); got = true; }
    if (!cleanStudied(local.studied).length && fields.studied && fields.studied.length) { out.studied = cleanStudied(fields.studied); got = true; }
    return got ? out : null;
  }
  /**
   * Merge rule (GK.sync), used only when BOTH this device and the account changed since the last version they
   * shared (base = syncBase); otherwise the newer copy simply wins (last writer wins on the whole document):
   *   lists                   by id, union; a list deleted on either side (listsGone, union, newest time) stays
   *                           deleted unless it changed after that. A list on both sides: the one that changed since
   *                           base wins as a whole; when both changed (or there is no base), its fields merge like
   *                           the schema 4 plan did: goals, example local; choice union, local wins; have, done
   *                           union, remote wins; name (and updatedAt) from the newer copy
   *   overrides               union by key, local wins on a conflict
   *   researched, perks, groupChoice
   *                           union by key, remote wins on a conflict
   *   studied                 union of the ids (an item unchecked on one side comes back from the other's copy)
   *   day + dayNumber         one pair: the copy with the higher day counter (the game only moves forward), else
   *                           the local one when it has a day, else the remote one
   *   dayAnchor               local when it has one, else remote
   *   dayDone                 the ticks of the copies that are still on the merged day (above), by union
   *   dayNotes                union by weekday; on a conflict the copy with the newer updatedAt wins
   *                           (remoteNewer = true: the account's), else the local one
   *   recents                 union, newest first: the ids of the copy with the newer updatedAt (remoteNewer), then
   *                           the other copy's that are missing, in their order; capped at RECENTS_MAX
   * A key deleted on one side can come back from the other side's copy (union): acceptable for checkmarks.
   * Both inputs are sanitized synced payloads; the result is one too.
   */
  function mergeList(l, r, base) {
    if (JSON.stringify(l) === JSON.stringify(r)) return l;
    const lc = !base || l.updatedAt > base, rc = !base || r.updatedAt > base;
    if (base && lc && !rc) return l;
    if (base && rc && !lc) return r;
    if (base && !lc && !rc) return r.updatedAt > l.updatedAt ? r : l;
    const newer = r.updatedAt > l.updatedAt ? r : l;
    return {
      id: l.id, name: newer.name, createdAt: l.createdAt < r.createdAt ? l.createdAt : r.createdAt, updatedAt: newer.updatedAt,
      goals: l.goals, choice: Object.assign({}, r.choice, l.choice), have: Object.assign({}, l.have, r.have),
      done: Object.assign({}, l.done, r.done), example: l.example,
    };
  }
  function mergeLists(L, R, base) {
    const gone = Object.assign({}, L.listsGone);
    for (const [k, v] of Object.entries(R.listsGone)) if (!gone[k] || v > gone[k]) gone[k] = v;
    const byId = new Map();
    for (const l of L.lists) byId.set(l.id, l);
    for (const r of R.lists) byId.set(r.id, byId.has(r.id) ? mergeList(byId.get(r.id), r, base) : r);
    const lists = Array.from(byId.values()).filter((l) => !(gone[l.id] && gone[l.id] >= l.updatedAt)).sort(byCreated).slice(0, LISTS_MAX);
    return { lists, listsGone: cleanGone(gone) };
  }
  function mergeSynced(local, remote, remoteNewer, base) {
    const L = sanitizeRemote(local) || sanitizeRemote({}), R = sanitizeRemote(remote) || sanitizeRemote({});
    const ov = {};
    for (const lang of new Set(Object.keys(R.overrides).concat(Object.keys(L.overrides)))) ov[lang] = Object.assign({}, R.overrides[lang], L.overrides[lang]);
    const days = pickDay(L, R);
    const dl = cleanDone(L.dayDone, days.day, days.dayNumber), dr = cleanDone(R.dayDone, days.day, days.dayNumber);
    const dayDone = dl && dr ? cleanDone({ day: days.day, number: dl.number != null ? dl.number : dr.number, ids: dl.ids.concat(dr.ids) }, days.day, days.dayNumber) : dl || dr;
    return {
      ...mergeLists(L, R, typeof base === "string" ? base : ""),
      overrides: ov,
      researched: Object.assign({}, L.researched, R.researched), perks: Object.assign({}, L.perks, R.perks),
      studied: cleanStudied(L.studied.concat(R.studied)),
      groupChoice: Object.assign({}, L.groupChoice, R.groupChoice),
      ...days, dayDone,
      dayNotes: remoteNewer ? Object.assign({}, L.dayNotes, R.dayNotes) : Object.assign({}, R.dayNotes, L.dayNotes),
      recents: cleanRecents(remoteNewer ? R.recents.concat(L.recents) : L.recents.concat(R.recents)),
    };
  }
  function pickDay(L, R) {
    const useR = !L.day || (R.day && R.dayNumber != null && (L.dayNumber == null || R.dayNumber > L.dayNumber));
    const w = useR ? R : L;
    return { day: w.day, dayNumber: w.dayNumber, dayAnchor: L.dayAnchor || R.dayAnchor };
  }
  // ISO time strictly after prev (clock skew between devices can't make a change look older than the last one)
  function stamp(prev) {
    const now = new Date().toISOString();
    return prev && ISO.test(prev) && now <= prev ? new Date(Date.parse(prev) + 1).toISOString() : now;
  }
  function migrate(o) {
    if (!o || typeof o !== "object") return null;
    const s = fresh();
    s.lang = typeof o.lang === "string" ? o.lang : null;
    // schema ≤ 4: the flat plan becomes the list MAIN, dated with the copy's updatedAt (EPOCH when it has none)
    Object.assign(s, sanitizeRemote(o, (o.schemaVersion || 1) < 2, o.updatedAt));
    s.showHidden = !!o.showHidden;
    s.ui = cleanUi(o.ui);
    loadActive(s);
    s.theme = THEMES.indexOf(o.theme) >= 0 ? o.theme : "auto";   // v1/v2 had no theme
    // v1–v3 had no updatedAt: a plan the user built gets the oldest possible time, so it is pushed to an
    // empty account but never overwrites one that already has a plan
    s.updatedAt = typeof o.updatedAt === "string" && ISO.test(o.updatedAt) ? o.updatedAt : (hasContent(s) ? EPOCH : "");
    s.syncBase = typeof o.syncBase === "string" && ISO.test(o.syncBase) ? o.syncBase : "";
    // fields written by a newer version of the page stay in the local copy (they are not ours to drop)
    for (const k of Object.keys(o)) if (!(k in s) && !/^__/.test(k)) s[k] = o[k];
    return s;
  }
  const ls = () => { try { return window.localStorage; } catch (e) { return null; } };
  function read(k) {
    try { const st = ls(), raw = st && st.getItem(k); return raw ? migrate(JSON.parse(raw)) : null; } catch (e) { return null; }
  }
  function load() {
    try {
      const st = ls(), last = st && st.getItem(LAST);
      const acc = last ? read(KEY + ":" + last) : null;
      if (acc) { key = KEY + ":" + last; state = acc; return true; }
      key = KEY;
      const s = read(KEY);
      if (s) { state = s; return true; }
    } catch (e) { /* storage blocked or corrupt: run in memory */ }
    return false;
  }
  function persistNow() {
    clearTimeout(timer); timer = null;
    try { const st = ls(); if (st) st.setItem(key, JSON.stringify(state)); } catch (e) { /* ignore */ }
  }
  function persist() {
    clearTimeout(timer);
    timer = setTimeout(persistNow, 120);
  }
  if (typeof window !== "undefined" && window.addEventListener) {
    // a pending write must not be lost when the tab closes or goes to the background (AUDITORIA S6)
    window.addEventListener("pagehide", () => { if (timer) persistNow(); });
    if (typeof document !== "undefined" && document.addEventListener) {
      document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden" && timer) persistNow(); });
    }
  }
  const notify = (meta) => { for (const f of subs) f(state, meta || {}); };
  /**
   * GK.sync tells the store whose plan this is. id = the account's user id, or null (no account: this device only).
   * Switches the localStorage key; returns true when the state in memory changed (subscribers were notified).
   */
  function useAccount(id) {
    const want = id ? KEY + ":" + id : KEY;
    const st = ls();
    try { if (st && id) st.setItem(LAST, String(id)); } catch (e) { /* ignore */ }
    if (want === key) return false;
    if (timer) persistNow();                          // the current owner's last edits stay in its own key
    const prefs = { lang: state.lang, theme: state.theme, showHidden: state.showHidden, ui: state.ui };
    let next = read(want);
    if (!next && id && key === KEY) next = state;     // first account on this browser: adopt the anonymous plan once
    const fromAnon = !!(id && key === KEY && next === state);
    if (!next) next = fresh();                        // someone else's plan was showing: start clean
    state = Object.assign(next, prefs);
    ensureLists(state);
    if (GK.data && GK.data.item && GK.data.get().items) for (const l of state.lists) l.goals = l.goals.filter((g) => !!GK.data.item(g.item));
    loadActive(state);                                // the open list of this device, if this account has it
    key = want;
    persistNow();
    if (fromAnon) { try { st.removeItem(KEY); } catch (e) { /* ignore */ } }
    if (!fromAnon) notify({ from: "account" });
    return !fromAnon;
  }
  // GK.sync: remember the version both sides hold (no re-render, no stamp)
  function setSyncBase(at) {
    if (typeof at !== "string" || state.syncBase === at) return;
    state.syncBase = at;
    persist();
  }
  function update(fn, meta) {
    const before = syncKey(state), noStamp = !!(meta && meta.noStamp);
    fn(state);
    commit(state, !noStamp);                          // the working copy back into its list
    if (!noStamp && syncKey(state) !== before) state.updatedAt = stamp(state.updatedAt);
    persist();
    notify(meta);
  }
  const touchGoals = (s) => { s.example = false; };
  const fixDone = (s) => { s.dayDone = cleanDone(s.dayDone, validDay(s.day), s.dayNumber); };
  const actions = {
    // The first goal added to the seeded example REPLACES it (the example goals and their checks go away);
    // subscribers get meta.exampleReplaced = {goals, done} so the UI can offer "Desfazer" (restoreExample).
    // Changing a quantity or removing a goal keeps the example list and simply adopts it (touchGoals).
    addGoal(item, qty) {
      let now = 0, replaced = null;
      if (state.example && state.goals.length) replaced = { goals: state.goals.map((g) => ({ item: g.item, qty: g.qty })), done: Object.assign({}, state.done) };
      update((s) => {
        if (replaced) { s.goals = []; s.done = {}; }
        touchGoals(s);
        const g = s.goals.find((x) => x.item === item);
        if (g) { g.qty = clampQty(g.qty + (qty || 1)); now = g.qty; }
        else { s.goals.push({ item, qty: clampQty(qty || 1) }); now = clampQty(qty || 1); }
        pushRecent(s, item);                          // every goal added is a "Recente" (search, Receitas, …)
      }, replaced ? { from: "search", exampleReplaced: replaced } : { from: "search" });
      return now;
    },
    // "Recentes": put an item first (addGoal does it too); unknown ids are ignored
    addRecent(item) {
      if (typeof item !== "string" || !cleanRecents([item]).length || (state.recents || [])[0] === item) return;
      update((s) => { pushRecent(s, item); }, { from: "recent" });
    },
    // "Desfazer" after the example was replaced: the example goals and checks come back, still flagged as example
    restoreExample(snap) {
      if (!snap || !Array.isArray(snap.goals)) return;
      update((s) => { s.goals = cleanGoals(snap.goals); s.done = trueMap(snap.done); s.example = s.goals.length > 0; }, { from: "example" });
    },
    setQty(item, qty, meta) { update((s) => { touchGoals(s); const g = s.goals.find((x) => x.item === item); if (g) g.qty = clampQty(qty); }, meta); },
    bumpQty(item, d) { update((s) => { touchGoals(s); const g = s.goals.find((x) => x.item === item); if (g) g.qty = clampQty(g.qty + d); }); },
    removeGoal(item) { update((s) => { touchGoals(s); s.goals = s.goals.filter((x) => x.item !== item); }); },
    clearGoals() { update((s) => { s.goals = []; s.done = {}; s.example = false; }); },
    // no stamp: an untouched example never overwrites a plan saved in the account
    seedExample(goals) { update((s) => { s.goals = goals.map((g) => ({ item: g.item, qty: clampQty(g.qty) })); s.example = true; }, { from: "example", noStamp: true }); },
    toggleHave(item) { update((s) => { if (s.have[item]) delete s.have[item]; else s.have[item] = true; }); },
    // "tenho N de M": true = everything, a number = partial stock, null / 0 = clear
    setHave(item, v) { update((s) => { const c = clampHave(typeof v === "string" ? +v : v); if (c == null) delete s.have[item]; else s.have[item] = c; }); },
    // group items ("Brema ou carpa"): which member fills it (null = any, shown as the group)
    setGroupChoice(group, member) { update((s) => { if (member) s.groupChoice[group] = member; else delete s.groupChoice[group]; }); },
    // yield bonuses ("Vantagens"): perk id on / off
    setPerk(id, on) { update((s) => { if (on) s.perks[id] = true; else delete s.perks[id]; }, { from: "perk" }); },
    chooseRecipe(item, rid) { update((s) => { if (rid) s.choice[item] = rid; else delete s.choice[item]; }); },
    toggleDone(key, on) { update((s) => { if (on) s.done[key] = true; else delete s.done[key]; }); },
    clearDone() { update((s) => { s.done = {}; }); },
    setLang(code) { update((s) => { s.lang = code; }, { from: "lang" }); },
    setTheme(mode) { update((s) => { s.theme = THEMES.indexOf(mode) >= 0 ? mode : "auto"; }, { from: "theme" }); },
    setShowHidden(on) { update((s) => { s.showHidden = !!on; }, { from: "search-toggle" }); },
    // collapsed planner panels (per device): setUi({todayCollapsed: true}); only the known flags are taken
    setUi(patch) {
      update((s) => {
        const u = (s.ui = cleanUi(s.ui)), p = patch && typeof patch === "object" ? patch : {};
        for (const k of UI_FLAGS) if (k in p) u[k] = !!p[k];
        if (p.stationCollapsed && typeof p.stationCollapsed === "object") u.stationCollapsed = cleanUi({ stationCollapsed: p.stationCollapsed }).stationCollapsed;
      }, { from: "ui" });
    },
    // one station card collapsed / expanded (key from ui/summary.js); on = undefined flips it
    toggleStation(key, on) {
      if (typeof key !== "string" || !key) return;
      update((s) => {
        const u = (s.ui = cleanUi(s.ui)), next = on === undefined ? !u.stationCollapsed[key] : !!on;
        if (next) u.stationCollapsed[key] = true; else delete u.stationCollapsed[key];
      }, { from: "ui" });
    },
    setOverride(lang, item, value) {
      update((s) => {
        const v = String(value || "").trim();
        const m = (s.overrides[lang] = s.overrides[lang] || {});
        if (v) m[item] = v; else delete m[item];
        if (!Object.keys(m).length) delete s.overrides[lang];
      }, { from: "edit" });
    },
    // Tecnologias: "Já pesquisei" per technology id (synced with the account)
    setResearched(techId, on) { update((s) => { if (on) s.researched[techId] = true; else delete s.researched[techId]; }, { from: "tech" }); },
    clearResearched() { update((s) => { s.researched = {}; }, { from: "tech" }); },
    // Receitas: "Já estudei" per item id (synced with the account); unknown ids and no-op changes are ignored
    setStudied(itemId, on) {
      const cur = cleanStudied(state.studied), next = cleanStudied(on ? cur.concat([itemId]) : cur.filter((x) => x !== itemId));
      if (JSON.stringify(next) === JSON.stringify(cur)) return;
      update((s) => { s.studied = next; }, { from: "study" });
    },
    // Dias: "Hoje é este dia". dayNumber: a number / numeric string sets the HUD counter, null / "" clears it,
    // undefined keeps it. A day together with a counter (given now or already set) calibrates: dayAnchor = {number,
    // day}. setDay(null) clears day and counter (the calibration stays; clearAnchor() drops it).
    // Every day action ends with fixDone: the "feito hoje" ticks of a day that is no longer today go away.
    setDay(dayId, dayNumber) {
      update((s) => {
        s.day = validDay(dayId);
        if (dayNumber !== undefined) s.dayNumber = clampDayNumber(dayNumber);
        if (!s.day) s.dayNumber = null;
        else if (s.dayNumber != null) s.dayAnchor = { number: s.dayNumber, day: s.day };
        fixDone(s);
      }, { from: "day" });
    },
    // the HUD counter alone: calibrated -> the weekday follows from the anchor; not calibrated but a day is set ->
    // this pair becomes the anchor; else only the counter is kept. Returns the resulting day (or null).
    setDayNumber(n) {
      update((s) => {
        s.dayNumber = clampDayNumber(n);
        if (s.dayNumber != null) {
          const d = dayFromNumber(s.dayNumber, s.dayAnchor);
          if (d) s.day = d;
          else if (validDay(s.day)) s.dayAnchor = { number: s.dayNumber, day: s.day };
        }
        fixDone(s);
      }, { from: "day" });
      return state.day;
    },
    // "Feito hoje": tick / untick event #idx of today's day (on = undefined flips it). No-op without a day.
    toggleDayDone(idx, on) {
      const i = typeof idx === "string" && idx.trim() ? +idx : idx;
      if (!validDay(state.day) || !Number.isInteger(i) || i < 0 || i >= 100) return;
      update((s) => {
        const ids = new Set(doneToday(s)), next = on === undefined ? !ids.has(i) : !!on;
        if (next) ids.add(i); else ids.delete(i);
        s.dayDone = cleanDone({ day: s.day, number: s.dayNumber, ids: Array.from(ids) }, validDay(s.day), s.dayNumber);
      }, { from: "day-done" });
    },
    // "Bilhete do dia": the note of one weekday ("" / null removes it). Returns the stored text ("" = none).
    setDayNote(dayId, text) {
      const id = validDay(dayId);
      if (!id) return "";
      const v = cleanNote(text);
      update((s) => { s.dayNotes = cleanNotes(s.dayNotes); if (v) s.dayNotes[id] = v; else delete s.dayNotes[id]; }, { from: "day-note" });
      return v;
    },
    // "recalibrar": forget the calibration (the next day + counter pair sets a new one)
    clearAnchor() { update((s) => { s.dayAnchor = null; }, { from: "day" }); },
    // "Avançar dia": the next day in wheel order (wraps), counter + 1 when it is set. No-op without a day.
    advanceDay() {
      const st = state;
      if (!validDay(st.day)) return false;
      update((s) => {
        const order = dayOrder(), i = order.indexOf(s.day);
        s.day = order[(i + 1) % order.length] || order[0];
        if (s.dayNumber != null) s.dayNumber = Math.min(99999, s.dayNumber + 1);
        fixDone(s);
      }, { from: "day" });
      return true;
    },
    pruneUnknown(isKnown) {
      ensureLists(state);
      for (const l of state.lists) l.goals = l.goals.filter((g) => isKnown(g.item));
      loadActive(state);
    },
    // ---- lists (schema 5). Names are cleaned (one line, ≤ LIST_NAME_MAX); every list change is synced.
    // A new list starts empty and opens. Returns its id (null at LISTS_MAX lists).
    createList(name) {
      if (state.lists.length >= LISTS_MAX) return null;
      let id = null;
      update((s) => {
        const now = stamp(s.updatedAt);
        do { id = "l" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7); } while (s.lists.some((l) => l.id === id));
        s.lists.push(Object.assign({ id, name: cleanName(name), createdAt: now, updatedAt: now }, EMPTY_LIST()));
        s.ui = cleanUi(s.ui); s.ui.activeList = id;
        loadActive(s);
      }, { from: "lists" });
      return id;
    },
    // a blank name is ignored; returns the stored name
    renameList(id, name) {
      const nm = cleanName(name), l = state.lists.find((x) => x.id === id);
      if (!l || !nm) return l ? l.name : "";
      if (nm !== l.name) update((s) => { const x = s.lists.find((y) => y.id === id); x.name = nm; x.updatedAt = stamp(x.updatedAt); }, { from: "lists" });
      return nm;
    },
    // the last list cannot go; deleting the open one opens the first that is left. Returns true when deleted.
    deleteList(id) {
      if (state.lists.length < 2 || !state.lists.some((l) => l.id === id)) return false;
      update((s) => {
        const gone = s.lists.find((l) => l.id === id);
        s.lists = s.lists.filter((l) => l.id !== id);
        s.listsGone = cleanGone(Object.assign({}, s.listsGone, { [id]: stamp(gone.updatedAt > s.updatedAt ? gone.updatedAt : s.updatedAt) }));
        if (s.legacyOf === id) { s.ui = cleanUi(s.ui); s.ui.activeList = s.lists[0].id; loadActive(s); }
      }, { from: "lists" });
      return true;
    },
    // open another list on this device (not synced: no stamp, nothing pushed); everything re-renders
    switchList(id) {
      if (!state.lists.some((l) => l.id === id) || id === state.legacyOf) return;
      update((s) => { s.ui = cleanUi(s.ui); s.ui.activeList = id; loadActive(s); }, { from: "list-switch" });
    },
    // GK.sync: replace the synced fields with the account's copy (already sanitized)
    // (also used for a merged copy: then updatedAt is a fresh stamp and GK.sync pushes it)
    applyRemote(fields, updatedAt) {
      update((s) => {
        Object.assign(s, fields);
        ensureLists(s);
        for (const l of s.lists) l.goals = l.goals.filter((g) => !!GK.data.item(g.item));
        loadActive(s);                                // this device's open list (the first when it is gone)
        s.updatedAt = updatedAt;
      }, { from: "sync", noStamp: true });
    },
  };
  return { get: () => state, load, subscribe: (fn) => subs.push(fn), actions, update, clampQty, SCHEMA, THEMES, ISO, SYNCED,
    PER_LIST, MIRROR, syncPayload, syncKey, legacyMirror, sanitizeRemote, hasContent, mergeSynced, stamp, useAccount, setSyncBase,
    storageKey: () => key, activeList: (s) => activeList(s || state), LIST_NAME_MAX, LISTS_MAX, RECENTS_MAX, DAY_IDS, dayOrder, dayFromNumber, doneToday, NOTE_MAX, LATE, keepLate, adoptLate };
})();
