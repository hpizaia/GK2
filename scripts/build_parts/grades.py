"""Quality grades (item.grade, recipe.quality, line.grade / anyGrade) and perk bonuses (line.bonus, the perk table)."""
import re
import unicodedata
from collections import defaultdict

from build_parts.notes import note_bonus


# --------------------------------------------------------------------------- quality grades and perk bonuses
# What the page shows of the grades (the star in the icon corner, the bronze / silver / gold order) and of the perk
# bonuses, set here once; GK.data (src/js/data.js) reads them as they come. Rule: data/README-data.md "Quality grades".

GRADE_SUFFIX = re.compile(r"-(bronze|silver|gold)$")
_GRADE_IN_NAME = re.compile(r"^.+? from (.+?) \((bronze|silver|gold)\)\s*$", re.I)   # "<X> from <Y> (grade)"
_GRADE_AT_END = re.compile(r"\((bronze|silver|gold)\)\s*$", re.I)
_FROM_ANY = re.compile(r"\bfrom Any (.+?)\s*$", re.I)


def page_norm(s):
    """GK.data.norm: accents and apostrophes off, lower case ("Magpie’s Eye" -> "magpies eye")."""
    s = re.sub(r"[̀-ͯ]", "", unicodedata.normalize("NFD", str(s or "")))
    return re.sub(r"[’'`´]", "", s.lower()).strip()


def apply_grades(items, recipes):
    """Set, in place, the grades the page shows (keys only where there is a grade):
    - item.grade on a quality variant ("wine-silver": "silver", from the id) and on the plain item of a family with a
      silver or gold variant and no bronze one ("wine", "pumpkin", "cabbage-seed": "bronze");
    - recipe.quality = the grade of the variant it makes ("Wine (silver)" from the Barrel and from "Wine (bronze) +
      Spices"), else the "(grade)" its name ends with ("Cabbage soup from Cabbage (gold)"); never from the id alone
      ("polished-bronze" is not a grade); the bronze plain items do not count here;
    - line.grade on the input a "<X> from <Y> (grade)" recipe names when it stays the plain item (the bronze one:
      "Drink enhancement I from Wine (bronze)");
    - line.anyGrade on the input of a "<X> from Any <Y>" recipe (any grade: no star on it)."""
    en = {iid: page_norm(it.get("en") or it.get("pt") or iid) for iid, it in items.items()}

    def rname(r):
        nm = r.get("name")
        if not isinstance(nm, dict):
            return ""
        return (nm.get("en") if nm.get("en") is not None else nm.get("pt")) or ""

    def input_named(r, want):
        return next((ln for ln in r["in"] if ln["item"] in items and en[ln["item"]] == want), None)

    for r in recipes:
        m = _GRADE_IN_NAME.match(rname(r))
        ln = m and input_named(r, page_norm(m.group(1)))
        if ln and items[ln["item"]].get("kind") != "quality-variant" and items[ln["item"]].get("members") is None:
            ln["grade"] = m.group(2).lower()
    for iid, it in items.items():
        m = it.get("kind") == "quality-variant" and GRADE_SUFFIX.search(iid)
        if m:
            it["grade"] = m.group(1)
    for r in recipes:
        q = items.get(r["out"]["item"], {}).get("grade")
        if not q:
            m = _GRADE_AT_END.search(rname(r))
            q = m and m.group(1).lower()
        if q:
            r["quality"] = q
    fams = defaultdict(set)
    for it in items.values():
        if it.get("grade") and it.get("base"):
            fams[it["base"]].add(it["grade"])
    for iid, gs in fams.items():
        it = items.get(iid)
        if ("bronze" in gs or not gs & {"silver", "gold"} or not it or it.get("stub") or it.get("grade")
                or it.get("members") is not None or it.get("kind") in ("quality-variant", "group")):
            continue
        it["grade"] = "bronze"
    for r in recipes:
        m = _FROM_ANY.search(rname(r))
        ln = m and input_named(r, page_norm(m.group(1)))
        if ln and not ln.get("grade"):
            ln["anyGrade"] = True


def apply_bonuses(recipes):
    """Set line.bonus (note_bonus()) on every input, by-product and output whose note has a perk bonus, in place.
    Returns the perk table {id: {pt, en, uses}} in the order met: the pt name is the first real one (not equal to
    the English) a note gives; uses = how many lines name the perk."""
    perks = {}
    for r in recipes:
        for ln in r["in"] + r["extra"] + [r["out"]]:
            b = note_bonus(ln.get("note"))
            if not b:
                continue
            ln["bonus"], names = b
            for pid, en, pt in names:
                p = perks.setdefault(pid, {"pt": pt, "en": en, "uses": 0})
                if p["pt"] == p["en"] and pt != en:
                    p["pt"] = pt
                p["uses"] += 1
    return perks
