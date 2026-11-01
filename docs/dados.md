# Dados do Companheiro GK2

De onde vêm os dados, o que se pode fazer com eles, como estão organizados e o que falta. Números do build da 1.8.4 (01/11/2026). Os detalhes de cada arquivo estão nos READMEs em `data/` (em inglês).

## Fontes

| fonte | o que dá | como | onde fica |
|---|---|---|---|
| **wikily.gg** (wiki do Graveyard Keeper 2) | Receitas, itens, construções, estações, tecnologias, fórmulas de alquimia, URLs dos ícones. Em inglês; com `locale=pt-br` (minúsculas) a mesma API devolve os nomes em português | API pública de datasets, GET simples, 1 req/s: `https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/<slug>/list?limit=120&offset=N&locale=en&sortField=name&sortDir=asc`, com slugs `recipes`, `items`, `buildings`, `crafting-stations`, `technologies`, `alchemy-formulas`, `quests`. O servidor limita `limit` a 120. Com `locale=pt-BR` ou `pt` ele responde em inglês, sem erro | `data/raw/api-*.json` (fora do git) → `data/items.en.json`, `data/recipes.en.json` |
| wikily.gg, calculador | Qual receita o calculador do wiki usa para cada item (`calculator_default`) | A página `/crafting-calculator` fica atrás do desafio do Cloudflare (403 no curl). Foi aberta uma vez num navegador e as props do componente React foram salvas | `data/raw/calculator-props.json` (fora do git) |
| **Arquivos do jogo** (Steam app **4358690**, versão **1.011**, build Steam 26297960, Unity 6000.3) | Texto oficial em 11 idiomas, incluindo pt-BR: 9.474 chaves | `tools/exportar-textos/` no Windows com o jogo instalado. Lê o MonoBehaviour `lng_<idioma>` em `GraveyardKeeper2_Data/resources.assets`, só leitura | `data/game-texts/gk2_textos.json` (`{chave: {en, pt}}`, no git). Os 11 idiomas, os CSVs e `_resumo.json` ficam na mesma pasta, fora do git |
| Mod tailandês GK2Thai (`Jakkrich/graveyardkeeper2-bepinex-thai-plugin`) | Texto inglês do jogo com as chaves (`source_en.csv`, versão 1.0024). Serviu para ligar nome EN do wiki → `gameKey` | Download do CSV | `data/raw/l10n/thai_source_en.csv` |
| Wiki Fandom do GK1 em pt-BR | Pares EN → pt de nomes do primeiro jogo | MediaWiki API, `prop=langlinks` (script aposentado, no histórico do git) | `data/raw/l10n/gk1_*.json` → `names.manual` (`gk1-wiki`) |
| Claude | Tradução de máquina de tudo, como reserva | Escrita à mão na sessão | `data/names.machine.pt-BR.json` |

Versões: as receitas do wiki descrevem o jogo **1.010** (texto do próprio wiki em 30/10/2026). Os textos do jogo são da **1.011**. Quando o jogo mudar, as duas fontes precisam ser atualizadas (`docs/atualizacao.md`).

## Direitos e uso: conteúdo de fã

O Companheiro GK2 é um projeto de fã, gratuito e sem fins lucrativos, sem vínculo com a Lazy Bear Games ou a tinyBuild e sem endosso delas. A arte, os ícones, os nomes e os textos do jogo (© Lazy Bear Games / tinyBuild) são usados como conteúdo de fã, com crédito, como fazem as wikis e outras ferramentas de fã; o que os donos pedirem para tirar ou mudar sai ou muda. O único ponto ainda em aberto são os dados do wikily, a acertar antes da divulgação em massa.

- **wikily.gg não tem licença aberta.** O rodapé diz `© 2026 Wikily · NX Software`. Os Termos de Uso proíbem reproduzir o conteúdo "por spidering, scraping ou outro meio técnico" e o uso comercial sem licença. A NX Software é uma SAS francesa, então o direito *sui generis* de banco de dados da UE também pode valer. Pedido de autorização enviado a **contact@wikily.gg** em 31/10/2026, aguardando resposta (os ícones foram baixados de `media.wikily.gg`, então entram no mesmo pedido). O crédito mínimo, já no rodapé: *"Recipe data: Graveyard Keeper 2 Wiki by Wikily (https://wikily.gg/graveyard-keeper-2), © NX Software"*.
- **Arte e textos do jogo © Lazy Bear Games / tinyBuild.** Os ícones vão embutidos no sprite, e o texto oficial em pt-BR vem dos arquivos do jogo.
- O dump completo do jogo (11 idiomas, CSVs) fica fora do git. No git só fica a tabela en/pt usada pelo build.

