# -*- coding: utf-8 -*-
"""check_folder_icon.py — read the folder icon the way EXPLORER does.

`SHGetFileInfoW` is the wrong API for this question: it returns the generic folder icon for a
directory and does NOT honour desktop.ini, so a working setup looks broken (and every variant in
the matrix "failed" because the measurement was blind).

Explorer draws a folder's icon through the shell namespace:
    SHGetDesktopFolder -> IShellFolder::ParseDisplayName -> GetUIObjectOf(IExtractIconW)
    -> GetIconLocation + Extract
This script does exactly that and reports the icon location string the shell resolves, which
proves whether desktop.ini was read at all.

Run: python tools/check_folder_icon.py [folder]
"""
import ctypes
import os
import sys
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ole32 = ctypes.WinDLL("ole32")
shell32 = ctypes.WinDLL("shell32")
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

# --- minimal COM plumbing -------------------------------------------------
ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
ole32.CoUninitialize.argtypes = []
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, s):
        super().__init__()
        ole32.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(self))


ole32.CLSIDFromString.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(GUID)]

IID_IShellFolder = GUID("{000214E6-0000-0000-C000-000000000046}")
IID_IExtractIconW = GUID("{000214F9-0000-0000-C000-000000000046}")

# IShellFolder vtable order (after IUnknown): ParseDisplayName is index 3
VT_PARSE_DISPLAY_NAME = 3
VT_GET_UI_OBJECT_OF = 10          # index 10 in IShellFolder's vtable

# IExtractIconW: GetIconLocation index 3, Extract index 4
VT_GET_ICON_LOCATION = 3
VT_EXTRACT = 4


def _vt(ptr, index, restype, argtypes):
    """Build a callable for vtable slot `index` of the COM object at `ptr`."""
    vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0]
    fn_ptr = ctypes.cast(vtable, ctypes.POINTER(ctypes.c_void_p))[index]
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(fn_ptr)


def folder_icon_location(folder):
    """Return (location_string, index, flags) that Explorer would use for `folder`."""
    hr = ole32.CoInitializeEx(None, 0x2)      # APARTMENTTHREADED
    try:
        desktop = ctypes.c_void_p()
        hr = shell32.SHGetDesktopFolder(ctypes.byref(desktop))
        if hr != 0:
            return None

        # ParseDisplayName(pszDisplayName, pbc, pszName, pchEaten, ppidl, pdwAttributes)
        pidl = ctypes.c_void_p()
        eaten = ctypes.c_ulong(0)
        attrs = ctypes.c_ulong(0)
        parse = _vt(desktop, VT_PARSE_DISPLAY_NAME, ctypes.HRESULT,
                    [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_wchar_p,
                     ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_void_p),
                     ctypes.POINTER(ctypes.c_ulong)])
        try:
            # (this, hwndOwner, pbc, pszDisplayName, pchEaten, ppidl, pdwAttributes)
            hr = parse(desktop, None, None, folder, ctypes.byref(eaten),
                       ctypes.byref(pidl), ctypes.byref(attrs))
        except OSError as e:
            print("ParseDisplayName failed:", e)
            return None
        if hr != 0 or not pidl:
            print("ParseDisplayName returned", hr)
            return None

        # GetUIObjectOf(hwndOwner, cidl=1, apidl, riid, rgfReserved, ppv)
        extract = ctypes.c_void_p()
        one = (ctypes.c_void_p * 1)(pidl)
        getui = _vt(desktop, VT_GET_UI_OBJECT_OF, ctypes.HRESULT,
                    [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p),
                     ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)])
        try:
            hr = getui(desktop, None, 1, one, ctypes.byref(IID_IExtractIconW),
                       None, ctypes.byref(extract))
        except OSError as e:
            print("GetUIObjectOf failed:", e)
            return None
        if hr != 0 or not extract:
            print("GetUIObjectOf returned", hr)
            return None

        # GetIconLocation(uFlags, pszIconFile, cchMax, piIndex, pwFlags)
        buf = ctypes.create_unicode_buffer(260)
        index = ctypes.c_int(0)
        flags = ctypes.c_uint(0)
        getloc = _vt(extract, VT_GET_ICON_LOCATION, ctypes.HRESULT,
                     [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint,
                      ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_uint)])
        try:
            hr = getloc(extract, 0, buf, 260, ctypes.byref(index), ctypes.byref(flags))
        except OSError as e:
            print("GetIconLocation failed:", e)
            return None
        if hr != 0:
            print("GetIconLocation returned", hr)
            return None
        return buf.value, index.value, flags.value
    finally:
        ole32.CoUninitialize()


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else ROOT
    ini = os.path.join(folder, "desktop.ini")
    print("folder      :", folder)
    print("desktop.ini :", "present" if os.path.exists(ini) else "MISSING")
    if os.path.exists(ini):
        with open(ini, encoding="utf-8") as f:
            for line in f.read().splitlines():
                print("              |", line)

    res = folder_icon_location(folder)
    print()
    if not res:
        print("could not query the shell for this folder's icon")
        return 1
    loc, idx, flags = res
    print("shell says the icon comes from:")
    print("   location :", loc or "(empty - shell default)")
    print("   index    :", idx, "| flags:", hex(flags))

    ours = os.path.join(ROOT, "assets", "sparkles.ico").lower()
    ok = bool(loc) and loc.lower().startswith(ours[: len(loc) - 2] if loc else "") and \
        "sparkles" in loc.lower()
    print()
    print("VERDICT:", "OUR ICON (desktop.ini was read)" if ok
          else "shell is NOT using our .ico for this folder")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
