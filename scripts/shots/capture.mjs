#!/usr/bin/env node
/* Capturas de tela do app no Chrome headless, sem npm e sem servidor (a página abre por file://).

     node scripts/shots/capture.mjs --saida DIR PAGINA.html                       # só captura
     node scripts/shots/capture.mjs --saida DIR --antes A.html --depois B.html   # captura as duas e compara os pixels

   Quem chama no dia a dia é o compare.py (veja scripts/shots/README.md). Opções: --casos ARQ (padrão: casos.json
   ao lado), --filtro a,b (só os casos cujo nome contém um dos trechos), --paralelo N (Chromes ao mesmo tempo, padrão 4),
   --tempo-limite S (padrão 300: passou disso, fecha os Chromes e sai com erro), --tolerancia N (padrão 0: na
   comparação, um pixel cuja maior diferença por canal é ≤ N conta como igual, mas é contado em "tolerados").

   Cada caso de casos.json vira uma captura por idioma × tela: semeia localStorage["gk2-companion"] (e o
   sessionStorage, se o caso pedir), abre a página na rota, roda os passos (clicar, digitar, tecla) e grava em
   DIR/<lado>/: <caso>.png (página inteira, até ALTURA_MAX px), <caso>.html.txt (HTML do que está visível),
   <caso>.texto.txt (o texto visível) e <caso>.json (estado do GK.store, erros de JS, caixas dos painéis). Uma vez por
   página: dados.json (resumo do GK.data carregado: muda quando o dado muda, mesmo sem mudar a tela).
   Com --antes/--depois, compara os PNGs dentro do Chrome (canvas) e grava DIR/pixels.json e, para cada caso diferente,
   DIR/diferencas/<caso>.png (a imagem "depois" apagada, com os pixels diferentes em vermelho).

   O que deixa a captura igual de uma vez para outra:
   - relógio fixo (Date = RELOGIO), fuso e idioma do navegador fixos, perfil novo e um contexto isolado por captura
     (localStorage separado: as abas em paralelo não se misturam);
   - movimento reduzido (prefers-reduced-motion: reduce, que o app já respeita: sem transições) e o cursor de texto
     invisível (ele pisca);
   - um Chrome por aba em paralelo e rasterização sempre completa (ver abrirChrome);
   - rede: só as fontes do Google Fonts passam, e sempre com os mesmos bytes (cache em .shots/cache-fontes/; a
     primeira vez baixa). Qualquer outro pedido de rede é bloqueado;
   - espera de verdade em vez de pausa fixa: o "Carregando" sumir, document.fonts.ready, o sprite decodificado e o
     tamanho da página parar de mudar; e, logo antes da foto, de novo sprite, fontes e dois quadros;
   - na hora da foto, os elementos "sticky" viram "relative" (ver ANTES_DA_FOTO) e é uma foto só por captura.
   Contra processo preso: o Chrome roda com --remote-debugging-pipe (sem porta; morre sozinho quando este processo
   termina, até num kill -9), tempo-limite global, SIGINT/SIGTERM/exceção fecham o Chrome e apagam o perfil.
*/
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const RELOGIO = Date.parse("2026-11-01T12:00:00Z");   // "hoje" do app (painel Hoje, Dias, rodapé)
const FUSO = "America/Sao_Paulo";
const ALTURA_MAX = 12000;   // px CSS: cobre o plano longo no celular inteiro (~11000); passou disso, corta
const FONTES = /^https:\/\/fonts\.(googleapis|gstatic)\.com\//;
const CACHE_FONTES = path.join(ROOT, ".shots", "cache-fontes");

// ------------------------------------------------------------------ argumentos
function args(argv) {
  const o = { casos: path.join(HERE, "casos.json"), paralelo: 4, tempo: 300, tolerancia: 0, filtro: null, paginas: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i], v = () => argv[++i];
    if (a === "--saida") o.saida = path.resolve(v());
    else if (a === "--casos") o.casos = path.resolve(v());
    else if (a === "--antes") o.antes = path.resolve(v());
    else if (a === "--depois") o.depois = path.resolve(v());
    else if (a === "--filtro") o.filtro = v().split(",").filter(Boolean);
    else if (a === "--paralelo") o.paralelo = Math.max(1, +v() || 1);
    else if (a === "--tempo-limite") o.tempo = Math.max(10, +v() || 300);
    else if (a === "--tolerancia") o.tolerancia = Math.min(255, Math.max(0, Math.floor(+v() || 0)));
    else if (a.startsWith("--")) sair(`opção desconhecida: ${a}`);
    else o.paginas.push(path.resolve(a));
  }
  if (!o.saida) sair("falta --saida DIR");
  if (o.antes || o.depois) {
    if (!o.antes || !o.depois || o.paginas.length) sair("use --antes A.html --depois B.html (as duas, sem outra página)");
  } else if (o.paginas.length !== 1) sair("passe uma página (ou --antes e --depois)");
  return o;
}
function sair(msg) { console.error(`capture: ${msg}`); process.exit(2); }

