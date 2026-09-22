# -*- coding: utf-8 -*-
"""
report.py — read-only command-line report (cmd).
It only measures: nothing is ever deleted here.
Usage:
  python report.py                  full cache report (largest first)
  python report.py --top 30         only the first 30 entries
  python report.py --apps           list installed software
  python report.py --json out.json  machine-readable output for automation
  python report.py --no-discover    skip auto-discovered caches
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cc_rules as R      # noqa: E402
import scanner as S       # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def bar(frac, width=18):
    n = int(round(frac * width))
    return "#" * n + "." * (width - n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--apps", action="store_true")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--no-discover", action="store_true")
    ap.add_argument("--min-mb", type=float, default=0.0)
    a = ap.parse_args()

    t0 = time.time()
    if a.apps:
        apps = S.installed_apps()
        print("Installed software: %d entries\n" % len(apps))
        print("%-42s %-12s %-26s %10s" % ("Name", "Version", "Publisher", "Installed"))
        print("-" * 96)
        for x in apps:
            print("%-42s %-12s %-26s %10s" % (
                x["name"][:42], x["version"][:12], x["publisher"][:26],
                S.fmt_size(x["size_kb"] * 1024) if x["size_kb"] else "-"))
        return 0

    tg = S.build_targets(include_discovered=not a.no_discover)
    S.scan(tg)
    tg = [t for t in tg if t.size >= a.min_mb * 1024 * 1024]
    tg.sort(key=lambda x: -x.size)
    total = sum(t.size for t in tg)
    drives = S.drive_info()

    print("=" * 100)
    print("Application cache report — %s" % time.strftime("%Y-%m-%d %H:%M"))
    print("=" * 100)
    for d in sorted(drives):
        i = drives[d]
        if i.get("total"):
            print("Drive %s: %s free of %s" % (d, S.fmt_size(i["free"]), S.fmt_size(i["total"])))
    print("Reclaimable cache: %s across %d locations (%.1f s)\n"
          % (S.fmt_size(total), len(tg), time.time() - t0))

    print("%-9s %-6s %-28s %-20s %s" % ("Size", "Share", "Application", "Type", "Path"))
    print("-" * 100)
    shown = tg[:a.top] if a.top else tg
    mx = tg[0].size if tg else 1
    for t in shown:
        print("%9s %-6s %-28s %-20s %s" % (
            S.fmt_size(t.size), bar(t.size / mx), t.app[:28], t.kind[:20], t.path))
    if a.top and len(tg) > a.top:
        print("... and %d more (%s)" % (len(tg) - a.top,
                                        S.fmt_size(sum(x.size for x in tg[a.top:]))))
    print("\nUse the app itself (app.py / CacheCleaner.bat) to delete anything;")
    print("deletion always asks for confirmation, and this report is read-only.")

    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump({"generated": time.strftime("%Y-%m-%d %H:%M"),
                       "total_bytes": total,
                       "drives": drives,
                       "targets": [t.as_dict() for t in tg]}, f, ensure_ascii=False, indent=1)
        print("\nJSON written: %s" % a.json_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
