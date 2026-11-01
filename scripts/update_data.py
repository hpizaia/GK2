#!/usr/bin/env python3
"""Atualização de dados em etapas: encadeia os comandos do roteiro docs/atualizacao.md, na ordem certa.

    python3 -I scripts/update_data.py --dry-run tudo   # só lista os comandos e os passos manuais
    python3 -I scripts/update_data.py wiki montar      # o wiki foi atualizado (textos do jogo iguais)
    python3 -I scripts/update_data.py textos montar    # patch só do jogo: textos novos, wiki igual
    python3 -I scripts/update_data.py tudo             # wiki + textos + montar

Etapas (rodam sempre nesta ordem, qualquer que seja a ordem pedida):
  wiki    passo 1 do roteiro: baixa os 7 datasets em inglês (+ cópia das missões), os nomes pt-br de
          receitas e fórmulas de alquimia (para receita nova) e roda o build_dataset.py
  textos  passo 3: confere a exportação do jogo em data/game-texts/ e roda o juntar_nomes.py --atualizar
          (a exportação em si, passo 2, é no Windows)
  montar  passos 4 a 6: fatos, build só de dados, dias (só com textos novos), ícones, tecnologias,
          sprite, testes, build completo e check.py
  tudo    as três

Mostra cada comando antes de rodar e para no primeiro que sair com erro (exit ≠ 0). Não decide nada
por ninguém: o que precisa de gente (exportar no Windows, versão do wiki, nomes novos, changelog,
release, publicar) sai impresso como "passo manual", no ponto certo. Não faz commit nem push.
As etapas wiki e montar usam a rede (wikily e ícones); textos, não.
"""
import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = [sys.executable, "-I"]
STAGES = ("wiki", "textos", "montar")
EN_SLUGS = ("recipes", "items", "buildings", "crafting-stations", "technologies", "alchemy-formulas", "quests")
PT_SLUGS = ("recipes", "alchemy-formulas")   # nomes de receita em pt (passo 4 do roteiro, "Nomes de receita")


def game_versions():
    try:
        gv = json.loads((ROOT / "data" / "game-version.json").read_text(encoding="utf-8"))
        return gv.get("wiki"), gv.get("latest")
    except (OSError, ValueError):
        return None, None


# ------------------------------------------------------------------ passos que não são um comando externo

def make_dirs():
    for d in ("data/raw/days", "data/raw/pt"):
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    return 0


def copy_quests():
    shutil.copyfile(ROOT / "data/raw/api-quests-all.json", ROOT / "data/raw/days/probe-quests.json")
    return 0


def check_export():
    texts = ROOT / "data/game-texts/gk2_textos.json"
    if not texts.is_file():
        print("ERRO: falta data/game-texts/gk2_textos.json (exporte no Windows: passo 2 do roteiro)")
        return 1
    n = len(json.loads(texts.read_text(encoding="utf-8")))
    resumo = ROOT / "data/game-texts/_resumo.json"
    versao = "?"
    if resumo.is_file():
        versao = json.loads(resumo.read_text(encoding="utf-8")).get("versao_jogo") or "?"
    print(f"gk2_textos.json: {n} chaves; versão do jogo no _resumo.json: {versao} "
          f"(confira: 9.474 chaves na 1.011; a versão tem que ser a do patch)")
    return 0


# ------------------------------------------------------------------ as etapas

def cmd(*args):
    return ("cmd", list(args))


def py(script, *args):
    return ("cmd", PY + [script, *args])


def call(shown, fn):
    return ("call", shown, fn)


def manual(text):
    return ("manual", text)


def note(text):
    return ("nota", text)


