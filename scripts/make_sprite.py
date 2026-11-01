#!/usr/bin/env python3
"""Pack data/icons/*.png into one sprite sheet + manifest for the GK2 planner page.

    python3 -I scripts/make_sprite.py                          # data/icons -> data/sprite.json (+ data/sprite.png)
    python3 -I scripts/make_sprite.py --icons DIR --out PATH.json [--size N]
    python3 -I scripts/build.py                                # then rebuild: the page embeds data/sprite.json

Icons saved at an integer zoom (the wiki serves pixel art at 4x) are first reduced exactly to their native size.
Cell size: the icons' native size when every icon is at most 40 px, otherwise 32 px (override with --size).
Bigger icons are scaled down to fit (nearest neighbour: these are pixel-art icons), smaller ones are centred
unscaled. Identical icons share one cell. The file name stem is the item/station id; stems with a namespace
prefix (tech__<slug>, tp__red, branch__<key>, written by fetch_icons.py --techs; day__<id>, the HUD weekday
medallions of data/days.json) become ids tech:<slug>, tp:red, branch:<key>, day:<id>.

Manifest (data/sprite.json):
    { "image": "data:image/png;base64,...", "size": 32, "cols": 27, "rows": 26,
      "icons": { "<id>": [col, row], ... }, "count": {"files": 806, "cells": 685} }

Uses Pillow when it can be imported; otherwise a small stdlib PNG reader/writer (8-bit and palette PNGs,
non-interlaced and Adam7) that covers the wiki's icons. Exit codes: 0 ok, 1 some icons unreadable, 2 usage.
"""

import argparse
import base64
import hashlib
import json
import math
import os
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMESPACES = ("tech", "tp", "branch", "day")   # file stem "<ns>__<rest>" -> icon id "<ns>:<rest>"


def icon_id(stem):
    ns, sep, rest = stem.partition("__")
    return f"{ns}:{rest}" if sep and rest and ns in NAMESPACES else stem

try:  # optional
    from PIL import Image  # type: ignore
except Exception:  # noqa: BLE001  (ImportError, or a broken install)
    Image = None


