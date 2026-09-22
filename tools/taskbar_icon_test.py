"""taskbar_icon_test.py — A/B proof of the TASKBAR icon.

Closing the app is the wrong way to find its button: Windows re-centres the icon group, so a
huge region changes and the button cannot be isolated. Instead both captures are taken with
the app RUNNING, differing only in whether our icon is applied to the window:

  state A: launched normally            -> our .ico applied to the window class
  state B: launched with CC_NO_ICONS=1  -> skipped, Windows uses pythonw.exe's icon

The taskbar layout is identical in both states, so the region that differs IS our button, and
its colours say which icon Windows actually painted.

Run: python tools/taskbar_icon_test.py
"""
import ctypes
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PYW = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                   "Programs", "Python", "Python314", "pythonw.exe")
user32 = ctypes.windll.user32


def taskbar_bbox():
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    if not hwnd:
        return None

    class R(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                    ("r", ctypes.c_long), ("b", ctypes.c_long)]
    r = R()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.l, r.t, r.r, r.b)


def running():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process | Where-Object { $_.MainWindowTitle -eq "
                          "'Cache Cleaner' } | Measure-Object).Count"],
                         capture_output=True, text=True, timeout=90)
    return (out.stdout or "").strip() not in ("", "0")


def close_app():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process | Where-Object { $_.MainWindowTitle -eq 'Cache Cleaner' } | "
                    "ForEach-Object { $_.Kill() }"], capture_output=True, text=True, timeout=90)
    for _ in range(25):
        if not running():
            return True
        time.sleep(1)
    return False


def launch_app(env_extra=None):
    if not os.path.exists(PYW):
        return False
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    subprocess.Popen([PYW, os.path.join(ROOT, "app.py")], cwd=ROOT, env=env)
    for _ in range(45):
        if running():
            time.sleep(9)          # let the taskbar settle on the final icon
            return True
        time.sleep(1)
    return False


def colour_counts(img):
    px = list(img.getdata())
    n = max(1, len(px))
    green = sum(1 for p in px if p[1] > 95 and p[1] > p[0] + 20 and p[1] > p[2] + 3)
    blue = sum(1 for p in px if p[2] > 110 and p[2] > p[1] + 25 and p[2] > p[0] + 25)
    yellow = sum(1 for p in px if p[0] > 150 and p[1] > 130 and p[2] < 110)
    return green, blue, yellow, n


def diff_columns(a, b, thresh=1):
    """Columns where the two same-size taskbar captures differ."""
    w, h = a.size
    pa, pb = a.load(), b.load()
    cols = [0] * w
    for x in range(w):
        for y in range(h):
            if pa[x, y] != pb[x, y]:
                cols[x] += 1
    return [x for x in range(w) if cols[x] > thresh]


def main():
    from PIL import ImageGrab, Image

    box = taskbar_bbox()
    if not box:
        print("no taskbar found")
        return 1

    # --- state A: our icon applied
    close_app()
    if not launch_app():
        print("could not start the app")
        return 1
    a = ImageGrab.grab(bbox=box).convert("RGB")
    a.save(os.path.join(ROOT, "assets", "_taskbar_ours.png"))

    # --- state B: our icon skipped, so Windows falls back to pythonw.exe's icon
    close_app()
    if not launch_app({"CC_NO_ICONS": "1", "CC_NO_AUMID": "1"}):
        print("could not restart the app")
        return 1
    b = ImageGrab.grab(bbox=box).convert("RGB")
    b.save(os.path.join(ROOT, "assets", "_taskbar_fallback.png"))

    # leave the app running with our icon
    close_app()

    cols = diff_columns(a, b)
    print("columns differing between the two states: %d" % len(cols))
    if not cols:
        print("the two states are pixel-identical — the window icons are NOT reaching the taskbar")
        launch_app()
        return 1

    # group into runs and keep the widest (our button)
    runs, start = [], cols[0]
    for p, q in zip(cols, cols[1:]):
        if q - p > 4:
            runs.append((start, p)); start = q
    runs.append((start, cols[-1]))
    runs.sort(key=lambda r: r[1] - r[0], reverse=True)
    x0, x1 = runs[0]
    print("runs:", [(r[0], r[1], r[1] - r[0] + 1) for r in runs[:5]])
    print("our button: x %d..%d (width %d)" % (x0, x1, x1 - x0 + 1))

    # tight crop: no padding, so neighbouring app icons cannot leak into the counts
    cellA = a.crop((x0, 0, x1 + 1, a.size[1]))
    cellB = b.crop((x0, 0, x1 + 1, b.size[1]))
    out = os.path.join(ROOT, "assets", "_taskbar_button.png")
    combo = Image.new("RGB", (cellA.size[0] * 8, cellA.size[1] * 16 + 8), (0, 0, 0))
    combo.paste(cellA.resize((cellA.size[0] * 8, cellA.size[1] * 8), Image.NEAREST), (0, 0))
    combo.paste(cellB.resize((cellB.size[0] * 8, cellB.size[1] * 8), Image.NEAREST),
                (0, cellA.size[1] * 8 + 8))
    combo.save(out)
    print("saved 8x zoom (ours on top, fallback below):", out)

    gA, bA, yA, nA = colour_counts(cellA)
    gB, bB, yB, nB = colour_counts(cellB)
    print("OURS     : green %d (%.1f%%) | blue %d (%.1f%%) | yellow %d (%.1f%%)"
          % (gA, 100.0 * gA / nA, bA, 100.0 * bA / nA, yA, 100.0 * yA / nA))
    print("FALLBACK : green %d (%.1f%%) | blue %d (%.1f%%) | yellow %d (%.1f%%)"
          % (gB, 100.0 * gB / nB, bB, 100.0 * bB / nB, yB, 100.0 * yB / nB))

    ok = gA > gB and bA < bB
    print("VERDICT:", "OUR ICON in the taskbar (and the fallback really is the python one)"
          if ok else "inconclusive — the two states do not differ the way they should")

    launch_app()          # leave the app running for the user
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
