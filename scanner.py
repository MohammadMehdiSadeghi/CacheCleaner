# -*- coding: utf-8 -*-
"""
scanner.py — read-only scan engine.

Measures real cache sizes (no registry estimates), discovers unknown cache folders,
reports drive space and lists installed software. Nothing in this module deletes anything.
"""
import glob as globmod
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import cc_rules as R
import i18n_rules as I

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ------------------------------------------------------------------ helpers
def _run_hidden(args, timeout=25):
    try:
        p = subprocess.run(args, capture_output=True, timeout=timeout,
                           creationflags=_CREATE_NO_WINDOW)
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                return p.stdout.decode(enc)
            except UnicodeDecodeError:
                continue
        return p.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def dir_size(path, cap_files=400000, on_walk=None, walk_every=2000):
    """Return (bytes, files, dirs, locked) for a file or directory. Tolerates access errors.

    `on_walk(bytes, files)` is called every `walk_every` files so a live view can show real
    numbers WHILE a large folder is still being walked. Without it a multi-gigabyte folder
    reports nothing until it finishes, and the progress readouts look frozen for seconds.
    """
    total = 0
    files = 0
    dirs = 0
    locked = 0
    since = 0
    stack = [path]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            dirs += 1
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            total += e.stat(follow_symlinks=False).st_size
                            files += 1
                            since += 1
                            if on_walk and since >= walk_every:
                                since = 0
                                on_walk(total, files)
                            if files >= cap_files:
                                return total, files, dirs, locked
                    except (PermissionError, OSError):
                        locked += 1
        except (PermissionError, OSError):
            locked += 1
    return total, files, dirs, locked


def expand_glob(pattern):
    """Expand a rule pattern (env vars and wildcards) into existing paths."""
    p = R.expand(pattern)
    if "*" in p or "?" in p:
        return sorted(globmod.glob(p))
    return [p] if os.path.exists(p) else []


def is_protected(path):
    """True when the path is protected and must not be offered for cleaning."""
    return R.protection_status(path)[0]


def running(names):
    if not names:
        return []
    txt = _run_hidden(["tasklist", "/FO", "CSV", "/NH"], timeout=25).lower()
    return [n for n in names if n.lower() in txt]


def fmt_size(b):
    b = float(b or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024 or unit == "TB":
            return ("%.1f %s" % (b, unit)) if unit != "B" else ("%d B" % b)
        b /= 1024.0


def pretty_pkg_name(name):
    """'OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0' -> 'ChatGPT-Desktop (OpenAI)'."""
    n = name
    if "_" in n:
        head, tail = n.rsplit("_", 1)
        if len(tail) >= 10 and " " not in tail:
            n = head
    parts = n.split(".")
    if len(parts) > 1:
        return "%s (%s)" % (".".join(parts[1:]), parts[0])
    return n


# ------------------------------------------------------------------ targets
class Target:
    __slots__ = ("app", "kind", "risk", "desc", "processes", "path", "size",
                 "files", "dirs", "locked", "exists", "source", "needs_admin",
                 "app_fa", "kind_fa", "desc_fa")

    def __init__(self, app, kind, risk, desc, processes, path,
                 source="rule", needs_admin=False, fa=None):
        self.app = app
        self.kind = kind
        self.risk = risk
        self.desc = desc
        # Persian equivalents travel with the target so switching language never
        # needs a rescan (the UI just picks which field to render).
        self.app_fa = (fa or {}).get("app", app)
        self.kind_fa = (fa or {}).get("kind", kind)
        self.desc_fa = (fa or {}).get("desc", desc)
        self.processes = processes
        self.path = path
        self.source = source
        self.needs_admin = needs_admin
        self.size = 0
        self.files = 0
        self.dirs = 0
        self.locked = 0
        self.exists = False

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


def build_targets(include_discovered=True, discover_depth=None):
    targets = []
    seen = set()
    for rule in R.RULES:
        paths = []
        for pat in rule["paths"]:
            paths.extend(expand_glob(pat))
        fa = I.FA.get(rule["app"])
        for p in paths:
            key = os.path.normcase(os.path.normpath(p))
            if key in seen or is_protected(p):
                continue
            seen.add(key)
            targets.append(Target(rule["app"], rule["kind"], rule["risk"], rule["desc"],
                                  rule.get("processes", []), p,
                                  needs_admin=rule.get("needs_admin", False), fa=fa))
    if include_discovered:
        targets.extend(discover(seen, max_depth=discover_depth))
    return targets


def discover(seen, max_depth=None):
    """Find cache folders that are not covered by an explicit rule."""
    out = []
    for root_pat, depth, _label in R.DISCOVER_ROOTS:
        root = R.expand(root_pat)
        if not os.path.isdir(root):
            continue
        d = depth if max_depth is None else min(depth, max_depth)
        base_depth = root.rstrip("\\").count("\\")
        for cur, subdirs, _files in os.walk(root):
            if cur.count("\\") - base_depth >= d:
                subdirs[:] = []
                continue
            subdirs[:] = [s for s in subdirs
                          if s.lower() not in R.PRUNE_NAMES and not s.startswith(".")]
            for s in list(subdirs):
                if s.lower() in R.CACHE_DIR_NAMES:
                    full = os.path.join(cur, s)
                    key = os.path.normcase(os.path.normpath(full))
                    if key in seen or is_protected(full):
                        continue
                    seen.add(key)
                    app = os.path.basename(cur) or s
                    if "packages" in cur.lower():
                        app = pretty_pkg_name(app)
                    out.append(Target(
                        app, "Discovered cache", "medium",
                        "Cache folder detected automatically at %s. It holds rebuildable "
                        "temporary data." % cur, [], full, source="discover",
                        fa=dict(kind="کش کشف‌شده",
                                desc="پوشهٔ کش که خودکار در %s پیدا شد. محتوایش دادهٔ موقت "
                                     "و قابل بازسازی است." % cur)))
                    subdirs.remove(s)
    return out


# ------------------------------------------------------------------ scan
def scan(targets, workers=8, progress=None, tick=None, walk=None):
    """Measure every target. `tick(done, total, size, files)` fires after each target so a
    live view can show real numbers while the scan is still running.

    `walk(done, total, size, files, target)` fires DURING a single large folder, every few
    thousand files. A scan's time is dominated by one or two huge caches (an 8 GB temp folder
    can be 70% of the wall clock), so without it the readouts sit frozen for seconds and the
    percentage jumps straight to ~99% and waits.
    """
    done = [0]
    total = len(targets)
    acc_size = [0]
    acc_files = [0]
    lock = threading.Lock()

    def work(t):
        if not os.path.exists(t.path):
            return t
        t.exists = True
        if os.path.isfile(t.path):
            try:
                t.size = os.path.getsize(t.path)
                t.files = 1
            except OSError:
                t.locked = 1
        else:
            def on_walk(size_so_far, files_so_far):
                # report the folder's own running totals plus everything already finished
                if walk:
                    with lock:
                        walk(done[0], total, acc_size[0] + size_so_far,
                             acc_files[0] + files_so_far, t)

            t.size, t.files, t.dirs, t.locked = dir_size(t.path, on_walk=on_walk)
        with lock:
            done[0] += 1
            acc_size[0] += t.size
            acc_files[0] += t.files
            d, s, f = done[0], acc_size[0], acc_files[0]
        if progress:
            progress(d, total, t)
        if tick:
            tick(d, total, s, f, t)
        return t

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, targets))
    return targets


