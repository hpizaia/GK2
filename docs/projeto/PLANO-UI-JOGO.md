# Plano: sinais do jogo na interface (Companheiro GK2)

> 31/10/2026, sobre a versão 1.5.1. Documento de plano: nada disto está no app ainda.
> Protótipo: numa pasta interna (fora do git), publicado como artifact privado em https://claude.ai/artifact/C7aaTk2E5Z7sNQsuniYdie. É o app 1.5.1 de verdade com as mudanças pontuais e um botão **Atual / Novo** para comparar.

## 1. Resumo em 5 linhas

1. O app **continua como está**: estrutura, cores de fundo, cartões, abas, títulos e letras de `src/css/tokens.css`.
2. Do jogo entram **só sinais pontuais**, que o jogador reconhece de relance: check verde, ícone em espaço escuro, número amarelo da pilha, azul da energia, roxo da insanidade e × vermelho no fechar.
3. O balão de pergaminho fica **só na ficha do item** (já está no app desde a 1.5.0). A única correção é o texto do balão, um tom mais escuro, porque hoje parte dele fica abaixo de 4,5:1.
4. São **2 lotes pequenos** (P + P). A troca da letra do texto (Alegreya Sans pela letra do sistema) fica como proposta separada.
5. Regra para tudo o que vier: **limpo e minimalista, sinais do jogo, não molduras do jogo**. Legibilidade e uso vêm antes da semelhança.

## Decisão de 31/10 (noite)

A primeira versão deste plano ("janela do jogo") foi mostrada ao Hugo e **recusada por ficar pesada**. Ela trocava a cara do app inteiro: faixa de couro nos títulos e abas, losangos dourados, estações em quadros de madeira com moldura dourada, linha laranja entre quadros, Hoje como selo do HUD, janelas de ardósia com aro de ferro, grão e roda de pedra.

**Regra a partir daqui: limpo e minimalista. Sinais do jogo, não molduras do jogo.** Tudo o que estava na lista acima saiu do plano.

---

## 2. O que o jogo faz na interface

A pesquisa continua valendo: ela mostra o que existe no jogo, e a seção 3 diz o pouco que entra. Cores amostradas com Python nas capturas oficiais da Steam (1920 × 1080) e numa captura do Gamer Guides. JPEG muda a cor 1 ou 2 tons: use como direção, não como valor exato. As capturas ficaram só no scratchpad (licença); nada foi copiado para o repositório.

### Paleta amostrada

| O que é | Onde vi | Hex |
|---|---|---|
| Faixa de título das janelas (couro) | Árvore de Tecnologias, topo | `#735939` – `#7c603b` |
| Aba ativa (pergaminho levantado) | "Tech Tree" ativa | `#a37d4e` |
| Texto creme dos títulos | abas, título dos quadros | `#ffe8b6`, `#fff0c6` |
| Fundo da janela da árvore | atrás dos quadros | `#202028` – `#282020` |
| Janela do inventário (ardósia) | inventário | `#393138`, espaço `#383037` |
| Corpo do quadro da árvore (madeira) | nó "The Concept of Wood" | `#47382b` |
| Cabeçalho e rodapé do quadro | faixa ocre do nó | `#785128` |
| Moldura dourada do quadro | borda do nó | `#b78524` |
| Linha que liga os quadros | conectores | `#f19504` |
| Check verde | rodapé do nó | `#30c018` (sombra escura embaixo) |
| Botão fechar | × do canto | fundo `#79100f`, aro `#f14261`, × creme |
| Balão do item (pergaminho) | balão "Wheat seed" | `#c7a978` → `#a88958` |
| Texto do balão | título / rótulo | `#5e350a` / `#927342` (rótulo com contraste baixo) |
| Barra de energia | HUD, canto da tela | `#40b0f8`, raio `#3898f8`, trilho `#1f1e24` |
| Insanidade | HUD, cérebro roxo | `#9020b0` |
| Moldura do HUD | barra e contadores | `#363549`, aro `#404050` |
| Número da pilha | barra de atalhos | `#ffc200` com contorno escuro |
| Número do espaço (1, 2, 3) | barra de atalhos | `#949293` |
| Selo de lugar ("Garden") | canto superior | fundo `#303048`, texto `#ffca70` |
| Aviso de coleta ("+3 Stick") | canto inferior | `+3` verde `#59bf00`, nome `#e7ac7c` |
| Roda da semana | canto superior | pedra `#4e4f5a`, medalhões coloridos |

