# Dados do Companheiro GK2

De onde vêm os dados, o que se pode fazer com eles, como estão organizados e o que falta. Números de 30/10/2026. Os detalhes de cada arquivo estão nos READMEs em `data/` (em inglês).

## Fontes

| fonte | o que dá | como | onde fica |
|---|---|---|---|
| **wikily.gg** (wiki do Graveyard Keeper 2) | Receitas, itens, construções, estações, tecnologias, fórmulas de alquimia, URLs dos ícones. Só em inglês | API pública de datasets, GET simples, 1 req/s: `https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/<slug>/list?limit=120&offset=N&locale=en&sortField=name&sortDir=asc`, com slugs `recipes`, `items`, `buildings`, `crafting-stations`, `technologies`, `alchemy-formulas`. O servidor limita `limit` a 120 e ignora `locale` | `data/raw/api-*.json` (fora do git) → `data/items.en.json`, `data/recipes.en.json` |
| wikily.gg, calculador | Qual receita o calculador do wiki usa para cada item (`calculator_default`) | A página `/crafting-calculator` fica atrás do desafio do Cloudflare (403 no curl). Foi aberta uma vez num navegador e as props do componente React foram salvas | `data/raw/calculator-props.json` (fora do git) |
| **Arquivos do jogo** (Steam app **4358690**, versão **1.011**, build Steam 26297960, Unity 6000.3) | Texto oficial em 11 idiomas, incluindo pt-BR: 9.474 chaves | `tools/exportar-textos/` no Windows com o jogo instalado. Lê o MonoBehaviour `lng_<idioma>` em `GraveyardKeeper2_Data/resources.assets`, só leitura | `data/game-texts/gk2_textos.json` (`{chave: {en, pt}}`, no git). Os 11 idiomas, os CSVs e `_resumo.json` ficam na mesma pasta, fora do git |
| Mod tailandês GK2Thai (`Jakkrich/graveyardkeeper2-bepinex-thai-plugin`) | Texto inglês do jogo com as chaves (`source_en.csv`, versão 1.0024). Serviu para ligar nome EN do wiki → `gameKey` | Download do CSV | `data/raw/l10n/thai_source_en.csv` |
| Wiki Fandom do GK1 em pt-BR | Pares EN → pt de nomes do primeiro jogo | MediaWiki API, `prop=langlinks` (`scripts/fetch_gk1_langlinks.py`) | `data/raw/l10n/gk1_*.json` |
| Claude | Tradução de máquina de tudo, como reserva | Escrita à mão na sessão | `data/names.pt-BR.json` (parte `machine`), `data/names.machine.pt-BR.json` |

Versões: as receitas do wiki descrevem o jogo **1.010** (texto do próprio wiki em 30/10/2026). Os textos do jogo são da **1.011**. Quando o jogo mudar, as duas fontes precisam ser atualizadas (`docs/atualizacao.md`).

## Direitos e uso: conteúdo de fã

O Companheiro GK2 é um projeto de fã, gratuito e sem fins lucrativos, sem vínculo com a Lazy Bear Games ou a tinyBuild e sem endosso delas. A arte, os ícones, os nomes e os textos do jogo (© Lazy Bear Games / tinyBuild) são usados como conteúdo de fã, com crédito, como fazem as wikis e outras ferramentas de fã; o que os donos pedirem para tirar ou mudar sai ou muda. O único ponto ainda em aberto são os dados do wikily, a acertar antes da divulgação em massa.

- **wikily.gg não tem licença aberta.** O rodapé diz `© 2026 Wikily · NX Software`. Os Termos de Uso proíbem reproduzir o conteúdo "por spidering, scraping ou outro meio técnico" e o uso comercial sem licença. A NX Software é uma SAS francesa, então o direito *sui generis* de banco de dados da UE também pode valer. Pedido de autorização enviado a **contact@wikily.gg** em 31/10/2026, aguardando resposta (os ícones foram baixados de `media.wikily.gg`, então entram no mesmo pedido). O crédito mínimo, já no rodapé: *"Recipe data: Graveyard Keeper 2 Wiki by Wikily (https://wikily.gg/graveyard-keeper-2), © NX Software"*.
- **Arte e textos do jogo © Lazy Bear Games / tinyBuild.** Os ícones vão embutidos no sprite, e o texto oficial em pt-BR vem dos arquivos do jogo.
- O dump completo do jogo (11 idiomas, CSVs) fica fora do git. No git só fica a tabela en/pt usada pelo build.

## Modelo de dados

A saída do build é `data/gk2.json` (schema 1, descrito em detalhe em `scripts/README-build.md`). Textos traduzíveis são objetos `{pt, en}`.

- **`items`** (820, chave = id em slug do wiki, estável entre atualizações). Campos principais: `pt`, `en`, `cat`, `icon`, `tr` (nível da tradução), `raw` (folha por padrão), `obtain`, `kind`, `listed`, `unobtainable`, `recipes` (melhor primeiro), `defaultRecipe`. Opcionais: `members` (grupos como "Qualquer jornal"), `runes` (alquimia), `key` (gameKey).
  - Por `kind`: item 544, building 130, station 87, virtual 18, action 16, quality-variant 15, group 10.
  - 290 são `raw`. 297 não têm `defaultRecipe` (matérias-primas, itens sem receita útil ou presos em ciclo).