def plan(stages, days):
    wiki, latest = game_versions()
    steps = []
    if "wiki" in stages:
        steps += [
            ("etapa", "wiki (passo 1 do roteiro)"),
            manual("Antes: confira na página do wiki que ele já descreve a versão nova do jogo. "
                   "Sem isso não adianta continuar."),
            cmd("git", "status", "--short"),
            call("mkdir -p data/raw/days data/raw/pt", make_dirs),
            *[py("scripts/fetch_dataset.py", s, "data/raw") for s in EN_SLUGS],
            call("cp data/raw/api-quests-all.json data/raw/days/probe-quests.json", copy_quests),
            *[py("scripts/fetch_dataset.py", s, "data/raw/pt", "--locale", "pt-br") for s in PT_SLUGS],
            py("scripts/build_dataset.py", "."),
            cmd("git", "diff", "--stat", "data/items.en.json", "data/recipes.en.json"),
            manual(f'Versão do wiki: troque "wiki" em data/game-version.json (hoje {wiki!r}; latest {latest!r}) '
                   "pela versão que o wiki descreve."),
            manual("Leia a saída do build_dataset.py acima: dangling, unmatched calc e build variants "
                   "unresolved devem estar vazios ou quase (compare com a versão anterior)."),
            manual("Calculador (opcional): receitas novas ficam com calculator_default false até "
                   "recapturar data/raw/calculator-props.json (passo 1 do roteiro)."),
        ]
    if "textos" in stages:
        steps += [
            ("etapa", "textos (passos 2 e 3 do roteiro)"),
            manual("Antes: exporte os textos no Windows com o jogo atualizado (passo 2; "
                   "tools/exportar-textos/LEIA-ME.md) e traga gk2_textos.json e _resumo.json para data/game-texts/."),
            call("conferir data/game-texts/gk2_textos.json e _resumo.json", check_export),
            py("tools/exportar-textos/juntar_nomes.py", "--atualizar"),
            cmd("git", "diff", "--stat", "data/names.official.pt-BR.json"),
            manual('Leia a saída do juntar_nomes.py: "pt alterado", "gameKey sem texto" e "conferir à mão". '
                   'Item novo sem gameKey: acrescente à mão (passo 3 do roteiro, "matched_by": "en-text").'),
            manual("Patch só do jogo (wiki igual): troque latest, date e note em data/game-version.json."),
        ]
    if "montar" in stages:
        steps += [
            ("etapa", "montar (passos 4 a 6 do roteiro)"),
            py("scripts/build_facts.py"),
            py("scripts/build.py", "--no-src"),
            py("scripts/build_days.py") if days else
            note("build_days.py pulado: os textos do jogo não mudaram nesta rodada "
                   "(use a etapa textos junto, ou --dias, para rodar)."),
            py("scripts/fetch_icons.py"),
            py("scripts/build_techs.py"),
            py("scripts/fetch_icons.py", "--techs"),
            py("scripts/make_sprite.py"),
            py("scripts/test_techs.py"),
            py("scripts/build.py"),
            py("scripts/check.py"),
            manual("data/report-build.md: 0 erros; compare os avisos com a versão anterior. "
                   "data/report-l10n.md: receita nova em inglês ganha o nome pt à mão, na camada de nomes escrita à mão "
                   '(passo 4, "Nomes de receita em português"; o cache pt já foi baixado em data/raw/pt/).'),
            manual("Veja a página: servidor dist do .claude/launch.json (http://127.0.0.1:8766/preview.html)."),
            manual("Versão, changelog, release.py, commit, push e publicar: passos 7 e 8 do roteiro, "
                   "na sessão principal, com o ok do Hugo."),
        ]
    return steps


def shown(argv):
    out = []
    for a in argv:
        if a == sys.executable:
            a = "python3"
        out.append(shlex.quote(a))
    return " ".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 epilog=__doc__.split("\n", 1)[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("etapas", nargs="+", choices=STAGES + ("tudo",), metavar="etapa",
                    help="wiki, textos, montar ou tudo (pode passar mais de uma)")
    ap.add_argument("--dry-run", action="store_true", help="só lista os comandos e os passos manuais")
    ap.add_argument("--dias", action="store_true",
                    help="roda o build_days.py no montar mesmo sem a etapa textos")
    args = ap.parse_args(argv)
    stages = set(STAGES) if "tudo" in args.etapas else set(args.etapas)
    days = args.dias or "textos" in stages
    steps = plan(stages, days)
    print(f"update_data: {', '.join(s for s in STAGES if s in stages)}"
          + (" (só listando)" if args.dry_run else "") + f"  [{ROOT}]")
    manual_steps = []
    for step in steps:
        kind = step[0]
        if kind == "etapa":
            print(f"\n=== {step[1]}")
            continue
        if kind == "manual":
            manual_steps.append(step[1])
            print(f"\n  >> passo manual: {step[1]}")
            continue
        if kind == "nota":
            print(f"\n  (nota) {step[1]}")
            continue
        line = shown(step[1]) if kind == "cmd" else step[1]
        print(f"\n$ {line}", flush=True)
        if args.dry_run:
            continue
        if kind == "cmd":
            rc = subprocess.run(step[1], cwd=ROOT).returncode
        else:
            rc = step[2]()
        if rc != 0:
            print(f"\nupdate_data: PAROU. O comando acima saiu com {rc}. Conserte e rode de novo a etapa.")
            return rc if isinstance(rc, int) and 0 < rc < 256 else 1
    print(f"\nupdate_data: {'listados' if args.dry_run else 'concluído'}. Nada foi commitado. "
          f"Passos manuais desta rodada ({len(manual_steps)}):")
    for i, text in enumerate(manual_steps, 1):
        print(f"  {i}. {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
