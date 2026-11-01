# data/techs.json: the GK2 technology tree (pt-BR / EN)

Built by `scripts/build_techs.py` from the wikily.gg technologies dump. Tested by `scripts/test_techs.py`.

## Regenerate

```sh
cd GK2
python3 -I scripts/build_techs.py            # writes data/techs.json and prints the validation report
python3 -I scripts/build_techs.py --check    # validate only
python3 -I scripts/test_techs.py             # 12 tests on the real inputs (also checks techs.json is not stale)

# icons (only needed when new tech icons show up)
python3 -I scripts/fetch_icons.py --techs    # downloads techs.json `icons` into data/icons/<ns>__<id>.png
python3 -I scripts/make_sprite.py            # data/icons -> data/sprite.json + data/sprite.png
```

Inputs (read-only): `data/raw/api-technologies-all.json`, `data/gk2.json`, the three `data/names*.pt-BR.json`
layers and, if present, the game's own text table `data/game-texts/gk2_textos.json`
(`{key: {en, pt}}`; `build_techs.py --game-text <path>` overrides it). Exit code 1 means a validation error.

## Schema

```jsonc
{
  "meta": {
    "built": "2026-10-30", "count": 226,
    "branches": ["building", "metallurgy", "farming", "theology", "anatomy-and-alchemy", "cooking"],  // tab order
    "langs": ["pt", "en"], "sources": [...],
    "tp": { "red":   {"en": "Red tech points", "pt": "Pontos tecnológicos vermelhos", "tr": "likely",
                      "color": "#d0453a", "icon": "tp:red"},
            "green": {...}, "blue": {...} }
  },
  "branches": { "<branchKey>": { "pt": "Engenharia", "en": "Building", "order": 0, "tr": "official",
                                 "icon": "branch:building" } },
  "techs": { "<slug>": {
      "id": "alchemy-advanced", "pt": "Alquimia Avançada", "en": "Alchemy, Advanced",
      "tr": "official",                 // official | likely | guess | machine | missing
      "branch": "anatomy-and-alchemy",
      "column": 11, "x": 10, "y": 1,    // column is 1-based; x = column - 1; y may be .5 (half rows)
      "listed": true,
      "hidden": false,                  // badge "Hidden": not shown in the tree until revealed / given
      "given": false,                   // badge "Given": granted by the story, nothing to buy
      "cost": { "red": 200, "green": 0, "blue": 100 },
      "parents": ["battle-potions-iii"],          // all must be researched first
      "children": ["practical-potions", "crafting-potions"],   // derived from parents, sorted by column, y
      "rep": null,                      // or {"who": {"en": "Jack", "pt": "Jailson"}, "level": 70}
      "unlocks": [ { "item": "good-alchemist-s-kit" | null, "kind": "item|building|recipe|other",
                     "en": "Good Alchemist's kit", "pt": "Kit de Qualidade de Alquimista",
                     "tr": "official", "station": "jewelry-table" | null } ],
      "recipes": ["..."],               // recipe ids in gk2.json whose tech.id is this slug
      "icon": "good-alchemist-s-kit",   // sprite id: an item/station id, or "tech:<slug>"
      "notes": { "pt": "...", "en": "..." } | null
  } },
  "icons": { "tech:<slug>" | "tp:<colour>" | "branch:<key>": "https://media.wikily.gg/..." }  // non-item icons only
}
```

Techs are ordered by branch, then column, then y. File size about 240 kB (indent 1).

## Counts (2026-10-30)

| | |
|---|---|
| technologies | 226 (all `listed`; 38 hidden, 4 given, 27 free, 31 roots, 13 need reputation) |
| per branch | building 52, metallurgy 45, farming 34, theology 28, anatomy-and-alchemy 47, cooking 20 |
| parents | 180 techs have 1, 15 have 2, 31 have none; no edge crosses branches |
| `tr` | official 224, likely 2 (`fabric-building` "Tecido (Engenharia)", `fabric-farming` "Tecido (Agricultura)") |
| unlocks | 534: 522 mapped to an item/station id, 12 unmapped (the town buildings); kind item 312, building 198, recipe 24; pt official 504, likely 30 |
| recipes | 567 recipes linked to 220 techs (6 techs unlock no recipe: Artisans I/II, Market Stalls I-III, Soft parts) |
| icons | 211 techs reuse an item icon, 15 have their own (`tech:<slug>`); plus 3 `tp:*` and 6 `branch:*` |
| notes | 65 techs |

## Validation (all pass)

