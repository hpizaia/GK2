# site/ — GK2 Companion landing page

A one-page, bilingual (EN default, PT-BR toggle) presentation of the app, with links to the
live artifact and to this repository.

| file | what it is |
|---|---|
| `index.html` | The page as a Claude Artifact: no doctype/html/head/body (the artifact skeleton adds them). All CSS and JS inline; only Google Fonts is loaded from outside. |
| `preview.html` | The same page wrapped in a minimal HTML skeleton, for opening locally or hosting on GitHub Pages. Generated from `index.html`; do not edit by hand. |
| `media/` | Screenshots and GIFs the page references by relative path. Empty in git; the files are produced into `docs/media/`. |

Copy lives in the `I18N` dict at the bottom of `index.html` (`en` and `pt`, same keys). Elements
carry `data-i18n="key"` (text), `data-i18n-alt="key"` (image alt) and `data-html` (value is HTML).
The chosen language is kept in `localStorage` (`gk2-site-lang`). The version in the footer comes from
`const VERSION` in the same script; bump it together with `/VERSION`.

The footer carries the **Credits** block (`crTitle`, `cr1`–`cr5`, `crAsk`): fan project, free and
non-profit, not affiliated, made with Claude Code, © Lazy Bear Games / tinyBuild, recipe data from the
Wikily wiki, removal on request via GitHub issues. Keep it in step with the "Credits and rights"
section of the main README.

## Media the page expects

`media/hero.gif`, `media/planner-phone.png`, `media/recipes-phone.png`, `media/tech-phone.png`,
`media/days-phone.png`, `media/desktop.png`. Phone shots are shown in a 9:19 frame (cropped from the
top, so ~390×844 works); the desktop shot in a 16:10 frame (~1440×900). A missing file shows a
styled placeholder with its caption instead of a broken image.

## Regenerate preview.html

After editing `index.html`:

```sh
cd GK2/site
python3 -I - <<'PY'
s = open('index.html', encoding='utf-8').read()
i = s.index('</style>') + len('</style>')
head, body = s[:i], s[i:]
open('preview.html', 'w', encoding='utf-8').write(
  '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  '<!-- Generated from index.html (the Claude Artifact page). Do not edit by hand; see README.md. -->\n'
  '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
  'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
  + head.strip() + '\n</head>\n<body>\n' + body.strip() + '\n</body>\n</html>\n')
PY
```

To look at it locally, copy the media next to it and serve the folder:

```sh
cp ../docs/media/* media/
python3 -m http.server 8770 --bind 127.0.0.1 --directory .   # open http://127.0.0.1:8770/preview.html
```

## Publish as a Claude Artifact

Publish `site/index.html` with the Artifact tool and map each media file from `docs/media/` with
`files` (the key is the path the page uses):

```json
{
  "file_path": "site/index.html",
  "icon": "map",
  "description": "A free, fan-made crafting planner for Graveyard Keeper 2, in English and Brazilian Portuguese.",
  "files": {
    "media/hero.gif":           "docs/media/hero.gif",
    "media/planner-phone.png":  "docs/media/planner-phone.png",
    "media/recipes-phone.png":  "docs/media/recipes-phone.png",
    "media/tech-phone.png":     "docs/media/tech-phone.png",
    "media/days-phone.png":     "docs/media/days-phone.png",
    "media/desktop.png":        "docs/media/desktop.png"
  }
}
```

Later updates: publish the same `file_path` again (or pass the artifact's `url` from another
session); files left out of `files` are kept, so only list media that changed. Keep each file under
15 MB and the whole page under 16 MB. The artifact starts private; share it from the page's menu.

## Publish on GitHub Pages

1. Make a folder for Pages (for example `gh-pages` branch root, or `/docs` if Pages serves from there).
2. Copy `site/preview.html` there as `index.html`.
3. Copy `docs/media/*` into a `media/` folder next to it.
4. Enable Pages in the repository settings for that branch/folder.

The page has no build step and no external scripts; only the Google Fonts stylesheet is fetched.
