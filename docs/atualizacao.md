# Roteiro: o jogo recebeu um patch

Passo a passo para atualizar dados, nomes, ícones e a página quando sai uma versão nova do Graveyard Keeper 2. Os comandos rodam no Mac, na raiz do projeto, com `python3 -I`. O passo 2 roda no Windows com o jogo. A pasta tem espaços, então use sempre aspas.

```sh
cd GK2
git status                     # comece com a árvore limpa: fica fácil ver o que o patch mudou
```

Dependências entre os passos: `build_techs.py` lê o `gk2.json`, e o `build.py` lê o `techs.json` (nomes das tecnologias nas receitas, árvore na página). Os ícones saem do `gk2.json` e do `techs.json`. Por isso o build roda duas vezes: só dados no passo 4 e completo no passo 6.

## 1. Atualizar os dados do wikily

Primeiro confira se o wiki já foi atualizado: a página do wiki diz a versão do jogo que descreve. Sem isso não adianta continuar.

```sh
for s in recipes items buildings crafting-stations technologies alchemy-formulas; do
  python3 -I scripts/fetch_dataset.py "$s" data/raw || break
done
python3 -I scripts/build_dataset.py "$PWD"
git diff --stat data/items.en.json data/recipes.en.json     # o que mudou
```

- O `fetch_dataset.py` grava `data/raw/api-<slug>-offsetNNNN.json` e `api-<slug>-all.json` (fora do git). O `build_dataset.py` só lê os `-all.json`.
- O `build_dataset.py` imprime contagens e listas de problemas (`dangling`, `unmatched calc`, `build variants unresolved`). Compare com a versão anterior: o normal é tudo vazio ou quase.
- **Calculador (opcional).** `data/raw/calculator-props.json` só define `calculator_default`. Receitas novas ficam com `false` até ele ser recapturado. Para recapturar: abra `https://wikily.gg/graveyard-keeper-2/crafting-calculator` no navegador do Claude (ele passa pelo Cloudflare), extraia as props do componente `CraftingCalculatorIsland` (`craftables`, `graph`, `meta`, `stationIcons`) do payload `self.__next_f` e salve em `data/raw/calculator-props.json`. Se o resultado vier embrulhado, o script de uso único está no histórico: `git show 4639d65:scripts/unwrap_browser_dump.py`.
- **Itens novos.** Se o patch trouxe itens, regenere a camada de reserva para eles entrarem na lista de nomes:
  ```sh
  python3 -I scripts/build_names.py data      # data/names.pt-BR.json (GK1 + máquina + gameKey); imprime MISSING
  ```
  O `gameKey` vem do CSV do mod tailandês (jogo 1.0024), então itens novos chegam **sem** `gameKey` e não são ligados no passo 3. Veja a dica no fim do passo 3.

## 2. Exportar os textos do jogo (Windows)

No PC com o jogo atualizado pela Steam. É só leitura: nada é gravado na pasta do jogo. O passo a passo para leigos está em `tools/exportar-textos/LEIA-ME.md`.

**Opção A, a que rodou na 1.011** (exige UnityPy; grava também os 11 idiomas, a versão do jogo e `_resumo.json`). Na pasta de trabalho que já tem a `.venv`:

```bat
cd %USERPROFILE%\Documents\GK2-textos
rem copie para cá tools\exportar-textos\exportar_textos_unitypy.py
.venv\Scripts\python.exe -I exportar_textos_unitypy.py
rem sem .venv:  py -m venv .venv  e  .venv\Scripts\python.exe -m pip install UnityPy==1.25.4
```

