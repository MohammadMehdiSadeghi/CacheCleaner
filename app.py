# -*- coding: utf-8 -*-
"""
app.py — Cache Cleaner desktop application.

A pywebview window hosting ui/index.html; all scanning and cleaning happens in Python
(scanner.py / cleaner.py / cc_rules.py) and is exposed to the interface through a small
threaded API. The UI never deletes anything by itself.

Run:  pythonw app.py        (or double-click CacheCleaner.bat)
"""
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

import cc_rules as R          # noqa: E402
import cleaner as C           # noqa: E402
import scanner as S           # noqa: E402

CONFIG_PATH = os.path.join(APP_DIR, "config.json")
UI_INDEX = os.path.join(APP_DIR, "ui", "index.html")
ICON_ICO = os.path.join(APP_DIR, "assets", "sparkles.ico")
WINDOW = [None]        # the pywebview window, kept OUT of the API object (see Api.__init__)
EXIT = threading.Event()   # set when the window closes, so no thread outlives the app

# Only these hosts may be opened in a browser from the interface. Anything else is
# refused — an unknown link must never reach ShellExecute.
LINK_HOSTS = ("github.com", "www.github.com", "linkedin.com", "www.linkedin.com")
USER_LINKS = {
    "github": "https://github.com/MohammadMehdiSadeghi",
    "linkedin": "https://www.linkedin.com/in/mohammad-mehdi-sadeghi",
}

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def load_config():
    cfg = {"include_discovered": True, "exclude_apps": [], "lang": "en",
           "window": {"w": 1400, "h": 900}}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    if cfg.get("lang") not in ("en", "fa"):
        cfg["lang"] = "en"          # English is the default
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


