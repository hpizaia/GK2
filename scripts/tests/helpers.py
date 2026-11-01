#!/usr/bin/env python3
"""What the build tests share: paths, build.py and validate.py loaded once, running a script, the fixture
arguments, the page's texts, and a throwaway src/ project.  The tests: scripts/tests/test_*.py; run them all with
python3 -I scripts/test_build.py.
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__

TESTS = Path(__file__).resolve().parent
HERE = TESTS.parent              # scripts/
ROOT = HERE.parent
FIX = HERE / "fixtures"
BUILD = HERE / "build.py"
VALIDATE = HERE / "validate.py"


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate = load_mod("gk2_validate_t", VALIDATE)
build = load_mod("gk2_build_t", BUILD)


def run(script, *args):
    p = subprocess.run([sys.executable, "-I", str(script), *map(str, args)],
                       capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, p.stdout, p.stderr


def fixture_args(out_dir, items=None, recipes=None, names=None):
    names = names if names is not None else [FIX / "names.pt-BR.json", FIX / "names.machine.pt-BR.json"]
    a = ["--items", items or FIX / "items.en.json", "--recipes", recipes or FIX / "recipes.en.json",
         "--out-dir", out_dir, "--built", "2026-01-01", "--quiet", "--no-src"]
    for n in names:
        a += ["--names", n]
    return a


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


_TEXTS = {}


def texts(lang):
    """{key: text} of src/js/i18n/<lang>.js (pt.js, en.js): every text of the page, by screen, in file order."""
    if lang not in _TEXTS:
        src = (ROOT / "src" / "js" / "i18n" / f"{lang}.js").read_text(encoding="utf-8")
        pairs = re.findall(r'^\s*"([a-zA-Z]+\.[\w.-]+)": "((?:[^"\\]|\\.)*)"', src, re.M) + \
            re.findall(r', "([a-zA-Z]+\.[\w.-]+)": "((?:[^"\\]|\\.)*)"', src)   # a line may hold several keys
        _TEXTS[lang] = {k: json.loads('"%s"' % v) for k, v in pairs}
    return _TEXTS[lang]


def recipes_src():
    """The Receitas screen's code: ui/recipes-cards.js, ui/recipes-facts.js and ui/recipes.js (src/manifest.json order)."""
    js = read_json(ROOT / "src" / "manifest.json")["js"]
    return "\n".join((ROOT / "src" / f).read_text(encoding="utf-8") for f in js if f.startswith("js/ui/recipes"))


def expand_payload(page):
    """Undo build.page_payload (collapsed {pt, en} strings, dropped items[].id, default values left out), like GK.data
    does."""
    langs = page["meta"]["langs"]
    loc_keys = {"cat", "obtain", "note", "ext", "zone", "name", "type"}

    def walk(v, key=None):
        if isinstance(v, list):
            return [walk(x, key) for x in v]
        if isinstance(v, dict):
            return {k: walk(x, k) for k, x in v.items()}
        if isinstance(v, str) and key in loc_keys and not (key == "type" and v in TYPES):
            return {l: v for l in langs}
        return v

    TYPES = {"hand_craft", "star_craft", "auto", "factory", "building", "alchemy", "grow",
             "technology", "quest", "perk"}
    out = walk(page)
    # the fields build.py drop_defaults() leaves out, with the value GK.data (src/js/data.js) gives a missing one
    item_def = {"cat": None, "obtain": None, "icon": None, "tr": "missing", "kind": "item", "listed": True,
                "unobtainable": False}
    recipe_def = {"station": None, "in": [], "tech": None, "type": "hand_craft", "cd": False, "listed": True,
                  "noexp": False, "cyc": False, "alt": [], "ext": None, "extra": [], "mastery": None, "ticks": None,
                  "energy": None, "example": False, "runes": None, "zone": None}
    for iid, it in out["items"].items():
        for k, v in item_def.items():
            it.setdefault(k, v)
        it["id"] = iid
    for st in out["stations"].values():
        st.setdefault("icon", None)
        st.setdefault("tr", "missing")
    for r in out["recipes"]:
        for k, v in recipe_def.items():
            r.setdefault(k, list(v) if isinstance(v, list) else v)
        for ln in r["in"]:
            ln.setdefault("qty", 1)
        for ln in r["extra"] + [r["out"]]:
            ln.setdefault("qty", None)
    out["meta"].pop("collapsed", None)
    out["meta"].pop("sprite", None)
    out["meta"].pop("version", None)
    out["meta"].pop("changelog", None)
    out["meta"].pop("data", None)
    return out


def extract_block(html):
    m = re.search(r'<script id="gk2-data" type="application/json">(.*?)</script>', html, re.S)
    return m.group(1)


CHANGELOG = [
    {"version": "9.9.9", "date": None, "pt": ["Novidade <b>em teste</b>"], "en": ["Test feature"]},
    {"version": "9.9.8", "date": "2026-01-02", "pt": ["Versão anterior"], "en": ["Previous version"]},
]
TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>Fixture</title>
<!-- @css -->
</head>
<body>
<script id="gk2-data" type="application/json"><!-- @data --></script>
<main id="app"></main>
<!-- @js -->
</body>
</html>
"""


def make_project(root, js=None, css=None, version="9.9.9", changelog=CHANGELOG, template=TEMPLATE):
    """A throwaway project: root/src (manifest, template, css, js), root/VERSION, root/data/changelog.json."""
    src = root / "src"
    js = js if js is not None else {"js/core.js": "window.GK = { ui: {} };\n",
                                    "js/ui/second.js": "GK.second = 2; // replacement text: \\1 $1 \\g<0>\n",
                                    "js/app.js": "GK.app = 'boot';\n"}
    css = css if css is not None else {"css/tokens.css": ":root { --a: 1; }\n", "css/z-last.css": "body { color: red; }\n"}
    for rel_path, text in {**js, **css}.items():
        (src / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (src / rel_path).write_text(text, encoding="utf-8")
    (src / "index.html").write_text(template, encoding="utf-8")
    (src / "manifest.json").write_text(json.dumps({"css": list(css), "js": list(js)}), encoding="utf-8")
    if version is not None:
        (root / "VERSION").write_text(version + "\n", encoding="utf-8")
    if changelog is not None:
        (root / "data").mkdir(exist_ok=True)
        (root / "data" / "changelog.json").write_text(json.dumps(changelog, ensure_ascii=False), encoding="utf-8")
    return src