### Molduras e janelas
- **Janela** (inventário, Árvore): retângulo de ardósia com aro de ferro de 2 a 3 px, rebites e enfeites nos cantos. No topo, uma **faixa de couro** com o título centralizado em creme e um ícone à esquerda (a bolsa no inventário).
- **Abas**: na faixa de couro, separadas por **losangos dourados** com fios; a aba ativa vira um **pergaminho mais claro e levantado**. As sub-abas (ramos da árvore) são quadrados com ícone.
- **Quadros da árvore**: madeira escura, **cabeçalho e rodapé ocre**, moldura dourada fina, ícones em espaços escuros, **check verde** no rodapé quando pesquisado. **Linhas laranja** com curvas ligam um quadro ao seguinte.
- **Cantos**: quase retos (2 a 4 px), em degrau de pixel. Nada de cantos arredondados grandes.

### Balões (tooltips)
- **Pergaminho claro** com **ponta** apontando para o espaço do item, título centralizado, **linha pontilhada com losango** separando blocos, rótulo em marrom claro e valor escuro, ícone de maestria verde. O protótipo 22 ("Energia e efeito") já copiou esse balão e o Hugo aprovou.

### Ícones de estado
- **Check verde** com sombra escura (pesquisado, pronto).
- **× creme num quadrado vermelho** com aro claro (fechar).
- **Número amarelo** no canto inferior direito do espaço (quantidade); número cinza do atalho no canto esquerdo.
- **Espaço selecionado**: moldura dourada.
- **Cadeado**: não achei captura nítida; o jogo marca o que falta com o quadro apagado. Proposta: cadeado em SVG próprio só onde já existe "bloqueado".

### Tipografia
- O jogo usa uma **fonte pixel** (bitmap), negrito, com **contorno ou sombra escura de 1 px** nos títulos em creme. Nenhuma fonte achou o nome dela (procurei em resenhas, wiki e loja). É arte do jogo: **não usar**.
- Textos oficiais em português existem no arquivo do jogo no projeto (`data/game-texts/gk2_textos.json`): "Inventário", "Árvore de Tecnologias", "Efeito de uso", "Maestria necessária", "Produzir", "Construir", "Energia", "Insanidade". O app já usa vários.

### Barras
- **Energia**: cápsula azul (`#40b0f8`, brilho no topo, sombra embaixo) num trilho escuro com moldura de ferro, e o **raio** num quadrado ao lado.
- **Insanidade**: roxa, com o **cérebro**; come o topo da barra de energia (máximo = 100 menos insanidade).
- **Progresso** de estações (oficina): barrinhas **verdes** curtas embaixo de cada máquina.

### O que dizem de fora
- Resenhas (vistas via busca) dizem que a interface do jogo **às vezes é confusa** e que os balões só dão o básico. Ou seja: o companheiro deve parecer o jogo, mas **explicar mais** do que ele.
- O wikily.gg (wiki dos dados) também se veste "de jogo": ícone em espaço, nome em dourado, cartões de números. Bom sinal de que fãs esperam esse tom.

---

## 3. Princípios

### Copiar do jogo (só sinais)

| Sinal | Onde entra | Por quê |
|---|---|---|
| Check verde | caixinhas marcadas (Planejador, Hoje, Tecnologias) | "pronto" no jogo é esse check; lê melhor que o quadrado verde cheio de hoje |
| Ícone em espaço escuro | todos os espaços de ícone, **nos dois temas** | os ícones foram desenhados para fundo escuro; no claro hoje eles somem um pouco |
| Número amarelo no canto do ícone | ficha do item (pilha, já existe) e linha com "tenho N de M" | no jogo é "quanto você carrega": mesmo sentido aqui |
| Azul da energia (cápsula e raio) | balão da ficha (já existe) e um selo "+20" nas comidas da lista de Receitas e da busca | ajuda a escolher comida sem abrir a ficha |
| Roxo da insanidade | mesmo selo, quando a comida mexe na insanidade | o jogo usa roxo para insanidade; ninguém mais usa roxo no app |
| × vermelho em quadrado | só no fechar da faixa de aviso de patch | é o "fechar" das janelas do jogo; num só lugar, para não virar ruído |
| Barra em cápsula | Progresso, em **verde** | ver abaixo |

**Por que a barra de Progresso é verde, e não azul:** no jogo, azul quer dizer energia. Se o Progresso fosse azul, a mesma cor diria duas coisas. Verde é "pronto" no jogo (o check e as barrinhas das oficinas) e já é a cor de "feito" no app. Da barra de energia vem só a forma: cápsula com trilho escuro, brilho em cima e marcas a cada 10 %.

