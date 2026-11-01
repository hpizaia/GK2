"""Shared base of the build: paths and constants, validate.py, the names layers, the input helpers (Log, load_json,
as_list, parse_qty...), --lang parsing and file writing."""
import importlib.util
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# the names layers and the pt lookup, shared with build_techs.py (python3 -I: build.py puts scripts/ on sys.path)
from name_layers import TIERS, TIER_RANK, Layer, Translator, default_pt, norm_key, source_host  # noqa: F401

HERE = Path(__file__).resolve().parent.parent   # scripts/
ROOT = HERE.parent
DATA = ROOT / "data"

SCHEMA_VERSION = 1
BASE_LANG = "en"
# defaultRecipe preference when no recipe has calculator_default: true
TYPE_PREF = ("hand_craft", "star_craft", "auto", "factory", "building", "alchemy", "grow")
TYPE_RANK = {t: i for i, t in enumerate(TYPE_PREF)}
NOEXP_TYPES = {"grow"}   # recipes whose yield is unknown: kept, but never expanded
# Game version of the official texts when no names file has `_meta.game_version` (page only: meta.data.game). The
# wiki recipes' game version is the `wiki` field of data/game-version.json (load_wiki_version()).
GAME_TEXT_VERSION = "1.011"


def _load_validate():
    # `python3 -I` does not put the script dir on sys.path, so load validate.py by path.
    spec = importlib.util.spec_from_file_location("gk2_validate", HERE / "validate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate = _load_validate()


# --------------------------------------------------------------------------- helpers

def slugify(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "x"


class Log:
    """Collects coercions (things we had to fix in the inputs), counted per kind with examples."""

    def __init__(self, max_examples=8):
        self.counts = defaultdict(int)
        self.examples = defaultdict(list)
        self.max_examples = max_examples
        self.notes = []

    def coerce(self, kind, example):
        self.counts[kind] += 1
        if len(self.examples[kind]) < self.max_examples:
            self.examples[kind].append(str(example))

    def note(self, msg):
        self.notes.append(msg)


def load_json(path, what, log, required=True):
    p = Path(path)
    if not p.exists():
        if required:
            raise SystemExit(_die(f"{what}: file not found: {p}"))
        log.note(f"{what}: `{p.name}` not found, skipped")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except ValueError as e:
        raise SystemExit(_die(f"{what}: invalid JSON in {p}: {e}"))


def _die(msg):
    print(f"build: {msg}", file=sys.stderr)
    return 2


def as_list(data, what, log, keys):
    """Accept a list, a {"items": [...]} wrapper, or a dict keyed by id."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in keys:
            if isinstance(data.get(k), list):
                log.coerce(f"{what}: unwrapped `{k}` key", k)
                return data[k]
        if all(isinstance(v, dict) for v in data.values()):
            log.coerce(f"{what}: dict keyed by id converted to list", len(data))
            out = []
            for k, v in data.items():
                v = dict(v)
                v.setdefault("id", k)
                out.append(v)
            return out
    raise SystemExit(_die(f"{what}: expected a JSON array"))


def parse_qty(v, ctx, log, allow_null=False):
    """Returns int/float, or None (only when allow_null and v is None). Bad values become 0 (-> bad-qty error)."""
    if v is None:
        if allow_null:
            return None
        log.coerce("qty null -> 1", ctx)
        return 1
    if isinstance(v, bool):
        log.coerce("qty boolean -> 0/1", ctx)
        return int(v)
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return v
    if isinstance(v, str):
        try:
            f = float(v.strip().replace(",", "."))
        except ValueError:
            log.coerce("qty unparseable -> 0", f"{ctx}: {v!r}")
            return 0
        log.coerce("qty string -> number", f"{ctx}: {v!r}")
        return int(f) if f.is_integer() else f
    log.coerce("qty unparseable -> 0", f"{ctx}: {v!r}")
    return 0


def text_or_none(v):
    if v is None:
        return None
    if isinstance(v, list):
        v = "; ".join(str(x).strip() for x in v if x not in (None, ""))
    elif isinstance(v, dict):
        v = v.get("en") or v.get("name") or v.get("text")
    v = str(v).strip() if v is not None else ""
    return v or None


def parse_lang_specs(specs, log):
    """--lang pt=data/names.manual.pt-BR.json,data/names.machine.pt-BR.json  (repeatable)."""
    langs = []
    for spec in specs:
        if "=" not in spec:
            raise SystemExit(_die(f"--lang expects FIELD=PATH[,PATH...], got {spec!r}"))
        field, paths = spec.split("=", 1)
        field = field.strip()
        if not re.fullmatch(r"[a-z]{2,3}(_[A-Za-z]{2,4})?", field) or field == BASE_LANG:
            raise SystemExit(_die(f"--lang: bad field name {field!r}"))
        layers = []
        for p in [x for x in paths.split(",") if x.strip()]:
            p = Path(p.strip())
            if not p.is_absolute():
                p = (Path.cwd() / p)
            data = load_json(p, f"names[{field}]", log, required=False)
            layers.append(Layer(p, data, log, machine=".machine." in p.name))
        langs.append(Translator(field, layers))
    return langs


# --------------------------------------------------------------------------- IO

def write_if_changed(path, text):
    path = Path(path)
    data = text.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return True


def rel(p):
    p = Path(p).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return p.name
