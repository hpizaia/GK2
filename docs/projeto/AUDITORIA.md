> Documento de projeto. Parte do conteúdo descreve a versão 1.2;
> o estado atual está no [README](../../README.pt-BR.md) e no [CHANGELOG](../../CHANGELOG.md).

# Auditoria — Companheiro GK2 (v1.1)

Data: 2026-10-30. Escopo: `prototype/index.html` (página única atual), `scripts/`, `data/`, `tools/exportar-textos/`, docs.
Leitura apenas; nenhum arquivo do projeto foi alterado. Os achados citam **módulos** (`GK.calc`, `GK.sync`, `GK.ui.summary`…)
e não números de linha, para continuarem válidos depois da divisão em `src/`.
Severidade: **alta / média / baixa**. Esforço: **P** (≤ 2 h), **M** (meio dia a 1 dia), **G** (vários dias).

## Situação em 1.2.0

Atualizado em 2026-10-30, na documentação da 1.2.0. Os achados originais abaixo ficam como estavam (descrevem a v1.1); esta seção só diz o que já foi tratado. Os testes citados estão em `scripts/test_calc.mjs` (node) e `scripts/test_build.py`.

**Tratado**

| achado | o que mudou |
|---|---|
| C1 ordem dos cartões | Os cartões seguem as dependências: nenhuma estação depende de outra mais abaixo. Quando uma estação volta, ela ganha um segundo cartão ("de novo"). Teste de invariante sobre todos os itens fabricáveis |
| C2/D1 prata/ouro | O seletor mostra os ingredientes e a qualidade ("ouro"). Receitas "X a partir de Y (prata/ouro)" passam a consumir o Y com a qualidade certa (variante real ou sintética). Feito na carga da página (`GK.data`), não no build |
| C7 "tenho N" e grupos | "Tenho N de M" desconta antes do arredondamento. Itens de grupo ("Brema ou carpa") permitem escolher o membro |
| S1 última gravação vence | Reconciliação com base comum (`syncBase`): se só um lado mudou, ele vence; se os dois mudaram, mescla campo a campo (`GK.store.mergeSynced`) |
| S2 versões futuras | O `v` do documento é lido e mantido. Campos desconhecidos de `state` são preservados |
| S3 ouvinte morto | Re-assina uma vez, com espera, e de novo no evento `online` |
| S4 falha de gravação | Uma nova tentativa com jitter |
| S5 troca de conta | `localStorage` separado por conta. O plano anônimo vai para a primeira conta que abrir e depois é apagado |
| S6 (parte) | Gravação imediata no `pagehide`. Limite medido em bytes |
| U1 alvos de toque | 44 px nas ações das linhas, botões pequenos, seletores e lápis |
| U2 contraste | Tokens do tema claro (`--ink-3`, `--gold`, `--accent`) e `--blood` do escuro ajustados para ≥ 4,5:1 (ver `DESIGN.md` §2). A borda da busca usa `--gold`. Falta conferir `--gold` sobre `--slate` no escuro (4,14), se ainda houver texto assim |
| U3 nome marca a caixa | Só a caixa alterna. O nome fica livre |
| U4 combobox | Padrão combobox + listbox, `aria-activedescendant`, contagem anunciada |
| U6 textos | "receita sem ganho", "Vantagem" em todas as telas, "não oficial" sem hífen nos selos e no rodapé; a nota do rodapé aponta para as Vantagens |
| B1 (parte) | `scripts/test_calc.mjs`: cerca de 20 casos de `GK.data`, `GK.calc`, `GK.store`, `GK.sync` e rótulos do `GK.ui.fmt`. `test_build.py` testa `GK.tech` e a sintaxe de todos os módulos |
| B2/B3/B4 higiene | `tradução windows/` fora do git; `collect_en_names.py` e `unwrap_browser_dump.py` removidos; `BRIEF-WINDOWS.md` em `historico/`; documentos em `docs/`; só `gk2_textos.json` e o relatório do export do jogo no git |
| B5 (parte) | O build aceita `SOURCE_DATE_EPOCH` |
| B6 documentação | `README.md`, `docs/` (dados, atualização, arquitetura, guia de uso), `SPEC.md` e `DESIGN.md` atualizados |

**Ainda aberto** (no `BACKLOG.md`, Etapa 3)

- F1: sprite em WebP sem perdas (cerca de −430 KB).
- B1: faltam testes das telas (`GK.ui.*`) e o `test_calc.mjs` não é chamado pelo `test_build.py`.
- X4: licença do wikily. Situação em 31/10/2026: código publicado sob MIT (só o código), dados usados como conteúdo de fã com crédito, pedido de autorização enviado ao wikily; ver `docs/dados.md`.
- D2: 231 nomes de receita sem pt.
- D4: 45 categorias e 3 maestrias ainda de máquina.
- C2/D1 no build: o build já exporta `made_text` (como nota da saída) e `star_quality`, mas a qualidade das receitas "X a partir de Y (ouro)" e a troca da entrada pela variante ainda são feitas na página, pelo nome e pelo id.
- Também sem mudança: C3 (marcação não acompanha a quantidade), C4, C5, D3 (nomes pt repetidos), D6, D7 (rótulos de zona longos), F2–F5, U5, U7 (atalho "/"), U8, X2, X3, X5, S6 (poda de `have`/`choice`/`done`).

