"""Recipe notes: the English note shapes, their pt translation (translate_note_pt) and the perk bonus they carry
(note_bonus)."""
import re
import unicodedata


# --------------------------------------------------------------------------- recipe notes (pt)

# Recurring English shapes of the recipe input / by-product / output notes: (English regex, pt template, perk bonus).
# The last group is a perk or tech name ("Mason", "Farmer II and Grape Master"), resolved through the names layers.
# The bonus kind says what the shape does with the perk (note_bonus(), line.bonus on the page): "qty" = the amount
# becomes the group before the name ("3 (5 with Cook II)": 5), "add" = that group is added to each ("+1 each with
# Farmer II"); None = no amount (a chance, "with X").
_NUM = r"(\d+(?:\.\d+)?)"
NOTE_SHAPES = (
    (rf"^{_NUM}% chance with (.+)$", "{0}% de chance com {1}", None),
    (rf"^{_NUM}, or {_NUM} with (.+)$", "{0}, ou {1} com {2}", "qty"),
    (rf"^{_NUM} \({_NUM} with (.+)\)$", "{0} ({1} com {2})", "qty"),
    (rf"^\+{_NUM} each with (.+)$", "+{0} cada com {1}", "add"),
    (rf"^{_NUM} with (.+)$", "{0} com {1}", "qty"),
    (r"^with (.+)$", "com {0}", None),
)
NOTE_PATTERNS_PT = tuple((re.compile(en, re.I), tpl) for en, tpl, _ in NOTE_SHAPES)


def _pt_shape(tpl):
    """pt template -> the regex that reads it back ("{0} ({1} com {2})" -> numbers, then the perk names last); the pt
    number may use a decimal comma."""
    parts = re.split(r"\{(\d)\}", tpl)
    last = len(parts) // 2 - 1
    rx = "".join(re.escape(p) if i % 2 == 0 else ("(.+)" if int(p) == last else r"(\d+(?:[.,]\d+)?)")
                 for i, p in enumerate(parts))
    return re.compile(f"^{rx}$", re.I)


# the shapes that carry a perk bonus: (en regex, pt regex, kind)
BONUS_SHAPES = tuple((re.compile(en, re.I), _pt_shape(tpl), kind) for en, tpl, kind in NOTE_SHAPES if kind)


def perk_slug(s):
    """Perk name -> id, as the page always made it: "Cook II" -> "cook-ii", "Magpie’s Eye" -> "magpie-s-eye"."""
    s = unicodedata.normalize("NFD", str(s).lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def note_bonus(note):
    """note {pt, en} -> (bonus, names) | None: the first "; " segment of the English text in a bonus shape.
    bonus = {"perk": "<English names>", "perks": [id], "qty": M} or {..., "add": N}; names = [(id, en, pt)], the pt
    names read from the same segment of note.pt in the mirrored shape (the English one when it does not match or the
    count differs)."""
    if not isinstance(note, dict) or not note.get("en"):
        return None
    pt_text = note.get("pt") if note.get("pt") is not None else note.get("en")
    en = [x.strip() for x in str(note["en"]).split(";")]
    pt = [x.strip() for x in str(pt_text or "").split(";")]
    for k, seg in enumerate(en):
        for rx, rx_pt, kind in BONUS_SHAPES:
            m = rx.match(seg)
            if not m:
                continue
            v = float(m.groups()[-2])
            v = int(v) if v.is_integer() else v
            en_names = [x.strip() for x in re.split(r"\s+and\s+", m.groups()[-1], flags=re.I) if x.strip()]
            mp = rx_pt.match(pt[k]) if k < len(pt) and pt[k] else None
            pt_names = [x.strip() for x in re.split(r"\s+e\s+", mp.groups()[-1])] if mp else []
            names = [(perk_slug(e), e, pt_names[i] if len(pt_names) == len(en_names) else e)
                     for i, e in enumerate(en_names)]
            return {"perk": m.groups()[-1].strip(), "perks": [n[0] for n in names], kind: v}, names
    return None


def translate_note_pt(en, text_hit, name_hit):
    """English recipe note -> (pt or None, [unresolved names]).

    `text_hit(s)` -> pt for a literal string (the names files' `__notes` / `__obtain` maps, or a
    name), else None. `name_hit(s)` -> pt for a perk/tech name, else None. A note is split on "; "
    and every segment must be translated (literal first, then NOTE_PATTERNS_PT), or the result is
    None. A name with no translation stays in English and is reported in the second value."""
    if not en or not str(en).strip():
        return None, []
    unresolved = []

    def names(s):
        out = []
        for part in re.split(r"\s+and\s+", s.strip()):
            pt = name_hit(part)
            if pt is None:
                unresolved.append(part)
                pt = part
            out.append(pt)
        return " e ".join(out)

    segs = []
    for seg in str(en).split(";"):
        seg = seg.strip()
        if not seg:
            continue
        lit = text_hit(seg)
        if lit is not None:
            segs.append(lit)
            continue
        for rx, tpl in NOTE_PATTERNS_PT:
            m = rx.match(seg)
            if m:
                g = list(m.groups())
                g[-1] = names(g[-1])
                segs.append(tpl.format(*g))
                break
        else:
            return None, unresolved
    return ("; ".join(segs) if segs else None), unresolved
