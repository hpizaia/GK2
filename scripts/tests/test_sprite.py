#!/usr/bin/env python3
"""The icon sprite: make_sprite.py and the real data/sprite.json (a lossless WebP).

Part of the build tests; run them all with:  python3 -I scripts/test_build.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True   # keep scripts/ free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))   # helpers.py, next to this file (python3 -I leaves it out)
from helpers import HERE, ROOT, load_mod, run, read_json, extract_block  # noqa: E402


sprite_mod = load_mod("gk2_make_sprite_t", HERE / "make_sprite.py")
SPRITE = ROOT / "data" / "sprite.json"


class SpriteWebp(unittest.TestCase):
    """The app's icon sprite is a lossless WebP (make_sprite.py, cwebp): same sheet as data/sprite.png, smaller."""

    @unittest.skipUnless(SPRITE.exists(), "data/sprite.json not present")
    def test_real_sprite_is_webp_of_the_manifest_size(self):
        sp = read_json(SPRITE)
        prefix = "data:image/webp;base64,"
        self.assertTrue(sp["image"].startswith(prefix), sp["image"][:40])
        webp = sprite_mod.base64.b64decode(sp["image"][len(prefix):])
        W, H = sp["cols"] * sp["size"], sp["rows"] * sp["size"]
        self.assertEqual(sprite_mod.webp_size(webp), (W, H))      # RIFF/WEBP/VP8L header: lossless, sheet size
        self.assertEqual(int.from_bytes(webp[4:8], "little") + 8, len(webp))
        png = (ROOT / "data" / "sprite.png").read_bytes()         # the PNG reference copy is the same sheet
        self.assertEqual(sprite_mod.struct.unpack(">II", png[16:24]), (W, H))
        for iid, (c, r) in sp["icons"].items():
            self.assertTrue(0 <= c < sp["cols"] and 0 <= r < sp["rows"], iid)
        for page in ("dist/index.html", "prototype/index.html"):
            if (ROOT / page).exists():
                data = json.loads(extract_block((ROOT / page).read_text(encoding="utf-8")))
                self.assertEqual(data["meta"]["sprite"]["image"], sp["image"], page)

    @unittest.skipUnless(SPRITE.exists() and shutil.which("dwebp"), "needs data/sprite.json and dwebp")
    def test_real_sprite_decodes_like_the_png(self):
        sp = read_json(SPRITE)
        with tempfile.TemporaryDirectory() as t:
            src, pam = Path(t) / "s.webp", Path(t) / "s.pam"
            src.write_bytes(sprite_mod.base64.b64decode(sp["image"].split(",", 1)[1]))
            subprocess.run(["dwebp", "-quiet", "-pam", str(src), "-o", str(pam)], check=True)
            w, h, raw = sprite_mod.pam_read(pam.read_bytes())
        pw, ph, px = sprite_mod.png_read((ROOT / "data" / "sprite.png").read_bytes())
        self.assertEqual((w, h), (pw, ph))
        self.assertTrue(raw == bytes(c for p in px for c in p), "WebP and PNG differ in some pixel")

    @unittest.skipUnless(shutil.which("cwebp") and shutil.which("dwebp"), "needs cwebp and dwebp (brew install webp)")
    def test_make_sprite_webp_is_exact_and_repeatable(self):
        with tempfile.TemporaryDirectory() as t:
            icons, nothing = Path(t) / "icons", Path(t) / "empty-path"
            icons.mkdir()
            nothing.mkdir()
            half = (200, 30, 40, 128)   # semitransparent pixels must survive exactly
            for name, colour in (("log", (120, 80, 20, 255)), ("tech__carpentry", half), ("plank", (9, 9, 9, 255))):
                px = [colour if (x + y) % 3 else (0, 0, 0, 0) for y in range(20) for x in range(20)]
                (icons / f"{name}.png").write_bytes(sprite_mod.png_write(20, 20, px))
            outs = []
            for n in (1, 2):
                rc, so, se = run(HERE / "make_sprite.py", "--icons", icons, "--out", Path(t) / f"{n}" / "sprite.json")
                self.assertEqual(rc, 0, se)
                self.assertIn("identical to the sheet", so)
                outs.append((Path(t) / f"{n}" / "sprite.json").read_bytes())
            self.assertEqual(outs[0], outs[1])                          # same icons -> same bytes
            sp = json.loads(outs[0])
            self.assertTrue(sp["image"].startswith("data:image/webp;base64,"))
            self.assertEqual(set(sp["icons"]), {"log", "tech:carpentry", "plank"})
            rc, _, se = run(HERE / "make_sprite.py", "--icons", icons, "--out", Path(t) / "p" / "sprite.json", "--png")
            self.assertEqual(rc, 0, se)
            self.assertTrue(read_json(Path(t) / "p" / "sprite.json")["image"].startswith("data:image/png;base64,"))
            p = subprocess.run([sys.executable, "-I", str(HERE / "make_sprite.py"), "--icons", str(icons),
                                "--out", str(Path(t) / "x" / "sprite.json")], capture_output=True, text=True,
                               env=dict(sprite_mod.os.environ, PATH=str(nothing)))
            self.assertEqual(p.returncode, 2)                            # no cwebp: stop, never a silent PNG
            self.assertIn("brew install webp", p.stderr)
            self.assertFalse((Path(t) / "x").exists())
            # a WebP that does not decode to the sheet is refused
            W, H, png, sheet = sprite_mod.save_sheet(1, 1, 4, [[(1, 2, 3, 255)] * 16])
            sprite_mod.webp_encode(png, W, H, sheet)
            with self.assertRaises(sprite_mod.WebpError):
                sprite_mod.webp_encode(png, W, H, [(1, 2, 3, 254)] + sheet[1:])


if __name__ == "__main__":
    unittest.main(verbosity=2)
