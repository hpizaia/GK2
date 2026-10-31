"""Paginate a wikily dataset list endpoint and cache each page in data/raw/."""
import json, sys, time, urllib.request, urllib.parse, os
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
BASE = "https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/{slug}/list"
slug, outdir = sys.argv[1], sys.argv[2]
limit = 120
offset = 0
rows = []
total = None
while True:
    q = urllib.parse.urlencode({"limit": limit, "offset": offset, "locale": "en", "sortField": "name", "sortDir": "asc"})
    url = BASE.format(slug=slug) + "?" + q
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    if not r.headers.get("Content-Type", "").startswith("application/json"):
        raise SystemExit(f"non-json response for {url}")
    path = os.path.join(outdir, f"api-{slug}-offset{offset:04d}.json")
    open(path, "wb").write(body)
    d = json.loads(body)
    total = d.get("totalCount")
    page = d.get("rows") or []
    rows.extend(page)
    print(slug, offset, len(page), total, file=sys.stderr)
    offset += len(page)
    if not page or offset >= (total or 0):
        break
    time.sleep(1.0)
keys = [r["key"] for r in rows]
assert len(keys) == len(set(keys)), "duplicate keys across pages"
json.dump({"datasetSlug": slug, "totalCount": total, "rows": rows}, open(os.path.join(outdir, f"api-{slug}-all.json"), "w"), ensure_ascii=False)
print(slug, "rows", len(rows), "total", total)
