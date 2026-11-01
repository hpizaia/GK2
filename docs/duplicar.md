# Faça a sua cópia do Companheiro GK2

[English](duplicate.md) · **Português**

Passo a passo para ter a sua própria versão: o seu Claude Artifact, um site estático, outro idioma ou o ponto de partida de um planejador para outro jogo. Os passos 1 a 3 já dão uma cópia funcionando; o resto só é preciso quando você quiser dados novos.

Todos os comandos rodam na raiz do projeto. Use `python3 -I` (modo isolado). Ponha entre aspas qualquer caminho com espaço.

## 0. O que você precisa

| Precisa de | Para quê | Obrigatório? |
|---|---|---|
| **Python 3** (só biblioteca padrão) | tudo: build, dados, testes | sim |
| **git** | clonar e ver o que uma atualização de dados mudou | sim |
| **Node** | `scripts/test_calc.mjs` (cálculo, armazenamento, sincronização) | opcional |
| **cwebp** (`brew install webp`) | gerar o sprite dos ícones em WebP sem perda no `make_sprite.py` (ou `--png`, sem ele) | só para refazer o sprite |
| **Pillow** | empacotar o sprite mais rápido no `make_sprite.py` (há reserva só com a biblioteca padrão) | opcional |
| **Windows + Graveyard Keeper 2** (Steam) | exportar os nomes oficiais dos arquivos do seu jogo | opcional |
| **Conta do Claude + [Claude Code](https://claude.com/claude-code)** | publicar como Claude Artifact, com sincronização por conta | opcional |

## 1. Pegue o código

```sh
git clone https://github.com/hpizaia/GK2.git meu-gk2
cd meu-gk2
```

Ou use **Fork** no GitHub e clone o seu fork. O repositório já traz os dados montados (`data/gk2.json`, `data/techs.json`, `data/days.json`) e o sprite dos ícones (`data/sprite.json`), então ainda não é preciso baixar nada.

## 2. Monte e confira

```sh
python3 -I scripts/build.py           # grava prototype/index.html, dist/index.html, dist/preview.html, CHANGELOG.md
python3 -I scripts/test_build.py
python3 -I scripts/test_techs.py
node scripts/test_calc.mjs            # opcional
```

Abra `dist/preview.html` no navegador, ou sirva a página de desenvolvimento:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory prototype   # http://127.0.0.1:8765/
```

O `build.py` é idempotente: rodar de novo com as mesmas entradas imprime `wrote nothing (all outputs up to date)`. Ele sai com `1` se houver erro nos dados (e aí não grava o `gk2.json`) e com `2` em erro de uso ou de arquivo.

## 3. Publique

### Opção A: Claude Artifact (com sincronização por conta)

1. Abra a pasta do projeto no **Claude Code**.
2. Peça: *"Publique o `dist/index.html` como Claude Artifact, declarando as capacidades `db` e `user`."*
   - `db` dá a cada pessoa um documento privado no banco do artifact; `user` diz à página quem está vendo. Juntas, fazem a sincronização. Sem elas a página funciona igual e mostra "Só neste aparelho".
3. O Claude devolve o link do artifact. Artifacts são **privados** por padrão; compartilhe pelo menu da própria página.
4. **Versões seguintes:** peça para *republicar o `dist/index.html` na mesma URL do artifact*, sem passar capacidades (assim a página mantém `db` e `user`). Uma URL nova deixaria para trás os planos salvos de quem já usa.

O `dist/index.html` é feito para isso: não tem o esqueleto `<html>`/`<head>` (o visualizador do Artifact põe o dele), todos os ícones vêm do sprite embutido (o sandbox do Artifact bloqueia imagens externas) e todo o CSS e JS está dentro do arquivo.

### Opção B: qualquer hospedagem estática (sem sincronização)

Copie o `dist/preview.html` para a hospedagem com o nome `index.html`. No **GitHub Pages**, por exemplo:

```sh
mkdir -p public && cp dist/preview.html public/index.html
# depois mande public/index.html para um branch gh-pages, ou publique public/ com um workflow do GitHub Pages
```

O progresso fica só no `localStorage` do navegador. As fontes vêm do Google Fonts; o resto está no arquivo.

## 4. Atualize os dados de receitas (wikily.gg)

Só quando o jogo ou a wiki mudar. Antes, confira se a wiki já descreve a versão nova do jogo. Respeite a wiki: o coletor espera 1 segundo entre pedidos, e os dados são © NX Software (veja [Créditos e direitos](../README.pt-BR.md#créditos-e-direitos)); mantenha a sua cópia sem fins comerciais.

```sh
mkdir -p data/raw/days
for s in recipes items buildings crafting-stations technologies alchemy-formulas quests; do
  python3 -I scripts/fetch_dataset.py "$s" data/raw || break
done
cp data/raw/api-quests-all.json data/raw/days/probe-quests.json   # missões que pedem itens
python3 -I scripts/build_dataset.py "$PWD"
git diff --stat data/items.en.json data/recipes.en.json
```

- As páginas brutas vão para `data/raw/` (fora do git, uns 19 MB).
- O `build_dataset.py` imprime contagens e listas de problemas (`dangling`, `unmatched calc`…). Compare com a vez anterior; o normal é tudo vazio ou quase.
- O `data/raw/calculator-props.json` (qual receita o calculador da wiki prefere) é opcional e fica atrás de um desafio do navegador; veja "Calculador" em [`docs/atualizacao.md`](atualizacao.md).
- Os nomes em pt ficam em três camadas: `data/names.official.pt-BR.json` (do jogo, passo 5), `data/names.manual.pt-BR.json` (escolhidos à mão: nomes de receita, palavras do jogo, correções) e `data/names.machine.pt-BR.json` (reserva de máquina). Item novo sem nome oficial precisa de uma entrada à mão na de máquina. Receita nova aparece em inglês até alguém acrescentá-la (como buscar o nome na wiki em português: "Nomes de receita em português" em [`docs/atualizacao.md`](atualizacao.md)).

## 5. Nomes oficiais do seu próprio jogo (opcional, Windows)

Os nomes em pt-BR e inglês são os do próprio jogo, lidos da sua cópia instalada. Nada na pasta do jogo é alterado.

1. Copie `tools/exportar-textos/` para o PC com o jogo e dê dois cliques em `exportar_textos.bat` (passo a passo para leigos em `tools/exportar-textos/LEIA-ME.md`). O `exportar_textos_unitypy.py`, mais estrito, grava também os 11 idiomas do jogo.
2. Traga o `gk2_textos.json` de volta para `data/game-texts/`.
3. Junte os nomes, mantendo as entradas ligadas à mão:

```sh
python3 -I tools/exportar-textos/juntar_nomes.py --atualizar
git diff --stat data/names.official.pt-BR.json
```

Leia a saída: "pt alterado" (o jogo mudou uma tradução), "gameKey sem texto" (chave que sumiu) e "conferir à mão" (nomes com ícone no meio do texto).

## 6. Fatos do item, ícones, tecnologias e dias

```sh
python3 -I scripts/build_facts.py           # data/facts.json: quem vende, quem compra, estudo, pedidos (do cache do passo 4)
python3 -I scripts/build.py --no-src        # só dados: data/gk2.json e os relatórios
python3 -I scripts/fetch_icons.py           # data/icons/<id>.png, só o que falta (fora do git)
python3 -I scripts/build_techs.py           # data/techs.json (exit 1 se a árvore tiver erro)
python3 -I scripts/fetch_icons.py --techs   # ícones de tecnologias, pontos e ramos
python3 -I scripts/make_sprite.py           # data/sprite.json + data/sprite.png
python3 -I scripts/build_days.py            # data/days.json, a partir dos textos do jogo + a tabela EVENTS do script
python3 -I scripts/test_techs.py
```

- O `build_techs.py` lê o `data/gk2.json`, por isso vem depois do build só de dados.
- Os eventos de cada dia são frases curtas escritas à mão em `scripts/build_days.py` (`EVENTS`), cada uma ligada a um texto oficial do jogo. Para acrescentar ou corrigir, edite `EVENTS` e rode de novo. Detalhes: [`data/README-days.md`](../data/README-days.md).

## 7. Build completo, versão e saída

```sh
python3 -I scripts/build.py
python3 -I scripts/test_build.py && python3 -I scripts/test_techs.py && node scripts/test_calc.mjs
```

| Saída | O que é |
|---|---|
| `dist/index.html` | A página do Artifact (é esta que vai para o Claude) |
| `dist/preview.html` | A mesma página com esqueleto de documento (abrir localmente ou hospedar como `index.html`) |
| `prototype/index.html` | Página de desenvolvimento |
| `data/gk2.json` | O conjunto de dados montado (schema em [`scripts/README-build.md`](../scripts/README-build.md)) |
| `data/report-build.md`, `data/report-l10n.md` | Relatório do build (tem que dar 0 erros) e nomes sem tradução, do mais usado para o menos usado |
| `CHANGELOG.md` | Gerado a partir de `data/changelog.json`. Não edite à mão |

Para lançar uma versão: aumente o `VERSION`, acrescente uma entrada no topo de `data/changelog.json` com `"date": null` e frases curtas em `pt` e `en`, e rode `python3 -I scripts/build.py --release` (ele data a entrada e recusa se `VERSION` e changelog divergirem). Depois republique (passo 3).

## 8. Acrescente um idioma (exemplo: espanhol)

O lado dos dados:

1. Crie `data/names.es.json`, com chave = **texto inglês exato** de cada nome e valores como `{"name": "Espada de hierro", "source": "...", "confidence": "official|likely|guess"}` (o campo do valor pode se chamar `pt`, `name` ou `value`).
2. Monte com `python3 -I scripts/build.py --lang es=data/names.es.json` (separe várias camadas por vírgula). Todo objeto `{pt, en}` ganha um campo `es` (com o inglês de reserva) e o `data/report-l10n.es.md` lista o que falta. Para virar padrão, acrescente em `specs` no `main()` do `build.py`.
3. O jogo vem com 11 idiomas. O exportador UnityPy grava todos em `gk2_textos_todos.json`; ainda não há script que transforme outro idioma num arquivo de nomes, então adapte o `tools/exportar-textos/juntar_nomes.py` (ele liga os nomes da wiki às chaves do jogo pela `gameKey`).

O lado da interface:

4. Acrescente uma entrada em `LANGS` no `src/js/i18n.js` (`{ code: "es", locale: "es", label: "ES", name: "Español" }`).
5. Copie `src/js/i18n/en.js` para `src/js/i18n/es.js`, troque `en:` por `es:` na linha do `GK.i18n.add` e traduza os textos; liste o arquivo no `src/manifest.json`, logo depois do `js/i18n/en.js`. Chave que faltar cai no português.
6. Monte de novo. Detalhes: "Adding a language" em [`scripts/README-build.md`](../scripts/README-build.md#adding-a-language-for-example-spanish).

## 9. Mude o visual

- **Cores, fontes, espaçamento:** `src/css/tokens.css`. O escuro (noite) fica no `:root` puro; o claro (pergaminho) está definido duas vezes, em `@media (prefers-color-scheme: light)` e em `:root[data-theme="light"]`. Mude os dois blocos do claro juntos.
- **Fontes:** `--f-display` e `--f-body` nos tokens; o link do Google Fonts está em `src/index.html`.
- **Nome do app:** `<title>` em `src/index.html` e `app.title*` em `src/js/i18n/pt.js` e `src/js/i18n/en.js`.
- Por que o visual é assim: [`docs/projeto/DESIGN.md`](projeto/DESIGN.md). Monte de novo depois de qualquer mudança em `src/`; nunca edite `dist/` nem `prototype/`.

## 10. Acrescente uma função

Cada função é um módulo próprio (`src/js/ui/<nome>.js`, e opcionalmente `src/css/<nome>.css`), listado em `src/manifest.json`, com os próprios textos (uma seção em `src/js/i18n/pt.js` e `en.js`), a própria rota (`GK.router.register`) e o próprio painel (`GK.app.registerPanel`). O contrato, com exemplo, está em "Adding a module" no [`scripts/README-build.md`](../scripts/README-build.md#adding-a-module-the-contract-for-parallel-work). Foi isso que deixou vários agentes do Claude Code criarem funções em paralelo sem mexer nos arquivos uns dos outros.

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `build.py` sai com 1 | Leia `data/report-build.md`: referência solta ou quantidade inválida. O `gk2.json` bom anterior é mantido |
| Ícones aparecem como quadrinhos com letra | `data/sprite.json` falta ou está velho: rode `fetch_icons.py` (e `--techs`), depois `make_sprite.py`, depois o build |
| `test_techs.py` diz que o `techs.json` está desatualizado | Rode de novo `python3 -I scripts/build_techs.py` |
| O Artifact perdeu o progresso de todo mundo | Foi publicado numa URL nova, ou sem as capacidades `db`/`user`. Republique na URL original |
| O chip do rodapé diz "Só neste aparelho" | Sem login no Claude, ou página publicada sem capacidades, ou cópia estática. É o esperado |
