/* GK.ui.days: the Dias screen (#days): the 6-day week as the game HUD's wheel (the official day medallions from the
   sprite on a ring, Gluttony at 12 o'clock and the rest counter-clockwise in meta.order; the current day's medallion
   stands out of the ring with an arrow pointing at it), a "Hoje" bar (current day, HUD day counter with calibration,
   "Avançar dia", and "Ajustar o dia ›", a toggle (aria-expanded) that shows "Esquecer o dia" and "Recalibrar"), the
   selected day's card (name, "N coisas", events grouped by kind, "não confirmado" for medium/low confidence, source in
   the tooltip, unlock quest, detail, the official game text) with "Hoje é este dia" when it is not today already
   (the HOJE badge says it), a compact 6-row week table, and "Como funciona" (folded, at the top; it also says that
   the short lines are the app's own). 1.6.0 cut the fixed hint, the "Ira · Wrath" line, the permanent "Calibrado com
   o dia 61 = Ira…" sentence (the toast after calibrating says it once) and the wiki credit line (it is in Créditos).
   Each medallion on the wheel carries its short name ("Gula", "Ira"), so two similar reds never depend on colour
   alone. Under its header the day card holds that
   weekday's "Bilhete do dia" (one short note, GK.store dayNotes; noteBox below, shared with ui/today.js).
   Data: the payload's `days` block (data/days.json, embedded by scripts/build.py), kept by GK.data.load as
   GK.data.get().days.
   Owns: [data-panel="days"] (section created by GK.router.ensureScreens), the route "days" and its tab "tab.days",
   the shared week helpers below. State: GK.store day / dayNumber / dayAnchor / dayNotes (setDay, setDayNumber,
   advanceDay, clearAnchor, setDayNote).
   Exposes: GK.ui.days.{mount, render, open(dayId), week(), day(id), current(state), next(day), glyph(day, px),
   medal(day, px), kindIcon(kind, px), kinds, eventText(ev), whoText(ev), confidenceBadge(ev),
   eventMore(ev, state, quoteOpen) (the lines under an event: with whom, detail, items, game text), tile(day, px),
   numberToast(anchorBefore), noteBox(prefix, rerender)}.
   ui/today.js (the planner "Hoje" panel) uses the helpers. An event's `task` (data/days.json; absent = true) says
   whether the Hoje panel gives it a "feito hoje" tick.
   1.8.0 (backlog 2.5): the folded game text opens from a small quote mark “ (its label, "Texto do jogo", is for
   screen readers and the tooltip), no longer an underlined word that read like a link.
*/
GK.i18n.add({
  pt: {
    "tab.days": "Dias",
    "days.title": "Dias da semana",
    "days.wheel": "Roda da semana",
    "days.med": "{name}: {n} coisas",
    "days.medToday": "{name} (hoje): {n} coisas",
    "days.todayBadge": "hoje",
    "days.counter": "dia {n}",
    "days.todayIs": "Hoje: {name}",
    "days.todayUnset": "Qual dia é hoje no jogo?",
    "days.todayUnsetHint": "Toque na roda o símbolo que a seta aponta no jogo e use “Hoje é este dia”, ou digite o contador se já calibrou.",
    "days.nothing": "Nada especial registrado para este dia.",
    "days.setToday": "Hoje é este dia",
    "days.advance": "Avançar dia",
    "days.forget": "Esquecer o dia",
    "days.adjust": "Ajustar o dia",
    "days.number": "Contador do jogo",
    "days.numberPh": "nº",
    "days.recalibrate": "Recalibrar",
    "days.calibrateHint": "Para calibrar, informe uma vez o dia de hoje e o número do canto da tela (ex.: dia 60 = Orgulho); depois basta digitar o número.",
    "days.setToast": "Hoje: {name}",
    "days.setToastN": "Hoje: {name} · dia {n}",
    "days.calToast": "Calibrado: dia {n} = {name}",
    "days.numToast": "Dia {n}: {name}",
    "days.advToast": "Avançou para {name}",
    "days.advToastN": "Avançou para {name} · dia {n}",
    "days.forgotToast": "Dia de hoje esquecido",
    "days.recalToast": "Calibração apagada. Informe o dia e o número de novo.",
    "days.week": "A semana",
    "days.how": "Como funciona",
    "days.orderUnsure": "A ordem dos dias vem de guias e da wiki; o jogo não a escreve.",
    "days.machineNote": "As frases curtas foram escritas para este app; o texto oficial do jogo abre nas aspas “ de cada evento.",
    "days.unconfirmed": "não confirmado",
    "days.conf.medium": "Confiança média: só a wiki ou um guia diz isso",
    "days.conf.low": "Confiança baixa: um único guia, não verificado",
    "days.source": "Fonte: {src}",
    "days.also": "também: {src}",
    "days.who": "com {who}",
    "days.unlockQuest": "depois da missão “{q}”",
    "days.quote": "Texto do jogo",
    "days.items": "Itens:",
    "days.empty": "Os dados dos dias da semana não estão nesta página.",
    "days.kind.npc": "Pessoas",
    "days.kind.merchant": "Comércio",
    "days.kind.church": "Igreja",
    "days.kind.battle": "Combate",
    "days.kind.quest": "Missões",
    "days.kind.event": "Eventos",
    "days.kind.other": "Outros",
    "days.count.one": "{n} coisa",
    "days.count.other": "{n} coisas",
    "days.note.label": "Bilhete",
    "days.note.add": "Deixar um bilhete para este dia",
    "days.note.edit": "Editar",
    "days.note.editX": "Editar o bilhete de {name}",
    "days.note.ta": "Bilhete para {name}",
    "days.note.ph": "ex.: levar 3 peixes para o Pescador",
    "days.note.count": "{n}/{max} · Enter salva",
    "days.note.saved": "Bilhete salvo: {name}",
    "days.note.cleared": "Bilhete apagado: {name}",
  },
  en: {
    "tab.days": "Days",
    "days.title": "Days of the week",
    "days.wheel": "Week wheel",
    "days.med": "{name}: {n} things",
    "days.medToday": "{name} (today): {n} things",
    "days.todayBadge": "today",
    "days.counter": "day {n}",
    "days.todayIs": "Today: {name}",
    "days.todayUnset": "Which day is it in the game?",
    "days.todayUnsetHint": "Tap on the wheel the symbol the arrow points at in the game and use “Today is this day”, or type the counter once calibrated.",
    "days.nothing": "Nothing special recorded for this day.",
    "days.setToday": "Today is this day",
    "days.advance": "Next day",
    "days.forget": "Forget the day",
    "days.adjust": "Adjust the day",
    "days.number": "Game counter",
    "days.numberPh": "no.",
    "days.recalibrate": "Recalibrate",
    "days.calibrateHint": "To calibrate, give today's day and the number in the screen corner once (e.g. day 60 = Pride); after that, just type the number.",
    "days.setToast": "Today: {name}",
    "days.setToastN": "Today: {name} · day {n}",
    "days.calToast": "Calibrated: day {n} = {name}",
    "days.numToast": "Day {n}: {name}",
    "days.advToast": "Moved on to {name}",
    "days.advToastN": "Moved on to {name} · day {n}",
    "days.forgotToast": "Today's day forgotten",
    "days.recalToast": "Calibration cleared. Give the day and the number again.",
    "days.week": "The week",
    "days.how": "How it works",
    "days.orderUnsure": "The order of the days comes from guides and the wiki; the game never writes it.",
    "days.machineNote": "The short lines were written for this app; the official game text opens from each event’s quote mark “.",
    "days.unconfirmed": "unconfirmed",
    "days.conf.medium": "Medium confidence: only the wiki or a guide says so",
    "days.conf.low": "Low confidence: a single unverified guide",
    "days.source": "Source: {src}",
    "days.also": "also: {src}",
    "days.who": "with {who}",
    "days.unlockQuest": "after the quest “{q}”",
    "days.quote": "Game text",
    "days.items": "Items:",
    "days.empty": "The days of the week data is not in this page.",
    "days.kind.npc": "People",
    "days.kind.merchant": "Merchants",
    "days.kind.church": "Church",
    "days.kind.battle": "Battle",
    "days.kind.quest": "Quests",
    "days.kind.event": "Events",
    "days.kind.other": "Other",
    "days.count.one": "{n} thing",
    "days.count.other": "{n} things",
    "days.note.label": "Note",
    "days.note.add": "Leave a note for this day",
    "days.note.edit": "Edit",
    "days.note.editX": "Edit the note for {name}",
    "days.note.ta": "Note for {name}",
    "days.note.ph": "e.g. bring 3 fish to the Fisherman",
    "days.note.count": "{n}/{max} · Enter saves",
    "days.note.saved": "Note saved: {name}",
    "days.note.cleared": "Note removed: {name}",
  },
});

