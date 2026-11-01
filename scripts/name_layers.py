"""pt (and other language) names of the GK2 data: the names layers and the one lookup every script uses.

The pt layers, best first (DEFAULT_PT, files in data/):
    names.official.pt-BR.json   the game's own text (tools/exportar-textos/juntar_nomes.py)
    names.manual.pt-BR.json     chosen by hand: recipe names, wiki/game words, GK1 names, corrections (`fix`)
    names.machine.pt-BR.json    Claude's translation, the fallback (a file named *.machine.* is all tier machine)
Rule: a correction (`fix`) > official > by hand > machine; inside a file and on a tie, the first one wins.

Used by build.py, build_techs.py (and the tests). Python 3 stdlib only. `python3 -I` does not put scripts/ on
sys.path, so callers do `sys.path.insert(0, <scripts dir>)` before `import name_layers`.
"""
import json
import re
import unicodedata
from pathlib import Path

# Tier of a translation, best first. "missing" = no translation, English shown.
TIERS = ("official", "likely", "guess", "machine", "missing")
TIER_RANK = {t: i for i, t in enumerate(TIERS)}
DEFAULT_PT = ("names.official.pt-BR.json", "names.manual.pt-BR.json", "names.machine.pt-BR.json")


def default_pt(data_dir):
    """The pt layer files, best first, as paths under `data_dir`."""
    return [Path(data_dir) / f for f in DEFAULT_PT]


def norm_key(s):
    s = unicodedata.normalize("NFC", str(s))
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip().casefold()


class Layer:
    """One names file: { "<English>": {pt, source, confidence}, "__obtain": {"<English text>": "<pt>"} }.

    An entry with a non-empty `fix` (the reason, e.g. a typo of the official game text) is a correction: it wins
    over every layer and tier (Translator.name), keeping its own confidence (data/names.manual.pt-BR.json:
    "Wheat Bed" -> "Canteiro de Trigo", likely, where the game says "Canteiro de Trigorigo")."""

    def __init__(self, path, data, log, machine):
        self.path = Path(path)
        self.machine = machine
        self.names = {}    # norm key -> (pt, tier, source, original key)
        self.texts = {}    # norm key -> pt (free text: obtain, notes)
        self.keys = {}     # norm key -> game localisation key ("gameKey"), when the file has one
        self.fixes = {}    # norm key -> (pt, tier, source, original key): `fix` entries, they beat every tier
        if data is None:
            return
        if isinstance(data, dict) and isinstance(data.get("names"), dict):
            log.coerce("names: unwrapped `names` key", self.path.name)
            texts = data.get("__obtain") or data.get("obtain")
            data = dict(data["names"], __obtain=texts or {})
        if isinstance(data, list):   # [{en, pt, ...}]
            log.coerce("names: list converted to dict", self.path.name)
            data = {e.get("en") or e.get("name"): e for e in data if isinstance(e, dict)}
        if not isinstance(data, dict):
            log.note(f"names: `{self.path.name}` is not an object, ignored")
            return
        for k, v in data.items():
            if k is None:
                continue
            if k.startswith("__"):
                if isinstance(v, dict):
                    for tk, tv in v.items():
                        pt = tv.get("pt") if isinstance(tv, dict) else tv
                        if isinstance(pt, str) and pt.strip():
                            self.texts[norm_key(tk)] = pt.strip()
                else:
                    log.coerce("names: non-object special key ignored", f"{self.path.name}:{k}")
                continue
            if k.startswith("_"):
                log.coerce("names: `_` key ignored", f"{self.path.name}:{k}")
                continue
            if isinstance(v, str):
                log.coerce("names: bare string value -> confidence guess", f"{k!r}")
                v = {"pt": v, "confidence": "guess", "source": None}
            if not isinstance(v, dict):
                log.coerce("names: bad entry ignored", f"{k!r}")
                continue
            pt = v.get("pt") or v.get("name") or v.get("value")
            if not isinstance(pt, str) or not pt.strip():
                log.coerce("names: entry without pt ignored", f"{k!r}")
                continue
            conf = str(v.get("confidence") or "").strip().lower()
            source = v.get("source")
            if machine or (isinstance(source, str) and source.strip().lower() == "machine"):
                tier = "machine"
            elif conf in ("official", "likely", "guess"):
                tier = conf
            else:
                log.coerce("names: unknown confidence -> guess", f"{k!r}: {v.get('confidence')!r}")
                tier = "guess"
            nk = norm_key(k)
            if isinstance(v.get("fix"), str) and v["fix"].strip() and nk not in self.fixes:
                self.fixes[nk] = (pt.strip(), tier, source, k)
            gk = v.get("gameKey")
            if isinstance(gk, str) and gk.strip() and nk not in self.keys:
                self.keys[nk] = gk.strip()
            prev = self.names.get(nk)
            if prev and TIER_RANK[prev[1]] <= TIER_RANK[tier]:
                continue
            self.names[nk] = (pt.strip(), tier, source, k)


