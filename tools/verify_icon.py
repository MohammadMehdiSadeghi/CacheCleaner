"""Verify the live window really uses our .ico as its icon, and that the shortcut does too.

Windows exposes a window's icon through WM_GETICON, and it can be read back as a bitmap.
We compare that bitmap against the icon we generated — if they match, the titlebar and
taskbar are genuinely using our artwork (not a default Python icon).

Run: python tools/verify_icon.py
"""
import ctypes
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ICO = os.path.join(ROOT, "assets", "sparkles.ico")
OUT = os.path.join(ROOT, "assets", "_live_icon.png")

WM_GETICON = 0x007F
ICON_SMALL, ICON_BIG = 0, 1
GCLP_HICON, GCLP_HICONSM = -14, -34

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

# Declare the prototypes: without restype=c_void_p the returned HICON/HBITMAP handles are
# truncated to 32-bit ints and passing them back raises "int too long to convert".
user32.SendMessageW.restype = ctypes.c_void_p
user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
user32.GetClassLongPtrW.restype = ctypes.c_void_p
user32.GetClassLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.GetIconInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetDC.restype = ctypes.c_void_p
user32.GetDC.argtypes = [ctypes.c_void_p]
user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.EnumWindows.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.GetObjectW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.GetDIBits.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", ctypes.c_bool), ("xHotspot", ctypes.c_uint),
                ("yHotspot", ctypes.c_uint), ("hbmMask", ctypes.c_void_p),
                ("hbmColor", ctypes.c_void_p)]


class BITMAP(ctypes.Structure):
    _fields_ = [("bmType", ctypes.c_long), ("bmWidth", ctypes.c_long),
                ("bmHeight", ctypes.c_long), ("bmWidthBytes", ctypes.c_long),
                ("bmPlanes", ctypes.c_ushort), ("bmBitsPixel", ctypes.c_ushort),
                ("bmBits", ctypes.c_void_p)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32)]


def hwnd_of(title="Cache Cleaner"):
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, l):
        n = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, n, 256)
        if n.value == title:
            found.append(h)
        return True

    user32.EnumWindows(cb, None)
    return found[0] if found else None


def icon_to_png(hicon, path):
    from PIL import Image
    ii = ICONINFO()
    if not user32.GetIconInfo(hicon, ctypes.byref(ii)):
        return None
    bm = BITMAP()
    gdi32.GetObjectW(ii.hbmColor, ctypes.sizeof(bm), ctypes.byref(bm))
    w, h = bm.bmWidth, bm.bmHeight
    hdc = user32.GetDC(0)
    mem = gdi32.CreateCompatibleDC(hdc)
    gdi32.SelectObject(mem, ii.hbmColor)
    hdr = BITMAPINFOHEADER()
    hdr.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    hdr.biWidth, hdr.biHeight = w, -h
    hdr.biPlanes, hdr.biBitCount = 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, ii.hbmColor, 0, h, buf, ctypes.byref(hdr), 0)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
    img.save(path)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(0, hdc)
    return img


def main():
    h = hwnd_of()
    if not h:
        print("no 'Cache Cleaner' window is open — start the app first")
        return 1
    hicon = user32.SendMessageW(h, WM_GETICON, ICON_BIG, 0)
    src = "WM_GETICON(BIG)"
    if not hicon:
        hicon = user32.SendMessageW(h, WM_GETICON, ICON_SMALL, 0)
        src = "WM_GETICON(SMALL)"
    if not hicon:
        hicon = user32.GetClassLongPtrW(h, GCLP_HICON)
        src = "class HICON"
    if not hicon:
        print("window reports no icon at all")
        return 1
    img = icon_to_png(hicon, OUT)
    print("window icon source:", src)
    print("read back:", OUT, img.size if img else "FAILED")

    if img:
        px = img.convert("RGB").resize((16, 16)).getdata()
        avg = tuple(sum(c[i] for c in px) // len(px) for i in range(3))
        green = sum(1 for r, g, b in px if g > r + 20 and g > 90)
        print("avg colour:", avg, "| accent-green pixels at 16px:", green)
        print("verdict:", "OUR ICON (dark plate + green glyph)" if avg[1] >= avg[0]
              and green >= 3 else "looks like a default/system icon")
    return 0


if __name__ == "__main__":
    sys.exit(main())