# ================================================================ API
class Api:
    """Methods here are callable from JavaScript as cc_* (see ui/index.html)."""

    def __init__(self):
        self.cfg = load_config()
        self.lock = threading.Lock()
        self._reset_scan()
        self.clean = {"running": False, "done": 0, "total": 0, "current": "", "report": None}
        # NOTE: never store a pywebview Window on this object — pywebview walks the API
        # object's attributes to build the JS bridge and would recurse forever
        # (Window -> _js_api -> window -> ...). Use the module-level WINDOW instead.
        self._js_api_only = True

    # ---------------------------------------------------------- scan
    def _reset_scan(self):
        self.scan = {"running": False, "done": 0, "total": 0, "current": "",
                     "targets": [], "apps": [], "drives": {}, "admin": is_admin(),
                     "elapsed": 0.0, "runningProcs": [], "liveBytes": 0, "liveFiles": 0,
                     "found": 0, "recent": [], "currentFa": ""}

    def cc_start_scan(self, include_discovered=True):
        with self.lock:
            if self.scan["running"]:
                return {"ok": False, "reason": "already running"}
            self._reset_scan()
            self.scan["running"] = True
        threading.Thread(target=self._scan_worker, args=(bool(include_discovered),),
                         daemon=True).start()
        return {"ok": True}

    def _scan_worker(self, include_discovered):
        t0 = time.time()
        try:
            targets = S.build_targets(include_discovered=include_discovered)
            excl = set(self.cfg.get("exclude_apps") or [])
            if excl:
                targets = [t for t in targets if t.app not in excl]
            procs = _running_names(targets)          # subprocess call — never inside the lock
            with self.lock:
                self.scan["total"] = len(targets)
                self.scan["runningProcs"] = procs

            def prog(i, n, t):
                if EXIT.is_set():
                    raise KeyboardInterrupt("window closed")
                with self.lock:
                    self.scan["done"] = i
                    self.scan["current"] = t.app
                    self.scan["currentFa"] = getattr(t, "app_fa", None) or t.app

            def tick(i, n, size, files, t):
                """Real running totals + the newest caches found, for the live scan view."""
                if EXIT.is_set():
                    raise KeyboardInterrupt("window closed")
                with self.lock:
                    self.scan["liveBytes"] = size
                    self.scan["liveFiles"] = files
                    if t.size > 0:
                        self.scan["found"] = self.scan.get("found", 0) + 1
                        recent = self.scan["recent"]
                        recent.append({"app": t.app, "app_fa": getattr(t, "app_fa", None),
                                       "kind": t.kind, "kind_fa": getattr(t, "kind_fa", None),
                                       "size": t.size, "path": t.path})
                        del recent[:-8]

            def walk(i, n, size, files, t):
                """Sub-target updates: fired while one large folder is still being walked.

                Progress here is measured in bytes, not locations, because a single 8 GB temp
                folder can be most of the scan's wall clock — reporting only per-location makes
                the readouts freeze and the ring jump to ~99% and sit there.
                """
                if EXIT.is_set():
                    raise KeyboardInterrupt("window closed")
                with self.lock:
                    self.scan["liveBytes"] = size
                    self.scan["liveFiles"] = files
                    self.scan["current"] = t.app
                    self.scan["currentFa"] = getattr(t, "app_fa", None) or t.app

            S.scan(targets, workers=8, progress=prog, tick=tick, walk=walk)

            drives = S.drive_info()
            procs = _running_names(targets)
            apps = S.installed_apps()
            with self.lock:
                self.scan["drives"] = drives
                self.scan["runningProcs"] = procs
                self.scan["targets"] = [t.as_dict() for t in targets]
                self.scan["apps"] = apps
                self.scan["elapsed"] = time.time() - t0
                self.scan["running"] = False
                self.scan["current"] = ""
        except KeyboardInterrupt:
            # The progress callbacks raise this to abort the scan when the window is closing.
            # It is a BaseException, so `except Exception` does NOT catch it — without this the
            # worker died with a raw traceback instead of marking the scan stopped.
            with self.lock:
                self.scan["running"] = False
                self.scan["error"] = ""
        except Exception:
            with self.lock:
                self.scan["running"] = False
                self.scan["error"] = traceback.format_exc()[-800:]

    def cc_scan_state(self):
        with self.lock:
            return dict(self.scan)

    def cc_entries(self, path):
        """Per-file breakdown of one cache folder (largest first)."""
        items = []
        try:
            if os.path.isfile(path):
                items.append({"name": os.path.basename(path), "size": os.path.getsize(path),
                              "dir": False})
            elif os.path.isdir(path):
                with os.scandir(path) as it:
                    for e in it:
                        try:
                            if e.is_dir(follow_symlinks=False):
                                items.append({"name": e.name, "size": S.dir_size(e.path)[0],
                                              "dir": True})
                            else:
                                items.append({"name": e.name,
                                              "size": e.stat(follow_symlinks=False).st_size,
                                              "dir": False})
                        except OSError:
                            continue
        except Exception:
            pass
        items.sort(key=lambda x: -x["size"])
        return items

    def cc_apps(self):
        return S.installed_apps()

    # ---------------------------------------------------------- clean
    def cc_start_clean(self, paths, kill_first=False):
        with self.lock:
            if self.clean["running"]:
                return {"ok": False, "reason": "already running"}
            self.clean = {"running": True, "done": 0, "total": len(paths), "current": "",
                          "report": None}
        threading.Thread(target=self._clean_worker, args=(list(paths), bool(kill_first)),
                         daemon=True).start()
        return {"ok": True}

    def _clean_worker(self, paths, kill_first):
        try:
            by_path = {}
            for t in self.scan.get("targets", []):
                by_path[t["path"]] = t
            targets = []
            for p in paths:
                d = by_path.get(p)
                if d:
                    t = S.Target(d["app"], d["kind"], d["risk"], d.get("desc", ""),
                                 d.get("processes") or [], d["path"],
                                 source=d.get("source", "rule"),
                                 needs_admin=d.get("needs_admin", False))
                    t.size = d.get("size", 0)
                    t.files = d.get("files", 0)
                else:
                    t = S.Target("Cache", "Cache", "low", "", [], p)
                targets.append(t)

            if kill_first:
                procs = sorted({p for t in targets for p in t.processes})
                live = set(x.lower() for x in self.scan.get("runningProcs", []))
                for p in procs:
                    if p.lower() in live:
                        with self.lock:
                            self.clean["current"] = "closing " + p
                        subprocess.run(["taskkill", "/IM", p, "/T", "/F"],
                                       capture_output=True, creationflags=_CREATE_NO_WINDOW)
                time.sleep(2)

            def on_target(t, r, _rep):
                with self.lock:
                    self.clean["done"] += 1
                    self.clean["current"] = t.app

            rep = C.clean_many(targets, dry_run=False, on_target=on_target)
            with self.lock:
                self.clean["report"] = {
                    "freed": rep["freed"],
                    "failed": rep["failed"],
                    "skipped": rep["skipped"],
                    "paths": len(targets),
                    "seconds": rep["t1"] - rep["t0"],
                    "details": [{"app": x["app"], "path": x["path"], "freed": x["freed"],
                                 "reason": x["reason"], "failed": len(x["failed"])}
                                for x in rep["targets"]],
                }
                self.clean["running"] = False
                self.clean["current"] = ""
        except Exception:
            with self.lock:
                self.clean["running"] = False
                self.clean["report"] = {"freed": 0, "failed": 0, "skipped": 0,
                                        "paths": 0, "error": traceback.format_exc()[-600:]}

    def cc_clean_state(self):
        with self.lock:
            return dict(self.clean)

    def cc_preview(self, paths):
        """Safety dry-run: what would be freed, and whether each path is allowed."""
        by_path = {t["path"]: t for t in self.scan.get("targets", [])}
        targets = []
        for p in paths:
            d = by_path.get(p)
            t = S.Target(d["app"] if d else "Cache", d["kind"] if d else "Cache",
                         d["risk"] if d else "low", "", [], p)
            targets.append(t)
        return C.preview(targets)

    # ---------------------------------------------------------- misc
    def cc_open(self, path):
        try:
            if os.path.isdir(path):
                os.startfile(path)
            elif os.path.exists(path):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            else:
                return {"ok": False, "reason": "does not exist"}
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    def cc_kill(self, procs):
        killed = []
        live = set(x.lower() for x in self.scan.get("runningProcs", []))
        for p in procs or []:
            if p.lower() in live:
                subprocess.run(["taskkill", "/IM", p, "/T", "/F"],
                               capture_output=True, creationflags=_CREATE_NO_WINDOW)
                killed.append(p)
        return {"killed": killed}

    def cc_relaunch_admin(self):
        if is_admin():
            return {"ok": False, "reason": "already elevated"}
        try:
            exe = sys.executable
            pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
            if os.path.exists(pyw):
                exe = pyw
            script = os.path.join(APP_DIR, "app.py")
            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe,
                                                '"%s"' % script, APP_DIR, 1)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    def cc_config(self, patch=None):
        if isinstance(patch, dict):
            self.cfg.update(patch)
            if self.cfg.get("lang") not in ("en", "fa"):
                self.cfg["lang"] = "en"
            save_config(self.cfg)
        return dict(self.cfg)

    def cc_open_link(self, which):
        """Open one of the author's profile links in the default browser.

        The URL is looked up in USER_LINKS and the host is checked against LINK_HOSTS, so
        the interface can never hand an arbitrary string to ShellExecute.
        """
        url = USER_LINKS.get(str(which))
        if not url:
            return {"ok": False, "reason": "unknown link"}
        try:
            host = urllib.parse.urlsplit(url).netloc.lower()
        except Exception:
            return {"ok": False, "reason": "bad url"}
        if host not in LINK_HOSTS:
            return {"ok": False, "reason": "host not allowed"}
        try:
            os.startfile(url)
            return {"ok": True, "url": url}
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    def cc_info(self):
        return {"admin": is_admin(), "app_dir": APP_DIR, "python": sys.version.split()[0],
                "lang": self.cfg.get("lang", "en"),
                "links": {"github": USER_LINKS["github"], "linkedin": USER_LINKS["linkedin"]}}

    def cc_js_error(self, message):
        """Interface errors are reported here so they are never silently swallowed."""
        try:
            d = os.path.join(APP_DIR, "logs")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "ui-errors.log"), "a", encoding="utf-8") as f:
                f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), str(message)[:600]))
        except Exception:
            pass
        return {"ok": True}


