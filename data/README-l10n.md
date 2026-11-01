# pt-BR names for Graveyard Keeper 2 — layers, sources and findings

## The three layers (since 2026-11-01)

`scripts/build.py`, `scripts/build_techs.py` and `scripts/build_facts.py` read the same three files through one lookup, `scripts/name_layers.py` (default `--names`, best first). Every file is an object keyed by the **exact English name**; `_meta` and other `_` keys are skipped.

| file | what | source / confidence |
|---|---|---|
| `data/names.official.pt-BR.json` | the game's own text (1,020 names), joined by `gameKey` with `tools/exportar-textos/juntar_nomes.py --atualizar` | `game-files` / `official` |
| `data/names.manual.pt-BR.json` | chosen by hand (318): the 231 recipe names (field `recipes`) and the one correction, the 9 category names with the game's own words (field `game`), the 77 GK1 wiki names | `wikily-pt` / `likely`, `game-files` / `official`, `derived` / `guess`, `fix` / `likely`, `gk1-wiki` / `likely` |
| `data/names.machine.pt-BR.json` | Claude's translation, the fallback (1,066 names + 736 `__obtain` / `__notes` texts), with the `gameKey` / `kind` / `priority` of every name | `machine` / `guess` (the whole file, by its name) |

**Rule:** a correction (`fix`) > official > by hand > machine. Inside a file, and between files on a tie, the first one wins. `build_techs.py` puts the game text table (`data/game-texts/gk2_textos.json`) right after the official file; `build_facts.py` reads that table first, then the layers. `build_days.py` takes its names straight from the game table by key.

- **Recipe names** (`recipes` entries of the manual file): 159 `wikily-pt` / `likely` (the wikily.gg API with `locale=pt-br`, lowercase: `pt-BR` and `pt` come back in English; the wiki builds them from the official item and station names, checked 252/252 and 425/425), 5 `game-files` / `official` (whole game texts: Aprimorar Jornal I/II, Aprimorar História I/II, Abra a porta), 67 `derived` / `guess` (composed by us from official names: "Construir X (Zona)", "Cultivado no Canteiro de X (maestria Agricultura N)", "X (fórmula de alquimia)"; the page shows them with the "não oficial" badge). Grades are written "(ouro)", "(prata)", "(bronze)" like every other name of the app, never the wiki's "(qualidade ouro)". `wiki_pt` keeps the wiki's text when ours differs. A recipe added by a game patch shows up as missing in `data/report-l10n.md` ("Recipe names"); fetch the Portuguese name with `scripts/fetch_dataset.py <slug> data/raw/pt --locale pt-br` and add the entry by hand (`docs/atualizacao.md`).
- **Corrections (`fix`).** An entry with `"fix": "<reason>"` beats every layer, tier and the game text table, and keeps its own confidence, `likely`: no "não oficial" badge, but no "official" claim either. `gk2_textos.json` and `names.official.pt-BR.json` stay untouched. The only one today: **"Wheat Bed" → "Canteiro de Trigo"** (the game says "Canteiro de Trigorigo", key `garden_wheat`); it fixes the item, the station and the recipe "Cultivado no Canteiro de Trigo".
- **Category names with the game's words** (`game` entries): Construção: jardim, placas do jardim, pátio, casernas, túmulos e columbários, bancos de montagem, estação de produção; Materiais de produção; Suprimentos do Povoado. Left for a check in the game: Building: Metalwork, Book writing, Any Story, Dig.
- **GK1 names** (`gk1-wiki`): the official file covers 76 of the 77; only "Alchemy" → "Alquimia" shows.
- **Machine file merge.** Until 2026-11-01 a second machine layer, `names.pt-BR.json` (GK1 + machine + `gameKey`, made by `build_names.py` / `mt_glossary.py` / `fetch_gk1_langlinks.py`), was read before this one and won every tie. Its 21 names that the app shows and that differ are now the `pt` of the machine file, with the file's own text in `alt_pt` (e.g. "Smithing": `pt` "Metalurgia", `alt_pt` "Ferraria"). The old files and scripts are in git history.
- **Derived names** (`Builder.derive_names` in `build.py`, tier `likely`): quality grades, groups, "Any X", "Open (X)", and "Repair (X)" as **"Consertar (X)"**, like every concrete repair in the game.
- **Item sources** (`meta.refs.names`, glossary `MT` in `scripts/build_facts.py`, tr `machine`): 7 names follow the wiki / game words: Cogumelos pantaneiros, Madeira trazida pela maré, Depósito de minério de ferro / de pedra / de mármore, Buraco de areia, Prateleira quebrada.

## Research before the official text (2026-10-30)

The rest of this file is the research made before the game's text was exported (the export of 2026-10-30, game 1.011: `data/game-texts/gk2_textos.json`, 9,474 keys, report in `data/game-texts/RELATORIO-exportacao.md`). It explains where the GK1 names and the `gameKey` come from.

### Bottom line (then)