## Resumo executivo

1. A soma do `GK.calc` está **correta**: Caixote ×3, Espada Mestra, Vinho, Fornalha I e uma lista combinada batem com a conta feita à mão, e as 682 metas visíveis passaram nos invariantes (`runs = ceil(need/yield)`, `0 ≤ sobra < rendimento`).
2. A ordem dos cartões por estação **contradiz a dica "siga de cima para baixo"** em 105 de 412 planos (25%): um cartão depende de outro que aparece mais abaixo.
3. As receitas de qualidade (ouro/prata) **consomem o item comum** nos dados e aparecem no seletor com o mesmo texto, mudando só o rendimento. Quem escolhe "ouro" recebe uma conta de matéria-prima errada.
4. O `GK.sync` é cuidadoso com eco, cache e relógio, mas usa **"última gravação vence" no documento inteiro**: edições feitas offline em dois aparelhos se perdem sem aviso.
5. O sync **não é compatível com versões futuras**: campos novos (o "já pesquisei" das Tecnologias) serão apagados por uma aba ou aparelho com a versão antiga.
6. O ouvinte do `onSnapshot` morre e não volta; o plano local de uma conta pode ser enviado para outra conta no mesmo navegador.
7. Desempenho: o sprite em base64 ocupa 733 KB (42% da página e 78% do gzip). WebP sem perdas ou pngquant economiza cerca de 430 KB. Parse e cálculo são rápidos.
8. UX: vários alvos de toque têm 30–36 px (a SPEC promete ≥ 44). Há 9 pares de cores abaixo de 4,5:1, e tocar no nome de um item marca o item como coletado.
9. Pipeline: o build é idempotente e reprodutível (verificado byte a byte) e passa em 27 testes. Mas **não há teste do JS**, e o git carrega cerca de 30 MB de artefatos gerados e de dumps do jogo.
10. Licença: os dados do wikily, os ícones do jogo e os textos do jogo não são do projeto. Resolvido em 31/10/2026: a `LICENSE` (MIT) cobre só o código e exclui dados, ícones e textos; o uso é de fã, com crédito, e o pedido de autorização foi enviado ao wikily (`docs/dados.md`).

## Testes executados

| comando | resultado |
|---|---|
| `python3 -I scripts/test_build.py` | **27 testes OK** em 1,1 s (fixtures + smoke na base real: 820 itens, 695 receitas, 79 estações) |
| `python3 -I scripts/validate.py data/gk2.json` | exit 0. **0 erros**, 206 avisos (`cycle` 8, `orphan` 163, `zero-inputs` 35), 73 infos (`multi-recipe` 66, `cycle-trapped` 7) |
| `build.py --out-dir <tmp>` ×2 | 2ª execução: "wrote nothing". `gk2.json` idêntico ao versionado. `--artifact --sprite` reproduz `dist/index.html` byte a byte |
| `GK.util`+`GK.data`+`GK.calc` extraídos da página e rodados no node sobre o payload embutido | casos abaixo. Invariantes OK nas 682 metas visíveis. Ciclos sintéticos de 2 nós e autoconsumo OK |

---

## 1. Correção da calculadora (`GK.calc`)

**Casos reais conferidos à mão (todos corretos):**

| meta | resultado do `plan()` | conferência |
|---|---|---|
| Caixote ×3 | 3 Tora, 1 Gordura, 2 Argila, 3 Minério de Ferro. Caixote 2 execuções (sobra 1), Combustível 50 → 3 execuções (sobra 10), Placa de Madeira 7 → 7 Placas → 2 execuções | ok (Tora = 2 das Placas + 1 da Tora Pequena) |
| Espada Mestra ×1 | 8 Folha, 1 Cera, 3 Areia, 1 Tora, 4 Lingote de aço. Alcalino via mistura de exemplo (Lab. II) | ok (Lingote de aço só é vendido pelo Bispo, por isso é matéria-prima) |
| Vinho ×5 | 48 Uvas, 6 Areia, 1 Tora. 8 Sucos (bronze), 8 Garrafas, Combustível 60 | ok |
| Vinho ×5 com a receita alternativa cíclica "Aprimorar bebida I" | Vinho vira matéria-prima, `refused` + aviso | ok (rendimento líquido 0) |
| Fornalha I (construção) | 4 Pedra, 1 Tora, 8 Argila | ok |
| Caixote ×3 + Fornalha I + Espada, com "Já tenho" Kit de Madeira I | Combustível agregado 70 → 4 execuções (calculado separado daria 5) | ok: a agregação global acontece antes do arredondamento |

