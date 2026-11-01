# docs/: índice dos documentos

Um documento por linha, com o que ele responde. Os documentos de `docs/` são em português, menos o `duplicate.md` (inglês) e o `DESIGN.md` (notas em inglês).

## Nesta pasta

| arquivo | para quem | o que tem |
|---|---|---|
| [`guia-de-uso.md`](guia-de-uso.md) | quem joga | Como usar o app: Planejador, Receitas, Tecnologias, Dias, nomes, idioma, tema, sincronização |
| [`arquitetura.md`](arquitetura.md) | quem mexe no código | Pastas do repositório, pipeline de build, telas e módulos, limites do Claude Artifact, camadas de nomes |
| [`dados.md`](dados.md) | quem mexe nos dados | De onde vêm os dados, direitos de uso, modelo de dados, camadas de tradução, lacunas conhecidas |
| [`atualizacao.md`](atualizacao.md) | quem mantém | Roteiro passo a passo quando o jogo recebe um patch: dados, nomes, ícones, build, versão, publicação |
| [`duplicar.md`](duplicar.md) | quem quer a própria cópia | Como fazer a sua versão (outro artifact, site estático, outro idioma, outro jogo) |
| [`duplicate.md`](duplicate.md) | *idem, em inglês* | Mesmo conteúdo do `duplicar.md`. Os dois são PT/EN de propósito: mude os dois juntos |

## Subpastas

| pasta | o que tem | git |
|---|---|---|
| [`projeto/`](projeto/) | Documentos de projeto: [`SPEC.md`](projeto/SPEC.md) (especificação), [`DESIGN.md`](projeto/DESIGN.md) (design visual e de interface), [`BACKLOG.md`](projeto/BACKLOG.md) (pendências), [`AUDITORIA.md`](projeto/AUDITORIA.md) (auditoria da v1.1, histórica), [`PLANO-UI-JOGO.md`](projeto/PLANO-UI-JOGO.md) (sinais do jogo na interface, em espera). O status do projeto fica na seção "Onde estamos" do `BACKLOG.md` | sim |
| [`media/`](media/) | Imagens e GIFs dos READMEs e do guia de uso. O que é cada arquivo e onde é usado: [`media/README.md`](media/README.md) | sim |
| `revisao-ux/` | Relatórios internos (revisões, QA, pesquisas) e capturas. Interno: fica só no disco local | não (está no `.gitignore`) |

## Documentos em outras pastas

| arquivo | o que tem |
|---|---|
| [`../README.md`](../README.md), [`../README.pt-BR.md`](../README.pt-BR.md) | Apresentação do projeto no GitHub (inglês e português) |
| [`../CLAUDE.md`](../CLAUDE.md) | Regras e comandos para o Claude Code neste projeto (testes, release, armadilhas, decisões que não se reabrem) |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Como relatar nome, evento do dia, receita ou bug, e as regras para quem manda código |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Histórico de versões. **Gerado** pelo `build.py` a partir de `data/changelog.json`: não edite à mão |
| [`../scripts/README.md`](../scripts/README.md) | Tabela de todos os scripts: o que fazem, quando rodar, entradas e saídas. Inclui `check.py` (testes e conferências num comando só) e `release.py` (fechar uma versão) |
| [`../scripts/shots/README.md`](../scripts/shots/README.md) | Capturas de tela e comparação do app antes/depois, pixel a pixel |
| [`../scripts/README-build.md`](../scripts/README-build.md) | Referência técnica do `build.py` (inglês): opções, schema do `gk2.json`, contrato dos módulos de `src/`, validação |
| [`../data/README-data.md`](../data/README-data.md) | Dataset de receitas e itens do wikily (inglês): arquivos, contagens, schema, `facts.json`, lacunas |
| [`../data/README-l10n.md`](../data/README-l10n.md) | As 3 camadas de nomes pt-BR (`names.official`, `names.manual`, `names.machine`), a regra e a pesquisa das fontes (inglês) |
| [`../data/README-machine-l10n.md`](../data/README-machine-l10n.md) | Camada de tradução de máquina `names.machine.pt-BR.json` (inglês) |
| [`../data/README-techs.md`](../data/README-techs.md) | Árvore de tecnologias `techs.json` (inglês) |
| [`../data/README-days.md`](../data/README-days.md) | Semana de 6 dias `days.json`, a aba Dias (inglês) |
| `../data/report-build.md`, `../data/report-l10n.md` | Relatórios **gerados** a cada build: erros e avisos, nomes que faltam traduzir |
| [`../data/game-texts/RELATORIO-exportacao.md`](../data/game-texts/RELATORIO-exportacao.md) | Relatório da exportação dos textos oficiais do jogo (versão 1.011) |
| [`../tools/README.md`](../tools/README.md) | O que há em `tools/` |
| [`../tools/exportar-textos/LEIA-ME.md`](../tools/exportar-textos/LEIA-ME.md) | Passo a passo, para leigos, de como exportar os textos do jogo no Windows |
| [`../site/README.md`](../site/README.md) | Página de apresentação do projeto (inglês): imagens, publicação |
| [`../prototype/README.md`](../prototype/README.md) | O que é o `prototype/index.html` (gerado) |
| [`../.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/) | Modelos de issue: bug, nome ou dado errado, evento do dia |

Fora do repositório público: `historico/` (transcrições e arquivos de sessões, no repositório privado `hpizaia/GK2-historico`) e `docs/revisao-ux/`.