## Modelo de dados

A saída do build é `data/gk2.json` (schema 1, descrito em detalhe em `scripts/README-build.md`). Textos traduzíveis são objetos `{pt, en}`.

- **`items`** (838, chave = id em slug do wiki, estável entre atualizações). Campos principais: `pt`, `en`, `cat`, `icon`, `tr` (nível da tradução), `raw` (folha por padrão), `obtain`, `kind`, `listed`, `unobtainable`, `recipes` (melhor primeiro), `defaultRecipe`. Opcionais: `members` (grupos como "Qualquer jornal"), `runes` (alquimia), `key` (gameKey).
  - Por `kind`: item 544, building 130, station 87, quality-variant 33, virtual 18, action 16, group 10.
  - 302 são `raw`. 309 não têm `defaultRecipe` (matérias-primas, itens sem receita útil ou presos em ciclo).
- **`stations`** (79): `pt`, `en`, `tr`, `icon`. O id é o id do item da estação.
- **`recipes`** (707): `out {item, qty}`, `in [{item, qty, note?}]`, `station`, `alt` (estações alternativas), `ext` (extensão exigida), `extra` (subprodutos), `tech {id, type, pt, en}`, `mastery`, `ticks`, `energy`, `type`, `cd`, `listed`, `noexp`, `cyc`, `zone`, `runes`, `example`.
  - Por tipo: hand_craft 241, building 225, auto 80, factory 69, star_craft 47, alchemy 28, grow 17.
  - 71 itens têm mais de uma receita. O build escolhe o padrão: `cd` (escolha do calculador do wikily) primeiro, depois listada antes de oculta, depois por tipo.
