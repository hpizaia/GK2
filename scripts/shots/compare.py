#!/usr/bin/env python3
"""Prova de que o jogador vê exatamente o mesmo: compara o app de uma ref do git com o da árvore de trabalho.

    python3 -I scripts/shots/compare.py                 # HEAD:dist/preview.html × dist/preview.html (~30 s)
    python3 -I scripts/shots/compare.py --ref v1.8.4    # outra ref (commit, tag, branch)
    python3 -I scripts/shots/compare.py --filtro receitas,busca   # só os casos com esses trechos no nome
    python3 -I scripts/shots/compare.py --tolerancia 1  # diferença de até 1/255 por canal conta como igual (e é contada)
    python3 -I scripts/shots/compare.py --antes ARQ.html  # um arquivo no lugar da ref (o mesmo dos dois lados: 0 pixel)
    python3 -I scripts/shots/compare.py --only-capture  # só captura o dist/preview.html atual (prints para ver)

Rode o build antes (python3 -I scripts/build.py --built AAAA-MM-DD): compara o dist/preview.html do disco.
Abre as duas páginas nos mesmos casos (scripts/shots/casos.json) com scripts/shots/capture.mjs (Chrome headless,
sem servidor) e compara, caso a caso: os pixels da página inteira, o HTML e o texto do que está visível, o estado
do app e os erros de JS; e, uma vez, o resumo do GK.data (pega dado que mudou sem aparecer na tela).
Uma linha por caso (igual / DIFERENTE / ERRO; o DIFERENTE diz a maior diferença de cor por canal, "máx 1/255"
é invisível); exit 0 só se tudo for igual. Padrão --tolerancia 0 (exato): é o que vale para refatorar.

Saída (fora do git, apagada a cada rodada): .shots/compare/ com antes/, depois/ (PNG, HTML, texto e JSON de cada
caso) e diferencas/ (imagem com os pixels diferentes em vermelho e o diff do HTML e do texto de cada caso diferente).
Com --only-capture: .shots/capturas/. Precisa de node e do Google Chrome (variável CHROME para outro caminho).
"""
import argparse
import difflib
import json
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAGINA = "dist/preview.html"
TEMPO = 300   # segundos: o capture.mjs fecha o Chrome e sai sozinho; o Python só garante


def die(msg):
    print(f"compare: {msg}", file=sys.stderr)
    sys.exit(2)


def rodar_capture(argumentos):
    """Roda o capture.mjs; num Ctrl-C ou estouro de tempo, termina o node (que fecha o Chrome)."""
    if not shutil.which("node"):
        die("node não encontrado")
    cmd = ["node", str(HERE / "capture.mjs"), "--tempo-limite", str(TEMPO), *argumentos]
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log = []
    try:
        for linha in p.stdout:
            log.append(linha.rstrip("\n"))
            if linha.startswith(("ERRO", "AVISO")) or not linha.startswith("capturado"):
                print("  " + linha.rstrip("\n"))
        p.wait(timeout=TEMPO + 30)
    except (KeyboardInterrupt, subprocess.TimeoutExpired):
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
        raise
    finally:
        if p.stdout:
            p.stdout.close()
    return p.returncode, log


def ler(p):
    return p.read_text(encoding="utf-8") if p.is_file() else None


ENTRE_TAGS = re.compile(r">\s+<")


def html_normal(s):
    """O HTML sem o espaço em branco entre tags (indentação, linhas vazias): só ele mudar não muda a tela (os
    pixels e o texto pegam o caso raro em que muda). Texto dentro das tags e atributos ficam como estão."""
    return None if s is None else ENTRE_TAGS.sub(">\n<", s)


