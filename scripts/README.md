# scripts/: o que cada um faz

Tudo é Python 3 só com a biblioteca padrão (Pillow é opcional no `make_sprite.py`), menos o `test_calc.mjs`, que roda no Node. Rode sempre da raiz do projeto, com `python3 -I`, e ponha os caminhos entre aspas, porque a pasta tem espaços. O roteiro completo de atualização (patch do jogo) está em [`docs/atualizacao.md`](../docs/atualizacao.md). Opções e schema do build estão em [`README-build.md`](README-build.md) (em inglês; o nome fica assim porque o código em `src/` e `scripts/` aponta para ele).

## Pipeline principal (o que roda a cada versão)

| script | o que faz | quando rodar | entradas → saídas |
|---|---|---|---|
| `fetch_dataset.py <slug> data/raw` | Pagina a API pública de datasets do wikily (120 linhas por página, 1 req/s, User-Agent de navegador) e guarda cada página e o conjunto | Patch do jogo / wiki atualizado. Uma vez por slug: `recipes`, `items`, `buildings`, `crafting-stations`, `technologies`, `alchemy-formulas` | API wikily → `data/raw/api-<slug>-offsetNNNN.json` + `data/raw/api-<slug>-all.json` |
| `build_dataset.py "<raiz>"` | Normaliza os dumps do wikily em itens e receitas (kinds, grupos, variantes de qualidade, construções por área, alquimia, plantio; marca `calculator_default`) | Depois do `fetch_dataset.py` | `data/raw/api-*-all.json` + `data/raw/calculator-props.json` → `data/items.en.json`, `data/recipes.en.json` |
| `build.py` | Junta itens, receitas e as camadas de nomes em `gk2.json`, valida, escreve relatórios, monta a página a partir de `src/` e regenera `CHANGELOG.md`. `--release` data a versão | Sempre que mudar dado, nome, `src/`, `VERSION` ou changelog | `data/items.en.json`, `data/recipes.en.json`, `data/names*.pt-BR.json`, `data/sprite.json`, `src/`, `VERSION`, `data/changelog.json` → `data/gk2.json`, `data/report-build.md`, `data/report-l10n.md`, `prototype/index.html`, `dist/index.html`, `dist/preview.html`, `CHANGELOG.md` |
| `build_facts.py` | Extrai de `data/raw/api-items-all.json` as fontes (quem vende, pesca), energia, efeito e pilha de cada item para `data/facts.json`; o `build.py` aplica isso ao `gk2.json` | Quando `data/raw/` for atualizado, antes do `build.py` | `data/raw/api-items-all.json` → `data/facts.json` |
| `validate.py [data/gk2.json]` | Confere um `gk2.json` (refs soltas, quantidades, ciclos, padrões). O `build.py` já o chama | Avulso, para ver o relatório completo (`--json`, `--quiet`) | `data/gk2.json` → relatório no terminal (exit 1 se houver erro grave) |
| `build_techs.py` | Monta a árvore de tecnologias pt/EN (custos, pais/filhos, desbloqueios, notas, ícones) e valida (DAG etc.). `--check` só valida | Depois do `build.py` (lê o `gk2.json`) ou quando mudar nome | `data/raw/api-technologies-all.json`, `data/gk2.json`, as 3 camadas de nomes, `data/game-texts/gk2_textos.json` (outro caminho: `--game-text`) → `data/techs.json` |
| `fetch_icons.py [--techs]` | Baixa cada URL de ícone distinta (≤ 5 req/s, pula o que já existe). `--techs` inclui os ícones próprios da árvore | Quando aparecem itens ou tecnologias novos | `data/gk2.json` (+ `data/techs.json`) → `data/icons/<id>.png` (ignorado no git) |
| `make_sprite.py` | Empacota os ícones numa folha única (células de 32 px, ícones iguais compartilham célula) | Depois do `fetch_icons.py` | `data/icons/*.png` → `data/sprite.json` (manifesto com o PNG em `data:`) + `data/sprite.png` |

## Testes e release

Antes de cada commit ou publicação basta um comando: `python3 -I scripts/check.py`. Ele roda os 3 testes abaixo e as conferências que nenhum teste faz.

| script | o que faz | quando rodar | entradas → saídas |
|---|---|---|---|
| `check.py [--release]` | Confere versões (`VERSION`, topo do changelog, versão do site), build reprodutível (refaz numa pasta temporária e compara byte a byte), `site/preview.html` e `data/days.json` em dia, os 3 testes (cada um com seu código de saída) e o e-mail do git. Uma linha por conferência (ok / AVISO / FALHA), exit 1 se algo falhou. `--release` exige changelog datado e nenhum teste pulado | Antes de cada commit/publicação | o projeto → só o resultado (não grava nada) |
| `release.py X.Y.Z [--dry-run]` | Prepara a versão até o ponto de pedir OK: `VERSION`, número da versão no site, `site/preview.html`, `build.py --release`, `check.py --release`, arquivo da release e notas numa pasta temporária. Imprime os comandos de commit, push e `gh release` sem rodá-los | Ao fechar uma versão (`docs/atualizacao.md` §7–8) | entrada no topo de `data/changelog.json` → `VERSION`, `site/`, saídas do build + `companheiro-gk2-X.Y.Z.html` e `notas.md` fora do repositório |
| `site_preview.py [--check]` | Regenera `site/preview.html` a partir de `site/index.html` (funções usadas também pelo `check.py` e pelo `release.py`) | Depois de editar `site/index.html` | `site/index.html` → `site/preview.html` |
| `test_build.py` | Testes do `build.py` e do `validate.py` sobre `scripts/fixtures/` (saídas em pasta temporária), mais um teste de fumaça nos dados reais | Antes de cada commit/publicação | `scripts/fixtures/*`, `data/*.en.json` → só o resultado dos testes |
| `test_techs.py` | Testes do `build_techs.py` nos dados reais. Também acusa `data/techs.json` desatualizado. Sem `data/raw/` (fora do git), pula tudo com aviso | Depois de mexer em tecnologias ou nomes | `data/raw/api-technologies-all.json`, `data/gk2.json`, nomes, tabela do jogo → só o resultado dos testes |
| `test_calc.mjs` | Testes do JavaScript da página no node, sem dependências: `GK.data`, `GK.calc` (casos reais, ordem das estações, "tenho N", grupos, vantagens, prata/ouro), `GK.store` (migração, mesclagem), `GK.sync` (versão, campos desconhecidos, ouvinte, nova tentativa, armazenamento por conta) e as chaves de texto (toda chave de `GK.i18n.add` em pt e en). Rodar com `node scripts/test_calc.mjs` | Depois de mexer em `src/js/` ou nos dados, antes de publicar | `src/js/*.js`, dados embutidos em `prototype/index.html` (ou `data/gk2.json`) → só o resultado dos testes |