### Não copiar

| O quê | Por quê |
|---|---|
| Molduras, faixas de couro, losangos, rebites, madeira, grão | Pesado: recusado em 31/10 |
| Fonte pixel do jogo | Ilegível no celular e com letra grande; e é arte do jogo |
| Sprites de interface, molduras e ícones de interface do jogo | Licença: só estilo e cores. Todo sinal é CSS ou SVG desenhado por nós |
| Rótulo marrom claro do balão do jogo | 2,5:1, abaixo do mínimo |
| Informação só ao passar o mouse | No celular não existe |

### O celular manda
- Texto ≥ **4,5:1** e bordas de controles ≥ **3:1**, nos dois temas.
- Alvos de **44 px**. O × vermelho tem 28 px de desenho dentro do alvo de 44 px de hoje.
- Quantidades grandes em âmbar à direita, nomes em negrito: nada disso muda.
- **Letra grande** e o tamanho de letra do celular continuam funcionando (tudo em `rem`).
- **360 px sem rolagem lateral**. Temas claro e escuro.

---

## 4. Tokens

A base é a de hoje (`src/css/tokens.css`, que desde 01/11/2026 guarda também a paleta do balão, e o bloco do balão em `src/css/recipes.css`). Entram poucos tokens novos; três cores do balão escurecem um tom.

| Token | Escuro | Claro | Uso | Diferença para hoje |
|---|---|---|---|---|
| `--ok` | `#46c42a` | `#46c42a` | check verde (sempre sobre espaço escuro) | **novo** (hoje o marcado é `--moss` cheio) |
| `--slot-d` | `#1c1a22` | `#1c1a22` | fundo do espaço do ícone e da caixinha | **novo**; hoje o espaço usa `--bg-2` (`#161d23` / `#e3d3b0`) |
| `--slot-d-edge` | `#4a4757` | `#4a4757` | aro do espaço | hoje `--frame-soft` |
| `--stack` / `--stack-edge` | `#f2cb4c` / `#2a1606` | iguais | número no canto do ícone | igual (já está em `tokens.css`, paleta do jogo) |
| `--hud` / `--hud-edge` / `--hud-track` | `#262a35` / `#4d5263` / `#12151c` | iguais | cápsula da barra (Progresso e energia) | igual (já existe); sobe para `tokens.css` |
| `--prog` (enchimento) | `#5fcf34`, brilho `#b8f08a`, sombra `#2f8f1a` | iguais | Progresso | hoje `--moss` liso com faixas |
| `--close-bg` / `--close-rim` / `--close-ink` | `#8a1512` / `#e0454f` / `#ffe3cf` | iguais | × do aviso de patch | **novo** |
| `--en-txt` | `#6cb8ff` | `#134680` | selo "+20" de energia fora do balão | **novo** |
| `--ins-txt` | `#c58af0` | `#5d2a86` | selo "−3" de insanidade fora do balão | **novo** |
| `--tip-bg` / `--tip-bg-2` | `#c9ae7e` / `#bea171` | `#d8bf8f` / `#ccb07c` | balão da ficha | igual |
| `--tip-lbl` | `#4a3419` | igual | rótulos e nota do balão | **`#634a2c` → `#4a3419`** (contraste) |
| `--en-ink` | `#0d3b6e` | igual | "+20" dentro do balão | **`#134680` → `#0d3b6e`** (contraste) |
| `--ins-ink` | `#4a1f6e` | igual | insanidade dentro do balão | **`#5d2a86` → `#4a1f6e`** (contraste) |
| `--en` / `--en-hi` / `--en-lo` | `#2f86d6` / `#6cb8ff` / `#1b5a9e` | iguais | barra azul de energia | igual |

O balão novo (1.5.0) tem três textos abaixo de 4,5:1 no fundo do degradê, no tema escuro: rótulo 3,35, "+20" 3,85 e insanidade 3,98. Os valores da tabela corrigem isso sem mudar a cor de nada.

**Contraste dos pares que continuam:**