def ler_json(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def onde(px, info, escala):
    """"y 120–340 (painel summary)": a caixa dos pixels diferentes, em px CSS, e os painéis menores que ela toca."""
    x0, y0, x1, y1 = (round(v / escala) for v in px["caixa"])
    toca = []
    for c in (info or {}).get("caixas", []):
        if c["x"] <= x1 and c["x"] + c["w"] >= x0 and c["y"] <= y1 and c["y"] + c["h"] >= y0:
            toca.append((c["w"] * c["h"], c["nome"]))
    nomes = [n for _, n in sorted(toca)[:2]]
    return f"x {x0}–{x1}, y {y0}–{y1}" + (f" ({', '.join(nomes)})" if nomes else "")


def diff_texto(a, b, nome_a, nome_b):
    return "".join(difflib.unified_diff(a.splitlines(True), b.splitlines(True), nome_a, nome_b, n=2))


def primeira_linha_diferente(a, b):
    for i, (x, y) in enumerate(zip(a.splitlines(), b.splitlines()), 1):
        if x != y:
            return i
    return min(len(a.splitlines()), len(b.splitlines())) + 1


def comparar_dados(a, b):
    """O resumo do GK.data (dados.json) das duas páginas: o que mudou, em poucas palavras."""
    if a is None or b is None:
        return ["sem resumo do GK.data de um dos lados"]
    out = []
    if a.get("meta") != b.get("meta"):
        out.append(f"meta {a.get('meta')} → {b.get('meta')}")
    for k in sorted(set(a["chaves"]) | set(b["chaves"])):
        x, y = a["chaves"].get(k), b["chaves"].get(k)
        if x != y:
            txt = "novo" if x is None else "saiu" if y is None else f"{x['n']}→{y['n']} entradas, conteúdo mudou"
            pa, pb = a.get("metaPartes"), b.get("metaPartes")
            if k == "meta" and pa is not None and pb is not None:
                partes = sorted(i for i in set(pa) | set(pb) if pa.get(i) != pb.get(i))
                txt += ": " + ", ".join(partes) + (" (a imagem dos ícones: o efeito na tela está nos pixels acima)"
                                                   if partes == ["sprite.image"] else "")
            out.append(f"{k}: {txt}")
    for nome, chave in (("itens", "items"), ("receitas", "receitas")):
        x, y = a.get(chave, {}), b.get(chave, {})
        mud = sorted(i for i in set(x) | set(y) if x.get(i) != y.get(i))
        if mud:
            out.append(f"{nome} diferentes ({len(mud)}): " + ", ".join(mud[:8]) + (" …" if len(mud) > 8 else ""))
    if a.get("erros") != b.get("erros"):
        out.append(f"erros de JS ao abrir: {b.get('erros')}")
    return out


def comparar(saida, resumo):
    """Uma linha por caso; devolve quantos diferem (ou deram erro)."""
    pixels = ler_json(saida / "pixels.json") or {}
    A, B, dif = saida / "antes", saida / "depois", saida / "diferencas"
    tol = resumo.get("tolerancia", 0)
    ruins = 0
    for caso in resumo["casos"]:
        nome, escala = caso["nome"], caso["escala"]
        px = pixels.get(nome, {})
        if "erro" in px:
            ruins += 1
            print(f"  ERRO       {nome}: {px['erro']}")
            continue
        ia, ib = ler_json(A / f"{nome}.json"), ler_json(B / f"{nome}.json")
        motivos = []
        if px.get("diferentes"):
            ta = px.get("tamanhos") or []
            tam = f", altura {ta[1] // escala}→{ta[3] // escala}px" if len(ta) == 4 and ta[1] != ta[3] else ""
            fora = f" acima de {tol}/255" if tol else ""
            motivos.append(f"{px['diferentes']} pixels{fora} (máx {px.get('delta', '?')}/255) em {onde(px, ib, escala)}{tam}"
                           f" → diferencas/{nome}.png")
        for tipo in ("html", "texto"):
            a, b = ler(A / f"{nome}.{tipo}.txt"), ler(B / f"{nome}.{tipo}.txt")
            if tipo == "html":
                a, b = html_normal(a), html_normal(b)
            if a != b:
                dif.mkdir(exist_ok=True)
                (dif / f"{nome}.{tipo}.diff").write_text(diff_texto(a or "", b or "", f"antes/{nome}", f"depois/{nome}"), encoding="utf-8")
                motivos.append(f"{tipo} difere (linha {primeira_linha_diferente(a or '', b or '')}) → diferencas/{nome}.{tipo}.diff")
        if (ia or {}).get("estado") != (ib or {}).get("estado"):
            dif.mkdir(exist_ok=True)
            ja = json.dumps((ia or {}).get("estado"), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
            jb = json.dumps((ib or {}).get("estado"), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
            (dif / f"{nome}.estado.diff").write_text(diff_texto(ja, jb, f"antes/{nome}", f"depois/{nome}"), encoding="utf-8")
            motivos.append(f"estado do app difere → diferencas/{nome}.estado.diff")
        ea, eb = (ia or {}).get("erros", []), (ib or {}).get("erros", [])
        if ea != eb:
            motivos.append(f"erros de JS: antes {ea or 'nenhum'}, depois {eb or 'nenhum'}")
        elif eb:
            print(f"  AVISO      {nome}: os dois lados têm erros de JS: {eb[:2]}")
        tolerados = f" (tolerância {tol}: {px['tolerados']} px)" if px.get("tolerados") else ""
        if motivos:
            ruins += 1
            print(f"  DIFERENTE  {nome}{tolerados}")
            for m in motivos:
                print(f"               {m}")
        else:
            print(f"  igual      {nome}{tolerados}")
    return ruins


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ref", default="HEAD", help="ref do git com o 'antes' (padrão HEAD)")
    ap.add_argument("--antes", help="um arquivo como 'antes', no lugar da ref (o mesmo da --pagina: prova de 0 pixel)")
    ap.add_argument("--only-capture", action="store_true", help="só captura o dist/preview.html atual em .shots/capturas/")
    ap.add_argument("--pagina", default=PAGINA, help=f"a página 'depois' (padrão {PAGINA})")
    ap.add_argument("--filtro", help="só os casos com um destes trechos no nome (separados por vírgula)")
    ap.add_argument("--paralelo", type=int, default=4, help="Chromes ao mesmo tempo (padrão 4)")
    ap.add_argument("--tolerancia", type=int, default=0, metavar="N",
                    help="pixel com diferença de até N/255 por canal conta como igual (padrão 0: exato); o resumo conta quantos")
    ap.add_argument("--saida", help="pasta de saída (padrão .shots/compare ou .shots/capturas); é apagada antes")
    args = ap.parse_args(argv)

    pagina = (ROOT / args.pagina).resolve()
    if not pagina.is_file():
        die(f"{args.pagina} não existe (rode o build)")
    saida = Path(args.saida).resolve() if args.saida else ROOT / ".shots" / ("capturas" if args.only_capture else "compare")
    # só apaga uma pasta de .shots/ ou uma que já tenha saída deste script
    if saida.exists() and any(saida.iterdir()) and (ROOT / ".shots") not in saida.parents and not (saida / "resumo.json").is_file():
        die(f"{saida} não está vazia e não é uma saída deste script: escolha outra pasta")
    shutil.rmtree(saida, ignore_errors=True)
    saida.mkdir(parents=True)
    if not 0 <= args.tolerancia <= 255:
        die("--tolerancia vai de 0 a 255")
    extra = ["--paralelo", str(args.paralelo), "--tolerancia", str(args.tolerancia)] + (["--filtro", args.filtro] if args.filtro else [])
    t0 = time.time()

    if args.only_capture:
        print(f"capturando {args.pagina} → {saida}")
        rc, _ = rodar_capture(["--saida", str(saida), *extra, str(pagina)])
        resumo = ler_json(saida / "resumo.json") or {"casos": []}
        print(f"\n{len(resumo['casos'])} capturas em {time.time() - t0:.0f}s (PNG, HTML, texto e estado de cada caso) em {saida}")
        return 1 if rc else 0

    tmp = Path(tempfile.mkdtemp(prefix="gk2-compare-"))
    try:
        if args.antes:
            arq = (ROOT / args.antes).resolve()
            if not arq.is_file():
                die(f"{args.antes} não existe")
            conteudo, nome_antes = arq.read_bytes(), args.antes
        else:
            r = subprocess.run(["git", "show", f"{args.ref}:{PAGINA}"], cwd=ROOT, capture_output=True)
            if r.returncode != 0:
                die(f"git show {args.ref}:{PAGINA} falhou: {r.stderr.decode(errors='replace').strip()}")
            conteudo, nome_antes = r.stdout, f"{args.ref}:{PAGINA}"
        # as duas com o mesmo nome de arquivo, cada uma na sua pasta: só o conteúdo difere
        (tmp / "antes").mkdir()
        (tmp / "depois").mkdir()
        (tmp / "antes" / "preview.html").write_bytes(conteudo)
        shutil.copy2(pagina, tmp / "depois" / "preview.html")
        print(f"comparando {nome_antes} (antes) × {args.pagina} (depois) → {saida}")
        rc, log = rodar_capture(["--saida", str(saida), "--antes", str(tmp / "antes" / "preview.html"),
                                 "--depois", str(tmp / "depois" / "preview.html"), *extra])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    resumo = ler_json(saida / "resumo.json")
    if resumo is None:
        die(f"o capture.mjs saiu com {rc} sem terminar:\n" + "\n".join(log[-20:]))
    print()
    ruins = comparar(saida, resumo)
    dados = comparar_dados(ler_json(saida / "antes" / "dados.json"), ler_json(saida / "depois" / "dados.json"))
    if dados:
        ruins += 1
        print("  DIFERENTE  dados (GK.data)")
        for d in dados:
            print(f"               {d}")
    else:
        print("  igual      dados (GK.data)")
    n = len(resumo["casos"])
    veredito = "TUDO IGUAL" if not ruins and rc == 0 else f"{ruins} DIFERENTE(S)/ERRO(S)"
    px = [v for v in (ler_json(saida / "pixels.json") or {}).values() if "erro" not in v]
    tolerados = sum(v.get("tolerados", 0) for v in px)
    if args.tolerancia:
        veredito += f" (tolerância {args.tolerancia}: {tolerados} px em {sum(1 for v in px if v.get('tolerados'))} casos)"
    maximo = max((v.get("delta", 0) for v in px), default=0)
    print(f"\ncompare {nome_antes}: {veredito} — {n} casos + dados em {time.time() - t0:.0f}s; maior diferença de cor"
          f" {maximo}/255; arquivos em {saida}")
    return 0 if not ruins and rc == 0 else 1


def _interromper(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    # SIGTERM / SIGHUP como Ctrl-C: termina o node (que fecha o Chrome) e apaga a pasta temporária
    signal.signal(signal.SIGTERM, _interromper)
    signal.signal(signal.SIGHUP, _interromper)
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ncompare: interrompido", file=sys.stderr)
        sys.exit(130)
