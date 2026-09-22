# -*- coding: utf-8 -*-
"""
cleaner.py — the only module that deletes anything.

Rules it enforces:
  * It empties the *contents* of a cache folder, never the folder itself, so applications
    keep working and simply rebuild their cache.
  * Every path must pass `is_allowed()` before a single file is touched.
  * `dry_run=True` reports what would be freed without deleting anything.

Also exposes the command-line interface (see `main`).
"""
import json
import os
import shutil
import sys
import time

import cc_rules as R
import scanner as S

# Roots inside which cleaning is permitted at all (final safety net).
ALLOWED_ROOTS = [
    R.expand(r"%LOCALAPPDATA%"),
    R.expand(r"%APPDATA%"),
    R.expand(r"%PROGRAMDATA%"),
    R.expand(r"%USERPROFILE%\.gradle"),
    R.expand(r"%USERPROFILE%\.m2"),
    R.expand(r"%USERPROFILE%\.nuget"),
    R.expand(r"%WINDIR%\Temp"),
    R.expand(r"%WINDIR%\SoftwareDistribution\Download"),
    R.expand(r"%WINDIR%\Prefetch"),
    r"C:\xampp",
    R.expand(r"%PROGRAMFILES_X86%\Steam"),
    R.expand(r"%PROGRAMFILES%\Steam"),
]
ALLOWED_ROOTS = [os.path.normcase(os.path.normpath(p)) for p in ALLOWED_ROOTS]

# Roots that are themselves cleanup targets: emptying their contents is allowed.
EXACT_ROOTS = {
    os.path.normcase(os.path.normpath(R.expand(r"%WINDIR%\Temp"))),
    os.path.normcase(os.path.normpath(R.expand(r"%WINDIR%\SoftwareDistribution\Download"))),
    os.path.normcase(os.path.normpath(R.expand(r"%WINDIR%\Prefetch"))),
}

# Extra hard blocks (the scoped protection lives in cc_rules.protection_status).
FORBIDDEN = [
    R.expand(r"%APPDATA%\npm"),
    R.expand(r"%USERPROFILE%\.ssh"),
    R.expand(r"%WINDIR%\System32"),
    R.expand(r"%WINDIR%\SysWOW64"),
]
FORBIDDEN = [os.path.normcase(os.path.normpath(p)) for p in FORBIDDEN]


def _norm(p):
    return os.path.normcase(os.path.normpath(p))


def is_allowed(path):
    """Return (ok, reason). Gatekeeper for every delete."""
    if not path or len(path.strip()) < 8:
        return False, "invalid path"
    p = _norm(path)
    for f in FORBIDDEN:
        if p == f or p.startswith(f + os.sep):
            return False, "protected path"
    blocked, why = R.protection_status(path)
    if blocked:
        return False, why
    if not any(p == r or p.startswith(r + os.sep) for r in ALLOWED_ROOTS):
        return False, "outside the allowed roots"
    if p in ALLOWED_ROOTS and p not in EXACT_ROOTS:
        return False, "protected root"
    return True, ""


def measure(path):
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    return S.dir_size(path)[0]


def clean_target(t, dry_run=False, on_entry=None):
    """Empty one cache path. Returns a result dict with freed bytes and failures."""
    res = {"path": t.path, "app": t.app, "kind": t.kind, "freed": 0,
           "deleted": 0, "failed": [], "skipped": False, "reason": "", "entries": []}
    if not t.path or not os.path.exists(t.path):
        res["skipped"] = True
        res["reason"] = "does not exist"
        return res
    ok, why = is_allowed(t.path)
    if not ok:
        res["skipped"] = True
        res["reason"] = why
        return res

    try:
        entries = list(os.scandir(t.path))
    except PermissionError:
        res["skipped"] = True
        res["reason"] = "access denied (administrator rights required)"
        return res
    except OSError as e:
        res["skipped"] = True
        res["reason"] = str(e)[:80]
        return res

    if not entries:
        res["skipped"] = True
        res["reason"] = "already empty"
        return res

    for e in entries:
        try:
            isdir = e.is_dir(follow_symlinks=False)
        except OSError:
            continue
        before = measure(e.path)
        if dry_run:
            res["freed"] += before
            res["deleted"] += 1
            res["entries"].append({"name": e.name, "size": before, "dry": True})
            if on_entry:
                on_entry(res)
            continue
        try:
            if isdir:
                shutil.rmtree(e.path, ignore_errors=False)
            else:
                os.remove(e.path)
            res["freed"] += before
            res["deleted"] += 1
            res["entries"].append({"name": e.name, "size": before, "dry": False})
        except Exception as ex:
            after = measure(e.path)
            res["freed"] += max(0, before - after)
            if after == 0 and before > 0:
                res["deleted"] += 1
            else:
                res["failed"].append("%s: %s" % (e.name, str(ex)[:70]))
        if on_entry:
            on_entry(res)
    return res


