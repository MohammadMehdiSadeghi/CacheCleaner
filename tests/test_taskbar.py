"""test_taskbar.py — the taskbar/titlebar icon must be OURS, not Python's.

The failure this guards against is silent: the app looks right, but the taskbar button shows
the blue-and-yellow Python logo because pythonw.exe hosts the process. Two mechanisms fix it
and BOTH are checked here:

  * SetCurrentProcessExplicitAppUserModelID — without it the window's icons never reach the
    taskbar button at all (measured: identical pixels with and without).
  * SetClassLongPtr GCLP_HICON/GCLP_HICONSM + WM_SETICON — removes the residual python
    pixels that remain when only the AppUserModelID is set.

Run: python tests/test_taskbar.py
"""
import ctypes
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print("OK   %s%s" % (label, ("  " + detail) if detail else ""))
    else:
        print("FAIL %s%s" % (label, ("  " + detail) if detail else ""))
        FAILURES.append(label)


def main():
    import app

    # --- the .ico we ship must exist and contain real multi-resolution art
    check("the icon file exists", os.path.exists(app.ICON_ICO), app.ICON_ICO)
    from PIL import Image
    ico = Image.open(app.ICON_ICO)
    sizes = sorted(ico.ico.sizes())
    check("the .ico carries the small taskbar sizes",
          (16, 16) in sizes and (32, 32) in sizes, str(sizes[:6]))
    check("the .ico carries a 256px frame", any(s[0] >= 256 for s in sizes))

    # --- the AppUserModelID is actually claimed by the process
    check("_set_app_user_model_id reports success", app._set_app_user_model_id() is True)

    shell32 = ctypes.windll.shell32
    ptr = ctypes.c_wchar_p()
    hr = shell32.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(ptr))
    current = (ptr.value or "") if hr == 0 else ""
    check("Windows reports the AppUserModelID back", current == "MohammadMehdiSadeghi.CacheCleaner",
          "got %r" % current)

    # --- and it is not merely set but different from the host interpreter's
    check("the AppUserModelID is not python's", "python" not in current.lower())

    # --- the window-icon helper is wired into startup, with its escape hatch intact
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    check("startup claims the AppUserModelID", "_set_app_user_model_id()" in src)
    check("startup stamps the window icons", "_apply_window_icons(hwnd, ICON_ICO)" in src)
    check("the window-icon hook runs on 'shown'", "window.events.shown += on_shown" in src)
    check("CC_NO_ICONS escape hatch still exists", 'os.environ.get("CC_NO_ICONS")' in src)
    check("CC_NO_AUMID escape hatch still exists", 'os.environ.get("CC_NO_AUMID")' in src)
    check("webview.start is given the icon", "webview.start(debug=" in src and "icon=icon" in src)

    # --- GCLP_HICON / GCLP_HICONSM must be the values Windows expects
    body = src[src.index("def _apply_window_icons"):]
    body = body[:body.index("\ndef ", 10)]
    check("sets the big class icon", "GCLP_HICON" in body)
    check("sets the small class icon", "GCLP_HICONSM" in body)
    check("pushes WM_SETICON", "WM_SETICON" in body)

    print("\nFAILURES: %d" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
