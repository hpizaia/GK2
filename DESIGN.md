# Companheiro GK2 — Design

Notes are in English; every user-facing string (and the i18n keys' pt values) is pt-BR first,
with an EN dictionary alongside. Sources: `src/` (modules, see §5), built by `scripts/build.py` into
`prototype/index.html` (local) and `dist/index.html` (the Claude Artifact). Status as of 1.2.0.

---

## 1. Research findings (UX of crafting planners)

Sources looked at: wikily.gg GK2 crafting calculator (page itself is behind Cloudflare, so its
UX was read from the scraped props in `data/raw/calculator-props.json`, i.e. its own UI strings
and data graph), CraftTodo mod page (Thunderstore), Kirk McDonald's Factorio calculator,
satisfactory-calculator.com / Satisfactory planners, Minecraft "raw materials" calculators,
Stardew checklist tools (Stardew Checkup, community bundle trackers).

| Topic | What they do | Decision for us |
|---|---|---|
| **Quantity input** | wikily: −/+ with numeric field ("Decrease/Increase quantity"). CraftTodo: −/+, hold-to-repeat, Shift = ±10. Factorio/Satisfactory: rate per minute (irrelevant here). | **Copy**: −/+ buttons (44 px) + numeric `inputmode="numeric"` field, min 1, max 999. Long-press repeat shipped in 1.2. No rates — GK2 is batch crafting, not throughput. |
| **Tree vs. flat totals** | wikily: three views — "Materials needed" (flat), "Crafting steps", "Breakdown tree". CraftTodo: collapsible tree. Factorio: flat table per recipe + optional graph. Minecraft calcs: flat raw list + step list. | **Copy the flat pair** (raw totals + steps). On a phone the tree is the worst view: deep indentation eats 360 px. Show *steps grouped by station* instead, ordered by stage, which is what you physically do. Tree = v2 inside a "Receita" detail. |
| **Batch yields / leftovers** | wikily is batch-aware: "yields", "per craft", "Left over" with hint *"Each recipe makes a fixed batch, so the totals only rise when another batch is needed."* | **Copy**: runs = ceil(need / outQty); show "rende N" and "sobra N". GK2 recipes produce 3, 4, 10, 12, 20 per craft — ignoring this would wildly overstate raw needs. |
| **"I already have X"** | CraftTodo: "Have it elsewhere" (right-click) + reads inventory. Factorio (Kirk): "ignore" a recipe → its product becomes a raw input. | **Copy Kirk's model**: per-intermediate toggle "Já tenho" → item is no longer expanded and moves to the raw list (tagged). No inventory counting in v1 (we can't read the save); "tenho N de M" partial counts shipped in 1.2. |
| **Multiple recipes** | Factorio/Satisfactory: click the recipe icon to cycle / pick from a dropdown; choice is global per item. | **Copy**: one choice per *item* (global, remembered), via a native `<select>` on the step row, option text = its inputs ("2 Prancha + 2 Pregos"). Default = first recipe in data (the build script should sort "simplest first"). |
| **Grouping by station** | wikily lists station per craftable; CraftTodo lets you switch workbench. Factorio groups by building count. | **Copy**: steps grouped in one card per station, cards ordered so no card depends on a later one (1.2; a station that comes back gets a second card), so "Cavalete → Toco → Galpão → Fornalha → Bigorna" reads top-down. |
| **Checklist / progress** | Stardew trackers: checkboxes + % bars, persisted locally. CraftTodo: auto-clears when done. | **Copy**: check raw items ("coletado") and steps ("feito"), struck through, one progress bar for the whole plan, "Limpar coletados". |
| **Search** | wikily: "Search {n} items and buildings…", match count, clear button. | **Copy**: count in placeholder, clear (×) button, accent-insensitive pt+en, word-prefix ranking. |
| **Mobile** | wikily/Factorio are desktop-first: wide tables, hover tooltips, tiny icons. | **Avoid**: hover-only info, wide tables, 24 px controls, modal recipe pickers that cover the plan. |

