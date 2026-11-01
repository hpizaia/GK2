# Duplicate GK2 Companion for yourself

**English** · [Português](duplicar.md)

A step-by-step guide to running your own copy: your own Claude Artifact, a static site, another language, or a starting point for a planner for a different game. Steps 1 to 3 are enough for a working copy; the rest is only needed when you want fresh data.

All commands run from the project root. Use `python3 -I` (isolated mode). Quote any path that contains spaces.

## 0. What you need

| Need | For | Required? |
|---|---|---|
| **Python 3** (standard library only) | everything: build, data, tests | yes |
| **git** | cloning, seeing what a data refresh changed | yes |
| **Node** | `scripts/test_calc.mjs` (planner maths, storage, sync) | optional |
| **cwebp** (`brew install webp`) | the lossless WebP icon sprite in `make_sprite.py` (or `--png`, without it) | only to remake the sprite |
| **Pillow** | faster sprite packing in `make_sprite.py` (there is a stdlib fallback) | optional |
| **Windows + Graveyard Keeper 2** (Steam) | exporting the official names from your own game files | optional |
| **Claude account + [Claude Code](https://claude.com/claude-code)** | publishing as a Claude Artifact with per-account sync | optional |

## 1. Get the code

```sh
git clone https://github.com/hpizaia/GK2.git my-gk2
cd my-gk2
```

Or use **Fork** on GitHub and clone your fork. The repository already contains the built data (`data/gk2.json`, `data/techs.json`, `data/days.json`) and the icon sprite (`data/sprite.json`), so nothing needs downloading yet.

## 2. Build and check

```sh
python3 -I scripts/build.py           # writes prototype/index.html, dist/index.html, dist/preview.html, CHANGELOG.md
python3 -I scripts/test_build.py
python3 -I scripts/test_techs.py
node scripts/test_calc.mjs            # optional
```

Open `dist/preview.html` in a browser, or serve the dev page:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory prototype   # http://127.0.0.1:8765/
```

`build.py` is idempotent: a second run with the same inputs prints `wrote nothing (all outputs up to date)`. It exits with `1` on data errors (and then writes no `gk2.json`) and `2` on usage or file errors.

## 3. Publish

### Option A: Claude Artifact (with per-account sync)

1. Open the project folder in **Claude Code**.
2. Ask: *"Publish `dist/index.html` as a Claude Artifact, declaring the `db` and `user` capabilities."*
   - `db` gives each viewer a private document in the artifact's database; `user` tells the page who is viewing. Together they power the sync. Without them the page still works and shows "This device only".
3. Claude returns the artifact link. Artifacts are **private** by default; share from the page's own menu.
4. **Later releases:** ask Claude to *republish `dist/index.html` to the same artifact URL*, without passing capabilities (so the page keeps `db` and `user`). A new URL would leave your users' saved plans behind.

`dist/index.html` is made for this: it has no `<html>`/`<head>` skeleton (the Artifact viewer adds one), every icon comes from the embedded sprite (the Artifact sandbox blocks external images), and all CSS and JS are inline.

### Option B: any static host (no sync)

Copy `dist/preview.html` to your host and rename it `index.html`. For **GitHub Pages**, for example:

```sh
mkdir -p public && cp dist/preview.html public/index.html
# then push public/index.html to a gh-pages branch, or deploy public/ with a GitHub Pages Actions workflow
```

Progress is kept in the browser's `localStorage` only. Fonts load from Google Fonts; everything else is in the file.

## 4. Refresh the recipe data (wikily.gg)

Only when the game or the wiki changes. First check that the wiki already describes the new game version. Respect the wiki: the fetcher waits 1 second between requests, and the data is © NX Software (see [Credits and rights](../README.md#credits-and-rights)); keep your copy non-commercial.

```sh
mkdir -p data/raw/days
for s in recipes items buildings crafting-stations technologies alchemy-formulas quests; do
  python3 -I scripts/fetch_dataset.py "$s" data/raw || break
done
cp data/raw/api-quests-all.json data/raw/days/probe-quests.json   # quests that ask for items
python3 -I scripts/build_dataset.py "$PWD"
git diff --stat data/items.en.json data/recipes.en.json
```

- Raw pages land in `data/raw/` (ignored by git, about 19 MB).
- `build_dataset.py` prints counts and problem lists (`dangling`, `unmatched calc`…). Compare with the previous run; normally they are empty or nearly so.
- The optional `data/raw/calculator-props.json` (which recipe the wiki's calculator prefers) sits behind a browser challenge; see "Calculador" in [`docs/atualizacao.md`](atualizacao.md).
- Portuguese names live in three layers: `data/names.official.pt-BR.json` (from the game, step 5), `data/names.manual.pt-BR.json` (chosen by hand: recipe names, the game's own words, fixes) and `data/names.machine.pt-BR.json` (machine fallback). A new item with no official name needs a hand entry in the machine one. A new recipe shows in English until someone adds it (how to get the name from the Portuguese wiki: "Nomes de receita em português" in [`docs/atualizacao.md`](atualizacao.md), in Portuguese).

## 5. Official names from your own game (optional, Windows)

The pt-BR and English names are the game's own, read from your installed copy. Nothing in the game folder is modified.

1. Copy `tools/exportar-textos/` to the Windows PC with the game and double-click `exportar_textos.bat` (step-by-step for non-programmers in `tools/exportar-textos/LEIA-ME.md`). The stricter `exportar_textos_unitypy.py` also writes all 11 game languages.
2. Bring `gk2_textos.json` back to `data/game-texts/`.
3. Merge the names, keeping the hand-linked entries:

```sh
python3 -I tools/exportar-textos/juntar_nomes.py --atualizar
git diff --stat data/names.official.pt-BR.json
```

Read its output: "pt alterado" (the game changed a translation), "gameKey sem texto" (a key that disappeared) and "conferir à mão" (names with an inline icon).

## 6. Item facts, icons, technologies and days

```sh
python3 -I scripts/build_facts.py           # data/facts.json: who sells, who buys, study, requests (from the step 4 cache)
python3 -I scripts/build.py --no-src        # data only: data/gk2.json and the reports
python3 -I scripts/fetch_icons.py           # data/icons/<id>.png, only what is missing (ignored by git)
python3 -I scripts/build_techs.py           # data/techs.json (exit 1 if the tree is broken)
python3 -I scripts/fetch_icons.py --techs   # technology, point and branch icons
python3 -I scripts/make_sprite.py           # data/sprite.json + data/sprite.png
python3 -I scripts/build_days.py            # data/days.json, from the game texts + the EVENTS table in the script
python3 -I scripts/test_techs.py
```

- `build_techs.py` reads `data/gk2.json`, so it runs after the data-only build.
- The day events are short hand-written lines in `scripts/build_days.py` (`EVENTS`), each tied to an official game text. To add or fix one, edit `EVENTS` and rerun. Details: [`data/README-days.md`](../data/README-days.md).

## 7. Full build, version, output

```sh
python3 -I scripts/build.py
python3 -I scripts/test_build.py && python3 -I scripts/test_techs.py && node scripts/test_calc.mjs
```

| Output | What it is |
|---|---|
| `dist/index.html` | The Artifact page (publish this to Claude) |
| `dist/preview.html` | The same page with a document skeleton (open locally, or host statically as `index.html`) |
| `prototype/index.html` | Development page |
| `data/gk2.json` | The merged dataset (schema in [`scripts/README-build.md`](../scripts/README-build.md)) |
| `data/report-build.md`, `data/report-l10n.md` | Build report (must show 0 errors) and untranslated names, most used first |
| `CHANGELOG.md` | Generated from `data/changelog.json`. Do not edit by hand |

To release: bump `VERSION`, add an entry at the top of `data/changelog.json` with `"date": null` and short `pt` and `en` lines, then `python3 -I scripts/build.py --release` (it dates the entry and refuses if `VERSION` and the changelog disagree). Then republish (step 3).

## 8. Add a language (example: Spanish)

The data side:

1. Create `data/names.es.json`, keyed by the **exact English text** of each name, with values like `{"name": "Espada de hierro", "source": "...", "confidence": "official|likely|guess"}` (`pt`, `name` and `value` are all accepted as the value field).
2. Build with `python3 -I scripts/build.py --lang es=data/names.es.json` (comma-separate several layers). Every localised `{pt, en}` object gains an `es` field (English fallback) and `data/report-l10n.es.md` lists the gaps. To make it the default, add it to `specs` in `main()` of `build.py`.
3. The game ships 11 languages. The UnityPy exporter writes them all to `gk2_textos_todos.json`; there is no script yet that turns another language into a names file, so adapt `tools/exportar-textos/juntar_nomes.py` (it links wiki names to game keys through `gameKey`).

The interface side:

4. Add an entry to `LANGS` in `src/js/i18n.js` (`{ code: "es", locale: "es", label: "ES", name: "Español" }`).
5. Add an `es: {...}` block to every `GK.i18n.add({ pt: {...}, en: {...} })` call (16 modules: `grep -rl "GK.i18n.add" src/js`). Missing keys fall back to Portuguese.
6. Rebuild. Details: "Adding a language" in [`scripts/README-build.md`](../scripts/README-build.md#adding-a-language-for-example-spanish).

## 9. Change the look

- **Colours, fonts, spacing:** `src/css/tokens.css`. Dark (night) is on bare `:root`; light (parchment) is defined twice, under `@media (prefers-color-scheme: light)` and under `:root[data-theme="light"]`. Change both light blocks together.
- **Fonts:** `--f-display` and `--f-body` in the tokens; the Google Fonts link is in `src/index.html`.
- **Name of the app:** `<title>` in `src/index.html` and `app.title*` in `src/js/ui/header.js` (both languages).
- Design rationale: [`docs/projeto/DESIGN.md`](projeto/DESIGN.md). Rebuild after any change in `src/`; never edit `dist/` or `prototype/`.

## 10. Add a feature

Each feature is its own module (`src/js/ui/<name>.js`, optional `src/css/<name>.css`), listed in `src/manifest.json`, with its own strings (`GK.i18n.add`), its own route (`GK.router.register`) and its own panel (`GK.app.registerPanel`). The contract, with an example, is "Adding a module" in [`scripts/README-build.md`](../scripts/README-build.md#adding-a-module-the-contract-for-parallel-work). This is what let several Claude Code agents build features in parallel without touching each other's files.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `build.py` exits 1 | Read `data/report-build.md`: a dangling reference or bad quantity. The previous good `gk2.json` is kept |
| Icons show as letter tiles | `data/sprite.json` is missing or stale: run `fetch_icons.py` (and `--techs`), then `make_sprite.py`, then build |
| `test_techs.py` says `techs.json` is out of date | Rerun `python3 -I scripts/build_techs.py` |
| The Artifact lost everyone's progress | It was published to a new URL, or without the `db`/`user` capabilities. Republish to the original URL |
| Footer chip says "This device only" | No Claude login, or the page was published without capabilities, or it is a static copy. Expected |
