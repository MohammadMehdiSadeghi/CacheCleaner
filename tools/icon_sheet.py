"""Render every icon variant into one contact sheet so a human (or vision model) can
pick the best one. Run: python tools/icon_sheet.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")
NAMES = ["sparkles", "eraser", "layers", "database", "hard-drive", "zap", "wind"]
CELL = 240
PAD = 16
COLS = 4


def main():
    from PIL import Image, ImageDraw
    imgs = []
    for n in NAMES:
        p = os.path.join(ASSETS, n + ".png")
        if os.path.exists(p):
            imgs.append((n, Image.open(p).convert("RGBA")))
    if not imgs:
        raise SystemExit("no icons in assets/ — run tools/make_icon.py first")

    rows = (len(imgs) + COLS - 1) // COLS
    W = COLS * (CELL + PAD) + PAD
    H = rows * (CELL + PAD + 26) + PAD
    sheet = Image.new("RGBA", (W, H), (12, 13, 16, 255))
    d = ImageDraw.Draw(sheet)
    for i, (n, im) in enumerate(imgs):
        r, c = divmod(i, COLS)
        x = PAD + c * (CELL + PAD)
        y = PAD + r * (CELL + PAD + 26)
        sheet.alpha_composite(im.resize((CELL, CELL), Image.LANCZOS), (x, y))
        d.text((x + 4, y + CELL + 6), "%s  %dx%d" % (n, im.width, im.height), fill=(150, 155, 165, 255))
    out = os.path.join(ASSETS, "_sheet.png")
    sheet.convert("RGB").save(out, quality=92)
    print(out, sheet.size)


if __name__ == "__main__":
    sys.exit(main())
