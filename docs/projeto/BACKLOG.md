# Backlog — Companheiro GK2

01/11/2026 · o que já saiu está no [CHANGELOG.md](../../CHANGELOG.md); aqui fica só o que falta.

Esforço: **P** até 2 h · **M** meio dia a um dia · **G** vários dias. Quando a fonte não dava o esforço, ele é uma estimativa (marcada com \*).

## Onde estamos

- **Publicado:** 1.8.5 (01/11): app, site e release v1.8.5 no GitHub. Ajuste dos Recentes da busca (3 últimos, fecham ao perder o foco) e o app mais leve das rodadas de manutenção. Mídia do site e dos READMEs ainda da 1.8.4. Falta trocar a imagem de prévia do GitHub (`docs/media/social-preview.png`, envio manual) e conferir no iPhone o ✓ do teclado e os ícones em WebP.
- **Dados:** o jogo está na **1.011** (30/10) e as receitas da wiki ainda na **1.010**; o aviso de dados velhos está ligado. Os textos oficiais do jogo já são da 1.011.
- **Manutenção** (nada muda para o jogador). Rodadas 1 a 7 feitas em 01/11: um comando para testar tudo (`scripts/check.py`), `scripts/release.py` para fechar versão, trava de push (`scripts/git-hooks/pre-push`), `CLAUDE.md` com as regras, comparação de telas antes/depois (`scripts/shots/`), paridade dos textos pt/en, limpeza (código morto, testes repetidos, documentos, build sem mudança só por data) e, na 4, o sprite dos ícones em WebP sem perda (item 6.22: o app cai de 2,44 MB para 2,00 MB, ou de 909 KB para 575 KB comprimido; iPhone com iOS 13 ou mais velho fica sem ícones, com a letra). Na 5, os nomes pt em 3 camadas (`names.official`, `names.manual`, `names.machine`, lidas por `scripts/name_layers.py`), `fetch_dataset.py --locale pt-br` com trava contra resposta em inglês e `scripts/update_data.py` para o roteiro de atualização. Na 6, o código do app: qualidade e bônus prontos no build (item 6.12), payload sem campos padrão, CSS por componente com a paleta em `tokens.css`, textos em `src/js/i18n/pt.js` e `en.js`, Receitas em 3 arquivos, ajudantes comuns no lugar de 9 trechos repetidos, comentários sem diário de versões e trava no `check.py` contra citação de pasta interna. Na 7, `build.py` em partes por assunto (`scripts/build_parts/`) e os testes do build em `scripts/tests/` (o comando continua `test_build.py`).
- **Esperando o Hugo:**
  1. Três detalhes da ficha do item: preço em prata/bronze (hoje "12 prata"), "curtidas" ou "likes" como no jogo, e se os +48 KB incomodam no celular. No Hoje: dois eventos sem caixinha ("Pagamento do Armazém", "Agatha entrega corpos") e o título curto "Agatha (Encruzilhada)".
  2. O **plano de UI** (`docs/projeto/PLANO-UI-JOGO.md`, seção 4): decidido em 31/10 que primeiro vêm os cortes e os consertos, e a UI volta depois, com o plano atual como base.
  3. As **ideias sem decisão**: 6, 7 (missão como meta, seção 3), 15, 16, 19 e 20 (seção 6).

## Próximas rodadas

A rodada 1 (16 cortes de ruído) saiu inteira entre a 1.6.0 e a 1.8.0.

### 2. Consertos pequenos

| item | o que é | esforço | depende de |
|---|---|---|---|
| 2.6 | Testar num celular real: falta Android e o teclado cobrindo o aviso (no iPhone, o atalho na tela de início e o gesto de voltar funcionam) | P\* | um Android |
| 2.10 | Metas fora da grade nova (sem caixinha; decidido manter) e quantidade das Etapas no topo da linha: só mexer se incomodar | P\* | — |
| 2.13 | Aba Tecnologias: colunas recolhidas com bastante espaço entre si; apertar se incomodar | P | — |

### 3. Missão como meta

Um toque na busca adiciona tudo o que uma missão pede, com as quantidades (ideia 7; a wiki tem 110 missões). Precisa do sim do Hugo. Total: **M–G**.

| item | o que é | esforço | depende de |
|---|---|---|---|
| 3.1 | Missões no build: as 110 da wiki, com itens, quantidades e o nome oficial em PT | M | build novo dos dados |
| 3.2 | A missão aparece na busca só quando você digita o nome (para não dar spoiler) | P\* | 3.1 |
| 3.3 | Tocar adiciona os itens agrupados sob o nome da missão; tratar "tenha com você" e quantidade vazia | M\* | 3.1, 3.2 |

### 4. Sinais do jogo na interface

Só os sinais que o jogador reconhece de relance (check verde, ícone em espaço escuro, pilha amarela, azul da energia), sem molduras nem faixas: a "janela do jogo" foi recusada por pesada em 31/10. Limpo e minimalista, legibilidade primeiro. Plano em `docs/projeto/PLANO-UI-JOGO.md`.

| item | o que é | esforço | depende de |
|---|---|---|---|
| 4.1 | Aprovar o protótipo refeito (app 1.5.1 real com botão Atual / Novo) | P | Hugo |
| 4.2 | Lote 1: check verde nas caixinhas, espaço escuro dos ícones nos dois temas, pilha amarela quando há "tenho N", Progresso em cápsula verde, × vermelho no aviso de patch, contraste do balão | P | 4.1 |
| 4.3 | Lote 2: raio e cérebro em SVG próprio no balão; selo "+20" azul e "−3" roxo nas comidas da lista de Receitas e da busca | P | 4.2 |
| 4.4 | Opcional: trocar a Alegreya Sans pela letra do sistema no texto (cerca de 70 KB a menos) | P | Hugo |

