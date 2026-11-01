#!/usr/bin/env python3
"""Um comando só para saber se o projeto está pronto para commit ou publicação.

    python3 -I scripts/check.py             # tudo (~6 s); exit 0 só se nada FALHOU
    python3 -I scripts/check.py --release   # + exige changelog datado e nenhum teste pulado (data/raw/ presente)

Confere: versões (VERSION, topo de data/changelog.json, `const VERSION` e #ver do site), build reprodutível,
site/preview.html, data/days.json, os 3 testes (test_build.py, test_techs.py, test_calc.mjs), que nenhum arquivo
versionado cite as pastas internas (docs/revisao-ux/, historico/) e o e-mail do git.
Uma linha por conferência (ok / AVISO / FALHA); embaixo, o log só de quem falhou. Exit 1 se houver FALHA.

Não grava nada no repositório: o build roda numa pasta temporária (apagada no fim) e é comparado byte a byte
com o que está no disco. Não use com `| tail`: a saída já é um resumo, e o pipe esconde o código de saída.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True   # importar build_days/site_preview não deixa __pycache__ para trás
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from site_preview import site_preview, site_versions  # noqa: E402

ROOT = HERE.parent
PY = [sys.executable, "-I"]
GIT_EMAIL = "1241727+hpizaia@users.noreply.github.com"


def sh(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def read(p):
    return (ROOT / p).read_text(encoding="utf-8")


# ------------------------------------------------------------------ conferências
# cada uma devolve (estado, resumo, log): estado True = ok, None = AVISO, False = FALHA

def check_versions(release):
    v = read("VERSION").strip()
    top = json.loads(read("data/changelog.json"))[0]
    js, span = site_versions(read("site/index.html"))
    bad = []
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        bad.append(f"VERSION {v!r} não é X.Y.Z")
    if top["version"] != v:
        bad.append(f"VERSION {v} ≠ topo do changelog {top['version']}")
    if not top.get("pt") or not top.get("en"):
        bad.append("topo do changelog sem frases em pt ou en")
    if js != [v] or span != [v]:
        bad.append(f"site/index.html: const VERSION={js}, #ver={span}, esperado [{v!r}]")
    if release and top.get("date") is None:
        bad.append("topo do changelog ainda sem data (rode build.py --release)")
    return not bad, "; ".join(bad) or f"versão {v}", ""


def check_build():
    """build.py numa cópia temporária, com o mesmo meta.built, tem que reproduzir os arquivos do disco.

    Sem lista de saídas: a pasta temporária recebe src/, VERSION e os arquivos soltos de data/ (as entradas do
    projeto: changelog, techs, days, sprite...; as camadas de nomes e os dados brutos o build lê direto do
    repositório). Depois do build, TODO arquivo da pasta temporária (fora src/) tem que ser igual ao do
    repositório: o que o build gerou ou reescreveu e não bate é diferença. Se o build passar a ler outra
    entrada do projeto fora de data/, a saída muda e a conferência falha (no sentido seguro)."""
    built = json.loads(read("data/gk2.json"))["meta"]["built"]
    tmp = Path(tempfile.mkdtemp(prefix="gk2-check-"))
    try:
        shutil.copytree(ROOT / "src", tmp / "src")
        shutil.copy2(ROOT / "VERSION", tmp / "VERSION")
        (tmp / "data").mkdir()
        for f in (ROOT / "data").iterdir():
            if f.is_file():
                shutil.copy2(f, tmp / "data" / f.name)
        rc, log = sh(PY + ["scripts/build.py", "--src", str(tmp / "src"), "--out-dir", str(tmp / "data"),
                           "--built", built])
        if rc != 0:
            return False, f"build.py saiu com {rc}", log
        gen = [p.relative_to(tmp) for p in tmp.rglob("*") if p.is_file() and p.relative_to(tmp).parts[0] != "src"]
        if not any(p.parts[0] == "dist" for p in gen):
            return False, "o build não gerou dist/ (mudou a interface do build.py?)", log
        diff = sorted(str(p) for p in gen
                      if not (ROOT / p).is_file() or (ROOT / p).read_bytes() != (tmp / p).read_bytes())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if diff:
        return False, ("o build gera arquivos diferentes dos do disco: " + ", ".join(diff)
                       + f"  → rode: python3 -I scripts/build.py --built {built}"), ""
    return True, f"dist/, prototype/, data/ e CHANGELOG.md batem com src/ + data/ (built {built})", ""


def check_site_preview():
    ok = site_preview(read("site/index.html")) == read("site/preview.html")
    return ok, ("site/preview.html em dia" if ok
                else "site/preview.html desatualizado  → rode: python3 -I scripts/site_preview.py"), ""


def check_days():
    import build_days  # noqa: E402  (lê data/game-texts/gk2_textos.json e data/gk2.json, não grava)
    disk = json.loads(read("data/days.json"))
    ok = build_days.build(disk["meta"]["built"]) == disk
    return ok, ("data/days.json em dia" if ok else
                f"data/days.json desatualizado  → rode: python3 -I scripts/build_days.py --date {disk['meta']['built']}"), ""


def check_test(cmd, release, hint=""):
    if cmd[0] == "node" and not shutil.which("node"):
        return False, "node não encontrado (instale o Node para rodar os testes de JavaScript)", ""
    rc, log = sh(cmd)
    m = re.search(r"Ran \d+ tests?", log) or re.search(r"\d+ checks passed, \d+ failed", log)
    count = m.group(0) if m else "?"
    if rc != 0:
        return False, f"exit {rc} — {count}", log
    skipped = re.search(r"skipped=(\d+)", log)
    if skipped:
        # passou, mas não testou tudo: aviso no dia a dia, falha na publicação
        return (False if release else None), f"{count}, {skipped.group(1)} pulado(s){hint}", log
    return True, count, ""


# Pastas internas (fora do git, CLAUDE.md regra 3): um arquivo versionado não aponta para nada lá dentro, porque
# quem clona o repositório não tem essas pastas. A busca é por texto, em cada linha.
INTERNAL = ("docs/revisao-ux/", "historico/")
# Únicos lugares que podem citar as pastas: os que dizem que elas são internas ou as mantêm fora do git.
# {arquivo: trechos}: com None, o arquivo inteiro; senão, só as linhas que contêm um dos trechos.
INTERNAL_OK = {
    ".gitignore": None,                    # é quem tira as pastas do git
    "CLAUDE.md": None,                     # a regra 3 e o mapa das pastas
    ".claude/agents/gk2-worker.md": None,  # as mesmas regras, para os agentes
    "scripts/git-hooks/pre-push": None,    # a trava do push lista os caminhos proibidos
    "scripts/check.py": None,              # esta conferência
    "docs/README.md": ("está no `.gitignore`", "Fora do repositório público"),
    "docs/arquitetura.md": ("está no `.gitignore`",),
    "docs/atualizacao.md": ("não devem aparecer", "está no `.gitignore`"),
    "scripts/release.py": ("não podem aparecer",),
}


def tracked_files():
    """Arquivos versionados + novos que o .gitignore não tira (os que entrariam num `git add -A`)."""
    rc, out = sh(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"])
    if rc != 0:
        raise RuntimeError("git ls-files falhou: " + out.strip()[:200])
    return sorted({f for f in out.split("\0") if f and (ROOT / f).is_file()})


def check_internal_refs():
    hits = []
    for f in tracked_files():
        ok = INTERNAL_OK.get(f, ())
        if ok is None:
            continue
        try:
            text = (ROOT / f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue   # binário
        for n, ln in enumerate(text.splitlines(), 1):
            if any(s in ln for s in INTERNAL) and not any(s in ln for s in ok):
                hits.append(f"{f}:{n}: {ln.strip()[:160]}")
    if hits:
        return False, (f"{len(hits)} linha(s) citam {' ou '.join(INTERNAL)} (pasta interna, fora do git); "
                       "tire a citação ou, se a linha só descreve a pasta, ponha em INTERNAL_OK"), "\n".join(hits)
    return True, f"nenhum arquivo versionado cita {' ou '.join(INTERNAL)}", ""


def check_identity():
    _, email = sh(["git", "config", "user.email"])
    email = email.strip()
    if email == GIT_EMAIL:
        return True, f"git user.email = {email}", ""
    return None, f"git user.email = {email or '(vazio)'}; esperado {GIT_EMAIL} (use git -c user.email=... no commit)", ""


def failure_lines(log):
    """Só o que interessa do log de quem falhou."""
    lines = log.rstrip().splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("=" * 20):   # unittest: os blocos FAIL/ERROR começam numa linha de "="
            return lines[i:][-60:]
    # tira as linhas que passaram ("... ok" do unittest, "ok ..." do test_calc); num teste pulado, mostra os pulos
    lines = [ln for ln in lines if not (ln.endswith(" ... ok") or ln.startswith("ok "))]
    skips = [ln for ln in lines if "skipped" in ln]
    return (skips or lines)[-40:]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--release", action="store_true",
                    help="regras de publicação: changelog datado e nenhum teste pulado")
    args = ap.parse_args(argv)
    raw_hint = "" if (ROOT / "data" / "raw").is_dir() else ": falta data/raw/ (fica fora do git)"
    node_hint = "" if shutil.which("node") else ": falta node"
    steps = [
        ("versões", lambda: check_versions(args.release)),
        ("build reprodutível", check_build),
        ("site/preview.html", check_site_preview),
        ("days.json", check_days),
        ("test_build.py", lambda: check_test(PY + ["scripts/test_build.py"], args.release, node_hint or raw_hint)),
        ("test_techs.py", lambda: check_test(PY + ["scripts/test_techs.py"], args.release, raw_hint)),
        ("test_calc.mjs", lambda: check_test(["node", "scripts/test_calc.mjs"], args.release)),
        ("citação interna", check_internal_refs),
        ("identidade git", check_identity),
    ]
    results, t0 = [], time.time()
    for name, fn in steps:
        t = time.time()
        try:
            ok, msg, log = fn()
        except Exception as e:  # noqa: BLE001  (uma conferência quebrada é uma FALHA, não um traceback)
            ok, msg, log = False, f"erro: {e!r}", ""
        results.append((name, ok, msg, log, time.time() - t))
    print()
    for name, ok, msg, _, dt in results:
        tag = "ok   " if ok else ("AVISO" if ok is None else "FALHA")
        print(f"  {tag}  {name:<20} {dt:4.1f}s  {msg}")
    failed = [r for r in results if r[1] is False]
    for name, _, _, log, _ in failed:
        lines = failure_lines(log)
        if lines:
            print(f"\n----- {name}: últimas linhas -----\n" + "\n".join(lines))
    warns = sum(1 for r in results if r[1] is None)
    verdict = f"{len(failed)} FALHA(S)" if failed else ("TUDO OK" if not warns else f"ok, com {warns} AVISO(S)")
    print(f"\ncheck{' --release' if args.release else ''}: {verdict} em {time.time() - t0:.1f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
