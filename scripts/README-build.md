# GK2 planner: data build and validation

The build uses only the Python 3 standard library. Always run it with `python3 -I` from the project root. Paths
may contain spaces, so quote them.

| script | what it does |
|---|---|
| `scripts/build.py` | Merges items, recipes and names into `data/gk2.json` and `data/gk2.min.json`, writes the reports, assembles the page from `src/` (data, version and changelog embedded) and regenerates `CHANGELOG.md` |
| `scripts/validate.py` | Checks a merged `gk2.json`. build.py also runs it on every build |
| `scripts/test_build.py` | Tests on `scripts/fixtures/` (plus a read-only smoke test on the real data) |
| `scripts/fetch_icons.py` | Downloads every distinct `icon` URL of `data/gk2.json` (items + stations) into `data/icons/<id>.png` (≤ 5 req/s, skips existing files) |
| `scripts/make_sprite.py` | Packs `data/icons/*.png` into one sprite sheet: `data/sprite.json` (manifest with a `data:` PNG) + `data/sprite.png` |

## Run

```sh
# everything: data/gk2.json, gk2.min.json, both reports, CHANGELOG.md, and the page assembled from src/:
#   prototype/index.html  local dev page (full document skeleton)
#   dist/index.html       Claude Artifact page (no skeleton, no remote icon URLs)
#   dist/preview.html     dist/index.html inside a minimal skeleton, for local viewing
# The sprite (data/sprite.json) is embedded when it exists.
python3 -I scripts/build.py

# publish a version: dates the top entry of data/changelog.json (if still null) with the build date
python3 -I scripts/build.py --release

# data only (no page)
python3 -I scripts/build.py --no-src

# legacy: embed the data in an existing single-file page (in place + .bak, or into --out)
python3 -I scripts/build.py --inject some/page.html
python3 -I scripts/build.py --inject some/page.html --out dist/index.html --artifact --sprite data/sprite.json

# icons -> sprite (once, or when icons change), then rebuild
python3 -I scripts/fetch_icons.py            # data/icons/<id>.png
python3 -I scripts/make_sprite.py            # data/sprite.json + data/sprite.png (Pillow optional)
python3 -I scripts/build.py

# validate an existing build (exit 1 on hard errors)
python3 -I scripts/validate.py data/gk2.json            # markdown report
python3 -I scripts/validate.py data/gk2.json --json     # machine-readable

# tests
python3 -I scripts/test_build.py
```

Options for `build.py`:

| option | default | |
|---|---|---|
| `--items PATH` | `data/items.en.json` | |
| `--recipes PATH` | `data/recipes.en.json` | |
| `--names PATH` (repeatable) | `data/names.official.pt-BR.json`, `data/names.recipes.pt-BR.json`, `data/names.wiki.pt-BR.json`, `data/names.pt-BR.json`, `data/names.machine.pt-BR.json` | pt layers. A missing file is skipped with a note in the report. An entry with `"fix": "<reason>"` is a correction of the official text: it wins over every layer and tier and keeps its own confidence (`data/README-l10n.md`) |
| `--lang FIELD=PATH[,PATH]` (repeatable) | none | extra language (see below) |
| `--out-dir DIR` | `data/` | where the JSON and the reports go |
| `--src DIR` | `src/` when `src/manifest.json` exists and `--inject` is not given | assemble the page from `DIR` and write `DIR/../prototype/index.html`, `DIR/../dist/index.html`, `DIR/../dist/preview.html`. `VERSION`, `data/changelog.json`, `data/sprite.json` and `CHANGELOG.md` are read/written in `DIR/..` |
| `--no-src` | | data only, no page |
| `--release` | | set the `date` of the top `data/changelog.json` entry to the build date (`--built` / `SOURCE_DATE_EPOCH` / today) when it is `null`. Exit 2 when `VERSION` and the top entry differ |
| `--inject HTML` / `--out PATH` | | legacy: replace the content of `<script id="gk2-data" type="application/json">…</script>` in an existing page |
| `--allow-errors` | off | write the JSON and inject even with hard errors (the exit code stays 1) |
| `--built YYYY-MM-DD` | `SOURCE_DATE_EPOCH`, else today (UTC) | `meta.built` |
| `--source NAME` (repeatable) | | extra entry in `meta.sources` |
| `--sprite PATH.json` | `data/sprite.json` (src mode, when present) | embed a `make_sprite.py` manifest as `meta.sprite`; the page draws icons from it |
| `--techs PATH.json` | `data/techs.json` when present, in src mode or with the default `--items`/`--recipes` | technology tree (`scripts/build_techs.py`, see `data/README-techs.md`): recipe `tech` names of type technology follow it (also in `gk2.json`), and the page embeds a compact copy as `techs`. In `--inject` mode it is embedded only when given explicitly |
| `--no-techs` | | ignore `data/techs.json` (cannot be combined with `--techs`) |
| `--days PATH.json` | `data/days.json` when present, in src mode or with the default `--items`/`--recipes` | the 6-day week (`scripts/build_days.py`, see `data/README-days.md`), embedded in the page as `days` (see below). Absent file = no `days` block, no error; a malformed one is exit 2. In `--inject` mode it is embedded only when given explicitly |
| `--no-days` | | ignore `data/days.json` (cannot be combined with `--days`) |
| `--artifact` | | with `--inject … --out PATH`: Claude Artifact page (see below) + `preview.html` next to it |
| `--quiet` | | no stdout summary. Errors still go to stderr |