### 5. Dados quando a wiki chegar à 1.011

Trocar as receitas 1.010 pelas da 1.011 e fazer o aviso de dados velhos sumir. Roteiro em `docs/atualizacao.md` (o passo 2, textos do jogo, não precisa: já são 1.011).

| item | o que é | esforço | depende de |
|---|---|---|---|
| 5.1 | Conferir se a wiki atualizou: Frascos de Alquimia II ou Suco de Uva mudaram | P | — |
| 5.2 | Passos 1 e 3 a 6 do roteiro, com 0 erros; trocar `"wiki"` em `data/game-version.json` para 1.011 | P | 5.1 |
| 5.3 | Versão e changelog "Dados do jogo 1.011"; publicar e conferir que o aviso sumiu | P | 5.2 |

### 6. Itens adiados

Guardados: só entram se o uso pedir ou se o Hugo decidir.

| item | o que é | esforço | depende de |
|---|---|---|---|
| **Ideias** | | | |
| 6.1 | Importar o save no computador (ideia 10); risco alto, o formato muda com patch | G | falar com o autor do editor de save |
| 6.3 | Sermões para a missa, no dia da Ira (ideia 15) | M | build novo (fé, bronze, paroquianos) |
| 6.4 | Missões, lista simples (ideia 16) | G | a seção 3 ser muito usada |
| 6.6 | Código do plano para copiar e colar (ideia 19) | P/M | — |
| 6.7 | Compartilhar a lista pelo menu do celular (ideia 20; o "Copiar lista" saiu na 1.8.2) | P | confirmar se o artifact deixa |
| 6.8 | "Hoje dá para resolver algo do seu plano" no painel Hoje (ideia 6) | M/G | — |
| 6.9 | "Onde conseguir" também na lista de Matérias-primas e agrupar por lugar (resto da ideia 14) | M | — |
| **Dados e tradução** | | | |
| 6.11 | Conferir no jogo 4 nomes: "Dig", "Any Story", "Building: Metalwork" e Escrita de livros × Escritura ("Sucata de Cobre" e "Anotação…" são do próprio jogo: ficam) | P\* | — |
| 6.12 | ~~Qualidade prata/ouro marcada no build, e não deduzida na página (C2/D1)~~ feito na manutenção 6 (com o bônus de vantagem; −137 KB no app) | M | — |
| 6.13 | Alquimia por runas: calcular as misturas válidas | G\* | — |
| 6.14 | Script para levar ao arquivo de tradução os nomes editados no app | P\* | — |
| **Telas e sincronização** | | | |
| 6.15 | Link direto para um item da tela Receitas | M\* | — |
| 6.16 | Redesenhar só o painel que mudou, para listas grandes no celular (F3) | M | — |
| 6.17 | Escolha de grupo ("Brema ou carpa"): decidir se é apagada ao remover a meta | P\* | Hugo |
| 6.19 | Rótulos de zona longos nos cartões de construção (D7) | P | — |
| 6.20 | Selo "não oficial" quebrando a linha em nomes longos | P\* | — |
| 6.21 | Navegador compartilhado sem login: avisar antes de levar o plano anônimo para a conta | P\* | — |
| **Peso, testes e licença** | | | |
| 6.23 | Testes das telas (os 3 testes já rodam juntos no `check.py`, e o `scripts/shots/` compara o visual) | M | — |
| 6.25 | Autorização do wikily (X4): e-mail enviado em 31/10, esperar a resposta | P | resposta do wikily |
| 6.26 | Tirar o `dist/` do git, só se o tamanho incomodar | P | — |

## Fora de escopo

- **Modo "No jogo" e tela acesa** (ideias 11 e 12): dispensados em 31/10; a "Letra grande" cobre a leitura de longe.
- **Notificações e alarmes:** o artifact não tem permissão, e o tempo do jogo não segue o relógio. O bilhete por dia cobre.
- **Contagem regressiva do dia:** o app não sabe que horas são no jogo.
- **Conta e servidor próprios:** a conta do Claude já sincroniza; servidor custa e exige cuidar de dados alheios.
- **Painel por cima do jogo (overlay):** os mods de PC já fazem; o celular é a alternativa a isso.
- **Ler o save pelo celular:** o celular não enxerga os arquivos do PC (a versão do computador é o 6.1).
- **Chat com IA:** pode inventar receita e custa dinheiro; a busca responde mais rápido.
- **Mapa interativo:** pesado, ruim com o dedo, e o Wand já faz.
- **Busca por voz:** o microfone do teclado do celular já faz.
- **Otimizador de zumbis e pontuação do cemitério:** depende do save.
- **Lista de conquistas:** pouco a ver com fabricar, e seria mais uma aba.
- **Lista entre dois jogadores (co-op):** convite, permissão e conflito; só quando o co-op for comum.
- **Instalar como app (PWA):** o artifact não permite; o atalho na tela de início já funciona.
- **Preço atual de venda:** muda com o estoque do comerciante; só o preço base é confiável (é o que a ficha do item mostra).
- **Sprite de 36 px:** deixaria o sprite 30% maior; os ícones ficam a cargo da seção 4.

## Como usar este arquivo

1. Terminou um item: marque "feito" na linha, com a versão em que saiu.
2. Ao publicar a versão, leve os itens feitos para o changelog (`data/changelog.json`, que gera o `CHANGELOG.md`), apague-os daqui e atualize "Onde estamos".
3. Este arquivo é público: nada de links privados nem de arquivos internos.
4. Toda vez que mexer neste arquivo, troque a data do topo.
