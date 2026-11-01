#!/usr/bin/env python3
"""site/preview.html a partir de site/index.html, e o número da versão do site.

    python3 -I scripts/site_preview.py           # regenera site/preview.html (só grava se mudou)
    python3 -I scripts/site_preview.py --check   # só confere; exit 1 se estiver desatualizado

site/index.html é a página do Artifact (sem doctype/html/head/body); preview.html é a mesma página num esqueleto
HTML mínimo, para abrir localmente. O check.py usa estas funções para conferir e o release.py para trocar a
versão e regenerar o preview.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "site" / "index.html"
PREVIEW = ROOT / "site" / "preview.html"

# os dois lugares do site que mostram a versão: o rodapé (#ver) e a constante do script
VER_JS = re.compile(r'const VERSION = "([^"]+)";')
VER_SPAN = re.compile(r'(id="ver">)v([^<]+)(<)')


def site_preview(index_html):
    """O texto de site/preview.html para um site/index.html."""
    i = index_html.index("</style>") + len("</style>")
    head, body = index_html[:i], index_html[i:]
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<!-- Generated from index.html (the Claude Artifact page). Do not edit by hand; see README.md. -->\n'
            '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
            'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
            + head.strip() + '\n</head>\n<body>\n' + body.strip() + '\n</body>\n</html>\n')


def site_versions(index_html):
    """(versões em `const VERSION`, versões em #ver): cada lista deve ter exatamente 1 item."""
    return VER_JS.findall(index_html), [m[1] for m in VER_SPAN.findall(index_html)]


def set_site_version(index_html, v):
    """Troca só o número da versão nos 2 lugares; ValueError se não achar exatamente 1 de cada."""
    out, n1 = VER_JS.subn(f'const VERSION = "{v}";', index_html)
    out, n2 = VER_SPAN.subn(rf"\g<1>v{v}\g<3>", out)
    if (n1, n2) != (1, 1):
        raise ValueError(f"site/index.html: esperava 1 'const VERSION' e 1 'id=\"ver\"', achei {n1} e {n2}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="só confere, não grava")
    args = ap.parse_args(argv)
    new = site_preview(INDEX.read_text(encoding="utf-8")).encode("utf-8")
    same = PREVIEW.exists() and PREVIEW.read_bytes() == new
    if args.check:
        print("site/preview.html em dia" if same else "site/preview.html desatualizado: rode scripts/site_preview.py")
        return 0 if same else 1
    if not same:
        PREVIEW.write_bytes(new)
    print("site/preview.html regenerado" if not same else "site/preview.html já estava em dia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
