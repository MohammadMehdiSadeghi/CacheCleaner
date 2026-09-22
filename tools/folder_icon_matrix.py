# -*- coding: utf-8 -*-
"""folder_icon_matrix.py — find which attribute combination makes Explorer honour desktop.ini.

Theory vs reality check. The documented recipe (read-only folder + hidden/system desktop.ini)
is not being honoured here, so this tries the plausible variants in FRESH folders (a name the
shell has never cached) and reports which one the shell actually returns our icon for.

Variants tried per folder:
  A  read-only folder        + desktop.ini RHS        (the documented recipe)
  B  system folder           + desktop.ini RHS
  C  read-only + system      + desktop.ini RHS
  D  read-only folder        + desktop.ini RHS, icon referenced by index 0 and no InfoTip

Run: python tools/folder_icon_matrix.py
"""
import ctypes
import os
import shutil
import sys
import tempfile
import time
import uuid
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ICO = os.path.join(ROOT, "assets", "sparkles.ico")

shell32 = ctypes.WinDLL("shell32", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
k32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]

READONLY, HIDDEN, SYSTEM, DIRECTORY = 0x1, 0x2, 0x4, 0x10
SHGFI_ICON, SHGFI_LARGEICON = 0x100, 0x0


class SHFILEINFO(ctypes.Structure):
    _fields_ = [("hIcon", wintypes.HICON), ("iIcon", ctypes.c_int),
                ("dwAttributes", wintypes.DWORD), ("szDisplayName", ctypes.c_wchar * 260),
                ("szTypeName", ctypes.c_wchar * 80)]


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

shell32.SHGetFileInfoW.argtypes = [ctypes.c_wchar_p, wintypes.DWORD,
                                   ctypes.POINTER(SHFILEINFO), ctypes.c_uint, ctypes.c_uint]
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.c_void_p]
user32.GetDC.restype = ctypes.c_void_p
user32.GetDC.argtypes = [ctypes.c_void_p]
user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.DestroyIcon.argtypes = [ctypes.c_void_p]
gdi32.GetObjectW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.GetDIBits.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]


def signature(folder):
    """(size, avg RGB, green, tan) of the icon the shell reports for `folder`."""
    sfi = SHFILEINFO()
    if not shell32.SHGetFileInfoW(folder, 0, ctypes.byref(sfi), ctypes.sizeof(sfi),
                                  SHGFI_ICON | SHGFI_LARGEICON) or not sfi.hIcon:
        return None
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


def attrs(p):
    a = k32.GetFileAttributesW(p)
    if a == 0xFFFFFFFF:
        return "MISSING"
    return "".join(nm for bit, nm in ((READONLY, "R"), (HIDDEN, "H"), (SYSTEM, "S"),
                                      (DIRECTORY, "D")) if a & bit) or "-"


def make(base, name, folder_flags, ini_body):
    d = os.path.join(base, name)
    os.makedirs(d, exist_ok=True)
    ini = os.path.join(d, "desktop.ini")
    with open(ini, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(ini_body)
    k32.SetFileAttributesW(ini, READONLY | HIDDEN | SYSTEM)
    k32.SetFileAttributesW(d, folder_flags | DIRECTORY)
    return d, ini


def main():
    base = os.path.join(tempfile.gettempdir(), "cc_icon_matrix_" + uuid.uuid4().hex[:8])
    os.makedirs(base, exist_ok=True)
    body = "[.ShellClassInfo]\r\nIconResource=%s,0\r\n" % ICO
    body_alt = "[.ShellClassInfo]\r\nIconResource=%s,0\r\nInfoTip=test\r\n" % ICO

    cases = [
        ("A_readonly", READONLY, body),
        ("B_system", SYSTEM, body),
        ("C_both", READONLY | SYSTEM, body),
        ("D_readonly_tip", READONLY, body_alt),
        ("E_plain_control", 0, body),
    ]

    print("base:", base)
    print("icon:", ICO, os.path.exists(ICO))
    print()
    results = {}
    for name, flags, ini_body in cases:
        d, ini = make(base, name, flags, ini_body)
        time.sleep(0.3)
        sig = signature(d)
        results[name] = sig
        print("%-16s folder=%-4s ini=%-4s -> %s" % (name, attrs(d), attrs(ini), sig))

    print()
    ok = [n for n, s in results.items() if s and s[2] >= 3 and s[3] < s[2]]
    print("folders showing OUR icon:", ok or "NONE")
    if not ok:
        print("\nNo variant worked. The shell is not reading desktop.ini at all here.")
        print("Fallback that always works: put the icon ON THE SHORTCUT (already done) and/or")
        print("create a shortcut TO the folder with a custom icon.")
    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
