#!/usr/bin/env python3
"""Prepara uma versão do Companheiro GK2 até o ponto de pedir OK. Não faz commit, push nem release no GitHub.

    python3 -I scripts/release.py 1.8.5             # prepara
    python3 -I scripts/release.py 1.8.5 --dry-run   # só confere e diz o que faria

Antes: escreva a entrada no TOPO de data/changelog.json ({"version": "1.8.5", "date": null, "pt": [...], "en": [...]}).
Faz, nesta ordem: confere (branch main, versão, changelog, tag livre no GitHub, node); grava VERSION; troca só o
número da versão em site/index.html (const VERSION e #ver) e regenera site/preview.html; build.py --release
(data a entrada); check.py --release; copia dist/preview.html para companheiro-gk2-1.8.5.html e escreve as notas
da release numa pasta temporária, fora do repositório.
Depois imprime os comandos de commit, push e gh release (para rodar só com o OK do Hugo) e a lista do que só o
Claude faz (artifacts, BACKLOG, memória). Repetir o comando depois de consertar um erro é seguro.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from site_preview import set_site_version, site_preview  # noqa: E402  (as mesmas funções que o check.py usa)

ROOT = HERE.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
APP_URL = "https://claude.ai/artifact/8hp57ZZTFoH6GyDQUdHZAn"
SITE_URL = "https://claude.ai/artifact/Bgn32T3eDPRFydxYoxgWTr"
GIT_ID = '-c user.name="Hugo Pizaia" -c user.email="1241727+hpizaia@users.noreply.github.com"'


def die(msg):
    print(f"release: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print(f"release: aviso: {msg}", file=sys.stderr)


def git(*a):
    r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout.rstrip()   # rstrip: o git status --short começa com espaço


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def notes(entry):
    """Notas da release no formato da v1.8.4: PT, EN, o arquivo único e o link do app."""
    v = entry["version"]
    pt = "\n".join(f"- {s}" for s in entry["pt"])
    en = "\n".join(f"- {s}" for s in entry["en"])
    return (f"**PT**\n{pt}\n\n**EN**\n{en}\n\nArquivo único / single file: companheiro-gk2-{v}.html "
            f"(abra no navegador). App: {APP_URL}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("version", help="X.Y.Z (a mesma do topo de data/changelog.json)")
    ap.add_argument("--dry-run", action="store_true", help="só confere; não grava nada")
    args = ap.parse_args(argv)
    v = args.version
    if not SEMVER.match(v):
        die(f"versão {v!r} não é X.Y.Z")

    # ---- conferências antes de mexer em qualquer arquivo
    _, branch = git("branch", "--show-current")
    if branch != "main":
        die(f"o branch atual é {branch!r}; a release sai da main")
    cur = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if vtuple(v) < vtuple(cur):
        die(f"{v} é menor que a VERSION atual {cur}")
    top = json.loads((ROOT / "data" / "changelog.json").read_text(encoding="utf-8"))[0]
    if top["version"] != v:
        die(f"o topo de data/changelog.json é {top['version']}, não {v}. Acrescente no topo:\n"
            f'  {{"version": "{v}", "date": null, "pt": ["..."], "en": ["..."]}}')
    if top.get("date") is not None and v != cur:
        die(f"a entrada {v} já tem data {top['date']}; deixe \"date\": null (o build --release data)")
    if not top.get("pt") or not top.get("en"):
        die("a entrada do changelog precisa de frases em pt e en")
    if len(top["pt"]) != len(top["en"]):
        warn(f"{len(top['pt'])} frase(s) em pt e {len(top['en'])} em en")
    rc, tags = git("ls-remote", "--tags", "origin", f"refs/tags/v{v}")
    if rc != 0:
        warn("não consegui consultar as tags do GitHub (sem rede?); confira antes do gh release")
    elif tags:
        die(f"a tag v{v} já existe no GitHub")
    if not shutil.which("node"):
        die("node não encontrado (os testes de JavaScript não rodariam)")
    if not shutil.which("gh"):
        warn("gh não encontrado; o gh release create impresso no fim vai precisar dele")
    site_idx = ROOT / "site" / "index.html"
    try:
        new_site = set_site_version(site_idx.read_text(encoding="utf-8"), v)
    except ValueError as e:
        die(str(e))
    if args.dry_run:
        print(f"release (dry-run): {cur} → {v}; changelog ok; tag livre. Gravaria VERSION, a versão do site "
              f"e site/preview.html, rodaria build.py --release e check.py --release.")
        return 0

    # ---- arquivos versionados (tudo aparece no git diff)
    (ROOT / "VERSION").write_text(v + "\n", encoding="utf-8")
    site_idx.write_text(new_site, encoding="utf-8")
    (ROOT / "site" / "preview.html").write_text(site_preview(new_site), encoding="utf-8")
    py = [sys.executable, "-I"]
    if subprocess.run(py + ["scripts/build.py", "--release"], cwd=ROOT).returncode != 0:
        die("build.py --release falhou (veja data/report-build.md). Conserte e rode este comando de novo")
    if subprocess.run(py + ["scripts/check.py", "--release"], cwd=ROOT).returncode != 0:
        die("check.py --release falhou. Conserte e rode este comando de novo")

    # ---- arquivo da release e notas, fora do repositório
    out = Path(tempfile.mkdtemp(prefix=f"gk2-release-{v}-"))
    asset = out / f"companheiro-gk2-{v}.html"
    shutil.copy2(ROOT / "dist" / "preview.html", asset)
    notes_file = out / "notas.md"
    entry = json.loads((ROOT / "data" / "changelog.json").read_text(encoding="utf-8"))[0]
    notes_file.write_text(notes(entry), encoding="utf-8")
    _, status = git("status", "--short")

    print(f"""
==================== v{v} pronta para conferir ====================
Arquivos alterados:
{status}

Arquivo da release e notas (pasta temporária, some ao reiniciar):
  {asset}
  {notes_file}

Só com o OK do Hugo, nesta ordem (o gh release só depois do push, senão a tag nasce no commit errado):
  git add -A && git status --short          # historico/ e docs/revisao-ux/ não podem aparecer
  git {GIT_ID} commit -m "Companheiro GK2 v{v}: <resumo>"     # + a linha Co-Authored-By do Claude
  git push
  gh release create v{v} "{asset}" --title "Companheiro GK2 v{v}" --notes-file "{notes_file}" --target main

Só o Claude (Artifact tool), depois do push:
  [ ] app:  republicar dist/index.html em {APP_URL} (ler a versão publicada antes; NÃO passar capabilities)
  [ ] site: listar os arquivos publicados de {SITE_URL} e republicar site/index.html (só a versão mudou)
  [ ] abrir os dois e conferir v{v} no rodapé
  [ ] docs/projeto/BACKLOG.md (linha "Publicado") + commit "Backlog: {v} publicada" + push
  [ ] notas internas (fora do git) e memória do projeto
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