**Opção B, a amigável:** copie a pasta `tools\exportar-textos\` inteira e dê dois cliques em `exportar_textos.bat`. Ela grava `gk2_textos.json`, os CSVs e `gk2_exportacao_log.txt`.

Traga de volta para o Mac, em `data/game-texts/`: `gk2_textos.json` (obrigatório, vai para o git), mais `gk2_textos_todos.json`, os CSVs e `_resumo.json` (ficam fora do git, pelo `.gitignore`). Se a sessão no Windows escrever um relatório novo, substitua `data/game-texts/RELATORIO-exportacao.md`.

Conferências rápidas: a contagem de chaves (9.474 na 1.011) e a versão do jogo no `_resumo.json` (`versao_jogo`).

## 3. Juntar os nomes oficiais

```sh
python3 -I tools/exportar-textos/juntar_nomes.py --atualizar
git diff --stat data/names.official.pt-BR.json
```

- **Use sempre `--atualizar`.** Ele parte do `names.official.pt-BR.json` atual, troca `pt`/`en_game` pelo texto novo da mesma `gameKey`, mantém as 32 entradas ligadas à mão (zonas, perks, `matched_by`) e acrescenta as `gameKey` novas do `names.pt-BR.json`. Sem o flag, o arquivo é refeito só pelas 972 `gameKey` e perde as outras 32.
- Leia a saída: "pt alterado" (o jogo mudou a tradução), "gameKey sem texto" (chave que sumiu; a entrada fica como estava) e "conferir à mão" (4 nomes com ícone no meio do texto, como "Poção Tóxica de `<sprite>`").
- **Item novo sem gameKey:** procure a chave pelo texto inglês e acrescente a entrada à mão no `names.official.pt-BR.json`, no mesmo formato, com `"matched_by": "en-text"`:
  ```sh
  python3 -I -c 'import json,sys; t=json.load(open("data/game-texts/gk2_textos.json")); q=sys.argv[1].lower(); [print(k, v) for k,v in t.items() if q in (v["en"] or "").lower()]' "Nome em inglês"
  ```

## 4. Dados provisórios e ícones

```sh
python3 -I scripts/build.py --no-src        # data/gk2.json etc., sem a página
python3 -I scripts/fetch_icons.py           # data/icons/<id>.png (só baixa o que falta)
```

O `build.py --no-src` termina com exit 1 se houver erro grave. Nesse caso leia `data/report-build.md` antes de seguir.

## 5. Tecnologias (e os ícones delas)

```sh
python3 -I scripts/build_techs.py           # data/techs.json + relatório de validação (exit 1 = erro)
python3 -I scripts/fetch_icons.py --techs   # ícones próprios da árvore: tech__*, tp__*, branch__*
python3 -I scripts/make_sprite.py           # data/sprite.json + data/sprite.png
python3 -I scripts/test_techs.py
```

O `build_techs.py` lê o `data/gk2.json` (por isso vem depois do passo 4) e a tabela do jogo em `data/game-texts/gk2_textos.json` (outro caminho: `--game-text <arquivo>`). Ele termina com exit 1 se a árvore tiver erro (pai inexistente, ciclo, custo inválido). Para só conferir, sem gravar: `python3 -I scripts/build_techs.py --check`.

## 6. Build completo e testes

```sh
python3 -I scripts/build.py                 # gk2.json, relatórios, prototype/, dist/, CHANGELOG.md
python3 -I scripts/test_build.py
python3 -I scripts/test_techs.py            # de novo: confere que techs.json não ficou desatualizado
node scripts/test_calc.mjs                  # cálculo, armazenamento e sincronização sobre os dados novos
```

- `data/report-build.md`: tem que dar **0 erros**. Compare os avisos com a versão anterior (hoje 206, quase todos `orphan`).
- `data/report-l10n.md`: lista o que ainda está como máquina ou sem tradução, do mais usado para o menos usado.
- Para ver a página: no Claude, o servidor `dist` do `.claude/launch.json` (`http://127.0.0.1:8766/preview.html`), ou abra `dist/preview.html`.

## 7. Versão e histórico

1. Aumente `VERSION` (por exemplo `1.2.0` → `1.2.1` para só dados, `1.3.0` para funcionalidade).
2. Acrescente a entrada no **topo** de `data/changelog.json`, com `"date": null` e frases curtas que o jogador entenda, em pt e en:
   ```json
   {"version": "1.2.1", "date": null,
    "pt": ["Dados do jogo 1.0xx"], "en": ["Game data 1.0xx"]}
   ```
   Confira se o JSON ficou válido: `python3 -I -c "import json; json.load(open('data/changelog.json'))"`.
3. Feche a versão:
   ```sh
   python3 -I scripts/build.py --release       # data a entrada do topo; recusa se VERSION e changelog divergirem
   python3 -I scripts/test_build.py && node scripts/test_calc.mjs
   ```

O `CHANGELOG.md` é gerado: não edite à mão.

## 8. Publicar e versionar

1. **Artifact:** peça ao Claude para republicar `dist/index.html` **no mesmo artifact** (https://claude.ai/artifact/8hp57ZZTFoH6GyDQUdHZAn), sem criar outro. Se for outra sessão, ele acha a URL com a listagem de artifacts e lê a versão publicada antes. Ao republicar, ele não passa `capabilities`, para manter as que a página já tem (`db` e `user`, usadas na sincronização por conta). Abra a página publicada e confira a versão no rodapé.
2. **Git:**
   ```sh
   git status
   git add -A
   git status --short   # confira: historico/ e os dumps do jogo não devem aparecer
   git commit -m "Companheiro GK2 v1.2.1: dados do jogo 1.0xx"
   git push
   ```
   O `.gitignore` mantém fora do git `data/raw/`, `data/icons/`, o dump completo do jogo e as `.venv`. Se o push recusar por falta de credencial: `gh auth login` (ou `gh auth setup-git`), depois `git push` de novo. Confira antes `git config user.email`: os commits devem sair com o e-mail noreply da conta do GitHub usada no repositório (configurado localmente com `git config --local user.email`).
3. **Histórico da sessão:** peça ao Claude para exportar a transcrição da sessão e guarde em `historico/` (por exemplo `historico/sessao-AAAA-MM-DD-<assunto>.zip`), com uma linha nova na tabela do `historico/README.md`. A pasta `historico/` está no `.gitignore` do repositório público; o histórico fica no repositório privado `hpizaia/GK2-historico`.
