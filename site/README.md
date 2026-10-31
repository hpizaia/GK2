# site/ — GK2 Companion landing page

A one-page, bilingual (EN default, PT-BR toggle) presentation of the app, with links to the
live artifact and to this repository.

| file | what it is |
|---|---|
| `index.html` | The page as a Claude Artifact: no doctype/html/head/body (the artifact skeleton adds them). All CSS and JS inline; only Google Fonts is loaded from outside. |
| `preview.html` | The same page wrapped in a minimal HTML skeleton, for opening locally or hosting on GitHub Pages. Generated from `index.html`; do not edit by hand. |
| `media/` | Screenshots and the hero GIF the page references by relative path, one file per language (`-en` / `-pt`). |

Copy lives in the `I18N` dict at the bottom of `index.html` (`en` and `pt`, same keys). Elements
carry `data-i18n="key"` (text), `data-i18n-alt="key"` (image alt) and `data-html` (value is HTML).
The chosen language is kept in `localStorage` (`gk2-site-lang`). The version in the footer comes from
`const VERSION` in the same script; bump it together with `/VERSION`.

The footer carries the **Credits** block (`crTitle`, `cr1`–`cr5`, `crAsk`): fan project, free and
non-profit, not affiliated, made with Claude Code, © Lazy Bear Games / tinyBuild, recipe data from the
Wikily wiki, removal on request via GitHub issues. Keep it in step with the "Credits and rights"
section of the main README.

## Media the page expects

Every picture exists once per language, and the page shows the one that matches the chosen language:

| English | Portuguese | what it shows |
|---|---|---|
| `media/hero-en.gif` | `media/hero-pt.gif` | hero animation in the phone frame (360×780) |
| `media/planner-phone-en.png` | `media/planner-phone-pt.png` | `#plan`: goals, progress, start of raw materials |
| `media/recipes-phone-en.png` | `media/recipes-phone-pt.png` | `#recipes` with the Master Sword detail open |
| `media/tech-phone-en.png` | `media/tech-phone-pt.png` | `#tech`: the technology tree |
| `media/days-phone-en.png` | `media/days-phone-pt.png` | `#days`: the week wheel with a day and counter set |
| `media/desktop-en.png` | `media/desktop-pt.png` | the planner at desktop width |

Phone shots are 750×1624 (a 375×812 viewport at 2x) and are shown in a 9:19 frame, cropped from the
top; the desktop shot is 2880×1800 (1440×900 at 2x) in a 16:10 frame. All are dark theme with the
demo plan (3 Iron Sword, 2 Beehive, 6 Conveyor Belt; Day of Wrath, counter 61).

How the switch picks media: each `<img>` in the hero and in `#screens` has `data-src-en` and
`data-src-pt`; `src` starts on the English file (the default language), and `apply(lang)` sets
`img.src` from `data-src-<lang>`. A file that fails to load shows a styled placeholder with its
caption instead of a broken image. The hero is marked `data-fallback`: if `hero-en.gif` fails, it
loads `hero-pt.gif` first and only shows the placeholder if that fails too.

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

To look at it locally, serve the folder (the media already sit in `media/`):

```sh
python3 -m http.server 8770 --bind 127.0.0.1 --directory .   # open http://127.0.0.1:8770/preview.html
```

## Publish as a Claude Artifact

Publish `site/index.html` with the Artifact tool and map each media file from `site/media/` with
`files` (the key is the path the page uses):

```json
{
  "file_path": "site/index.html",
  "icon": "map",
  "description": "A free, fan-made crafting planner for Graveyard Keeper 2, in English and Brazilian Portuguese.",
  "files": {
    "media/hero-en.gif":           "site/media/hero-en.gif",
    "media/hero-pt.gif":           "site/media/hero-pt.gif",
    "media/planner-phone-en.png":  "site/media/planner-phone-en.png",
    "media/planner-phone-pt.png":  "site/media/planner-phone-pt.png",
    "media/recipes-phone-en.png":  "site/media/recipes-phone-en.png",
    "media/recipes-phone-pt.png":  "site/media/recipes-phone-pt.png",
    "media/tech-phone-en.png":     "site/media/tech-phone-en.png",
    "media/tech-phone-pt.png":     "site/media/tech-phone-pt.png",
    "media/days-phone-en.png":     "site/media/days-phone-en.png",
    "media/days-phone-pt.png":     "site/media/days-phone-pt.png",
    "media/desktop-en.png":        "site/media/desktop-en.png",
    "media/desktop-pt.png":        "site/media/desktop-pt.png"
  }
}
```

Later updates: publish the same `file_path` again (or pass the artifact's `url` from another
session); files left out of `files` are kept, so only list media that changed. Keep each file under
15 MB and the whole page under 16 MB. The artifact starts private; share it from the page's menu.

## Publish on GitHub Pages

1. Make a folder for Pages (for example `gh-pages` branch root, or `/docs` if Pages serves from there).
2. Copy `site/preview.html` there as `index.html`.
3. Copy `site/media/*` into a `media/` folder next to it.
4. Enable Pages in the repository settings for that branch/folder.

The page has no build step and no external scripts; only the Google Fonts stylesheet is fetched.