**Achados**

**C1. Ordem dos cartões quebra dependências.** Severidade média, esforço P/M.
- Evidência: os cartões são ordenados por `minStage`. No Caixote, "Bancada de Carpintaria I" (etapas 2–6) vem antes de "Cubo de Destilação" (etapa 4), mas a Tábua engordurada (etapa 5) precisa da Gordura Derretida feita no Cubo. Na Espada, "Bigorna de aço" (etapas 1–8) vem antes do "Laboratório II" (7). Medido: 105 de 412 planos com mais de uma estação.
- Por que importa: a dica "Siga de cima para baixo" leva o jogador a uma bancada antes de ter os insumos.
- Recomendação: no `GK.calc.plan`, dividir o grupo de uma estação em blocos de etapas contíguas, ou ordenar os cartões por etapa e repetir a estação quando ela volta. Mostrar a etapa em cada linha. Criar um teste com o invariante "nenhum cartão depende de um cartão posterior".

**C2. Receitas de qualidade indistinguíveis e com insumo errado.** Severidade alta, esforço M (ver D1).
- Evidência: `baked-pumpkin-from-pumpkin-gold` tem a entrada `pumpkin` ×2 e a saída 7. A versão bronze tem a mesma entrada e saída 2. No seletor aparece "A · Forno da Cozinha: 2 Abóbora + 10 Combustível → 2" e "C · … → 7". O `recipeLabel` não usa `r.name`.
- Por que importa: ao escolher "ouro", o plano mostra 3,5× menos abóboras e não diz que é preciso abóbora de ouro.
- Recomendação: curto prazo, `GK.ui.fmt.recipeLabel` mostra o sufixo de qualidade (do id ou de `r.name`, "(ouro)"). Definitivo: corrigir os dados (D1).

**C3. "Marcado" não acompanha a quantidade.** Severidade média, esforço P.
- Evidência: `GK.store` guarda `done["step:<id>"] = true`. Se a meta sobe de 3 para 10, Lenha continua marcada. A marca também sobrevive a `removeGoal` e vale para planos futuros.
- Recomendação: gravar `done[key] = qty` marcada e mostrar como pendente (ou "parcial") quando `need > qty`. Limpar as chaves fora do plano em `removeGoal`.

**C4. Autoconsumo sem aviso de "semente inicial".** Severidade baixa, esforço P.
- Evidência: `howToMake` desconta a entrada igual à saída (rendimento líquido), mas a primeira execução precisa de `self` unidades. Teste sintético: S (1 S + 1 Z → 3 S) pede só Z.
- Recomendação: incluir `seed: self` no passo e exibir "precisa de N X para começar".

**C5. Corte de ciclo depende da ordem das metas.** Severidade baixa, esforço P (documentar).
- Evidência: num ciclo sintético A↔B, `[A,B]` e `[B,A]` dão listas de matérias-primas diferentes. No grafo real das receitas padrão não há ciclos (só via escolha do usuário).
- Recomendação: documentar no `GK.calc` e no teste. Opcional: cortar sempre na aresta de volta para a meta.

**C6. Subprodutos não abatidos.** Severidade baixa.
- Evidência: 80 `extra`, só 19 determinísticos, e todos vêm de receitas que não se expandem (colheita, Tora, Minério). Hoje não altera nenhum plano.
- Recomendação: manter "não somado". Rever quando houver "tenho N".

**C7. "Já tenho" é binário, e itens de grupo não permitem escolher o membro.** Severidade baixa, esforço P (o motor já tem `opt.stock`).
- Recomendação: na tarefa "tenho N de M" do backlog, ligar `stock` no `GK.app.computePlan`. Para grupos, um `choice` de membro que troque a folha.

## 2. Qualidade dos dados

**D1. Variantes de qualidade colapsadas no item base.** Severidade alta, esforço M (`scripts/build_dataset.py` / `build.py`).
- Evidência: as receitas `*-from-<x>-gold|silver` de abóbora assada, sopas, anéis de cebola, torradas, Suprimentos: Conservas I/II, Vegetais e Vinho consomem `pumpkin`, `cabbage`, `onion`, `wine` comuns, com rendimentos diferentes. As de Suco de Uva e Vinho já usam ids de variante (`grape-juice-gold`).
- Por que importa: é a principal fonte de conta errada (C2). Também faz "Aprimorar bebida" parecer um autoconsumo de Vinho.
- Recomendação: no build, quando `name` termina em "(gold|silver)" e a entrada é o item base, apontar a entrada para a `quality-variant` (criar a variante se não existir, com `base_item`). Validar com um novo aviso `quality-input`.

**D2. Nomes de receita não traduzidos e não usados.** Severidade média, esforço P/M.
- Evidência: 231 de 232 `recipe.name` estão `missing` em pt (`report-l10n.md`). O seletor de receitas não mostra nenhum nome.
- Recomendação: gerar o pt derivado ("<saída> de <entrada> (ouro)") com as regras de "Derived names" do `build.py` e exibir no `recipeLabel`.

