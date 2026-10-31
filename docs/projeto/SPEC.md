> Documento de projeto. Parte do conteúdo descreve a versão 1.2;
> o estado atual está no [README](../../README.pt-BR.md) e no [CHANGELOG](../../CHANGELOG.md).

# Companheiro GK2 — Planejador de Crafting (spec 1.2)

Esta é a especificação do que existe na versão 1.2.0. A v1 original (só o Planejador, protótipo em arquivo único) está no histórico do git. Pendências: `BACKLOG.md`.

## Objetivo
Página única (Claude Artifact, mobile-first) onde o jogador de Graveyard Keeper 2 diz o que quer fabricar e vê
**todos os ingredientes** necessários, agregados, para se programar antes de jogar. Também serve de consulta:
todas as receitas do jogo e a árvore de tecnologias. Interface bilíngue: **pt-BR (padrão)** e **inglês**. Nomes
de itens iguais aos do jogo no idioma escolhido.

## Idiomas (i18n)
- Seletor PT / EN no cabeçalho; escolha salva no estado. Padrão: pt-BR (ou inglês se `navigator.language`
  começar com "en").
- Toda string da interface vem do dicionário. Cada módulo traz as suas com `GK.i18n.add({pt, en})` no topo do
  próprio arquivo. Plurais por chave `.one` / `.other`.
- Nomes de itens, estações, categorias e tecnologias são objetos `{pt, en}`. A busca casa nos dois idiomas, sem
  acento, independentemente do idioma exibido.
- Nomes em pt vêm em camadas: **oficial (texto do jogo) > derivado / GK1 > máquina**. O que não é oficial leva o
  selo "não oficial". O usuário pode editar qualquer nome (selo "editado") e exportar as edições como JSON.
- Terceiro idioma: um dicionário novo em cada módulo + um campo nos dados (ver "Adding a language" em
  `scripts/README-build.md`).

## Arquitetura
- Fonte em `src/`: `index.html` (modelo), `css/` (por assunto), `js/` (um módulo `GK.*` por arquivo) e
  `manifest.json` (ordem de montagem). `scripts/build.py` junta tudo num HTML único com os dados embutidos
  (`<script type="application/json">`), sem fetch em tempo de execução: funciona offline.
- Módulos puros e testáveis: `GK.data` (carga e normalização), `GK.calc` (expansão e agregação), `GK.tech`
  (árvore de tecnologias), `GK.store` (estado único serializável, com versão de schema e migrações). Telas e
  painéis em `GK.ui.*`. `GK.router` (hash `#plan`, `#recipes`, `#tech`, `#changelog`), `GK.theme`, `GK.sync`.
- Uma tela nova é um módulo que chama `GK.router.register` e `GK.app.registerPanel`, sem mexer nos outros.
  Contrato em `scripts/README-build.md` ("Adding a module"). Lista de telas e módulos em `docs/arquitetura.md`.
- Testes: `scripts/test_build.py` (build e módulos), `scripts/test_techs.py` (árvore), `scripts/test_calc.mjs`
  (cálculo, armazenamento e sincronização, no node).

## Telas

### Planejador (`#plan`)
1. **Buscar** um item pelo nome (pt ou en, sem acento, prefixo de palavra, fuzzy leve). Combobox acessível, com
   a contagem de resultados anunciada. Itens ocultos (fora da wiki, inobtíveis, não-itens) só sob pedido.
2. **Metas** com quantidade (−/+ e campo numérico; segurar −/+ repete). Várias metas ao mesmo tempo. Lista de
   exemplo na primeira visita.
3. **Resumo:**
   - **Matérias-primas** totais (folhas da árvore), com "Já tenho" ou **"tenho N de M"** (desconta antes do
     arredondamento) e, para itens de grupo ("Brema ou carpa"), a escolha do item usado.
   - **Etapas por estação**, com execuções, rendimento e sobra. Ordem garantida: nenhuma estação depende de
     outra mais abaixo; se uma estação volta, ganha um segundo cartão ("de novo").
   - Item com várias receitas: seletor com os ingredientes e a qualidade (prata/ouro). A escolha é global por
     item e fica lembrada. Receitas de qualidade consomem o ingrediente com a qualidade certa.
   - Receitas circulares ou sem ganho viram matéria-prima, com aviso.