// ------------------------------------------------------------------ Chrome por pipe (CDP)
// Um Chrome por trabalhador (cada aba em paralelo no seu Chrome: nada de rasterização dividida).
const navegadores = [];
let encerrando = false;
function abrirChrome() {
  const perfil = fs.mkdtempSync(path.join(os.tmpdir(), "gk2-shots-"));
  const proc = spawn(CHROME, ["--headless=new", "--remote-debugging-pipe", `--user-data-dir=${perfil}`, "--no-first-run",
    "--no-default-browser-check", "--disable-gpu", "--hide-scrollbars", "--force-color-profile=srgb",
    "--font-render-hinting=none", "--disable-extensions", "--disable-background-networking", "--disable-sync",
    "--disable-component-update", "--mute-audio",
    // rasterização sempre completa (sem ladrilho de baixa resolução, sem raster parcial, imagens já decodificadas):
    // sem isto, com a máquina ocupada, um canto ou borda saía com ±1 de cor
    "--disable-low-res-tiling", "--disable-partial-raster", "--disable-checker-imaging", "about:blank"], { stdio: ["ignore", "ignore", "pipe", "pipe", "pipe"] });
  const b = { proc, perfil, pend: new Map(), ouvintes: new Set(), seq: 0, abaComparar: null };
  navegadores.push(b);
  proc.on("error", (e) => { console.error(`capture: não consegui abrir o Chrome (${CHROME}): ${e.message}`); fechar(2); });
  proc.stderr.on("data", () => {});   // o Chrome fala muito no stderr; ignorar sem encher o buffer
  proc.on("exit", () => { if (!encerrando) { console.error("capture: o Chrome fechou sozinho"); fechar(2); } });
  let buf = "";
  proc.stdio[4].on("data", (d) => {
    buf += d.toString("utf8");
    let i;
    while ((i = buf.indexOf("\0")) >= 0) {
      const m = JSON.parse(buf.slice(0, i)); buf = buf.slice(i + 1);
      if (m.id && b.pend.has(m.id)) { const p = b.pend.get(m.id); b.pend.delete(m.id); m.error ? p.rej(new Error(`${p.metodo}: ${m.error.message}`)) : p.res(m.result); }
      else if (m.method) for (const f of b.ouvintes) f(m);
    }
  });
  b.cdp = (metodo, params = {}, sessionId) => new Promise((res, rej) => {
    const id = ++b.seq;
    b.pend.set(id, { res, rej, metodo });
    proc.stdio[3].write(JSON.stringify({ id, method: metodo, params, sessionId }) + "\0");
  });
  return b;
}
function fechar(codigo) {
  if (encerrando) return;
  encerrando = true;
  for (const b of navegadores) {
    try { if (b.proc.exitCode === null) b.proc.kill("SIGKILL"); } catch (e) { /* já fechou */ }
    try { fs.rmSync(b.perfil, { recursive: true, force: true }); } catch (e) { /* tanto faz */ }
  }
  if (codigo !== undefined) process.exit(codigo);
}
for (const s of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(s, () => { console.error(`capture: ${s}, fechando o Chrome`); fechar(130); });
process.on("uncaughtException", (e) => { console.error("capture: erro:", e && e.stack || e); fechar(2); });
process.on("unhandledRejection", (e) => { console.error("capture: erro:", e && e.stack || e); fechar(2); });
process.on("exit", () => fechar());
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
function comPrazo(p, ms, oque) {
  let t;
  return Promise.race([p, new Promise((_, rej) => { t = setTimeout(() => rej(new Error(`passou de ${ms / 1000} s: ${oque}`)), ms); })])
    .finally(() => clearTimeout(t));
}

// ------------------------------------------------------------------ fontes: sempre os mesmos bytes
const memFontes = new Map();
async function fonte(url, headers) {
  if (memFontes.has(url)) return memFontes.get(url);
  const h = createHash("sha1").update(url).digest("hex"), arq = path.join(CACHE_FONTES, h);
  let r = null;
  if (fs.existsSync(arq + ".json")) {
    r = JSON.parse(fs.readFileSync(arq + ".json", "utf8"));
    r.corpo = fs.readFileSync(arq + ".bin").toString("base64");
  } else {
    try {
      const pedir = {};
      for (const [k, v] of Object.entries(headers || {})) if (/^(user-agent|accept|accept-language|origin|referer)$/i.test(k)) pedir[k] = v;
      const resp = await fetch(url, { headers: pedir });
      if (resp.ok) {
        const corpo = Buffer.from(await resp.arrayBuffer());
        const cab = [];
        for (const [k, v] of resp.headers) if (/^(content-type|access-control-allow-origin|timing-allow-origin)$/i.test(k)) cab.push({ name: k, value: v });
        r = { status: resp.status, cabecalhos: cab };
        fs.mkdirSync(CACHE_FONTES, { recursive: true });
        fs.writeFileSync(arq + ".bin", corpo);
        fs.writeFileSync(arq + ".json", JSON.stringify({ url, ...r }, null, 1));
        r.corpo = corpo.toString("base64");
      }
    } catch (e) { r = null; }
  }
  memFontes.set(url, r);
  return r;
}
let semFontes = false;
async function aoPedirRede(b, m) {
  if (m.method !== "Fetch.requestPaused") return;
  const { requestId, request } = m.params, s = m.sessionId;
  try {
    if (FONTES.test(request.url)) {
      const r = await fonte(request.url, request.headers);
      if (r) return await b.cdp("Fetch.fulfillRequest", { requestId, responseCode: r.status, responseHeaders: r.cabecalhos, body: r.corpo }, s);
      semFontes = true;
    }
    await b.cdp("Fetch.failRequest", { requestId, errorReason: "BlockedByClient" }, s);
  } catch (e) { /* a aba já fechou */ }
}

// ------------------------------------------------------------------ casos
const EPOCH = "1970-01-01T00:00:00.000Z";
function lerCasos(arq) {
  const C = JSON.parse(fs.readFileSync(arq, "utf8"));
  const out = [];
  for (const c of C.casos) {
    for (const idioma of c.idiomas || ["pt"]) for (const tela of c.telas || C.telasPadrao) {
      if (!C.telas[tela]) sair(`caso ${c.nome}: tela desconhecida ${tela}`);
      if (c.estado && !C.estados[c.estado]) sair(`caso ${c.nome}: estado desconhecido ${c.estado}`);
      const nome = `${c.nome}.${idioma}.${tela}`;
      out.push({ nome, caso: c, idioma, tela: C.telas[tela], nomeTela: tela });
    }
  }
  return { C, variantes: out };
}
// o estado salvo de um jogador (schema de casos.json), com idioma e tema da variante
function montarEstado(C, v) {
  const e = v.caso.estado ? C.estados[v.caso.estado] : null;
  if (!e) return null;
  const s = JSON.parse(JSON.stringify(Object.assign({}, C.estadoBase, e)));
  s.ui = Object.assign({}, C.estadoBase.ui || {}, e.ui || {});
  s.schemaVersion = C.schemaVersion;
  s.lang = v.idioma;
  s.theme = v.tela.tema;
  if (!s.lists) {
    // uma lista só ("Minha lista"), como o app grava desde o schema 5
    s.lists = [{ id: "main", name: "", createdAt: EPOCH, updatedAt: s.updatedAt, goals: s.goals || [], choice: s.choice || {},
      have: s.have || {}, done: s.done || {}, example: !!s.example }];
    s.legacyOf = "main";
    s.listsGone = s.listsGone || {};
  }
  const ativa = s.lists.find((l) => l.id === s.ui.activeList) || s.lists[0];
  for (const k of ["goals", "choice", "have", "done", "example"]) s[k] = ativa[k];
  return s;
}

// ------------------------------------------------------------------ dentro da página
// espera o app ficar pronto e parado; devolve o estado das fontes
const PRONTO = `(async () => {
  const pausa = (ms) => new Promise((r) => setTimeout(r, ms));
  const quadro = () => new Promise((r) => requestAnimationFrame(() => r()));
  for (let i = 0; i < 300 && (document.readyState !== "complete" || document.getElementById("boot-msg")); i++) await pausa(50);
  if (!document.getElementById("gk2-shots-cursor")) {
    const st = document.createElement("style"); st.id = "gk2-shots-cursor";
    st.textContent = "*, *::before, *::after { caret-color: transparent !important; }";
    document.head.appendChild(st);
  }
  await document.fonts.ready;
  const sp = document.getElementById("gk-sprite"), m = sp && /url\\("([^"]+)"\\)/.exec(sp.textContent);
  if (m) { const im = new Image(); im.src = m[1]; await im.decode().catch(() => {}); }
  await Promise.all(Array.from(document.images).map((im) => im.decode().catch(() => {})));
  const assin = () => document.documentElement.scrollHeight + ":" + document.body.innerHTML.length;
  let antes = "";
  for (let i = 0; i < 30; i++) { await quadro(); await quadro(); const a = assin(); if (a === antes) break; antes = a; await pausa(60); }
  await document.fonts.ready;
  return { pronto: !document.getElementById("boot-msg"), fontes: Array.from(document.fonts).filter((f) => f.status !== "unloaded").map((f) => f.family + " " + f.weight + " " + f.style + " " + f.status).sort() };
})()`;
// logo antes da foto (depois de coletar o HTML): os elementos "sticky" viram "relative" sem deslocamento (com a página
// no topo, é onde já estavam: a foto não muda) e espera o sprite decodificado, as fontes e dois quadros pintados.
// Por quê: com o cabeçalho sticky do desktop (e a busca aberta nele), a foto da página inteira às vezes saía sem um
// elemento fora da tela (um botão de ícone inteiro, com moldura), ~1 caso em 10 rodadas. Devolve quantos eram sticky.
const ANTES_DA_FOTO = `(async () => {
  const quadro = () => new Promise((r) => requestAnimationFrame(() => r()));
  let n = 0;
  for (const el of document.querySelectorAll("*")) {
    if (getComputedStyle(el).position !== "sticky") continue;
    n++;
    el.style.setProperty("position", "relative", "important");
    for (const k of ["top", "right", "bottom", "left"]) el.style.setProperty(k, "auto", "important");
  }
  const sp = document.getElementById("gk-sprite"), m = sp && /url\\("([^"]+)"\\)/.exec(sp.textContent);
  if (m) { const im = new Image(); im.src = m[1]; await im.decode().catch(() => {}); }
  await document.fonts.ready;
  await quadro(); await quadro();
  return n;
})()`;
// o que está visível: HTML, texto, estado do store, caixas dos painéis (para dizer "onde" mudou)
const COLETAR = `(() => {
  const vis = (el) => el && !el.hidden && el.getClientRects().length > 0;
  const partes = ["#top", "#tabs-band", "[data-panel=search]", "main", "footer", "#toast"].map((s) => document.querySelector(s)).filter(Boolean);
  const html = partes.map((el) => {
    const c = el.cloneNode(true);
    c.querySelectorAll("[hidden], script, style").forEach((x) => x.remove());
    return c.outerHTML;
  }).join("\\n");
  const caixas = [];
  document.querySelectorAll("[data-panel], [data-slot], [data-screen], #top, #tabs-band, footer").forEach((el) => {
    if (!vis(el)) return;
    const r = el.getBoundingClientRect();
    const nome = el.id ? "#" + el.id : el.dataset.panel ? "painel " + el.dataset.panel : el.dataset.slot ? "slot " + el.dataset.slot : el.dataset.screen ? "tela " + el.dataset.screen : el.tagName.toLowerCase();
    caixas.push({ nome, x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height) });
  });
  let estado = null;
  try { estado = JSON.parse(JSON.stringify(GK.store.get())); } catch (e) { estado = String(e); }
  return { html, texto: document.body.innerText, estado, caixas, rota: location.hash, tema: document.documentElement.getAttribute("data-theme"), lang: document.documentElement.lang };
})()`;
// resumo do GK.data: um hash por chave de topo e um por item e por receita (objetos repetidos viram "→id")
const DADOS = `(() => {
  const D = GK.data.get();
  const h = (str) => { let a = 0xdeadbeef, b = 0x41c6ce57; for (let i = 0; i < str.length; i++) { const c = str.charCodeAt(i); a = Math.imul(a ^ c, 2654435761); b = Math.imul(b ^ c, 1597334677); }
    a = Math.imul(a ^ (a >>> 16), 2246822507) ^ Math.imul(b ^ (b >>> 13), 3266489909); b = Math.imul(b ^ (b >>> 16), 2246822507) ^ Math.imul(a ^ (a >>> 13), 3266489909);
    return (4294967296 * (2097151 & b) + (a >>> 0)).toString(36); };
  const ref = new Map();
  for (const [id, it] of Object.entries(D.items || {})) ref.set(it, "→item:" + id);
  for (const r of D.recipes || []) ref.set(r, "→receita:" + r.id);
  for (const [id, s] of Object.entries(D.stations || {})) ref.set(s, "→estacao:" + id);
  const ser = (v, raiz, pais) => {
    if (v === null || typeof v !== "object") return typeof v === "function" ? '"[função]"' : JSON.stringify(v) === undefined ? "null" : JSON.stringify(v);
    if (v !== raiz && ref.has(v)) return JSON.stringify(ref.get(v));
    if (pais.has(v)) return '"[ciclo]"';
    pais.add(v);
    let s;
    if (Array.isArray(v)) s = "[" + v.map((x) => ser(x, raiz, pais)).join(",") + "]";
    else if (v instanceof Map || v instanceof Set) s = ser(Array.from(v), raiz, pais);
    else s = "{" + Object.keys(v).sort().map((k) => JSON.stringify(k) + ":" + ser(v[k], raiz, pais)).join(",") + "}";
    pais.delete(v);
    return s;
  };
  const um = (v) => { const s = ser(v, v, new Set()); return { n: Array.isArray(v) ? v.length : v && typeof v === "object" ? Object.keys(v).length : 1, hash: h(s), tam: s.length }; };
  const chaves = {};
  for (const k of Object.keys(D).sort()) chaves[k] = um(D[k]);
  const items = {}, receitas = {};
  for (const id of Object.keys(D.items || {}).sort()) items[id] = h(ser(D.items[id], D.items[id], new Set()));
  for (const r of D.recipes || []) receitas[r.id] = h(ser(r, r, new Set()));
  // meta por partes (o sprite separado em imagem e o resto): para dizer o que mudou dentro dela
  const metaPartes = {};
  for (const [k, v] of Object.entries(D.meta || {})) {
    if (k === "sprite" && v && typeof v === "object") for (const [k2, v2] of Object.entries(v)) metaPartes["sprite." + k2] = um(v2).hash;
    else metaPartes[k] = um(v).hash;
  }
  return { meta: { built: D.meta && D.meta.built, version: D.meta && D.meta.version }, schema: GK.store.SCHEMA, chaves, metaPartes, items, receitas };
})()`;

// ------------------------------------------------------------------ uma captura
async function avaliar(b, s, expr, oque) {
  const r = await b.cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }, s);
  if (r.exceptionDetails) throw new Error(`${oque}: ${(r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text}`.slice(0, 400));
  return r.result.value;
}
async function abrirAba(b, v, url, semente) {
  const { browserContextId } = await b.cdp("Target.createBrowserContext", { disposeOnDetach: true });
  const { targetId } = await b.cdp("Target.createTarget", { url: "about:blank", browserContextId });
  const { sessionId: s } = await b.cdp("Target.attachToTarget", { targetId, flatten: true });
  const erros = [];
  let carregou;
  const carregado = new Promise((r) => { carregou = r; });
  const ouvinte = (m) => {
    if (m.sessionId !== s) return;
    if (m.method === "Fetch.requestPaused") aoPedirRede(b, m);
    else if (m.method === "Page.loadEventFired") carregou();
    else if (m.method === "Runtime.exceptionThrown") erros.push("exceção: " + ((m.params.exceptionDetails.exception && m.params.exceptionDetails.exception.description) || m.params.exceptionDetails.text).split("\n")[0]);
    else if (m.method === "Runtime.consoleAPICalled" && (m.params.type === "error" || m.params.type === "warning" || m.params.type === "assert"))
      erros.push(`console.${m.params.type}: ` + m.params.args.map((a) => a.value !== undefined ? String(a.value) : a.description || a.type).join(" ").slice(0, 300));
  };
  b.ouvintes.add(ouvinte);
  const t = v.tela;
  await b.cdp("Fetch.enable", { patterns: [{ urlPattern: "http*" }] }, s);
  await b.cdp("Page.enable", {}, s);
  await b.cdp("Runtime.enable", {}, s);
  await b.cdp("Emulation.setDeviceMetricsOverride", { width: t.largura, height: t.altura, deviceScaleFactor: t.escala, mobile: !!t.celular }, s);
  await b.cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: t.tema }, { name: "prefers-reduced-motion", value: "reduce" }] }, s);
  await b.cdp("Emulation.setTimezoneOverride", { timezoneId: FUSO }, s);
  await b.cdp("Emulation.setLocaleOverride", { locale: v.idioma === "en" ? "en-US" : "pt-BR" }, s);
  await b.cdp("Emulation.setUserAgentOverride", { userAgent: "Mozilla/5.0 GK2-shots", acceptLanguage: v.idioma === "en" ? "en-US,en" : "pt-BR,pt" }, s);
  await b.cdp("Page.addScriptToEvaluateOnNewDocument", { source: `(() => {
    const T = ${RELOGIO}, D = Date;
    class F extends D { constructor(...a) { super(...(a.length ? a : [T])); } static now() { return T; } }
    window.Date = F;
    if (!sessionStorage.getItem("gk2-shots")) {
      sessionStorage.setItem("gk2-shots", "1");
      localStorage.clear();
      const S = ${JSON.stringify(semente)};
      for (const [k, v] of Object.entries(S.local)) localStorage.setItem(k, JSON.stringify(v));
      for (const [k, v] of Object.entries(S.sessao)) sessionStorage.setItem(k, JSON.stringify(v));
    }
  })();` }, s);
  await b.cdp("Page.navigate", { url }, s);
  await comPrazo(carregado, 20000, "carregar a página");
  return { s, targetId, browserContextId, erros, fim: async () => {
    b.ouvintes.delete(ouvinte);
    await b.cdp("Target.closeTarget", { targetId }).catch(() => {});
    await b.cdp("Target.disposeBrowserContext", { browserContextId }).catch(() => {});
  } };
}
async function passo(b, s, p) {
  if (p.clicar) {
    await avaliar(b, s, `(() => { const el = document.querySelector(${JSON.stringify(p.clicar)}); if (!el) throw new Error("não achei " + ${JSON.stringify(p.clicar)}); el.scrollIntoView({ block: "center" }); el.click(); })()`, `clicar ${p.clicar}`);
  } else if (p.digitar !== undefined) {
    if (p.em) await avaliar(b, s, `(() => { const el = document.querySelector(${JSON.stringify(p.em)}); if (!el) throw new Error("não achei " + ${JSON.stringify(p.em)}); el.focus(); })()`, `focar ${p.em}`);
    await b.cdp("Input.insertText", { text: p.digitar }, s);
  } else if (p.tecla) {
    const k = { Enter: 13, Escape: 27, ArrowDown: 40, ArrowUp: 38, Tab: 9 }[p.tecla] || 0;
    for (const type of ["keyDown", "keyUp"]) await b.cdp("Input.dispatchKeyEvent", { type, key: p.tecla, code: p.tecla, windowsVirtualKeyCode: k }, s);
  } else if (p.rolar) {
    await avaliar(b, s, `(() => { const el = document.querySelector(${JSON.stringify(p.rolar)}); if (el) el.scrollIntoView({ block: "start" }); })()`, `rolar ${p.rolar}`);
  } else throw new Error("passo desconhecido: " + JSON.stringify(p));
  await dormir(p.espera ?? 350);   // o tempo das esperas do app (busca com debounce, gravação adiada)
}
async function capturar(b, C, v, pagina, dir) {
  const estado = montarEstado(C, v);
  const semente = { local: estado ? { "gk2-companion": estado } : {}, sessao: v.caso.sessao || {} };
  const url = "file://" + pagina + "#" + (v.caso.rota || "plan");
  const aba = await abrirAba(b, v, url, semente);
  try {
    const s = aba.s;
    const pronto = await comPrazo(avaliar(b, s, PRONTO, "esperar o app"), 20000, "esperar o app");
    if (!pronto.pronto) throw new Error("o app não terminou de abrir (o \"Carregando\" ficou na tela)");
    for (const p of v.caso.passos || []) { await passo(b, s, p); await avaliar(b, s, PRONTO, "esperar depois do passo"); }
    const info = await avaliar(b, s, COLETAR, "coletar HTML e estado");
    // o estado semeado foi aceito? (um schema ou formato errado o app descarta em silêncio e abre o exemplo)
    if (estado) {
      const st = info.estado || {}, quer = (estado.goals || []).length, tem = (st.goals || []).length;
      if (quer !== tem || !!st.example !== !!estado.example) aba.erros.push(`semente: o app abriu com ${tem} meta(s)${st.example ? " (exemplo)" : ""} em vez de ${quer}`);
    }
    const m = await b.cdp("Page.getLayoutMetrics", {}, s);
    const altura = Math.min(ALTURA_MAX, Math.ceil(m.cssContentSize.height));
    const sticky = await avaliar(b, s, ANTES_DA_FOTO, "preparar a foto");
    // uma foto só: uma segunda foto logo depois da primeira sai diferente (o anel de foco da busca some)
    const { data } = await b.cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: true,
      clip: { x: 0, y: 0, width: v.tela.largura, height: altura, scale: 1 } }, s);
    fs.writeFileSync(path.join(dir, v.nome + ".png"), Buffer.from(data, "base64"));
    fs.writeFileSync(path.join(dir, v.nome + ".html.txt"), info.html.replace(/></g, ">\n<") + "\n");
    fs.writeFileSync(path.join(dir, v.nome + ".texto.txt"), info.texto + "\n");
    const json = { caso: v.nome, rota: info.rota, tema: info.tema, lang: info.lang, alturaPagina: Math.ceil(m.cssContentSize.height),
      alturaCaptura: altura, escala: v.tela.escala, sticky, fontes: pronto.fontes, erros: aba.erros, caixas: info.caixas, estado: info.estado };
    fs.writeFileSync(path.join(dir, v.nome + ".json"), JSON.stringify(json, null, 1) + "\n");
    return { png: data, erros: aba.erros };
  } finally { await aba.fim(); }
}
async function resumoDados(b, pagina, dir) {
  const v = { nome: "dados", caso: { rota: "plan" }, idioma: "pt", tela: { largura: 800, altura: 600, escala: 1, tema: "dark" } };
  const aba = await abrirAba(b, v, "file://" + pagina + "#plan", { local: {}, sessao: {} });
  try {
    await comPrazo(avaliar(b, aba.s, PRONTO, "esperar o app"), 20000, "esperar o app");
    const d = await avaliar(b, aba.s, DADOS, "resumir GK.data");
    d.erros = aba.erros;
    fs.writeFileSync(path.join(dir, "dados.json"), JSON.stringify(d, null, 1) + "\n");
  } finally { await aba.fim(); }
}

