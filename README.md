<h1 align="center">GK2 Companion</h1>

<p align="center">A free crafting planner for <b>Graveyard Keeper 2</b>, made by a fan: pick what you want to build and it adds up every raw material, lists the steps by station in the right order and shows the technologies you still need.</p>

<p align="center">
  <a href="https://claude.ai/artifact/8hp57ZZTFoH6GyDQUdHZAn"><img src="https://img.shields.io/badge/Open_the_app-free_%C2%B7_phone_%26_desktop-e3a24e?style=for-the-badge" alt="Open the app: free, phone and desktop"></a>
</p>

<p align="center"><b>English</b> · <a href="README.pt-BR.md">Português</a></p>

<p align="center">
  <a href="https://github.com/hpizaia/GK2/releases/latest"><img src="https://img.shields.io/github/v/release/hpizaia/GK2?label=version&color=e3a24e" alt="latest version"></a>
  <a href="#languages-and-themes"><img src="https://img.shields.io/badge/UI-EN%20%7C%20pt--BR-8fae5e" alt="English and Brazilian Portuguese"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/code-MIT-green" alt="code: MIT"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/built%20with-Claude%20Code-d97757" alt="built with Claude Code"></a>
  <img src="https://img.shields.io/badge/fan_project-not_affiliated_with_Lazy_Bear-555" alt="fan project, not affiliated with Lazy Bear Games">
</p>

<p align="center">
  <img src="docs/media/hero-en.gif" width="280" alt="Searching for a sword, adding it as a goal and scrolling to the raw materials and the steps per station">
</p>

