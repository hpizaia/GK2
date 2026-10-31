# Reddit demo clip (English)

Files: `gif-reddit-demo-en.gif` (540 px wide, ~18 s, loops), `reddit-demo-en.mp4` (720 px wide, H.264, same clip).
Also made the same way: `site/media/hero-en.gif` (390 px wide, ~9 s, English copy of `site/media/hero.gif`).

How they were made (2026-10-31, app v1.3.1):

1. Served `dist/` with `python3 -m http.server 8781 --bind 127.0.0.1 --directory dist` and opened `preview.html` in the Claude desktop Browser pane, mobile viewport 375x812 (screenshots at 2x = 750x1624), language EN, theme Dark.
2. Started from an empty plan (`GK.store.actions.clearGoals()`), day picker collapsed.
3. One screenshot per state: empty planner -> typing "swo" -> "sword" -> + Add Iron Sword -> quantity 3 -> Progress -> Raw materials -> Steps by station (3 positions) -> "Have it" on Iron Ore, type 5, OK (9 -> 4) -> Technologies still needed -> Days tab with today = Envy (set with `setDay("envy")`) -> Next day (Pride) -> Planner Today panel.
4. Frames copied to `frame-0001.jpg...` with duplicates for holds (10 fps), then:
   - GIF: `ffmpeg -framerate 10 -i frame-%04d.jpg -vf "scale=540:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=full[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -loop 0 out.gif`
   - MP4: `ffmpeg -framerate 10 -i frame-%04d.jpg -vf scale=720:-2:flags=lanczos -c:v libx264 -pix_fmt yuv420p -crf 23 -r 10 -movflags +faststart out.mp4`
   - Hero: same GIF command with `scale=390:-1`.
