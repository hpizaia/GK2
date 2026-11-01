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
`const VERSION` in the same script (and `#ver` in the footer markup); `scripts/release.py` sets both to `/VERSION`.

Page order: hero (subtitle with the phone-next-to-the-game pitch, the app button, a trust line and a
one-line personal note), what it does, screenshots, save your progress / home screen, how it's built, a
final "Open the app" block (`fnTitle`, `fnNote`), footer.

The footer carries the **Credits** block (`crTitle`, `cr1`–`cr5`, `crAsk`): fan project, free and
non-profit, not affiliated, made with Claude Code (the data is not AI-made), © Lazy Bear Games / tinyBuild, recipe data from the
Wikily wiki, removal on request via GitHub issues. Keep it in step with the "Credits and rights"
section of the main README.

## Media the page expects

Every picture exists once per language, and the page shows the one that matches the chosen language:

| English | Portuguese | size | what it shows |
|---|---|---|---|
| `media/hero-en.gif` | `media/hero-pt.gif` | 390×844 / 360×780 | hero animation in the phone frame |
| `media/hero-en-still.webp` | `media/hero-pt-still.webp` | same as the GIF | one frame of the hero GIF (goals filled in), shown instead of the GIF when the visitor asks for reduced motion |
| `media/planner-phone-en.webp` | `media/planner-phone-pt.webp` | 480×1039 | `#plan`: the Today line, goals, start of raw materials |
| `media/recipes-phone-en.webp` | `media/recipes-phone-pt.webp` | 480×1039 | `#recipes` with the Supply: Vegetables detail open (grouped recipe, quality stars) |
| `media/tech-phone-en.webp` | `media/tech-phone-pt.webp` | 480×1039 | `#tech`: the technology tree |
| `media/days-phone-en.webp` | `media/days-phone-pt.webp` | 480×1039 | `#days`: the week wheel with a day and counter set |
| `media/desktop-en.webp` | `media/desktop-pt.webp` | 2176×1360 | the planner at desktop width (hidden on screens under 600 px) |

Phone shots are captured at 750×1624 (a 375×812 viewport at 2x), then saved as WebP 480 px wide
(quality 80), and shown in a 9:19 frame, cropped from the top. The desktop shot is captured at 2880×1800
(1440×900 at 2x) and saved as WebP 2176 px wide, in a 16:10 frame. All are dark theme with the demo plan
(2 Beehive, 4 Wine, 3 Iron Sword; Sand ticked as owned; Day of Wrath, counter 61, one task done; 11 Building
techs researched), recorded on v1.8.4. Converting a new capture:

```sh
ffmpeg -i planner-phone-en.png -vf scale=480:-1 -c:v libwebp -quality 80 planner-phone-en.webp
ffmpeg -i desktop-en.png -vf scale=2176:-1:flags=lanczos -c:v libwebp -quality 80 desktop-en.webp
# hero still: pick a frame with the plan filled in (frame 7 of hero-en.gif and of hero-pt.gif today)
ffmpeg -i hero-en.gif -vf "select=eq(n\,7)" -frames:v 1 -c:v libwebp -quality 82 hero-en-still.webp
```

When a hero GIF is re-recorded, extract its still again.

The hero GIFs (v1.8.4) follow one script in both languages: the plan starts with Beehive and Wine, search "sword" /
"espada", add Iron Sword, + twice to 3, cut to the raw materials, tick Sand (it moves to "You already have"), cut to
the steps. 11 frames, 96 colours without dithering (`palettegen` + `paletteuse=dither=none:diff_mode=rectangle`), which
keeps them near 560 KB (EN) and 460 KB (PT). Frames are captured with headless Chrome at 1x on a 390×844 (EN) or
360×780 (PT) viewport, with the plan seeded in `localStorage` (`gk2-companion`).

How the switch picks media: each `<img>` in the hero and in `#screens` has `data-src-en` and
`data-src-pt`. The screenshots' `src` starts on the English file (they are `loading="lazy"`, so only the
language in use is fetched), and `apply(lang)` sets `img.src` from `data-src-<lang>`. The hero `<img>` has
**no** `src`: a small inline script right after it picks the language (saved choice, else the browser
language) and sets `src` while the page is parsed, so a visitor downloads only one GIF; it also has
`data-still-en` / `data-still-pt`, used instead of the GIF under `prefers-reduced-motion: reduce`. A
`<noscript>` copy shows the English GIF without JavaScript. A file that fails to load shows a styled
placeholder with its caption instead of a broken image. The hero is marked `data-fallback`: if the English
file fails, it loads the Portuguese one first and only shows the placeholder if that fails too.

## Regenerate preview.html

After editing `index.html` (`scripts/release.py` already does this when it bumps the version, and
`scripts/check.py` fails while `preview.html` is stale):

```sh
python3 -I scripts/site_preview.py           # from the project root; --check only compares
```

To look at it locally, serve the folder (the media already sit in `media/`):

```sh
python3 -m http.server 8770 --bind 127.0.0.1 --directory site   # from the project root; open http://127.0.0.1:8770/preview.html
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
    "media/hero-en.gif":              "site/media/hero-en.gif",
    "media/hero-pt.gif":              "site/media/hero-pt.gif",
    "media/hero-en-still.webp":       "site/media/hero-en-still.webp",
    "media/hero-pt-still.webp":       "site/media/hero-pt-still.webp",
    "media/planner-phone-en.webp":    "site/media/planner-phone-en.webp",
    "media/planner-phone-pt.webp":    "site/media/planner-phone-pt.webp",
    "media/recipes-phone-en.webp":    "site/media/recipes-phone-en.webp",
    "media/recipes-phone-pt.webp":    "site/media/recipes-phone-pt.webp",
    "media/tech-phone-en.webp":       "site/media/tech-phone-en.webp",
    "media/tech-phone-pt.webp":       "site/media/tech-phone-pt.webp",
    "media/days-phone-en.webp":       "site/media/days-phone-en.webp",
    "media/days-phone-pt.webp":       "site/media/days-phone-pt.webp",
    "media/desktop-en.webp":          "site/media/desktop-en.webp",
    "media/desktop-pt.webp":          "site/media/desktop-pt.webp"
  }
}
```

Later updates: publish the same `file_path` again (or pass the artifact's `url` from another
session); files left out of `files` are kept, so only list media that changed, and remove a file that is
no longer used by mapping its path to `null` (for example `"media/desktop-en.png": null`). Keep each file under
15 MB and the whole page under 16 MB. The artifact starts private; share it from the page's menu.

## Publish on GitHub Pages

1. Make a folder for Pages (for example `gh-pages` branch root, or `/docs` if Pages serves from there).
2. Copy `site/preview.html` there as `index.html`.
3. Copy `site/media/*` into a `media/` folder next to it.
4. Enable Pages in the repository settings for that branch/folder.

The page has no build step and no external scripts; only the Google Fonts stylesheet is fetched.
