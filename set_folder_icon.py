# -*- coding: utf-8 -*-
"""set_folder_icon.py — put our icon on the PROJECT FOLDER itself (Explorer icon).

Windows draws a folder's icon from a `desktop.ini` inside it, but only when Explorer is
willing to read that file. Two conditions have to hold, and skipping either one makes this
look like it silently did nothing:

1. The folder must carry the READ-ONLY attribute (`attrib +r`). That flag is what tells
   Explorer to parse `desktop.ini` for a user folder — it has nothing to do with the folder
   actually being read-only.
2. `desktop.ini` itself must be hidden + system (`attrib +h +s`), or Explorer treats it as
   ordinary content and shows it in the file listing.

The icon path inside `desktop.ini` should be absolute, otherwise it is resolved relative to
the folder in ways that break when the project moves.

Explorer caches folder icons aggressively, so the last step pokes it to rebuild
(`ie4uinit.exe -show`). Even then an already-open window may keep the old icon until it is
refreshed; that is cosmetic, not a failure of this script.

Run: python set_folder_icon.py            (uses this file's own folder)
     python set_folder_icon.py <folder>   (any other folder)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ICO = os.path.join(HERE, "assets", "sparkles.ico")
INI = os.path.join(HERE, "desktop.ini")

DESKTOP_INI = """[.ShellClassInfo]
IconResource={icon},0
InfoTip=Cache Cleaner - find and clear the cache of every application
"""


def attrib(path, flags):
    """Apply attribute flags via attrib.exe and return its output."""
    r = subprocess.run(["attrib", flags, path], capture_output=True, text=True,
                       timeout=60, errors="replace")
    return (r.stdout or "").strip() + (r.stderr or "").strip()


def get_attrs(path):
    """Read the current attribute string for a path (from attrib.exe, no flags = display)."""
    r = subprocess.run(["attrib", path], capture_output=True, text=True, timeout=60,
                       errors="replace")
    line = (r.stdout or "").strip().splitlines()
    return line[0][:22].strip() if line else ""


def refresh_explorer():
    """Ask Explorer to rebuild its icon cache. Best effort — failures are not fatal."""
    for args in (["ie4uinit.exe", "-show"], ["ie4uinit.exe", "-ClearIconCache"]):
        try:
            subprocess.run(args, capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            pass


def set_folder_icon(folder):
    folder = os.path.abspath(folder)
    ico = os.path.join(folder, "assets", "sparkles.ico")
    ini = os.path.join(folder, "desktop.ini")

    if not os.path.isdir(folder):
        print("not a folder:", folder)
        return 1
    if not os.path.exists(ico):
        print("icon missing:", ico)
        return 1

    # the .ico needs a large frame or Explorer upscales a small one and it looks blurry
    try:
        from PIL import Image
        sizes = sorted(Image.open(ico).ico.sizes())
        biggest = max(s[0] for s in sizes)
        print("icon frames:", sizes)
        if biggest < 256:
            print("WARNING: largest frame is %dpx — folder icons look best at 256px" % biggest)
    except Exception as e:
        print("could not inspect the .ico:", e)

    # 1. write desktop.ini (absolute icon path, so moving the project does not break it)
    with open(ini, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(DESKTOP_INI.format(icon=ico))
    print("wrote", ini)

    # 2. folder must be read-only for Explorer to honour desktop.ini
    print("folder attrs before:", get_attrs(folder) or "(none)")
    attrib(folder, "+r")
    print("folder attrs after :", get_attrs(folder) or "(none)")

    # 3. desktop.ini itself must be hidden + system
    attrib(ini, "+h")
    attrib(ini, "+s")
    print("ini attrs          :", get_attrs(ini) or "(none)")

    refresh_explorer()
    print("asked Explorer to rebuild its icon cache")
    print("\nDONE — the folder should now show the sparkles icon.")
    print("If it still shows a plain folder, close and reopen the Desktop window;")
    print("Explorer keeps a cached icon for folders it has already drawn.")
    return 0


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else HERE
    return set_folder_icon(folder)


if __name__ == "__main__":
    sys.exit(main())
