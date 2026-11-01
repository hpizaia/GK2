# Graveyard Keeper 2 crafting dataset (English)

Extracted 2026-10-30 from **wikily.gg** (Graveyard Keeper 2 wiki, data reflects game version **1.010** per the wiki's own text).
Built by `scripts/build_dataset.py` from cached API responses in `data/raw/`.

> **Licensing / attribution: read before publishing.** wikily.gg publishes **no open licence** (no CC-BY / CC-BY-SA notice anywhere on the wiki pages, footer, legal notice or terms). The footer says `© 2026 Wikily · NX Software`. The Terms of Service (https://wikily.gg/terms-of-service) say that all intellectual property in the website belongs to NX Software. They also prohibit reproducing the site's contents "by ... spidering, scraping or any other technological means" and using content "for commercial purposes ... without obtaining a license". NX Software is a French SAS (Paris), so the EU *sui generis* database right may also apply. Before redistributing this dataset publicly, ask for permission at **contact@wikily.gg**. At minimum, credit it as: *"Recipe data: Graveyard Keeper 2 Wiki by Wikily (https://wikily.gg/graveyard-keeper-2), © NX Software"*. Game content © Lazy Bear Games / tinyBuild.
> The `icon` URLs point at wikily's media CDN (`media.wikily.gg`), so using them in a page means hotlinking their assets.

## Files

| file | content |
|---|---|
| `recipes.en.json` | array of 695 recipe records |
| `items.en.json` | array of 820 item records (every id referenced by a recipe exists here) |
| `raw/api-<dataset>-offsetNNNN.json` | untouched API pages (cache) |
| `raw/api-<dataset>-all.json` | concatenated rows per dataset |
| `raw/calculator-props.json` | props of the crafting-calculator React island (the calculator's own one-recipe-per-item graph) |

(`raw/l10n/` was not created by this extraction. It belongs to a separate localisation task.)

## Record counts

- **Recipes: 695**
  - `hand_craft` 241, `auto` 80, `factory` 69, `star_craft` 35. Together these are the 425 rows of the wiki's recipe dataset: the 416 listed on /recipes plus 9 unlisted rows (`listed:false`).
  - `building` 225 (construction/build costs of 208 buildings, plus 17 alternative per-area variants; 13 records are unlisted on the wiki)
  - `alchemy` 28 (rune-based alchemy formulas)
  - `grow` 17 (crop-bed harvests, de-duplicated per bed and mastery tier)
  - 66 output items have more than one recipe (alternatives).
  - `calculator_default: true` marks the 406 recipes the wikily calculator uses: one per craftable thing, and every one was matched.
- **Items: 820**
  - by `kind`: `item` 544 (wiki item pages), `building` 130, `station` 87, `virtual` 18, `action` 16, `quality-variant` 15, `group` 10
  - **574 items have at least one recipe** (`recipe_ids` non-empty); **246 have none**.
  - **290 are `is_raw: true`**: 235 items, 23 buildings, 18 stations, 10 groups and 4 quality variants. 91 items are flagged `unobtainable` (the wiki says nothing gives them in 1.010), which leaves 148 obtainable raw items.
  - 41 items carry `alchemy_runes`.

## Schema

### recipes.en.json
```jsonc
{
  "id": "reinforced-plank",            // stable slug (wiki recipe key; "build-<building>[--<area>]", "alchemy-<formula>", "grow-<bed>-m<mastery>")
  "name": "Reinforced Plank",
  "type": "hand_craft",                // hand_craft | auto | factory | star_craft | building | alchemy | grow
  "output": {"item": "reinforced-plank", "qty": 1},   // base qty, no perks
  "extra_outputs": [{"item": "salt", "qty": 1, "note": "1, or 2 with Cremator"}], // by-products / perk- or chance-based bonus outputs
  "made_text": "3 (4 with Engineer)",  // wiki's yield text incl. perk bonus, or null
  "station": "Wooden Anvil",           // station display name; null for buildings
  "station_id": "wooden-anvil",        // id in items.en.json (kind station/building/item), or null
  "alt_stations": ["Iron Anvil", "Steel Anvil"],      // other stations that can run the same recipe
  "station_extension": "Fine Tool Rack",              // required extension on the station, or null
  "inputs": [{"item": "oiled-plank", "qty": 1}, {"item": "bronze-detail", "qty": 2, "note": "..."}],
  "unlock": {"name": "Reinforced Plank", "type": "technology|quest|perk", "id": "reinforced-plank", "url": "..."}, // or null
  "mastery": {"type": "Smithing", "level": 4},        // required mastery, or null
  "time_ticks": 5,                     // base ticks (fewer with higher mastery), or null
  "energy_per_tick": 2,                // null for auto/factory/no-energy recipes
  "tech_points_reward": {"red": 3},    // tech points granted when the craft finishes, or null
  "star_quality": {"silver_at": "6 successful ticks", "gold_at": "12 successful ticks"}, // star crafts only
  "note": "Needs the Fine Tool Rack extension.",      // wiki card note, or null
  "listed": true,                      // false = hidden on the wiki list (unreachable/unused content)
  "calculator_default": true,          // the recipe wikily's calculator picks for this output
  "source_url": "https://wikily.gg/graveyard-keeper-2/items/reinforced-plank",
  // building only:  "zone": "Sawmill"     (area the variant is built in; "note" holds chips such as storage slots)
  // alchemy only:   "inputs_are_example": true, "rune_requirement": {"red":1,"green":4,"blue":2},
  //                 "example_input_combos": [[{item,qty,note?}...], ...], "mix_count": 883
  // grow only:      "output_note": "amount varies with the bed; +1 each with Farmer and Farmer II"  (output.qty is null)
}
```

### items.en.json
```jsonc
{
  "id": "iron-ore", "name": "Iron Ore",
  "kind": "item",          // item | building | station | group | quality-variant | virtual | action | (planted beds are items)
  "category": "Metals & ores",           // wiki category; "Building: <category>" for buildings/stations
  "icon": "https://media.wikily.gg/...png",   // absolute URL or null
  "is_raw": true,          // true when no recipe in this dataset crafts it as main output from >=1 input
                           // (grow recipes and zero-input zombie production do not count, so crops, logs and ore are raw)
  "obtain": "Produced at the Zombie Miner. Sold by the Trademaster. Gathered from iron ore deposits.",  // wiki summary minus "used in" sentences
  "sources": ["Crafting", "Traders", "Gathering"],    // wiki source tags (items only)
  "page_url": "https://wikily.gg/graveyard-keeper-2/items/iron-ore",
  "listed": true,
  "recipe_ids": ["iron-ore"],             // recipes whose main output is this item
  // optional: "unobtainable": true, "alchemy_runes": {"red":3}, "building": {category, zones[], listed},
  //           "group_members": [...ids] (kind group), "base_item": "story" (kind quality-variant)
}
```

Special item kinds:
- `group`: a wildcard ingredient such as "Any Newspaper", "Bream or Carp" or "Newspaper (silver or gold)". `group_members` lists the concrete ids that can fill it.
- `quality-variant`: a bronze, silver or gold grade such as "Story (gold)". The wiki has no separate page for these.
- `virtual`: an item referenced only by name, with no wiki page (prayers, Story, Newspaper, Injection/Solution...).
- `action`: a recipe "output" that is not an item: PR-machine zombie-limit buffs, repairs, opening doors, Summon Fairy.

### facts.json

`scripts/build_facts.py` reads `raw/api-items-all.json` (no download), `game-texts/gk2_textos.json` and
`names.official.pt-BR.json` (plus `raw/days/probe-quests.json` for the quests that ask for an item), and writes `facts.json`; `scripts/build.py` merges it into `gk2.json` and the page when
it exists (src mode or the default inputs). Re-run it after `fetch_dataset.py items` or a names update.

```jsonc
{
  "meta": {"source": "...", "counts": {"items": 544, "where": 292, "buy": 176, "fish": 22, "energy": 59, "insanity": 17,
           "buff": 14, "stack": 544, "sell": 197, "sell_priced": 132, "sell_likes": 75, "price": 197, "study": 333,
           "study_faith": 39, "asked_quest": 81, "asked_quest_lines": 93, "quests": 60, "asked_town": 29,
           "asked_order": 22, "asked": 122, "names": 215, "names_unofficial": 34, "buffs": 15}},
  "names": {"vegetable-stand": {"en": "Vegetable Stand", "pt": "Banca de Vegetais", "key": "Vegetable_t1"},
            "tree": {"en": "Tree", "pt": "Árvore", "tr": "machine"}},          // tr: machine | missing = not official
  "buffs": {"building-spirit-ii": {"en": "Building spirit II", "pt": "Espírito da Engenharia II",
            "d": {"en": "You temporarily have +2 Building mastery.", "pt": "..."}, "key": "buff_talent_orange_2"}},
            // "dtr": "machine" when the description is a translated wiki chip (no game text)
  "items": {
    "pumpkin":      {"where": [["buy", "vegetable-stand", 2]], "use": {"en": 6}, "stack": 50},
    "pumpkin-soup": {"use": {"en": 20, "enB": [22, "steamed-up"], "buff": ["building-spirit-ii", 450, 1]}, "stack": 30},
    "bream":        {"where": [["fish", "village", "breadcrumb-bait", 50, 33.3]], "stack": 20},
    "polished-bronze": {"sell": [["furniture-maker", 54, 56, 20], ["jeweler", 55, 56, 40], ["smithy", 54, 55]],
                        "price": 75, "study": [30, 0, 20, 3],
                        "asked": {"q": [["the-nun-with-the-hairy-ass", 2, "nun"]], "t": [["jeweler-ii", 5], ["jeweler-iii", 10]]}},
    "goldfish":     {"sell": [["fish-stand"]], "price": 72, "fix": 1, "study": [50, 50, 50, 3, 3]}
  }
}
```

- `where` entries are `[kind, ref, ...]`; `ref` is a `names` key or `@<item id>` (the item's own name is used).
  `buy`: `[.., trader, level]` (level omitted = from the start, `"talk"` = sold in conversation only; trader grades
  Bronze/Silver/Gold collapse to one entry with the lowest level). `fish`: `[.., spot, bait item id, % by day,
  % at night]`, the best bait of that spot. Other kinds: `gather quest battle chest found looter autopsy burial
  container town study church start outfit resurrect character`. Wiki "Barracks" sources are skipped (the build
  recipe says it). Order: buy, fish, gather, then wiki order.
- `use`: `en` energy, `ins` insanity, `enB` / `insB` = `[value under the buff, buff key]` (the stat chip "+22 with
  Steamed Up"), `buff` = `[buff key, seconds, 1 if using another restarts the timer]`.
- `sell` (item card "Quem compra", wiki `boughtBy`): one `[trader, lo, hi, likes, likesLevel, level]` per buyer, trailing
  zeros trimmed. `lo`/`hi` = what it pays for one at its usual stock, lowest/highest over trader levels 1-3 (`hi` 0 =
  same as `lo`; `lo` 0 or absent = the wiki gives no number); a price that only holds at an empty usual stock ("pays
  only 1 bronze") counts only when it is the only one. `likes` = the most Likes a week from selling to it (-1 =
  "earns Likes", no amount), `likesLevel` = first trader level that gives them, `level` = first trader level that
  buys it (0 = level 1). Money is in bronze (1 silver = 100 bronze, 1 gold = 100 silver).
- `price`: the base price (the ceiling, paid when the trader is short of stock), only for items someone buys (197 of
  the 306 with a price). `fix: 1`: every buyer pays that fixed price (fish and the like; stock does not change it).
- `study` (item card "Estudar", wiki `studyCards`): `[red, green, blue, science, faith]`, trailing zeros trimmed:
  the Study Table points by colour, then the Science and the Faith the study costs.
- `asked` (item card "Pedido em"): `{q: [[quest, qty, giver]], t: [[town building, qty]], o: [[trader, qty, level,
  likes]]}`, each key only when non-empty. `q` from `raw/days/probe-quests.json` `needs` (items handed over or carried;
  "given to you" skipped; no quantity = 1), in story order; `t` = town restorations and `o` = town orders (wiki
  `usedIn` kinds Town / Order; the urgent and the normal order of one trader level merge into one with the most
  Likes). Repairs, battles, bait, sermons, bags, combat and the game description are left out on purpose. Quest,
  giver and town names are `names` keys. Quest givers with no entry in the game's name table but spelled out in
  official dialogue (Davy the Dagger, Hans, Sven, Old God) keep that text (no `tr`, the dialogue line as `key`); the
  other 7 (Captain, Village guards...) come from the script's glossary (`tr: "machine"`, shown "não oficial").
- In `gk2.json` the fields land on `items[id]` and the tables in `meta.refs` (`{names, buffs}`, game keys
  dropped).

## Endpoints / URLs used

All JSON came from the wiki's public dataset API (plain GET, normal browser User-Agent, 1 request/s):
```
https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/recipes/list?limit=120&offset=N&locale=en&sortField=name&sortDir=asc
https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/items/list?...             (544 rows)
https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/buildings/list?...         (208 rows)
https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/crafting-stations/list?... (85 rows)
https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/technologies/list?...      (226 rows)
https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/alchemy-formulas/list?...  (28 rows)
```
- The server caps `limit` at 120. Leaving out `fields` returns every column. The /recipes page itself requests `fields=...&filters=[{"fieldRef":"listed","value":"yes","operator":"equals"}]`.
- The HTML pages (https://wikily.gg/graveyard-keeper-2/crafting-calculator and /recipes) sit behind a Cloudflare managed challenge that returns 403 to curl. They were opened once in a normal browser session, and the calculator's server-rendered props (`self.__next_f` RSC payload, island `CraftingCalculatorIsland`: `craftables`, `graph`, `meta`, `stationIcons`) were saved to `raw/calculator-props.json`. Those props were used only to set `calculator_default`. The API endpoints are not behind the challenge.
- Also consulted for context (not stored): /graveyard-keeper-2/crafting (explains ticks, mastery and tech points), /terms-of-service, /legal-notice.

## Known gaps and caveats

- **Base amounts only.** Perk effects appear only as text (`made_text`, `note`, `extra_outputs[].note`), for example "4 (6 with Cook II)" or "50% chance with Glassworker".
- **Alchemy is combinatorial.** Any 2–3 ingredients whose runes add up to the formula's runes work (up to ~900 mixes). `inputs` holds the wiki's first suggested best mix plus 1 `alchemy-flasks`, flagged `inputs_are_example`. The other suggestions are in `example_input_combos`, and rune values per ingredient are in `items[].alchemy_runes` (41 items). Rune-graded "Alchemic Powder (2 red)" style inputs are mapped to the single `alchemic-powder` item, with the grade in `note`.
- **Grow recipes** have `output.qty = null`, because the yield "varies with the bed". Crops and seeds are marked raw. The matching planting step is the `star_craft` "Plant X seed" recipe, whose output is the planted bed item (`beet-bed` etc.).
- **Building variants.** When a building can be built in several areas at different costs, the first area is the main `build-<slug>` record and the others are `build-<slug>--<area>` records. 29 build records have no inputs, either because they are free (grave areas, garden tablets) or because the wiki gives no material cost (PR machines).
- **Station repairs are missing.** Some stations come from repairing a broken object (for example the Kitchen Oven, "repairing the Broken Oven with 2 Piece of stone"). These appear only in the station's `obtain` text, not as recipes, so a few stations (Kitchen Oven, Kitchen Table, Assembly bench...) are `is_raw:true`.
- **Group ingredients.** "Any Wine" uses the real `wine` item page. The other groups are synthetic, and their `group_members` are derived from names.
- **Unlisted content is kept.** 22 recipes have `listed:false` (hidden on the wiki: unbuildable or unused content), and 91 items are flagged `unobtainable`. Filter both out in the UI.
- **Factory (conveyor) recipes are included** (`type: factory`). The wikily calculator leaves them out.
- **Ids are wiki slugs**, so they stay stable across re-fetches. Synthetic ids are slugified names (`any-newspaper`, `story-gold`).
- **Tech points** are rewards for finishing the craft, not costs. Technologies' own costs come from `raw/api-technologies-all.json` and are exported by `scripts/build_techs.py` into `data/techs.json` (see `README-techs.md`).
- **Version.** Data matches the wiki on 2026-10-30, which describes game version 1.010. Re-run `scripts/fetch_dataset.py <slug> data/raw` for each dataset, then `scripts/build_dataset.py <project_dir>`.