## Capturas e comparação visual (`scripts/shots/`)

| script | o que faz | quando rodar | entradas → saídas |
|---|---|---|---|
| `shots/compare.py [--ref REF] [--only-capture]` | Abre o app de `REF:dist/preview.html` (padrão `HEAD`) e o `dist/preview.html` atual no Chrome headless, nos mesmos casos (`shots/casos.json`: cada aba e tela principal, pt/en, 390/1280 px, claro/escuro), e compara pixels, HTML e texto visíveis, estado do app, erros de JS e o resumo do `GK.data`. Uma linha por caso, exit 1 se algo mudou. Lento (~30 s): fica fora do `check.py`. Detalhes em [`shots/README.md`](shots/README.md) | Antes e depois de refatorar (depois do build); `--only-capture` para tirar prints | as duas páginas → `.shots/compare/` (ou `.shots/capturas/`), fora do git |

## Camada pt-BR de reserva (GK1 + tradução de máquina)

Estes scripts geraram `data/names.pt-BR.json`, a camada anterior aos textos oficiais do jogo. A camada oficial (`data/names.official.pt-BR.json`) cobre quase tudo, mas esta continua sendo a fonte das `gameKey` usadas pelo `juntar_nomes.py` e o reserva para nomes que o jogo não tem. Só é preciso rodar de novo quando o wikily ganhar nomes novos que precisem de `gameKey`.

| script | o que faz | quando rodar | entradas → saídas |
|---|---|---|---|
| `fetch_gk1_langlinks.py data/raw/l10n` | Baixa os pares interwiki pt-br ↔ en da wiki Fandom do Graveyard Keeper 1 (MediaWiki API, 0,7 s entre chamadas) | Raramente: a wiki do GK1 quase não muda | API Fandom → `data/raw/l10n/gk1_*langlinks_*.json`, `gk1_langlinks_merged.json` |
| `mt_glossary.py` | Não roda sozinho: é o glossário EN → pt-BR do Claude (tabelas `MT`, `CROPS`, `SEEDS`, `QUAL`, `SUPPLY`, `SINS`, `CATS`) importado pelo `build_names.py` | Editar quando quiser corrigir uma tradução de máquina | — |
| `build_names.py data` | Monta `names.pt-BR.json` com chave = nome EN exato: GK1 (`likely`) > glossário (`guess`), com prioridade e `gameKey` | Quando entrar item novo no wikily, antes do `juntar_nomes.py` | `data/items.en.json`, `data/recipes.en.json`, `data/raw/l10n/thai_source_en.csv`, `data/raw/l10n/gk1_langlinks_merged.json` → `data/names.pt-BR.json` |

`data/names.machine.pt-BR.json` (a tradução de máquina completa, com os textos `__obtain`) não tem gerador no repositório. Veja `data/README-machine-l10n.md`.

## Fora de `scripts/`

| script | o que faz | quando rodar | entradas → saídas |
|---|---|---|---|
| `tools/exportar-textos/exportar_textos.py` (+ `.bat`) | No Windows com o jogo: lê `lng_pt-br` e `lng_en` de `resources.assets`, só leitura. Versão amigável, com leitor embutido (UnityPy opcional) | Patch do jogo | jogo instalado → `gk2_textos.json`, CSVs, log (ao lado do script) |
| `tools/exportar-textos/exportar_textos_unitypy.py` | Variante estrita (exige UnityPy) que gerou a exportação 1.011; grava também os 11 idiomas, a versão do jogo e `_resumo.json` | Patch do jogo (alternativa) | jogo instalado → `gk2_textos.json`, `gk2_textos_todos.json`, CSVs, `_resumo.json` |
| `tools/exportar-textos/juntar_nomes.py --atualizar` | Atualiza `names.official.pt-BR.json` com a exportação nova pela `gameKey`, mantém as entradas ligadas à mão e lista o que mudou | Depois de trazer a exportação para `data/game-texts/` | `data/game-texts/gk2_textos.json`, `data/names.pt-BR.json`, `data/names.official.pt-BR.json` → `data/names.official.pt-BR.json` |

## Removidos (estão no histórico do git)

- `collect_en_names.py`: primeiro coletor de nomes EN, substituído pelo `build_names.py`.
- `unwrap_browser_dump.py`: uso único, desembrulhava o resultado salvo do `javascript_tool` do navegador em `data/raw/calculator-props.json`. Recuperar com `git show 4639d65:scripts/unwrap_browser_dump.py` se precisar capturar o calculador de novo (veja `docs/atualizacao.md`).
- `tools/exportar-textos/_teste_join.json`: saída de teste do `juntar_nomes.py` feita com o CSV inglês do mod tailandês.