**Exit codes:** `0` ok (warnings allowed), `1` hard validation errors, `2` usage or IO error (missing input, page
without a data block or with more than one, a broken `src/` manifest or template, a source file containing
`</script` / `</style`, a malformed `VERSION` or `data/changelog.json`).

With hard errors, `gk2.json` and `gk2.min.json` are **not** written (the previous good build is kept) and nothing is
injected. Both reports are always written.

**Idempotent:** a file is rewritten only when its bytes change, so a second run with the same inputs on the same
day touches nothing and prints `wrote nothing (all outputs up to date)`. The `.bak` copy is made only when the page
actually changes. Output order is deterministic: items and stations are sorted by id, and recipes keep their input
order.

**Injection safety:** in the embedded JSON every `<` becomes `<` (and U+2028/2029 are escaped too). The JSON
stays valid and no `</script>` or `<!--` can end the block. Read it with
`JSON.parse(document.getElementById("gk2-data").textContent)`.

**Where the data block sits:** after the markup (after `</footer>` and the toast) and before the modules. The
shell then paints from the first ~75 KB of the page instead of after the ~1.75 MB of data (UX review #9: `<header`
moved from byte 1,816,040 to ~73,000 of `dist/preview.html`); the modules still run after the block is parsed, so
`GK.data.load()` finds it at boot. The build finds the tag by its id wherever it is (both `<!-- @data -->` in src
mode and `--inject`), so moving it needs no build change. `#boot-msg` ("Carregando o Companheiro… · Loading…",
static and bilingual because no module has run yet) shows while the page downloads; `app.js` removes it at boot.

## The page sources (`src/`)

```
src/
  manifest.json        {"template": "index.html", "css": [...], "js": [...]}: build order (paths relative to src/)
  index.html           page template: <title>, metas, fonts, <!-- @css -->, markup (header, tab band, search row,
                       "Carregando" line, <main>, footer, toast), then
                       <script id="gk2-data" type="application/json"><!-- @data --></script>, <!-- @js -->
  css/                 tokens, base, header, components, planner, screens, recipes (Receitas), tech (Tecnologias
                       + the planner panel), responsive (keep last)
  js/core.js           window.GK + GK.app.registerPanel (keep FIRST)
  js/util.js i18n.js data.js store.js calc.js router.js theme.js sync.js
  js/tech.js           GK.tech: pure functions over the technology tree (prerequisites, missing techs, costs)
  js/ui/fmt.js header.js search.js goals.js summary.js checklist.js soon.js (generic placeholder) changelog.js
       footer.js toast.js
  js/ui/recipes.js     the Receitas screen (#recipes): browse, filters, item detail, "Usado em", add to goals
  js/ui/tech.js        the Tecnologias screen (#tech);  js/ui/techneeds.js  planner panel "Tecnologias que faltam"
  js/ui/days.js        the Dias screen (#days: week wheel, day card, week table); js/ui/today.js  planner panel "Hoje"
  js/app.js            boot + render loop (keep LAST: it boots right away)
```

