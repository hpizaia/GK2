# tools/: ferramentas fora do pipeline principal

| pasta | o que tem | onde roda |
|---|---|---|
| [`exportar-textos/`](exportar-textos/) | Exportador dos textos oficiais do jogo (`exportar_textos.py` + `exportar_textos.bat`, versão amigável; `exportar_textos_unitypy.py`, versão estrita que gerou a exportação 1.011) e `juntar_nomes.py`, que liga esses textos aos nomes do wiki e grava `data/names.official.pt-BR.json` | O exportador roda no **Windows**, no PC com o jogo (só leitura). O `juntar_nomes.py` roda no Mac, na raiz do projeto |

- Passo a passo para quem vai exportar (leigos): [`exportar-textos/LEIA-ME.md`](exportar-textos/LEIA-ME.md).
- Entradas, saídas e quando rodar cada script: seção "Fora de `scripts/`" do [`scripts/README.md`](../scripts/README.md).
- Onde isso entra no roteiro de patch: passos 2 e 3 do [`docs/atualizacao.md`](../docs/atualizacao.md).

As saídas do exportador quando ele roda dentro desta pasta (`gk2_textos*.json`, CSVs, `_resumo.json`, log) ficam fora do git pelo `.gitignore`. A tabela que vai para o git é `data/game-texts/gk2_textos.json`.
