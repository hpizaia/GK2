# Arquitetura do Companheiro GK2

Pastas, pipeline de build, telas e módulos, limites do artifact e camadas de nomes. O detalhe técnico da interface (o contrato de cada módulo, o manifesto e a montagem) está em [`scripts/README-build.md`](../scripts/README-build.md), seções "The page sources" e "Adding a module".

## Pastas

| pasta / arquivo | o que tem | git |
|---|---|---|
| `src/` | Código da página: `index.html` (modelo), `css/`, `js/` (módulos `GK.*`), `manifest.json` (ordem de montagem) | sim |
| `data/` | Dados de entrada e saída do build: `items.en.json`, `recipes.en.json`, camadas `names*.pt-BR.json`, `gk2.json`/`gk2.min.json`, `techs.json`, `sprite.json`/`sprite.png`, `changelog.json`, relatórios `report-*.md`, READMEs | sim |
| `data/game-texts/` | Texto oficial do jogo: `gk2_textos.json` (en/pt) e `RELATORIO-exportacao.md` | sim. Os 11 idiomas, os CSVs e `_resumo.json` ficam fora |
| `data/raw/` | Cache da API do wikily, props do calculador, pesquisa de localização (`l10n/`) | não (19 MB, regenerável) |
| `data/icons/` | Um PNG por item, estação ou tecnologia | não (regenerável, vira o sprite) |
| `scripts/` | Pipeline Python (só biblioteca padrão) e testes. Tabela em [`scripts/README.md`](../scripts/README.md) | sim |
| `scripts/fixtures/` | Dados pequenos para o `test_build.py` | sim |
| `tools/exportar-textos/` | Exportador dos textos do jogo (Windows) e `juntar_nomes.py` | sim |
| `prototype/index.html` | Página de desenvolvimento (com esqueleto HTML), gerada | sim |
| `dist/index.html` | A página do artifact (sem esqueleto), gerada. `dist/preview.html` é a mesma coisa com esqueleto, para ver localmente | sim |
| `docs/` | Estes documentos, as imagens do README (`docs/media/`) | sim |
| `docs/projeto/` | Documentos de projeto: [`SPEC.md`](projeto/SPEC.md) (especificação), [`DESIGN.md`](projeto/DESIGN.md) (design), [`BACKLOG.md`](projeto/BACKLOG.md) (pendências), [`AUDITORIA.md`](projeto/AUDITORIA.md) (auditoria da v1.1). Parte do conteúdo descreve a versão 1.2 | sim |
| `site/` | Página de apresentação do projeto (outro Claude Artifact), ver `site/README.md` | sim |
| `.github/` | Modelos de issue (`ISSUE_TEMPLATE/`) | sim |
| `historico/` | Transcrições e arquivos de sessões passadas, só no disco local | não (está no `.gitignore`; o histórico fica no repositório privado `hpizaia/GK2-historico`) |
| `VERSION`, `CHANGELOG.md` | Versão atual. O changelog é gerado a partir de `data/changelog.json` | sim |
| `.claude/launch.json` | Servidores locais `prototype` (porta 8765) e `dist` (porta 8766) | sim |
| `tradução windows/` | Sobra da cópia do Windows: a `.venv` e um link de compatibilidade para `data/game-texts/gk2_textos.json` | não |

## Pipeline

```
 wikily API ──fetch_dataset.py──► data/raw/api-*-all.json ─┐
 calculador (navegador) ────────► data/raw/calculator-props.json
                                                            ▼
                                   build_dataset.py ──► data/items.en.json
                                                        data/recipes.en.json
                                                            │
 jogo (Windows) ─exportar_textos─► data/game-texts/gk2_textos.json
                                                │           │
 GK1 wiki + mod GK2Thai ─build_names.py─► data/names.pt-BR.json (GK1 + máquina + gameKey)
                                                │           │
                                juntar_nomes.py ▼           │
                        data/names.official.pt-BR.json      │
                        data/names.machine.pt-BR.json       │
                                                │           │
                                                ▼           ▼
                                 build.py ──► data/gk2.json, gk2.min.json, report-*.md
                                    │  ▲
                                    │  └─ data/techs.json ◄── build_techs.py ◄── gk2.json, api-technologies, nomes, gk2_textos
                                    │
                 fetch_icons.py ◄───┘ (gk2.json, techs.json) ──► data/icons/ ──make_sprite.py──► data/sprite.json
                                    │
 src/ + VERSION + changelog.json + sprite.json + techs.json
                                    ▼
                                 build.py ──► prototype/index.html, dist/index.html, dist/preview.html, CHANGELOG.md
                                                                     │
                                                         Claude Artifact (mesma URL)
```

Propriedades do `build.py`: idempotente (só regrava arquivos cujo conteúdo mudou), determinístico (itens ordenados por id) e bloqueante (com erro grave não grava `gk2.json` nem injeta nada). Os dados vão embutidos na página num `<script type="application/json">`, com `<` escapado. Não há fetch em tempo de execução: a página funciona offline.

## Telas e módulos