**Avoid list (explicit):** hover tooltips as the only source of info; rate/throughput maths;
sankey/graph views on mobile; auto-clearing the list (players plan ahead — keep it until they
press "Limpar lista"); infinite recursion on cyclic recipes (GK2 has e.g. Bones → Bones; break
cycles and flag them); emoji as icons.

---

## 2. Visual identity

### What the games look like (from GK2 Steam screenshots, sampled)
- **World**: rust/ochre dirt `#784818 #604818 #904818`, moss `#23351b`, red roof tiles `#bc362d`,
  warm lantern glow `#ef9a47`, night ground teal-navy `#111820`.
- **UI (tech-tree panel)**: very dark umber wood panel `#28201e`, slate-iron frame `#44444c`
  with a bevel, slate-violet header band `#383442`, cream/parchment label text `#eccfad`,
  gold-ochre node borders `#9d7c35`, amber connector lines `#a57103`, green check marks,
  a red × close button. Tabs are small caps on the dark band with gold separators.
- **Mood**: dark comedy, medieval, "deeper than six feet". Pixel art with soft modern lighting.

### Design system — tokens (dark is the default, light = parchment by day)

| Token | Dark (night) | Light (parchment) | Use |
|---|---|---|---|
| `--bg` | `#11171c` | `#ece0c4` | page ground (night teal-navy / old paper) |
| `--bg-2` | `#161d23` | `#e3d3b0` | sticky bars, inset wells |
| `--panel` | `#261e1a` | `#f6ecd6` | wood / parchment cards |
| `--panel-2` | `#30261f` | `#efe2c6` | raised rows, inputs |
| `--frame` | `#4a4954` | `#9a8664` | slate-iron borders (light: brown ink) |
| `--seam` | `#3a2e25` | `#dccaa6` | dividers inside panels |
| `--ink` | `#ecd9b6` | `#2b2017` | text (parchment cream / iron-gall ink) |
| `--ink-2` | `#b9a587` | `#5e4c38` | secondary text |
| `--ink-3` | `#9a8a72` | `#64553f` | captions, disabled |
| `--accent` | `#e3a24e` | `#824810` | lantern amber: primary action, numbers that matter |
| `--accent-ink` | `#1d1309` | `#fff6e6` | text on accent |
| `--gold` | `#a8853c` | `#6d531c` | trim, station headers, focus ring base |
| `--moss` | `#8fae5e` | `#4b6a26` | done / collected / progress fill |
| `--blood` | `#e06a5c` | `#9e2c22` | remove, destructive, cycle warning |
| `--slate` | `#2b2934` | `#d9ccae` | header band, tab bar (GK2 UI band) |

Semantic colours (moss/blood) are separate from the accent. Contrast: `--ink` on `--panel`
≈ 11.8:1 dark, 13.5:1 light; `--accent` on `--bg` ≈ 8.2:1 dark, 5.6:1 light.
1.2.0 contrast pass (AUDITORIA U2): light `--ink-3` `#75634a` → `#64553f`, `--gold` `#8a6a24` → `#6d531c`,
`--accent` `#9a5513` → `#824810` (each ≥ 4.5:1 on `--slate`); dark `--blood` `#d0574a` → `#e06a5c`
(≈ 5:1 on `--panel`). Source of truth: `src/css/tokens.css`. Theme: dark on bare `:root`, light under
`prefers-color-scheme: light` or `[data-theme="light"]`, `[data-theme="dark"]` forces dark (`GK.theme`).

### Typography (Google Fonts, full Portuguese accent support)
- **Display — Grenze Gotisch** (600–800): blackletter-flavoured but open counters, readable
  at 18 px+. Used only for the wordmark, fixed section titles and the letter fallback tile.
  Never for numbers or data-driven names: in blackletter the roman numerals "I/II" read as "U"
  (found in testing with "Bancada de marcenaria II"), so station/item names use the body face.
- **Body / UI / numbers — Alegreya Sans** (400/500/700/800): humanist sans with a calligraphic
  root (pairs with the gothic display), excellent accents, supports `tabular-nums` + lining
  figures. Quantities use 700 + `font-variant-numeric: tabular-nums lining-nums`.
