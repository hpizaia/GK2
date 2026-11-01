# Build report

Built 2026-11-01 (schema 1). Result: **0 error(s), 205 warning(s), 78 info(s)**.

## Inputs

- items: `data/items.en.json`
- recipes: `data/recipes.en.json`
- names[pt]: `data/names.official.pt-BR.json (sourced layer, 1020 names, 0 texts)`
- names[pt]: `data/names.manual.pt-BR.json (sourced layer, 318 names, 0 texts)`
- names[pt]: `data/names.machine.pt-BR.json (machine layer, 1066 names, 736 texts)`
- names[pt]: `derived (sourced layer, 47 names, 0 texts)`

## Counts

| what | count |
|---|---:|
| items | 838 |
| recipes | 707 |
| stations | 79 |
| categories | 53 |
| techs | 231 |
| multiRecipeItems | 71 |
| noexpRecipes | 17 |
| tr | official 784, likely 48, guess 0, machine 6, missing 0 |
| cycles | 7 |
| errors | 0 |
| warnings | 205 |
| items by kind | action 16, building 130, group 10, item 544, quality-variant 33, station 87, virtual 18 |
| recipes by type | alchemy 28, auto 80, building 225, factory 69, grow 17, hand_craft 241, star_craft 47 |
| unlisted recipes | 22 |
| unobtainable items | 91 |
| items with defaultRecipe | 529 |
| obtain texts translated | 804 / 804 |

## Notes

- names[pt]: 47 derived name(s) (quality grades, groups, Any/Open/Repair), tier likely

## Input coercions

Things build.py had to fix or interpret in the inputs (count, examples).

| coercion | count | examples |
|---|---:|---|
| names: `_` key ignored | 3 | names.official.pt-BR.json:_meta; names.manual.pt-BR.json:_meta; names.machine.pt-BR.json:_meta |

## Cycles

Strongly connected components of the item graph (item -> inputs of its expandable recipes). `trapped` = items whose every expandable recipe feeds back into the cycle.

| # | size | items | example path | recipes | trapped |
|---:|---:|---|---|---|---|
| 1 | 1 | bones | bones -> bones | improve-organ-i-from-any-bones, improve-organ-ii-from-any-bones | bones |
| 2 | 1 | brain | brain -> brain | improve-organ-i-from-any-brain, improve-organ-ii-from-any-brain | brain |
| 3 | 1 | guts | guts -> guts | improve-organ-i-from-any-guts, improve-organ-ii-from-any-guts | guts |
| 4 | 1 | heart | heart -> heart | improve-organ-i-from-any-heart, improve-organ-ii-from-any-heart | heart |
| 5 | 1 | inquisitor-s-medallion | inquisitor-s-medallion -> inquisitor-s-medallion | open-the-door | inquisitor-s-medallion |
| 6 | 1 | skin | skin -> skin | improve-organ-i-from-any-skin, improve-organ-ii-from-any-skin | skin |
| 7 | 1 | skull | skull -> skull | improve-organ-i-from-any-skull, improve-organ-ii-from-any-skull | skull |

# Validation

## Errors (0)

_none_

## Warnings (205)

### `cycle` (7)

- cycle (self-loop): bones (Bones) -> bones (Bones); recipes: improve-organ-i-from-any-bones, improve-organ-ii-from-any-bones
- cycle (self-loop): brain (Brain) -> brain (Brain); recipes: improve-organ-i-from-any-brain, improve-organ-ii-from-any-brain
- cycle (self-loop): guts (Guts) -> guts (Guts); recipes: improve-organ-i-from-any-guts, improve-organ-ii-from-any-guts
- cycle (self-loop): heart (Heart) -> heart (Heart); recipes: improve-organ-i-from-any-heart, improve-organ-ii-from-any-heart
- cycle (self-loop): inquisitor-s-medallion (Inquisitor’s medallion) -> inquisitor-s-medallion (Inquisitor’s medallion); recipes: open-the-door
- cycle (self-loop): skin (Skin) -> skin (Skin); recipes: improve-organ-i-from-any-skin, improve-organ-ii-from-any-skin
- cycle (self-loop): skull (Skull) -> skull (Skull); recipes: improve-organ-i-from-any-skull, improve-organ-ii-from-any-skull

### `orphan` (163)

