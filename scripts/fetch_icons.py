#!/usr/bin/env python3
"""Download every distinct icon used by the GK2 planner into data/icons/<id>.png.

Reads the merged dataset (data/gk2.json by default: items[].icon and stations[].icon), downloads each
distinct URL once, politely (at most --rate requests per second, default 5), and writes one PNG per
item/station id. Ids that share a URL get a copy of the same bytes. Existing files are skipped, so the
script can be re-run to resume. Python 3 stdlib only.

    python3 -I scripts/fetch_icons.py                    # data/gk2.json -> data/icons/
    python3 -I scripts/fetch_icons.py --dry-run          # list what would be downloaded
    python3 -I scripts/fetch_icons.py --data PATH --out DIR --rate 2
    python3 -I scripts/fetch_icons.py --techs            # also the tech-tree icons listed in data/techs.json

--techs [PATH] (opt-in) adds the `icons` map of data/techs.json (scripts/build_techs.py): namespaced ids such as
`tech:<slug>`, `tp:red` and `branch:<key>`, for icons no item/station shares. A `:` in an id becomes `__` in the
file name (tech:archers-tower -> tech__archers-tower.png); scripts/make_sprite.py maps it back.

Exit codes: 0 ok, 1 some downloads failed (listed on stderr), 2 usage / IO error.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) GK2-planner-icon-fetch/1.0 (personal, polite)"
ALLOWED_HOSTS = {"media.wikily.gg"}
PNG_SIG = b"\x89PNG\r\n\x1a\n"


def collect(ds):
    """-> {url: [ids...]} for items and stations with an icon URL (ids sorted, items before stations)."""
    by_url = {}
    for section in ("items", "stations"):
        for iid in sorted(ds.get(section) or {}):
            url = (ds[section][iid] or {}).get("icon")
            if isinstance(url, str) and url.strip():
                ids = by_url.setdefault(url.strip(), [])
                if iid not in ids:
                    ids.append(iid)
    return by_url


def collect_techs(doc, by_url=None):
    """Add data/techs.json `icons` ({id: url}) to a {url: [ids...]} map."""
    by_url = {} if by_url is None else by_url
    for iid, url in sorted((doc.get("icons") or {}).items()):
        if isinstance(url, str) and url.strip():
            ids = by_url.setdefault(url.strip(), [])
            if iid not in ids:
                ids.append(iid)
    return by_url


def safe_name(iid):
    iid = iid.replace(":", "__")   # namespaced ids (tech:<slug>, tp:red) -> tech__<slug>.png
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in iid) + ".png"


def fetch(url, timeout=30, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/png,image/*;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            if not data.startswith(PNG_SIG):
                raise ValueError("not a PNG")
            return data
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = e
            code = getattr(e, "code", None)
            if code in (403, 404, 410):
                break
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(last))


def write_atomic(path, data):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Download GK2 item/station icons into data/icons/<id>.png")
    ap.add_argument("--data", default=str(ROOT / "data" / "gk2.json"), help="merged dataset (build.py output)")
    ap.add_argument("--out", default=str(ROOT / "data" / "icons"), help="output folder")
    ap.add_argument("--rate", type=float, default=5.0, help="max requests per second (default 5)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--techs", nargs="?", const=str(ROOT / "data" / "techs.json"), metavar="PATH",
                    help="also fetch the non-item icons in techs.json `icons` (default PATH: data/techs.json)")
    args = ap.parse_args(argv)

    try:
        ds = json.loads(Path(args.data).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"fetch_icons: cannot read {args.data}: {e}", file=sys.stderr)
        return 2
    by_url = collect(ds)
    if args.techs:
        try:
            collect_techs(json.loads(Path(args.techs).read_text(encoding="utf-8")), by_url)
        except (OSError, ValueError) as e:
            print(f"fetch_icons: cannot read {args.techs}: {e}", file=sys.stderr)
            return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gap = 1.0 / max(0.1, min(args.rate, 5.0))     # never faster than 5 req/s

    todo, skipped, bad_host = [], 0, []
    for url, ids in by_url.items():
        host = urllib.parse.urlsplit(url).hostname or ""
        if urllib.parse.urlsplit(url).scheme != "https" or host not in ALLOWED_HOSTS:
            bad_host.append(url)
            continue
        missing = [i for i in ids if not (out / safe_name(i)).exists()]
        if not missing:
            skipped += 1
            continue
        have = next((out / safe_name(i) for i in ids if (out / safe_name(i)).exists()), None)
        if have is not None:   # another id already has this URL's bytes: copy, no request
            data = have.read_bytes()
            for i in missing:
                write_atomic(out / safe_name(i), data)
            skipped += 1
            continue
        todo.append((url, missing))

    print(f"fetch_icons: {len(by_url)} distinct URLs, {sum(len(v) for v in by_url.values())} ids; "
          f"{skipped} already present, {len(todo)} to download"
          + (f", {len(bad_host)} skipped (not https://{'/'.join(sorted(ALLOWED_HOSTS))})" if bad_host else ""))
    if args.dry_run:
        for url, ids in todo:
            print(f"  {', '.join(ids)}  <-  {url}")
        return 0

    failed = []
    last = 0.0
    for n, (url, ids) in enumerate(todo, 1):
        wait = last + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        last = time.monotonic()
        try:
            data = fetch(url)
        except RuntimeError as e:
            failed.append((ids, url, str(e)))
            continue
        for i in ids:
            write_atomic(out / safe_name(i), data)
        if n % 50 == 0 or n == len(todo):
            print(f"fetch_icons: {n}/{len(todo)}")
    for ids, url, err in failed:
        print(f"fetch_icons: FAILED {', '.join(ids)}: {err} ({url})", file=sys.stderr)
    print(f"fetch_icons: done, {len(todo) - len(failed)} downloaded, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