**D3. Nomes pt repetidos entre itens visíveis.** Severidade média, esforço P.
- Evidência: "Tinta" = Ink e Paint. "Placa de Madeira" = Wooden Plank e Wooden Sign. "Anotação encontrada na masmorra da Inquisição" = Inquisitor's note e *Key from the Inquisition dungeon* (`gameKey intro_prison_key`, provável erro do próprio jogo).
- Por que importa: na busca, os dois resultados ficam iguais.
- Recomendação: no `GK.ui.search` (e nas linhas), mostrar o nome EN em letra pequena quando o nome pt colidir, ou sempre, como sugere o `README-l10n` (item 1, não implementado). Criar um aviso `name-collision` no validate.

**D4. Camadas de tradução.** Positivo: `official > likely > machine` funciona. Itens: 785 oficiais, 29 derivados, só 6 de máquina.
- Nas 200 entradas mais usadas, a camada de máquina diverge da oficial em 119. A maioria é caixa ("Placa de madeira" × "Placa de Madeira"), mas há trocas de termo que justificavam o selo: Brick "Tijolo" → oficial "Bloco", Board "Prancha" → "Placa", Iron Detail "Peça de ferro" → "Detalhe de Ferro", Stick "Graveto" → "Vareta", Guts "Tripas" → "Entranhas".
- Oficiais suspeitos (texto do jogo, manter, mas anotar): Clay Molds → "Urnas de argila" (colide em sentido com Clay Urn "Urna de Argila"), Assembly bench II → "**Banco** de Montagem II" × I "**Bancada** de Montagem I", e caixa inconsistente ("Tábua engordurada" × "Placa de Madeira").
- Ainda de máquina: 45 categorias (não exibidas hoje; as Receitas vão exibir), 3 maestrias, 21 notas.
- Recomendação: revisar as 45 categorias antes da tela Receitas. Baixa/P.

**D5. Defaults: amostra de 15 itens com várias receitas.** Avaliação: **sensatos**. Iron Ingot (Fornalha II 3→3), Brick (forno), Glass, Board, Short Log, Firewood (tora pequena × 20 gravetos), Wooden Kit I (bancada, 2 por execução), Iron Kit I, Bronze Ingot (pepita), Peat, Alcohol (qualquer vinho → 4), Melted Fat, Seed Oil, Wine (bronze), Porter Station (área principal).
- Discutível: Suco de Uva (ouro) usa "Aprimorar II a partir de prata + Umami" (o `cd` do wikily), em vez de prensar direto. Wooden Kit I e Iron Kit I têm receitas de fábrica muito mais baratas (1 tora → 4 kits). Aceitável para o começo de jogo; vale uma dica "há receita mais barata".

**D6. Defaults com receita oculta ou insumo oculto: 33 casos.** Severidade baixa, esforço P.
- Evidência: as rezas (`basic-prayer` etc.) pedem "História" (`virtual`). `rusty-armor` pede `simple-iron-part` (inobtível). 18 construções/itens usam uma receita `listed:false` como padrão.
- Recomendação: no `build.py`, preferir uma receita listada quando houver. No `GK.ui.summary`, selo "oculto" na matéria-prima inobtível.

**D7. Rótulos de zona enormes.** Severidade baixa, esforço P.
- Evidência: zonas como "Pátio, Cemitério, Jardim, Mina Antiga, Pedreira, … (14)" viram título de cartão (`GK.data.zoneStation`).
- Recomendação: um cartão único "Construção (no local)" e a zona como sublinha de cada passo, abreviada ("14 áreas").

**D8. Outros pontos.**
- Versões diferentes: receitas do wiki em 1.010, textos do jogo em 1.011. Mostrar as duas no rodapé.
- `orphan` (163) é ruído no relatório: rebaixar para info.
- Estações que vêm de reparo (Forno da Cozinha…) aparecem como matéria-prima: já documentado em `README-data.md`.
- Filtro de ocultos (`listed`, `unobtainable`, kinds `virtual`/`action`) está coerente. O seletor ainda lista receitas ocultas, marcadas "oculta", o que está correto.

## 3. Sincronização (`GK.sync`) e store (`GK.store`)

Pontos fortes: ignora o eco (`hasPendingWrites`); cópia de cache nunca dispara gravação; carimbo monotônico (`stamp` > anterior, o que neutraliza relógio adiantado); exemplo intocado não sobrescreve a conta (`noStamp`); migração v1→v4 cobre `overrides` e `updatedAt = EPOCH`; corpo remoto reconstruído campo a campo (`sanitizeRemote`); uma gravação por vez; timeout de 10 s. O caminho `data/users/<id>/state` é privado até para o dono, segundo o contrato de `db` 0.2.94.