# ------------------------------------------------------------------ system info
def drive_info():
    out = {}
    txt = _run_hidden(
        ["powershell.exe", "-NoProfile", "-Command",
         "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | "
         "Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json -Compress"], timeout=40)
    try:
        data = json.loads(txt or "[]")
        if isinstance(data, dict):
            data = [data]
        for d in data:
            out[d["DeviceID"].rstrip(":")] = {"total": d.get("Size") or 0,
                                              "free": d.get("FreeSpace") or 0}
    except Exception:
        pass
    if not out:
        import shutil
        try:
            u = shutil.disk_usage("C:\\")
            out["C"] = {"total": u.total, "free": u.free}
        except Exception:
            pass
    return out


def installed_apps():
    """Software from the uninstall registry (fast, no disk walk)."""
    ps = r"""
$keys = @(
 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
Get-ItemProperty $keys -ErrorAction SilentlyContinue |
 Where-Object { $_.DisplayName } |
 Select-Object DisplayName,DisplayVersion,Publisher,InstallLocation,EstimatedSize |
 ConvertTo-Json -Compress
"""
    txt = _run_hidden(["powershell.exe", "-NoProfile", "-Command", ps], timeout=60)
    apps = []
    try:
        data = json.loads(txt or "[]")
        if isinstance(data, dict):
            data = [data]
        for a in data:
            apps.append({
                "name": a.get("DisplayName") or "",
                "version": a.get("DisplayVersion") or "",
                "publisher": a.get("Publisher") or "",
                "location": a.get("InstallLocation") or "",
                "size_kb": a.get("EstimatedSize") or 0,
            })
    except Exception:
        pass
    apps.sort(key=lambda a: a["name"].lower())
    return apps


def store_apps():
    """Microsoft Store packages."""
    ps = ("Get-AppxPackage | Select-Object Name,PackageFullName,InstallLocation | "
          "ConvertTo-Json -Compress")
    txt = _run_hidden(["powershell.exe", "-NoProfile", "-Command", ps], timeout=60)
    out = []
    try:
        data = json.loads(txt or "[]")
        if isinstance(data, dict):
            data = [data]
        for a in data:
            out.append({"name": a.get("Name") or "", "full": a.get("PackageFullName") or "",
                        "location": a.get("InstallLocation") or ""})
    except Exception:
        pass
    return out


if __name__ == "__main__":
    t0 = time.time()
    tg = build_targets()
    scan(tg)
    tg.sort(key=lambda x: -x.size)
    for t in tg[:25]:
        if t.size:
            print("%10s  %-32s %s" % (fmt_size(t.size), t.app[:32], t.path))
    print("grand total: %s in %.1fs" % (fmt_size(sum(x.size for x in tg)), time.time() - t0))
    print("drives:", drive_info())