The build fills the data block first, then replaces `<!-- @css -->` with one `<style>` (the css files in manifest
order) and `<!-- @js -->` with one `<script>` (`"use strict";` + the js files in manifest order). Each file is
preceded by a `/* ==== src/<path> ==== */` banner, so a stack trace or a search in the built page leads back to the
source. A `.js` / `.css` file under `src/` that is not in the manifest is reported as a warning and not built.
**Edit `src/`, never `prototype/index.html` or `dist/`: they are overwritten on every build.**

### Adding a module (the contract for parallel work)

A feature lives in its own files (`src/js/ui/<name>.js`, optionally `src/css/<name>.css`), listed in
`src/manifest.json` (before `js/app.js`; css before `css/responsive.css`). Inside the module, at load time:

```js
/* GK.ui.recipes: what it owns / what it exposes. */
GK.i18n.add({ pt: { "recipes.title": "Receitas" }, en: { "recipes.title": "Recipes" } });   // its own strings

GK.ui.recipes = (function () {
  let root;
  return {
    mount(el, planRoot) { root = el; /* event delegation on el */ },
    render(state, meta, plan) { /* called on every store change and route change */ },
  };
})();

// a tab: header renders the tab bar from this registry; a <section data-screen="recipes" data-panel="recipes">
// is created in <main> when the template has none. tab: false = route-only screen (like #changelog).
GK.router.register({ id: "recipes", labelKey: "recipes.title", screen: "recipes", order: 20 });
// the render loop: mount into [data-panel="recipes"] ...
GK.app.registerPanel(GK.ui.recipes, { id: "recipes", panel: "recipes", order: 80 });
// ... or into a new <div data-panel="<id>"> inside the planner, after the summary:
GK.app.registerPanel(GK.ui.techNeeds, { id: "tech-needs", slot: "planner-extra", order: 80 });
```

Registering a route id that already exists replaces it. A tab can start as a placeholder
(`GK.router.register({ id, labelKey, screen: "soon", soon: true })`, rendered by `ui/soon.js`) and later be taken
over by its real screen; Receitas and Tecnologias did this in 1.2.0, and no placeholder is registered now.
Hash routes are bare tokens (`#recipes`), the only form the Artifact viewer passes through.

## Version and update history

- `VERSION` (project root): one line, e.g. `1.2.0`. Embedded as `meta.version`; the footer shows
  "Companheiro GK2 v1.2.0 · Histórico de atualizações" with a link to `#changelog`.
- `data/changelog.json`: newest first, `[{"version": "1.2.0", "date": "YYYY-MM-DD" | null, "pt": [...], "en": [...]}]`.
  `date: null` = unreleased ("em desenvolvimento"). Embedded as `meta.changelog` and rendered by `ui/changelog.js`.
  The top entry's version should match `VERSION` (warning otherwise; `--release` refuses).
- `CHANGELOG.md` is generated from it on every build (pt first, en below). Do not edit it by hand.
- Releasing: bump `VERSION`, add the entry at the top with `"date": null`, list the changes, then
  `python3 -I scripts/build.py --release`.

## Output schema (`data/gk2.json`, schema 1)

Every field below is always present, with `null`, `false` or `[]` when there is no value. `{pt, en}` means a
localized object. When a name has no translation, `pt` is the English text.