**S1. "Última gravação vence" no documento inteiro.** Severidade alta, esforço M.
- Evidência: `onSnap` → `applyRemote(fields)` substitui `goals/choice/have/done/overrides` se `d.updatedAt` for maior. Dois aparelhos editando offline: o de carimbo menor perde tudo, sem aviso. A plataforma não tem transações (`set` é LWW).
- Recomendação: (a) mínimo: antes do `applyRemote`, guardar o estado local substituído em `localStorage` (`gk2-companion.prev`) e mostrar um toast "Plano atualizado de outro aparelho · Desfazer"; (b) melhor: carimbo por chave (`goals[i].at`, `done[k] = at`) e união no `GK.store`, com mesclagem campo a campo.

**S2. Sem compatibilidade com versões futuras.** Severidade média, esforço P. **Fazer antes da tela Tecnologias.**
- Evidência: o `v` do documento é gravado e nunca lido. `sanitizeRemote` descarta campos desconhecidos. `migrate` aceita `schemaVersion > SCHEMA`. Uma aba antiga aberta vai regravar o documento sem `researched` na próxima alteração.
- Recomendação: no `GK.sync`, se `d.v > SCHEMA`, não gravar e mostrar "Há uma versão nova: recarregue". No `GK.store`, preservar campos desconhecidos (`rest`) no local e no remoto.

**S3. Ouvinte morto não é recriado.** Severidade média, esforço P.
- Evidência: pelo contrato, `unavailable` encerra o ouvinte, e "um novo onSnapshot é a única recuperação". O `onError` só muda o status. O `Unsubscribe` não é guardado.
- Recomendação: guardar o `unsub`. Em `onError` depois de `ready`, re-assinar uma vez com espera aleatória (e no `online`/`visibilitychange`).

**S4. Falha de gravação sem nova tentativa.** Severidade baixa, esforço P.
- Evidência: o `catch` zera `dirty`, e a nova tentativa só vem na próxima alteração. O contrato recomenda tentar de novo uma vez em `unavailable`.
- Recomendação: uma nova tentativa com jitter, e outra no evento `online`.

**S5. Troca de conta no mesmo navegador.** Severidade média, esforço P.
- Evidência: o `localStorage` não guarda o id do usuário. Se B entra com a conta vazia, `pushLocal` envia o plano de A para a conta de B. Ao sair da conta (`use("db")` = null), o plano de A fica visível como "Só neste aparelho".
- Recomendação: gravar `syncedUser` no estado. Se for diferente do `user.id()` atual, não enviar; adotar o remoto ou começar do zero.

**S6. Pequenos riscos de perda e crescimento.** Severidade baixa, esforço P.
- `persist` tem atraso de 120 ms e não grava em `pagehide`: adicionar a gravação imediata.
- O limite de 200 000 é contado em caracteres e o limite real é 256 KiB em bytes (acentos ocupam 2 bytes). Medir com `new Blob([json]).size`.
- `have`/`choice`/`done` nunca são podados. Hoje são pequenos; podar ao remover metas.
- Cota do `localStorage`: o estado tem poucos KB, sem risco.

## 4. Desempenho em celular

| parte (página do artifact) | bruto | gzip |
|---|---:|---:|
| página total (`dist/index.html`) | 1,72 MB | 713 KB |
| sprite (PNG em base64 dentro do JSON) | 733 KB | 553 KB |
| dados sem sprite | 855 KB | 114 KB |
| código (CSS + JS) | 116 KB | ~30 KB |

Medido no node (desktop): `JSON.parse` 3,8 ms, `GK.data.load` 9,4 ms, `plan` (3 metas) 0,06 ms, busca 0,3–1,5 ms por tecla. Num celular intermediário, estimo de 4 a 8 vezes mais: cerca de 100 ms de boot, que não é gargalo.

**F1. Sprite pesado.** Severidade média, esforço P (`scripts/make_sprite.py`).
- Evidência: o PNG RGBA tem 550 KB. Com `pngquant --quality 70-100` vai para 217 KB (−61%); em **WebP sem perdas**, 227 KB (−59%, sem perda visual). Base64 não comprime no gzip.
- Recomendação: gerar WebP sem perdas (ou pngquant opcional) no `make_sprite.py`. Economia de cerca de 430 KB brutos e 330 KB em gzip.

**F2. Campos sem uso no payload.** Severidade baixa, esforço P (`build.py --inject`).
- Evidência: `key` (18 KB), `raw`, `cd`, `icon: null`, e `false`/`[]`/`null` padrão em todo registro. Sem eles, os dados vão de 855 para 688 KB (−20% de parse e memória; só −10 KB em gzip).
- Recomendação: omitir valores padrão e deixar o `GK.data.normItem/normRecipe` repor (já faz). Manter `ticks`/`energy`/`runes`/`name` para a tela Receitas.

