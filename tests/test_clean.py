# -*- coding: utf-8 -*-
"""test_clean.py — exercises the deletion engine on a synthetic sandbox, never on real
caches. Run: python tests/test_clean.py
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cc_rules as R
import scanner as S
import cleaner as C

SANDBOX = R.expand(r"%LOCALAPPDATA%\Temp\cc_sandbox_test")
fails = 0


def mk(path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"x" * size)


def check(name, cond, extra=""):
    global fails
    print(("OK   " if cond else "FAIL ") + name + ("  " + str(extra) if extra else ""))
    if not cond:
        fails += 1


# --- build the sandbox ---
if os.path.exists(SANDBOX):
    shutil.rmtree(SANDBOX, ignore_errors=True)
mk(os.path.join(SANDBOX, "a.bin"), 300 * 1024)
mk(os.path.join(SANDBOX, "sub", "b.bin"), 200 * 1024)
os.makedirs(os.path.join(SANDBOX, "emptydir"), exist_ok=True)

before = S.dir_size(SANDBOX)[0]
check("sandbox created (%s)" % S.fmt_size(before), before > 400 * 1024, before)

t = S.Target("Test sandbox", "Cache", "low", "", [], SANDBOX)

# --- 1) dry-run must not delete anything ---
rep = C.clean_many([t], dry_run=True)
check("dry-run deleted nothing", os.path.exists(os.path.join(SANDBOX, "a.bin")))
check("dry-run reported reclaimable bytes", rep["freed"] >= before, rep["freed"])

# --- 2) real deletion ---
rep = C.clean_many([t], dry_run=False)
after = S.dir_size(SANDBOX)[0]
check("real deletion emptied the cache", after == 0, "after=%d" % after)
check("the cache folder itself survived (apps keep working)", os.path.isdir(SANDBOX))
check("freed bytes were reported", rep["freed"] >= before * 0.95, rep["freed"])

# --- 3) guard: dangerous paths are never deleted ---
danger = S.Target("Danger", "Test", "low", "", [], R.expand(r"%USERPROFILE%\Desktop"))
rep2 = C.clean_many([danger], dry_run=False)
check("Desktop survived", os.path.isdir(R.expand(r"%USERPROFILE%\Desktop")))
check("dangerous path was skipped", rep2["targets"][0]["skipped"], rep2["targets"][0]["reason"])

danger2 = S.Target("Danger2", "Test", "low", "", [], r"C:\Windows\System32")
rep3 = C.clean_many([danger2], dry_run=False)
check("System32 survived", os.path.isdir(r"C:\Windows\System32"))
check("System32 was skipped", rep3["targets"][0]["skipped"])

# --- 4) missing folder ---
t2 = S.Target("Missing", "Cache", "low", "", [], os.path.join(SANDBOX, "nope"))
r4 = C.clean_target(t2)
check("missing folder skipped without error", r4["skipped"], r4["reason"])

# --- 5) dry-run against real caches ---
cands = [x for x in S.build_targets(include_discovered=False) if os.path.exists(x.path)]
S.scan(cands)
real = sorted(cands, key=lambda x: -x.size)[:6]
rd = C.clean_many(real, dry_run=True)
check("dry-run on real caches deleted nothing",
      all(os.path.exists(x.path) for x in real))
check("dry-run on real caches estimated a size", rd["freed"] > 0, S.fmt_size(rd["freed"]))

shutil.rmtree(SANDBOX, ignore_errors=True)
print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