- **Free, no ads, no account needed.** Open the link and use it, on phone or desktop. If you are signed in to Claude, your plan syncs between your devices; if not, it stays in that browser.
- **Private.** The app has no analytics and no tracking; nobody else can see your plan.
- **Want it offline?** [Download the single HTML file](https://github.com/hpizaia/GK2/releases/latest) and open it in any browser.
- **Wrong name, recipe or a bug?** [Tell me here](https://github.com/hpizaia/GK2/issues/new/choose) (needs a free GitHub account). **No GitHub account?** Leave a comment on the project's Reddit post or on the [project site](https://claude.ai/artifact/Bgn32T3eDPRFydxYoxgWTr).

Made by **Hugo Pizaia**, a Brazilian player who is not a programmer, with [Claude Code](https://claude.com/claude-code) (AI) under his direction. Recipes come from the [wikily.gg wiki](https://wikily.gg/graveyard-keeper-2) and item names from the game's own files: the game content is not AI-generated. In Portuguese the app is called *Companheiro GK2*. Not affiliated with or endorsed by Lazy Bear Games or tinyBuild. [Credits and rights](#credits-and-rights).

## Features

### Planner

#### Goals, raw materials and steps

<p align="center"><img src="docs/media/planner-overview-phone-en.png" width="280" alt="Planner with three goals, the Today bar and the progress card"></p>

- **Goals.** Search in English or Portuguese, accents optional (`swor` finds *Sword*). Set quantities with − / + (hold to repeat).
- **Raw materials.** Everything to gather, buy or already have in a chest, with totals.
- **Steps per station.** What to craft at each bench, how many runs, yield and leftovers. Follow top to bottom: no station depends on one further down.
- **Perks** that change yields ("Cook II") recalculate the plan.

#### Alternative recipes and the checklist

<p align="center"><img src="docs/media/planner-steps-phone-pt.png" width="280" alt="Steps per station with alternative recipe selectors"></p>

- **Alternative recipes.** When an item can be made several ways, pick one; silver/gold quality recipes are labelled.
- **Groups** like "Bream or carp": choose which member you will use.
- **Checklist** with a progress bar, per raw material and per step.

#### "I have N of M"

<p align="center"><img src="docs/media/gif-have-n-of-m-pt.gif" width="280" alt="Marking I have 5 of 9 iron ore, then marking all sticks as owned"></p>

Type how many you already own and the totals drop. "All" removes the item from the plan.

#### Collapse what you are done with

<p align="center"><img src="docs/media/gif-collapse-sections-pt.gif" width="280" alt="Collapsing the Today panel, raw materials, two stations and the steps section"></p>

Collapse the Today panel, raw materials, steps and each station. The app remembers, per device.

(Most images show the app in Portuguese; one tap switches it to English.)

### Technologies still needed

<p align="center"><img src="docs/media/tech-needs-phone-pt.png" width="280" alt="Technologies still needed panel with point totals per colour"></p>

Below the plan, the app lists every technology you have not researched yet that the plan requires (stations included), **in research order**, with the **sum of red, green and blue points**. Tick them off right there. Quests and perks the plan needs show under "Also needed".

### Recipes tab

<p align="center"><img src="docs/media/recipe-detail-phone-pt.png" width="280" alt="Recipe detail for Master Sword"></p>

Every item in the game, with search and filters by category and station. Each item shows **all its recipes** (ingredients, station, technology, mastery, time, energy, silver/gold thresholds, by-products), how to obtain it and **"Used in"**. Add it to your goals or choose which recipe the planner uses.

### Technologies tab

<p align="center"><img src="docs/media/tech-tree-phone-pt.png" width="280" alt="Technology tree, Engineering branch"></p>

All **226 technologies** in 6 branches, with cost, prerequisites, what each one unlocks and notes. Tick **"Researched"**: ticking one marks everything before it. Search by technology or by what it unlocks.

### Days (the week wheel)

<p align="center"><img src="docs/media/gif-days-wheel-today-pt.gif" width="280" alt="Tapping a day on the wheel, confirming it as today and seeing the Today panel in the planner"></p>

The game has a 6-day week shown as a wheel in the HUD. The **Days** tab reproduces it and lists what happens on each day (battles, trade ship, resurrection, town orders, mass…). Tap today's symbol, hit **"Today is this day"**, and a **Today** panel appears at the top of the planner. Tap **Next day** when you sleep in the game. **Calibrate** once with the in-game day counter ("day 60 = Pride") and from then on just type the number. Events that come only from guides, not from the game text, are marked *unconfirmed*.

Each of today's events has a **"done today"** checkbox (it resets when the day changes and syncs across devices), the panel previews **tomorrow** so you can prepare before sleeping, and you can leave one short **note per weekday** ("bring 3 fish to the Fisherman") that comes back on that day. A **Large text** switch in the footer makes everything easier to read from a distance, and the app follows your phone's text-size setting.

### Languages and themes

<table align="center">
<tr>
<td align="center"><img src="docs/media/planner-materials-phone-en.png" width="160" alt="Raw materials in English"><br><sub>English</sub></td>
<td align="center"><img src="docs/media/planner-light-phone-pt.png" width="160" alt="Planner in the light theme"><br><sub>Light theme (parchment)</sub></td>
</tr>
</table>

- **EN / PT** switches everything, item names included. Names come from the **official game files** in both languages; the few that do not are tagged *unofficial*, and you can edit any name (the edit is tagged *edited*).
- **Theme:** dark (night), light (parchment) or automatic.
- **Per-account sync:** goals, quantities, chosen recipes, "have", checks, edited names, researched techs, perks and the current day follow your Claude account. Two devices editing offline are merged field by field when they reconnect.
- **Update history** in the footer, with the version number.

On a computer the planner uses three columns:

<p align="center"><img src="docs/media/planner-desktop-dark-pt-small.png" width="600" alt="Desktop layout with goals, raw materials and steps side by side"></p>

## How it works

- **Recipe data.** Items, recipes, stations, technologies and alchemy from the public datasets API of the [wikily.gg](https://wikily.gg/graveyard-keeper-2) wiki (game 1.010), normalised by `scripts/fetch_dataset.py` + `scripts/build_dataset.py`.
- **Official names.** pt-BR and English names exported from the player's own copy of the game (Steam, version 1.011) with `tools/exportar-textos/` (read-only, Windows). Fallbacks: the GK1 wiki and machine translation, always tagged.
- **One HTML file.** `scripts/build.py` assembles `src/` (one JS module per feature, plain CSS, no framework, no dependencies) plus the data into a single page: `dist/index.html`.
- **Icons.** The Artifact sandbox blocks external images, so every icon is packed into one embedded sprite (`scripts/make_sprite.py`).
- **Sync.** The page declares the Claude Artifact `db` and `user` capabilities: each viewer gets a private document in the artifact's database. `localStorage` is the first source, so it opens instantly and works offline.

Deeper docs (Portuguese): [architecture](docs/arquitetura.md), [data and translation layers](docs/dados.md), [game patch runbook](docs/atualizacao.md), [user guide](docs/guia-de-uso.md), project documents (spec, design, backlog, audit) in [`docs/projeto/`](docs/projeto/). Build options and schema (English): [`scripts/README-build.md`](scripts/README-build.md).

## Run locally, build and test

Requirements: **Python 3** (standard library only). **Node** is optional, for the JavaScript tests. Run everything from the project root; quote paths that contain spaces.

```sh
git clone https://github.com/hpizaia/GK2.git && cd GK2

# data + page -> prototype/, dist/index.html, dist/preview.html, CHANGELOG.md
python3 -I scripts/build.py
# build tests (fixtures + smoke test on the real data)
python3 -I scripts/test_build.py
# technology tree tests
python3 -I scripts/test_techs.py
# planner maths, storage and sync tests
node scripts/test_calc.mjs

# then open http://127.0.0.1:8765/
python3 -m http.server 8765 --bind 127.0.0.1 --directory prototype
```

The repository already contains the built data and sprite, so a fresh clone builds without downloading anything.

**Host it yourself** (no Claude account, no sync): put the release file (or `dist/preview.html`), renamed to `index.html`, on any static host (GitHub Pages, Netlify, a USB stick…). Everything is inline except the Google Fonts stylesheet: no server, no API calls. `dist/index.html` is the Artifact flavour of the same page: it has no `<html>`/`<head>` skeleton because the Artifact viewer adds its own.

| Folder | Contents |
|---|---|
| `src/` | Page source: `index.html` template, `css/`, `js/` (one `GK.*` module per file), `manifest.json` (build order) |
| `scripts/` | Build, validation, tests and data collection ([table](scripts/README.md)) |
| `tools/exportar-textos/` | Exporter for the official game texts (Windows) and `juntar_nomes.py` |
| `data/` | Build inputs and outputs: items, recipes, name layers, techs, days, sprite, changelog |
| `dist/`, `prototype/` | Generated pages. **Edit `src/`, never these.** `dist/preview.html` is the whole app in one file |
| `site/` | The project's presentation page (another Claude Artifact) |
| `docs/` | Documentation ([index](docs/README.md)), the media used here and the project documents (`docs/projeto/`) |

## Duplicate it for yourself

Want your own copy (another language, your own artifact, a fork for a different game)? Follow **[docs/duplicate.md](docs/duplicate.md)** (Portuguese: [docs/duplicar.md](docs/duplicar.md)): requirements, refreshing the data, exporting official names from your own game, icons, building, publishing as a Claude Artifact or on any static host, adding a language and changing the theme.

Contributions and bug reports: [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and rights

<a id="data-and-licence"></a>

GK2 Companion is a **fan project**, made by **Hugo Pizaia**, a Brazilian fan of the game, to make playing it more fun. It is **free**, has **no ads**, sells nothing and makes no profit.

**Not affiliated with or endorsed by Lazy Bear Games or tinyBuild.**

- **The game's art, icons, item names and texts** (`data/game-texts/`, the name layers, `data/sprite.*`): **Graveyard Keeper 2 © Lazy Bear Games / tinyBuild.** Used as fan content, with credit, only to show which item is which. Graveyard Keeper is their trademark. If they ask for anything to be removed or changed, it will be: [open an issue](https://github.com/hpizaia/GK2/issues).
- **Recipe and item data** (`data/items.en.json`, `data/recipes.en.json` and everything derived from them): [Graveyard Keeper 2 Wiki](https://wikily.gg/graveyard-keeper-2) on **Wikily**, © NX Software. No open licence. Permission for this fan use is being requested from the wiki (the icon files were also taken from the wiki's image server, so they are part of that request). Please do not reuse this data commercially.
- **Official Brazilian Portuguese and English names:** Lazy Bear Games / tinyBuild. Read from the game's own text files (`tools/exportar-textos/`), not translated by this project. Fallbacks, always tagged in the app: the Graveyard Keeper (GK1) Fandom wiki and machine translation; game-key mapping from the GK2Thai mod's source CSV.
- **Code** (`src/`, `scripts/`, `tools/`, `site/`, docs): Hugo Pizaia. **[MIT](LICENSE), code only.** The licence file says explicitly what it does not cover: `data/`, the icons and sprite, the game texts, the screenshots and the generated pages that embed them (`dist/`, `prototype/`). Learn from it, fork it for another game, send fixes.

**Made with AI.** The app was built with **[Claude Code](https://claude.com/claude-code)** (Anthropic). The code, design and translations were produced with the AI under Hugo's direction, using several agents in parallel (one per feature module, plus audit, QA and docs agents), and tested in the game. The game content itself is not generated: recipes come from the wiki, names from the game files, and every number is computed from those.

If you hold rights to anything here and want it changed or removed, please [open an issue](https://github.com/hpizaia/GK2/issues).