**F3. Re-render total a cada ação.** Severidade média, esforço M (`GK.app.renderAll`).
- Evidência: toda mudança no store recalcula o plano e refaz o `innerHTML` dos 7 painéis, cabeçalho e rodapé inclusive. Marcar uma caixa reconstrói todas as linhas e `<select>`. Com 30 metas (cerca de 150 linhas), deve travar em aparelho fraco, e o iOS fecha o `<select>` aberto.
- Recomendação: um conjunto de "painéis sujos" por tipo de mudança (`meta.from`). Para `toggleDone`, só alternar a classe `is-done` e a barra de progresso.

**F4. Fontes do Google bloqueiam a renderização.** Severidade baixa, esforço P.
- Recomendação: `<link rel=preload as=style>` + `media="print" onload`, ou subset local. O fallback já existe.

**F5. Busca.** O debounce de 70 ms e o índice pré-normalizado estão adequados. O fuzzy traz ruído ("mestra" → "Melhorar Estradas e Caminhos"). Severidade baixa: exigir fuzzy só quando houver menos de 5 resultados melhores.

## 5. UX e acessibilidade

**U1. Alvos de toque abaixo de 44 px** (contra a SPEC). Severidade média, esforço P (CSS).
- Evidência: `.btn-sm` 36 px (Limpar lista, Copiar lista, Já tenho, Fabricar, sugestões), `<select>` 36 px, `.hidden-toggle` 36 px, lápis `.edit-ico` 30×30. Passa no WCAG 2.5.8 (24 px).
- Recomendação: altura mínima de 44 px nas ações das linhas. O lápis com 44 px de área útil (padding negativo).

**U2. Contraste (WCAG 1.4.3 / 1.4.11).** Severidade média, esforço P (tokens).

| par | escuro | claro | onde |
|---|---:|---:|---|
| `--gold` sobre `--slate` | 4,14 | **3,17** | "etapa N" nos cabeçalhos das estações (12 px) |
| `--accent` sobre `--slate` | 6,50 | **3,58** | aba atual |
| `--ink-3` sobre `--slate` / `--bg-2` | 4,25 | **3,63 / 3,90** | selo "em breve", placeholder da busca |
| `--blood` sobre `--panel` | **4,01** | 6,30 | "Limpar lista", ✕ |
| `--accent-ink` sobre `--blood` | **4,48** | 6,90 | "Confirmar limpeza" |
| `--gold` sobre `--panel` | 4,74 | **4,29** | letra no lugar do ícone |
| `--frame` sobre `--bg-2` (borda) | **1,92** | **2,38** | borda da busca e do contador (precisa de ≥ 3) |

Recomendação: no claro, escurecer `--gold`/`--accent` no cabeçalho (ou usar `--ink` lá) e `--ink-3` para cerca de `#6a5940`. No escuro, clarear `--blood` para cerca de `#e06a5c`. Nas bordas dos campos, usar `--gold`.

**U3. Tocar no nome marca como coletado.** Severidade média, esforço P (`GK.ui.fmt.nameBlock`, `GK.ui.summary`).
- Evidência: nome e sublinha são `<label for=cb>`. Quem toca para ler, ou erra o lápis, marca o item.
- Recomendação: só a caixa alterna. O nome fica livre para abrir o detalhe (tela Receitas).

**U4. Busca sem semântica de combobox.** Severidade média, esforço P (`GK.ui.search`).
- Evidência: faltam `aria-expanded`/`aria-controls`/`aria-activedescendant`. A contagem de resultados é `aria-hidden` e nada é anunciado.
- Recomendação: o padrão combobox + listbox da ARIA APG e uma região `aria-live` com "N resultados".

**U5. Foco perdido.** Severidade baixa, esforço P.
- Evidência: depois de "Já tenho" (o botão muda de lista), de ✕ e de "Fabricar", o foco cai no `body`.
- Recomendação: no `GK.app.renderAll`, levar o foco à linha vizinha ou ao novo botão "Fabricar".

**U6. Texto em pt-BR.** Severidade baixa, esforço P (`GK.i18n`).
- "não-oficial" → **"não oficial"** (pelo Acordo Ortográfico de 1990, "não" não leva hífen).
- "receita recusada" é opaco → "receita sem ganho".
- "Talento: {tech}" → **"Vantagem: {tech}"** (o jogo diz "Vantagem de joalheiro").
- A dica "Siga de cima para baixo" só vale depois do C1.
- Inglês ok.

**U7. Teclado e movimento.** Positivo: `:focus-visible` global, setas na lista de resultados, Esc fecha, `aria-pressed` nos segmentos, `aria-current` nas abas, `aria-live` no toast, `prefers-reduced-motion` respeitado, `lang` atualizado.
- Pendente: atalho "/" para focar a busca. Severidade baixa.

**U8. Celular.** A lista de resultados com `max-height: 62vh` fica sob o teclado do iOS: usar `visualViewport.height`. Selos `nowrap` em nomes longos já estão no backlog. Severidade baixa.

## 6. Pipeline de build e testes, higiene do repositório