def clean_many(targets, dry_run=False, on_target=None, on_entry=None):
    report = {"dry": dry_run, "freed": 0, "targets": [], "failed": 0, "skipped": 0,
              "t0": time.time(), "t1": time.time(), "free_after": {}}
    for t in targets:
        r = clean_target(t, dry_run=dry_run, on_entry=on_entry)
        report["targets"].append(r)
        report["freed"] += r["freed"]
        if r["skipped"]:
            report["skipped"] += 1
        report["failed"] += len(r["failed"])
        if on_target:
            on_target(t, r, report)
    report["t1"] = time.time()
    report["free_after"] = S.drive_info()
    return report


def preview(targets):
    """What would be freed, without touching anything (used by the UI before confirming)."""
    total = 0
    rows = []
    for t in targets:
        ok, why = is_allowed(t.path)
        rows.append({"path": t.path, "app": t.app, "size": t.size,
                     "allowed": ok, "reason": why})
        if ok:
            total += t.size
    return {"total": total, "rows": rows}


# ------------------------------------------------------- command line
def select_targets(pattern, include_discovered=True):
    """Find cache paths whose app/kind/path contains `pattern` (case-insensitive)."""
    pat = pattern.strip().lower()
    out = []
    for t in S.build_targets(include_discovered=include_discovered):
        if pat and pat in (t.app + " " + t.kind + " " + t.path).lower():
            out.append(t)
    S.scan(out)
    return [t for t in out if t.size > 0]


def main(argv):
    """Usage:
       python cleaner.py --list                        list caches (read-only)
       python cleaner.py --app spotify --dry-run       simulate cleaning Spotify's cache
       python cleaner.py --app spotify --yes           clean it for real
       python cleaner.py --all-low --dry-run           every low-risk cache, simulated
       python cleaner.py --paths-file p.json --out r.json   scripted / elevated mode
    """
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", action="append", default=[], help="part of an app name")
    ap.add_argument("--all-low", action="store_true", help="every low-risk cache")
    ap.add_argument("--list", action="store_true", help="just print the list")
    ap.add_argument("--paths-file")
    ap.add_argument("--out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    ap.add_argument("--no-discover", action="store_true")
    a = ap.parse_args(argv)

    if a.paths_file:
        with open(a.paths_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        dry = a.dry_run or bool(data.get("dry_run"))
        targets = [S.Target(i.get("app", ""), i.get("kind", "Cache"), "low", "", [],
                            i["path"]) for i in data.get("paths", [])]
        rep = clean_many(targets, dry_run=dry)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                json.dump(rep, f, ensure_ascii=False, indent=1)
        print("%s: %s" % ("Would free" if dry else "Freed", S.fmt_size(rep["freed"])))
        return 0

    if a.list:
        tg = S.build_targets(include_discovered=not a.no_discover)
        S.scan(tg)
        tg.sort(key=lambda x: -x.size)
        for t in tg[:40]:
            if t.size:
                print("%10s  %-32s %s" % (S.fmt_size(t.size), t.app[:32], t.path))
        print("total: %s" % S.fmt_size(sum(t.size for t in tg)))
        return 0

    targets = []
    if a.all_low:
        tg = S.build_targets(include_discovered=not a.no_discover)
        S.scan(tg)
        targets = [t for t in tg if t.risk == "low" and t.size > 0]
    for p in a.app:
        targets.extend(select_targets(p, include_discovered=not a.no_discover))
    seen, uniq = set(), []
    for t in targets:
        if t.path not in seen:
            seen.add(t.path)
            uniq.append(t)
    if not uniq:
        print("Nothing to clean. Example: python cleaner.py --app spotify --dry-run")
        return 1

    print("Selected %d path(s):" % len(uniq))
    for t in uniq[:30]:
        print("  %10s  %-32s %s" % (S.fmt_size(t.size), t.app[:32], t.path))
    if len(uniq) > 30:
        print("  ... and %d more" % (len(uniq) - 30))
    print("total: %s" % S.fmt_size(sum(t.size for t in uniq)))

    if a.dry_run:
        rep = clean_many(uniq, dry_run=True)
        print("\n[DRY RUN] Nothing was deleted. Would free: %s" % S.fmt_size(rep["freed"]))
        return 0

    if not a.yes:
        if input("Delete these caches? (yes/no): ").strip().lower() not in ("yes", "y"):
            print("Cancelled.")
            return 1
    rep = clean_many(uniq, dry_run=False)
    print("\nFreed: %s" % S.fmt_size(rep["freed"]))
    if rep["failed"]:
        print("Locked/skipped files: %d" % rep["failed"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