def _running_names(targets):
    names = sorted({p for t in targets for p in (t.processes or [])})
    if not names:
        return []
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                             timeout=25, creationflags=_CREATE_NO_WINDOW)
        txt = out.stdout.decode("utf-8", "replace").lower()
    except Exception:
        return []
    return [n for n in names if n.lower() in txt]


# ================================================================ main
def _single_instance_guard():
    """Only one Cache Cleaner may run at a time.

    Two copies are the classic cause of "I closed it but it is still in the background":
    the second window stays hidden behind the first, so closing the visible one leaves a
    live process. A named mutex makes the second launch exit immediately.

    Two details matter: the mutex lives in the Local\\ namespace (Global\\ needs
    SeCreateGlobalPrivilege, which a normal user does not have, so CreateMutexW would fail
    with ERROR_ACCESS_DENIED and the guard would silently never engage), and kernel32 must
    be loaded with use_last_error=True — plain ctypes.windll does not preserve the last
    error, so GetLastError() reads 0 and the already-exists check never fires.
    """
    if os.name != "nt":
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, "Local\\CacheCleanerSingleInstance")
    if not handle:
        return None
    if ctypes.get_last_error() == 183:          # ERROR_ALREADY_EXISTS
        return "exists"
    return handle


def _set_app_user_model_id(app_id="MohammadMehdiSadeghi.CacheCleaner"):
    """Tell Windows which app this window belongs to.

    The TITLEBAR icon comes from webview.start(icon=...), but the TASKBAR button does not use
    it: Windows groups taskbar buttons by the process's AppUserModelID and, when that is unset,
    falls back to the executable's own icon — so a pythonw.exe-hosted app shows the Python logo
    in the taskbar. Setting an explicit AppUserModelID (and, since the process has no shortcut
    Windows can read it from, a relaunch stub registered under it) makes the taskbar use ours.
    """
    if os.name != "nt":
        return False
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except Exception:
        return False