> **Layout em 1.2.0.** Rastreados no git: `src/` (fontes da página), `scripts/` (+ `fixtures/`), `tools/exportar-textos/`, `data/` (entradas, `gk2.json`, `gk2.min.json`, `techs.json`, `sprite.json`/`sprite.png`, nomes, relatórios) e `data/game-texts/` (só `gk2_textos.json` e `RELATORIO-exportacao.md`), `prototype/index.html`, `dist/index.html` + `preview.html`, `docs/`, `historico/` (o zip de 10,6 MB e o `BRIEF-WINDOWS.md`). Fora do git: `data/raw/`, `data/icons/`, o dump completo do jogo, `tradução windows/` (só a `.venv` e um link de compatibilidade). Os commits antigos ainda carregam os dumps (cerca de 30 MB): limpar o histórico só se o tamanho do repositório incomodar. Mapa completo em `docs/arquitetura.md`.

**B1. Nenhum teste do JS.** Severidade média, esforço M.
- Evidência: `GK.calc`, `GK.store.migrate/sanitizeRemote`, `GK.data.load` (forma "collapsed") e `GK.sync.onSnap` não têm teste. Os 27 testes cobrem só o Python.
- Recomendação: `scripts/test_calc.mjs` (node, sem dependências) carregando os módulos de `src/` com um stub mínimo de `document`, como fiz nesta auditoria. Casos: os 6 da seção 1, invariantes sobre todas as metas, C1, ciclos sintéticos, migração v1→v4, `onSnap` com eco, cache, mais novo e mais antigo (com um `ref` falso). Chamar a partir do `test_build.py`.

**B2. Artefatos gerados e dumps no git (cerca de 30 MB por commit de build).** Severidade média, esforço P.
- Evidência (rastreados): `historico/*.zip` 10,6 MB; `tradução windows/gk2_textos_en/` 11 MB (`gk2_textos_todos.json` 8,9 MB, CSVs completos do jogo, cópia velha do `exportar_textos.py`); `dist/index.html` + `preview.html` 3,4 MB; `prototype/index.html` com os dados 1,8 MB; `gk2.min.json`; `sprite.json` (o `sprite.png` em base64, duplicado); `tools/exportar-textos/_teste_join.json`.
- Recomendação: versionar fontes e `gk2.json`. Ignorar `dist/preview.html`, `gk2.min.json` e `sprite.json` (gerar a partir do PNG). Tirar o HTML com dados de `prototype/` ou `src/`, injetando só no `dist/`. Mover `historico/` e o export do jogo para fora do git, ou para `data/raw/game-text/` (ignorado). Guardar só `names.official.pt-BR.json` e um resumo.

**B3. Scripts superados ou de uso único.** Severidade baixa, esforço P.
- `collect_en_names.py` (o README diz que foi substituído pelo `build_names.py`) e `unwrap_browser_dump.py` (uso único): remover.
- `build_names.py`, `mt_glossary.py`, `fetch_gk1_langlinks.py` geraram camadas que a oficial já cobre: mover para `tools/legado/`.
- `BRIEF-WINDOWS.md` (briefing de sessão): mover para `historico/`.
- A cópia de `exportar_textos.py` em `tradução windows/` (12,5 KB × 40 KB em `tools/`) está desatualizada: remover.

**B4. Pastas.** Severidade baixa, esforço P.
- Renomear `tradução windows/` (espaço e acento atrapalham scripts) para `tools/exportar-textos/saida/`, ignorado.
- O `.venv` de 54 MB já está ignorado por `tradução windows/**/.venv/`: apagar do disco.
- `scripts/__pycache__`, `.DS_Store`: ok.

**B5. Build.** Positivo: idempotente, determinístico, escrita só quando os bytes mudam, `.bak` só com mudança, erro grave bloqueia a saída, injeção com `<` escapado.
- Ressalva: `meta.built` tem como padrão "hoje" (UTC). Rodar no dia seguinte altera todas as saídas. Usar `SOURCE_DATE_EPOCH` fixado no `VERSION`, ou a data dos dados. Severidade baixa.
- Faltam testes do build a partir de `src/` (já no backlog).

**B6. Documentação desatualizada ou ausente.** Severidade média, esforço M.
- `SPEC.md` ainda diz "ícones remotos", "< 2 MB" e "Conta/sync fora de escopo". Na v1.1 há sprite embutido, sync e 1,7 MB.
- `DESIGN.md` §4 descreve o contrato do mock, não o schema 1.
- `README-l10n.md` diz "nenhum oficial".
- Faltam `README.md`, `docs/atualizacao.md` (roteiro de patch do jogo) e `docs/dados.md` (fontes e licenças): todos já no backlog.

## 7. Segurança e privacidade

**X1. Escape: ok.** Todo texto vindo de dados, nomes editados, notas, nomes de estação e rótulos de `<option>` passa por `GK.util.esc`. Ids passam por `domId`. A URL do sprite tem aspas removidas. O bloco `gk2-data` escapa `<`, U+2028 e U+2029. Nenhum `eval` ou `new Function`. Nenhum segredo nos arquivos rastreados (varredura por padrões de chave: vazia).

