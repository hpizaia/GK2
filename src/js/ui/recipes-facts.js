/* GK.ui.rcFacts: the item facts of the Receitas detail (GK.ui.recipes), from data/facts.json via the build:
   "Onde conseguir" (items[].where), the game-style use tooltip (items[].use) and the stack (items[].stack), "Quem
   compra" (items[].sell / .price / .fix), "Estudar" (items[].study, state.studied) and "Pedido em" (items[].asked).
   No state, no panel: the detail passes what it keeps ("mais N" open in whereHtml, "Pedido em" open in askedHtml).
   Exposes: GK.ui.rcFacts.{whereHtml, tipHtml, stackSlot, stackCap, sellHtml, studyHtml, askedHtml}.
   Each block returns "" when the item has no data for it. Texts: the rc.* keys of src/js/i18n/pt.js and en.js.
*/
GK.ui.rcFacts = (function () {
  const { t, name, num } = GK.i18n, { esc, slot } = GK.util, { UNOFFICIAL } = GK.ui.fmt;
  /* ---------- facts: "Onde conseguir", use tooltip, stack (data/facts.json via the build) ---------- */
  const WHERE_CAP = 4, MINUS = "−";
  const signed = (v) => (v < 0 ? MINUS + num(-v) : "+" + num(v));
  const refs = () => (GK.data.get().meta.refs || {});
  const unofficialBadge = (title) => (GK.i18n.lang() !== "en" ? `<span class="badge" title="${esc(title)}">${esc(t("rc.unofficial"))}</span>` : "");
  // a source name: "@item-id" (the app's item name) or a key of meta.refs.names ("x" or {pt, en, tr})
  function refName(ref, state) {
    if (typeof ref !== "string") return { txt: "" };
    if (ref[0] === "@") { const it = GK.data.item(ref.slice(1)); return { txt: it ? name(it, state.overrides) : ref.slice(1), tr: it && UNOFFICIAL[it.tr] }; }
    const e = (refs().names || {})[ref];
    if (e == null) return { txt: ref };
    return typeof e === "string" ? { txt: e } : { txt: name(e), tr: !!e.tr };
  }
  function whereLine(w, state) {
    const k = w[0], nm = refName(w[1], state);
    let what = esc(nm.txt), det = "";
    if (k === "buy") det = w[2] === "talk" ? t("rc.w.talk") : w[2] ? t("rc.w.level", { n: w[2] }) : "";
    else if (k === "fish" && w.length > 2) {
      const bait = w[2] === "no-bait" ? t("rc.w.noBait") : name(GK.data.item(w[2]) || { en: w[2] }, state.overrides);
      what += ", " + esc(bait);
      det = w[3] === w[4] ? t("rc.w.allDay", { d: num(w[3]) }) : t("rc.w.dayNight", { d: num(w[3]), n: num(w[4]) });
    } else if (k === "chest") det = t("rc.w.chestOnce");
    else if (k === "found") det = t("rc.w.once");
    const badge = nm.tr ? unofficialBadge(t("rc.w.unofficialTitle")) : "";
    return `<li><b class="rc-where-v">${esc(t("rc.w." + k))}:</b> ${what}${badge}${det ? ` <span class="rc-where-d">${esc(det)}</span>` : ""}</li>`;
  }
  // whereAll: "mais N" was tapped (the detail keeps it until another item opens)
  function whereHtml(it, rs, state, whereAll) {
    const w = Array.isArray(it.where) ? it.where.filter((x) => Array.isArray(x) && x.length > 1) : [];
    if (!w.length) return "";
    const shown = whereAll ? w : w.slice(0, WHERE_CAP), rest = w.length - shown.length;
    const questOnly = !rs.length && w.every((x) => x[0] === "quest");
    return `<div class="rc-info rc-where"><h3 class="rc-k">${esc(t("rc.where"))}</h3>
      ${questOnly ? `<p class="rc-where-only"><span class="badge badge-warn" title="${esc(t("rc.questOnlyTitle"))}">${esc(t("rc.questOnly"))}</span></p>` : ""}
      <ul class="rc-where-list">${shown.map((x) => whereLine(x, state)).join("")}</ul>
      ${rest > 0 ? `<button type="button" class="btn btn-sm btn-ghost rc-where-more" id="rc-where-more" data-where-more aria-label="${esc(t("rc.whereMoreLabel", { n: rest }))}">${esc(t("rc.whereMore", { n: rest }))}</button>` : ""}
    </div>`;
  }
  function duration(secs) {
    const m = Math.floor(secs / 60), s = secs % 60;
    return [m ? `${num(m)} min` : "", s ? `${num(s)} s` : ""].filter(Boolean).join(" ");
  }
  function buffName(key) {
    const b = (refs().buffs || {})[key];
    return b ? { b, txt: name(b) } : { b: null, txt: key };
  }
  // the game's item tooltip: "Efeito de uso: (bolt) +20", the HUD-like energy bar, the boosted value, the buff
  function tipHtml(it) {
    const u = it.use;
    if (!u || typeof u !== "object") return "";
    const en = typeof u.en === "number" ? u.en : null, ins = typeof u.ins === "number" ? u.ins : null;
    const vals = [];
    if (en != null) vals.push(`<span class="gk-val gk-en"><span class="gk-bolt" role="img" aria-label="${esc(t("rc.energyName"))}"></span>${esc(signed(en))}</span>`);
    if (ins != null) vals.push(`<span class="gk-val gk-ins">${esc(signed(ins))} <small>${esc(t("rc.insanityName"))}</small></span>`);
    const parts = [];
    if (vals.length) parts.push(`<p class="gk-eff"><span class="gk-lbl">${esc(t("rc.useLbl"))}</span> ${vals.join(" ")}</p>`);
    if (en != null && en > 0) {
      const pct = (v) => Math.max(0, Math.min(100, v)) / 100;
      const boost = Array.isArray(u.enB) && typeof u.enB[0] === "number" ? u.enB : null;
      const plus = boost && boost[0] > en ? pct(boost[0]) - pct(en) : 0;
      parts.push(`<div class="gk-bar" role="img" aria-label="${esc(t("rc.barLabel", { n: en }))}">
        <span class="gk-bar-ico"><span class="gk-bolt"></span></span>
        <span class="gk-bar-track"><span class="gk-bar-empty"></span><span class="gk-bar-fill" style="width:calc((100% - 6px) * ${pct(en)})"></span>${plus > 0 ? `<span class="gk-bar-plus" style="left:calc(3px + (100% - 6px) * ${pct(en)});width:calc((100% - 6px) * ${plus.toFixed(3)})"></span>` : ""}<span class="gk-bar-ticks"></span></span>
      </div>`);
    }
    const notes = [];
    if (en != null && en > 0) notes.push(esc(t("rc.bar", { n: en })));
    for (const [f, base] of [["enB", en], ["insB", ins]]) {
      const b = u[f];
      if (!Array.isArray(b) || typeof b[0] !== "number" || base == null) continue;
      const bn = buffName(b[1]);
      notes.push(t("rc.boost", { v: `<b>${esc(f === "enB" ? num(b[0]) : signed(b[0]))}</b>`, buff: `<b${bn.b && bn.b.d ? ` title="${esc(name(bn.b.d))}"` : ""}>${esc(bn.txt)}</b>` }));
    }
    if (notes.length) parts.push(`<p class="gk-note">${notes.join(" · ")}</p>`);
    if (Array.isArray(u.buff) && u.buff.length) {
      const bn = buffName(u.buff[0]), secs = typeof u.buff[1] === "number" ? u.buff[1] : null;
      const d = bn.b && bn.b.d ? name(bn.b.d) : "";
      const time = [secs ? esc(t("rc.lasts", { t: "\u0000" })).replace("\u0000", `<b>${duration(secs)}</b>`) : "", u.buff[2] ? esc(t("rc.restart")) : ""].filter(Boolean).join(" ");
      if (parts.length) parts.push(`<div class="gk-rule" aria-hidden="true"></div>`);
      parts.push(`<div class="gk-buff"><span class="gk-buff-ico" aria-hidden="true"></span><div>
        <p class="gk-buff-name">${esc(bn.txt)}${bn.b && bn.b.tr ? unofficialBadge(t("rc.w.unofficialTitle")) : ""}</p>
        ${d ? `<p class="gk-buff-d">${esc(d)}${bn.b.dtr ? unofficialBadge(t("rc.descUnofficial")) : ""}</p>` : ""}
        ${time ? `<p class="gk-buff-t">${time}</p>` : ""}
      </div></div>`);
    }
    return parts.length ? `<div class="gk-tip">${parts.join("")}</div>` : "";
  }
  // the big item slot with the stack in its corner (as the game prints the count), + one caption line
  function stackSlot(it, nm) {
    const html = slot(it, nm), st = typeof it.stack === "number" && it.stack > 0 ? it.stack : null;
    if (!st || st < 2) return html;
    return html.replace(/^<span class="(slot[^"]*)"/, `<span class="$1" title="${esc(t("rc.stackTitle", { n: st }))}"`)
      .replace(/<\/span>$/, `<span class="stack-n tabnum" aria-hidden="true">${esc(num(st))}</span></span>`);
  }
  function stackCap(it) {
    const st = typeof it.stack === "number" && it.stack > 0 ? it.stack : null;
    if (!st) return "";
    return `<p class="stack-cap">${st > 1 ? esc(t("rc.stack", { n: "\u0000" })).replace("\u0000", `<b>${esc(num(st))}</b>`) : esc(t("rc.stackOne"))}</p>`;
  }
  /* ---------- "Quem compra", "Estudar", "Pedido em" ---------- */
  const int = (v) => (typeof v === "number" && isFinite(v) ? Math.round(v) : 0);
  // an amount in bronze (1 silver = 100 bronze, 1 gold = 100 silver) as the game's coins: (s)1 (b)37
  function coins(v) {
    const parts = [["g", Math.floor(v / 10000)], ["s", Math.floor(v / 100) % 100], ["b", v % 100]].filter((p) => p[1]);
    return parts.map(([k, n]) => `<span class="coin coin-${k}" aria-hidden="true"></span>${esc(num(n))}<span class="sr-only"> ${esc(t("rc.coin." + k))}</span>`).join(" ");
  }
  // lo–hi: one bronze coin when both are under 1 silver ("54–56"), else each amount in full
  function coinRange(lo, hi) {
    if (!hi || hi === lo) return coins(lo);
    if (hi < 100) return `<span class="coin coin-b" aria-hidden="true"></span>${esc(num(lo))}–${esc(num(hi))}<span class="sr-only"> ${esc(t("rc.coin.b"))}</span>`;
    return `${coins(lo)} – ${coins(hi)}`;
  }
  function sellHtml(it, state) {
    const rows = Array.isArray(it.sell) ? it.sell.filter((e) => Array.isArray(e) && typeof e[0] === "string") : [];
    if (!rows.length) return "";
    const base = int(it.price) > 0 ? int(it.price) : 0, fix = !!it.fix && base > 0;
    const li = rows.map((e) => {
      const nm = refName(e[0], state), lo = int(e[1]), hi = int(e[2]), likes = int(e[3]), likeLv = int(e[4]), lvl = int(e[5]);
      let pay = "";
      if (fix) pay = coins(base);
      else if (lo > 0) pay = coinRange(lo, hi) + (base > Math.max(lo, hi) ? ` <span class="sell-max">${esc(t("rc.sellUpTo", { v: "\u0000" })).replace("\u0000", coins(base))}</span>` : "");
      else if (base) pay = `<span class="sell-max">${esc(t("rc.sellUpTo", { v: "\u0000" })).replace("\u0000", coins(base))}</span>`;
      const d = [];
      if (fix) d.push(t("rc.sellFix"));
      if (likes > 0) d.push(likeLv > 1 ? t("rc.sellLikesFrom", { n: num(likes), lv: likeLv }) : t("rc.sellLikes", { n: num(likes) }));
      else if (likes < 0) d.push(likeLv > 1 ? t("rc.sellLikesAnyFrom", { lv: likeLv }) : t("rc.sellLikesAny"));
      if (lvl > 1) d.push(t("rc.sellLevel", { n: lvl }));
      const badge = nm.tr ? unofficialBadge(t("rc.w.unofficialTitle")) : "";
      return `<li><span class="sell-who">${esc(nm.txt)}${badge}</span><span class="sell-pay tabnum">${pay}</span>${d.length ? `<span class="sell-d">${esc(d.join(" · "))}</span>` : ""}</li>`;
    }).join("");
    const note = fix ? esc(t("rc.sellNoteFix", { n: "\u0000" })).replace("\u0000", coins(base)) : esc(t("rc.sellNote"));
    return `<div class="rc-info rc-sell">
      <div class="rc-k-row"><h3 class="rc-k" id="rc-sell-h">${esc(t("rc.sell"))}</h3>
        <details class="rc-i"><summary aria-label="${esc(t("rc.sellInfo"))}" title="${esc(t("rc.sellInfo"))}"><span aria-hidden="true">i</span></summary>
          <p class="rc-i-p">${note}</p></details></div>
      <ul class="sell-list" aria-labelledby="rc-sell-h">${li}</ul>
    </div>`;
  }
  function studyHtml(it, state, id) {
    const st = Array.isArray(it.study) ? it.study.map(int) : [];
    if (!st.length || !st.some((v) => v > 0)) return "";
    const [red, green, blue, sci, faith] = [0, 1, 2, 3, 4].map((i) => st[i] || 0);
    const cost = { red, green, blue };
    // the point gems of "Tecnologias que faltam" (GK.ui.tech.costHtml)
    const pts = (red || green || blue) && GK.ui.tech && GK.ui.tech.costHtml ? GK.ui.tech.costHtml(cost, { big: true }) : "";
    const on = Array.isArray(state.studied) && state.studied.indexOf(id) >= 0;
    const nm = name(it, state.overrides);
    const costTxt = sci || faith ? " " + t(faith ? "rc.studyCostFaith" : "rc.studyCost", { sci: num(sci), faith: num(faith) }) : "";
    return `<div class="rc-info rc-study">
      <h3 class="rc-k">${esc(t("rc.study"))}</h3>
      <div class="study-row">${pts}
        <label class="study-done" for="rc-studied"><span class="tick"><input type="checkbox" id="rc-studied" data-studied="${esc(id)}"${on ? " checked" : ""} aria-label="${esc(t("rc.studiedLabel", { name: nm }))}"></span>${esc(t("rc.studied"))}</label></div>
      <p class="study-d">${esc(t("rc.studyNote") + costTxt)}</p>
    </div>`;
  }
  function askedLine(mark, qty, nameHtml, note) {
    return `<li><div class="rc-line rc-line-static"><span class="slot slot-sm asked-mark"><span class="slot-letter" aria-hidden="true">${mark}</span></span><span class="rc-line-q tabnum">${esc(num(qty))}<small>×</small></span>
      <span class="rc-line-main"><span class="rc-line-name">${nameHtml}</span>${note ? `<span class="rc-line-note">${note}</span>` : ""}</span></div></li>`;
  }
  // askedOpen: "Pedido em" unfolded (the detail keeps it until another item opens)
  function askedHtml(it, state, askedOpen) {
    const a = it.asked && typeof it.asked === "object" ? it.asked : {};
    const rows = (k) => (Array.isArray(a[k]) ? a[k].filter((e) => Array.isArray(e) && typeof e[0] === "string") : []);
    const nameOf = (ref) => { const nm = refName(ref, state); return esc(nm.txt) + (nm.tr ? unofficialBadge(t("rc.w.unofficialTitle")) : ""); };
    const q = rows("q"), town = rows("t"), ord = rows("o");
    const other = town.length + ord.length, total = q.length + other;
    if (!total) return "";
    const group = (k) => `<li class="asked-g" aria-hidden="true">${esc(t(k))}</li>`;
    const lines = [];
    if (q.length) {
      lines.push(group("rc.askedQ"));
      for (const e of q) lines.push(askedLine("!", int(e[1]) || 1, nameOf(e[0]), typeof e[2] === "string" ? nameOf(e[2]) : ""));
    }
    if (town.length) {
      lines.push(group("rc.askedTown"));
      for (const e of town) lines.push(askedLine("+", int(e[1]) || 1, nameOf(e[0]), ""));
    }
    if (ord.length) {
      lines.push(group("rc.askedOrder"));
      for (const e of ord) {
        const d = [int(e[2]) > 1 ? t("rc.askedLevel", { n: int(e[2]) }) : "", int(e[3]) > 0 ? t("rc.askedLikes", { n: num(int(e[3])) }) : ""].filter(Boolean);
        lines.push(askedLine("+", int(e[1]) || 1, nameOf(e[0]), esc(d.join(" · "))));
      }
    }
    const show = q.length && other ? t("rc.askedShowQO", { n: q.length, o: other }) : q.length ? t("rc.askedShowQ", { n: q.length }) : t("rc.askedShowO", { n: other });
    return `<section class="rc-sec" aria-labelledby="rc-asked-h">
      <h3 class="h2" id="rc-asked-h">${esc(t("rc.asked"))} <span class="count">${total}</span></h3>
      <details class="card list rc-asked" id="rc-asked"${askedOpen ? " open" : ""}>
        <summary><span class="asked-t"><span class="asked-show">${esc(show)}</span><span class="asked-hide">${esc(t("rc.askedHide"))}</span></span>
          ${q.length ? `<span class="asked-warn">${esc(t("rc.askedWarn"))}</span>` : ""}<span class="rc-chev" aria-hidden="true">›</span></summary>
        <ul class="rc-lines">${lines.join("")}</ul>
      </details>
    </section>`;
  }
  return { whereHtml, tipHtml, stackSlot, stackCap, sellHtml, studyHtml, askedHtml };
})();