Cada arquivo de `src/js/` é um módulo `GK.*` que começa com um comentário dizendo o que ele possui e o que expõe. A ordem de montagem está em `src/manifest.json` (`core.js` primeiro, `app.js` por último). Contrato e exemplo: [`scripts/README-build.md`](../scripts/README-build.md#adding-a-module-the-contract-for-parallel-work).

| tela / função | módulos | o que fazem |
|---|---|---|
| Planejador (`#plan`) | `ui/search.js`, `ui/goals.js`, `ui/summary.js`, `ui/checklist.js` | Busca (combobox), metas com −/+ (segurar repete), matérias-primas e etapas por estação ("tenho N de M", grupos, escolha de receita, edição de nomes), progresso, vantagens, copiar e exportar |
| Tecnologias que faltam | `ui/techneeds.js` (+ `tech.js`) | Painel no Planejador (`slot: "planner-extra"`): tecnologias que faltam para o plano, soma de pontos por cor |
| Receitas (`#recipes`) | `ui/recipes.js` | Lista com busca e filtros; detalhe do item, "Usado em", adicionar às metas, escolher receita |
| Tecnologias (`#tech`) | `ui/tech.js` (+ `tech.js`) | Árvore por ramo, busca, "Já pesquisei", detalhe da tecnologia |
| Histórico (`#changelog`) | `ui/changelog.js` | Tela só de rota (sem aba), a partir de `data/changelog.json` |
| Créditos (`#credits`) | `ui/credits.js` | Tela só de rota (sem aba), ligada no rodapé: projeto de fã, créditos ao estúdio e ao wiki, feito com IA, sem fins lucrativos |
| Cabeçalho e rodapé | `ui/header.js`, `ui/footer.js`, `ui/toast.js` | Abas, tema, idioma; chip de sincronização, versão, créditos; avisos rápidos |
| Tema | `theme.js` | `data-theme` claro, escuro ou automático |
| Sincronização | `sync.js` (+ `store.js`) | Documento privado da conta, mesclagem entre aparelhos, armazenamento local por conta |
| Base | `core.js`, `util.js`, `i18n.js`, `data.js`, `store.js`, `calc.js`, `tech.js`, `router.js`, `ui/fmt.js`, `app.js` | Namespace e registro de painéis, dicionários, carga dos dados, estado, cálculo do plano, árvore de tecnologias, rotas, marcação compartilhada, boot |

`ui/soon.js` é o marcador "em breve" para uma aba futura (nenhuma o usa hoje). Os módulos puros (`data`, `calc`, `store`, `sync`, `ui/fmt`) têm testes em `scripts/test_calc.mjs`; `tech.js` e a sintaxe de todos os módulos, em `scripts/test_build.py`.

## Limites do Claude Artifact

A página publicada é um único HTML hospedado como Claude Artifact, compartilhado por link (qualquer pessoa com o link abre).

- **CSP sem imagens externas.** Imagens remotas (o CDN do wikily) são bloqueadas. Todos os ícones vão num **sprite embutido** (`data:image/png;base64`, células de 32 px, ~760 KB), e o build zera as URLs remotas no modo artifact. Sem sprite, a página mostra um quadrinho com a letra do item.
- **Sem esqueleto.** O artifact envolve a página no próprio documento, então `dist/index.html` sai sem doctype, `<html>`, `<head>`, `<body>`, charset ou viewport, e começa no `<title>`. O `prototype/index.html` e o `dist/preview.html` mantêm o esqueleto para uso local.
- **Tudo inline.** CSS e JS ficam embutidos. Scripts externos só de CDNs permitidos e com versão fixa. Hoje não há nenhum: é JavaScript puro.
- **Sincronização por conta.** A página declara as capacidades **`db`** e **`user`**. Cada pessoa tem um documento privado `data/users/<id do usuário>/state` (metas, escolhas de receita e de grupo, "tenho", marcações, nomes editados, pesquisadas, vantagens). O `localStorage` é a primeira fonte (abre na hora e funciona offline) e é separado por conta. Se só um lado mudou desde a última versão comum, ele vence; se os dois mudaram, o `GK.store.mergeSynced` mescla campo a campo. Campos que a versão não conhece são preservados. Detalhes no comentário de `src/js/sync.js` e no [`docs/projeto/SPEC.md`](projeto/SPEC.md). Sem as capacidades, a página funciona "só neste aparelho". Ao republicar, não mude as capacidades.
- **Tamanho.** O limite é 16 MB. Hoje a página tem ~2 MB (o sprite em base64 é quase metade).
- **Compartilhamento.** O artifact está como "qualquer pessoa com o link" desde 31/10/2026; os dados são usados como conteúdo de fã, com crédito, e o pedido de autorização ao wikily está em andamento (`docs/dados.md`).

## Nomes e tradução

- Toda string da interface vem de um dicionário `i18n[lang][chave]`. Nomes de item, estação, categoria e tecnologia são objetos `{pt, en}`. A busca casa nos dois idiomas, sem acento.
- Os arquivos de nomes usam como chave o **texto inglês exato** do wiki. O build aplica as camadas e o melhor nível vence: **oficial (jogo) > derivado / GK1 (likely) > guess > máquina**. Cada nome leva o campo `tr` com o nível que venceu, e a interface marca o que não é oficial.
- A ponte entre o wiki e o jogo é a **`gameKey`** (chave de localização do jogo, por exemplo `nails_bronze`). Ela vem do `names.pt-BR.json` e é usada pelo `juntar_nomes.py`.
- Para acrescentar um idioma: um dicionário novo na interface e um `--lang campo=arquivo` no build. Ver "Adding a language" em `scripts/README-build.md`. A tabela `gk2_textos_todos.json`, fora do git, já tem os 11 idiomas do jogo.
