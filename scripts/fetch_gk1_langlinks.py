"""Fetch GK1 fandom interlanguage links (pt-br <-> en) via MediaWiki API. Writes raw JSON pages to data/raw/l10n."""
import json, sys, time, urllib.request, urllib.parse
OUT = sys.argv[1]
UA = "gk2-l10n-research/1.0 (personal companion page)"
def get(base, params):
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)
def crawl(base, lllang, tag):
    params = {"action":"query","generator":"allpages","gapnamespace":0,"gaplimit":50,
              "prop":"langlinks","lllang":lllang,"lllimit":500,"format":"json","gapfilterredir":"nonredirects"}
    pages, n = {}, 0
    while True:
        d = get(base, params)
        json.dump(d, open(f"{OUT}/{tag}_{n:03d}.json","w"), ensure_ascii=False)
        for p in d.get("query",{}).get("pages",{}).values():
            ll = [x["*"] for x in p.get("langlinks",[])]
            pages[p["title"]] = ll[0] if ll else None
        n += 1
        if "continue" not in d: break
        params.update(d["continue"]); time.sleep(0.7)
    return pages
pt = crawl("https://graveyardkeeper.fandom.com/pt-br/api.php", "en", "gk1_ptbr_langlinks")
en = crawl("https://graveyardkeeper.fandom.com/api.php", "pt-br", "gk1_en_langlinks")
json.dump({"pt_to_en": pt, "en_to_pt": en}, open(f"{OUT}/gk1_langlinks_merged.json","w"), ensure_ascii=False, indent=1)
print("pt pages", len(pt), "with en link", sum(1 for v in pt.values() if v))
print("en pages", len(en), "with pt link", sum(1 for v in en.values() if v))
