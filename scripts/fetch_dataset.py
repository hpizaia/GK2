"""Paginate a wikily dataset list endpoint and cache each page in data/raw/.

    python3 -I scripts/fetch_dataset.py <slug> data/raw                      # English (default)
    python3 -I scripts/fetch_dataset.py <slug> data/raw/pt --locale pt-br    # Portuguese

Slugs: recipes, items, buildings, crafting-stations, technologies, alchemy-formulas, quests.
English writes api-<slug>-offsetNNNN.json + api-<slug>-all.json (unchanged since the first version).
Portuguese writes api-<slug>-pt-br-offsetNNNN.json + api-<slug>-pt-br-all.json (the all-file also records
"locale"), so it never overwrites the English cache, even in the same folder.

Locale trap: the API only answers in Portuguese for `locale=pt-br` in LOWERCASE; `pt-BR` and `pt` come back in
English without any error, and the response does not say which language it is. So --locale accepts only `en`
and `pt-br` (spellings like `pt-BR` / `pt_BR` are normalized to `pt-br`, with a warning), and a pt-br fetch is
compared with the English cache (`api-<slug>-all.json` in the output folder, its parent or data/raw/): if more
than 90% of the names are identical to the English ones, it stops with an error before writing the all-file.
"""
import argparse, json, sys, time, urllib.request, urllib.parse, os
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
BASE = "https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/{slug}/list"
ROOT = Path(__file__).resolve().parent.parent
LOCALES = ("en", "pt-br")
SAME_AS_EN_MAX = 0.90   # pt-br with more than this share of names identical to English = the API answered in English


def norm_locale(value):
    """'pt-BR', 'PT_br'... -> 'pt-br' (with a warning); anything but en / pt-br is refused."""
    loc = value.strip().lower().replace("_", "-")
    if loc not in LOCALES:
        raise argparse.ArgumentTypeError(
            f"locale {value!r} não aceito: use en ou pt-br (a API devolve inglês, sem erro, para pt e pt-BR)")
    if loc != value:
        print(f"AVISO: locale {value!r} normalizado para {loc!r} (a API só entende pt-br em minúsculas)",
              file=sys.stderr)
    return loc


def names(rows):
    return {r["key"]: r["data"]["name"] for r in rows
            if isinstance(r.get("data"), dict) and isinstance(r["data"].get("name"), str)}


def english_cache(slug, outdir):
    """The English all-file to compare a pt-br fetch with (first found)."""
    for d in (Path(outdir), Path(outdir).parent, ROOT / "data" / "raw"):
        p = d / f"api-{slug}-all.json"
        if p.is_file():
            return p
    return None


def check_not_english(slug, rows, en_names, en_path, partial):
    """Stop if the pt-br rows look English. Returns a one-line summary."""
    pt = names(rows)
    common = [k for k in pt if k in en_names]
    if not common:
        sys.exit(f"ERRO: nenhuma chave de {slug} em comum com {en_path}; não dá para conferir o idioma.")
    same = sum(1 for k in common if pt[k] == en_names[k])
    share = same / len(common)
    if share > SAME_AS_EN_MAX:
        sys.exit(f"ERRO: a API devolveu inglês; confira o locale. {same} de {len(common)} nomes de {slug} "
                 f"({share:.0%}) são iguais aos de {en_path}"
                 + (" (já na 1ª página; nada foi gravado)." if partial else " (o arquivo -all não foi gravado)."))
    return f"{same} de {len(common)} nomes iguais ao inglês ({share:.0%}; limite {SAME_AS_EN_MAX:.0%})"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 epilog="Detalhes no início do arquivo e em docs/atualizacao.md.")
    ap.add_argument("slug", help="dataset do wikily (recipes, items, buildings, crafting-stations, technologies, "
                                 "alchemy-formulas, quests)")
    ap.add_argument("outdir", help="pasta de saída (data/raw para inglês, data/raw/pt para português)")
    ap.add_argument("--locale", type=norm_locale, default="en",
                    help="en (padrão) ou pt-br; pt-BR/pt_BR viram pt-br com aviso, o resto é recusado")
    args = ap.parse_args(argv)
    slug, outdir, locale = args.slug, args.outdir, args.locale
    tag = "" if locale == "en" else f"-{locale}"

    en_names = en_path = None
    if locale != "en":
        en_path = english_cache(slug, outdir)
        if en_path is None:
            sys.exit(f"ERRO: sem o cache em inglês (api-{slug}-all.json em {outdir}, na pasta acima ou em "
                     f"data/raw/) para conferir o idioma. Busque antes em inglês: "
                     f"python3 -I scripts/fetch_dataset.py {slug} data/raw")
        en_names = names(json.loads(en_path.read_text(encoding="utf-8"))["rows"])

    limit = 120
    offset = 0
    rows = []
    total = None
    while True:
        q = urllib.parse.urlencode({"limit": limit, "offset": offset, "locale": locale, "sortField": "name", "sortDir": "asc"})
        url = BASE.format(slug=slug) + "?" + q
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
        if not r.headers.get("Content-Type", "").startswith("application/json"):
            raise SystemExit(f"non-json response for {url}")
        d = json.loads(body)
        page = d.get("rows") or []
        if en_names is not None and offset == 0 and page:
            check_not_english(slug, page, en_names, en_path, partial=True)   # fail fast, before writing anything
        path = os.path.join(outdir, f"api-{slug}{tag}-offset{offset:04d}.json")
        open(path, "wb").write(body)
        total = d.get("totalCount")
        rows.extend(page)
        print(slug, offset, len(page), total, file=sys.stderr)
        offset += len(page)
        if not page or offset >= (total or 0):
            break
        time.sleep(1.0)
    keys = [r["key"] for r in rows]
    assert len(keys) == len(set(keys)), "duplicate keys across pages"
    if total is not None and len(rows) != total:
        print(f"AVISO: {slug}: {len(rows)} linhas baixadas, mas a API diz totalCount={total}", file=sys.stderr)
    if locale == "en":
        doc = {"datasetSlug": slug, "totalCount": total, "rows": rows}
    else:
        summary = check_not_english(slug, rows, en_names, en_path, partial=False)
        print(f"{slug} {locale}: {summary}", file=sys.stderr)
        doc = {"datasetSlug": slug, "locale": locale, "totalCount": total, "rows": rows}
    with open(os.path.join(outdir, f"api-{slug}{tag}-all.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    print(slug, *([locale] if tag else []), "rows", len(rows), "total", total)


if __name__ == "__main__":
    main()
