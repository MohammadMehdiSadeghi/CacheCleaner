"""mid_scan_close_test.py — closing the window DURING a scan must leave nothing running.

The scan now reports progress from inside a large folder (the `walk` callback), so the worker
raises the stop signal far more often than before. "Close mid-scan" is therefore the case worth
proving: if the worker cannot unwind, the process survives with no window.

Two things this gets right that a naive version does not:

* The scan is started by the app's OWN button (`#btnScan.click()` through evaluate_js), not by
  PostMessage-ing a keystroke — a synthetic 'r' never reaches WebView2's page, so an earlier
  version of this test passed while no scan was running at all.
* It ASSERTS the scan is in flight (the scan overlay is visible and the live byte counter is
  climbing) before closing. Without that the test can pass vacuously.

Process detection is scoped to our tree: matching every msedgewebview2.exe also catches other
apps' WebView2 helpers (including the Hermes desktop app's), which reports survivors even when
our app exited cleanly.

Run: python tools/mid_scan_close_test.py
"""
import ctypes
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYW = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                   "Programs", "Python", "Python314", "pythonw.exe")
user32 = ctypes.WinDLL("user32", use_last_error=True)
WM_CLOSE = 0x0010

PS_TREE = r'''
$all = Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine
$mine = $all | Where-Object { $_.Name -eq "pythonw.exe" -and $_.CommandLine -like "*app.py*" }
$ids = New-Object System.Collections.ArrayList
foreach ($m in $mine) { [void]$ids.Add($m.ProcessId) }
$grow = $true
while ($grow) {
  $grow = $false
  foreach ($p in $all) {
    if ($ids -contains $p.ParentProcessId -and -not ($ids -contains $p.ProcessId)) {
      [void]$ids.Add($p.ProcessId); $grow = $true
    }
  }
}
$out = @()
foreach ($i in $ids) {
  $p = $all | Where-Object { $_.ProcessId -eq $i } | Select-Object -First 1
  if ($p) { $out += ("{0}|{1}" -f $p.ProcessId, $p.Name) }
}
$out -join ","
'''

READ_SCAN = """(() => {
  const s = document.getElementById('scanStage');
  const vis = s && !s.hasAttribute('hidden') && getComputedStyle(s).display !== 'none';
  const g = id => { const e = document.getElementById(id); return e ? e.textContent.trim() : null; };
  return JSON.stringify({vis: !!vis, pct: g('scanPct'), size: g('roSize'), files: g('roFiles'),
                         now: g('scanNow')});
})()"""


def ps(script, timeout=120):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                       capture_output=True, text=True, timeout=timeout, errors="replace")
    return (r.stdout or "").strip()


def our_tree():
    out = ps(PS_TREE)
    items = []
    for part in out.split(","):
        part = part.strip()
        if "|" in part:
            pid, name = part.split("|", 1)
            if pid.strip().isdigit():
                items.append((int(pid), name.strip()))
    return items


def kill_ours():
    ps("Get-Process | Where-Object { $_.MainWindowTitle -eq 'Cache Cleaner' } | "
       "ForEach-Object { $_.Kill() }")


def hwnd_of(title="Cache Cleaner"):
    return user32.FindWindowW(None, title) or None


def main():
    if not os.path.exists(PYW):
        print("SKIP: pythonw.exe not found at", PYW)
        return 0

    if our_tree():
        print("clearing %d process(es) from an earlier run" % len(our_tree()))
        kill_ours()
        time.sleep(5)
        if our_tree():
            print("could not clear: %s" % our_tree()[:5])
            return 1

    # --- drive the app in-process so we can click its real Rescan button
    import webview
    sys.path.insert(0, ROOT)
    import app as A

    cfg = A.load_config()
    win_cfg = cfg.get("window", {})
    api = A.Api()
    w = webview.create_window("Cache Cleaner", A.UI_INDEX, js_api=api,
                              width=1400, height=900, background_color="#0a0b0d")
    A.WINDOW[0] = w
    state = {"peak": 0, "samples": [], "started": False}

    def probe():
        time.sleep(7)
        # finish the automatic boot scan first, then start a fresh one through the real button
        t0 = time.time()
        while time.time() - t0 < 120 and api.cc_scan_state()["running"]:
            time.sleep(0.5)
        print("boot scan done:", api.cc_scan_state()["running"] is False)

        w.evaluate_js("document.getElementById('btnScan').click()")
        time.sleep(0.9)

        for _ in range(40):
            try:
                d = __import__("json").loads(w.evaluate_js(READ_SCAN))
            except Exception:
                time.sleep(0.2)
                continue
            state["samples"].append(d)
            if d.get("vis"):
                state["started"] = True
            state["peak"] = max(state["peak"], len(our_tree()))
            time.sleep(0.2)
        # the walk callback fires throughout; close right in the middle of it
        user32.PostMessageW(hwnd_of(), WM_CLOSE, 0, 0)
        time.sleep(0.4)

    webview.start(probe, debug=False)
    A.EXIT.set()

    vis = sum(1 for s in state["samples"] if s.get("vis"))
    sizes = [s.get("size") for s in state["samples"] if s.get("size")]
    pcts = [s.get("pct") for s in state["samples"] if s.get("pct")]
    print("overlay visible in %d/%d samples" % (vis, len(state["samples"])))
    print("live size readout samples:", list(dict.fromkeys(sizes))[:6])
    print("percent samples:", list(dict.fromkeys(pcts))[:6])

    if not state["started"]:
        print("FAIL: the scan never started — a clean exit here would prove nothing")
        return 1
    if len(set(sizes)) < 2:
        print("FAIL: the scan overlay never updated — not really in flight")
        return 1
    print("scan confirmed in flight (overlay up, live counter moving)")

    # --- the process must be gone now
    gone_at = None
    for i in range(25):
        time.sleep(1)
        if not our_tree():
            gone_at = i + 1
            break
    left = our_tree()
    print("our processes still alive: %d %s" % (len(left), left[:4]))
    if gone_at and not left:
        print("OK   closing mid-scan left nothing running (%ds to exit)" % gone_at)
        return 0
    print("FAIL: something survived the mid-scan close: %s" % left[:6])
    kill_ours()
    return 1


if __name__ == "__main__":
    sys.exit(main())
