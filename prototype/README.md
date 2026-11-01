# prototype/: página de desenvolvimento (gerada)

`index.html` é o app inteiro num arquivo só, **com** o esqueleto HTML (doctype, `<head>`, `<body>`), para abrir no computador. Ele é **gerado** pelo `python3 -I scripts/build.py` a partir de `src/` e `data/`, e é regravado a cada build: **não edite à mão**, mude `src/` e rode o build de novo.

- Ver localmente: o servidor `prototype` do `.claude/launch.json` (`http://127.0.0.1:8765/`), ou `python3 -m http.server 8765 --bind 127.0.0.1 --directory prototype`.
- O `node scripts/test_calc.mjs` lê os dados embutidos neste arquivo.
- `index.html.bak` (se aparecer) é uma cópia automática do modo legado `build.py --inject`. Está no `.gitignore` (`*.bak`) e pode ser apagada.
- A página publicada como Claude Artifact é a de `dist/` (`dist/index.html`, sem esqueleto; `dist/preview.html`, com esqueleto). Veja [`docs/arquitetura.md`](../docs/arquitetura.md).
