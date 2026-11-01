"""The page: assembled from src/ (manifest order), the data block filled, and the Artifact / preview variants."""
import json
import re
import sys
from pathlib import Path

from build_parts.common import _die


# --------------------------------------------------------------------------- data block

def dumps_min(ds):
    s = json.dumps(ds, ensure_ascii=False, separators=(",", ":"))
    # Safe inside <script>: "<" only occurs inside JSON strings, so \u003c keeps it valid JSON
    # and prevents "</script>" / "<!--" from terminating the block.
    return s.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


SCRIPT_RE = re.compile(
    r"(<script\b(?=[^>]*\bid\s*=\s*([\"'])gk2-data\2)[^>]*>)(.*?)(</script\s*>)",
    re.IGNORECASE | re.DOTALL)


def fill_data(html, payload, where):
    """html with the content of its single <script id="gk2-data" ...> replaced by payload (SystemExit(2) otherwise)."""
    matches = list(SCRIPT_RE.finditer(html))
    if len(matches) != 1:
        raise SystemExit(_die(f"--src: expected exactly one <script id=\"gk2-data\"> in {where}, "
                              f"found {len(matches)}"))
    m = matches[0]
    if "application/json" not in m.group(1).lower():
        print(f"build: warning: gk2-data script tag in {where} has no type=\"application/json\"", file=sys.stderr)
    return html[:m.start(3)] + payload + html[m.end(3):]


# --------------------------------------------------------------------------- Artifact page

# Skeleton tags the Artifact wrapper supplies itself. Only removed outside <script>/<style>.
SKELETON_RE = re.compile(
    r"<!doctype[^>]*>\s*|</?html\b[^>]*>\s*|</?head\b[^>]*>\s*|</?body\b[^>]*>\s*"
    r"|<meta\s+charset\s*=[^>]*>\s*|<meta\s+name\s*=\s*([\"'])viewport\1[^>]*>\s*",
    re.IGNORECASE)
RAWTEXT_RE = re.compile(r"<(script|style)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)


def strip_skeleton(html):
    """Remove doctype/html/head/body tags and the charset/viewport metas, keep everything else in order."""
    out, pos = [], 0
    for m in RAWTEXT_RE.finditer(html):
        out.append(SKELETON_RE.sub("", html[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(SKELETON_RE.sub("", html[pos:]))
    return "".join(out).lstrip()


PREVIEW_HEAD = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '<!-- local preview only: same content as index.html inside the skeleton the Artifact wrapper adds -->\n'
                '</head>\n<body>\n')


def artifact_page(html):
    out = strip_skeleton(html)
    if not out.startswith("<title"):
        print("build: warning: artifact page does not start with <title>", file=sys.stderr)
    return out


def preview_page(artifact_html):
    return PREVIEW_HEAD + artifact_html + "\n</body>\n</html>\n"


# --------------------------------------------------------------------------- page from src/

MARKERS = {"css": "<!-- @css -->", "js": "<!-- @js -->", "data": "<!-- @data -->"}


def load_manifest(src_dir):
    src = Path(src_dir)
    mp = src / "manifest.json"
    try:
        man = json.loads(mp.read_text(encoding="utf-8"))
    except OSError as e:
        raise SystemExit(_die(f"--src: cannot read {mp}: {e}"))
    except ValueError as e:
        raise SystemExit(_die(f"--src: invalid JSON in {mp}: {e}"))
    if not (isinstance(man, dict) and all(isinstance(man.get(k), list) and all(isinstance(x, str) for x in man[k])
                                          for k in ("css", "js"))):
        raise SystemExit(_die(f"--src: {mp} needs \"css\": [paths] and \"js\": [paths] (relative to {src})"))
    return man


def assemble(src_dir, payload=None, warn=True):
    """src/index.html with the data block filled (payload; None keeps the <!-- @data --> marker) and
    <!-- @css --> / <!-- @js --> replaced by the manifest's files, concatenated in order.
    The data goes in first, so text in the sources can never be mistaken for the data block."""
    src = Path(src_dir)
    man = load_manifest(src)
    tpl_path = src / man.get("template", "index.html")
    try:
        html = tpl_path.read_text(encoding="utf-8")
    except OSError as e:
        raise SystemExit(_die(f"--src: cannot read template {tpl_path}: {e}"))
    for k, mk in MARKERS.items():
        if html.count(mk) != 1:
            raise SystemExit(_die(f"--src: template {tpl_path.name} must contain {mk} exactly once "
                                  f"(found {html.count(mk)})"))
    seen = set()

    def part(kind, closer):
        chunks = []
        for f in man[kind]:
            fp = src / f
            if f in seen:
                raise SystemExit(_die(f"--src: {f} is listed twice in manifest.json"))
            seen.add(f)
            try:
                text = fp.read_text(encoding="utf-8")
            except OSError as e:
                raise SystemExit(_die(f"--src: manifest entry {f}: {e}"))
            if closer in text.lower():
                raise SystemExit(_die(f"--src: {f} contains \"{closer}\", which would end the page's <{closer[2:]}> block"))
            chunks.append(f"/* ==== src/{f} ==== */\n" + text.rstrip("\n") + "\n")
        return "\n".join(chunks)

    css = part("css", "</style")
    js = part("js", "</script")
    if warn:
        listed = {(src / f).resolve() for f in seen}
        for ext in ("css", "js"):
            for fp in sorted(src.rglob("*." + ext)):
                if fp.resolve() not in listed:
                    print(f"build: warning: {fp.relative_to(src)} is not in {src.name}/manifest.json (not built)",
                          file=sys.stderr)
    if payload is not None:
        html = fill_data(html, payload, tpl_path)
    # markers are replaced via a function, so backslashes / group refs in the sources stay literal
    html = re.sub(re.escape(MARKERS["css"]), lambda m: "<style>\n" + css + "</style>", html, count=1)
    html = re.sub(re.escape(MARKERS["js"]), lambda m: '<script>\n"use strict";\n' + js + "</script>", html, count=1)
    return html