| Par | Escuro | Claro |
|---|---|---|
| `--tip-lbl` sobre `--tip-bg-2` | 4,75 (era 3,35) | 5,60 (era 3,95) |
| `--en-ink` sobre `--tip-bg-2` | 4,56 (era 3,85) | 5,39 |
| `--ins-ink` sobre `--tip-bg-2` | 4,98 (era 3,98) | 5,88 |
| `--tip-ink` `#34200f` sobre `--tip-bg-2` | 6,27 | 7,41 |
| `--en-txt` sobre `--panel` / `--panel-2` | 7,75 / 6,99 | 8,07 / 7,39 |
| `--ins-txt` sobre `--panel` / `--panel-2` | 6,44 / 5,81 | 8,36 / 7,64 |
| `--ok` sobre `--slot-d` (ícone) | 7,53 | 7,53 |
| `--stack` sobre `--slot-d` (com contorno) | 11,0 | 11,0 |
| `--frame` sobre `--slot-d` (borda da caixinha vazia) | 3,58 | 3,42 |
| `--slot-d` sobre `--panel` (o espaço contra o cartão) | 1,05 (o aro e o relevo dão a borda; decorativo) | 14,7 |
| `--prog` sobre `--hud-track` | 9,1 | 9,1 |
| `--close-ink` sobre `--close-bg` | 7,80 | 7,80 |

### Desenho (só CSS e SVG próprios)

| Sinal | Como |
|---|---|
| Check verde | SVG de 9 × 8 px em `data:`, verde `--ok` com sombra `#12380a`, `shape-rendering: crispEdges`, 16 px dentro da caixinha de 24 px |
| Cápsula | `.bar` com `padding: 3px`, `border: 2px solid var(--hud-edge)`, trilho em `::before`, marcas a cada 10 % em `::after` (`repeating-linear-gradient`), enchimento com degradê de 3 faixas |
| × vermelho | `::before` com `inset: 8px` dentro do botão de 44 px: fundo `--close-bg`, aro de 2 px `--close-rim`; o × é o texto creme |
| Raio da energia | SVG próprio de 9 × 11 px, no lugar do PNG da wiki que o balão usa hoje (o raio em `.gk-bolt`, `recipes.css`) |
| Cérebro da insanidade | SVG próprio de 9 × 8 px, roxo |
| Pilha | o `.stack-n` que já existe (texto com contorno de 1 px em 8 direções) |

Nada de sombra com desfoque, nada de animação nova. Custo: cerca de 2 KB de CSS e 1 KB de SVG.

### Fontes (proposta separada, não depende do visual)

| | Hoje | Proposta |
|---|---|---|
| Texto, nomes, números | Alegreya Sans (4 pesos + itálico) | letra do sistema (`system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`) |
| Títulos e marca | Grenze Gotisch | igual (ou Grenze, mais legível em "I/II") |
| Peso (latin, woff2) | **126 KB** | **17 KB** (só a Gotisch) ou **55 KB** (Gotisch + Grenze) |

A letra do sistema é mais nítida em telas pequenas e não precisa de download. Por outro lado, a Alegreya Sans dá ao app um tom "de livro" que combina com o jogo. Por isso é uma decisão do Hugo, à parte.

---

## 5. Inventário de componentes

Só o que muda. O resto (cabeçalho, abas, títulos, cartões, estações, Hoje, botões, campos, seletor de receita, selos META/AGORA, toasts, roda dos Dias, Tecnologias, rodapé, Créditos) **fica como está**.

| Componente | Mudança | Esforço | Risco |
|---|---|---|---|
| Caixinha marcada (Planejador, Hoje, Tecnologias) | quadrado verde cheio → **check verde** num espaço escuro | P | baixo |
| Espaço do ícone | escuro **também no tema claro** | P | médio: muda o tom do tema claro; linha feita (opacidade .5) fica cinza, talvez subir para .6 |
| Linha com "tenho N de M" | **número amarelo** no canto do ícone (N) | P | baixo: só aparece quando há "tenho" |
| Barra de Progresso | lisa → **cápsula verde** com trilho escuro e marcas a cada 10 % | P | baixo |
| Aviso de patch (faixa) | ✕ simples → **× creme em quadrado vermelho** | P | baixo |
| Balão da ficha do item | igual; **3 textos um tom mais escuros**; raio em SVG próprio | P | baixo |
| Lista de Receitas e busca | selo **"+20" azul com raio** nas comidas; **"−3" roxo com cérebro** quando mexem na insanidade | P | baixo: só comidas (dado já existe em `facts.json`) |

---

## 6. Ordem de ataque