**X2. HTML confiável no dicionário.** Severidade baixa, esforço P.
- Evidência: `app.title` (`<b>`) e `footer.data` (`{link}`) vão por `innerHTML` sem escape.
- Recomendação: regra no `GK.i18n`: só chaves com sufixo `.html` podem ter HTML, e as variáveis sempre passam por escape (importa quando entrar um idioma de colaborador).

**X3. Estado remoto sem limites de tamanho.** Severidade baixa, esforço P (`GK.store.sanitizeRemote`).
- Evidência: valida tipos, mas não o tamanho nem a existência: um override pode ter qualquer tamanho, e as chaves de `done`/`have`/`choice` não são conferidas. Só a própria conta escreve ali.
- Recomendação: limitar override a 80 caracteres e 2000 entradas, e filtrar ids por `GK.data.item`.

**X4. Licença e redistribuição.** Severidade alta (é uma decisão), esforço P para conter.
- Evidência: os termos do wikily proíbem scraping e uso sem licença (`data/README-data.md`). Os ícones são arte do jogo (© Lazy Bear) embutida no sprite. O dump completo da localização do jogo fica fora do git (`.gitignore`).
- Situação em 31/10/2026: repositório público com `LICENSE` MIT só para o código e aviso de escopo; autorização pedida a contact@wikily.gg; dumps fora do git. O crédito no rodapé e na tela Créditos está correto.

**X5. `exportar_textos.bat` instala `UnityPy` sem versão fixa.** Severidade baixa, esforço P.
- Recomendação: fixar a versão (`UnityPy==<testada>`) e manter o leitor embutido como padrão.

---

## Plano sugerido

| ordem | item | severidade | esforço | onde (módulo / arquivo) |
|---:|---|---|---|---|
| 1 | S2: versão futura (ler `v`, preservar campos desconhecidos, bloquear gravação de cliente antigo) | média | P | `GK.sync.onSnap`, `GK.store.migrate/sanitizeRemote` |
| 2 | C2/D1: entradas de qualidade apontando para a variante; sufixo "(ouro)" no seletor | alta | M | `build.py` / `build_dataset.py`, `GK.ui.fmt.recipeLabel` |
| 3 | S1: backup do estado substituído + toast "Desfazer"; depois mesclagem por chave | alta | M | `GK.sync`, `GK.store.actions.applyRemote` |
| 4 | C1: cartões em blocos de etapas contíguas + teste de invariante | média | P/M | `GK.calc.plan`, `GK.ui.summary` |
| 5 | B1: testes JS do calc, store e sync no node | média | M | `scripts/test_calc.mjs`, `test_build.py` |
| 6 | S3 + S4: re-assinar o ouvinte, nova tentativa com jitter, evento `online` | média | P | `GK.sync.onError/flush` |
| 7 | S5: id do usuário no estado local; não enviar para outra conta | média | P | `GK.store`, `GK.sync.start` |
| 8 | F1: sprite em WebP sem perdas (ou pngquant) | média | P | `scripts/make_sprite.py`, `GK.util.setSprite` |
| 9 | U2 + U1: tokens de contraste e alvos de 44 px | média | P | CSS (`:root`, `.btn-sm`, `select`, `.edit-ico`) |
| 10 | U3: o nome não marca a caixa | média | P | `GK.ui.fmt.nameBlock`, `GK.ui.summary` |
| 11 | C3: marcação guarda a quantidade; poda em `removeGoal` | média | P | `GK.store.actions`, `GK.ui.checklist` |
| 12 | D3: nome EN secundário quando o pt colide; aviso `name-collision` | média | P | `GK.ui.search`, `GK.ui.summary`, `validate.py` |
| 13 | B2 + B4: tirar dumps, zip e artefatos gerados do git; renomear `tradução windows/` | média | P | `.gitignore`, pastas |
| 14 | U4: combobox ARIA + anúncio da contagem | média | P | `GK.ui.search` |
| 15 | F3: re-render por painel; marcar sem reconstruir | média | M | `GK.app.renderAll`, `GK.ui.*.render` |
| 16 | D2: nomes de receita derivados em pt | média | P/M | `build.py` (derived names) |
| 17 | B6: SPEC, DESIGN §4, README, `docs/atualizacao.md`, `docs/dados.md` | média | M | docs |
| 18 | U6: textos ("não oficial", "Vantagem", "receita sem ganho") | baixa | P | `GK.i18n` (dicionários) |
| 19 | F2: omitir campos padrão e sem uso no payload | baixa | P | `build.py --inject` |
| 20 | C4, D6, D7, S6, X2, X3, X5, B3, B5, U5, U8, F4, F5 | baixa | P | módulos citados em cada item |
| — | X4: decisão de licença antes de qualquer publicação aberta | alta | P | `docs/dados.md`, contato com o wikily |
