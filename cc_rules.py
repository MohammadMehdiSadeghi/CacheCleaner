# -*- coding: utf-8 -*-
"""
cc_rules.py — Cache location rules for known applications, plus the protected-path lists.

Each rule describes one application: where its caches live, what the cache contains
(shown to the user before deleting), how risky it is, and which process owns it.

Rule fields
-----------
app        Display name shown in the UI.
kind       Short category label ("Browser cache", "Package cache", ...).
risk       "low"  -> safe, rebuilt automatically.
           "medium" -> safe but costs a rebuild (index, package re-download, ...).
desc       What the cache actually contains, in plain English.
processes  Executable names that must be closed for a full clean.
paths      Path patterns; %VARS% and * wildcards are supported.
needs_admin  True when deletion requires an elevated shell.
"""
import os

# ---------------------------------------------------------------- environment
ENV = {
    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
    "APPDATA": os.environ.get("APPDATA", ""),
    "PROGRAMDATA": os.environ.get("ProgramData", r"C:\ProgramData"),
    "USERPROFILE": os.environ.get("USERPROFILE", ""),
    "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
    "PROGRAMFILES": os.environ.get("ProgramFiles", r"C:\Program Files"),
    "PROGRAMFILES_X86": os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    "TEMP": os.environ.get("TEMP", ""),
}


def expand(p: str) -> str:
    """Expand %VAR% placeholders and normalise separators."""
    for k, v in ENV.items():
        p = p.replace("%" + k + "%", v)
    return os.path.normpath(os.path.expandvars(p))


def _chromium(base: str) -> list:
    """Cache sub-paths shared by every Chromium-based browser/Electron app."""
    subs = [
        r"*\Cache", r"*\Cache\Cache_Data", r"*\Code Cache", r"*\GPUCache",
        r"*\Media Cache", r"*\Application Cache", r"*\Service Worker\CacheStorage",
        r"*\DawnCache", r"*\DawnGraphiteCache", r"*\DawnWebGPUCache",
        r"*\GrShaderCache", r"ShaderCache", r"ShaderCache\GPUCache",
        r"*\Session Storage\Logs", r"*\blob_storage", r"*\Cache\No_Vary_Search",
        r"*\optimization_guide_hint_cache_store", r"*\shared_proto_db",
    ]
    return [base + s for s in subs]


