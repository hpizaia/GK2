/* GK.ui.qr: a small QR code generator in plain JS (byte mode, error correction M, versions 1 to 6 = up to 106 bytes,
   the mask with the lowest penalty), from the ideia-21 prototype, checked with the macOS QR reader (CoreImage).
   Used by ui/credits.js for the "open on your phone" card on wide screens. No state, no panel, no texts.
   Exposes: GK.ui.qr.{matrix(text) -> rows of booleans (true = dark), svg(text, label) -> an <svg> string with a
   4-module quiet zone, dark modules on a fixed light ground (readable in both themes)}.
*/
GK.ui.qr = (function () {
  function qr(text) {
    const ECC = [0, 10, 16, 26, 18, 24, 16], BLK = [0, 1, 1, 1, 2, 2, 4];
    const bytes = Array.from(new TextEncoder().encode(text));
    const raw = (v) => { let r = (16 * v + 128) * v + 64; if (v >= 2) { const n = Math.floor(v / 7) + 2; r -= (25 * n - 10) * n - 55; } return r; };
    const dataCap = (v) => Math.floor(raw(v) / 8) - ECC[v] * BLK[v];
    let ver = 1; while (ver <= 6 && 4 + 8 + bytes.length * 8 > dataCap(ver) * 8) ver++;
    if (ver > 6) throw new Error("texto longo demais");
    const size = ver * 4 + 17, cap = dataCap(ver) * 8;
    // bits: modo 0100, contagem (8 bits), dados, terminador, alinhamento ao byte, bytes de enchimento
    const bits = [];
    const put = (val, n) => { for (let i = n - 1; i >= 0; i--) bits.push((val >>> i) & 1); };
    put(4, 4); put(bytes.length, 8); bytes.forEach((b) => put(b, 8));
    put(0, Math.min(4, cap - bits.length)); put(0, (8 - bits.length % 8) % 8);
    for (let p = 0xEC; bits.length < cap; p ^= 0xEC ^ 0x11) put(p, 8);
    const data = []; for (let i = 0; i < bits.length; i += 8) data.push(parseInt(bits.slice(i, i + 8).join(""), 2));
    // Reed-Solomon em GF(256), polinômio 0x11D
    const mul = (x, y) => { let z = 0; for (let i = 7; i >= 0; i--) { z = (z << 1) ^ ((z >>> 7) * 0x11D); z ^= ((y >>> i) & 1) * x; } return z; };
    const div = (() => { const d = new Array(ECC[ver]).fill(0); d[d.length - 1] = 1; let root = 1;
      for (let i = 0; i < ECC[ver]; i++) { for (let j = 0; j < d.length; j++) { d[j] = mul(d[j], root); if (j + 1 < d.length) d[j] ^= d[j + 1]; } root = mul(root, 2); } return d; })();
    const rem = (dat) => { const r = div.map(() => 0); for (const b of dat) { const f = b ^ r.shift(); r.push(0); div.forEach((c, i) => { r[i] ^= mul(c, f); }); } return r; };
    // blocos e intercalação
    const nb = BLK[ver], rawCw = Math.floor(raw(ver) / 8), nShort = nb - rawCw % nb, shortLen = Math.floor(rawCw / nb);
    const blocks = [];
    for (let i = 0, k = 0; i < nb; i++) { const d = data.slice(k, k + shortLen - ECC[ver] + (i < nShort ? 0 : 1)); k += d.length; const e = rem(d); if (i < nShort) d.push(0); blocks.push(d.concat(e)); }
    const cw = [];
    for (let i = 0; i < blocks[0].length; i++) blocks.forEach((b, j) => { if (i !== shortLen - ECC[ver] || j >= nShort) cw.push(b[i]); });
    // padrões fixos
    const M = [], F = [];
    for (let y = 0; y < size; y++) { M.push(new Array(size).fill(false)); F.push(new Array(size).fill(false)); }
    const fn = (x, y, d) => { M[y][x] = d; F[y][x] = true; };
    for (let i = 0; i < size; i++) { fn(6, i, i % 2 === 0); fn(i, 6, i % 2 === 0); }
    const finder = (cx, cy) => { for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) { const x = cx + dx, y = cy + dy, d = Math.max(Math.abs(dx), Math.abs(dy)); if (x >= 0 && x < size && y >= 0 && y < size) fn(x, y, d !== 2 && d !== 4); } };
    finder(3, 3); finder(size - 4, 3); finder(3, size - 4);
    if (ver >= 2) { const n = Math.floor(ver / 7) + 2, step = Math.floor((ver * 8 + n * 3 + 5) / (n * 4 - 4)) * 2, pos = [6];
      for (let p = size - 7; pos.length < n; p -= step) pos.splice(1, 0, p);
      pos.forEach((ax, i) => pos.forEach((ay, j) => { if ((i === 0 && j === 0) || (i === 0 && j === n - 1) || (i === n - 1 && j === 0)) return;
        for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) fn(ax + dx, ay + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1); })); }
    const format = (mask) => { const d = (0 << 3) | mask; let r = d; for (let i = 0; i < 10; i++) r = (r << 1) ^ ((r >>> 9) * 0x537); const b = ((d << 10) | r) ^ 0x5412, g = (i) => ((b >>> i) & 1) === 1;
      for (let i = 0; i <= 5; i++) fn(8, i, g(i)); fn(8, 7, g(6)); fn(8, 8, g(7)); fn(7, 8, g(8)); for (let i = 9; i < 15; i++) fn(14 - i, 8, g(i));
      for (let i = 0; i < 8; i++) fn(size - 1 - i, 8, g(i)); for (let i = 8; i < 15; i++) fn(8, size - 15 + i, g(i)); fn(8, size - 8, true); };
    format(0);
    // dados em zigue-zague
    let bi = 0;
    for (let right = size - 1; right >= 1; right -= 2) { if (right === 6) right = 5;
      for (let v = 0; v < size; v++) for (let j = 0; j < 2; j++) { const x = right - j, up = ((right + 1) & 2) === 0, y = up ? size - 1 - v : v;
        if (!F[y][x] && bi < cw.length * 8) { M[y][x] = ((cw[bi >>> 3] >>> (7 - (bi & 7))) & 1) === 1; bi++; } } }
    const MASKS = [(x, y) => (x + y) % 2 === 0, (x, y) => y % 2 === 0, (x) => x % 3 === 0, (x, y) => (x + y) % 3 === 0,
      (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0, (x, y) => x * y % 2 + x * y % 3 === 0,
      (x, y) => (x * y % 2 + x * y % 3) % 2 === 0, (x, y) => ((x + y) % 2 + x * y % 3) % 2 === 0];
    const applyMask = (m) => { for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) if (!F[y][x] && MASKS[m](x, y)) M[y][x] = !M[y][x]; };
    const penalty = () => { let p = 0, dark = 0;
      const line = (get) => { for (let a = 0; a < size; a++) { let run = 1; const s = [];
        for (let b = 0; b < size; b++) { const c = get(a, b); s.push(c ? 1 : 0); if (b > 0) { if (c === get(a, b - 1)) { run++; if (run === 5) p += 3; else if (run > 5) p++; } else run = 1; } }
        const str = s.join(""); for (const pat of ["00001011101", "10111010000"]) { let i = str.indexOf(pat); while (i >= 0) { p += 40; i = str.indexOf(pat, i + 1); } } } };
      line((a, b) => M[a][b]); line((a, b) => M[b][a]);
      for (let y = 0; y < size - 1; y++) for (let x = 0; x < size - 1; x++) { const c = M[y][x]; if (c === M[y][x + 1] && c === M[y + 1][x] && c === M[y + 1][x + 1]) p += 3; }
      M.forEach((r) => r.forEach((c) => { if (c) dark++; }));
      return p + Math.floor(Math.abs(dark * 20 - size * size * 10) / (size * size)) * 10; };
    let best = 0, bestP = Infinity;
    for (let m = 0; m < 8; m++) { applyMask(m); format(m); const pp = penalty(); if (pp < bestP) { bestP = pp; best = m; } applyMask(m); }
    applyMask(best); format(best);
    return M;
  }
  function svg(text, label) {
    const M = qr(text), n = M.length, q = 4;
    let d = "";
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (M[y][x]) d += "M" + x + " " + y + "h1v1h-1z";
    const box = `${-q} ${-q} ${n + 2 * q} ${n + 2 * q}`;
    const a11y = label ? `role="img" aria-label="${GK.util.esc(label)}"` : 'aria-hidden="true"';
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${box}" shape-rendering="crispEdges" ${a11y}><rect x="${-q}" y="${-q}" width="${n + 2 * q}" height="${n + 2 * q}" fill="#fffaf0"/><path d="${d}" fill="#1d1309"/></svg>`;
  }
  return { matrix: qr, svg };
})();
