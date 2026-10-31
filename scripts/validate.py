#!/usr/bin/env python3
"""Validate a GK2 planner dataset (the merged `data/gk2.json` schema).

Usable standalone:
    python3 -I scripts/validate.py data/gk2.json [--json] [--quiet]

or from build.py:
    report = validate.validate(data, pre_issues=[...])

Severities
  error    hard problem; the UI would break or show wrong numbers (exit code 1)
  warning  suspicious but tolerable; the UI must cope with it
  info     facts the UI should know about (e.g. items with several recipes)

Checks
  E dangling-ref      recipe output/input item or station id not defined
  E stub-item         item that build.py had to invent for a dangling ref
  E duplicate-id      duplicate recipe id (item duplicates come from build.py)
  E bad-qty           output or input qty that is not a number > 0
                      (output qty null is allowed only on `noexp` recipes, e.g. grow)
  W zero-inputs       recipe with no inputs (free buildings, zombie production...)
  W cycle             strongly connected component in the item graph
                      (item -> inputs of any of its expandable recipes), incl. self-loops
  W raw-with-recipe   item flagged raw that is the output of an expandable recipe
                      with >= 1 input (grow / zero-input recipes do not count)
  W orphan            item not used by any recipe (as output, input or station)
  W duplicate-input   the same item listed twice in one recipe's inputs
  I multi-recipe      item produced by more than one recipe
  E bad-default       item.defaultRecipe that is unknown, not producing the item, or noexp
  W cyclic-default    item.defaultRecipe flagged `cyc` (build.py never picks one)
  I cycle-trapped     item in a cycle whose every expandable recipe feeds back into
                      itself (recipe.cyc, raw items as leaves): no defaultRecipe, the UI
                      must treat it as raw
"""
import argparse
import json
import sys
from collections import defaultdict

SEVERITIES = ("error", "warning", "info")


class Issue:
    __slots__ = ("severity", "code", "message", "refs")

    def __init__(self, severity, code, message, refs=None):
        assert severity in SEVERITIES, severity
        self.severity = severity
        self.code = code
        self.message = message
        self.refs = refs or {}

    def to_dict(self):
        return {"severity": self.severity, "code": self.code,
                "message": self.message, "refs": self.refs}

    def __repr__(self):
        return f"Issue({self.severity}, {self.code}, {self.message!r})"


class Report:
    def __init__(self):
        self.issues = []
        self.cycles = []          # list of {"items": [...], "path": [...], "recipes": [...], "trapped": [...]}

    def add(self, severity, code, message, **refs):
        self.issues.append(Issue(severity, code, message, refs))

    def extend(self, issues):
        for i in issues or []:
            if isinstance(i, Issue):
                self.issues.append(i)
            else:  # tolerate plain dicts / tuples
                if isinstance(i, dict):
                    self.issues.append(Issue(i["severity"], i["code"], i["message"], i.get("refs")))
                else:
                    self.issues.append(Issue(*i))

    def by_severity(self, sev):
        return [i for i in self.issues if i.severity == sev]

    @property
    def errors(self):
        return self.by_severity("error")

    @property
    def warnings(self):
        return self.by_severity("warning")

    @property
    def infos(self):
        return self.by_severity("info")

    def codes(self, severity=None):
        out = defaultdict(int)
        for i in self.issues:
            if severity is None or i.severity == severity:
                out[i.code] += 1
        return dict(sorted(out.items()))

    def to_dict(self):
        return {
            "errors": len(self.errors), "warnings": len(self.warnings), "infos": len(self.infos),
            "codes": self.codes(),
            "issues": [i.to_dict() for i in self.issues],
            "cycles": self.cycles,
        }

    def summary_line(self):
        return (f"{len(self.errors)} error(s), {len(self.warnings)} warning(s), "
                f"{len(self.infos)} info(s)")

    def to_markdown(self, heading_level=2, limit_per_code=None):
        h = "#" * heading_level
        lines = []
        for sev in SEVERITIES:
            group = self.by_severity(sev)
            lines.append(f"{h} {sev.capitalize()}s ({len(group)})")
            lines.append("")
            if not group:
                lines.append("_none_")
                lines.append("")
                continue
            per_code = defaultdict(list)
            for i in group:
                per_code[i.code].append(i)
            for code in sorted(per_code):
                items = per_code[code]
                lines.append(f"{h}# `{code}` ({len(items)})")
                lines.append("")
                shown = items if limit_per_code is None else items[:limit_per_code]
                for i in shown:
                    lines.append(f"- {md_escape(i.message)}")
                if len(shown) < len(items):
                    lines.append(f"- ... and {len(items) - len(shown)} more")
                lines.append("")
        return "\n".join(lines)


