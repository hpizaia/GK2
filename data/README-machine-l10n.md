# Machine pt-BR fallback layer (`names.machine.pt-BR.json`)

Claude's own Brazilian Portuguese translation of every name in the GK2 dataset, made 2026-10-30. **None of it comes from the game.** It is a fallback layer. Any name found in an official or GK1-derived source (`names.pt-BR.json` entries whose `source` is not `machine`) overrides it at build time. Its job is full coverage and consistent terminology.

## Schema

Same as `names.pt-BR.json`: an object keyed by the **exact English string**.

```jsonc
{
  "_meta":   { "generated": "2026-10-30", "counts": { ... }, ... },   // skip keys starting with "_"
  "Iron Ingot": { "pt": "Lingote de ferro", "source": "machine", "confidence": "guess" },
  ...
  "__obtain": { "<items[].obtain English text>": "<pt-BR text>", ... }
}
```

`__obtain` is keyed by the whole `obtain` string, so a lookup is `obtain_pt = m["__obtain"][item.obtain]`.

## Coverage (checked by a script: 100%, no missing keys, no leftover placeholders)

| group | distinct keys | notes |
|---|---|---|
| items (`items[].name`) | 820 | includes the 15 quality variants and 10 group/wildcard items |
| stations (`station` + `alt_stations`) | 79 | all 79 are also item names, so they share entries |
| categories (`items[].category`) | 53 | |
| technologies (`unlock.name`) | 231 | 188 are not item names. Includes 10 quest names and 1 perk used as unlocks |
| mastery types (`mastery.type`) | 5 | added for parity with `names.pt-BR.json`. "Farming" is shared with the category |
| **name keys total** | **1065** | the same key set as `names.pt-BR.json`, checked |
| obtain texts (`__obtain`) | 725 | every distinct non-null `obtain` |

### How the obtain texts were translated
The 725 texts split into 1,142 distinct sentences. About 85% follow ~45 fixed wiki patterns, such as "Made at the X from …", "Sold by …", "Unlocked by …", "X is built in … for …", "Brewed by alchemy …", "Using it restores …" and "X is not obtainable in version 1.010 …". These were rendered by templates that insert the names from this same file, so item names in the sentences always match the name entries. The remaining ~140 sentences were translated by hand.

Grammatical agreement:
- Participles and pronouns agree with the item's gender and number: "Feito/Feita/Feitos/Feitas", "Usá-lo/Usá-la", "Não podem ser comidas".
- The definite article follows the station's or area's gender: no/na/nos/nas, pelo/pela.
- Nine texts are shared by items of different genders (for example a fishing spot that yields both "Anchova" and "Atum"). These use impersonal phrasing instead ("Pesca-se no ponto de pesca da Floresta").

Ingredient lists keep the source's "N Name" form, without plurals ("com 2 Placa de madeira e 4 Pregos de bronze"), the same way the English does.

## Conventions

- **Capitalisation:** only the first word is capitalised ("Lingote de ferro", not "Lingote De Ferro"). Proper nouns, Latin alchemy terms and names of sins and gods are exceptions. After a colon the text continues in lowercase ("Bancada de montagem: torno", "Suprimento: cerveja").
- **Roman numerals are kept:** "Laboratório II", "Fornalha I".
- **Quality tags:** `(bronze)`, `(prata)`, `(ouro)`. "(Bronze)" inside obtain texts is lowercased the same way.
- **Group/wildcard items:** "Any Newspaper" → "Qualquer jornal", "Bream or Carp" → "Brema ou carpa", and "Any Anchovy or Mackerel" inside a recipe → "Anchova ou cavala (qualquer)".
- **Proper nouns stay untranslated:** Herm, Gunter, Januarius, Harold, Homobonus, Linda, Jack, Necronomicon, Krotowuha, Kraken Jr. Descriptive epithets are translated: Davy the Dagger → "Davy, o Punhal"; Comrade Donkey → "Camarada Burro".
- **Verb-named buildings** ("Upgrade Bed", "Fix the Attic") use the infinitive: "Aprimorar a cama", "Consertar o sótão".
- **Week days:** GK2's week days are named after the sins, so "on a Lust" → "em um dia da Luxúria".

## Glossary (applied consistently across names and obtain texts)