- every parent exists; the prerequisite graph is a DAG (Kahn's algorithm); costs are non-negative ints;
- `prerequisites[]` equals `parents`, `leadsTo[]` equals the derived `children`, `costs[]` sums equal `costRed/Green/Blue`, `costTotal` equals the sum;
- every recipe `tech` of type `technology` in gk2.json has a record. The 11 recipe techs without a record are not technologies: 10 quests (`chasing-fairy-lights`, `congregation-trouble`, `gluttony-and-pride`, `i-love-you-man`, `jack-in-a-boat`, `lust-and-envy`, `press-for-cash`, `rhyme-and-printed`, `well-deserved-rest`, `wrath-and-sloth`) and 1 perk (`jeweler`).

## Mapping heuristics

- **pt names.** Priority: `names.official.pt-BR.json` > game text table (tier official; for tech names keys `tech_*` are preferred, for branches `tech_tab_*`, quests `<n>_*`, NPCs `npc_*`, town buildings `*_t1`) > likely > guess > machine (the layers are read by `scripts/name_layers.py`, the same lookup as build.py) > missing. Keys are compared after NFC, curly quotes to `'`, whitespace collapse and casefold. The game table supplied the 6 techs missing from the official file (Artisans I/II, Market Stalls I-III, Soft parts), all six branch tabs ("Anatomy\nand alchemy" becomes "Anatomia e alquimia") and the 12 town buildings.
- **Fabric.** Both "Fabric (Building)" and "Fabric (Farming)" are "Fabric" in game (`displayName`). They become official "Tecido" + the branch pt, tier likely: "Tecido (Engenharia)" and "Tecido (Agricultura)", in techs.json and in gk2.json alike.
- **unlocks → item.** First the exact title among gk2 item names ("Wine (gold)" would be its own item), then the href slug (`/items/`, `/buildings/`, `/crafting-stations/`, `/alchemy/<slug>`) as an item or station id. `kind`: `/items/` item, `/alchemy/` recipe (alchemy formula; `item` is the formula's output), `/buildings/`, `/crafting-stations/`, `/town-buildings/` building, an empty href follows the item's kind. `pt` is the item's pt when the names match. When the title only adds a grade ("Wine (gold)" → `wine`), the pt gets the grade back ("Vinho (ouro)", at most tier likely). Otherwise the title is looked up in the name layers. `station` is the subtitle matched to a station name ("Kitchen Table" → `kitchen-table`).
- **icon.** The tech's icon URL matched against `items[].icon` / `stations[].icon`: an unlocked item with that URL first, otherwise the first id in sort order. With no match, `tech:<slug>`, and its URL goes into `icons`.
- **notes.** Built from `availability[]` ("Given for free: …", "Hidden in the tree until revealed by: …", "Given for free and revealed by: …"), `gates[]` ("Needs N reputation with X") and `notesText`. pt uses templates, official quest/NPC/item names from the game table and gk2.json, and short hand translations (tier machine) for the story events and the 9 `notesText` strings (`MACHINE_PT` in build_techs.py). `hiddenText` is only the lead-in to "revealed by" and is covered by `hidden` plus the note.

## Icons / sprite

`fetch_icons.py --techs` (opt-in; without it the script behaves as before) writes `data/icons/tech__<slug>.png`, `tp__<colour>.png`, `branch__<key>.png` (`:` becomes `__`). `make_sprite.py` maps those stems back to `tech:<slug>`, `tp:<colour>`, `branch:<key>`. Sprite after the change: 830 files → 709 cells of 32 px, 27×27, sheet 864×864 (before: 806 → 685 cells, 27×26, 864×832). The tech-point icons are tiny (9×11 native, centred in the 32 px cell); scale them up in CSS if needed.

`build.py`'s `page_payload` keeps the sprite ids of items and stations plus the `tech:*`, `tp:*` and `branch:*` namespaces, so these icons reach the page.

## For the UI: technologies missing for a goal list

1. For each goal recipe (and, if wanted, every recipe in its expanded crafting tree) take `recipe.tech`. Skip `null`. Skip `type` quest/perk: no tech record, show them as "quest X" / "perk X" instead.
2. Walk up from that slug through `techs[slug].parents` (iterative DFS with a `seen` set). Every ancestor is required, since a tech needs all of its parents.
3. Drop the slugs marked researched. If a tech is researched, its ancestors are too, so you can also stop the walk at a researched tech.
4. Sum `cost.red/green/blue` over the remaining set (the set is deduplicated, so shared ancestors count once). Display in topological order: sort by (branch order, column, y), which respects parents because no edge crosses branches and every parent sits in a lower column.
5. Flag techs with `rep` (reputation gate), `hidden` (must be revealed first, see `notes`) and zero-cost `given`/free techs (granted by an event, not bought; `notes` says which).
