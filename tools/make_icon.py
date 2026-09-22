"""Icon generator for Cache Cleaner.

Builds a modern app icon (dark squircle + accent glyph) and exports it as a
multi-resolution .ico for the window, the taskbar and the desktop shortcut.

Glyphs come from lucide (ISC licensed) — real icon-library path data, downloaded
into glyphs/ by fetch_glyphs.sh, not hand-drawn approximations.

Run: python tools/make_icon.py            (all variants)
     python tools/make_icon.py sparkles   (one variant)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GLYPHS = os.path.join(HERE, "glyphs")
OUT = os.path.join(ROOT, "assets")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# palette — must match ui/index.html
BG_TOP = "#191c22"
BG_BOTTOM = "#08090b"
ACCENT = "#45d9a6"
ACCENT_DIM = "#1f8f6d"

SIZES = [256, 128, 96, 64, 48, 40, 32, 24, 20, 16]
APP_ICON = "sparkles"          # chosen glyph; assets/ also keeps the other candidates

HTML = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  html,body {{ margin:0; padding:0; width:1024px; height:1024px; background:transparent; }}
  svg {{ display:block; }}
</style></head><body>
<svg width="1024" height="1024" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.6" y2="1">
      <stop offset="0" stop-color="{bg_top}"/>
      <stop offset="1" stop-color="{bg_bottom}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.30" cy="0.24" r="0.62">
      <stop offset="0" stop-color="{accent}" stop-opacity="0.30"/>
      <stop offset="0.55" stop-color="{accent}" stop-opacity="0.07"/>
      <stop offset="1" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.20"/>
      <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.05"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0.02"/>
    </linearGradient>
    <linearGradient id="glyph" x1="0.15" y1="0" x2="0.85" y2="1">
      <stop offset="0" stop-color="#a8f7dc"/>
      <stop offset="0.42" stop-color="{accent}"/>
      <stop offset="0.78" stop-color="#35c9c0"/>
      <stop offset="1" stop-color="{accent_dim}"/>
    </linearGradient>
    <filter id="soft" x="-25%" y="-25%" width="150%" height="150%">
      <feGaussianBlur stdDeviation="26"/>
    </filter>
  </defs>

  <!-- squircle body -->
  <rect x="44" y="44" width="936" height="936" rx="222" fill="url(#bg)"/>
  <rect x="44" y="44" width="936" height="936" rx="222" fill="url(#glow)"/>
  <rect x="45.5" y="45.5" width="933" height="933" rx="220.5"
        fill="none" stroke="url(#edge)" stroke-width="3"/>

  <!-- glyph: blurred copy for the glow, then the crisp one -->
  <g transform="translate(512 512) scale({scale}) translate(-12 -12)"
     fill="none" stroke="{accent}" stroke-width="{sw}"
     stroke-linecap="round" stroke-linejoin="round" opacity="0.55" filter="url(#soft)">
    {paths}
  </g>
  <g transform="translate(512 512) scale({scale}) translate(-12 -12)"
     fill="none" stroke="url(#glyph)" stroke-width="{sw}"
     stroke-linecap="round" stroke-linejoin="round">
    {paths}
  </g>
</svg>
</body></html>
"""


def glyph_paths(name):
    """Pull the drawing commands out of a downloaded lucide svg."""
    with open(os.path.join(GLYPHS, name + ".svg"), "r", encoding="utf-8") as f:
        svg = f.read()
    body = svg[svg.index(">", svg.index("<svg")) + 1:svg.rindex("</svg>")]
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    return "\n    ".join(lines)


def build(name, scale, stroke):
    from PIL import Image
    html = HTML.format(bg_top=BG_TOP, bg_bottom=BG_BOTTOM, accent=ACCENT,
                       accent_dim=ACCENT_DIM, scale=scale, sw=stroke,
                       paths=glyph_paths(name))
    tmp_html = os.path.join(HERE, "_icon_%s.html" % name)
    tmp_png = os.path.join(HERE, "_icon_%s.png" % name)
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(html)

    for p in (tmp_png,):
        if os.path.exists(p):
            os.remove(p)

    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", "--window-size=1024,1024",
           "--default-background-color=00000000",
           "--screenshot=" + tmp_png, "file:///" + tmp_html.replace("\\", "/")]
    subprocess.run(cmd, capture_output=True, timeout=120)
    if not os.path.exists(tmp_png):
        raise SystemExit("Edge did not produce " + tmp_png)

    img = Image.open(tmp_png).convert("RGBA")
    # Edge may pad the viewport by a scrollbar's worth; crop to the squircle bbox
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    side = max(img.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))

    os.makedirs(OUT, exist_ok=True)
    ico = os.path.join(OUT, "%s.ico" % name)
    sq.resize((256, 256), Image.LANCZOS).save(
        ico, format="ICO", sizes=[(s, s) for s in SIZES if s <= 256])
    sq.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "%s.png" % name))
    for p in (tmp_html, tmp_png):
        try:
            os.remove(p)
        except OSError:
            pass
    print("%-10s -> %s (%d bytes, %d sizes)" % (name, ico, os.path.getsize(ico), len(SIZES)))
    return ico


if __name__ == "__main__":
    want = sys.argv[1:] or [APP_ICON]
    for n in want:
        build(n, scale=25.0, stroke=1.75)