- Fallbacks: `"Grenze Gotisch", "UnifrakturCook", Georgia, serif` /
  `"Alegreya Sans", "Segoe UI", system-ui, sans-serif`.
- Scale (px): 12 caption · 14 meta · 16 body · 18 row name · 22 section · 28 wordmark.
  Uppercase labels: 12 px, 700, letter-spacing .08em.

### Spacing, radius, elevation
- Spacing scale 4 · 8 · 12 · 16 · 24 · 32. Gutter `max(16px, safe-area)`.
- Radius: **2–4 px** only (pixel-art UI has near-square corners). Cards use a *double frame*
  (1 px `--frame` + inner 1 px highlight) instead of big radii or drop shadows.
- Touch targets ≥ 44 × 44 px; row height 56 px.

### "Wood & parchment" in CSS only (no images)
- **Wood panel**: `repeating-linear-gradient(90deg, …)` with 2–3 stripes at 3–5 % alpha for
  grain, over `--panel`; bevel via `box-shadow: inset 0 1px 0 rgba(255,235,200,.06),
  inset 0 -2px 0 rgba(0,0,0,.35)`; frame = `border: 1px solid var(--frame)` + `outline`
  offset inside in `--seam`.
- **Parchment (light)**: same rule, but the grain gradient becomes a radial vignette
  (`radial-gradient(ellipse at 50% 0, transparent 60%, rgba(120,80,30,.10))`).
- **Noise**: one tiny inline SVG `feTurbulence` as a `data:` URI on `body::after`
  (opacity .05, `pointer-events:none`), < 600 bytes.
- **Pixel corners**: buttons/chips use `clip-path` stepped corners (2 px notch) to echo the
  game's pixel frames, without touching layout.
- Icons: `image-rendering: pixelated`, on a 40 px dark "slot" tile like the game's hotbar;
  fallback tile = first letter in Grenze Gotisch on the slot.

---

## 3. Layout

### Mobile (360–430 px) — single column

```
┌──────────────────────────────────────┐
│ ✝ Companheiro GK2          [PT|EN]   │  header (slate band, sticky)
│ [Planejador] [Receitas·] [Tecnol.·]  │  tabs (own overflow-x)
├──────────────────────────────────────┤
│ 🔍 Buscar entre 44 itens…        [×] │  search (sticky under header)
│  ┌ result: [ic] Cerca de madeira II ┐│  results drop down over content
│  │         Bancada de marcenaria I [+]││
├──────────────────────────────────────┤
│ METAS (3)                 Limpar lista│
│ [ic] Caixão de madeira  [−][ 3 ][+] ✕│
│ [ic] Lanterna I         [−][ 1 ][+] ✕│
├──────────────────────────────────────┤
│ Progresso ▓▓▓▓▓░░░░░ 9/23  Copiar  │
│                       Limpar coletados│
├──────────────────────────────────────┤
│ MATÉRIAS-PRIMAS (12)                 │
│ [☐][ic] Tora ............... 14      │
│ [☑][ic] Areia ̶.̶.̶.̶ ̶6̶          │
│ [☐][ic] Gordura derretida  Já tenho↺│
├──────────────────────────────────────┤
│ ETAPAS POR ESTAÇÃO                   │
│ ┌ [st] Cavalete ─────────── etapa 1 ┐│
│ │[☐][ic] Tábua  ×12                  ││
│ │   3 execuções · rende 4 · sobra 0  ││
│ │   1 Tora por execução   [Já tenho] ││
│ └────────────────────────────────────┘│
│ ┌ [st] Fornalha II ──────── etapa 3 ┐│ …
├──────────────────────────────────────┤
│ Dados: wikily.gg · protótipo         │
└──────────────────────────────────────┘
```

### Desktop (≥ 900 px) — two columns, max-width 1180 px