- **`stations`** (79): `pt`, `en`, `tr`, `icon`. O id é o id do item da estação.
- **`recipes`** (695): `out {item, qty}`, `in [{item, qty, note?}]`, `station`, `alt` (estações alternativas), `ext` (extensão exigida), `extra` (subprodutos), `tech {id, type, pt, en}`, `mastery`, `ticks`, `energy`, `type`, `cd`, `listed`, `noexp`, `cyc`, `zone`, `runes`, `example`.
  - Por tipo: hand_craft 241, building 225, auto 80, factory 69, star_craft 35, alchemy 28, grow 17.
  - 66 itens têm mais de uma receita. O build escolhe o padrão: `cd` (escolha do calculador do wikily) primeiro, depois listada antes de oculta, depois por tipo.
- **`data/techs.json`** (226 tecnologias em 6 ramos): custo em pontos vermelho/verde/azul, `parents`/`children` (um DAG, nenhuma aresta cruza ramos), posição na árvore, `rep` (exige reputação), `unlocks`, `recipes`, `notes`. Detalhes em `data/README-techs.md`. 567 receitas apontam para uma tecnologia. 12 apontam para missão e 1 para perk, que não têm registro na árvore.

### Marcas de "oculto"

O que a interface esconde por padrão ou marca:

| campo | significado | quantos |
|---|---|---|
| `items[].listed: false` | escondido na lista do wiki (conteúdo não usado ou inalcançável) | 104 itens |
| `items[].unobtainable: true` | nada no jogo 1.010 dá o item | 91 |
| `kind: virtual` / `action` | não é item de inventário (rezas, "História", buffs, consertos, abrir porta) | 18 / 16 |
| `recipes[].listed: false` | receita escondida no wiki | 22 |
| `recipes[].noexp: true` | nunca expandir (plantio: o rendimento varia) | 17 |
| `techs[].hidden` / `given` | tecnologia escondida até ser revelada / dada pela história | 38 / 4 |

### Ciclos

Algumas receitas consomem o próprio produto, como os "Melhorar órgão" de ossos e cérebro, ou o vinho que vira vinho melhor. O `validate.py` acha 8 componentes cíclicos. 15 receitas recebem `cyc: true` e nunca são escolhidas como padrão. 7 itens ficam "presos" (`cycle-trapped`: toda receita deles volta para eles) e viram folha. O grafo das receitas padrão não tem ciclo, mas a interface precisa se proteger mesmo assim, porque o usuário pode escolher outra receita.

## Camadas de tradução (pt-BR)

Cada arquivo de nomes é um objeto com chave = **texto inglês exato** e valor `{pt, source, confidence}`. O `build.py` aplica todos e o melhor nível vence: **official > likely > guess > machine**. Em empate, vence o primeiro arquivo.

| prioridade | camada | arquivo | conteúdo |
|---|---|---|---|
| 1 | **oficial** (`game-files`, `official`) | `data/names.official.pt-BR.json` | 1.004 nomes: 972 ligados pela `gameKey` + 32 ligados à mão pelo texto inglês (zonas, perks, Suco de Uva, 4 nomes com ícone no meio). Gerado por `juntar_nomes.py` |
| 2 | **derivado** (`derived`, `likely`) | sintético, dentro do `build.py` | Montado a partir de partes oficiais: "X (ouro)", "A ou B", "Qualquer X", "Abrir (X)". 29 itens |
| 3 | **GK1** (`gk1-wiki`, `likely`) | `data/names.pt-BR.json` | 77 nomes da wiki do GK1. O mesmo arquivo traz as `gameKey` |
| 4 | **máquina** (`machine`, `guess`) | `data/names.pt-BR.json` (988) e `data/names.machine.pt-BR.json` (1.065 nomes + 725 textos `__obtain`) | Tradução do Claude, com glossário consistente. Só aparece onde não há nada melhor |

O `build_techs.py` usa a mesma ordem e, além dela, consulta direto `data/game-texts/gk2_textos.json` para ramos, missões, NPCs e prédios da cidade.

Resultado hoje: itens com 785 nomes oficiais, 29 derivados e 6 de máquina. Tecnologias: 224 oficiais e 2 prováveis.

## Lacunas conhecidas

- **Quantidades base.** Bônus de perk só aparecem como texto ("4, ou 6 com Cozinheiro II").
- **Variantes de qualidade colapsadas.** Várias receitas "a partir de X (ouro/prata)" consomem o item base. É a principal fonte de conta errada (AUDITORIA D1).
- **Alquimia é combinatória.** As entradas são só uma mistura sugerida (`example: true`).
- **Plantio** tem rendimento desconhecido (`out.qty: null`).
- **Reparos não são receitas.** Estações que vêm de consertar algo (Forno da Cozinha...) aparecem como matéria-prima.
- **Nomes de receita** (232) quase todos sem pt. A qualidade das receitas "X a partir de Y (ouro)" é deduzida pela página, pelo nome e pelo id da receita (`GK.data`). **Categorias** (45 de 53) ainda de máquina. Também de máquina: 3 maestrias e 21 notas (`data/report-l10n.md`).
- **Nomes pt repetidos** entre itens diferentes ("Tinta" = Ink e Paint).
- **Oficiais estranhos** vindos do próprio jogo: "Banco de Montagem II" × "Bancada de Montagem I", caixa inconsistente.
- **`names.machine.pt-BR.json` não tem gerador** no repositório. Itens novos ficam sem a camada de máquina até alguém traduzir.
- O texto do jogo traz tags (`<sprite name="...">`) e tokens (`@(Tecla)`). O `juntar_nomes.py` tira as tags no modo `--atualizar`. Os 4 nomes com ícone no meio do texto são conferidos à mão.