```jsonc
{
  "meta": {
    "schema": 1,
    "built": "2026-10-30",
    "langs": ["pt", "en"],                       // localized fields present on {pt, en} objects
    "counts": { "items": 820, "recipes": 695, "stations": 79, "categories": 53, "techs": 231,
                "multiRecipeItems": 66, "noexpRecipes": 17,
                "tr": {"official": 0, "likely": 75, "guess": 0, "machine": 745, "missing": 0},
                "cycles": 8, "errors": 0, "warnings": 206 },
    "sources": ["gk1-wiki", "wikily.gg"]         // recipe source_url hosts + names-file sources (not "machine")
  },
  "items": {
    "<id>": {
      "id": "iron-ore",
      "pt": "Minério de ferro", "en": "Iron Ore",
      "cat": {"pt": "Metais e minérios", "en": "Metals & ores"} | null,
      "icon": "https://media.wikily.gg/…png" | null,
      "tr": "official" | "likely" | "guess" | "machine" | "missing",    // tier of the pt name that won
      "raw": true,                       // input is_raw (computed if missing): a leaf by default
      "obtain": {"pt", "en"} | null,     // pt from the names files' "__obtain" text map, else English
      "kind": "item" | "building" | "station" | "group" | "quality-variant" | "virtual" | "action",
      "listed": true,                    // false = hidden on the wiki. The UI hides it by default
      "unobtainable": false,             // true = nothing gives it in 1.010. The UI hides it by default
      "recipes": ["<recipe id>", …],     // every recipe whose main output is this item, best first
      "defaultRecipe": "<recipe id>" | null,   // null = leaf (raw, no usable recipe, or trapped in a cycle)
      // optional:
      "members": ["<item id>", …],       // kind "group": the concrete items that can fill it ("Any Newspaper")
      "runes": {"red": 3},               // alchemy rune values
      "stub": true                       // invented by build.py for a dangling reference (hard error)
    }
  },
  "stations": {
    "<station-id>": { "pt", "en", "tr", "icon": url | null }   // id = the input station_id (an item id), else slug(name)
  },
  "recipes": [
    {
      "id": "reinforced-plank",
      "out": {"item": "<id>", "qty": 1 | null, "note"?: {"pt", "en"}},   // qty null only when noexp (grow);
                                                     // note = made_text when it says more than qty
                                                     // ("3 (5 with Cook II)": the page reads the perk bonus)
      "station": "<station-id>" | null,              // null for buildings (built in the world)
      "in": [ {"item": "<id>", "qty": 2, "note"?: {"pt", "en"}} ],   // duplicate lines are merged
      "tech": {"pt", "en", "id", "type": "technology" | "quest" | "perk"} | null,  // from unlock
      "type": "hand_craft" | "star_craft" | "auto" | "factory" | "building" | "alchemy" | "grow",
      "cd": true,                 // calculator_default (wikily's own pick)
      "listed": true,             // false = hidden on the wiki
      "noexp": false,             // true = never expand (grow: unknown yield)
      "cyc": false,               // true = an input can lead back to this output (raw items as leaves)
      "alt": ["<station-id>", …], // alt_stations
      "ext": {"pt", "en"} | null, // station_extension needed on the station
      "extra": [ {"item", "qty": n | null, "note"?: {"pt", "en"}} ],  // extra_outputs (by-products, chance)
      "mastery": {"type": {"pt", "en"}, "level": 4} | null,
      "ticks": 5 | null,          // time_ticks
      "energy": 2 | null,         // energy_per_tick
      "example": false,           // inputs_are_example (alchemy: inputs are one suggested mix)
      "runes": {"red": 1, …} | null,   // rune_requirement (alchemy)
      "zone": {"pt", "en"} | null,     // building area variant
      "star_quality"?: {"silver": 6, "gold": 10},   // star_craft thresholds (successful ticks; text if not "N successful ticks")
      "name"?: {"pt", "en"}       // only when it says more than the output name ("Board (Sawhorse)")
    }
  ]
}
```

### How `defaultRecipe` is chosen

1. A raw item gets `null`: it stays a leaf, but its recipes are still listed for a manual choice.
2. Otherwise build.py looks at the item's `recipes` from best to worst, skipping `noexp` and `cyc` recipes. The
   order is: `calculator_default` first, then listed before unlisted, then by type
   (`hand_craft > star_craft > auto > factory > building > alchemy > grow`), then input order.
3. If no recipe is left, the result is `null`. This happens when every recipe loops back to the item, for example
   the bones/brain/... "Improve organ" upgrades, which consume the item they produce.

In the real data, the graph of default recipes has no cycles. The UI must still guard against cycles, because
the user can pick another recipe.

### Translation layers

Names files map an **exact English string** (item name, station, category, unlock name, mastery type, zone, recipe
name) to a pt value: `{"pt": "...", "source": "...", "confidence": "official|likely|guess"}`. Lookups ignore case and
extra whitespace. Keys starting with `_` (such as `_meta`) are ignored. `__obtain` is a free-text map
`{"<English obtain/note text>": "<pt>"}`.

When several layers have the same key, the best tier wins:
**official > likely > guess > machine**. An entry is `machine` when its `source` is `"machine"` or its file name
contains `.machine.`. If the tiers are equal, the first file given wins. The pipeline also accepts a bare string
value (treated as a guess) and an unknown confidence (treated as a guess); both are logged as coercions.