**GK1 official pt-BR vocabulary reused.** The items marked * were confirmed by the GK1 pt-BR wiki entries in `names.pt-BR.json`.

| EN | pt-BR |
|---|---|
| Faith / Science / Fuel | Fé / Ciência / Combustível |
| Blue / green / red tech points | pontos de tecnologia azuis / verdes / vermelhos |
| Zombie / Corpse / Body | Zumbi / Cadáver / Corpo |
| Graveyard / Grave / Crypt | Cemitério / Cova / Cripta |
| Morgue / Church / Embalming / Autopsy | Necrotério / Igreja / Embalsamamento / Autópsia |
| Burial / Exhumation certificate | Certidão de sepultamento / de exumação |
| Gravestone / Fence / Cross | Lápide / Cerca / Cruz |
| Skull* / Bones / Flesh / Skin / Blood / Fat / Guts | Caveira / Ossos / Carne / Pele / Sangue / Gordura / Tripas |
| Alchemy / Flask / Powder / Vial / Solution | Alquimia / Frasco / Pó / Ampola / Solução |
| Furnace / Anvil / Sawmill / Workbench | Fornalha / Bigorna / Serraria / Bancada |
| Ingot / Ore / Nugget / Scrap / Nails / Screws / Gear | Lingote / Minério / Pepita / Sucata / Pregos / Parafusos / Engrenagem |
| Wooden Plank* / Board / Beam / Log / Stick | Placa de madeira / Prancha / Viga / Tora / Graveto |
| Beeswax / Peat / Candle / Incense | Cera de abelha / Turfa / Vela / Incenso |
| Berry* / Clean Paper* / Paper glop* / Frog* / Goldfish* / Gudgeon* / Alkali* | Frutinha / Papel vazio / Mistureba de papel / Sapo / Peixinho-dourado / Góbrio / Alcalino |
| Mastery / Quality / Star | Maestria / Qualidade / Estrela |

**GK2-specific choices made here**

| EN | pt-BR | why |
|---|---|---|
| Detail (Bronze/Iron/Steel/Advanced Detail) | Peça (de bronze / de ferro / de aço / avançada) | |
| Kit (Wooden/Iron/Stone Kit) | Kit (de madeira / de ferro / de pedra) | |
| Oiled / Reinforced / Polished / Carved | oleada(o) / reforçada(o) / polida(o) / entalhada(o) | agrees with the noun |
| Upgrade (verb / noun) | Aprimorar / Aprimoramento | keeps "Garden **Upgrade** I" separate from the tech "Garden **Improvement** I" |
| Improve / Improvement | Melhorar / Melhoria | |
| Expand | Expandir | |
| Garden (area) / Garden Bed / Gardening | Horta / Canteiro / Horticultura | |
| Yard / Home / Factory / Barracks / Vineyard | Pátio / Casa / Fábrica / Quartel / Vinhedo | |
| Writing Basement / Vineyard Basement | Porão de escrita / Porão do vinhedo | |
| Stand (zombie work stations) | Posto (Posto de lenhador, Posto de escavação de argila) | |
| Bench (seat) vs bench (workbench) | Banco vs Bancada | |
| Table (station) | Mesa (Mesa de autópsia, Mesa de cozinha) | |
| Supply / Supplies | Suprimento / Suprimentos | |
| Techbook | Livro técnico | |
| Scroll / Notebook | Pergaminho / Caderno | |
| Prayer | Oração | |
| Potion / Elixir | Poção / Elixir | |
| PR (Machine, Agreement) | RP (relações públicas) | |
| the Keeper | o Zelador | |
| Smithing (mastery) / Smithy (station, trader) | Ferraria | |
| Building / Farming / Anatomy / Book writing (mastery) | Construção / Agricultura / Anatomia / Escrita de livros | |
| tool belt | cinto de ferramentas | |
| energy / stamina / insanity / health | energia / vigor / insanidade / vida | |
| red skulls (zombie quality) | caveiras vermelhas | |
| Factory power | energia da fábrica | |
| Steamed Up (buff) | A todo vapor | |
| Berserk / Fighter / Zombie Motivation (buffs) | Fúria / Lutador / Motivação zumbi | |
| Trademaster / Apothecary / Furniture Maker / Merc Leader | Mestre do comércio / Boticário / Moveleiro / Líder dos mercenários | |
| Pike (weapon) / Pike (fish) | Pique / Lúcio | |

