# -*- coding: utf-8 -*-
"""make_shortcut.py — create a Desktop shortcut. Run: python make_shortcut.py

Note: PowerShell mangles non-ASCII paths inside -Command/-File, so the shortcut is
created under a temporary ASCII name and then renamed with Python.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# The icon-bearing exe is the preferred target; fall back to the batch file.
TARGET = os.path.join(HERE, "CacheCleaner.exe")
if not os.path.exists(TARGET):
    TARGET = os.path.join(HERE, "CacheCleaner.bat")
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
FINAL = os.path.join(DESKTOP, "Cache Cleaner.lnk")
LEGACY = os.path.join(DESKTOP, "\u067e\u0627\u06a9\u200c\u06a9\u0646\u0646\u062f\u0647 \u06a9\u0634.lnk")
TMP_LNK = os.path.join(HERE, "_shortcut_tmp.lnk")
ICON = os.path.join(HERE, "assets", "sparkles.ico")
if not os.path.exists(ICON):
    ICON = r"%SystemRoot%\System32\imageres.dll,54"

ps = r'''$s = (New-Object -ComObject WScript.Shell).CreateShortcut("%s")
$s.TargetPath = "%s"
$s.WorkingDirectory = "%s"
$s.IconLocation = "%s"
$s.Description = "Cache Cleaner"
$s.Save()
''' % (TMP_LNK, TARGET, HERE, ICON)

fd, path = tempfile.mkstemp(suffix=".ps1")
os.close(fd)
with open(path, "w", encoding="utf-8-sig") as f:
    f.write(ps)

r = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path],
                   capture_output=True, text=True)
try:
    os.remove(path)
except OSError:
    pass

if not os.path.exists(TMP_LNK):
    print("Could not create the shortcut:\n" + (r.stdout or "") + (r.stderr or "")[:600])
    sys.exit(1)

try:
    for old in (FINAL, LEGACY):
        if os.path.exists(old):
            os.remove(old)
    os.replace(TMP_LNK, FINAL)
except Exception as e:
    print("Shortcut created but rename failed: %s\n%s" % (e, TMP_LNK))
    sys.exit(1)

print("Shortcut created: " + FINAL)