- **The game has an official Brazilian Portuguese interface.** The Steam store lists *Português (Brasil)* for interface and subtitles; audio is English only (store API `appdetails?appids=4358690`). The decompiled language table (`LazyBearTechnology/LL.cs` in GitHub repo `Kupie/GYK2_DECOMP`) registers `pt-br` / `pt-BR` / "Português do Brasil", and maps the system language Portuguese to `pt-br`. **There is no pt-PT.** The 11 shipped languages are en, de, fr, pt-br, es, ru, pl, ja, zh_cn, ko, tr.
- **The official pt-BR strings are not published anywhere I could reach.** I found no wiki, mod repo, Steam guide or dump with GK2's in-game Portuguese text. Every pt-BR name in the JSON is therefore either a **GK1 name** (`gk1-wiki`, *likely*) or a **machine translation by Claude** (`machine`, *guess*). None is marked *official*.
- **The official text can be joined in later.** 972 of the 1065 entries carry `gameKey`, the game's own localization key (for example `nails_bronze` or `tech_steel_instruments_1`). If anyone exports the game's `pt-br` locale from a copy of the game, replacing values by `gameKey` turns them into official entries mechanically.

### Output format of the old `names.pt-BR.json` (its entries now live in the manual and machine files)

`data/names.pt-BR.json` is keyed by the exact English names in `data/items.en.json` (`name`), plus the names from `data/recipes.en.json` (`station`, `alt_stations`, `unlock.name`, `mastery.type`) and the item `category` values.

```json
"Bronze Nails": {"pt": "Pregos de bronze", "source": "machine", "confidence": "guess",
                 "kind": ["item"], "priority": 1, "gameKey": "nails_bronze"}
```

- `priority`: 1 = listed, obtainable item; 2 = station; 3 = category; 4 = technology; 5 = everything else (buildings, actions, unlisted or unobtainable items, quality variants).
- `_meta` holds the counts and the legend. Skip that key when you load the file.

| source / confidence | entries |
|---|---|
| gk1-wiki / likely | 77 (66 of them priority 1) |
| machine / guess | 988 |
| **total** | **1065** (p1 453, p2 89, p3 57, p4 195, p5 271) |

### Leads, one by one

### 1. wikily.gg: no localization (did not work)
- `curl` and WebFetch both get a Cloudflare challenge (HTTP 403) on `https://wikily.gg/graveyard-keeper-2/`. The locale routes `/pt/`, `/pt-br/`, `/pt-BR/` and `/br/` also return 403. `robots.txt` is reachable.
- I read the JSON payloads the other agent saved (`data/raw/api-*-all.json`): there are no `locale`, `lang`, `pt` or `translations` fields in any record. Per the coordinator, the API's `?locale=` parameter is ignored and always returns English (wrong, found on 2026-11-01: `locale=pt-br`, lowercase, returns Portuguese; see the update at the top).
- Conclusion at the time: wikily is English only. The data was still useful: icon file names and the English names were joined to game keys.

### 2. Local game install (not present)
- Steam library `~/Library/Application Support/Steam/steamapps/` (24 appmanifests, `common/`): GK2 is not installed. Its app id is **4358690**, and no manifest exists for it.
- Epic manifests: only one game, not GK2. There is no GOG folder, and Spotlight finds nothing named "Graveyard Keeper".
- GK2 is **Windows only** on Steam (`platforms: windows`). On a Mac it runs only through Wine or CrossOver; the GitHub repo `ignasave/gravemac-keeper-2` is a script for that.
- **Where the game keeps its text** (from mod tooling, not checked locally): Unity MonoBehaviour assets named `lng_<language>` (e.g. `lng_en`, `lng_pt-br`) inside `<game>_Data/resources.assets`. Each one holds parallel arrays of keys and texts, about 9.4k keys. This is not plain text, so it needs a Unity extractor. Evidence: `GK2Thai/tools/locale_codec.py` and `GK2Thai/docs/TRANSLATION-TH.md` in `Jakkrich/graveyardkeeper2-bepinex-thai-plugin` ("Export source EN from resources.assets (9,370 keys)"). The game also loads community language packs from `Languages/<code>/strings.csv` (`key,value`) plus `language.json` (see `LanguageModLoader.cs` in the decompiled repo and `AcTePuKc/GraveyardKeeper2-Mods/mods/bulgarian-localization`).