4. **Progresso:** marcar coletado / feito, barra de progresso, limpar marcações, copiar a lista como texto,
   exportar nomes editados. **Vantagens** (perks) que mudam quantidades no plano, ligáveis uma a uma.
5. **Tecnologias que faltam:** as tecnologias ainda não pesquisadas para fabricar tudo do plano (estações
   incluídas), em ordem de pesquisa, com a soma de pontos vermelhos, verdes e azuis, "Já pesquisei" na própria
   linha e as missões / vantagens que o plano também pede. Some quando não falta nada.

### Receitas (`#recipes`)
- Lista de todos os itens com busca, filtros por categoria e estação (com contagem), itens ocultos sob pedido,
  60 por página.
- Detalhe: cada receita (ingredientes, estação e alternativas, extensão, tecnologia / missão / vantagem,
  maestria, tempo e energia, runas, subprodutos), membros de grupo, como obter, "Usado em", adicionar às metas,
  escolher a receita que o Planejador usa.

### Tecnologias (`#tech`)
- As 226 tecnologias nos 6 ramos, com contagem de pesquisadas por ramo, busca (também pelo que desbloqueiam),
  custo por cor, selos (reputação, oculta, dada pela história).
- "Já pesquisei": marcar uma conta as anteriores como pesquisadas. Detalhe com pré-requisitos (e "marcar
  pré-requisitos"), o que desbloqueia, o que vem depois e notas. "Limpar pesquisadas" com confirmação.

### Histórico de atualizações (`#changelog`)
- Lista de versões a partir de `data/changelog.json`. Link no rodapé, ao lado da versão.

## Estado e sincronização
- Estado único: `goals`, `choice`, `have`, `done`, `overrides`, `researched`, `groupChoice`, `perks`, mais
  `lang`, `theme`, `showHidden`, `example`, `updatedAt`, `syncBase`.
- `localStorage` é a primeira fonte (abre na hora, funciona offline), separado por conta. O plano anônimo vai
  uma vez para a primeira conta que abrir a página naquele navegador e depois é apagado.
- Com as capacidades `db` e `user` do artifact, cada pessoa tem um documento privado
  `data/users/<id>/state`. Ao receber a cópia da conta:
  - só a conta mudou: a conta vence; só este aparelho mudou: envia a cópia local;
  - os dois mudaram desde a última versão comum: mescla campo a campo (união dos mapas; metas, receitas e nomes
    editados ficam com o aparelho, marcações, "tenho", pesquisadas, vantagens e grupos com a conta);
  - campos que esta versão não conhece (escritos por uma página mais nova) são preservados.
- Uma gravação por vez, 1,5 s de espera, nova tentativa em caso de falha, ouvinte recriado se cair.
- Chip de status no rodapé: "Sincronizado há N min", "Sincronizando…", "Só neste aparelho", "Não sincronizado".
- Sem as capacidades (ou sem login), tudo funciona "só neste aparelho".

## Dados
- Receitas e itens do wikily.gg (jogo 1.010); nomes oficiais do jogo 1.011; tecnologias em `data/techs.json`.
  Fontes, licença e lacunas em `docs/dados.md`; schema em `scripts/README-build.md`.
- Ícones num sprite embutido (o CSP do artifact bloqueia imagens externas). Sem sprite, quadrinho com a letra.
- Crédito ao wikily e à Lazy Bear Games no rodapé.

## UX / visual
- Mobile-first (360 px+), margem de 16 px, sem scroll horizontal; duas colunas a partir de 900 px.
- Tema escuro (noite), claro (pergaminho) ou automático. Tokens CSS em `:root` (`src/css/tokens.css`,
  `DESIGN.md` §2), com contraste ≥ 4,5:1 nos textos.
- Alvos de toque ≥ 44 px; nada só no hover; foco visível; respeita `prefers-reduced-motion`.
- JavaScript puro, sem framework nem script externo.
- Página de cerca de 2 MB (o sprite ocupa quase metade; limite do artifact: 16 MB).

## Fora de escopo (por enquanto)
- Preços e venda, mapa, NPCs, calendário de dias da semana, missões como tela própria.
- Ler o save do jogo ou o inventário.
- Alquimia combinatória completa (hoje: uma mistura de exemplo por fórmula).
- Bônus de vantagens além do que está escrito nas notas da wiki; rendimento do plantio.
- Publicação aberta (depende de autorização do wikily).
- Outros idiomas além de pt-BR e inglês.