- **Fatos do item** (`data/facts.json`, gerado por `scripts/build_facts.py` a partir de `data/raw/api-items-all.json`, que já estava em cache: nada foi baixado). O `build.py` copia para `gk2.json` e para a página quando o arquivo existe. Campos novos em `items`:
  - `where`: onde conseguir, uma lista de fontes `[tipo, ref, …]`. `ref` é uma chave de `meta.refs.names` ou `@<id do item>`. Tipos: `buy` (comprar; `["buy", comerciante, nível]`, nível omitido = desde o início, `"talk"` = só na conversa), `fish` (`["fish", local, isca, % de dia, % de noite]`, a melhor isca do local), `gather`, `quest`, `battle`, `chest` (baú cheio uma vez no início), `found`, `looter`, `autopsy`, `burial`, `container`, `town`, `study`, `church`, `start`, `outfit`, `resurrect`, `character`. Ordem: lojas, pesca, coleta, o resto na ordem do wiki. "Construído no Quartel" fica de fora (a receita de construção já diz). 292 itens têm fontes: 176 compráveis, 22 peixes.
  - `use`: efeito de uso. `en` (energia devolvida, 59 itens), `ins` (insanidade, 17), `enB`/`insB` (`[valor, reforço]`, o valor com um reforço ativo, ex. 22 com Aquecido), `buff` (`[reforço, segundos, 1 = usar outro reinicia o tempo]`, 14 itens).
  - `stack`: tamanho da pilha (os 544 itens com página no wiki).
  - `meta.refs.names` (215 nomes de comerciantes, locais, missões, batalhas, pontos de coleta) e `meta.refs.buffs` (15 reforços com nome e descrição): `{pt, en}` quando o texto é oficial, `{pt, en, tr: "machine" | "missing"}` quando não é (a página mostra o selo "não oficial"). pt: tabela do jogo (`gk2_textos.json`, mesmo texto em inglês) primeiro, depois `names.official.pt-BR.json`, depois o glossário `MT` do script (41 nomes, todos pontos de coleta e afins). As descrições oficiais trocam os ícones do jogo (`<sprite name="talent_orange">`) por palavras ("Engenharia").
  - Custo: cerca de 38 KB a mais em `dist/preview.html` (dados) e 17 KB de código e estilo do detalhe.
  - **Ficha do item** (Receitas, detalhe do item):
    - `sell` (bloco "Quem compra", 197 itens): um `[comerciante, menor, maior, curtidas, nível das curtidas, nível]` por comprador, zeros do fim cortados. Menor/maior = quanto ele paga por 1 com o estoque normal, do nível 1 ao 3 do comerciante (132 itens têm esse número; nos outros só há o preço base). Curtidas = o máximo por semana vendendo para ele (-1 = "dá curtidas", sem número; 75 itens). Dinheiro em bronze (1 prata = 100 bronze, 1 ouro = 100 prata). A tela mostra "até N" (o preço base) ao lado do preço e um "i" explicando que o preço cai quando o comerciante já tem estoque e que peixe tem preço fixo.
    - `price` (preço base, o teto quando o comerciante está sem estoque) e `fix: 1` (preço fixo, como nos peixes). Só nos 197 itens que alguém compra: nos outros 109 dos 306 com preço o número não aparece em lugar nenhum.
    - `study` (bloco "Estudar", 333 itens): `[vermelho, verde, azul, Ciência, Fé]`, zeros do fim cortados; 39 custam Fé. A caixinha "Já estudei" grava `studied` (lista global de ids de item, sincronizada, fusão por união) no estado do app.
    - `asked` (bloco "Pedido em", recolhido por padrão por causa de spoiler): `{q: [[missão, qtd, quem pede]], t: [[restauração, qtd]], o: [[comerciante, qtd, nível, curtidas]]}`. Missões: 81 itens, 93 pedidos em 60 missões, de `data/raw/days/probe-quests.json` (itens entregues ou levados; os 3 que a missão dá ao jogador ficam de fora). Restauração do povoado: 29 itens; encomendas do povoado: 22. Consertos, batalha, isca, sermões, bolsas, combate e a descrição do jogo ficaram de fora. Nomes das missões, restaurações e comerciantes: oficiais. Quem pede: 4 nomes saem de falas oficiais do jogo (Davy the Dagger = Orlando, Olha a Faca; Hans = Anselmo; Sven = Arnaldo; Old God = Deus Antigo); 7 não têm texto oficial e levam o selo "não oficial" (Capitão, Guardas da vila, Líder dos mercenários, Monge, Refugiados, Alma, Dig).
    - Custo: cerca de 28 KB de dados e 19 KB de código e estilo em `dist/preview.html`.
    - `probe-quests.json` é o dataset `quests` do wiki: ao atualizar o wiki, baixe e copie (passo 1 de `docs/atualizacao.md`).
- **`data/techs.json`** (226 tecnologias em 6 ramos): custo em pontos vermelho/verde/azul, `parents`/`children` (um DAG, nenhuma aresta cruza ramos), posição na árvore, `rep` (exige reputação), `unlocks`, `recipes`, `notes`. Detalhes em `data/README-techs.md`. 579 receitas apontam para uma tecnologia. 12 apontam para missão e 1 para perk, que não têm registro na árvore.

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

Algumas receitas consomem o próprio produto, como os "Melhorar órgão" de ossos e cérebro. O `validate.py` acha 7 componentes cíclicos. 13 receitas recebem `cyc: true` e nunca são escolhidas como padrão. 7 itens ficam "presos" (`cycle-trapped`: toda receita deles volta para eles) e viram folha. O grafo das receitas padrão não tem ciclo, mas a interface precisa se proteger mesmo assim, porque o usuário pode escolher outra receita.

## Camadas de tradução (pt-BR)

Cada arquivo de nomes é um objeto com chave = **texto inglês exato** e valor `{pt, source, confidence}`. São três, lidos pela mesma busca (`scripts/name_layers.py`) no `build.py`, no `build_techs.py` e no `build_facts.py`. A regra cabe numa frase: **correção (`fix`) > oficial > à mão > máquina**; dentro de um arquivo e em empate, vence o primeiro.