- `acid` (Acid) is not produced, consumed or used as a station by any recipe
- `albedo-tear` (Albedo Tear) is not produced, consumed or used as a station by any recipe
- `alchemist-s-bag` (Alchemist's bag) is not produced, consumed or used as a station by any recipe
- `alchemist-s-clothes` (Alchemist's Clothes) is not produced, consumed or used as a station by any recipe
- `alchemist-s-note` (Alchemist's note) is not produced, consumed or used as a station by any recipe
- `alum` (Alum) is not produced, consumed or used as a station by any recipe
- `anchovy` (Anchovy) is not produced, consumed or used as a station by any recipe
- `anima-mundi-fragment` (Anima Mundi Fragment) is not produced, consumed or used as a station by any recipe
- `aqua-vitae` (Aqua Vitae) is not produced, consumed or used as a station by any recipe
- `battle-loot` (Battle Loot) is not produced, consumed or used as a station by any recipe
- `big-universal-bag` (Big universal bag) is not produced, consumed or used as a station by any recipe
- `black-oil` (Black Oil) is not produced, consumed or used as a station by any recipe
- `blacksmith-s-clothes` (Blacksmith's Clothes) is not produced, consumed or used as a station by any recipe
- `boiled-egg` (Boiled Egg) is not produced, consumed or used as a station by any recipe
- `bream` (Bream) is not produced, consumed or used as a station by any recipe
- `brimstone` (Brimstone) is not produced, consumed or used as a station by any recipe
- `broken-ceramic` (Broken ceramic) is not produced, consumed or used as a station by any recipe
- `builder-s-bag` (Builder's bag) is not produced, consumed or used as a station by any recipe
- `burial-certificate-i` (Burial Certificate I) is not produced, consumed or used as a station by any recipe
- `burial-certificate-ii` (Burial Certificate II) is not produced, consumed or used as a station by any recipe
- `burial-certificate-iii` (Burial Certificate III) is not produced, consumed or used as a station by any recipe
- `cake` (Cake) is not produced, consumed or used as a station by any recipe
- `camphor` (Camphor) is not produced, consumed or used as a station by any recipe
- `carp` (Carp) is not produced, consumed or used as a station by any recipe
- `catalyst` (Catalyst) is not produced, consumed or used as a station by any recipe
- `catfish` (Catfish) is not produced, consumed or used as a station by any recipe
- `chaos-spagyric-root` (Chaos Spagyric Root) is not produced, consumed or used as a station by any recipe
- `cinnabar` (Cinnabar) is not produced, consumed or used as a station by any recipe
- `coniunctio-salt` (Coniunctio Salt) is not produced, consumed or used as a station by any recipe
- `copper-detail` (Copper Detail) is not produced, consumed or used as a station by any recipe
- `copper-ingot` (Copper Ingot) is not produced, consumed or used as a station by any recipe
- `copper-nails` (Copper Nails) is not produced, consumed or used as a station by any recipe
- `copper-scrap` (Copper Scrap) is not produced, consumed or used as a station by any recipe
- `crucian` (Crucian) is not produced, consumed or used as a station by any recipe
- `deck-of-cards` (Deck of Cards) is not produced, consumed or used as a station by any recipe
- `defender-s-emblem` (Defender's Emblem) is not produced, consumed or used as a station by any recipe
- `dye` (Dye) is not produced, consumed or used as a station by any recipe
- `eel` (Eel) is not produced, consumed or used as a station by any recipe
- `empty-glass-bottle` (Empty Glass Bottle) is not produced, consumed or used as a station by any recipe
- `energy-potion` (Energy Potion) is not produced, consumed or used as a station by any recipe
- `energy-potion-ii` (Energy Potion II) is not produced, consumed or used as a station by any recipe
- `energy-potion-iii` (Energy Potion III) is not produced, consumed or used as a station by any recipe
- `energy-potion-scroll` (Energy Potion Scroll) is not produced, consumed or used as a station by any recipe
- `everlasting-needles` (Everlasting Needles) is not produced, consumed or used as a station by any recipe
- `exhumation-certificate` (Exhumation Certificate) is not produced, consumed or used as a station by any recipe
- `fairy-s-swamp-map` (Fairy's Swamp Map) is not produced, consumed or used as a station by any recipe
- `farmer-s-bag` (Farmer's bag) is not produced, consumed or used as a station by any recipe
- `farmer-s-clothes` (Farmer's Clothes) is not produced, consumed or used as a station by any recipe
- `fisherman-s-bag` (Fisherman's bag) is not produced, consumed or used as a station by any recipe
- `fishing-line` (Fishing Line) is not produced, consumed or used as a station by any recipe
- `food-bag` (Food bag) is not produced, consumed or used as a station by any recipe
- `forest-pass` (Forest Pass) is not produced, consumed or used as a station by any recipe
- `fried-egg` (Fried egg) is not produced, consumed or used as a station by any recipe
- `garden-well-ii` (Garden Well II) is not produced, consumed or used as a station by any recipe
- `glue` (Glue) is not produced, consumed or used as a station by any recipe
- `grape-pie` (Grape pie) is not produced, consumed or used as a station by any recipe
- `green-jelly` (Green jelly) is not produced, consumed or used as a station by any recipe
- `green-mold` (Green mold) is not produced, consumed or used as a station by any recipe
- `green-scroll` (Green Scroll) is not produced, consumed or used as a station by any recipe
- `grow-potion` (Grow potion) is not produced, consumed or used as a station by any recipe
- `gudgeon` (Gudgeon) is not produced, consumed or used as a station by any recipe
- `gunpowder` (Gunpowder) is not produced, consumed or used as a station by any recipe
- `hands` (Hands) is not produced, consumed or used as a station by any recipe
- `healing-potion-scroll` (Healing Potion Scroll) is not produced, consumed or used as a station by any recipe
- `herring` (Herring) is not produced, consumed or used as a station by any recipe
- `homunculus` (Homunculus) is not produced, consumed or used as a station by any recipe
- `imported-components` (Imported Components) is not produced, consumed or used as a station by any recipe
- `inquisitor-s-note` (Inquisitor's note) is not produced, consumed or used as a station by any recipe
- `inquisitor-s-note-i` (Inquisitor's Note I) is not produced, consumed or used as a station by any recipe
- `inquisitor-s-note-ii` (Inquisitor's Note II) is not produced, consumed or used as a station by any recipe
- `inventory` (Inventory) is not produced, consumed or used as a station by any recipe
- `iron-scrap` (Iron Scrap) is not produced, consumed or used as a station by any recipe
- `kebab-with-fish-and-mushrooms` (Kebab with fish and mushrooms) is not produced, consumed or used as a station by any recipe
- `kebab-with-fish-and-onion` (Kebab with fish and onion) is not produced, consumed or used as a station by any recipe
- `kebab-with-fish-and-pumpkin` (Kebab with fish and pumpkin) is not produced, consumed or used as a station by any recipe
- `keeper-s-clothes` (Keeper's Clothes) is not produced, consumed or used as a station by any recipe
- `key-from-the-inquisition-dungeon` (Key from the Inquisition dungeon) is not produced, consumed or used as a station by any recipe
- `key-to-the-resurrection-room` (Key to the Resurrection Room) is not produced, consumed or used as a station by any recipe
- `keys-for-looters` (Keys for Looters) is not produced, consumed or used as a station by any recipe
- `king-s-signet` (King's signet) is not produced, consumed or used as a station by any recipe
- `krotowuha` (Krotowuha) is not produced, consumed or used as a station by any recipe
- `krotowuha-scroll` (Krotowuha Scroll) is not produced, consumed or used as a station by any recipe
- `life-water` (Life water) is not produced, consumed or used as a station by any recipe
- `love-novel` (Love Novel) is not produced, consumed or used as a station by any recipe
- `mackerel` (Mackerel) is not produced, consumed or used as a station by any recipe
- `mash-drop` (Mash drop) is not produced, consumed or used as a station by any recipe
- `master-rod` (Master Rod) is not produced, consumed or used as a station by any recipe
- `mercurius-vivus` (Mercurius Vivus) is not produced, consumed or used as a station by any recipe
- `moonshine` (Moonshine) is not produced, consumed or used as a station by any recipe
- `mortificatio-oil` (Mortificatio Oil) is not produced, consumed or used as a station by any recipe
- `mysterious-chest` (Mysterious Chest) is not produced, consumed or used as a station by any recipe
- `natural-resin` (Natural Resin) is not produced, consumed or used as a station by any recipe
- `necronomicon` (Necronomicon) is not produced, consumed or used as a station by any recipe
- `nigredo-ash` (Nigredo Ash) is not produced, consumed or used as a station by any recipe
- `no-bait` (No Bait) is not produced, consumed or used as a station by any recipe
- `omelet` (Omelet) is not produced, consumed or used as a station by any recipe
- `organ-randomizer` (Organ Randomizer) is not produced, consumed or used as a station by any recipe
- `organ-restorer` (Organ Restorer) is not produced, consumed or used as a station by any recipe
- `pancakes` (Pancakes) is not produced, consumed or used as a station by any recipe
- `pasta` (Pasta) is not produced, consumed or used as a station by any recipe
- `philosophic-sulfur` (Philosophic Sulfur) is not produced, consumed or used as a station by any recipe
- `pike` (Pike) is not produced, consumed or used as a station by any recipe
- `pilgrim-s-clothes` (Pilgrim's Clothes) is not produced, consumed or used as a station by any recipe
- `po-ta-to` (Po-ta-to) is not produced, consumed or used as a station by any recipe
- `polishing-paste` (Polishing Paste) is not produced, consumed or used as a station by any recipe
- `portal-fragment-envy` (Portal fragment Envy) is not produced, consumed or used as a station by any recipe
- `portal-fragment-gluttony` (Portal fragment Gluttony) is not produced, consumed or used as a station by any recipe
- `portal-fragment-greed` (Portal fragment Greed) is not produced, consumed or used as a station by any recipe
- `portal-fragment-lust` (Portal fragment Lust) is not produced, consumed or used as a station by any recipe
- `portal-fragment-pride` (Portal fragment Pride) is not produced, consumed or used as a station by any recipe
- `portal-fragment-sloth` (Portal fragment Sloth) is not produced, consumed or used as a station by any recipe
- `portal-fragment-wrath` (Portal fragment Wrath) is not produced, consumed or used as a station by any recipe
- `potion-bag` (Potion bag) is not produced, consumed or used as a station by any recipe
- `pr-agreement` (PR Agreement) is not produced, consumed or used as a station by any recipe
- `prayer-for-music` (Prayer for Music) is not produced, consumed or used as a station by any recipe
- `prayer-for-speed` (Prayer for Speed) is not produced, consumed or used as a station by any recipe
- `priest-s-clothes` (Priest's Clothes) is not produced, consumed or used as a station by any recipe
- `prima-materia-dust` (Prima Materia Dust) is not produced, consumed or used as a station by any recipe
- `quicksilver` (Quicksilver) is not produced, consumed or used as a station by any recipe
- `quintessence-vial` (Quintessence Vial) is not produced, consumed or used as a station by any recipe
- `red-eye` (Red Eye) is not produced, consumed or used as a station by any recipe
- `red-jelly` (Red jelly) is not produced, consumed or used as a station by any recipe
- `resin` (Resin) is not produced, consumed or used as a station by any recipe
- `resurrection-note` (Resurrection Note) is not produced, consumed or used as a station by any recipe
- `roach` (Roach) is not produced, consumed or used as a station by any recipe
- `royal-pardon` (Royal Pardon) is not produced, consumed or used as a station by any recipe
- `rubedo-crystallis` (Rubedo Crystallis) is not produced, consumed or used as a station by any recipe
- `rusty-axe` (Rusty Axe) is not produced, consumed or used as a station by any recipe
- `rusty-hammer` (Rusty Hammer) is not produced, consumed or used as a station by any recipe
- `rusty-pickaxe` (Rusty Pickaxe) is not produced, consumed or used as a station by any recipe
- `rusty-shovel` (Rusty Shovel) is not produced, consumed or used as a station by any recipe
- `rusty-sword` (Rusty Sword) is not produced, consumed or used as a station by any recipe
- `salmon` (Salmon) is not produced, consumed or used as a station by any recipe
- `scary-idol` (Scary Idol) is not produced, consumed or used as a station by any recipe
- `science` (Science) is not produced, consumed or used as a station by any recipe
- `separatio-membrane` (Separatio Membrane) is not produced, consumed or used as a station by any recipe
- `shrimp-bait` (Shrimp Bait) is not produced, consumed or used as a station by any recipe
- `signed-pr-agreement` (Signed PR Agreement) is not produced, consumed or used as a station by any recipe
- `signed-printed-money` (Signed Printed Money) is not produced, consumed or used as a station by any recipe
- `slug` (Slug) is not produced, consumed or used as a station by any recipe
- `special-clothes` (Special Clothes) is not produced, consumed or used as a station by any recipe
- `speed-potion` (Speed Potion) is not produced, consumed or used as a station by any recipe
- `speed-potion-scroll` (Speed Potion Scroll) is not produced, consumed or used as a station by any recipe
- `surgeon-s-error` (Surgeon's Error) is not produced, consumed or used as a station by any recipe
- `temptation` (Temptation) is not produced, consumed or used as a station by any recipe
- `tool-bag` (Tool bag) is not produced, consumed or used as a station by any recipe
- `town-gratitude` (Town Gratitude) is not produced, consumed or used as a station by any recipe
- `toxic-potion` (Toxic Potion) is not produced, consumed or used as a station by any recipe
- `toxic-potion-ii` (Toxic Potion II) is not produced, consumed or used as a station by any recipe
- `transmutation-potion-i` (Transmutation Potion I) is not produced, consumed or used as a station by any recipe
- `transmutation-potion-ii` (Transmutation Potion II) is not produced, consumed or used as a station by any recipe
- `trout` (Trout) is not produced, consumed or used as a station by any recipe
- `tuna` (Tuna) is not produced, consumed or used as a station by any recipe
- `unholy-idol` (Unholy Idol) is not produced, consumed or used as a station by any recipe
- `universal-bag` (Universal bag) is not produced, consumed or used as a station by any recipe
- `victory-flag` (Victory Flag) is not produced, consumed or used as a station by any recipe
- `violin` (Violin) is not produced, consumed or used as a station by any recipe
- `wanted-poster` (Wanted Poster) is not produced, consumed or used as a station by any recipe
- `wooden-billet` (Wooden Billet) is not produced, consumed or used as a station by any recipe
- `worms-bait` (Worms Bait) is not produced, consumed or used as a station by any recipe
- `written-softcover-book` (Written Softcover Book) is not produced, consumed or used as a station by any recipe
- `zombie` (Zombie) is not produced, consumed or used as a station by any recipe
- `zombie-goo` (Zombie goo) is not produced, consumed or used as a station by any recipe

### `zero-inputs` (35)

- recipe `build-columbarium-area-i` (Columbarium Area I) has no inputs
- recipe `build-columbarium-area-ii` (Columbarium Area II) has no inputs
- recipe `build-empty-grave` (Empty Grave) has no inputs
- recipe `build-garden-bed` (Garden Bed) has no inputs
- recipe `build-grave-area-i` (Grave Area I) has no inputs
- recipe `build-grave-area-ii` (Grave Area II) has no inputs
- recipe `build-grave-area-iii` (Grave Area III) has no inputs
- recipe `build-grave-area-iv` (Grave Area IV) has no inputs
- recipe `build-kitchen-stove` (Kitchen: Stove) has no inputs
- recipe `build-mixed-area-i` (Mixed Area I) has no inputs
- recipe `build-mixed-area-ii` (Mixed Area II) has no inputs
- recipe `build-mixed-area-iii` (Mixed Area III) has no inputs
- recipe `build-pr-machine-i` (PR Machine I) has no inputs
- recipe `build-pr-machine-ii` (PR Machine II) has no inputs
- recipe `build-pr-machine-iii` (PR Machine III) has no inputs
- recipe `build-pr-machine-iv` (PR Machine IV) has no inputs
- recipe `build-pr-machine-v` (PR Machine V) has no inputs
- recipe `build-tablet-beet` (Tablet "Beet") has no inputs
- recipe `build-tablet-cabbage` (Tablet "Cabbage") has no inputs
- recipe `build-tablet-carrot` (Tablet "Carrot") has no inputs
- recipe `build-tablet-flax` (Tablet "Flax") has no inputs
- recipe `build-tablet-grapes` (Tablet "Grapes") has no inputs
- recipe `build-tablet-hops` (Tablet "Hops") has no inputs
- recipe `build-tablet-onion` (Tablet "Onion") has no inputs
- recipe `build-tablet-pumpkin` (Tablet "Pumpkin") has no inputs
- recipe `build-tablet-wheat` (Tablet "Wheat") has no inputs
- recipe `build-village-toilet` (Village toilet) has no inputs
- recipe `build-walkway-area-i` (Walkway Area I) has no inputs
- recipe `build-walkway-area-ii` (Walkway Area II) has no inputs
- recipe `clay` (Clay) has no inputs
- recipe `iron-ore` (Iron Ore) has no inputs
- recipe `log` (Log) has no inputs
- recipe `marble` (Marble) has no inputs
- recipe `sand` (Sand) has no inputs
- recipe `stone` (Stone) has no inputs

## Infos (78)

### `cycle-trapped` (7)

- `bones` (Bones): every recipe feeds back into its cycle; the calculator must stop expanding it (treat as raw)
- `brain` (Brain): every recipe feeds back into its cycle; the calculator must stop expanding it (treat as raw)
- `guts` (Guts): every recipe feeds back into its cycle; the calculator must stop expanding it (treat as raw)
- `heart` (Heart): every recipe feeds back into its cycle; the calculator must stop expanding it (treat as raw)
- `inquisitor-s-medallion` (Inquisitor’s medallion): every recipe feeds back into its cycle; the calculator must stop expanding it (treat as raw)
- `skin` (Skin): every recipe feeds back into its cycle; the calculator must stop expanding it (treat as raw)
- `skull` (Skull): every recipe feeds back into its cycle; the calculator must stop expanding it (treat as raw)

### `multi-recipe` (71)

- `alchemy-flasks` (Alchemy Flasks) has 2 recipes: place-alchemy-flasks-i, place-alchemy-flasks-ii
- `alcohol` (Alcohol) has 6 recipes: alcohol-from-any-wine, alcohol-from-apple-cider, alcohol-from-beer, alcohol-from-berry-cider, alcohol-from-blueberry-cider, alcohol-from-mead
- `ash` (Ash) has 2 recipes: ash-crematorium-i, ash-crematorium-ii
- `baked-pumpkin` (Baked pumpkin) has 3 recipes: baked-pumpkin-from-pumpkin-bronze, baked-pumpkin-from-pumpkin-gold, baked-pumpkin-from-pumpkin-silver
- `board` (Board) has 2 recipes: board-circular-saw, board-sawhorse
- `bones` (Bones) has 2 recipes: improve-organ-i-from-any-bones, improve-organ-ii-from-any-bones
- `bowl-of-sauerkraut-gold` (Bowl of sauerkraut (gold)) has 2 recipes: bowl-of-sauerkraut-gold, food-enhancement-ii-from-bowl-of-sauerkraut-silver
- `bowl-of-sauerkraut-silver` (Bowl of sauerkraut (silver)) has 2 recipes: bowl-of-sauerkraut-silver, food-enhancement-i-from-bowl-of-sauerkraut-bronze
- `brain` (Brain) has 2 recipes: improve-organ-i-from-any-brain, improve-organ-ii-from-any-brain
- `brick` (Brick) has 2 recipes: brick-kiln, brick-smithy-i
- `bronze-ingot` (Bronze Ingot) has 2 recipes: bronze-ingot-from-bronze-scrap, bronze-ingot-from-copper-nugget
- `bronze-nails` (Bronze Nails) has 2 recipes: bronze-nails-from-bronze-ingot, bronze-nails-from-bronze-scrap
- `building-kit-i` (Building Kit I) has 2 recipes: building-kit-i-assembly-bench-i, building-kit-i-woodworking-workbench-i
- `cabbage-bed` (Cabbage Bed) has 3 recipes: plant-cabbage-seed-bronze, plant-cabbage-seed-gold, plant-cabbage-seed-silver
- `cabbage-soup` (Cabbage soup) has 3 recipes: cabbage-soup-from-cabbage-bronze, cabbage-soup-from-cabbage-gold, cabbage-soup-from-cabbage-silver
- `clean-paper` (Clean Paper) has 2 recipes: clean-paper-paper-press, clean-paper-writing-desk
- `expand-military-building-area` (Expand Military Building Area) has 3 recipes: build-expand-military-building-area, build-expand-military-building-area--barracks, build-expand-military-building-area--barracks-2
- `fabric` (Fabric) has 2 recipes: fabric-assembly-bench-i, fabric-weaving-loom
- `firewood` (Firewood) has 2 recipes: firewood-from-short-log, firewood-from-stick
- `firewood-shed-i` (Firewood shed I) has 2 recipes: build-firewood-shed-i, build-firewood-shed-i--home-alchemy-lab-vineyard-basement
- `firewood-shed-ii` (Firewood shed II) has 2 recipes: build-firewood-shed-ii, build-firewood-shed-ii--home-alchemy-lab-vineyard-basement
- `furniture-kit-i` (Furniture Kit I) has 2 recipes: furniture-kit-i-assembly-bench-ii, furniture-kit-i-woodworking-workbench-ii
- `gardener-stand` (Gardener Stand) has 2 recipes: build-gardener-stand, build-gardener-stand--vineyard
- `glass` (Glass) has 2 recipes: glass-furnace-i, glass-smithy-i
- `golden-ingot` (Golden ingot) has 2 recipes: gold-transmutation-from-iron-ingot, golden-ingot
- `grape-juice-gold` (Grape Juice (gold)) has 2 recipes: drink-enhancement-ii-from-grape-juice-silver, grape-juice-from-grapes-gold
- `grape-juice-silver` (Grape Juice (silver)) has 2 recipes: drink-enhancement-i-from-grape-juice-bronze, grape-juice-from-grapes-silver
- `grapes-bed` (Grapes Bed) has 3 recipes: plant-grape-seeds-bronze, plant-grape-seeds-gold, plant-grape-seeds-silver
- `guts` (Guts) has 2 recipes: improve-organ-i-from-any-guts, improve-organ-ii-from-any-guts
- `heart` (Heart) has 2 recipes: improve-organ-i-from-any-heart, improve-organ-ii-from-any-heart
- `iron-ingot` (Iron Ingot) has 2 recipes: iron-ingot-furnace-ii, iron-ingot-smithy-i
- `iron-kit-i` (Iron Kit I) has 2 recipes: iron-kit-i-iron-anvil, iron-kit-i-smithy-i
- `lantern-i` (Lantern I) has 2 recipes: build-lantern-i, build-lantern-i--yard
- `lantern-ii` (Lantern II) has 2 recipes: build-lantern-ii, build-lantern-ii--yard
- `lens` (Lens) has 2 recipes: lens-furnace-i, lens-smithy-ii
- `melted-fat` (Melted Fat) has 2 recipes: melted-fat-from-fat, melted-fat-from-seed-oil
- `mysterious-fish-fillet` (Mysterious fish fillet) has 3 recipes: mysterious-fish-fillet-from-goldfish, mysterious-fish-fillet-from-silverfin, mysterious-fish-fillet-from-swamp-ghost
- `newspaper-gold` (Newspaper (gold)) has 2 recipes: improve-newspaper-ii, printing-press-gold
- `newspaper-silver` (Newspaper (silver)) has 2 recipes: improve-newspaper-i, printing-press-silver
- `onion-bed` (Onion Bed) has 3 recipes: plant-onion-seed-bronze, plant-onion-seed-gold, plant-onion-seed-silver
- `onion-rings` (Onion rings) has 3 recipes: onion-rings-from-onion-bronze, onion-rings-from-onion-gold, onion-rings-from-onion-silver
- `paper-glop` (Paper glop) has 2 recipes: paper-glop-from-flax, paper-glop-from-wheat
- `peat` (Peat) has 2 recipes: peat-compost-pile, peat-compost-pile-ii
- `porter-station` (Porter Station) has 9 recipes: build-porter-station, build-porter-station--old-mine, build-porter-station--quarry, build-porter-station--riverside, build-porter-station--sawmill, build-porter-station--sawmill-2, build-porter-station--supply-storage, build-porter-station--vineyard, build-porter-station--vineyard-basement
- `pumpkin-bed` (Pumpkin Bed) has 3 recipes: plant-pumpkin-seeds-bronze, plant-pumpkin-seeds-gold, plant-pumpkin-seeds-silver
- `pumpkin-soup` (Pumpkin soup) has 3 recipes: pumpkin-soup-from-pumpkin-bronze, pumpkin-soup-from-pumpkin-gold, pumpkin-soup-from-pumpkin-silver
- `river-fish-fillet` (River fish fillet) has 4 recipes: river-fish-fillet-from-bream-or-carp, river-fish-fillet-from-crucian-or-herring, river-fish-fillet-from-pike-or-catfish, river-fish-fillet-from-roach-or-gudgeon
- `sea-fish-fillet` (Sea fish fillet) has 3 recipes: sea-fish-fillet-from-anchovy-or-mackerel, sea-fish-fillet-from-eel-or-trout, sea-fish-fillet-from-tuna-or-salmon
- `seed-oil` (Seed oil) has 7 recipes: seed-oil-from-any-cabbage-seed, seed-oil-from-any-onion-seed, seed-oil-from-any-pumpkin-seeds, seed-oil-from-beet-seed, seed-oil-from-carrot-seed, seed-oil-from-flax-seed, seed-oil-from-wheat-seed
- `short-log` (Short Log) has 2 recipes: short-log-circular-saw, short-log-sawhorse
- `skin` (Skin) has 2 recipes: improve-organ-i-from-any-skin, improve-organ-ii-from-any-skin
- `skull` (Skull) has 2 recipes: improve-organ-i-from-any-skull, improve-organ-ii-from-any-skull
- `stone-kit` (Stone Kit) has 2 recipes: stone-kit-assembly-bench-i, stone-kit-stonemason-s-workbench
- `story-gold` (Story (gold)) has 2 recipes: improve-story-ii, story-gold
- `story-silver` (Story (silver)) has 2 recipes: improve-story-i, story-silver
- `supply-clothes-i` (Supply: Clothes I) has 2 recipes: supply-clothes-i-assembly-bench-ii, supply-clothes-i-sewing-table
- `supply-fabric` (Supply: Fabric) has 2 recipes: supply-fabric-assembly-bench-i, supply-fabric-woodworking-workbench-i
- `supply-iron` (Supply: Iron) has 2 recipes: supply-iron-assembly-bench-i, supply-iron-woodworking-workbench-i
- `supply-preserves-i` (Supply: Preserves I) has 5 recipes: supply-preserves-i-from-beet, supply-preserves-i-from-cabbage-bronze, supply-preserves-i-from-cabbage-gold, supply-preserves-i-from-cabbage-silver, supply-preserves-i-from-carrot
- `supply-preserves-ii` (Supply: Preserves II) has 6 recipes: supply-preserves-ii-from-onion-bronze, supply-preserves-ii-from-onion-gold, supply-preserves-ii-from-onion-silver, supply-preserves-ii-from-pumpkin-bronze, supply-preserves-ii-from-pumpkin-gold, supply-preserves-ii-from-pumpkin-silver
- `supply-vegetables` (Supply: Vegetables) has 11 recipes: supply-vegetables-from-beet, supply-vegetables-from-cabbage-bronze, supply-vegetables-from-cabbage-gold, supply-vegetables-from-cabbage-silver, supply-vegetables-from-carrot, supply-vegetables-from-onion-bronze, supply-vegetables-from-onion-gold, supply-vegetables-from-onion-silver, supply-vegetables-from-pumpkin-bronze, supply-vegetables-from-pumpkin-gold, supply-vegetables-from-pumpkin-silver
- `supply-wine` (Supply: Wine) has 3 recipes: supply-wine-from-wine-bronze, supply-wine-from-wine-gold, supply-wine-from-wine-silver
- `timber-stockpile` (Timber stockpile) has 2 recipes: build-timber-stockpile, build-timber-stockpile--sawmill
- `toast-with-onions` (Toast with onions) has 3 recipes: toast-with-onions-from-onion-bronze, toast-with-onions-from-onion-gold, toast-with-onions-from-onion-silver
- `vegetable-salad-gold` (Vegetable salad (gold)) has 2 recipes: food-enhancement-ii-from-vegetable-salad-silver, vegetable-salad-gold
- `vegetable-salad-silver` (Vegetable salad (silver)) has 2 recipes: food-enhancement-i-from-vegetable-salad-bronze, vegetable-salad-silver
- `wine-gold` (Wine (gold)) has 2 recipes: drink-enhancement-ii-from-wine-silver, wine-from-grape-juice-gold
- `wine-silver` (Wine (silver)) has 2 recipes: drink-enhancement-i-from-wine-bronze, wine-from-grape-juice-silver
- `wooden-kit-i` (Wooden Kit I) has 3 recipes: wooden-kit-i-from-bronze-nails-assembly-bench-i, wooden-kit-i-from-log-assembly-bench-i, wooden-kit-i-woodworking-workbench-i
- `wooden-plank` (Wooden Plank) has 2 recipes: wooden-plank-circular-saw, wooden-plank-woodworking-workbench-i
- `zombie-supplier-station` (Zombie Supplier Station) has 2 recipes: build-zombie-supplier-station, build-zombie-supplier-station--home