| Lote | O que entra | Esforço | O que dá para testar | Pronto quando |
|---|---|---|---|---|
| **1. Sinais no Planejador** | check verde; espaço escuro nos dois temas; pilha amarela no "tenho N"; Progresso em cápsula verde; × vermelho no aviso de patch; texto do balão mais escuro | **P** (meio dia) | protótipo `ui-jogo/planejador.html` (Atual / Novo); matriz de capturas 360/390/1280 × escuro/claro × Letra grande; script de contraste | igual ao protótipo nos dois temas; contraste da tabela da seção 4; nada da seção 3 do `simplificar.md` mudou |
| **2. Energia e insanidade** | raio e cérebro em SVG próprio (sai o PNG da wiki); selo "+20" / "−3" nas comidas da lista de Receitas e da busca | **P** (meio dia) | Receitas filtrada em Comida; busca "sopa", "cerveja"; ficha da Sopa de abóbora e de uma bebida com insanidade | selos legíveis em 360 px com letra grande; nenhum PNG da wiki na interface |
| **3. Letra do texto** (opcional, à parte) | Alegreya Sans → letra do sistema | **P** | matriz de capturas; `scripts/tests/test_app_shell.py` (TypeScale) | só se o Hugo aprovar; fontes ≤ 55 KB |

---

## 7. Riscos

| Risco | Tamanho | Como segurar |
|---|---|---|
| Peso da página | baixo | +2 KB de CSS e +1 KB de SVG; sem imagem nova. A letra do sistema (lote 3) tiraria cerca de 70 a 110 KB de fontes |
| Celular antigo | baixo | sem desfoque, sem animação nova |
| Contraste | baixo | tabela da seção 4; o lote 1 já corrige o balão de hoje |
| Letra grande | baixo | nada muda de tamanho; selos em `rem` |
| Licença de arte | médio se descuidar | só estilo e cores. O raio de hoje é um PNG da wiki: o lote 2 troca por SVG nosso. Nenhum sprite de interface, moldura ou fonte do jogo |
| Voltar a ficar "temático demais" | médio | a regra da decisão de 31/10: um sinal por função, nunca moldura. Se um sinal novo não diz nada que o texto já não diga, ele não entra |

---

## 8. Dúvidas para o Hugo

1. O **número amarelo** no canto do ícone só quando você tem parte do item ("tenho 3 de 10"): faz sentido, ou prefere sem?
2. **Ícones em espaço escuro também no tema claro**, como no jogo: fica bom, ou pesa na tela clara?
3. Trocar a **Alegreya Sans pela letra do celular** no texto (proposta separada, à parte do visual)?

---

## 9. Fontes

- Steam, página do jogo: https://store.steampowered.com/app/4358690/ (lista de capturas via https://store.steampowered.com/api/appdetails?appids=4358690&l=brazilian)
  - Árvore de Tecnologias: https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/4358690/746f158d975b126bdceffb01b3e502174e18def1/ss_746f158d975b126bdceffb01b3e502174e18def1.1920x1080.jpg
  - HUD, roda da semana, barra de atalhos, selo de lugar, aviso de coleta: https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/4358690/d4e05aa7d5ec3e9cd9648dbe2006482a886328de/ss_d4e05aa7d5ec3e9cd9648dbe2006482a886328de.1920x1080.jpg
  - Oficina com barras de progresso: https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/4358690/e6649cbfa91e2297be1c7fb472a2ce35ede14df8/ss_e6649cbfa91e2297be1c7fb472a2ce35ede14df8.1920x1080.jpg
- Gamer Guides, inventário (captura do inventário com o balão "Wheat seed"): https://gamer-guides.com/wiki/graveyard-keeper-2/mechanic/inventory/ (imagem https://gamer-guides.com/wp-content/uploads/2026/09/gk2-wheat-seed-inventory-1024x576.webp)
- Gamer Guides, energia (balões de comida, máximo = 100 − insanidade): https://gamer-guides.com/wiki/graveyard-keeper-2/mechanic/energy/
- All Things How, barra roxa de insanidade: https://allthings.how/graveyard-keeper-2-how-to-remove-the-purple-fatigue-on-your-energy-bar/
- wikily.gg, Sopa de abóbora (lida pelo painel do navegador; o WebFetch recebe 403): https://wikily.gg/graveyard-keeper-2/items/pumpkin-soup
- wikily.gg, calendário de 6 dias: https://wikily.gg/graveyard-keeper-2/calendar
- Resenhas sobre a interface (via busca): https://www.gamespew.com/2026/09/graveyard-keeper-2-review/ , https://www.thexboxhub.com/graveyard-keeper-2-review/
- Google Fonts: https://fonts.google.com/specimen/Grenze , https://fonts.google.com/specimen/Grenze+Gotisch (pesos medidos em 31/10/2026, subconjunto latin)
- No projeto: `docs/projeto/DESIGN.md` §2 (cores já amostradas da Steam), `data/game-texts/gk2_textos.json` (textos oficiais), `data/facts.json` e `data/gk2.json` (números do protótipo)
