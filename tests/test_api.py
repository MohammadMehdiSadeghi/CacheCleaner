# -*- coding: utf-8 -*-
"""test_api.py — tests the Python API layer that the interface calls.
Exercises a real scan, the per-file breakdown, the safety preview and the
clean engine on an artificial sandbox (never on real caches).
Run: python tests/test_api.py
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as A       # noqa: E402
import cc_rules as R  # noqa: E402
import cleaner as C   # noqa: E402
import scanner as S   # noqa: E402

fails = 0


def check(name, cond, extra=""):
    global fails
    print(("OK   " if cond else "FAIL ") + name + ("  " + str(extra) if extra else ""))
    if not cond:
        fails += 1


def pump_scan(api, timeout=180):
    t0 = time.time()
    while api.cc_scan_state()["running"] and time.time() - t0 < timeout:
        time.sleep(0.25)
    return api.cc_scan_state()


def main():
    api = A.Api()

    info = api.cc_info()
    check("cc_info returns admin flag and python version", "admin" in info and "python" in info,
          "%s / py%s" % (info["admin"], info["python"]))

    # ---- scan
    api.cc_start_scan(True)
    st = api.cc_scan_state()
    check("scan reports itself as running", st["running"], st["total"])
    st = pump_scan(api)
    check("scan finished", not st["running"])
    # the live fields the scan animation reads must be real, not placeholders
    check("scan reports a live byte total", st.get("liveBytes", 0) > 0, st.get("liveBytes"))
    check("scan reports a live file count", st.get("liveFiles", 0) > 0, st.get("liveFiles"))
    check("scan reports how many caches were found", st.get("found", 0) > 0, st.get("found"))
    check("scan keeps a recent-found list", isinstance(st.get("recent"), list), type(st.get("recent")))
    # the animation must keep moving WHILE a big folder is walked, not only between folders:
    # one 8 GB temp dir can be most of the scan's wall clock, so per-folder-only updates freeze.
    walked = []
    S.scan(S.build_targets(include_discovered=True)[:60], workers=4,
           walk=lambda i, n, size, files, t: walked.append((i, size)))
    check("walk callback fires during a large folder",
          len(walked) > 0, "%d sub-target updates" % len(walked))
    check("walk updates carry a real byte total",
          bool(walked) and walked[-1][1] > 0,
          S.fmt_size(walked[-1][1]) if walked else "none")
    check("the live byte total matches the measured targets",
          abs(st.get("liveBytes", 0) - sum(t["size"] for t in st["targets"])) == 0,
          "%s vs %s" % (st.get("liveBytes"), sum(t["size"] for t in st["targets"])))
    check("scan found cache targets", len(st["targets"]) > 20, len(st["targets"]))
    check("scan found installed apps", len(st["apps"]) > 10, len(st["apps"]))
    check("scan reported drives", bool(st["drives"]), list(st["drives"])[:5])
    check("scan measured a non-zero total",
          sum(t["size"] for t in st["targets"]) > 100 * 1024 * 1024,
          S.fmt_size(sum(t["size"] for t in st["targets"])))
    check("target dicts carry the fields the UI reads",
          all(k in st["targets"][0] for k in
              ("app", "kind", "risk", "desc", "processes", "path", "size", "files",
               "source", "needs_admin")))

    biggest = max(st["targets"], key=lambda t: t["size"])
    check("every target has a description for the detail panel",
          all(t["desc"] for t in st["targets"] if t["source"] == "rule"))

    # ---- per-file breakdown
    items = api.cc_entries(biggest["path"])
    check("cc_entries lists the folder contents", len(items) > 0,
          "%d items in %s" % (len(items), biggest["app"]))
    check("entries are sorted largest first",
          all(items[i]["size"] >= items[i + 1]["size"] for i in range(len(items) - 1)))
    check("entries sum matches the measured size",
          abs(sum(i["size"] for i in items) - biggest["size"]) <= max(4096, biggest["size"] * 0.02),
          "%s vs %s" % (S.fmt_size(sum(i["size"] for i in items)), S.fmt_size(biggest["size"])))

    # ---- safety preview refuses dangerous paths
    pv = api.cc_preview([biggest["path"]])
    check("preview marks a real cache as allowed", pv["rows"][0]["allowed"], pv["rows"][0]["reason"])
    pv2 = api.cc_preview([R.expand(r"%USERPROFILE%\Desktop"),
                          R.expand(r"%WINDIR%\System32"),
                          R.expand(r"%APPDATA%\npm")])
    check("preview refuses Desktop / System32 / global npm",
          all(not r["allowed"] for r in pv2["rows"]),
          ", ".join(r["reason"] for r in pv2["rows"]))
    check("preview does not count refused paths in the total", pv2["total"] == 0)

    # ---- clean engine on a sandbox
    sandbox = R.expand(r"%LOCALAPPDATA%\Temp\cc_api_sandbox")
    shutil.rmtree(sandbox, ignore_errors=True)
    os.makedirs(os.path.join(sandbox, "sub"))
    with open(os.path.join(sandbox, "a.bin"), "wb") as f:
        f.write(b"x" * (400 * 1024))
    with open(os.path.join(sandbox, "sub", "b.bin"), "wb") as f:
        f.write(b"y" * (200 * 1024))
    api.cc_start_clean([sandbox], False)
    t0 = time.time()
    while api.cc_clean_state()["running"] and time.time() - t0 < 60:
        time.sleep(0.2)
    cs = api.cc_clean_state()
    check("clean finished", not cs["running"])
    check("clean freed the sandbox bytes", cs["report"]["freed"] >= 600 * 1024,
          S.fmt_size(cs["report"]["freed"]))
    check("cache folder itself survived", os.path.isdir(sandbox))
    check("clean report carries per-path details", len(cs["report"]["details"]) == 1,
          cs["report"]["details"])
    shutil.rmtree(sandbox, ignore_errors=True)

    # ---- the scan worker must survive its own abort signal. The progress callbacks raise
    # KeyboardInterrupt when the window closes; that is a BaseException, so a plain
    # `except Exception` does not catch it and the worker used to die with a raw traceback
    # (leaving `error` unset and `running` stale) instead of stopping cleanly.
    import threading as _th
    _real = S.scan
    def _boom(*a, **k):
        raise KeyboardInterrupt("window closed")
    try:
        S.scan = _boom
        api2 = A.Api()
        api2.cc_start_scan(True)
        t0 = time.time()
        while api2.cc_scan_state()["running"] and time.time() - t0 < 30:
            time.sleep(0.2)
        st2 = api2.cc_scan_state()
        check("an aborted scan marks itself stopped", st2["running"] is False)
        check("an aborted scan reports no error", not st2.get("error"), st2.get("error"))
    finally:
        S.scan = _real

    # ---- clean refuses a protected path, and says so
    api.cc_start_clean([R.expand(r"%USERPROFILE%\Desktop")], False)
    t0 = time.time()
    while api.cc_clean_state()["running"] and time.time() - t0 < 30:
        time.sleep(0.2)
    cs = api.cc_clean_state()
    d = cs["report"]["details"][0]
    check("Desktop was refused by the clean engine", d["freed"] == 0 and d["reason"],
          d["reason"])
    check("Desktop still exists", os.path.isdir(R.expand(r"%USERPROFILE%\Desktop")))

    # ---- config round-trip
    api.cc_config({"exclude_apps": ["__test_only__"]})
    check("config persists to disk", os.path.exists(A.CONFIG_PATH))
    api.cc_config({"exclude_apps": []})

    print("\nFAILURES:", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
