# -*- coding: utf-8 -*-
"""folder_icon_diag.py — work out WHY Explorer is not showing a custom folder icon.

`desktop.ini` + read-only folder is the documented way to give a folder a custom icon, but the
shell caches icons per folder and keeps serving the generic one. This script:

1. calls SHChangeNotify(SHCNE_UPDATEDIR / SHCNE_ASSOCCHANGED) to force a re-read, then re-queries;
2. proves the mechanism itself works on a THROWAWAY folder (so a failure can be attributed to
   caching rather than to a blocked mechanism).

Run: python tools/folder_icon_diag.py
"""
import ctypes
import os
import shutil
import sys
import tempfile
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ICO = os.path.join(ROOT, "assets", "sparkles.ico")

shell32 = ctypes.WinDLL("shell32", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]

SHCNE_UPDATEDIR = 0x00001000
SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_PATHW = 0x0005
SHCNF_IDLIST = 0x0000

READONLY, HIDDEN, SYSTEM = 0x1, 0x2, 0x4

SHGFI_ICON, SHGFI_LARGEICON = 0x100, 0x0


class SHFILEINFO(ctypes.Structure):
    _fields_ = [("hIcon", wintypes.HICON), ("iIcon", ctypes.c_int),
                ("dwAttributes", wintypes.DWORD), ("szDisplayName", ctypes.c_wchar * 260),
                ("szTypeName", ctypes.c_wchar * 80)]


shell32.SHGetFileInfoW.argtypes = [ctypes.c_wchar_p, wintypes.DWORD,
                                   ctypes.POINTER(SHFILEINFO), ctypes.c_uint, ctypes.c_uint]


def icon_signature(folder):
    """Return (size, avg RGB, green px, tan px) for the icon the shell reports for `folder`."""
    sfi = SHFILEINFO()
    if not shell32.SHGetFileInfoW(folder, 0, ctypes.byref(sfi), ctypes.sizeof(sfi),
                                  SHGFI_ICON | SHGFI_LARGEICON) or not sfi.hIcon:
        return None
    # render it
    class ICONINFO(ctypes.Structure):
        _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD),
                    ("yHotspot", wintypes.DWORD), ("hbmMask", wintypes.HBITMAP),
                    ("hbmColor", wintypes.HBITMAP)]
    class BITMAP(ctypes.Structure):
        _fields_ = [("bmType", ctypes.c_long), ("bmWidth", ctypes.c_long),
                    ("bmHeight", ctypes.c_long), ("bmWidthBytes", ctypes.c_long),
                    ("bmPlanes", ctypes.c_ushort), ("bmBitsPixel", ctypes.c_ushort),
                    ("bmBits", ctypes.c_void_p)]
    class BIH(ctypes.Structure):
        _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                    ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                    ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                    ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                    ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                    ("biClrImportant", ctypes.c_uint32)]
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.c_void_p]
    gdi32.GetObjectW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
    gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
    gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    gdi32.GetDIBits.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
    gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
    user32.GetDC.restype = ctypes.c_void_p
    user32.GetDC.argtypes = [ctypes.c_void_p]
    user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    user32.DestroyIcon.argtypes = [ctypes.c_void_p]
    ii = ICONINFO()
    if not user32.GetIconInfo(sfi.hIcon, ctypes.byref(ii)):
        return None
    bm = BITMAP()
    gdi32.GetObjectW(ii.hbmColor, ctypes.sizeof(bm), ctypes.byref(bm))
    w, h = bm.bmWidth, bm.bmHeight
    hdc = user32.GetDC(0)
    mem = gdi32.CreateCompatibleDC(hdc)
    gdi32.SelectObject(mem, ii.hbmColor)
    hdr = BIH()
    hdr.biSize = ctypes.sizeof(BIH)
    hdr.biWidth, hdr.biHeight = w, -h
    hdr.biPlanes, hdr.biBitCount = 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, ii.hbmColor, 0, h, buf, ctypes.byref(hdr), 0)
    from PIL import Image
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(0, hdc)
    user32.DestroyIcon(sfi.hIcon)
    px = list(img.convert("RGB").resize((16, 16)).get_flattened_data())
    avg = tuple(sum(c[i] for c in px) // len(px) for i in range(3))
    green = sum(1 for r, g, b in px if g > r + 20 and g > 90)
    tan = sum(1 for r, g, b in px if r > b + 30 and r > 90)
    return img.size, avg, green, tan


def notify(folder):
    shell32.SHChangeNotify(SHCNE_UPDATEDIR, SHCNF_PATHW, ctypes.c_wchar_p(folder), None)
    shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)


def make_custom(folder, ico):
    ini = os.path.join(folder, "desktop.ini")
    with open(ini, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("[.ShellClassInfo]\r\nIconResource=%s,0\r\n" % ico)
    k32.SetFileAttributesW(ini, READONLY | HIDDEN | SYSTEM)
    k32.SetFileAttributesW(folder, READONLY | 0x10)
    return ini


def main():
    print("--- 1. the real project folder, after SHChangeNotify ---")
    before = icon_signature(ROOT)
    print("before notify:", before)
    notify(ROOT)
    time.sleep(2)
    after = icon_signature(ROOT)
    print("after notify :", after)
    print("changed:", before != after)

    print("\n--- 2. does the mechanism work at all? throwaway folder ---")
    tmp = os.path.join(tempfile.gettempdir(), "cc_icon_diag")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    generic = icon_signature(tmp)
    print("plain temp folder      :", generic)
    make_custom(tmp, ICO)
    notify(tmp)
    time.sleep(2)
    custom = icon_signature(tmp)
    print("temp folder + desktop.ini:", custom)
    works = custom and generic and custom[2] > generic[2] and custom[3] < generic[3]
    print("mechanism works:", bool(works))
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