// ------------------------------------------------------------------ comparar pixels (no próprio Chrome)
// devolve diferentes (pixels acima da tolerância), tolerados (diferentes, mas ≤ tolerância), delta (a maior diferença
// por canal entre todos os pixels que não são idênticos, de 0 a 255) e, se algum passou da tolerância, caixa e imagem
async function comparar(b, pa, pb, escala, tol) {
  if (!b.abaComparar) {
    const { targetId } = await b.cdp("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await b.cdp("Target.attachToTarget", { targetId, flatten: true });
    b.abaComparar = { s: sessionId, targetId };
    await b.cdp("Runtime.enable", {}, sessionId);
  }
  if (pa === pb) return { diferentes: 0, tolerados: 0, delta: 0 };
  const expr = `(async () => {
    const ler = async (b64) => createImageBitmap(await (await fetch("data:image/png;base64," + b64)).blob());
    const [x, y] = await Promise.all([ler(${JSON.stringify(pa)}), ler(${JSON.stringify(pb)})]);
    const W = Math.max(x.width, y.width), H = Math.max(x.height, y.height);
    const pix = (im) => { const c = new OffscreenCanvas(W, H), g = c.getContext("2d"); g.drawImage(im, 0, 0); return g.getImageData(0, 0, W, H).data; };
    const p = pix(x), q = pix(y);
    const out = new OffscreenCanvas(W, H), g = out.getContext("2d");
    g.fillStyle = "#fff"; g.fillRect(0, 0, W, H); g.globalAlpha = 0.25; g.drawImage(y, 0, 0); g.globalAlpha = 1;
    const img = g.getImageData(0, 0, W, H), d = img.data;
    let n = 0, tolerados = 0, x0 = W, y0 = H, x1 = -1, y1 = -1, delta = 0;
    for (let i = 0; i < p.length; i += 4) {
      const dp = Math.max(Math.abs(p[i] - q[i]), Math.abs(p[i + 1] - q[i + 1]), Math.abs(p[i + 2] - q[i + 2]), Math.abs(p[i + 3] - q[i + 3]));
      if (dp > delta) delta = dp;
      if (dp <= ${tol}) {
        if (dp) tolerados++;
        const cinza = (d[i] + d[i + 1] + d[i + 2]) / 3; d[i] = d[i + 1] = d[i + 2] = cinza; continue;
      }
      n++; d[i] = 230; d[i + 1] = 0; d[i + 2] = 0; d[i + 3] = 255;
      const k = i / 4, X = k % W, Y = (k - X) / W;
      if (X < x0) x0 = X; if (X > x1) x1 = X; if (Y < y0) y0 = Y; if (Y > y1) y1 = Y;
    }
    if (!n) return { diferentes: 0, tolerados, delta, tamanhos: [x.width, x.height, y.width, y.height] };
    g.putImageData(img, 0, 0);
    g.strokeStyle = "#e60000"; g.lineWidth = Math.max(2, ${escala} * 2); g.strokeRect(x0 - 4, y0 - 4, x1 - x0 + 9, y1 - y0 + 9);
    const blob = await out.convertToBlob({ type: "image/png" });
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let bin = ""; for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return { diferentes: n, tolerados, delta, caixa: [x0, y0, x1, y1], tamanhos: [x.width, x.height, y.width, y.height], imagem: btoa(bin) };
  })()`;
  return avaliar(b, b.abaComparar.s, expr, "comparar pixels");
}

// ------------------------------------------------------------------ principal
async function main() {
  const o = args(process.argv.slice(2));
  if (!fs.existsSync(CHROME)) sair(`Chrome não encontrado em ${CHROME} (use a variável CHROME)`);
  const { C, variantes } = lerCasos(o.casos);
  const lista = o.filtro ? variantes.filter((v) => o.filtro.some((f) => v.nome.includes(f))) : variantes;
  if (!lista.length) sair("nenhum caso com esse filtro");
  const lados = o.antes ? [["antes", o.antes], ["depois", o.depois]] : [["", o.paginas[0]]];
  for (const [, p] of lados) if (!fs.existsSync(p)) sair(`página não encontrada: ${p}`);
  // o schema dos casos e o da página: o app migra um estado mais velho, mas aí a captura não é a de um jogador atual
  for (const [lado, p] of lados) {
    const m = /const SCHEMA = (\d+);/.exec(fs.readFileSync(p, "utf8"));
    if (m && +m[1] !== C.schemaVersion) console.log(`AVISO: casos.json está no schema ${C.schemaVersion}, a página ${lado || ""} no ${m[1]}: atualize os estados de casos.json`);
  }
  fs.mkdirSync(o.saida, { recursive: true });
  for (const [lado] of lados) fs.mkdirSync(path.join(o.saida, lado), { recursive: true });
  const tempo = setTimeout(() => { console.error(`capture: passou do tempo-limite (${o.tempo} s), fechando o Chrome`); fechar(3); }, o.tempo * 1000);
  const t0 = Date.now();
  const nav = Array.from({ length: Math.min(o.paralelo, lista.length) }, abrirChrome);
  const versao = await comPrazo(Promise.all(nav.map((b) => b.cdp("Browser.getVersion"))), 15000, "abrir o Chrome");
  for (const b of nav) b.ouvintes.add((m) => { if (m.method === "Target.targetCrashed") console.error("capture: uma aba do Chrome caiu"); });
  await Promise.all(lados.map(([lado, p], i) => resumoDados(nav[i % nav.length], p, path.join(o.saida, lado))));
  const pixels = {};
  let fila = lista.slice(), erros = 0;
  async function trabalhador(b) {
    for (let v = fila.shift(); v; v = fila.shift()) {
      const r = {};
      try {
        for (const [lado, p] of lados) r[lado || "depois"] = await comPrazo(capturar(b, C, v, p, path.join(o.saida, lado)), 45000, `capturar ${v.nome}`);
        if (o.antes) {
          const c = await comparar(b, r.antes.png, r.depois.png, v.tela.escala, o.tolerancia);
          if (c.imagem) {
            fs.mkdirSync(path.join(o.saida, "diferencas"), { recursive: true });
            fs.writeFileSync(path.join(o.saida, "diferencas", v.nome + ".png"), Buffer.from(c.imagem, "base64"));
            delete c.imagem;
          }
          pixels[v.nome] = c;
        }
        console.log(`capturado  ${v.nome}`);
      } catch (e) {
        erros++;
        pixels[v.nome] = { erro: String(e.message || e) };
        console.log(`ERRO       ${v.nome}: ${e.message || e}`);
      }
    }
  }
  try {
    await Promise.all(nav.map(trabalhador));
  } finally {
    clearTimeout(tempo);
  }
  const resumo = { casos: lista.map((v) => ({ nome: v.nome, escala: v.tela.escala })), segundos: Math.round((Date.now() - t0) / 100) / 10,
    tolerancia: o.tolerancia, semFontes, chrome: versao[0].product };
  fs.writeFileSync(path.join(o.saida, "resumo.json"), JSON.stringify(resumo, null, 1) + "\n");
  if (o.antes) fs.writeFileSync(path.join(o.saida, "pixels.json"), JSON.stringify(pixels, null, 1) + "\n");
  if (semFontes) console.log("AVISO: as fontes do Google Fonts não vieram (sem rede e sem cache): capturas com a fonte reserva");
  await Promise.all(nav.map((b) => b.cdp("Browser.close").catch(() => {})));
  fechar(erros ? 1 : 0);
}
main();
