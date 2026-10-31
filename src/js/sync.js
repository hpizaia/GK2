/* GK.sync: keeps the planner in the viewer's own private db document
   (Claude Artifact `db` + `user` capabilities):
       data/users/<user id>/state  =  { v, updatedAt, state: {goals, choice, have, done, overrides, example,
                                                              researched, groupChoice, perks, day, dayNumber,
                                                              dayAnchor, dayDone, dayNotes, …} }
   localStorage stays the first source (instant render, offline), keyed by account (GK.store.useAccount).
   Reconciling a snapshot with the local copy (base = the last version both held, state.syncBase):
     - same updatedAt                 nothing to do
     - only the account changed       the account copy wins (applyRemote)
     - only this device changed       push the local copy
     - both changed since base        merge field by field (GK.store.mergeSynced: maps by union, remote wins for
                                      done/have/researched/perks/groupChoice, local wins for goals/choice/overrides),
                                      stamp it newer than both and push it
     - no base yet (first sync)       the newer updatedAt wins (an EPOCH plan is pushed only to an empty account)
   dayDone / dayNotes (1.3.4, GK.store.LATE) are absent from docs written by older pages, and absent is not "empty":
     - the account wins but its doc has no such key   keep this device's value (keepLate), stamp, push
     - same updatedAt, the doc has them, we don't     adopt the doc's (adoptLate; an older page carried them along)
     - merge                                          dayDone by union on the merged day, dayNotes newer side wins
   Forward compatibility: the doc's `v` is read and kept (max of ours and theirs), and top-level fields of
   `state` this version does not know (written by a newer page) are written back untouched.
   One subscription (recreated once, with backoff, after it dies; again on `online`), one write in flight,
   1.5 s debounce, writes only when the payload changed, one retry with jitter after a failed write.
   Without the capabilities: "this device only".
   Exposes: GK.sync.{start, onStore, status, syncedAt, subscribe}. Its status texts live in ui/footer.js.
*/
GK.sync = (function () {
  const DEBOUNCE = 1500, LOAD_TIMEOUT = 10000, MAX_BYTES = 250000;   // db limit is 256 KiB a doc
  const TERMINAL = { revoked: 1, not_granted: 1, capability_disabled: 1, capability_removed: 1, invalid_argument: 1, transform_error: 1 };
  let status = "loading";      // loading | syncing | synced | local | error
  let syncedAt = 0;
  let ref = null;              // DocumentReference of the viewer's state doc
  let unsub = null;            // the live onSnapshot listener (null = none / dead)
  let ready = false;           // an authoritative (not cached) snapshot was reconciled
  let inFlight = false, dirty = false, timer = null, loadTimer = null, retryTimer = null, started = false;
  let listenRetries = 0, writeRetried = false, gen = 0;
  let lastPushed = null;       // JSON of the payload the account holds (pushed or received)
  let lastSeenAt = null;       // local updatedAt already scheduled
  let remoteV = 0;             // the doc's schema version as last read
  let remoteRest = {};         // fields of the doc's `state` this version does not know (kept on write)
  const subs = [];
  const S = () => GK.store;
  function setStatus(s) {
    status = s;
    if (s === "synced") syncedAt = Date.now();
    subs.forEach((f) => f(status));
  }
  function stopListening() { if (unsub) { try { unsub(); } catch (e) { /* ignore */ } } unsub = null; }
  function disable() { stopListening(); ref = null; clearTimeout(timer); clearTimeout(retryTimer); setStatus("local"); }
  function schedule(ms) {
    clearTimeout(timer);
    timer = setTimeout(flush, ms);
  }
  const jitter = (a, b) => a + Math.floor(Math.random() * (b - a));
  const bytes = (s) => (typeof Blob !== "undefined" ? new Blob([s]).size : typeof TextEncoder !== "undefined" ? new TextEncoder().encode(s).length : s.length * 3);
  // the doc body: unknown fields of the account copy first, then everything this version owns
  function body(st) {
    return { v: Math.max(S().SCHEMA, remoteV || 0), updatedAt: st.updatedAt, state: Object.assign({}, remoteRest, S().syncPayload(st)) };
  }
  async function flush() {
    if (!ref || !ready) return;               // reconciled first; the snapshot handler flushes afterwards
    if (inFlight) { dirty = true; return; }
    const st = S().get();
    if (!st.updatedAt) return;                // nothing the user made (fresh state / untouched example)
    const json = JSON.stringify(S().syncPayload(st));
    if (json === lastPushed) { S().setSyncBase(st.updatedAt); if (status !== "error") setStatus("synced"); return; }
    const doc = JSON.parse(JSON.stringify(body(st)));
    if (bytes(JSON.stringify(doc)) > MAX_BYTES) { setStatus("error"); return; }
    inFlight = true; dirty = false;
    setStatus("syncing");
    const at = st.updatedAt, myRef = ref;
    try {
      await myRef.set(doc);
      lastPushed = json;
      writeRetried = false;
      S().setSyncBase(at);
      setStatus("synced");
    } catch (e) {
      const code = (e && e.code) || "unavailable";
      if (TERMINAL[code]) disable();          // e.g. a view-only member: no writes for this visit
      else {
        setStatus("error");                   // rate limit, quota, offline
        if (!writeRetried) { writeRetried = true; dirty = false; schedule(jitter(2000, 5000)); }
      }
      dirty = false;
    } finally {
      inFlight = false;
      if (dirty && ref) schedule(0);
    }
  }
  function onSnap(snap) {
    listenRetries = 0;
    const meta = snap.metadata || {};
    if (meta.hasPendingWrites) return;        // our own write echoing back before confirmation
    const authoritative = !meta.fromCache;
    const st = S().get();
    let pushLocal = false;
    const d = snap.exists ? snap.data() : null;
    const fields = d && typeof d.updatedAt === "string" && S().ISO.test(d.updatedAt) ? S().sanitizeRemote(d.state) : null;
    if (d && d.state && typeof d.state === "object") {
      remoteV = typeof d.v === "number" && isFinite(d.v) ? d.v : 0;
      remoteRest = {};
      for (const [k, v] of Object.entries(d.state)) if (S().SYNCED.indexOf(k) < 0) remoteRest[k] = v;
    }
    if (fields) {
      const base = st.syncBase || "";
      const localChanged = !!st.updatedAt && (!base || st.updatedAt > base);
      const remoteChanged = !base || d.updatedAt > base;
      if (d.updatedAt === st.updatedAt) {    // same version (or our echo)
        const adopt = S().adoptLate(fields, S().syncPayload(st));
        if (adopt) S().actions.applyRemote(adopt, d.updatedAt);
        lastPushed = JSON.stringify(S().syncPayload(S().get()));
        if (authoritative) S().setSyncBase(d.updatedAt);
      } else if (base && localChanged && remoteChanged) {
        // both edited since the version they shared: merge (rule in GK.store.mergeSynced), then push
        const merged = S().mergeSynced(S().syncPayload(st), fields, d.updatedAt > st.updatedAt);
        const at = S().stamp(d.updatedAt > st.updatedAt ? d.updatedAt : st.updatedAt);
        S().actions.applyRemote(merged, at);
        lastSeenAt = at;
        pushLocal = true; lastPushed = null;
      } else if (!st.updatedAt || d.updatedAt > st.updatedAt) {
        const kept = S().keepLate(fields, d.state, S().syncPayload(st));
        if (kept) {
          // the account wins, but its doc predates dayDone / dayNotes: ours stay, and the result is pushed
          const at = S().stamp(d.updatedAt);
          S().actions.applyRemote(kept, at);
          lastSeenAt = at;
          pushLocal = true; lastPushed = null;
        } else {
          lastSeenAt = d.updatedAt;
          S().actions.applyRemote(fields, d.updatedAt);
          lastPushed = JSON.stringify(S().syncPayload(S().get()));
          if (authoritative) S().setSyncBase(d.updatedAt);
        }
      } else { pushLocal = true; lastPushed = null; }   // local is newer
    } else {                                  // no doc, or a body that fails validation: push local if it has content
      pushLocal = !!st.updatedAt;
      lastPushed = null;
    }
    if (!authoritative) return;               // a cached copy can update the view, never trigger writes
    clearTimeout(loadTimer);
    ready = true;
    if (pushLocal) schedule(0);
    else if (status !== "error") setStatus("synced");
  }
  function listen() {
    if (!ref) return;
    stopListening();
    const g = gen;
    try {
      const u = ref.onSnapshot((snap) => { if (g === gen) onSnap(snap); }, (e) => { if (g === gen) onError(e); });
      unsub = typeof u === "function" ? u : () => {};
    } catch (e) { onError(e); }
  }
  // the listener is dead after an error (platform contract): one new subscription after a random wait
  function onError(e) {
    stopListening();
    const code = (e && e.code) || "unavailable";
    if (TERMINAL[code]) { clearTimeout(loadTimer); disable(); return; }
    if (listenRetries < 1) {
      listenRetries++;
      if (ready) setStatus("error");
      clearTimeout(retryTimer);
      retryTimer = setTimeout(listen, jitter(1500, 4000));
      return;
    }
    clearTimeout(loadTimer);
    if (!ready) disable(); else setStatus("error");
  }
  // back online / tab visible again: bring a dead listener back (and send what is pending)
  function revive() {
    if (!ref || unsub) return;
    listenRetries = 0;
    clearTimeout(retryTimer);
    listen();
  }
  if (typeof window !== "undefined" && window.addEventListener) {
    window.addEventListener("online", () => { revive(); if (ref && ready && status === "error") schedule(0); });
    if (typeof document !== "undefined" && document.addEventListener) {
      document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") revive(); });
    }
  }
  async function start(c) {
    if (started && !c) return;
    started = true;
    gen++;
    stopListening(); clearTimeout(retryTimer);
    ref = null; ready = false; lastPushed = null; dirty = false; clearTimeout(timer);   // (a second start is a test hook)
    listenRetries = 0; writeRetried = false; remoteV = 0; remoteRest = {};
    const claude = c || window.claude;
    if (!claude || typeof claude.use !== "function") { setStatus("local"); return; }
    setStatus("loading");
    clearTimeout(loadTimer);
    loadTimer = setTimeout(() => { if (!ready) setStatus("local"); }, LOAD_TIMEOUT);   // stop waiting, keep the page
    let db = null, user = null, id = null, failed = false;
    try {
      [db, user] = await Promise.all([claude.use("db"), claude.use("user")]);
      id = db && user ? await user.id() : null;
    } catch (e) { db = null; failed = true; }
    if (!db || !id) {
      clearTimeout(loadTimer);
      // no account for sure (not a transient failure): show the device's own plan, never another account's
      if (!failed) S().useAccount(null);
      setStatus("local");
      return;
    }
    S().useAccount(String(id));               // this account's local copy (migrates the anonymous one once)
    try { ref = db.collection("data/users/" + id).doc("state"); } catch (e) { clearTimeout(loadTimer); setStatus("local"); return; }
    if (status === "loading") setStatus("syncing");
    lastSeenAt = S().get().updatedAt;
    listen();
  }
  // every local change to a synced field: debounce, then one write
  function onStore(state, meta) {
    if (meta && (meta.from === "sync" || meta.from === "account")) { lastSeenAt = state.updatedAt; return; }
    if (state.updatedAt === lastSeenAt) return;   // theme, language, search toggle: nothing to send
    lastSeenAt = state.updatedAt;
    if (!ref) return;
    if (status === "synced" || status === "error") setStatus("syncing");
    schedule(DEBOUNCE);
  }
  return {
    start, onStore,
    status: () => status, syncedAt: () => syncedAt,
    subscribe: (f) => subs.push(f),
  };
})();
