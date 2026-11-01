# Companheiro GK2 — instruções para o Claude

Planejador de crafting de Graveyard Keeper 2 (pt-BR e inglês): uma página HTML única publicada como
Claude Artifact, mais um site de apresentação. Repositório PÚBLICO `hpizaia/GK2`: tudo que é versionado
qualquer um lê. Dono: Hugo, brasileiro, não programador. Responda em português do Brasil, frases curtas,
sem jargão. Antes de começar, leia "Onde estamos" em `docs/projeto/BACKLOG.md` (é lá que fica o status).
Se existir `CLAUDE.local.md` (privado, fora do git), leia também.

## Regras fixas

1. **Commit sempre com a identidade do projeto** (a global do Mac é de outra conta):
   `git -c user.name="Hugo Pizaia" -c user.email="1241727+hpizaia@users.noreply.github.com" commit -m "..."`
2. **Push só da main para o origin:** `git push origin main` (e tags `v*`). Nunca `--all`, `--mirror` nem
   outra branch. As branches locais `backup-main-pre-rewrite` e `historico` têm o histórico antigo, com
   documentos internos: nunca vão para o `origin`. A trava `scripts/git-hooks/pre-push` recusa isso; num
   clone novo, ative com `git config core.hooksPath scripts/git-hooks`.
3. **Internos nunca no GitHub:** `historico/`, `docs/revisao-ux/`, `CLAUDE.local.md`. Arquivo versionado
   (código, comentário, teste, doc) não aponta para arquivos dentro delas (quem clona não abre).
4. **Nada sai sem pedido do Hugo:** commit, push, release, publicação de artifact, e-mail, post,
   comentário, compartilhamento.
5. **Mudança visual** (layout, cor, espaçamento, texto da interface) só depois de protótipo aprovado
   pelo Hugo. Ele quer o app enxuto: na dúvida, menos coisa na tela.
6. **Não reabra as decisões do Hugo** (lista no fim) sem ele pedir.
7. **Agentes:** use o agente `gk2-worker` (Opus, esforço alto; nunca Fable) e não passe `model` na chamada.
   Agente não commita, não dá push e não publica: isso é da sessão principal, com o ok do Hugo.
8. **Processos:** quem abre `http.server` ou Chrome headless fecha antes de terminar. Nada de
   `until`/`while` esperando em segundo plano. No fim, `pgrep -fl "http.server|remote-debugging-port"`
   volta vazio.
9. **Arquivos gerados não se editam à mão:** `dist/`, `prototype/`, `CHANGELOG.md`, `data/gk2*.json`,
   `data/report-*.md`. Mude `src/` ou `data/` e rode o build.

## Comandos (na raiz; a pasta tem espaços, use aspas nos caminhos)

```sh
python3 -I scripts/check.py            # testes + build reprodutível + versões; tem que passar antes de entregar
python3 -I scripts/check.py --release  # versão mais rígida, antes de publicar
python3 -I scripts/build.py --built AAAA-MM-DD   # build do dia a dia (data: ver "meta.built" abaixo)
python3 -I scripts/test_build.py && python3 -I scripts/test_techs.py && node scripts/test_calc.mjs
```
Ver o app: servidor `dist` do `.claude/launch.json` → http://127.0.0.1:8766/preview.html.
Detalhe de cada script em `scripts/README.md`; opções do build em `scripts/README-build.md`.

## Publicar uma versão (sessão principal, com o ok do Hugo)

1. Entrada no topo de `data/changelog.json` (pt e en, frases para o jogador, `"date": null`).
2. `python3 -I scripts/release.py X.Y.Z` (`--dry-run` só confere): grava `VERSION`, troca só o número da
   versão no site e regenera `site/preview.html`, roda `build.py --release` e `check.py --release`, e
   **imprime** os comandos de commit, push e `gh release` (nessa ordem); não executa nada. Rode-os só com o
   ok do Hugo (commit com a regra 1).