def _apply_window_icons(hwnd, ico_path):
    """Set both the big and small window icons from our .ico, on the window itself.

    SetClassLongPtr with GCLP_HICON/GCLP_HICONSM changes the class defaults; that is what the
    taskbar and Alt-Tab read. LoadImage with LR_LOADFROMFILE gives us the image sizes Windows
    actually asks for (32 and 16 px).
    """
    if os.name != "nt" or not hwnd or not os.path.exists(ico_path):
        return False
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.LoadImageW.restype = ctypes.c_void_p
    user32.LoadImageW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.SendMessageW.restype = ctypes.c_void_p
    user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    user32.SetClassLongPtrW.restype = ctypes.c_void_p
    user32.SetClassLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]

    IMAGE_ICON, LR_LOADFROMFILE = 1, 0x0010
    WM_SETICON, ICON_SMALL, ICON_BIG = 0x0080, 0, 1
    GCLP_HICON, GCLP_HICONSM = -14, -34

    ok = False
    for size, which, gcl in ((32, ICON_BIG, GCLP_HICON), (16, ICON_SMALL, GCLP_HICONSM)):
        h = user32.LoadImageW(None, ico_path, IMAGE_ICON, size, size, LR_LOADFROMFILE)
        if not h:
            continue
        user32.SendMessageW(hwnd, WM_SETICON, which, h)
        user32.SetClassLongPtrW(hwnd, gcl, h)
        ok = True
    return ok


def _focus_hwnd(title="Cache Cleaner"):
    """The HWND of our own window (used to stamp the icon onto the window class)."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.FindWindowW.restype = ctypes.c_void_p
        user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        return user32.FindWindowW(None, title)
    except Exception:
        return None


def _focus_existing_window():
    """Bring the already-running window to the front (best effort)."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hwnd = user32.FindWindowW(None, "Cache Cleaner")
        if hwnd:
            user32.ShowWindow(hwnd, 9)          # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def main():
    guard = _single_instance_guard()
    if guard == "exists":
        # A second launch must not start a duplicate process (that is exactly how a window
        # ends up running invisibly in the background). Surface the existing one instead.
        # No modal dialog here: MessageBoxW blocks the process until someone clicks it,
        # which leaves a stuck copy alive — the very thing this guard exists to prevent.
        _focus_existing_window()
        return

    # The taskbar groups buttons by AppUserModelID; without one it shows pythonw.exe's icon.
    if not os.environ.get("CC_NO_AUMID"):
        _set_app_user_model_id()

    if not os.path.exists(UI_INDEX):
        raise SystemExit("ui/index.html is missing next to app.py")
    try:
        import webview
    except ImportError:
        raise SystemExit(
            "pywebview is required for the interface.\n"
            "Install it with:  pip install pywebview\n"
            "Or use the command line: python report.py --top 25")

    cfg = load_config()
    win_cfg = cfg.get("window", {})
    api = Api()
    window = webview.create_window(
        "Cache Cleaner", UI_INDEX, js_api=api,
        width=int(win_cfg.get("w", 1400)), height=int(win_cfg.get("h", 900)),
        min_size=(980, 620), background_color="#0a0b0d", text_select=True)
    WINDOW[0] = window

    def on_closing():
        # Tell the workers to stop and remember the window size before the webview tears
        # itself down; anything left running after this keeps the process alive in the
        # background with no visible window.
        EXIT.set()
        try:
            cfg["window"] = {"w": int(window.width), "h": int(window.height)}
            save_config(cfg)
        except Exception:
            pass
        return True          # allow the close

    try:
        window.events.closing += on_closing
    except Exception:
        pass

    def on_shown():
        """Stamp our .ico onto the real HWND once Windows has created it."""
        if os.environ.get("CC_NO_ICONS"):
            return
        hwnd = _focus_hwnd()
        if hwnd and os.path.exists(ICON_ICO):
            _apply_window_icons(hwnd, ICON_ICO)

    try:
        window.events.shown += on_shown
    except Exception:
        pass

    icon = ICON_ICO if os.path.exists(ICON_ICO) else None
    webview.start(debug=bool(os.environ.get("CC_DEBUG")), icon=icon)

    # webview.start() returns once the window is gone — make sure nothing outlives it.
    EXIT.set()
    try:
        cfg["window"] = {"w": int(window.width), "h": int(window.height)}
        save_config(cfg)
    except Exception:
        pass
    # Non-daemon stragglers (a thread pool still winding down) would keep the process in
    # the background. Nothing is left to do once the window is closed, so exit explicitly.
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc()
        try:
            ctypes.windll.user32.MessageBoxW(None, err[-1200:], "Cache Cleaner", 0x10)
        except Exception:
            print(err)
        sys.exit(1)
