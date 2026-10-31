# Backlog — Companheiro GK2

Estado em 2026-10-30. Em publicação: 1.2.0 (abas Receitas e Tecnologias, cálculo avançado, sincronização mais segura). Publicada antes: 1.1 (tema, sincronização por conta, traduções oficiais).

## Etapa 0 — Base para crescer (feita)
- [x] Quebrar `prototype/index.html` em `src/` (HTML, CSS e um JS por módulo); `scripts/build.py` monta a página.
- [x] Dicionário i18n por módulo (`GK.i18n.add`), para módulos novos não disputarem o mesmo arquivo.
- [x] Arquivo `VERSION` + `data/changelog.json` (pt/en) → versão no rodapé e tela "Histórico de atualizações" (`#changelog`); `CHANGELOG.md` gerado.
- [x] Testes do build cobrindo a montagem a partir de `src/`.

## Etapa 1 — Funcionalidades (feita)
- [x] **Receitas**: lista por categoria/estação com busca; detalhe do item (receitas alternativas, estação, tecnologia, maestria, tempo/energia, subprodutos, "usado em"); botão "Adicionar às metas"; link `#recipes`.
- [x] **Tecnologias**: as 226 tecnologias no build (custos por cor, pré-requisitos, desbloqueios, ramo); ícones extras no sprite; tela por ramo com detalhe; "Já pesquisei" sincronizado; painel no Planejador com as tecnologias que faltam e a soma de pontos por cor.
- [x] **Cálculo avançado**: "tenho N de M"; escolha do membro em itens de grupo ("Brema ou carpa"); vantagens (perks) que alteram rendimento; segurar +/− para repetir.
- [x] **Auditoria**: revisão de código, dados e UX com melhorias priorizadas (`AUDITORIA.md`).

## Etapa 2 — Consolidação (1.2.0)
- [x] Documentação: `README.md`, `docs/arquitetura.md`, `docs/atualizacao.md`, `docs/dados.md`, `docs/guia-de-uso.md`; `SPEC.md` e `DESIGN.md` atualizados.
- [x] Organização de pastas: `tools/`, `docs/`, `historico/`; restos de protótipo removidos.
- [x] Melhorias da auditoria que couberam: ordem das estações, prata/ouro, sincronização (mesclagem, campos preservados, ouvinte, conta), alvos de 44 px, contraste, nome não marca a caixa, busca acessível, textos. Situação em `AUDITORIA.md`, seção "Situação em 1.2.0".
- [x] `made_text` (vira nota da saída, com o bônus de vantagem) e `star_quality` (ciclos para prata/ouro, mostrados na tela Receitas) no build.
- [x] Changelog da 1.2.
- [ ] QA integrado em celular e desktop; correções.
- [ ] Publicar 1.2 (`build.py --release`, mesmo artifact), commit, push, exportar a transcrição para `historico/`.

## Etapa 3 — Depois (sob demanda)

Dados e tradução
- [ ] Traduzir os 231 nomes de receita (derivar "<saída> de <entrada> (ouro)" das partes oficiais) e mostrá-los no seletor e na tela Receitas (AUDITORIA D2).
- [ ] Categorias (45 de 53) e maestrias (3) ainda de máquina: revisar, já que a tela Receitas mostra as categorias (D4).
- [ ] Marcar no build a qualidade das receitas "X a partir de Y (prata/ouro)" e apontar a entrada para a variante; hoje a página deduz pelo nome e pelo id (C2/D1).
- [ ] Gerador do `data/names.machine.pt-BR.json`: não existe em `scripts/` (ficou no rascunho da sessão de 30/10). Sem ele, itens novos de um patch ficam sem a camada de máquina.
- [ ] Nomes pt repetidos entre itens ("Tinta" = Ink e Paint): mostrar o nome EN pequeno quando colidir (D3).
- [ ] Alquimia por runas: calcular misturas válidas em vez de uma de exemplo.
- [ ] Script para reincorporar ao arquivo de tradução os nomes editados no app.

Interface
- [ ] Receitas com link direto: hoje só `#recipes` chega à página, e o item aberto fica no `sessionStorage`. Um link para um item específico não funciona.
- [ ] Gesto de voltar do celular no detalhe da Receita (e da Tecnologia): o detalhe não entra no histórico do navegador, então voltar não leva à lista. Usar o histórico, se o artifact deixar.
- [ ] Memória da escolha de grupo: o membro escolhido vale para o grupo em todos os planos e nunca é apagado. Decidir se deve ser limpo ao remover a meta.
- [ ] "Marcado" não acompanha a quantidade: marcar 3 e depois pedir 10 continua marcado (C3).
- [ ] Rótulos de zona longos nos cartões de construção (D7).
- [ ] Re-render por painel, para listas grandes no celular (F3).
- [ ] Selo "não oficial" em nomes longos (quebra de linha).

Sincronização e privacidade
- [ ] Navegador compartilhado sem login: o plano anônimo vai para a primeira conta que abrir a página naquele navegador. Avisar, ou perguntar antes de levar.
- [ ] Podar `have`/`choice`/`done` ao remover metas (S6).

Desempenho e repositório
- [ ] Sprite em WebP sem perdas (cerca de −430 KB na página) (F1). Sprite de 36 px para ícones mais nítidos (+30% de tamanho).
- [ ] Testes das telas (`GK.ui.*`); chamar o `test_calc.mjs` a partir do `test_build.py` (B1).
- [ ] Tirar do git o zip de `historico/` e os artefatos gerados, se o tamanho do repositório incomodar (B2).

Licença
- [ ] Decidir sobre publicação aberta: pedir autorização em contact@wikily.gg (X4).

## Etapa 4 — Revisão de UX de 31/10/2026 (app, site, GitHub, ideias)

Quatro relatórios em `docs/revisao-ux/` (índice com a ordem de ataque em `docs/revisao-ux/README.md`). Resumo: tirar documentos internos do repositório público; reordenar o Planejador e fixar as abas no celular; linhas de meta e de matéria-prima mais baixas; site com o diferencial no topo e imagens leves; README com o botão do app no topo; depois as ideias novas ("amanhã" e "feito hoje", bilhete por dia, próximo passo, missão como meta, modo letra grande).