```
┌───────────────────────────────────────────────────────────────┐
│ ✝ Companheiro GK2   [Planejador][Receitas][Tecnologias]  [PT|EN]│
├─────────────────────────┬─────────────────────────────────────┤
│ 🔍 Buscar…              │ Progresso ▓▓▓▓░░ 9/23  Copiar Limpar │
│ METAS                   │ ┌ MATÉRIAS-PRIMAS ┐ ┌ ETAPAS ────────┐│
│ [ic] Caixão  [−] 3 [+] ✕│ │ (2-col grid)    │ │ station cards  ││
│ [ic] Lanterna[−] 1 [+] ✕│ └─────────────────┘ └────────────────┘│
│ (sticky column, 360 px) │  ≥1180: raw list + stations side by side│
└─────────────────────────┴─────────────────────────────────────┘
```

---

## 4. Data contract the prototype consumes (`<script id="gk2-data" type="application/json">`)

> Historical: this is the mock contract the first prototype was designed against. The real payload is
> `data/gk2.json` schema 1 (plus `techs`, `meta.version`, `meta.changelog`, `meta.sprite`), documented in
> `scripts/README-build.md` ("Output schema" and "Page payload"). `GK.data` still accepts the lenient forms below.

```jsonc
{
  "schema": 1,
  "stations":   { "<stationId>": { "pt": "Cavalete", "en": "Sawhorse", "icon": "https://…|null" } },
  "categories": { "<catId>": { "pt": "Material", "en": "Material" } },
  "techs":      { "<techId>": { "pt": "Marcenaria I", "en": "Woodworking I" } },
  "items": {
    "<id>": { "id": "...", "pt": "Nome", "en": "Name", "cat": "<catId>", "icon": "https://…|null",
              "tr": "official|likely|guess", "obtain": { "pt": "...", "en": "..." } /* optional, raw items */ }
  },
  "recipes": [
    { "id": "...", "out": { "item": "<id>", "qty": 4 }, "station": "<stationId>",
      "in": [ { "item": "<id>", "qty": 1 } ], "tech": "<techId>|null" }
  ]
}
```
`data.normalize()` is lenient: `station`/`tech` may also be an inline `{pt,en}` object or a plain
string (used for both languages), and `stations/categories/techs` may be omitted.

## 5. Front-end architecture (source modules in `src/`, built into one HTML file)

Sources live in `src/` (one JS file per module, CSS split by concern, order in `src/manifest.json`);
`scripts/build.py` concatenates them into a single page with the data embedded. See
`scripts/README-build.md` → "The page sources" for the build and the module contract.

```
core.js      window.GK, GK.app.registerPanel(module, {id, panel | slot, order})
GK.util      esc, domId, slot (sprite icons), copyText, debounce
GK.i18n      LANGS[], DICT filled by each module via GK.i18n.add({pt, en}); t(key, vars), plurals, name(obj), num()
GK.data      load + normalize JSON → items, recipes, byOut, usedIn, stations, search index, meta (version, changelog)
GK.store     single serializable state {schemaVersion, lang, theme, goals, choice, have, done, overrides,
             researched, groupChoice, perks, updatedAt, syncBase, …}; localStorage per account; mergeSynced
             load/migrate/save (try/catch), subscribe(), actions
GK.calc      pure: plan(goals, data, {choice, have, perks, groupChoice}) → {raw[], steps[], stations[], cycles[], refused[]};
             search(); station cards follow dependencies (a station that comes back gets a second card)
GK.tech      pure: technology tree (prerequisites, missing techs for a plan, point totals)
GK.router    hash routes (#plan, #recipes, #tech, #changelog); register({id, labelKey, screen, order, tab});
             header renders the tab bar from it; missing <section data-screen> are created
GK.theme / GK.sync   theme attribute; account sync (Artifact db + user; merge field by field, keeps unknown fields)
GK.ui.*      header, search, goals, summary, checklist, techneeds (planner); recipes (#recipes); tech (#tech);
             changelog, soon, footer, toast (+ fmt helpers):
             each {mount(el, planRoot), render(state, meta, plan)}, registered with GK.app.registerPanel
GK.app       boot: data → store → i18n → theme → mount registered panels → router; render loop
```
Add a language: a `GK.i18n.LANGS` entry, its strings in every module's `GK.i18n.add` call, and an `xx`
field on items/stations/categories/techs (falls back to `en`). Add a tab or panel: a new module that calls
`GK.router.register` and/or `GK.app.registerPanel` (planner add-ons use `slot: "planner-extra"`).