### 3. VGTimes "GK2 Codex" and Thunderstore (no pt-BR text)
- `https://vgtimes.com/games/graveyard-keeper-2/files/98320-.html` (read only, **not downloaded**): a 58 kB ZIP holding a BepInEx plugin, `GK2Codex.dll`, by SaintArchI, uploaded 2026-09-23. It is an in-game encyclopedia with Items, Buildings, Zombies and Alchemy tabs. The page says "The UI is fully translated" but lists no languages. Because it runs inside the game, it would show the game's own localized names; it does not ship them as text.
- Thunderstore (`https://thunderstore.io/c/graveyard-keeper-2/`, 36 mods): **CraftTodo** by NalmDevelops claims 11 languages, has no source link, and does not say where item names come from. **GK2LocalizationAPI** (Ice_Box_Studio_GK2) is for a mod's own strings only. **GK2 AutoKeeper** by focabr is EN/PT-BR; its repo is `focabr/GK2-AutoKeeper`, and its Portuguese UI text is the author's own (e.g. "mesa de autópsia", "crematório", "Privação de Sono"). That is weak evidence and was not used as a source.
- GitHub repos reviewed (read-only via API or raw):
  - `Jakkrich/graveyardkeeper2-bepinex-thai-plugin`: `translations/source_en.csv` holds **the game's English locale with its keys** (9,370 keys). It was used for `gameKey`; the copy is at `data/raw/l10n/thai_source_en.csv`. Its other CSVs contain Thai only.
  - `AcTePuKc/GraveyardKeeper2-Mods`: Bulgarian `strings.csv` (`key,value`, Bulgarian only).
  - `Kupie/GYK2_DECOMP`: decompiled C# with no assets. Used to confirm the language list.
  - `NetroScript/graveyard-keeper-2-savegame-editor`: its asset exporter exports English names only.
  - `sarawittel/fiambrerapp`: GK2 item JSON with **Spanish** names (useless for pt-BR). `runoverlabs/graveyard-factory` and `Dragonir44/gk-companion`: English names.
  - GitHub code search for pt-BR in-game phrases and `lng_pt*` found nothing GK2-related.

### 4. Steam (confirms the language, no names)
- Store API, `l=english` and `l=brazilian`: confirms *Português (Brasil)*. The pt-BR store description contains no item names.
- Community guides (`https://steamcommunity.com/app/4358690/guides/`): the Portuguese language filter returns **"No items matching"**. Across about 120 top-rated guides, the only Portuguese ones are an auto-generated interactive-map listing ("[MAPA INTERATIVO]…", which links to wand.gg) and a joke guide. Nothing usable.

### 5. Graveyard Keeper 1 (used, `gk1-wiki`)
- MediaWiki API on `https://graveyardkeeper.fandom.com/pt-br/api.php` and `https://graveyardkeeper.fandom.com/api.php`, with `prop=langlinks` (interwiki pt-br ↔ en). This gave 283 EN→PT pairs. Raw responses are `data/raw/l10n/gk1_*langlinks_*.json` and the merged file is `gk1_langlinks_merged.json`. Script: `scripts/fetch_gk1_langlinks.py`.
- 77 GK2 names matched exactly (case-insensitive), e.g. Iron Ore → Minério de ferro, Log → Tora, Wooden Plank → Placa de madeira, Faith → Fé, Zombie → Zumbi, Morgue → Necrotério, Potter's Wheel → Torno de oleiro, Study Table → Mesa de estudo.
- **How far to trust these:** the pt-BR wiki has 369 articles and is edited by players. Titles usually follow the GK1 in-game text, but some are clearly wrong (`Ash`→"Ash", `Stone block`→"Stone block", `Snake`→"Rato"); I filtered those out. Lazy Bear may also have reworded things for GK2 with a different translation vendor. Hence *likely*, not *official*.

### Other web sources checked (not used as sources)
- `games.gg/pt-BR/graveyard-keeper-2/guides/`: Portuguese articles that keep the item names in English ("Polished Bronze", "Iron Ore").
- `criticalhits.com.br`, e.g. `/dicas/graveyard-keeper-2-como-conseguir-tabuas-de-madeira/` (saved as `criticalhits_tabuas.html`): written on launch day. It translates both *Board* and *Wooden Plank* as "Tábua(s)" and *Potter's Wheel* as "Roda de Oleiro", which shows the writer translated the names himself. Not reliable.
- `playnews.gg/pt-br/guias/...`: returns 403 to curl. These are site-translated articles and not reliable for exact names.

### Scripts (retired 2026-11-01, in git history)
- `fetch_gk1_langlinks.py` crawled the GK1 interwiki pairs (MediaWiki API); `mt_glossary.py` was Claude's EN→pt-BR glossary; `build_names.py data` built `names.pt-BR.json` from both and attached `gameKey`. What they made lives on in `names.manual.pt-BR.json` (GK1) and `names.machine.pt-BR.json` (machine names, `gameKey`).

### Recommendation for the site (then)

1. Show the pt-BR name when it exists and keep the English name visible as secondary text (a tooltip or small grey line), because none of these names are confirmed. Players can then match what they see in the game, and searches can match either language.
2. Mark trust visually: no badge for `gk1-wiki/likely`, and a small "tradução não oficial" mark for `machine/guess`. Search should accept PT, EN and accent-insensitive input ("pa" finds "Pá").
3. Let the user edit any name inline and save it to `localStorage`, keyed by English name or `gameKey`. Offer a JSON export of their corrections so they can be merged back into the names files. The player sees the real game text, so a few corrections per session will quickly turn the common items "official".
4. The best route to fully official names is to export `lng_pt-br` from the player's own copy of the game (Windows or Wine install) and join on `gameKey`. Two ways: the read-only decoder approach in the GK2Thai `locale_codec.py` (it parses the `lng_*` MonoBehaviour from `resources.assets`), or a tiny BepInEx plugin that iterates the keys and calls the game's localization lookup with the language set to pt-br. Either is a one-time job of a few minutes on a machine with the game, and it would change about 970 entries to `game-files/official`.