GK.ui.days = (function () {
  const { t, name, num } = GK.i18n, { esc } = GK.util;
  const KINDS = ["npc", "merchant", "church", "battle", "quest", "event", "other"];

  // ---- pixel glyphs (fallback when the sprite has no medallion): 9x9 grids, "#" = filled ----
  const G = {
    trident: ["#...#...#", "#...#...#", "#...#...#", "##..#..##", ".#######.", "....#....", "....#....", "....#....", "....#...."],
    moon: ["...####..", "..##.....", ".##......", ".##......", ".##......", ".##......", "..##.....", "...####..", "........."],
    venus: ["..#####..", ".#.....#.", ".#.....#.", ".#.....#.", "..#####..", "....#....", "..#####..", "....#....", "....#...."],
    horns: ["#.......#", ".#.....#.", "..#####..", ".##...##.", ".#.....#.", ".#.....#.", ".##...##.", "..#####..", "........."],
    sun: ["....#....", ".#.....#.", "...###...", "..#####..", "#.#####.#", "..#####..", "...###...", ".#.....#.", "....#...."],
    mars: ["....#....", "...###...", "..#.#.#..", "....#....", "..#####..", ".#.....#.", ".#.....#.", ".#.....#.", "..#####.."],
    coin: ["..#####..", ".#.....#.", "#...#...#", "#..###..#", "#...#...#", "#..###..#", "#...#...#", ".#.....#.", "..#####.."],
    // event kinds
    npc: ["...###...", "..#####..", "..#####..", "...###...", ".........", ".#######.", "#########", "#########", "#########"],
    merchant: [".........", "..#####..", ".#.....#.", "..#####..", ".#.....#.", "..#####..", ".#.....#.", "..#####..", "........."],
    church: ["...###...", "...###...", "#########", "#########", "...###...", "...###...", "...###...", "...###...", "...###..."],
    battle: [".......##", "......###", ".....###.", "#...###..", ".#.###...", "..###....", "..##.....", ".#..#....", "#........"],
    quest: ["...###...", "...###...", "...###...", "...###...", "...###...", ".........", "...###...", "...###...", "........."],
    event: ["....#....", "....#....", "...###...", "#########", ".#######.", "..#####..", "..##.##..", ".##...##.", ".#.....#."],
    other: ["....#....", "...###...", "..#####..", ".#######.", "#########", ".#######.", "..#####..", "...###...", "....#...."],
  };
  const pathCache = {};
  function gridPath(key) {
    if (pathCache[key]) return pathCache[key];
    let d = "";
    (G[key] || G.other).forEach((row, y) => {
      for (let x = 0; x < row.length;) {
        if (row[x] !== "#") { x++; continue; }
        let w = 1;
        while (row[x + w] === "#") w++;
        d += `M${x} ${y}h${w}v1h-${w}z`;
        x += w;
      }
    });
    return (pathCache[key] = d);
  }
  // which drawn glyph fits the data's `glyph` description, else the sin itself
  const KEYWORDS = [[/trident|ψ|tridente/i, "trident"], [/crescent|moon|lua/i, "moon"], [/venus|♀/i, "venus"],
    [/horn|♉|chifre/i, "horns"], [/\bsun\b|\bsol\b/i, "sun"], [/♂|mars|arrow|flame|seta|chama/i, "mars"], [/coin|moeda/i, "coin"]];
  const BY_SIN = { gluttony: "trident", sloth: "moon", lust: "venus", envy: "horns", pride: "sun", wrath: "mars", greed: "coin" };
  function glyphKey(d) {
    const txt = [d.glyph, d.glyphPt].filter((x) => typeof x === "string").join(" ");
    for (const [re, k] of KEYWORDS) if (re.test(txt)) return k;
    return BY_SIN[d.id] || null;
  }
  function glyph(d, px) {
    const k = d && glyphKey(d), s = px || 24;
    if (!k) return `<span class="days-letter" aria-hidden="true" style="font-size:${Math.round(s * 0.8)}px">${esc((name(d && d.sin) || "?")[0].toUpperCase())}</span>`;
    return `<svg class="days-glyph" width="${s}" height="${s}" viewBox="0 0 9 9" aria-hidden="true" focusable="false" shape-rendering="crispEdges" fill="currentColor"><path d="${gridPath(k)}"/></svg>`;
  }
  const kindIcon = (kind, px) => `<svg class="days-kind-ico" width="${px || 16}" height="${px || 16}" viewBox="0 0 9 9" aria-hidden="true" focusable="false" shape-rendering="crispEdges" fill="currentColor"><path d="${gridPath(KINDS.indexOf(kind) >= 0 ? kind : "other")}"/></svg>`;
  // the official medallion in the sprite ("day:<id>", else the day's own sprite id)
  function spritePos(d) {
    const sp = GK.data.get().meta && GK.data.get().meta.sprite;
    if (!sp || !sp.icons) return null;
    return sp.icons["day:" + d.id] || (d.sprite && sp.icons[d.sprite]) || null;
  }
  // medallion art at about px: the sprite cell scaled so its 25 px disc (centred in a 32 px cell) is px wide,
  // else the drawn glyph
  function medal(d, px) {
    const pos = spritePos(d);
    if (pos) return `<span class="ico days-ico" aria-hidden="true" style="--s:${Math.round(px * 32 / 25)}px;--x:${+pos[0]};--y:${+pos[1]}"></span>`;
    return glyph(d, Math.round(px * 0.6));
  }
  // square tile with the medallion (lists, cards, the planner panel)
  function tile(d, px, cls) {
    const style = d.color ? ` style="--day:${esc(d.color)}"` : "";
    return `<span class="days-tile${spritePos(d) ? " has-ico" : ""} ${cls || ""}"${style}>${medal(d, px)}</span>`;
  }

  // ---- the week, normalized once per payload ----
  let weekSrc, weekCache = null;
  const locOf = (v) => (v == null || v === "" ? null : typeof v === "string" ? { pt: v, en: v } : v);
  const HEX = /^#[0-9a-f]{3}([0-9a-f]{3})?([0-9a-f]{2})?$/i;
  function week() {
    const raw = GK.data.get().days;
    if (raw === weekSrc) return weekCache;
    weekSrc = raw; weekCache = null;
    if (!raw || !Array.isArray(raw.days) || !raw.days.length) return null;
    const meta = raw.meta || {};
    const days = raw.days.filter((d) => d && typeof d.id === "string" && d.id).map((d, i) => {
      const sin = locOf(d.sin) || { pt: d.id, en: d.id };
      return {
        id: d.id, order: typeof d.order === "number" ? d.order : i, sin, name: locOf(d.name) || sin, tr: d.tr || "official",
        sprite: d.sprite || null, glyph: d.glyph || null, glyphPt: d.glyph_pt || null,
        color: typeof d.color === "string" && HEX.test(d.color) ? d.color : null,
        events: (Array.isArray(d.events) ? d.events : []).filter((e) => e && (e.en || e.pt)).map((e) => ({
          kind: KINDS.indexOf(e.kind) >= 0 ? e.kind : "other", pt: e.pt || e.en, en: e.en || e.pt, tr: e.tr || "official",
          task: e.task !== false,   // something to do or buy that day (the Hoje panel's "feito hoje" tick); absent = true
          who: e.who || e.who_pt ? { en: e.who || e.who_pt, pt: e.who_pt || e.who } : null,
          source: e.source || null, also: Array.isArray(e.also) ? e.also : [],
          confidence: e.confidence === "medium" || e.confidence === "low" ? e.confidence : "high",
          items: Array.isArray(e.items) ? e.items.filter((x) => typeof x === "string") : [],
          unlock: e.unlock && (e.unlock.en || e.unlock.pt) ? e.unlock : null,
          short: e.short && (e.short.en || e.short.pt) ? { en: e.short.en || e.short.pt, pt: e.short.pt || e.short.en } : null,   // hand-written line title (Hoje)
          detail: locOf(e.detail), quote: e.quote && (e.quote.en || e.quote.pt) ? e.quote : null,
        })),
      };
    });
    // wheel / cycle order: meta.order, else `order`
    const ord = Array.isArray(meta.order) ? meta.order : [];
    const rank = (d) => (ord.indexOf(d.id) >= 0 ? ord.indexOf(d.id) : 100 + d.order);
    days.sort((a, b) => rank(a) - rank(b));
    weekCache = {
      days,
      meta: { notes: locOf(meta.notes), orderNote: locOf(meta.order_note), greed: meta.greed ? locOf(meta.greed.note) : null,
        orderConfidence: meta.order_confidence || null },
    };
    return weekCache;
  }
  const day = (id) => { const w = week(); return (w && id && w.days.find((d) => d.id === id)) || null; };
  const current = (state) => day(state.day);
  // the day after d in the wheel cycle (wraps)
  const next = (d) => { const w = week(), i = w && d ? w.days.indexOf(d) : -1; return i >= 0 ? w.days[(i + 1) % w.days.length] : null; };
  const eventText = (ev) => name(ev);
  const whoText = (ev) => (ev.who ? name(ev.who) : "");
  function confidenceBadge(ev) {
    if (ev.confidence === "high") return "";
    const tip = [t("days.conf." + ev.confidence), ev.source ? t("days.source", { src: ev.source }) : ""].filter(Boolean).join(" · ");
    return `<span class="badge days-unconf" title="${esc(tip)}">${esc(t("days.unconfirmed"))}</span>`;
  }
  // toast after a counter change (anchorBefore = state.dayAnchor before it)
  function numberToast(anchorBefore) {
    const st = GK.store.get(), d = current(st), a = st.dayAnchor;
    if (!d || st.dayNumber == null) return;
    if (a && (!anchorBefore || anchorBefore.number !== a.number || anchorBefore.day !== a.day)) GK.ui.toast(t("days.calToast", { n: a.number, name: name(d.name) }));
    else GK.ui.toast(t("days.numToast", { n: st.dayNumber, name: name(d.name) }));
  }

  // ---- "Bilhete do dia": one short note per weekday (GK.store dayNotes), shown and edited in the day card and in
  // ui/today.js. noteBox(prefix, rerender) remembers which day is being edited (ids are prefixed, so the two copies
  // never clash). html(d, state) draws the note line with "Editar", the quiet "Deixar um bilhete" link, or the
  // textarea (≤ NOTE_MAX, saved on Enter or when it loses focus; Esc cancels), with a toast. bind(root) once;
  // sig(id) for the caller's re-render memo; keep() before a re-render keeps what is being typed.
  function noteBox(pfx, rerender) {
    let editing = null;
    const ID = { edit: pfx + "-note-edit", ta: pfx + "-note-ta", n: pfx + "-note-n" };
    const MAX = GK.store.NOTE_MAX || 200;
    const noteOf = (id) => (GK.store.get().dayNotes || {})[id] || "";
    function html(d, state) {
      const txt = (state.dayNotes || {})[d.id] || "";
      if (editing === d.id) {
        return `<div class="day-note is-editing">
          <label class="sr-only" for="${ID.ta}">${esc(t("days.note.ta", { name: name(d.name) }))}</label>
          <textarea class="day-note-ta" id="${ID.ta}" data-note-ta="${esc(d.id)}" rows="2" maxlength="${MAX}" enterkeyhint="done" placeholder="${esc(t("days.note.ph"))}" aria-describedby="${ID.n}">${esc(txt)}</textarea>
          <span class="day-note-n tabnum" id="${ID.n}">${esc(t("days.note.count", { n: txt.length, max: MAX }))}</span>
        </div>`;
      }
      if (!txt) return `<div class="day-note is-empty"><button type="button" class="day-note-add" id="${ID.edit}" data-note-edit="${esc(d.id)}"><span aria-hidden="true">✎</span> ${esc(t("days.note.add"))}</button></div>`;
      return `<div class="day-note">
        <p class="day-note-text"><span class="day-note-l">${esc(t("days.note.label"))}:</span> ${esc(txt)}</p>
        <button type="button" class="btn btn-ghost btn-sm day-note-btn" id="${ID.edit}" data-note-edit="${esc(d.id)}" aria-label="${esc(t("days.note.editX", { name: name(d.name) }))}"><span aria-hidden="true">✎</span> ${esc(t("days.note.edit"))}</button>
      </div>`;
    }
    function focusEdit() { const b = document.getElementById(ID.edit); if (b) b.focus({ preventScroll: true }); }
    function save(ta, refocus) {
      const id = ta.dataset.noteTa, before = noteOf(id), d = day(id);
      editing = null;
      const after = GK.store.actions.setDayNote(id, ta.value);
      rerender();
      if (d && after !== before) GK.ui.toast(t(after ? "days.note.saved" : "days.note.cleared", { name: name(d.name) }));
      if (refocus) focusEdit();
    }
    function bind(root) {
      root.addEventListener("click", (e) => {
        const b = e.target.closest("[data-note-edit]");
        if (!b || !root.contains(b)) return;
        editing = b.dataset.noteEdit;
        rerender();
        const ta = document.getElementById(ID.ta);
        if (ta) { ta.focus({ preventScroll: true }); ta.setSelectionRange(ta.value.length, ta.value.length); }
      });
      root.addEventListener("keydown", (e) => {
        const ta = e.target.closest && e.target.closest("[data-note-ta]");
        if (!ta) return;
        if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); save(ta, true); }
        else if (e.key === "Escape") { e.preventDefault(); editing = null; rerender(); focusEdit(); }
      });
      root.addEventListener("input", (e) => {
        const ta = e.target.closest && e.target.closest("[data-note-ta]"), n = ta && document.getElementById(ID.n);
        if (n) n.textContent = t("days.note.count", { n: ta.value.length, max: MAX });
      });
      // leaving the field saves it, after the tap that moved the focus has landed (saving re-renders the panel, and
      // the button under the finger must still get its click); a field re-created meanwhile and focused again wins
      root.addEventListener("focusout", (e) => {
        const ta = e.target.closest && e.target.closest("[data-note-ta]");
        if (!ta || editing !== ta.dataset.noteTa) return;
        const go = () => {
          const a = document.activeElement;
          if (editing === ta.dataset.noteTa && !(a && a.matches && a.matches("[data-note-ta]"))) save(ta, false);
        };
        if (down) pend = go; else setTimeout(go, 0);
      });
    }
    let down = false, pend = null;
    if (typeof document !== "undefined" && document.addEventListener) {
      const up = () => { down = false; if (pend) { const f = pend; pend = null; setTimeout(f, 0); } };
      document.addEventListener("pointerdown", () => { down = true; }, true);
      document.addEventListener("pointerup", up, true);
      document.addEventListener("pointercancel", up, true);
    }
    // what is being typed survives a re-render that happens meanwhile (a sync snapshot, a store change)
    function keep() {
      const ta = document.getElementById(ID.ta);
      if (!ta || !editing) return () => {};
      const v = ta.value, a = ta.selectionStart, b = ta.selectionEnd, had = document.activeElement === ta;
      return () => {
        const nt = document.getElementById(ID.ta);
        if (!nt) return;
        nt.value = v;
        const n = document.getElementById(ID.n); if (n) n.textContent = t("days.note.count", { n: v.length, max: MAX });
        if (had) { nt.focus({ preventScroll: true }); try { nt.setSelectionRange(a, b); } catch (e) { /* ignore */ } }
      };
    }
    const sig = (id) => [editing === id ? "e" : "", noteOf(id)].join(":");
    return { html, bind, keep, sig, editing: () => editing };
  }

  // ---- screen state ----
  let root = null, sel = null, lastDay, memo = "", dirty = true;
  let adjOpen = false;   // "Ajustar o dia ›" open (per visit; closes after forgetting or recalibrating)
  const notes = noteBox("days", () => rerender());
  const isOn = () => GK.router.current() === "days";

  // ---- wheel: ring + medallions (HTML buttons over an SVG), Gluttony at 12 o'clock, counter-clockwise ----
  const R_RING = 33, R_OUT = 40.5;   // % of the wheel box
  // "Dia da Gula" -> "Gula", "Day of Gluttony" -> "Gluttony": the label beside each medallion
  const shortName = (d) => { const n = name(d.name); return n.replace(/^(dia d[aoe]s?|day of)\s+/i, "") || n; };
  const angle = (i, n) => -Math.PI / 2 - i * ((2 * Math.PI) / n);
  const at = (r, a) => [50 + r * Math.cos(a), 50 + r * Math.sin(a)].map((v) => Math.round(v * 100) / 100);
  function wheel(w, state) {
    const n = w.days.length, cur = current(state);
    const meds = w.days.map((d, i) => {
      const isSel = d.id === sel, isToday = !!cur && d.id === cur.id;
      const [x, y] = at(isToday ? R_OUT : R_RING, angle(i, n));
      const label = t(isToday ? "days.medToday" : "days.med", { name: name(d.name), n: d.events.length });
      // the short name under (lower half) or above (upper half) the medallion, so the colours are never the only cue
      const tag = `<span class="days-med-name${y < 50 ? " is-up" : ""}${isSel ? " is-sel" : ""}${isToday ? " is-today" : ""}" data-day="${esc(d.id)}" aria-hidden="true" style="left:${x}%;top:${y}%">${esc(shortName(d))}</span>`;
      return `<button type="button" class="days-med${isSel ? " is-sel" : ""}${isToday ? " is-today" : ""}${spritePos(d) ? " has-ico" : ""}" id="days-med-${esc(d.id)}" data-day="${esc(d.id)}" aria-pressed="${isSel}" aria-label="${esc(label)}" title="${esc(name(d.name))}" style="left:${x}%;top:${y}%${d.color ? `;--day:${esc(d.color)}` : ""}">${medal(d, isToday ? 60 : 50)}</button>${tag}`;
    }).join("");
    let arrow = "";
    if (cur) {
      const a = angle(w.days.indexOf(cur), n);
      const tip = at(R_OUT - 11, a), b1 = at(R_RING - 9, a - 0.2), b2 = at(R_RING - 9, a + 0.2), h0 = at(13, a), h1 = at(R_RING - 9, a);
      arrow = `<line class="days-hand" x1="${h0[0]}" y1="${h0[1]}" x2="${h1[0]}" y2="${h1[1]}"/>
        <polygon class="days-arrow" points="${tip.join(",")} ${b1.join(",")} ${b2.join(",")}"/>`;
    }
    const hub = state.dayNumber != null ? `<text class="days-hub-n" x="50" y="50.5" text-anchor="middle" dominant-baseline="middle">${esc(num(state.dayNumber))}</text>`
      : cur ? "" : `<text class="days-hub-n days-hub-q" x="50" y="51" text-anchor="middle" dominant-baseline="middle">?</text>`;
    return `<div class="days-wheel" role="group" aria-label="${esc(t("days.wheel"))}">
      <svg class="days-wheel-bg" viewBox="0 0 100 100" aria-hidden="true" focusable="false">
        <circle class="days-band" cx="50" cy="50" r="${R_RING}"/>
        <circle class="days-band-edge" cx="50" cy="50" r="${R_RING + 8.5}"/><circle class="days-band-edge" cx="50" cy="50" r="${R_RING - 8.5}"/>
        ${arrow}
        <circle class="days-hub" cx="50" cy="50" r="13"/>${hub}
      </svg>
      ${meds}
    </div>`;
  }

  // ---- "Hoje" bar: current day, counter + calibration, advance, "Ajustar o dia ›" (forget, recalibrate) ----
  function todayBar(state) {
    const cur = current(state), a = state.dayAnchor, ad = a ? day(a.day) : null;
    const head = cur ? `${tile(cur, 30)}<p class="days-tb-line"><b>${esc(t("days.todayIs", { name: name(cur.name) }))}</b>${state.dayNumber != null ? ` · <span class="tabnum">${esc(t("days.counter", { n: state.dayNumber }))}</span>` : ""}</p>`
      : `<p class="days-tb-line"><b>${esc(t("days.todayUnset"))}</b><span class="days-tb-sub">${esc(t("days.todayUnsetHint"))}</span></p>`;
    // calibrated: nothing to say (the toast said it once); else how to calibrate
    const cal = a && ad ? "" : `<p class="days-cal">${esc(t("days.calibrateHint"))}</p>`;
    // the two rare controls, one tap away
    const rare = [cur ? `<button type="button" class="btn btn-ghost btn-sm" id="days-forget" data-forget>${esc(t("days.forget"))}</button>` : "",
      a && ad ? `<button type="button" class="btn btn-ghost btn-sm" id="days-recal" data-recal>${esc(t("days.recalibrate"))}</button>` : ""].filter(Boolean);
    if (!rare.length) adjOpen = false;
    return `<section class="card days-tb" aria-labelledby="days-tb-h">
      <h3 class="sr-only" id="days-tb-h">${esc(cur ? t("days.todayIs", { name: name(cur.name) }) : t("days.todayUnset"))}</h3>
      <div class="days-tb-head">${head}</div>
      <div class="days-tb-ctl">
        <label class="days-num" for="days-num"><span class="days-num-l">${esc(t("days.number"))}</span>
          <input type="number" id="days-num" inputmode="numeric" min="1" max="99999" step="1" placeholder="${esc(t("days.numberPh"))}" value="${state.dayNumber != null ? state.dayNumber : ""}"${cal ? ` aria-describedby="days-cal-hint"` : ""}>
        </label>
        <button type="button" class="btn" id="days-adv" data-advance${cur ? "" : " disabled"}>${esc(t("days.advance"))} ›</button>
        ${rare.length ? `<button type="button" class="btn btn-ghost btn-sm days-adj" id="days-adj" data-adjust aria-expanded="${adjOpen}" aria-controls="days-adj-in">${esc(t("days.adjust"))} <span class="days-adj-chev" aria-hidden="true">›</span></button>` : ""}
      </div>
      ${rare.length ? `<div class="days-adj-in" id="days-adj-in"${adjOpen ? "" : " hidden"}>${rare.join("")}</div>` : ""}
      ${cal ? `<div id="days-cal-hint">${cal}</div>` : ""}
    </section>`;
  }

  // ---- the selected day's card ----
  function itemChips(ids, state) {
    const D = GK.data.get(), items = ids.map((id) => D.items[id]).filter(Boolean);
    if (!items.length) return "";
    const canOpen = GK.ui.recipes && typeof GK.ui.recipes.open === "function";
    return `<span class="days-items"><span class="sr-only">${esc(t("days.items"))}</span>${items.map((it) => {
      const nm = name(it, state.overrides);
      return canOpen ? `<button type="button" class="days-item" data-recipe-open="${esc(it.id)}" aria-label="${esc(t("info.label", { name: nm }))}">${GK.util.slot(it, nm, true)}<span>${esc(nm)}</span></button>`
        : `<span class="days-item">${GK.util.slot(it, nm, true)}<span>${esc(nm)}</span></span>`;
    }).join("")}</span>`;
  }
  // what goes under an event's line, shared by the Dias card and the Hoje panel's opened row (ui/today.js):
  // "com X · depois da missão", the longer detail, the item chips and the official game text (folded in a
  // <details> here; quoteOpen = shown as an open block, the Hoje row being already the thing the player opened)
  function eventMore(ev, state, quoteOpen) {
    const who = whoText(ev);
    const unlock = ev.unlock ? (ev.unlock.key ? t("days.unlockQuest", { q: name(ev.unlock) }) : name(ev.unlock)) : "";
    const sub = [who ? t("days.who", { who }) : "", unlock].filter(Boolean).join(" · ");
    const quote = !ev.quote ? "" : quoteOpen ? `<span class="days-quote is-open"><span class="days-quote-l">${esc(t("days.quote"))}</span><q>${esc(name(ev.quote))}</q></span>`
      : `<details class="days-quote"><summary title="${esc(t("days.quote"))}" aria-label="${esc(t("days.quote"))}"><span aria-hidden="true">“</span></summary><q>${esc(name(ev.quote))}</q></details>`;
    return `${sub ? `<span class="days-ev-who">${esc(sub)}</span>` : ""}
      ${ev.detail ? `<span class="days-ev-detail">${esc(name(ev.detail))}</span>` : ""}
      ${itemChips(ev.items, state)}
      ${quote}`;
  }
  function eventLi(ev, state) {
    const tipParts = [ev.source ? t("days.source", { src: ev.source }) : "", ev.also.length ? t("days.also", { src: ev.also.join(", ") }) : ""].filter(Boolean);
    return `<li class="days-ev${ev.confidence !== "high" ? " is-unsure" : ""}"${tipParts.length ? ` title="${esc(tipParts.join("\n"))}"` : ""}>
      <span class="days-ev-text">${esc(eventText(ev))}${confidenceBadge(ev)}</span>
      ${eventMore(ev, state, false)}
    </li>`;
  }
  function eventsByKind(d, state) {
    if (!d.events.length) return `<p class="hint days-nothing">${esc(t("days.nothing"))}</p>`;
    return KINDS.filter((k) => d.events.some((e) => e.kind === k)).map((k) => `<section class="days-group">
        <h3 class="days-group-h">${kindIcon(k, 18)}<span>${esc(t("days.kind." + k))}</span></h3>
        <ul class="days-evs">${d.events.filter((e) => e.kind === k).map((e) => eventLi(e, state)).join("")}</ul>
      </section>`).join("");
  }
  function card(d, state) {
    const cur = current(state), isToday = !!cur && cur.id === d.id, lang = GK.i18n.lang();
    const unofficial = lang !== "en" && (d.tr === "machine" || d.tr === "guess") ? `<span class="badge">${esc(t("badge.unofficial"))}</span>` : "";
    return `<article class="card days-card" aria-labelledby="days-card-h"${d.color ? ` style="--day:${esc(d.color)}"` : ""}>
      <header class="days-card-head">
        ${tile(d, 40, "days-tile-lg")}
        <div class="days-card-title">
          <h2 id="days-card-h">${esc(name(d.name))}${isToday ? `<span class="badge days-today-badge">${esc(t("days.todayBadge"))}</span>` : ""}${unofficial}</h2>
          <span class="row-sub">${esc(t("days.count", { n: d.events.length }))}</span>
        </div>
      </header>
      <div class="days-note-box">${notes.html(d, state)}</div>
      <div class="days-card-body">${eventsByKind(d, state)}</div>
      ${isToday ? "" : `<div class="days-ctl">
        <button type="button" class="btn" id="days-set" data-set-day="${esc(d.id)}">${esc(t("days.setToday"))}</button>
      </div>`}
    </article>`;
  }
  // ---- compact week table ----
  function table(w, state) {
    const cur = current(state);
    return `<section class="days-week" aria-labelledby="days-week-h">
      <h3 class="tech-col" id="days-week-h"><span>${esc(t("days.week"))}</span></h3>
      <div class="card list days-rows">${w.days.map((d) => {
        const sum = d.events.length ? d.events.map(eventText).join(" · ") : t("days.nothing");
        const isToday = !!cur && cur.id === d.id;
        return `<button type="button" class="days-row${d.id === sel ? " is-sel" : ""}${isToday ? " is-today" : ""}" id="days-row-${esc(d.id)}" data-day="${esc(d.id)}" aria-pressed="${d.id === sel}">
          ${tile(d, 30)}
          <span class="days-row-main"><span class="days-row-name">${esc(name(d.sin))}${isToday ? `<span class="badge days-today-badge">${esc(t("days.todayBadge"))}</span>` : ""}</span>
          <span class="days-row-sum">${esc(sum)}</span></span>
          <span class="days-row-n tabnum" aria-hidden="true">${d.events.length}</span>
        </button>`;
      }).join("")}</div>
    </section>`;
  }
  function howHtml(w) {
    const m = w.meta, parts = [m.notes, m.orderNote, m.greed].filter(Boolean).map((x) => `<p>${esc(name(x))}</p>`);
    if (!m.orderNote && m.orderConfidence && m.orderConfidence !== "official") parts.push(`<p class="days-unsure">${esc(t("days.orderUnsure"))}</p>`);
    // the app's own short lines, when some day quotes the game's text beside them
    if (w.days.some((d) => d.events.some((e) => e.tr === "machine" && e.quote))) parts.push(`<p class="days-mt">${esc(t("days.machineNote"))}</p>`);
    return parts.length ? `<details class="days-how"><summary>${esc(t("days.how"))}</summary>${parts.join("")}</details>` : "";
  }

  function render(state) {
    if (!root) return;
    if (!isOn()) { dirty = true; return; }
    const w = week();
    if (!w) {
      if (memo !== "none") { root.innerHTML = `<div class="card empty"><p>${esc(t("days.empty"))}</p></div>`; memo = "none"; }
      return;
    }
    // follow the current day when it moves (advance / counter / set elsewhere) and the selection was on it, or when
    // a day is set after none was
    const curId = current(state) ? state.day : null;
    if (curId !== lastDay) { if (!sel || !lastDay || sel === lastDay) sel = curId || sel; lastDay = curId; }
    if (!sel || !day(sel)) sel = curId || w.days[0].id;
    const a = state.dayAnchor;
    const sig = [sel, curId, state.dayNumber, a ? a.number + a.day : "", GK.i18n.lang(), JSON.stringify(state.overrides[GK.i18n.lang()] || {}), notes.sig(sel)].join("|");
    if (!dirty && sig === memo) return;
    dirty = false; memo = sig;
    const open = [...root.querySelectorAll("details")].filter((x) => x.open).map((x) => x.dataset.k);
    const typed = notes.keep();
    root.innerHTML = `<div class="days-screen">
      <div class="days-head">
        <div class="section-head"><h2 class="h2">${esc(t("days.title"))}</h2></div>
        ${howHtml(w)}
      </div>
      <div class="days-wheel-box">${wheel(w, state)}${todayBar(state)}</div>
      <div class="days-detail">${card(day(sel), state)}</div>
      <div class="days-table">${table(w, state)}</div>
    </div>`;
    // keep open <details> open across re-renders (same position = same key)
    root.querySelectorAll("details").forEach((x, i) => { x.dataset.k = sel + ":" + i; if (open.indexOf(x.dataset.k) >= 0) x.open = true; });
    typed();
  }
  // re-render keeping focus on the element that had it (same id)
  function rerender() {
    const act = document.activeElement && root.contains(document.activeElement) ? document.activeElement.id : null;
    dirty = true; render(GK.store.get(), {});
    if (act) { const el = document.getElementById(act); if (el) el.focus({ preventScroll: true }); }
  }
  function select(id) { if (day(id)) { sel = id; rerender(); } }
  function setToday(id) {
    const d = day(id);
    if (!d) return;
    const before = GK.store.get().dayAnchor;
    GK.store.actions.setDay(id);
    const st = GK.store.get(), a = st.dayAnchor;
    if (a && (!before || before.number !== a.number || before.day !== a.day)) GK.ui.toast(t("days.calToast", { n: a.number, name: name(d.name) }));
    else GK.ui.toast(st.dayNumber != null ? t("days.setToastN", { name: name(d.name), n: st.dayNumber }) : t("days.setToast", { name: name(d.name) }));
  }
  function advance() {
    if (!GK.store.actions.advanceDay()) return;
    const st = GK.store.get(), d = current(st);
    if (d) GK.ui.toast(st.dayNumber != null ? t("days.advToastN", { name: name(d.name), n: st.dayNumber }) : t("days.advToast", { name: name(d.name) }));
  }
  function mount(el) {
    root = el;
    notes.bind(root);
    root.addEventListener("click", (e) => {
      if (e.target.closest("[data-note-edit]")) return;   // noteBox
      const ro = e.target.closest("[data-recipe-open]");
      if (ro) { GK.ui.recipes.open(ro.dataset.recipeOpen, { from: "days" }); return; }
      const s = e.target.closest("[data-set-day]");
      if (s) { setToday(s.dataset.setDay); return; }
      if (e.target.closest("[data-advance]")) { advance(); return; }
      if (e.target.closest("[data-adjust]")) { adjOpen = !adjOpen; rerender(); return; }
      if (e.target.closest("[data-recal]")) {
        adjOpen = false;
        GK.store.actions.clearAnchor(); GK.ui.toast(t("days.recalToast"));
        const f = root.querySelector("#days-num"); if (f) f.focus({ preventScroll: true });
        return;
      }
      if (e.target.closest("[data-forget]")) {
        adjOpen = false;
        GK.store.actions.setDay(null); GK.ui.toast(t("days.forgotToast"));
        const b = root.querySelector("#days-set"); if (b) b.focus({ preventScroll: true });
        return;
      }
      const d = e.target.closest("[data-day]");
      if (d) select(d.dataset.day);
    });
    root.addEventListener("keydown", (e) => {
      const m = e.target.closest && e.target.closest(".days-med");
      if (!m) return;
      // arrows walk the wheel in cycle order (right/down = next day)
      const step = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
      const w = week(), i = w ? w.days.findIndex((x) => x.id === m.dataset.day) : -1;
      if (!step || i < 0) return;
      e.preventDefault();
      sel = w.days[(i + step + w.days.length) % w.days.length].id;
      dirty = true; render(GK.store.get(), {});
      const nx = document.getElementById("days-med-" + sel);
      if (nx) nx.focus({ preventScroll: true });
    });
    // the HUD counter: calibrated -> sets the day too; else calibrates with today's day, or is kept alone
    root.addEventListener("change", (e) => {
      if (e.target.id !== "days-num") return;
      const before = GK.store.get().dayAnchor;
      GK.store.actions.setDayNumber(e.target.value);
      numberToast(before);
    });
  }
  function open(id) {
    // the requested day stays selected even on the first visit (the "follow today" rule in render must not take it)
    if (day(id)) { sel = id; const st = GK.store.get(); lastDay = current(st) ? st.day : null; }
    dirty = true;
    if (isOn()) { render(GK.store.get(), {}); window.scrollTo(0, 0); return; }
    GK.router.forget("days");   // opens at the top, not where the Dias screen was left
    location.hash = "#days";
    window.scrollTo(0, 0);
  }
  return { mount, render, open, week, day, current, next, noteBox, glyph, medal, kindIcon, kinds: KINDS, eventText, whoText, confidenceBadge, eventMore, tile, numberToast };
})();

GK.router.register({ id: "days", labelKey: "tab.days", screen: "days", order: 40 });
GK.app.registerPanel(GK.ui.days, { id: "days", panel: "days", order: 72 });
