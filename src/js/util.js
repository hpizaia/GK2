/* GK.util: small shared helpers (HTML escaping, DOM ids, icon slots from the sprite, clipboard, debounce).
   Owns: the icon sprite <style> rule and the broken-image fallback listener.
   Exposes: GK.util.{esc, domId, slot, setSprite, copyText, debounce}.
   slot(ent, label, small, grade) (1.8.0): an item with a quality grade (item.grade, or the grade a recipe line gives
   it: the bronze Cabbage of "… from Cabbage (bronze)") gets the pixel star in its icon's top-left corner (.qstar
   q-b / q-s / q-g, components.css), out of the way of a stack number. The one place that draws it. The plain item of
   a graded family is the bronze one (item.grade "bronze", GK.data bronzePlain); grade = false draws no star (an
   "Any X" line, or a row that stands for the whole family).
*/
GK.util = (function () {
  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ESC[c]);
  const domId = (s) => String(s).replace(/[^a-zA-Z0-9_-]/g, "_");
  const failedIcons = new Set();
  let sprite = null; // { icons: {id: [col, row]} } once setSprite() ran
  // One <style> rule carries the sheet (a data: URI), so each icon is just a positioned <span>.
  function setSprite(sp) {
    if (!sp || !sp.image || !sp.icons) return;
    sprite = sp;
    const st = document.createElement("style");
    st.id = "gk-sprite";
    st.textContent = `.ico{background-image:url("${String(sp.image).replace(/["\\\s]/g, "")}");--cols:${+sp.cols || 1}}`;
    document.head.appendChild(st);
  }
  const letterTile = (cls, letter) => `<span class="${cls}"><span class="slot-letter" aria-hidden="true">${letter}</span></span>`;
  const STAR = { bronze: "q-b", silver: "q-s", gold: "q-g" };
  // ent = item or station ({id, icon}); label = shown name (for the letter fallback); grade = a line's grade (else
  // ent.grade; false = no star)
  function slot(ent, label, small, grade) {
    const letter = esc((String(label || "?").trim()[0] || "?").toUpperCase());
    const q = grade === false ? "" : STAR[grade || (ent && ent.grade)] || "";
    const cls = "slot" + (small ? " slot-sm" : "") + (q ? " has-q" : "");
    const star = q ? `<span class="qstar ${q}" aria-hidden="true"></span>` : "";
    const pos = ent && sprite && sprite.icons[ent.id];
    if (pos) return `<span class="${cls}"><span class="ico" style="--x:${+pos[0]};--y:${+pos[1]}"></span>${star}</span>`;
    const icon = ent && ent.icon;
    if (icon && !failedIcons.has(icon)) {
      return `<span class="${cls}"><img src="${esc(icon)}" alt="" loading="lazy" decoding="async" width="32" height="32" data-fb="${letter}">${star}</span>`;
    }
    return star ? `<span class="${cls}"><span class="slot-letter" aria-hidden="true">${letter}</span>${star}</span>` : letterTile(cls, letter);
  }
  // Broken remote icons (blocked host, 404, offline) fall back to the letter tile.
  document.addEventListener("error", (e) => {
    const img = e.target;
    if (!img || img.tagName !== "IMG" || !img.dataset.fb) return;
    failedIcons.add(img.getAttribute("src"));
    const s = document.createElement("span");
    s.className = "slot-letter"; s.setAttribute("aria-hidden", "true"); s.textContent = img.dataset.fb;
    img.replaceWith(s);
  }, true);
  // Clipboard with a selectable <textarea> fallback (clipboard API is often blocked in iframes).
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (e) { /* fall through */ }
    try {
      const ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;top:0;left:0;opacity:0";
      document.body.appendChild(ta); ta.select();
      const ok = document.execCommand && document.execCommand("copy");
      ta.remove();
      return !!ok;
    } catch (e) { return false; }
  }
  function debounce(fn, ms) { let t = null; return function () { const a = arguments; clearTimeout(t); t = setTimeout(() => fn.apply(null, a), ms); }; }
  return { esc, domId, slot, setSprite, copyText, debounce };
})();
