"""Numeric QC for the icon variants: centering, glyph coverage, corner rounding,
and whether the glyph still has contrast against the plate at 32/16 px.
Run: python tools/icon_qc.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
NAMES = ["sparkles", "eraser", "layers", "database", "hard-drive", "zap", "wind"]


def report():
    from PIL import Image
    print("%-11s %8s %8s %9s %8s %8s" % ("icon", "offset", "cover%", "corner", "c32", "c16"))
    for n in NAMES:
        p = os.path.join(ASSETS, n + ".png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGBA")
        a = im.getchannel("A")
        bb = a.getbbox()
        side = im.width
        # how far the opaque plate is off-center
        off = (abs((bb[0] + bb[2]) / 2 - side / 2) + abs((bb[1] + bb[3]) / 2 - side / 2))
        # corner rounding: alpha at the very corner must be ~0
        corner = a.getpixel((2, 2))
        # glyph = pixels clearly lighter than the plate; measure its spread
        px = im.load()
        step = max(1, side // 256)
        glyph = 0
        total = 0
        xs, ys = [], []
        for y in range(0, side, step):
            for x in range(0, side, step):
                r, g, b, al = px[x, y]
                if al < 200:
                    continue
                total += 1
                if g > 120 and g > r + 25:          # accent-green pixels = glyph
                    glyph += 1
                    xs.append(x)
                    ys.append(y)
        cover = 100.0 * glyph / max(1, total)
        gcx = (min(xs) + max(xs)) / 2 if xs else 0
        gcy = (min(ys) + max(ys)) / 2 if ys else 0
        goff = abs(gcx - side / 2) + abs(gcy - side / 2)

        def contrast(size):
            small = im.resize((size, size), Image.LANCZOS)
            sp = small.load()
            vals = []
            for y in range(size):
                for x in range(size):
                    r, g, b, al = sp[x, y]
                    if al > 200:
                        vals.append(g)
            if not vals:
                return 0
            vals.sort()
            lo = vals[len(vals) // 10]
            hi = vals[-max(1, len(vals) // 10)]
            return hi - lo

        print("%-11s %8.1f %7.1f%% %9d %8d %8d" % (n, goff, cover, corner,
                                                   contrast(32), contrast(16)))
    print("\noffset: glyph center vs plate center in px (lower = better centered)")
    print("cover%%: share of plate covered by glyph (aim 8-18%%)")
    print("corner: alpha at pixel (2,2) — must be 0 for rounded corners")
    print("c32/c16: luminance spread at 32px/16px (higher = still legible when small)")


if __name__ == "__main__":
    sys.exit(report())