3. App: republique `dist/index.html` no mesmo artifact **sem passar `capabilities`** (a página já tem
   `db` e `user`). Se o tool recusar, leia a versão publicada, compare com o git e republique.
4. Site: republique (o número da versão já foi trocado pelo `release.py`; receita em `site/README.md`).
5. BACKLOG: tire os itens feitos (já estão no changelog) e atualize "Onde estamos".

Patch do jogo ou wiki atualizada: `docs/atualizacao.md`.

## Mapa (detalhe em `docs/arquitetura.md`)

| pasta | o que é |
|---|---|
| `src/` | código da página: `js/` (módulos `GK.*`), `css/`, `manifest.json` (ordem) |
| `data/` | dados do wiki, camadas de nomes `names*.pt-BR.json`, `facts.json`, `days.json`, `techs.json`, `changelog.json` |
| `scripts/` | build, pipeline de dados, testes, `git-hooks/` (Python só com biblioteca padrão; um teste em Node) |
| `dist/`, `prototype/` | páginas geradas (o artifact do app é `dist/index.html`) |
| `site/` | site de apresentação. **O Hugo edita o texto**: não mexa sem ele pedir |
| `docs/` | documentos públicos (índice `docs/README.md`); status em `docs/projeto/BACKLOG.md` |
| `tools/exportar-textos/` | exportador dos textos do jogo (roda no Windows, com o jogo) |
| `docs/revisao-ux/`, `historico/` | internos (fora do git): relatórios, protótipos, capturas, sessões antigas |

## Armadilhas conhecidas

- **meta.built:** sem `--built`, o build grava a data de hoje e vários arquivos gerados mudam só por isso.
  No dia a dia use a data do topo de `data/changelog.json` (a da última release). Se um build mudou só
  a data, `git diff --stat` mostra; desfaça com `git checkout -- <arquivo>`. `--release` é que data a versão.
- wikily: a API só devolve português com `locale=pt-br` (minúsculo); `pt-BR` volta em inglês.
- Um teste exige que o erro de digitação "Trigorigo" não exista no app: não escreva essa forma no changelog.
- Republicar o app: nunca passe `capabilities`. Republicar artifact de outra sessão: o tool exige ler a
  versão publicada antes.
- Mídia do site: liste antes os arquivos do artifact (`scope: "files"`), senão a publicação é recusada.
- `docs/projeto/DESIGN.md` não muda de lugar: `test_build.py` confere o caminho na 1ª linha de `src/css/tokens.css`.
- Qualidade: o item sem sufixo é o bronze; os ids `-silver`/`-gold` ficam por causa de planos salvos.
- Pares que mudam juntos: `README.md` e `README.pt-BR.md`; `docs/duplicar.md` e `docs/duplicate.md`.
- Capturas que semeiam `localStorage["gk2-companion"]` gravam `schemaVersion`: use o `SCHEMA` atual de
  `src/js/store.js`.
- O Reddit é bloqueado para todas as ferramentas do Claude: peça print ou PDF ao Hugo.
- A imagem de prévia do GitHub (`docs/media/social-preview.png`) é enviada à mão em Settings.

## Decisões do Hugo (não reabrir sem ele pedir)

- Sem cartão "Próximo passo" no Planejador (saiu na 1.5.1: atrapalhava).
- Sem modo "No jogo" nem tela acesa; a "Letra grande" cobre. A densidade atual está aprovada.
- Visual "com a cara do jogo" = só sinais pontuais (check verde, ícone em fundo escuro…), nunca molduras
  de couro e madeira (`docs/projeto/PLANO-UI-JOGO.md`, em espera).
- Metas com "− N +" à direita; com quantidade 1 o "−" vira ✕, com Desfazer.
- Aba Tecnologias: todas as colunas que faltam ficam abertas. Aviso de dados velhos só no rodapé.
- Ícone da tela de início: o livro.