class Translator:
    """All layers of one language: a correction (`fix`) first, then the best tier (official > likely > guess >
    machine), the first layer on a tie."""

    def __init__(self, field, layers):
        self.field = field
        self.layers = layers
        self.looked_up = set()   # norm keys of every English string we asked for

    def name(self, en):
        """-> (text, tier, source). Falls back to English with tier 'missing'."""
        if en is None:
            return None, "missing", None
        nk = norm_key(en)
        self.looked_up.add(nk)
        fixed = self.fix(en)
        if fixed is not None:
            return fixed
        best = None
        for li, layer in enumerate(self.layers):
            hit = layer.names.get(nk)
            if hit and (best is None or TIER_RANK[hit[1]] < TIER_RANK[best[1][1]]):
                best = (li, hit)
        if best is None:
            return en, "missing", None
        pt, tier, source, _ = best[1]
        return pt, tier, source

    def fix(self, en):
        """-> (text, tier, source) of a correction (`fix`) for this English name, first file first; else None.
        A caller with an extra official source of its own (build_techs.py: the game text table) asks this first,
        so a correction also beats that source."""
        if en is None:
            return None
        nk = norm_key(en)
        for layer in self.layers:
            if nk in layer.fixes:
                pt, tier, source, _ = layer.fixes[nk]
                return pt, tier, source
        return None

    def game_key(self, en):
        """Game localisation key for an English name (first layer that has one), or None."""
        if en is None:
            return None
        nk = norm_key(en)
        for layer in self.layers:
            if nk in layer.keys:
                return layer.keys[nk]
        return None

    def text(self, en):
        """Free text (obtain / notes): text maps first, then names. Falls back to English."""
        if en is None:
            return None
        hit = self.text_hit(en)
        return en if hit is None else hit

    def text_hit(self, en):
        """Like text(), but None when no text map or names entry has the string."""
        if en is None:
            return None
        nk = norm_key(en)
        for layer in self.layers:
            if nk in layer.texts:
                return layer.texts[nk]
        pt, tier, _ = self.name(en)
        return None if tier == "missing" else pt

    def sources(self):
        out = set()
        for layer in self.layers:
            for (_, tier, source, _) in layer.names.values():
                if isinstance(source, str) and source.strip():
                    out.add(source_host(source))
        return out

    def unused(self):
        out = []
        for li, layer in enumerate(self.layers):
            for nk, (pt, tier, source, key) in layer.names.items():
                if nk not in self.looked_up:
                    out.append((layer.path.name, key, pt, tier))
        return sorted(out, key=lambda x: (x[0], norm_key(x[1])))


def source_host(s):
    m = re.match(r"^[a-z][a-z0-9+.-]*://([^/]+)", s.strip(), re.I)
    if m:
        h = m.group(1).lower()
        return h[4:] if h.startswith("www.") else h
    return s.strip()


class NullLog:
    """Stand-in for build.Log when nobody reports input coercions (build_techs.py)."""

    def coerce(self, kind, example):
        pass

    def note(self, msg):
        pass


def load(paths, field="pt", log=None):
    """Translator over the given names files (best first). A missing file is an empty layer."""
    log = log or NullLog()
    layers = []
    for p in paths:
        p = Path(p)
        data = json.loads(p.read_text(encoding="utf-8-sig")) if p.exists() else None
        layers.append(Layer(p, data, log, machine=".machine." in p.name))
    return Translator(field, layers)
