# scripts/shots/: capturas e "o jogador vê o mesmo?"

Rede de segurança para refatorar: abre o app de antes e o de depois nos mesmos casos e compara tudo o que o
jogador vê. Precisa de `node` e do Google Chrome do macOS (outro caminho: variável `CHROME`). Sem npm, sem servidor.

```sh
python3 -I scripts/build.py --built AAAA-MM-DD      # primeiro o build: compara o dist/preview.html do disco
python3 -I scripts/shots/compare.py                 # HEAD × árvore de trabalho (~40 s); exit 0 = tudo igual
python3 -I scripts/shots/compare.py --ref v1.8.4    # contra outra ref (commit, tag)
python3 -I scripts/shots/compare.py --filtro receitas,busca   # só alguns casos
python3 -I scripts/shots/compare.py --tolerancia 1  # diferença de cor de até 1/255 conta como igual (e é contada)
python3 -I scripts/shots/compare.py --antes dist/preview.html  # um arquivo no lugar da ref (o mesmo: prova de 0 pixel)
python3 -I scripts/shots/compare.py --only-capture  # só tira os prints do app atual (para mostrar ao Hugo)
```

## O que compara

Para cada caso de `casos.json`, em cada idioma e tela (390 px celular e 1280 px desktop, claro e escuro):

- os **pixels** da página inteira (até 12 000 px de altura), comparados dentro do próprio Chrome;
- o **HTML** e o **texto** do que está visível (cabeçalho, busca, a tela aberta, rodapé); no HTML, o espaço em
  branco entre tags não conta (indentação e linhas vazias não mudam a tela);
- o **estado** do app depois de abrir (o que o `GK.store` guardou) e os **erros de JS**.

E uma vez por página, o **resumo do `GK.data`** (um hash por item, por receita e por bloco): pega dado que mudou
sem aparecer em nenhuma tela. Uma linha por caso: `igual`, `DIFERENTE` (com quantos pixels, a maior diferença de cor
por canal, onde e qual painel) ou `ERRO`. "máx 1/255" é invisível: acontece, por exemplo, quando a imagem dos ícones
muda de formato (PNG → WebP) e o Chrome decodifica por outro caminho. Para essas mudanças, `--tolerancia 1` conta esses
pixels como iguais e diz quantos foram tolerados (`igual (tolerância 1: 952 px)`); o padrão é 0 (exato), o que vale
para refatorar. Mudou só a imagem dos ícones? A linha dos dados diz `meta … sprite.image`: o efeito na tela está nos
pixels.

## Onde fica a saída (fora do git)

`.shots/compare/` (apagada a cada rodada): `antes/` e `depois/` com `<caso>.png`, `.html.txt`, `.texto.txt` e
`.json` de cada caso, e `diferencas/` só com os casos diferentes: `<caso>.png` (a página "depois" apagada, com os
pixels diferentes em vermelho e um retângulo em volta) e os diffs de HTML, texto e estado. `--only-capture` grava em
`.shots/capturas/`. As fontes do Google Fonts ficam em `.shots/cache-fontes/` (baixadas uma vez; apague a pasta
para baixar de novo).

## Casos (`casos.json`)

Plano de exemplo (primeira visita), plano curto (nas 4 telas), plano longo, Hoje aberto, qualidade (Vinho prata,
"tenho", marcado), duas listas, Letra grande, busca (recentes, "vinho", "wine"), Receitas (lista, ficha do Vinho
prata, ficha da Abóbora), Tecnologias (árvore e detalhe), Dias, Créditos e Histórico; e casos de clique (só
desktop claro): o ícone que abre a receita no Resumo, no Hoje, nas Tecnologias e nos Dias (`ico-*`), e dobrar e
desdobrar cada seção do Planejador e o Hoje, pelo botão e pelo título (`dobra-*`). Hoje = 1º de novembro de 2026,
dia 61 (Ira). Cada estado é o `localStorage["gk2-companion"]` de um jogador no schema de `schemaVersion` (o `SCHEMA`
de `src/js/store.js`); o `capture.mjs` avisa se a página estiver noutro schema e acusa ERRO se o app descartar o
estado semeado. Para um caso novo, copie um parecido; os passos possíveis estão no comentário do topo do arquivo.

## Por que dá sempre o mesmo resultado

Relógio, fuso e idioma fixos; um perfil novo e um contexto isolado por captura; movimento reduzido (o app tira as
transições) e cursor de texto invisível; só as fontes passam pela rede, sempre com os mesmos bytes; um Chrome por
aba em paralelo e rasterização completa; logo antes da foto, de novo sprite decodificado, fontes e dois quadros; os
elementos `sticky` (o cabeçalho do desktop, a coluna de metas) viram `relative` no mesmo lugar (com o cabeçalho sticky
e a busca aberta, a foto da página inteira às vezes saía sem um botão de ícone fora da tela); e uma foto só por
captura (uma segunda foto logo em seguida perde o anel de foco da busca). Rodar duas vezes a mesma página
(`--antes dist/preview.html`) dá 0 pixel de diferença.

## Processos

O Chrome roda com `--remote-debugging-pipe` (sem porta) e morre junto com o `node`, mesmo num `kill -9`. Há
tempo-limite global (300 s) e Ctrl-C fecha tudo. Depois de rodar, `pgrep -fl "Google Chrome.*headless"` volta vazio.

`capture.mjs` também roda sozinho (`node scripts/shots/capture.mjs --saida DIR PAGINA.html`, ou `--antes A --depois B`);
as opções estão no topo do arquivo.