# ---------------------------------------------------------------- rules
RULES = [
    # ---------- browsers ----------
    dict(app="Google Chrome", kind="Browser cache", risk="low", processes=["chrome.exe"],
         desc="Cached page assets (HTML/CSS/JS/images), compiled JavaScript, GPU shader and "
              "media buffers. Sites feel slower on the first visit after cleaning. Bookmarks, "
              "passwords, cookies and history are stored elsewhere and are never touched.",
         paths=_chromium(r"%LOCALAPPDATA%\Google\Chrome\User Data")),
    dict(app="Microsoft Edge", kind="Browser cache", risk="low", processes=["msedge.exe"],
         desc="Cached page assets, compiled JavaScript and GPU shaders for Edge. "
              "Favourites, passwords and cookies are not in these folders.",
         paths=_chromium(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")),
    dict(app="Brave", kind="Browser cache", risk="low", processes=["brave.exe"],
         desc="Cached page assets and GPU shader cache for Brave.",
         paths=_chromium(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")),
    dict(app="Opera / Opera GX", kind="Browser cache", risk="low", processes=["opera.exe", "opera_gx.exe"],
         desc="Cached page assets and compiled JavaScript for Opera and Opera GX.",
         paths=_chromium(r"%APPDATA%\Opera Software\Opera Stable")
               + _chromium(r"%APPDATA%\Opera Software\Opera GX Stable")
               + _chromium(r"%LOCALAPPDATA%\Opera Software\Opera Stable")),
    dict(app="Vivaldi", kind="Browser cache", risk="low", processes=["vivaldi.exe"],
         desc="Cached page assets for Vivaldi.",
         paths=_chromium(r"%LOCALAPPDATA%\Vivaldi\User Data")),
    dict(app="Mozilla Firefox", kind="Cache", risk="low", processes=["firefox.exe"],
         desc="The HTTP cache (cache2), startup cache, shader cache and thumbnail cache. "
              "Your profile, bookmarks and logins are outside these folders.",
         paths=[r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\cache2",
                r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\startupCache",
                r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\shader-cache",
                r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\thumbnails",
                r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\jumpListCache",
                r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\safebrowsing"]),

    # ---------- messaging ----------
    dict(app="Telegram Desktop", kind="Media cache", risk="low", processes=["Telegram.exe"],
         desc="Cached photos and videos from your chats plus the emoji set. Messages, your "
              "account and downloaded files (tdata, media) are untouched.",
         paths=[r"%APPDATA%\Telegram Desktop\tdata\user_data\cache",
                r"%APPDATA%\Telegram Desktop\tdata\user_data\emoji",
                r"%APPDATA%\Telegram Desktop\tdata\emoji"]),
    dict(app="Discord", kind="Electron cache", risk="low", processes=["Discord.exe", "Update.exe"],
         desc="Cached page assets, compiled JavaScript and GPU shaders used by the Discord client.",
         paths=_chromium(r"%APPDATA%\discord") + _chromium(r"%APPDATA%\Discord")),
    dict(app="Slack", kind="Electron cache", risk="low", processes=["slack.exe"],
         desc="Cached page assets and temporary files used by the Slack client.",
         paths=_chromium(r"%APPDATA%\Slack")),
    dict(app="WhatsApp Desktop", kind="Store app cache", risk="medium", processes=["WhatsApp.exe"],
         desc="Internal cache of the Microsoft Store build of WhatsApp. "
              "Your chats live in LocalState and are not touched.",
         paths=[r"%LOCALAPPDATA%\Packages\5319275A.WhatsAppDesktop_*\LocalCache",
                r"%LOCALAPPDATA%\Packages\5319275A.WhatsAppDesktop_*\TempState"]),
    dict(app="Microsoft Teams", kind="Electron cache", risk="low", processes=["Teams.exe", "ms-teams.exe"],
         desc="Cached page assets, compiled JavaScript and logs for classic and new Teams.",
         paths=_chromium(r"%APPDATA%\Microsoft\Teams")
               + _chromium(r"%LOCALAPPDATA%\Microsoft\Teams")
               + [r"%APPDATA%\Microsoft\Teams\logs",
                  r"%LOCALAPPDATA%\Microsoft\TeamsMeetingAddin"]),

    # ---------- media ----------
    dict(app="Spotify", kind="Offline audio cache", risk="low", processes=["Spotify.exe"],
         desc="Songs downloaded for offline playback plus cached album art. "
              "Tracks are re-downloaded when you play them again.",
         paths=[r"%LOCALAPPDATA%\Spotify\Storage", r"%LOCALAPPDATA%\Spotify\Browser\Cache",
                r"%LOCALAPPDATA%\Spotify\Data"]),
    dict(app="VLC", kind="Plugin cache", risk="low", processes=["vlc.exe"],
         desc="Plugin cache and temporary files created by VLC.",
         paths=[r"%APPDATA%\vlc\cache", r"%LOCALAPPDATA%\vlc\cache"]),
    dict(app="Adobe Premiere / After Effects", kind="Media cache", risk="low",
         processes=["Adobe Premiere Pro.exe", "AfterFX.exe"],
         desc="Media Cache and Peak Files for Adobe projects. They are rebuilt on demand, "
              "so the first open of an old project is slower afterwards.",
         paths=[r"%APPDATA%\Adobe\Common\Media Cache", r"%APPDATA%\Adobe\Common\Media Cache Files",
                r"%APPDATA%\Adobe\Common\Peak Files", r"%APPDATA%\Adobe\Common\Team Projects Cache"]),
    dict(app="Adobe Camera Raw", kind="AI model cache", risk="low",
         processes=["Photoshop.exe", "Bridge.exe"],
         desc="Adobe's AI models for denoise, subject select and reflection removal. "
              "Each feature re-downloads its model the next time you use it.",
         paths=[r"%PROGRAMDATA%\Adobe\CameraRaw\ModelZoo"], needs_admin=True),

    # ---------- developer ----------
    dict(app="Visual Studio Code", kind="Editor cache", risk="low", processes=["Code.exe"],
         desc="Compiled JavaScript cache, GPU cache and logs. Extensions and settings are not "
              "in these folders. Includes cached extension installers (VSIX).",
         paths=[r"%APPDATA%\Code\Cache", r"%APPDATA%\Code\CachedData", r"%APPDATA%\Code\Code Cache",
                r"%APPDATA%\Code\GPUCache", r"%APPDATA%\Code\logs", r"%APPDATA%\Code\DawnCache",
                r"%APPDATA%\Code\CachedExtensionVSIXs", r"%APPDATA%\Code\CachedProfilesData"]),
    dict(app="Cursor", kind="Editor cache", risk="low", processes=["Cursor.exe"],
         desc="Compiled JavaScript cache, GPU cache and logs for the Cursor editor.",
         paths=[r"%APPDATA%\Cursor\Cache", r"%APPDATA%\Cursor\CachedData", r"%APPDATA%\Cursor\Code Cache",
                r"%APPDATA%\Cursor\GPUCache", r"%APPDATA%\Cursor\logs", r"%APPDATA%\Cursor\DawnCache"]),
    dict(app="JetBrains IDEs", kind="Index cache", risk="medium",
         processes=["idea64.exe", "pycharm64.exe", "webstorm64.exe"],
         desc="Project indexes, caches, logs and temp files for IntelliJ-based IDEs. "
              "Projects are re-indexed the next time you open them.",
         paths=[r"%LOCALAPPDATA%\JetBrains\*\caches", r"%LOCALAPPDATA%\JetBrains\*\index",
                r"%LOCALAPPDATA%\JetBrains\*\log", r"%LOCALAPPDATA%\JetBrains\*\tmp",
                r"%LOCALAPPDATA%\JetBrains\*\compile-server"]),
    dict(app="npm", kind="Package cache", risk="low", processes=[],
         desc="Downloaded npm packages. The next `npm install` re-downloads only what it needs.",
         paths=[r"%LOCALAPPDATA%\npm-cache", r"%APPDATA%\npm-cache"]),
    dict(app="pip (Python)", kind="Package cache", risk="low", processes=[],
         desc="Downloaded wheels and source archives used by pip.",
         paths=[r"%LOCALAPPDATA%\pip\Cache"]),
    dict(app="Yarn", kind="Package cache", risk="low", processes=[],
         desc="Yarn package cache (classic and Berry).",
         paths=[r"%LOCALAPPDATA%\Yarn\Cache", r"%LOCALAPPDATA%\Yarn\berry\cache"]),
    dict(app="pnpm", kind="Package store", risk="medium", processes=[],
         desc="pnpm content-addressable store. Safe to clear, but every project must "
              "re-link or re-download its packages afterwards.",
         paths=[r"%LOCALAPPDATA%\pnpm\store", r"%LOCALAPPDATA%\pnpm-store"]),
    dict(app="uv (Python)", kind="Package cache", risk="low", processes=[],
         desc="Downloaded wheels and build artefacts cached by uv.",
         paths=[r"%LOCALAPPDATA%\uv\cache"]),
    dict(app="NuGet / .NET", kind="Package cache", risk="medium", processes=[],
         desc="NuGet packages and scratch files. The next build re-downloads what it needs.",
         paths=[r"%USERPROFILE%\.nuget\packages", r"%LOCALAPPDATA%\NuGet\v3-cache",
                r"%LOCALAPPDATA%\Temp\NuGetScratch"]),
    dict(app="Gradle / Maven", kind="Build cache", risk="medium", processes=[],
         desc="Java dependency and build caches. The next build re-downloads them.",
         paths=[r"%USERPROFILE%\.gradle\caches", r"%USERPROFILE%\.gradle\daemon",
                r"%USERPROFILE%\.m2\repository"]),
    dict(app="Docker Desktop", kind="Container logs", risk="medium",
         processes=["Docker Desktop.exe"],
         desc="Daemon logs and image download cache. Your images and volumes are not touched.",
         paths=[r"%LOCALAPPDATA%\Docker\log", r"%LOCALAPPDATA%\Docker\cache"]),

    # ---------- Windows ----------
    dict(app="Windows — User temp", kind="Temp files", risk="low", processes=[],
         desc="Temporary files written by applications. Files that are still in use are "
              "locked and will be skipped automatically.",
         paths=[r"%LOCALAPPDATA%\Temp"]),
    dict(app="Windows — System temp", kind="Temp files", risk="low", processes=[],
         needs_admin=True,
         desc="System-wide temporary files. Requires an elevated shell.",
         paths=[r"%WINDIR%\Temp"]),
    dict(app="Windows — Crash dumps", kind="Crash dumps", risk="low", processes=[],
         desc="Memory dumps written when an application crashed.",
         paths=[r"%LOCALAPPDATA%\CrashDumps"]),
    dict(app="Windows — Error reports", kind="Error reports", risk="low", processes=[],
         desc="Windows Error Reporting queues that are waiting to be sent to Microsoft.",
         paths=[r"%LOCALAPPDATA%\Microsoft\Windows\WER", r"%PROGRAMDATA%\Microsoft\Windows\WER"]),
    dict(app="Windows — Internet & Web cache", kind="System cache", risk="low", processes=[],
         desc="WinINet/WebView caches, icon caches and Remote Desktop bitmap cache.",
         paths=[r"%LOCALAPPDATA%\Microsoft\Windows\INetCache",
                r"%LOCALAPPDATA%\Microsoft\Windows\WebCache",
                r"%LOCALAPPDATA%\Microsoft\Windows\Caches",
                r"%LOCALAPPDATA%\Microsoft\Terminal Server Client\Cache"]),
    dict(app="Windows — Icon & thumbnail cache", kind="Icon cache", risk="medium",
         processes=["explorer.exe"],
         desc="Explorer icon and thumbnail databases. Windows locks them while Explorer runs, "
              "so locked files are skipped unless Explorer is closed first.",
         paths=[r"%LOCALAPPDATA%\Microsoft\Windows\Explorer"]),
    dict(app="Windows — DirectX shader cache", kind="GPU cache", risk="low", processes=[],
         desc="Compiled DirectX shaders. Games and GPU apps take slightly longer on first launch.",
         paths=[r"%LOCALAPPDATA%\D3DSCache"]),
    dict(app="NVIDIA", kind="GPU cache", risk="low", processes=[],
         desc="NVIDIA shader caches (DirectX and OpenGL) and driver download cache.",
         paths=[r"%LOCALAPPDATA%\NVIDIA\DXCache", r"%LOCALAPPDATA%\NVIDIA\GLCache",
                r"%LOCALAPPDATA%\NVIDIA Corporation\NV_Cache",
                r"%PROGRAMDATA%\NVIDIA Corporation\NV_Cache"]),
    dict(app="Windows Update", kind="Update cache", risk="medium", processes=[], needs_admin=True,
         desc="Already-downloaded Windows updates. Do not clean this while an update is "
              "installing or pending a restart.",
         paths=[r"%WINDIR%\SoftwareDistribution\Download"]),
    dict(app="Windows — Prefetch", kind="Boot cache", risk="medium", processes=[], needs_admin=True,
         desc="Prefetch traces Windows uses to launch applications faster. Applications start "
              "slightly slower until the traces are rebuilt.",
         paths=[r"%WINDIR%\Prefetch"]),
    dict(app="Windows — Delivery Optimization", kind="Update cache", risk="medium",
         processes=[], needs_admin=True,
         desc="Peer-to-peer update download cache shared between PCs on your network.",
         paths=[r"%LOCALAPPDATA%\Microsoft\Windows\DeliveryOptimization"]),
    dict(app="OneDrive", kind="Logs", risk="low", processes=["OneDrive.exe"],
         desc="OneDrive diagnostic logs. Synced files and the local OneDrive folder are not touched.",
         paths=[r"%LOCALAPPDATA%\Microsoft\OneDrive\logs",
                r"%LOCALAPPDATA%\Microsoft\OneDrive\setup\logs"]),
    dict(app="Microsoft Office", kind="File cache", risk="low",
         processes=["WINWORD.EXE", "EXCEL.EXE"],
         desc="Office file cache: recent versions of documents kept for fast reopen and recovery.",
         paths=[r"%LOCALAPPDATA%\Microsoft\Office\16.0\OfficeFileCache",
                r"%LOCALAPPDATA%\Microsoft\Office\15.0\OfficeFileCache"]),
    dict(app="Xbox / Game Bar", kind="Store app cache", risk="low", processes=["GameBar.exe"],
         desc="Internal caches of the Xbox, Game Bar and Microsoft Store apps.",
         paths=[r"%LOCALAPPDATA%\Packages\Microsoft.XboxGamingOverlay_*\LocalCache",
                r"%LOCALAPPDATA%\Packages\Microsoft.GamingApp_*\LocalCache",
                r"%LOCALAPPDATA%\Packages\Microsoft.WindowsStore_*\LocalCache"]),

    # ---------- launchers ----------
    dict(app="Steam", kind="Launcher cache", risk="medium", processes=["steam.exe"],
         desc="Steam's built-in browser cache, shader cache, logs and download manifests. "
              "Installed games are not touched.",
         paths=[r"%PROGRAMFILES_X86%\Steam\appcache", r"%PROGRAMFILES_X86%\Steam\htmlcache",
                r"%PROGRAMFILES_X86%\Steam\steamapps\shadercache", r"%PROGRAMFILES_X86%\Steam\logs",
                r"%PROGRAMFILES_X86%\Steam\depotcache"]),
    dict(app="Epic Games Launcher", kind="Launcher cache", risk="low",
         processes=["EpicGamesLauncher.exe"],
         desc="Web cache and logs for the Epic Games Launcher.",
         paths=[r"%LOCALAPPDATA%\EpicGamesLauncher\Saved\webcache",
                r"%LOCALAPPDATA%\EpicGamesLauncher\Saved\Logs"]),

    # ---------- local tooling ----------
    dict(app="XAMPP (Apache)", kind="Server logs", risk="low", processes=["httpd.exe"],
         desc="Apache access and error logs. Your site files and configuration are not touched.",
         paths=[r"C:\xampp\apache\logs"]),
    dict(app="MongoDB", kind="Database logs", risk="low", processes=["mongod.exe"],
         desc="MongoDB server logs. Your databases are not touched.",
         paths=[r"C:\ProgramData\MongoDB\log"]),
    dict(app="Installer temp folders", kind="Temp files", risk="low", processes=[],
         desc="Temp folders left behind by installers and package managers.",
         paths=[r"%PROGRAMDATA%\Temp", r"%LOCALAPPDATA%\Temp\chocolatey"]),
]

# ---------------------------------------------------------------- protection
# PROTECTED_STRICT: never offered for cleaning, and never deletable (path or any child).
PROTECTED_STRICT = [
    r"%USERPROFILE%\.ssh",
    r"%USERPROFILE%\.gnupg",
    r"%USERPROFILE%\Desktop",
    r"%USERPROFILE%\Documents",
    r"%USERPROFILE%\Downloads",
    r"%USERPROFILE%\Pictures",
    r"%USERPROFILE%\Videos",
    r"%USERPROFILE%\OneDrive",
    r"%APPDATA%\npm",                       # globally installed npm packages
    r"%APPDATA%\Microsoft\Crypto",
    r"%APPDATA%\Microsoft\Protect",
    r"%WINDIR%\System32",
    r"%WINDIR%\SysWOW64",
]

# PROTECTED_SCOPED: (root, allowed segments). The root itself is protected, but a path below
# it is deletable when one of its segments is in the allowed list — e.g.
#   Chrome\User Data\<profile>\Cache        -> allowed
#   Chrome\User Data\<profile>\Login Data   -> blocked
_CACHE_SEGS = ("cache", "caches", "cache_data", "cache2", "code cache", "gpucache",
               "gpu cache", "media cache", "imagecache", "image cache", "appcache",
               "application cache", "cachestorage", "service worker", "shadercache",
               "shader-cache", "grshadercache", "dawncache", "dawn_graphitecache",
               "dawnwebgpucache", "graphitecache", "blob_storage", "session storage",
               "shared_proto_db", "no_vary_search", "optimization_guide_hint_cache_store",
               "webcache", "htmlcache", "startupcache", "thumbnails", "jumplistcache",
               "safebrowsing", "cacheddata", "cachedprofilesdata", "cachedmessages", "logs",
               "localcache", "tempstate", "inetcache", "crashdumps", "d3dscache",
               "nvcache", "emoji")

PROTECTED_SCOPED = [
    (r"%LOCALAPPDATA%\Google\Chrome\User Data", _CACHE_SEGS),
    (r"%LOCALAPPDATA%\Microsoft\Edge\User Data", _CACHE_SEGS),
    (r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data", _CACHE_SEGS),
    (r"%APPDATA%\Opera Software", _CACHE_SEGS),
    (r"%LOCALAPPDATA%\Vivaldi\User Data", _CACHE_SEGS),
    (r"%APPDATA%\Mozilla\Firefox\Profiles", ("cache2", "startupcache", "shader-cache",
                                             "thumbnails", "jumplistcache", "safebrowsing")),
    (r"%APPDATA%\Telegram Desktop\tdata", ("cache", "emoji")),
    (r"%LOCALAPPDATA%\Packages", ("localcache", "tempstate")),
    (r"%PROGRAMDATA%\Adobe\CameraRaw", ("modelzoo",)),
]

PROTECTED_STRICT = [expand(p).lower() for p in PROTECTED_STRICT]
PROTECTED_SCOPED = [(expand(p).lower(), tuple(s.lower() for s in segs))
                    for p, segs in PROTECTED_SCOPED]


def protection_status(path):
    """Return (blocked, reason). Scoped roots only allow their cache sub-paths."""
    if not path:
        return True, "empty path"
    low = os.path.normpath(path).lower().rstrip("\\")
    for prot in PROTECTED_STRICT:
        if low == prot or low.startswith(prot + os.sep):
            return True, "protected path"
    for root, segs in PROTECTED_SCOPED:
        if low == root or low.startswith(root + os.sep):
            rel = low[len(root):].strip(os.sep)
            parts = [p for p in rel.split(os.sep) if p]
            if not parts:
                return True, "protected root"
            if any(p in segs for p in parts):
                return False, ""
            return True, "inside a protected folder but not a cache"
    return False, ""


# Backwards-compatible aliases
PROTECTED = PROTECTED_STRICT + [r for r, _ in PROTECTED_SCOPED]
PROTECTED_ALLOW = [(r, s) for r, s in PROTECTED_SCOPED]

# Folder names that are recognised as caches (used by auto-discovery).
CACHE_DIR_NAMES = {
    "cache", "caches", "cache2", "code cache", "gpucache", "gpu cache", "shadercache",
    "shader cache", "cachestorage", "cacheddata", "cachedprofilesdata", "blob_storage",
    "dawncache", "dawn_graphitecache", "graphitecache", "webcache",
    "appcache", "htmlcache", "thumbnails", "thumbcache", "startupcache",
    "localcache", "tempstate", "inetcache", "crashdumps", "d3dscache", "nvcache",
    "service worker", "indexeddb.blob", "media cache", "imagecache", "image cache",
    "optimization_guide_hint_cache_store", "cachedmessages", "cache_data",
}

# Folder names that are never descended into during discovery (speed + safety).
PRUNE_NAMES = {
    "node_modules", ".git", ".svn", ".hg", "venv", ".venv", "__pycache__", "site-packages",
    "dist", "build", "target", "obj", "bin", "lib", "include", "src", "assets", "media",
    "logs", "log", "installer", "installers", "update", "updates", "driverstore",
    "windowsapps", "winsxs", "assembly", "packages",
    "photoshop", "premiere pro", "after effects", "games", "steamapps",
}

# Auto-discovery roots: (path, max depth, label)
DISCOVER_ROOTS = [
    (r"%LOCALAPPDATA%", 3, "AppData Local"),
    (r"%APPDATA%", 3, "AppData Roaming"),
    (r"%PROGRAMDATA%", 2, "ProgramData"),
    (r"%LOCALAPPDATA%\Packages", 2, "Store apps"),
]
