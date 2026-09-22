# -*- coding: utf-8 -*-
"""Fix the folder-icon attributes through the Win32 API.

`attrib.exe +s` refuses to touch a file that is already hidden ("Not resetting hidden
file"), so desktop.ini never gets the SYSTEM bit — and Explorer only parses desktop.ini when
that file carries BOTH hidden and system. SetFileAttributesW has no such reservation.

Run: python tools/fix_folder_icon_attrs.py
"""
import ctypes
import os

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.SetFileAttributesW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
k32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]

READONLY, HIDDEN, SYSTEM, DIRECTORY = 0x1, 0x2, 0x4, 0x10
FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INI = os.path.join(FOLDER, "desktop.ini")


def show(p):
    a = k32.GetFileAttributesW(p)
    if a == 0xFFFFFFFF:
        return "MISSING"
    names = [nm for bit, nm in ((READONLY, "R"), (HIDDEN, "H"),
                                (SYSTEM, "S"), (DIRECTORY, "D")) if a & bit]
    return "0x%X (%s)" % (a, "".join(names) or "-")


def main():
    print("ini before   :", show(INI))
    ok = k32.SetFileAttributesW(INI, READONLY | HIDDEN | SYSTEM)
    print("SetFileAttributes(ini, R|H|S) ->", bool(ok),
          "| last error:", ctypes.get_last_error())
    print("ini after    :", show(INI))

    print("folder before:", show(FOLDER))
    ok = k32.SetFileAttributesW(FOLDER, READONLY | DIRECTORY)
    print("SetFileAttributes(folder, R|D) ->", bool(ok),
          "| last error:", ctypes.get_last_error())
    print("folder after :", show(FOLDER))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