**Derived names** (pt only, tier `likely`, source `derived`; a synthetic last layer, so an official entry for the full
name, or a `likely` entry in a names file, still wins). Parts must resolve at official/likely:
quality grades `"<Base> (bronze|silver|gold|silver or gold)"` → `"<pt Base> (bronze|prata|ouro|prata ou ouro)"`
(base from `base_item`, else the text before the parenthesis); groups `"A or B"` → `"<pt A> ou <pt b>"`;
`"Any X"` → `"Qualquer <pt x>"`; `"Open (X)"` / `"Repair (X)"` → `"Abrir (<pt X>)"` / `"Reparar (<pt X>)"`.

**Game keys:** when a names entry has `gameKey` (the official file has it for every entry), items get it as an
optional `key` field.

## Page payload (what `--inject` embeds)

`gk2.min.json` stays the full schema. The embedded copy is smaller: `{pt, en}` objects whose texts are identical become
one string (obtain texts, notes, zones, categories…), `items[].id` is dropped (it is the key), and
`meta.collapsed: true` is set. With `--sprite`, `meta.sprite` = `{image, size, cols, rows, icons: {id: [col, row]}}`
(icons limited to known item/station ids plus the `tech:*`, `tp:*` and `branch:*` ids of the technology tree). `meta.version` and `meta.changelog` carry `VERSION` and
`data/changelog.json` when they exist, and `meta.data` = `{"wiki": "1.010", "game": "1.011"}` the game versions of the
two sources (`WIKI_GAME_VERSION`; the official names file's `_meta.game_version`, else `GAME_TEXT_VERSION`), shown in
the footer (page only: `gk2.json` does not have them). The page's `GK.data` normalizes both forms.

`--artifact` (needs `--out`): Claude Artifacts wrap the page in their own document, so the output has no doctype,
`<html>`, `<head>`, `<body>`, charset or viewport meta (removed outside `<script>`/`<style>` only; the page then
starts with `<title>`), and every remote `icon` URL is set to `null` (the Artifact CSP blocks external images:
icons come from the sprite, else a letter tile). `preview.html` (same content inside a minimal skeleton) is written
next to it for local viewing. The source page keeps its skeleton.

### `techs` (the technology tree, page only)

With a techs file (`--techs`, default `data/techs.json`), `build.py` first aligns every recipe `tech` of type
`technology` with the tree's names (`apply_tech_names`: the tree has the official game names, e.g. "Tecido
(Engenharia)" where the recipes said "Tecido (Construção)"; quests and perks keep theirs), then embeds
`techs_payload()` (about 85 kB on the real data, test limit 250 kB):

```jsonc
"techs": {
  "tp":       { "red": {"pt", "en", "color": "#d0453a", "icon": "tp:red"}, "green": {...}, "blue": {...} },
  "branches": { "building": {"pt": "Engenharia", "en": "Building", "order": 0, "icon": "branch:building"}, ... },  // tab order
  "techs": { "<slug>": {
      "pt", "en", "tr"?,                  // tr only when not "official"
      "branch", "column", "y",
      "cost": [red, green, blue],
      "parents"?: [slug], "hidden"?: true, "given"?: true, "listed"?: false,
      "rep"?: {"who": {"pt", "en"} | "same", "level": 40},
      "unlocks"?: [ {"item"?, "kind", "pt"?, "en"?, "tr"?, "station"?} ],   // names only when they differ from the item's
      "icon"?: "<item/station id | tech:slug>", "notes"?: {"pt", "en"}
  } }
}
```

Dropped from `data/techs.json`: `meta` (except `tp`), `icons` (URLs; the sprite has the images), `id`, `x`,
`children` and `recipes` (the page derives both), and every default value. `GK.tech` (`src/js/tech.js`) reads
the block and rebuilds the full records.

### `days` (the 6-day week, page only)

With a days file (`--days`, default `data/days.json` when it exists), the page embeds `days_payload()`: the file's
`{meta, days}` with the days sorted by `order` (file order on ties), `mentions` dropped (`DAYS_DROP`: the page
never reads them; the events keep their `quote`), every other field kept, null values and empty lists dropped (the page reads a missing field as `null` / `[]`). `gk2.json` does not carry it. The sprite keeps the
ids `day:<id>` and each day's `sprite` value, so `make_sprite.py` icons with those names are drawn by the page.

```jsonc
"days": {
  "meta": { "week_length": 6, "order_confidence": "...", "notes": {"pt", "en"} },
  "days": [ { "id": "sloth", "order": 0, "sin": {"en", "pt"}, "name": {"en", "pt"}, "tr", "sprite"?, "glyph"?, "color"?,
              "events": [ { "kind": "npc|merchant|church|battle|quest|event|other", "en", "pt", "tr", "who"?, "source"?,
                            "confidence": "high|medium|low", "items"?: [itemId] } ] } ]
}
```

`GK.data` keeps it as `GK.data.get().days` (`ui/days.js` wraps `GK.data.load` for that). The player's current day
lives in the synced store fields `day` (a day id) and `dayNumber` (the HUD counter, optional); the wheel order for
`advanceDay()` is the order of this block.

## Reports

- `data/report-l10n.md`: every item, station, extension, category, tech, mastery, zone and recipe name whose `tr` is
  `missing`, `machine` or `guess`. Each kind is split into "missing" and "needs review", sorted by **uses** (number
  of recipes that reference the name), most used first. It ends with names-file keys that matched nothing (likely
  typos).
- `data/report-build.md`: inputs, counts (by kind and type), notes, **input coercions** (what had to be fixed, with
  examples), a cycle table, and every error, warning and info.

## Validation (`validate.py`)

| severity | code | meaning |
|---|---|---|
| error | `dangling-ref` | recipe output, input, extra output or station not defined |
| error | `stub-item` | item invented by build.py for a reference that is not in items.en.json |
| error | `duplicate-id` | duplicate item or recipe id (the first one is kept) |
| error | `bad-qty` | qty that is not a number > 0 (output `null` is allowed only on `noexp`) |
| error | `bad-default` | `defaultRecipe` unknown, not producing the item, or `noexp` |
| warning | `zero-inputs` | recipe with no inputs (free buildings, zombie production) |
| warning | `cycle` | strongly connected component of item → inputs, including self-loops, over all expandable recipes |
| warning | `raw-with-recipe` | item flagged raw that is the output of an expandable recipe with inputs |
| warning | `orphan` | item that no recipe produces, consumes or uses as a station |
| warning | `duplicate-input` | same input listed twice (build.py merges these, so this shows up only on hand-made JSON) |
| warning | `cyclic-default` | `defaultRecipe` flagged `cyc` |
| info | `multi-recipe` | item with more than one recipe |
| info | `cycle-trapped` | item in a cycle whose every expandable recipe is `cyc`, so it can only be a leaf |

## Adding a language (for example Spanish)

1. Create `data/names.es.json`, keyed by the same English strings. The value field is still called `pt`, or use
   `name` or `value`; all three are accepted.
2. Build with `python3 -I scripts/build.py --lang es=data/names.es.json` (comma-separate several layers:
   `es=data/names.es.json,data/names.machine.es.json`).
3. Every localized object then gains an `es` field (English fallback), items and stations gain `tr_es`,
   `meta.langs` becomes `["pt", "es", "en"]`, and `data/report-l10n.es.md` is written.
4. In the UI, add an `i18n.es` dictionary and read `obj[lang] ?? obj.en`.

The code needs no other change. To make `--lang es=…` the default, add it to `specs` in `main()`.

## Fixtures

`scripts/fixtures/` holds 16 items, 13 recipes, two names layers and `page.html`. They cover:

- a dangling ref (`glue`)
- a 3-item cycle (beet → seed → beet, beet → fertilizer → beet)
- an item with two recipes, where `calculator_default` beats `hand_craft`
- a grow recipe with `qty: null`
- an output of 2 (1 log → 2 planks) and an output of 5 (nails)
- a zero-input recipe, orphans, and a raw item with a recipe
- missing, guess and machine translations, and layer precedence
- odd input shapes: an English-name ref, a string qty, an `[item, qty]` pair, a string output, a duplicate input
  line, a list as `obtain`, a bare-string name entry, and an unknown confidence
- a `</script>` inside a string

The technology tests (`TechsBuild`, `RealTechs` in `test_build.py`) use a 3-tech tree written inline (`FIX_TECHS`:
a given root, a hidden child with a reputation gate, a second branch). They cover `apply_tech_names`, the compact
`techs` payload, the sprite filter, `--techs` / `--no-techs` in src and inject mode, `GK.tech` itself (run in
node with a stub `GK.data`, skipped without node) and, on the real data, the payload size (< 250 kB) and the
recipe names in `gk2.json`.
