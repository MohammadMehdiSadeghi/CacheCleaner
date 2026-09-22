# -*- coding: utf-8 -*-
"""test_shutdown.py — proves the app leaves nothing running after the window closes.

Closing the window must end the whole process: no lingering pythonw, no orphaned
WebView2 helper, no second copy hiding in the background. A named mutex makes a second
launch exit immediately instead of silently starting a duplicate.

Run: python tests/test_shutdown.py
"""
import ctypes
import os
import subprocess
import sys
import time

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYW = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                   "Programs", "Python", "Python314", "pythonw.exe")
PY = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                  "Programs", "Python", "Python314", "python.exe")

fails = 0


def check(name, cond, extra=""):
    global fails
    print(("OK   " if cond else "FAIL ") + name + ("  " + str(extra) if extra else ""))
    if not cond:
        fails += 1


def ps(script):
    """Run PowerShell and return stdout."""
    r = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                       capture_output=True, text=True, timeout=90)
    return (r.stdout or "").strip()


def procs_matching(needle):
    out = ps("Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
             "Where-Object { $_.CommandLine -like '*%s*' } | "
             "ForEach-Object { $_.ProcessId }" % needle)
    return [int(x) for x in out.split() if x.strip().isdigit()]


def webviews_of(pid):
    out = ps("Get-CimInstance Win32_Process -Filter \"Name='msedgewebview2.exe'\" | "
             "Where-Object { $_.ParentProcessId -eq %d } | ForEach-Object { $_.ProcessId }" % pid)
    return [int(x) for x in out.split() if x.strip().isdigit()]


def wait_gone(pids, timeout=25):
    """Poll until every pid is gone; return the ones still alive."""
    deadline = time.time() + timeout
    alive = list(pids)
    while alive and time.time() < deadline:
        alive = [p for p in alive if ps("(Get-Process -Id %d -ErrorAction SilentlyContinue | "
                                       "Measure-Object).Count" % p) not in ("", "0")]
        if alive:
            time.sleep(1.0)
    return alive


if not os.path.exists(PYW):
    print("SKIP: pythonw.exe not found at", PYW)
    sys.exit(0)

# Make sure nothing is left over from an earlier run before we measure.
for p in procs_matching("CacheCleaner"):
    ps("Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % p)
time.sleep(2)

# ---------------------------------------------------------------- 1. launch and close
p = subprocess.Popen([PYW, os.path.join(APP_DIR, "app.py")], cwd=APP_DIR)
time.sleep(18)

pids = procs_matching("CacheCleaner")
check("the app starts and stays running", len(pids) >= 1, pids)

if not pids:
    print("\nFAILURES: 1 (nothing started, later checks skipped)")
    sys.exit(1)

main_pid = pids[0]
kids = webviews_of(main_pid)
check("the window uses a WebView2 host process", len(kids) >= 1, kids)

# Close it the way a user does: ask the main window to close.
ps("$p = Get-Process -Id %d -ErrorAction SilentlyContinue; "
   "if ($p) { $p.CloseMainWindow() | Out-Null }" % main_pid)

alive = wait_gone([main_pid])
check("closing the window ends the process (nothing in the background)", not alive, alive)

if kids:
    alive_kids = wait_gone(kids, timeout=15)
    check("no orphaned WebView2 helper is left behind", not alive_kids, alive_kids)

check("no Cache Cleaner process survives the close",
      not procs_matching("CacheCleaner"), procs_matching("CacheCleaner"))

# ---------------------------------------------------------------- 2. second copy refused
p1 = subprocess.Popen([PYW, os.path.join(APP_DIR, "app.py")], cwd=APP_DIR)
time.sleep(16)
first = procs_matching("CacheCleaner")
check("first copy is running", len(first) == 1, first)

p2 = subprocess.Popen([PYW, os.path.join(APP_DIR, "app.py")], cwd=APP_DIR)
time.sleep(8)
both = procs_matching("CacheCleaner")
check("a second copy does not start a duplicate", len(both) == 1, both)

for proc in (p1, p2):
    if proc.poll() is None:
        proc.terminate()
for pid in procs_matching("CacheCleaner"):
    ps("Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % pid)
time.sleep(2)

print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