# --------------------------------------------------------------------------- stdlib PNG

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _unfilter(raw, width, height, bpp, rowbytes, offset=0):
    """Undo PNG filters for one (sub)image. Returns (list of row bytearrays, new offset)."""
    rows, prev = [], bytearray(rowbytes)
    for _ in range(height):
        ft = raw[offset]
        line = bytearray(raw[offset + 1: offset + 1 + rowbytes])
        offset += 1 + rowbytes
        if ft == 1:
            for i in range(bpp, rowbytes):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif ft == 2:
            for i in range(rowbytes):
                line[i] = (line[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(rowbytes):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(rowbytes):
                left = line[i - bpp] if i >= bpp else 0
                up_left = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(left, prev[i], up_left)) & 255
        elif ft != 0:
            raise ValueError(f"bad filter type {ft}")
        rows.append(line)
        prev = line
    return rows, offset


def _samples(line, width, depth, channels):
    if depth == 8:
        return list(line[: width * channels])
    if depth == 16:
        return [line[i] for i in range(0, width * channels * 2, 2)]   # keep the high byte
    per = 8 // depth
    mask = (1 << depth) - 1
    out = []
    for i in range(width * channels):
        byte = line[i // per]
        shift = 8 - depth * (i % per + 1)
        out.append((byte >> shift) & mask)
    return out


def png_read(data):
    """-> (width, height, list of RGBA tuples, row-major)."""
    if not data.startswith(PNG_SIG):
        raise ValueError("not a PNG")
    pos, idat, plte, trns = 8, [], None, None
    w = h = depth = ctype = interlace = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos: pos + 4])
        kind = data[pos + 4: pos + 8]
        body = data[pos + 8: pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            plte = [tuple(body[i: i + 3]) for i in range(0, len(body), 3)]
        elif kind == b"tRNS":
            trns = body
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if w is None:
        raise ValueError("no IHDR")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(b"".join(idat))
    bpp = max(1, channels * depth // 8)

    def to_rgba(vals):
        if ctype == 6:
            return [tuple(vals[i: i + 4]) for i in range(0, len(vals), 4)]
        if ctype == 2:
            key = struct.unpack(">HHH", trns) if trns and len(trns) == 6 else None
            out = []
            for i in range(0, len(vals), 3):
                r, g, b = vals[i: i + 3]
                a = 0 if key and (r, g, b) == tuple(k >> 8 if depth == 16 else k for k in key) else 255
                out.append((r, g, b, a))
            return out
        if ctype == 3:
            out = []
            for v in vals:
                r, g, b = plte[v]
                a = trns[v] if trns and v < len(trns) else 255
                out.append((r, g, b, a))
            return out
        scale = 255 // ((1 << min(depth, 8)) - 1)
        if ctype == 0:
            key = struct.unpack(">H", trns)[0] if trns and len(trns) == 2 else None
            return [(v * scale, v * scale, v * scale, 0 if key is not None and v == key else 255) for v in vals]
        return [(vals[i] * scale,) * 3 + (vals[i + 1] * scale,) for i in range(0, len(vals), 2)]   # ctype 4

    px = [(0, 0, 0, 0)] * (w * h)
    if not interlace:
        rowbytes = (w * channels * depth + 7) // 8
        rows, _ = _unfilter(raw, w, h, bpp, rowbytes)
        out = []
        for line in rows:
            out.extend(to_rgba(_samples(line, w, depth, channels)))
        return w, h, out
    # Adam7
    passes = [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
    off = 0
    for x0, y0, dx, dy in passes:
        pw = (w - x0 + dx - 1) // dx if w > x0 else 0
        ph = (h - y0 + dy - 1) // dy if h > y0 else 0
        if not pw or not ph:
            continue
        rowbytes = (pw * channels * depth + 7) // 8
        rows, off = _unfilter(raw, pw, ph, bpp, rowbytes, off)
        for j, line in enumerate(rows):
            for i, p in enumerate(to_rgba(_samples(line, pw, depth, channels))):
                px[(y0 + j * dy) * w + x0 + i * dx] = p
    return w, h, px


def png_write(w, h, px):
    """RGBA pixels -> PNG bytes (filter chosen per row by min-sum heuristic, zlib level 9)."""
    stride = w * 4
    flat = bytearray()
    for p in px:
        flat.extend(p)
    out, prev = bytearray(), bytearray(stride)
    for y in range(h):
        line = flat[y * stride: (y + 1) * stride]
        cands = [(0, line)]
        sub = bytearray(stride)
        up = bytearray(stride)
        for i in range(stride):
            sub[i] = (line[i] - (line[i - 4] if i >= 4 else 0)) & 255
            up[i] = (line[i] - prev[i]) & 255
        cands += [(1, sub), (2, up)]
        ft, best = min(cands, key=lambda c: sum(v if v < 128 else 256 - v for v in c[1]))
        out.append(ft)
        out.extend(best)
        prev = line

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    return (PNG_SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(out), 9)) + chunk(b"IEND", b""))


# --------------------------------------------------------------------------- image ops (both backends)

def load(path):
    """-> (w, h, RGBA pixel list)."""
    if Image is not None:
        im = Image.open(path).convert("RGBA")
        return im.width, im.height, list(im.getdata())
    return png_read(Path(path).read_bytes())


def unscale(w, h, px):
    """Pixel art saved at an integer zoom (the wiki serves 4x icons): undo it exactly.
    Returns (w, h, px, k) with k = the zoom found (1 when none). Transparent pixels get RGB 0."""
    px = [p if p[3] else (0, 0, 0, 0) for p in px]
    for k in (8, 6, 5, 4, 3, 2):
        if w % k or h % k:
            continue
        ok = True
        for y in range(h):
            row = y * w
            top = (y - y % k) * w
            for x in range(w):
                if px[row + x] != px[top + x - x % k]:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            nw, nh = w // k, h // k
            return nw, nh, [px[(y * k) * w + x * k] for y in range(nh) for x in range(nw)], k
    return w, h, px, 1


def fit(w, h, px, cell):
    """Scale down (nearest) to fit cell x cell, keep aspect, centre on a transparent cell."""
    scale = min(1.0, cell / max(w, h))
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    ox, oy = (cell - nw) // 2, (cell - nh) // 2
    out = [(0, 0, 0, 0)] * (cell * cell)
    for y in range(nh):
        sy = min(h - 1, int((y + 0.5) * h / nh))
        for x in range(nw):
            sx = min(w - 1, int((x + 0.5) * w / nw))
            out[(oy + y) * cell + ox + x] = px[sy * w + sx]
    return out


def save_sheet(cols, rows, cell, cells):
    W, H = cols * cell, rows * cell
    sheet = [(0, 0, 0, 0)] * (W * H)
    for n, px in enumerate(cells):
        cx, cy = (n % cols) * cell, (n // cols) * cell
        for y in range(cell):
            base = (cy + y) * W + cx
            sheet[base: base + cell] = px[y * cell: (y + 1) * cell]
    if Image is not None:
        import io
        im = Image.new("RGBA", (W, H))
        im.putdata(sheet)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        return W, H, buf.getvalue()
    return W, H, png_write(W, H, sheet)


# --------------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="Pack icon PNGs into one sprite sheet + JSON manifest")
    ap.add_argument("--icons", default=str(ROOT / "data" / "icons"), help="folder of <id>.png files")
    ap.add_argument("--out", default=str(ROOT / "data" / "sprite.json"), help="manifest path (PNG written next to it)")
    ap.add_argument("--size", type=int, help="cell size in px (default: native if all icons <= 40 px, else 32)")
    args = ap.parse_args(argv)

    files = sorted(p for p in Path(args.icons).glob("*.png") if p.is_file())
    if not files:
        print(f"make_sprite: no PNG files in {args.icons}", file=sys.stderr)
        return 2
    imgs, bad, zooms = {}, [], {}
    for p in files:
        try:
            w, h, px, k = unscale(*load(p))
            imgs[icon_id(p.stem)] = (w, h, px)
            zooms[k] = zooms.get(k, 0) + 1
        except Exception as e:  # noqa: BLE001
            bad.append((p.name, str(e)))
    if not imgs:
        print("make_sprite: no readable icons", file=sys.stderr)
        return 1
    dims = [max(w, h) for w, h, _ in imgs.values()]
    cell = args.size or (max(dims) if max(dims) <= 40 else 32)

    cells, by_hash, icons = [], {}, {}
    for iid in sorted(imgs):
        w, h, px = imgs[iid]
        fitted = fit(w, h, px, cell)
        key = hashlib.sha1(bytes(c for p in fitted for c in p)).hexdigest()
        if key not in by_hash:
            by_hash[key] = len(cells)
            cells.append(fitted)
        icons[iid] = by_hash[key]
    cols = max(1, math.ceil(math.sqrt(len(cells))))
    rows = math.ceil(len(cells) / cols)
    W, H, png = save_sheet(cols, rows, cell, cells)
    manifest = {
        "image": "data:image/png;base64," + base64.b64encode(png).decode("ascii"),
        "size": cell, "cols": cols, "rows": rows,
        "icons": {iid: [n % cols, n // cols] for iid, n in icons.items()},
        "count": {"files": len(imgs), "cells": len(cells)},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(manifest, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(tmp, out)
    out.with_suffix(".png").write_bytes(png)
    sizes = {}
    for d in dims:
        sizes[d] = sizes.get(d, 0) + 1
    print(f"make_sprite: {len(imgs)} icons -> {len(cells)} cells of {cell}px, sheet {W}x{H}, "
          f"PNG {len(png):,} bytes, manifest {out.stat().st_size:,} bytes "
          f"({'Pillow' if Image is not None else 'stdlib PNG codec'}); zoom undone {dict(sorted(zooms.items()))}; "
          f"native sizes {dict(sorted(sizes.items()))}; {sum(1 for d in dims if d > cell)} scaled down to fit")
    for name, err in bad:
        print(f"make_sprite: unreadable {name}: {err}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