## Review these first (least certain, ~25)

1. **"the Keeper" → "Zelador"** (protagonist title in obtain texts) and the techs **"Graveyard Keeper I–IV" → "Zelador do cemitério I–IV"**. The GK1 pt-BR term for the protagonist is unverified. It may simply be "Graveyard Keeper" left untranslated.
2. **Wooden Plank → "Placa de madeira"** (GK1) and, following it, **Oiled/Reinforced Plank → "Placa oleada/reforçada"**, while **Board → "Prancha"**. Because of this, Wooden Sign became "Letreiro de madeira".
3. **Ink → "Tinta"** and **Paint → "Tinta de pintura"**. Portuguese uses one word for both.
4. **Detail → "Peça"**. "Simple iron part" became "Peça de ferro simples", which sits close to "Peça de ferro" (Iron Detail).
5. **Stick → "Graveto"**. It could also be "Vareta" or "Pau".
6. **Garden → "Horta"**, **Gardener Stand → "Posto do jardineiro"**, **Gardening → "Horticultura"**. "Jardim" is also plausible.
7. **Upgrade = Aprimorar/Aprimoramento vs Improve = Melhorar/Melhoria**. This is a deliberate split, but the official text may use one word for both.
8. **Brewing Stand → "Bancada de cervejaria"**.
9. **Sluice Box → "Calha de lavagem"**.
10. **Kiln → "Forno de olaria"**. The alternative is "Forno de cerâmica".
11. **Chopping Spot → "Cepo de lenha"**.
12. **Stonemason's Workbench → "Bancada de cantaria"**.
13. **Techbook → "Livro técnico"** (Blue/Green/Red).
14. **Berserker Potion → "Poção de fúria"**, chosen to match the Berserk buff "Fúria".
15. **Headstart Fertilizer → "Fertilizante de arranque"** and **Crop Boosting Fertilizer → "Fertilizante potencializador de colheita"**.
16. **Church Smells → "Aromas da igreja"** and **Church Shrine → "Altar da igreja"**.
17. **Body Places I/II → "Lugares para corpos"**.
18. **Grave Area / Walkway Area / Empty Grave → "Área de covas" / "Área de passagem" / "Cova vazia"**. Grave is rendered as "cova", not "túmulo".
19. **Zombie Power → "Força zumbi"**, kept separate from Factory power → "energia da fábrica".
20. **Alkali → "Alcalino"**. This is the GK1 form, but grammatically it is an adjective. "Álcali" is the noun.
21. **Tech names that are jokes:** "Anyway..." → "Enfim...", "Oh no!" → "Ah, não!", "Suit Up!" → "Vista-se!".
22. **Pun quest titles** (in the key set or in obtain texts): Press for Cash → "Prensa por dinheiro", Rhyme and Printed → "Rima e impressão", Nun of Your Business → "Não é da sua freira", The Frill of the Chase → "O babado da caçada", Two Peas in a Pod → "Unha e carne", Jack in a Boat → "Jack num barco", I Love You, Man → "Eu te amo, cara", Go Wild in the Wild Lands → "Solte a fera nas Terras Selvagens".
23. **Jeweler perk → "Talento: Joalheiro"**. The official pt-BR word for "perk" is unknown. It could be "Vantagem" or "Habilidade".
24. **NPC epithets:** Davy the Dagger → "Davy, o Punhal", Comrade Donkey → "Camarada Burro", Trademaster → "Mestre do comércio".
25. **Latin alchemy names** (Aqua vitae, Mercurius vivus, Rubedo crystallis, Coniunctio/Separatio/Mortificatio/Nigredo/Albedo) are kept in Latin inside Portuguese phrases. The official text may translate them.

## Regenerating

The generator (name table, templates for obtain sentences, hand-translated sentences, coverage validator) ran from Claude's session scratchpad and is **not** in this repo, because `scripts/` belongs to another agent. If the dataset changes, the simplest path is to ask for a re-run, or to recover the generator from the session archive (`historico/sessao-2026-10-30-companheiro-gk2.zip`) and add it to `scripts/` (open item in `BACKLOG.md`). A name that is not in this file falls back to English.