def md_escape(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- graph helpers

def tarjan_scc(nodes, edges):
    """Iterative Tarjan. nodes: iterable of hashables; edges: dict node -> iterable of nodes.
    Returns a list of SCCs (each a list of nodes), in reverse topological order."""
    index = {}
    low = {}
    on_stack = set()
    stack = []
    sccs = []
    counter = 0
    for root in nodes:
        if root in index:
            continue
        work = [(root, iter(edges.get(root, ())))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter
                    counter += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(edges.get(nxt, ()))))
                    advanced = True
                    break
                elif nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == node:
                        break
                sccs.append(comp)
    return sccs


def find_cycle_path(start, members, edges):
    """Shortest path start -> ... -> start inside `members` (BFS). Returns list of nodes incl. start twice."""
    from collections import deque
    prev = {}
    q = deque()
    for nxt in sorted(edges.get(start, ())):
        if nxt in members and nxt not in prev:
            prev[nxt] = start
            q.append(nxt)
    while q:
        n = q.popleft()
        if n == start:
            break
        for nxt in sorted(edges.get(n, ())):
            if nxt in members and nxt not in prev:
                prev[nxt] = n
                q.append(nxt)
    if start not in prev:
        return [start, start]
    path = [start]
    cur = prev[start]
    while cur != start:
        path.append(cur)
        cur = prev[cur]
    path.append(start)
    path.reverse()
    return path


# --------------------------------------------------------------------------- main check

def _name(items, iid):
    it = items.get(iid)
    if isinstance(it, dict):
        return it.get("en") or iid
    return iid


def _is_pos_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 and v == v and v != float("inf")


