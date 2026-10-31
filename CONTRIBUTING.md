# Contributing to GK2 Companion

**English** · [Português](#português)

Thanks for helping. The most useful contributions need no code at all: telling us where a name, a day event or a quantity is wrong.

Opening an issue needs a free GitHub account. **No account?** Leave a comment on the project's Reddit post or on the [project site](https://claude.ai/artifact/Bgn32T3eDPRFydxYoxgWTr) instead; that works too.

## Report a wrong name or translation

Every item name can be corrected inside the app, and the app can hand you your corrections as JSON.

1. Next to the wrong name, tap the pencil **✎**, type the right name and tap **Save**. The name gets an *edited* tag and is used on every screen (for the language you are using).
2. In the planner's **Progress** card, tap **Export edited names (N)**. The JSON is copied to your clipboard (if copying is blocked, it is shown selected so you can copy it by hand).
3. Open an issue with the **Wrong name or data** template and paste the JSON. It looks like this:

```json
{
  "Iron Sword": { "pt": "Espada de Ferro", "source": "user", "confidence": "guess" }
}
```

The key is the exact English name from the wiki, which is what the names files in `data/` use, so a maintainer can merge it directly. Names tagged *unofficial* are the best candidates: they did not come from the game files.

## Report a wrong day event

The **Days** tab lists what happens on each of the 6 weekdays. Events marked *unconfirmed* come from guides, not from the game text. If you see something different in the game, open an issue with the **Day event** template and include:

- the day (symbol or name) and the in-game day counter,
- what happened, or did not happen,
- your game version (main menu) and, ideally, a screenshot.

The events live in the `EVENTS` table of `scripts/build_days.py`.

## Report a wrong recipe or quantity

Recipes come from the [wikily.gg Graveyard Keeper 2 wiki](https://wikily.gg/graveyard-keeper-2) (game 1.010). Open an issue with the **Wrong name or data** template: the item, what the app shows, what the game shows and your game version. If a recipe is wrong on the wiki too, please also tell the wiki. Known limits are listed under "Lacunas conhecidas" in [`docs/dados.md`](docs/dados.md) (quality variants, alchemy mixes, farming yields).

## Report a bug

Use the **Bug** template. Say what you did, what you expected and what happened, plus phone or desktop, browser, language, and the version shown in the footer.

## Code

Requirements: Python 3 (standard library only); Node for the JavaScript tests.

```sh
python3 -I scripts/build.py           # rebuild after any change in src/ or data/
python3 -I scripts/test_build.py      # build and validation tests
python3 -I scripts/test_techs.py      # technology tree tests
node scripts/test_calc.mjs            # planner maths, storage and sync tests
```

- **Edit `src/`, never `dist/` or `prototype/`**: they are regenerated on every build.
- One feature = one module (`src/js/ui/<name>.js`, optional CSS), listed in `src/manifest.json`, with its own i18n strings, route and panel. The contract is in [`scripts/README-build.md`](scripts/README-build.md#adding-a-module-the-contract-for-parallel-work); each file starts with a comment saying what it owns and exposes.
- Every user-facing string goes through `GK.i18n.add` in **both** `pt` and `en`.
- No new runtime dependencies: the page must stay a single self-contained HTML file that works inside a Claude Artifact (no external images, scripts only from allowed CDNs with pinned versions).
- User-visible changes get a short line, in `pt` and `en`, in the top entry of `data/changelog.json`. `CHANGELOG.md` is generated.
- Architecture and data docs (Portuguese): [`docs/arquitetura.md`](docs/arquitetura.md), [`docs/dados.md`](docs/dados.md).

By contributing code or docs you agree that your contribution is published under the project's code licence, **MIT** (see [`LICENSE`](LICENSE)). The licence covers the code only: the game data, names, icons and screenshots are not covered (see the scope notice in [`LICENSE`](LICENSE) and [`docs/dados.md`](docs/dados.md)). Name corrections you send are added to the name files in `data/`, which follow the same rules as the rest of the game data.

---

## Português

Obrigado por ajudar. As contribuições mais úteis não precisam de código: dizer onde um nome, um evento do dia ou uma quantidade está errado.

Abrir uma issue exige uma conta gratuita no GitHub. **Sem conta?** Deixe um comentário no post do projeto no Reddit ou no [site do projeto](https://claude.ai/artifact/Bgn32T3eDPRFydxYoxgWTr); também vale.

### Nome ou tradução errada

Todo nome de item pode ser corrigido dentro do app, e o app entrega as suas correções em JSON.

1. Ao lado do nome errado, toque no lápis **✎**, digite o nome certo e toque em **Salvar**. O nome ganha o selo *editado* e vale em todas as telas (no idioma em uso).
2. No cartão **Progresso** do Planejador, toque em **Exportar nomes editados (N)**. O JSON vai para a área de transferência (se não der para copiar, ele aparece selecionado para você copiar à mão).
3. Abra uma issue com o modelo **Nome ou dado errado** e cole o JSON (formato no exemplo acima). A chave é o nome inglês exato da wiki, o mesmo usado nos arquivos de nomes em `data/`.

Os nomes com o selo *não oficial* são os melhores candidatos: eles não vieram dos arquivos do jogo.

### Evento do dia errado

A aba **Dias** lista o que acontece em cada um dos 6 dias da semana. Os eventos com o selo *não confirmado* vêm de guias, não do texto do jogo. Se no jogo for diferente, abra uma issue com o modelo **Evento do dia** dizendo:

- o dia (símbolo ou nome) e o número do dia no contador do jogo,
- o que aconteceu, ou não aconteceu,
- a versão do jogo (menu principal) e, se der, uma captura de tela.

Os eventos ficam na tabela `EVENTS` do `scripts/build_days.py`.

### Receita ou quantidade errada

As receitas vêm da [wiki wikily.gg do Graveyard Keeper 2](https://wikily.gg/graveyard-keeper-2) (jogo 1.010). Abra uma issue com o modelo **Nome ou dado errado**: o item, o que o app mostra, o que o jogo mostra e a versão do jogo. Se estiver errado na wiki também, avise a wiki. Os limites conhecidos estão em "Lacunas conhecidas" no [`docs/dados.md`](docs/dados.md).

### Bug

Use o modelo **Bug**: o que você fez, o que esperava e o que aconteceu, mais celular ou computador, navegador, idioma e a versão que aparece no rodapé.

### Código

Os comandos e as regras são os da seção [Code](#code) acima: edite `src/` (nunca `dist/` nem `prototype/`), um módulo por função seguindo o contrato do [`scripts/README-build.md`](scripts/README-build.md#adding-a-module-the-contract-for-parallel-work), todo texto em `pt` e `en` via `GK.i18n.add`, nenhuma dependência nova, e uma linha no topo do `data/changelog.json` para cada mudança visível. Rode os quatro comandos de teste antes de mandar.

Ao contribuir com código ou documentação, você concorda que a sua contribuição seja publicada sob a licença do código do projeto, **MIT** (veja o [`LICENSE`](LICENSE)). A licença cobre só o código: os dados do jogo, os nomes, os ícones e as capturas de tela não estão cobertos (veja o aviso de escopo no [`LICENSE`](LICENSE) e o [`docs/dados.md`](docs/dados.md)). As correções de nomes que você mandar entram nos arquivos de nomes em `data/`, que seguem as mesmas regras do resto dos dados do jogo.
