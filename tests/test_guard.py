# -*- coding: utf-8 -*-
"""test_guard.py — proves the deletion guard refuses protected paths. Run: python tests/test_guard.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cleaner as C
import cc_rules as R
import scanner as S

CASES = [
    # (path, expected "is allowed to clean")
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default", False),
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache", True),
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Profile 1\Code Cache", True),
    (r"%USERPROFILE%\Desktop", False),
    (r"%USERPROFILE%\Documents", False),
    (r"%USERPROFILE%\Downloads", False),
    (r"%USERPROFILE%\.ssh", False),
    (r"%LOCALAPPDATA%\Packages\Claude_x\LocalCache", True),
    (r"%LOCALAPPDATA%\Packages\Claude_x\TempState", True),
    (r"%LOCALAPPDATA%\Packages\Claude_x", False),
    (r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\abc.default\cache2", True),
    (r"%APPDATA%\Mozilla\Firefox\Profiles\abc.default", False),
    (r"%LOCALAPPDATA%\Temp", True),
    (r"%WINDIR%\System32", False),
    (r"%WINDIR%\Prefetch", True),
    (r"%WINDIR%\SoftwareDistribution\Download", True),
    (r"C:\Windows", False),
    (r"C:\Program Files\SomeApp", False),
    (r"%APPDATA%\Telegram Desktop\tdata\user_data\cache", True),
    (r"%APPDATA%\Telegram Desktop\tdata", False),
    (r"%APPDATA%\npm", False),
    (r"%LOCALAPPDATA%\npm-cache", True),
    (r"%PROGRAMDATA%\Adobe\CameraRaw\ModelZoo", True),
    (r"%PROGRAMDATA%\Adobe\CameraRaw\CameraProfiles", False),  # Adobe needs this data — protected
    (r"C:\xampp\apache\logs", True),
    (r"", False),
    (r"C:\\", False),
]

fails = 0
for pat, want in CASES:
    p = R.expand(pat)
    got, why = C.is_allowed(p)
    ok = (got == want)
    if not ok:
        fails += 1
    print(("OK  " if ok else "FAIL") + "  want=%-5s got=%-5s %-22s %s" % (want, got, why, pat))

# scanner's own protection check
print("\n--- is_protected ---")
for pat, want in [(r"%USERPROFILE%\Desktop", True), (r"%LOCALAPPDATA%\Temp", False),
                  (r"%LOCALAPPDATA%\Packages\X\LocalCache", False),
                  (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache", False)]:
    p = R.expand(pat)
    got = S.is_protected(p)
    ok = got == want
    if not ok:
        fails += 1
    print(("OK  " if ok else "FAIL") + "  %-22s %s" % (got, pat))

# rules sanity: no rule may point at a protected path or outside the allowed roots
print("\n--- rules sanity ---")
bad = 0
for rule in R.RULES:
    for pat in rule["paths"]:
        for p in S.expand_glob(pat):
            if S.is_protected(p):
                print("PROTECTED-RULE!", rule["app"], p)
                bad += 1
            ok, why = C.is_allowed(p)
            if not ok:
                print("NOT-ALLOWED!", rule["app"], p, "|", why)
                bad += 1
fails += bad
print("rules issues:", bad)
print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