def validate(data, pre_issues=None):
    """Validate a merged dataset dict ({meta, items, stations, recipes}). Returns a Report."""
    rep = Report()
    rep.extend(pre_issues)

    items = data.get("items") or {}
    stations = data.get("stations") or {}
    recipes = data.get("recipes") or []

    # ---- stub items (created by build.py for dangling references)
    for iid in sorted(items):
        if items[iid].get("stub"):
            rep.add("error", "stub-item",
                    f"item `{iid}` does not exist in items.en.json; build.py created a placeholder",
                    item=iid)

    # ---- duplicate recipe ids
    seen = {}
    for idx, r in enumerate(recipes):
        rid = r.get("id")
        if rid in seen:
            rep.add("error", "duplicate-id", f"recipe id `{rid}` appears more than once (#{seen[rid]} and #{idx})",
                    recipe=rid)
        else:
            seen[rid] = idx

    produced_by = defaultdict(list)   # item -> [recipe ids]
    used_in = defaultdict(set)        # item -> recipe ids (as input)
    station_use = defaultdict(set)
    edges = defaultdict(set)          # item -> input items
    edge_recipes = defaultdict(set)   # (out, in) -> recipe ids

    for r in recipes:
        rid = r.get("id")
        out = r.get("out") or {}
        oid = out.get("item")
        if oid not in items:
            rep.add("error", "dangling-ref", f"recipe `{rid}` outputs unknown item `{oid}`", recipe=rid, item=oid)
        noexp = bool(r.get("noexp"))
        if not (_is_pos_number(out.get("qty")) or (noexp and out.get("qty") is None)):
            rep.add("error", "bad-qty", f"recipe `{rid}` has output qty {out.get('qty')!r} (must be > 0)",
                    recipe=rid)
        produced_by[oid].append(rid)

        st = r.get("station")
        if st is not None and st not in stations:
            rep.add("error", "dangling-ref", f"recipe `{rid}` uses unknown station `{st}`", recipe=rid, station=st)
        if st is not None:
            station_use[st].add(rid)
        for alt in r.get("alt") or []:
            if alt not in stations:
                rep.add("error", "dangling-ref", f"recipe `{rid}` lists unknown alt station `{alt}`",
                        recipe=rid, station=alt)
            station_use[alt].add(rid)

        for ex in r.get("extra") or []:
            eid = ex.get("item")
            if eid not in items:
                rep.add("error", "dangling-ref", f"recipe `{rid}` has unknown extra output `{eid}`",
                        recipe=rid, item=eid)
            used_in[eid].add(rid)

        ins = r.get("in") or []
        if not ins:
            rep.add("warning", "zero-inputs",
                    f"recipe `{rid}` ({_name(items, oid)}) has no inputs", recipe=rid, item=oid)
        counts = defaultdict(int)
        for inp in ins:
            iid = inp.get("item")
            counts[iid] += 1
            if iid not in items:
                rep.add("error", "dangling-ref", f"recipe `{rid}` needs unknown item `{iid}`", recipe=rid, item=iid)
            if not _is_pos_number(inp.get("qty")):
                rep.add("error", "bad-qty",
                        f"recipe `{rid}` input `{iid}` has qty {inp.get('qty')!r} (must be > 0)",
                        recipe=rid, item=iid)
            used_in[iid].add(rid)
            if not noexp:
                edges[oid].add(iid)
                edge_recipes[(oid, iid)].add(rid)
        for iid, c in counts.items():
            if c > 1:
                rep.add("warning", "duplicate-input",
                        f"recipe `{rid}` lists input `{iid}` {c} times", recipe=rid, item=iid)

    # ---- multiple recipes
    for oid in sorted(produced_by):
        rids = produced_by[oid]
        if len(rids) > 1 and oid in items:
            rep.add("info", "multi-recipe",
                    f"`{oid}` ({_name(items, oid)}) has {len(rids)} recipes: {', '.join(rids)}",
                    item=oid, recipes=rids)

    # ---- raw flagged but craftable
    recipe_by_id = {r.get("id"): r for r in recipes}
    for oid in sorted(produced_by):
        it = items.get(oid)
        if not (it and it.get("raw")):
            continue
        real = [rid for rid in produced_by[oid]
                if not recipe_by_id[rid].get("noexp") and recipe_by_id[rid].get("in")]
        if real:
            rep.add("warning", "raw-with-recipe",
                    f"`{oid}` ({_name(items, oid)}) is flagged raw but is the output of "
                    f"{', '.join(real)}",
                    item=oid, recipes=real)

    # ---- defaultRecipe consistency
    for iid in sorted(items):
        dr = items[iid].get("defaultRecipe")
        if dr is None:
            continue
        r = recipe_by_id.get(dr)
        if r is None or (r.get("out") or {}).get("item") != iid or r.get("noexp"):
            rep.add("error", "bad-default",
                    f"`{iid}`.defaultRecipe = `{dr}` is unknown, does not produce it, or is non-expandable",
                    item=iid, recipe=dr)
        elif r.get("cyc"):
            rep.add("warning", "cyclic-default",
                    f"`{iid}`.defaultRecipe = `{dr}` feeds back into its own cycle", item=iid, recipe=dr)

    # ---- orphans
    for iid in sorted(items):
        if iid not in produced_by and iid not in used_in and iid not in station_use and iid not in stations:
            rep.add("warning", "orphan",
                    f"`{iid}` ({_name(items, iid)}) is not produced, consumed or used as a station by any recipe",
                    item=iid)

    # ---- cycles
    nodes = sorted(set(edges) | {i for s in edges.values() for i in s})
    sorted_edges = {k: sorted(v) for k, v in edges.items()}
    sccs = tarjan_scc(nodes, sorted_edges)
    cyc = []
    for comp in sccs:
        members = set(comp)
        if len(comp) == 1 and comp[0] not in edges.get(comp[0], ()):
            continue
        start = min(comp)
        path = find_cycle_path(start, members, edges)
        rids = sorted({rid for a in comp for b in edges.get(a, ()) if b in members
                       for rid in edge_recipes[(a, b)]})
        # items in the SCC with no recipe escaping the SCC
        trapped = []
        for a in sorted(comp):
            escape = False
            for rid in produced_by.get(a, []):
                r = recipe_by_id.get(rid) or {}
                if r.get("noexp"):
                    continue
                if "cyc" in r:          # build.py's flag (raw items are leaves)
                    if not r["cyc"]:
                        escape = True
                        break
                    continue
                if not any((inp.get("item") in members) for inp in r.get("in") or []):
                    escape = True
                    break
            if not escape:
                trapped.append(a)
        cyc.append({"items": sorted(comp), "path": path, "recipes": rids, "trapped": trapped})
    cyc.sort(key=lambda c: (-len(c["items"]), c["items"]))
    rep.cycles = cyc
    for c in cyc:
        pretty = " -> ".join(f"{p} ({_name(items, p)})" if p == c["path"][0] else p for p in c["path"])
        kind = "self-loop" if len(c["items"]) == 1 else f"{len(c['items'])} items"
        rep.add("warning", "cycle",
                f"cycle ({kind}): {pretty}; recipes: {', '.join(c['recipes'])}",
                items=c["items"], path=c["path"], recipes=c["recipes"])
        for t in c["trapped"]:
            rep.add("info", "cycle-trapped",
                    f"`{t}` ({_name(items, t)}): every recipe feeds back into its cycle; "
                    f"the calculator must stop expanding it (treat as raw)",
                    item=t)
    return rep


# --------------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a merged GK2 planner dataset (gk2.json).")
    ap.add_argument("path", nargs="?", default=None, help="path to gk2.json (default: <project>/data/gk2.json)")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--quiet", action="store_true", help="only print the summary line")
    ap.add_argument("--limit", type=int, default=30, help="max messages per code in text output (0 = all)")
    args = ap.parse_args(argv)

    from pathlib import Path
    path = Path(args.path) if args.path else Path(__file__).resolve().parent.parent / "data" / "gk2.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"validate: cannot read {path}: {e}", file=sys.stderr)
        return 2
    rep = validate(data)
    if args.json:
        print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=1))
    elif args.quiet:
        print(rep.summary_line())
    else:
        print(rep.to_markdown(limit_per_code=args.limit or None))
        print(rep.summary_line())
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
