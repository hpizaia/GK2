# docs/media/: imagens dos READMEs e do guia

Capturas e GIFs usados no [`README.md`](../../README.md) (inglês), no [`README.pt-BR.md`](../../README.pt-BR.md) e no [`docs/guia-de-uso.md`](../guia-de-uso.md). As imagens da página de apresentação ficam em `site/media/` (veja o [`site/README.md`](../../site/README.md)). O sufixo `-pt` / `-en` diz o idioma do app na captura. Celular: viewport 375×812; computador: 1440×900 (as versões grandes, em 2x).

Todas as capturas e GIFs em uso foram regravados na v1.8.4 (01/11/2026) com o plano de exemplo Colmeia ×2, Vinho ×4 e Espada de Ferro ×3 (Areia já marcada, Dia da Ira, dia 61); como foram feitos: [`site/README.md`](../../site/README.md). Os PNG de celular são capturados em 2x, reduzidos para 375 px e passados no `pngquant`; os GIFs têm 96 cores sem pontilhado.

Antes de apagar ou renomear um arquivo, procure o nome dele nos `.md` (`git grep nome-do-arquivo`).

## Em uso

| arquivo | tamanho | o que mostra | onde é usada |
|---|---|---|---|
| `hero-en.gif` | 390×844 | Buscar uma espada, adicionar às metas, marcar a Areia como "já tenho" e descer até as etapas (inglês). Cópia idêntica de `site/media/hero-en.gif` | `README.md` (topo) |
| `gif-search-add-goal-pt.gif` | 360×780 | O mesmo percurso, em português. Cópia idêntica de `site/media/hero-pt.gif` | `README.pt-BR.md` (topo), `guia-de-uso.md` |
| `planner-overview-phone-en.png` | 375×812 | Planejador com a linha Hoje, três metas e as matérias-primas (inglês) | `README.md`; `README.pt-BR.md` (comparação de idiomas) |
| `planner-overview-phone-pt.png` | 375×812 | O mesmo, em português | `README.pt-BR.md` |
| `planner-steps-phone-pt.png` | 375×812 | Etapas por estação com o seletor "Por execução" de cada receita | `README.md`, `README.pt-BR.md` |
| `gif-have-n-of-m-pt.gif` | 360×780 | Tocar no "× 9 ▾" do Minério de Ferro, dizer "tenho 5" e depois marcar a caixinha da Vareta (vai para "Você já tem") | `README.md`, `README.pt-BR.md`, `guia-de-uso.md` |
| `gif-collapse-sections-pt.gif` | 360×780 | Recolher o painel Hoje, as matérias-primas, duas estações e as etapas (aparece Tecnologias que faltam) | `README.md`, `README.pt-BR.md` |
| `tech-needs-phone-pt.png` | 375×812 | Painel "Tecnologias que faltam" com a soma de pontos por cor | `README.md`, `README.pt-BR.md`, `guia-de-uso.md` |
| `recipe-detail-phone-pt.png` | 375×812 | Detalhe do Vinho (bronze): estrela de qualidade, onde conseguir, quem compra (moedas) e estudo | `README.md`, `README.pt-BR.md`, `guia-de-uso.md` |
| `tech-tree-phone-pt.png` | 375×812 | Árvore de tecnologias, ramo Engenharia (12 de 52 pesquisadas, colunas completas recolhidas) | `README.md`, `README.pt-BR.md`, `guia-de-uso.md` |
| `days-wheel-phone-pt.png` | 375×812 | Roda da semana (aba Dias) | `guia-de-uso.md` |
| `gif-days-wheel-today-pt.gif` | 360×780 | Tocar um dia na roda, confirmar como hoje e ver o painel Hoje no Planejador | `README.md`, `README.pt-BR.md`, `guia-de-uso.md` |
| `planner-materials-phone-en.png` | 375×812 | Matérias-primas em inglês | `README.md` (comparação de idiomas) |
| `planner-light-phone-pt.png` | 375×812 | Planejador no tema claro (pergaminho) | `README.md`, `README.pt-BR.md` |
| `planner-desktop-dark-pt-small.png` | 1440×900 | Layout de computador: metas, matérias-primas e etapas lado a lado (tema escuro) | `README.md`, `README.pt-BR.md` |

## Fora dos READMEs

Nenhum `.md` do repositório aponta para estes arquivos:

| arquivo | tamanho | o que é |
|---|---|---|
| `gif-reddit-demo-en.gif`, `reddit-demo-en.mp4` | 540 px / 720 px de largura, ~18 s | Clipe de demonstração em inglês feito para o post no Reddit. Como foi gravado: [`README-reddit-demo.md`](README-reddit-demo.md) |
| `social-preview.png` | 1280×640 | Imagem de prévia para links (o tamanho que o GitHub pede em Settings → Social preview, onde ela é enviada à mão) |

Removidos em 31/10/2026 (ficam no histórico do git, commit anterior a este): `planner-desktop-dark-pt.png` e `planner-desktop-light-pt.png`, os originais em 2x (2,3 e 2,0 MB) da captura de computador; a versão usada nos READMEs é a `-small`.