| prioridade | camada | arquivo | conteúdo |
|---|---|---|---|
| 0 | **correção** (`fix`, `likely`) | dentro de `names.manual` | Erro de digitação do texto oficial: vence tudo e fica `likely` (sem selo, mas sem dizer "oficial"). Hoje só "Wheat Bed" → "Canteiro de Trigo" (o jogo diz "Canteiro de Trigorigo") |
| 1 | **oficial** (`game-files`, `official`) | `data/names.official.pt-BR.json` | 1.020 nomes: 972 ligados pela `gameKey` + 48 ligados à mão pelo texto inglês (zonas, perks, Suco de Uva, 4 nomes com ícone no meio). Gerado por `juntar_nomes.py --atualizar` |
| 2 | **à mão** (`wikily-pt`/`gk1-wiki` `likely`, `derived` `guess`, `game-files` `official`) | `data/names.manual.pt-BR.json` | 318 nomes: os 231 de receita (campo `recipes`: 159 da wiki em pt, 67 compostos por nós com selo "não oficial", 5 textos inteiros do jogo; grau "(ouro)" como no app), 9 categorias com a palavra do jogo (campo `game`), 77 da wiki do GK1 (o oficial cobre 76; só "Alquimia" aparece) e a correção |
| 2b | **derivado** (`derived`, `likely`) | sintético, dentro do `build.py` | Montado a partir de partes oficiais: "X (ouro)", "A ou B", "Qualquer X", "Abrir (X)", "Consertar (X)". 47 itens |
| 3 | **máquina** (`machine`, `guess`) | `data/names.machine.pt-BR.json` | 1.066 nomes + 736 textos `__obtain`/`__notes`. Tradução do Claude, com glossário consistente; só aparece onde não há nada melhor. Guarda também a `gameKey` de cada nome (o `juntar_nomes.py` usa) |

O `build_techs.py` consulta, logo depois do oficial, a tabela do jogo (`data/game-texts/gk2_textos.json`) para ramos, missões, NPCs e prédios da cidade. O `build_facts.py` (quem vende, onde achar) lê essa tabela primeiro e tem um glossário próprio (`MT`) para nomes que nenhuma camada tem. O `build_days.py` tira os nomes direto da tabela do jogo, pela chave. Até 01/11/2026 eram cinco arquivos (`names.recipes`, `names.wiki` e `names.pt-BR`, este feito por `build_names.py`); estão no histórico do git.

Resultado hoje: itens com 784 nomes oficiais, 48 prováveis (47 derivados e o "Canteiro de Trigo" corrigido) e 6 de máquina. Tecnologias: 221 oficiais e 5 prováveis.

## Lacunas conhecidas

- **Quantidades base.** Bônus de perk só aparecem como texto ("4, ou 6 com Cozinheiro II").
- **Variantes de qualidade colapsadas.** Várias receitas "a partir de X (ouro/prata)" consomem o item base. É a principal fonte de conta errada (AUDITORIA D1).
- **Alquimia é combinatória.** As entradas são só uma mistura sugerida (`example: true`).
- **Plantio** tem rendimento desconhecido (`out.qty: null`).
- **Reparos não são receitas.** Estações que vêm de consertar algo (Forno da Cozinha...) aparecem como matéria-prima.
- **Nomes de receita**: todos em pt desde 11/2026 (`data/names.manual.pt-BR.json`); 67 são compostos por nós e levam o selo "não oficial". A qualidade das receitas "X a partir de Y (ouro)" é deduzida pela página, pelo nome e pelo id da receita (`GK.data`). **Categorias** (36 de 53) ainda de máquina (9 trocadas pela palavra do jogo em `names.manual.pt-BR.json`). Também de máquina: 3 maestrias e 21 notas (`data/report-l10n.md`).
- **Nomes pt repetidos** entre itens diferentes ("Tinta" = Ink e Paint).
- **Oficiais estranhos** vindos do próprio jogo: "Banco de Montagem II" × "Bancada de Montagem I", caixa inconsistente.
- **`names.machine.pt-BR.json` não tem gerador** no repositório. Itens novos ficam sem nome de máquina e sem `gameKey` até alguém escrever a entrada à mão.
- **Fatos do item só para os 544 itens com página no wiki.** Construções e estações não têm `where`/`use`/`stack`. Ícones dos reforços não vieram (seria preciso baixar 15 ícones e refazer a folha de ícones): o detalhe desenha um ícone redondo genérico. O nome de quem vende é o do NPC no jogo ("Herm" aparece como Hamilton, "Trademaster" como Gerente Comercial), que difere do texto longo "Como obter", traduzido por máquina.
- O texto do jogo traz tags (`<sprite name="...">`) e tokens (`@(Tecla)`). O `juntar_nomes.py` tira as tags no modo `--atualizar`. Os 4 nomes com ícone no meio do texto são conferidos à mão.
