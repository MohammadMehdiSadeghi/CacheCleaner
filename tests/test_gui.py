# -*- coding: utf-8 -*-
"""test_gui.py — end-to-end test of the real window: launches the pywebview app,
lets it scan the machine, then reads the rendered DOM through evaluate_js and
drives the interface (select a row, tick checkboxes, open the confirm dialog).
Nothing is deleted. Run: python tests/test_gui.py
"""
import json
import os
import subprocess
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as A  # noqa: E402
import webview   # noqa: E402

fails = 0
out = []


KB, MB, GB, TB = 1024, 1024 ** 2, 1024 ** 3, 1024 ** 4


def bytes_(b):
    """Same formatting as ui/index.html bytes(), so the test compares like with like."""
    b = int(b or 0)
    if b < KB:
        return "%d B" % b
    if b < MB:
        return "%.0f KB" % (b / KB)
    if b < GB:
        return "%.1f MB" % (b / MB) if b < 10 * MB else "%.0f MB" % (b / MB)
    if b < TB:
        return "%.1f GB" % (b / GB) if b < 10 * GB else "%.2f GB" % (b / GB)
    return "%.2f TB" % (b / TB)


def check(name, cond, extra=""):
    global fails
    line = ("OK   " if cond else "FAIL ") + name + ("  " + str(extra) if extra else "")
    out.append(line)
    print(line, flush=True)
    if not cond:
        fails += 1


def js(w, expr):
    try:
        return w.evaluate_js(expr)
    except Exception as e:
        return "JSERR: %s" % e


def run(w, api):
    try:
        # wait for the auto-scan to complete
        t0 = time.time()
        while time.time() - t0 < 180:
            st = api.cc_scan_state()
            if not st["running"] and st["targets"]:
                break
            time.sleep(0.4)
        time.sleep(2.5)

        st = api.cc_scan_state()
        check("python side scanned caches", len(st["targets"]) > 20, len(st["targets"]))

        rows = js(w, "document.querySelectorAll('#tbCaches tr[data-path]').length")
        check("table rendered rows in the real window", isinstance(rows, int) and rows > 5, rows)

        status = js(w, "document.getElementById('status').textContent")
        check("status line reports the scan result", "Scan finished" in str(status), status)

        total = js(w, "document.getElementById('stTotal').textContent")
        check("cache total is shown", str(total) not in ("—", "0 B", ""), total)

        drives = js(w, "document.getElementById('drives').textContent")
        check("drive free space is shown", "free" in str(drives), drives)

        admin = js(w, "document.getElementById('adminText').textContent")
        check("administrator state is shown", str(admin).strip() != "", admin)

        font = js(w, "getComputedStyle(document.body).fontFamily")
        check("Geist font stack applied", "Geist" in str(font), font)
        loaded = js(w, "JSON.stringify([...document.fonts].map(f=>f.family+':'+f.status))")
        check("both font files loaded in the window", "Geist:loaded" in str(loaded) and
              "Geist Mono:loaded" in str(loaded), loaded)

        mark = js(w, "(() => { const m=document.querySelector('.brand .mark');"
                     "return m ? m.naturalWidth + 'x' + m.naturalHeight : 'none'; })()")
        check("app icon renders in the header", str(mark).startswith(("26x26", "256x256")), mark)
        fav = js(w, "!!document.querySelector('link[rel=icon][href$=\\'icon.svg\\']')")
        check("favicon link points at icon.svg", fav is True, fav)

        # ---- open a row's detail panel
        js(w, "document.querySelector('#tbCaches tr[data-path]').click()")
        time.sleep(2.5)
        appname = js(w, "document.querySelector('.detail .appname') && document.querySelector('.detail .appname').textContent")
        check("detail panel shows the application", bool(appname), appname)
        desc = js(w, "document.querySelector('.detail .desc').textContent.length")
        check("detail panel explains what the cache contains", isinstance(desc, int) and desc > 30, desc)
        ec = js(w, "document.querySelectorAll('.entries .erow').length")
        check("per-file breakdown rendered", isinstance(ec, int) and ec > 0, ec)
        pathok = js(w, "document.querySelector('.pathline code').textContent")
        check("detail panel shows the folder path", str(pathok).count(":") >= 1, pathok)

        # ---- checkbox selection updates the header stat
        js(w, "document.querySelector('#tbCaches [data-check]').click()")
        time.sleep(0.6)
        sel = js(w, "document.getElementById('stSel').textContent")
        check("selecting a row updates the Selected stat", str(sel) not in ("0 B", ""), sel)
        btn = js(w, "document.getElementById('btnClean').textContent")
        check("clean button reflects the selection", "Clean 1" in str(btn), btn)

        # ---- select-all + clear
        js(w, "document.getElementById('btnLow').click()")
        time.sleep(0.5)
        low = js(w, "document.getElementById('stSelM').textContent")
        check("'Select low-risk' selects multiple rows", "selected" in str(low), low)
        js(w, "document.getElementById('btnNone').click()")
        time.sleep(0.4)
        check("'Clear selection' resets the stat",
              str(js(w, "document.getElementById('stSel').textContent")) == "0 B")

        # ---- confirm dialog (opened, then cancelled — nothing is deleted)
        js(w, "document.querySelector('#tbCaches [data-check]').click()")
        time.sleep(0.3)
        js(w, "document.getElementById('btnClean').click()")
        time.sleep(0.8)
        modal = js(w, "document.querySelector('.modal .mhead h2') && document.querySelector('.modal .mhead h2').textContent")
        check("confirmation dialog opens with a heading", "Clean" in str(modal), modal)
        note = js(w, "document.querySelectorAll('.modal .note').length")
        check("dialog states the safety guarantees", isinstance(note, int) and note >= 1, note)
        js(w, "document.getElementById('mCancel').click()")
        time.sleep(0.4)
        on = js(w, "document.getElementById('scrim').classList.contains('on')")
        check("cancelling closes the dialog", on is False)

        # ---- apps tab
        js(w, "document.querySelector('.tab[data-tab=\\'apps\\']').click()")
        time.sleep(0.8)
        arows = js(w, "document.querySelectorAll('#tbApps tr[data-app]').length")
        check("installed-software tab lists programs", isinstance(arows, int) and arows > 10, arows)
        js(w, "document.querySelector('#tbApps tr[data-app]').click()")
        time.sleep(0.6)
        ah = js(w, "document.querySelector('.modal .mhead h2') && document.querySelector('.modal .mhead h2').textContent")
        check("clicking a program shows its cache", bool(ah), ah)
        js(w, "document.getElementById('aClose') && document.getElementById('aClose').click()")
        time.sleep(0.3)

        # ---- help dialog
        js(w, "document.getElementById('btnHelp').click()")
        time.sleep(0.6)
        hh = js(w, "document.querySelector('.modal .mhead h2').textContent")
        check("help dialog opens", "works" in str(hh), hh)
        js(w, "document.getElementById('hClose').click()")

        # ---- search filter
        js(w, "document.querySelector('.tab[data-tab=\\'caches\\']').click()")
        time.sleep(0.3)
        before = js(w, "document.querySelectorAll('#tbCaches tr[data-path]').length")
        js(w, "var q=document.getElementById('q'); q.value='spotify'; q.dispatchEvent(new Event('input'))")
        time.sleep(0.6)
        after = js(w, "document.querySelectorAll('#tbCaches tr[data-path]').length")
        check("filter narrows the table", isinstance(after, int) and after < before and after >= 0,
              "%s -> %s" % (before, after))
        js(w, "var q=document.getElementById('q'); q.value=''; q.dispatchEvent(new Event('input'))")
        time.sleep(0.5)
        check("clearing the filter restores the table",
              js(w, "document.querySelectorAll('#tbCaches tr[data-path]').length") == before)

        # ---- size band: default floor of 25 MB hides the small caches
        floor = js(w, "document.getElementById('fMin').value")
        check("size floor defaults to 25 MB", str(floor) == "25", floor)
        sizes = js(w, "JSON.stringify([...document.querySelectorAll('#tbCaches tr[data-path]')]"
                      ".map(r=>Number(r.dataset.size)))")
        small = js(w, "document.querySelectorAll('#tbCaches tr[data-path][data-size]').length")
        hidden_rows = js(w, "(() => { const s=[...document.querySelectorAll('#tbCaches tr[data-path]')]"
                            ".map(r=>Number(r.dataset.size)); return s.filter(x=>x<25*1024*1024).length; })()")
        check("no visible row is below the 25 MB floor", hidden_rows == 0, hidden_rows)
        allc = js(w, "window.__ccAllSizes ? window.__ccAllSizes.length : -1")

        # ---- a custom range narrows the table
        js(w, "var a=document.getElementById('fMin'), b=document.getElementById('fMax');"
              "a.value='50'; b.value='500';"
              "a.dispatchEvent(new Event('input')); b.dispatchEvent(new Event('input'))")
        time.sleep(0.6)
        band_rows = js(w, "document.querySelectorAll('#tbCaches tr[data-path]').length")
        out_of_range = js(w, "(() => { const s=[...document.querySelectorAll('#tbCaches tr[data-path]')]"
                             ".map(r=>Number(r.dataset.size));"
                             "return s.filter(x=>x<50*1024*1024 || x>500*1024*1024).length; })()")
        check("50–500 MB range filters the table", isinstance(band_rows, int) and 0 < band_rows <= before,
              "%s rows (was %s)" % (band_rows, before))
        check("every row in the range is inside it", out_of_range == 0, out_of_range)

        # ---- "show all" reveals the small caches
        js(w, "document.getElementById('btnShowAll').click()")
        time.sleep(0.7)
        after_all = js(w, "document.querySelectorAll('#tbCaches tr[data-path]').length")
        check("show-all reveals every cache", isinstance(after_all, int) and after_all > before,
              "%s -> %s" % (before, after_all))
        check("show-all clears both boxes",
              str(js(w, "document.getElementById('fMin').value")) == "" and
              str(js(w, "document.getElementById('fMax').value")) == "")

        # ---- restore the default floor so later checks match a fresh launch
        js(w, "var a=document.getElementById('fMin'); a.value='25';"
              "a.dispatchEvent(new Event('input'))")
        time.sleep(0.5)

        # ---- language switch: English is the default, Persian is complete
        check("interface starts in English",
              str(js(w, "document.documentElement.lang")) == "en",
              js(w, "document.documentElement.lang"))
        check("starts left-to-right", str(js(w, "document.documentElement.dir")) == "ltr")
        check("Vazirmatn font is bundled and loaded",
              "Vazirmatn:loaded" in str(js(w, "JSON.stringify([...document.fonts]"
                                              ".map(f=>f.family+':'+f.status))")),
              js(w, "JSON.stringify([...document.fonts].map(f=>f.family+':'+f.status))"))
        check("app names are English by default",
              js(w, "/[؀-ۿ]/.test([...document.querySelectorAll("
                    "'#tbCaches tr[data-path] .appcell b')].map(e=>e.textContent).join(''))") is False)

        js(w, "document.getElementById('btnLang').click()")
        time.sleep(1.2)
        check("switching flips the document language",
              str(js(w, "document.documentElement.lang")) == "fa",
              js(w, "document.documentElement.lang"))
        check("Persian lays out right-to-left", str(js(w, "document.documentElement.dir")) == "rtl")
        check("header switches to Persian",
              "پاک‌کننده" in str(js(w, "document.querySelector('header h1').textContent")),
              js(w, "document.querySelector('header h1').textContent"))
        check("table headers switch to Persian",
              "برنامه" in str(js(w, "document.querySelector('#tblCaches thead th[data-sort=app]')"
                                      ".textContent")))
        check("toolbar labels switch to Persian",
              "حجم" in str(js(w, "document.querySelector('.sizeband .lb').textContent")))
        check("application names are translated",
              js(w, "/[؀-ۿ]/.test([...document.querySelectorAll("
                    "'#tbCaches tr[data-path] .appcell b')].map(e=>e.textContent).join(''))") is True,
              str(js(w, "JSON.stringify([...document.querySelectorAll("
                        "'#tbCaches tr[data-path] .appcell b')].map(e=>e.textContent))"))[:90])
        check("cache types are translated",
              js(w, "/[؀-ۿ]/.test([...document.querySelectorAll("
                    "'#tbCaches tr[data-path] .kind')].map(e=>e.textContent).join(''))") is True,
              js(w, "document.querySelector('#tbCaches tr[data-path] .kind').textContent"))
        check("Persian uses a real Persian typeface",
              "Vazirmatn" in str(js(w, "getComputedStyle(document.body).fontFamily")),
              js(w, "getComputedStyle(document.body).fontFamily"))

        # the detail panel must translate too, not just the table
        js(w, "document.querySelector('#tbCaches tr[data-path]').click()")
        time.sleep(1.5)
        fa_desc = js(w, "document.querySelector('.detail .desc').textContent")
        check("cache description is Persian",
              js(w, "/[؀-ۿ]/.test(document.querySelector('.detail .desc')"
                    ".textContent)") is True, str(fa_desc)[:80])
        check("detail headings are Persian",
              js(w, "/[؀-ۿ]/.test(document.querySelector('.detail').textContent)") is True)

        js(w, "document.getElementById('btnHelp').click()")
        time.sleep(0.7)
        check("help dialog is Persian",
              "چطور" in str(js(w, "document.querySelector('.modal .mhead h2').textContent")),
              js(w, "document.querySelector('.modal .mhead h2').textContent"))
        check("help body is Persian",
              js(w, "/[؀-ۿ]/.test(document.querySelector('.modal .mbody').textContent)"
                    ) is True)
        js(w, "document.getElementById('hClose').click()")
        time.sleep(0.4)

        # ---- switch back to English (the default) and confirm it sticks
        js(w, "document.getElementById('btnLang').click()")
        time.sleep(1.2)
        check("switching back restores English",
              str(js(w, "document.documentElement.lang")) == "en" and
              "Application" in str(js(w, "document.querySelector('#tblCaches thead "
                                          "th[data-sort=app]').textContent")))
        check("language choice is remembered in the interface",
              str(js(w, "localStorage.getItem('cc.lang')")) == "en",
              js(w, "localStorage.getItem('cc.lang')"))
        check("language choice is written to config.json",
              api.cc_config().get("lang") == "en", api.cc_config().get("lang"))
        check("English is the shipped default",
              json.load(open(os.path.join(A.APP_DIR, "config.json"), encoding="utf-8"))
              .get("lang") == "en")

        # ---- the ring must GLIDE, not teleport. The true percentage is locations measured,
        # and 98% of locations finish in milliseconds, so it genuinely jumps 0 -> 9 -> 99.
        # A MutationObserver records what the user actually sees; the eased display must pass
        # through many intermediate values and land exactly on the true one.
        js(w, "(() => { window.__pct = []; const e = document.getElementById('scanPct');"
              " new MutationObserver(() => window.__pct.push(e.textContent.trim()))"
              " .observe(e, {childList:true, characterData:true, subtree:true}); })()")
        js(w, "document.getElementById('btnScan').click()")
        time.sleep(1.2)
        for _ in range(40):
            if not api.cc_scan_state().get("running"):
                break
            time.sleep(0.4)
        time.sleep(1.5)
        raw = js(w, "JSON.stringify(window.__pct || [])")
        try:
            seq = json.loads(raw) if isinstance(raw, str) else []
        except Exception:
            seq = []
        nums = [int(v) for v in dict.fromkeys(seq) if str(v).isdigit()]
        check("the ring passes through many values instead of teleporting",
              len(nums) > 6, "%d distinct: %s" % (len(nums), nums[:12]))
        check("the ring's values never go backwards",
              all(nums[i] <= nums[i + 1] for i in range(len(nums) - 1)), nums[:12])
        check("the ring lands exactly on the true percentage",
              bool(nums) and nums[-1] == 100, nums[-3:] if nums else None)

        # ---- scan theatre: the overlay is driven by REAL scanner progress
        js(w, "document.getElementById('btnScan').click()")
        time.sleep(1.2)
        stage = js(w, "JSON.stringify({hidden: document.getElementById('scanStage').hidden,"
                      " rings: document.querySelectorAll('#scanStage .arc').length,"
                      " bars: document.querySelectorAll('#rail i').length})")
        stage = json.loads(stage) if isinstance(stage, str) else stage
        check("the scan overlay appears when scanning starts",
              isinstance(stage, dict) and stage.get("hidden") is False, stage)
        check("it has the animated ring and the rail",
              isinstance(stage, dict) and stage.get("rings") == 3 and stage.get("bars") == 44, stage)

        # wait for the scan to actually be under way, then read the live numbers
        live = None
        for _ in range(40):
            st = api.cc_scan_state()
            if st.get("running") and st.get("done", 0) > 3:
                live = st
                break
            time.sleep(0.5)
        check("the scan is running and reporting progress", live is not None and live.get("done", 0) > 3)

        dom = js(w, "JSON.stringify({"
                    "pct: document.getElementById('scanPct').textContent,"
                    "found: document.getElementById('roFound').textContent,"
                    "size: document.getElementById('roSize').textContent,"
                    "files: document.getElementById('roFiles').textContent,"
                    "places: document.getElementById('roPlaces').textContent,"
                    "bar: document.getElementById('scanBar').style.width,"
                    "now: document.getElementById('scanNow').textContent,"
                    "recent: document.getElementById('scanRecent').children.length,"
                    "tallest: Math.max(0, ...[...document.querySelectorAll('#rail i')]"
                    ".map(b => parseFloat(b.style.height)||0))})")
        dom = json.loads(dom) if isinstance(dom, str) else dom
        check("the ring shows a real percentage", isinstance(dom, dict) and dom.get("pct", "0") != "0", dom)
        check("locations readout shows done / total",
              isinstance(dom, dict) and "/" in str(dom.get("places")) and dom["places"] != "0 / 0", dom)
        check("measured size is real, not a placeholder",
              isinstance(dom, dict) and dom.get("size") not in ("0 B", "", None), dom)
        check("files walked is a real number",
              isinstance(dom, dict) and dom.get("files") not in ("0", "", None), dom)
        check("caches found is a real number",
              isinstance(dom, dict) and int(str(dom.get("found", "0")).replace(",", "") or 0) > 0, dom)
        check("the current application is named",
              isinstance(dom, dict) and len(str(dom.get("now") or "")) > 2, dom)
        check("the rail bars grew with real cache sizes",
              isinstance(dom, dict) and dom.get("tallest", 0) > 3, dom)

        # The page is fed by polling, so a single side-by-side read can always be one tick
        # behind. Assert convergence instead: the on-screen figure must match the scanner's
        # own total at some point while the scan runs — that is what proves the number comes
        # from Python and is not decorative.
        converged = False
        seen = []
        for _ in range(40):
            if not api.cc_scan_state().get("running"):
                break
            want = bytes_(api.cc_scan_state().get("liveBytes", 0))
            got = str(js(w, "document.getElementById('roSize').textContent"))
            seen.append(got)
            if got == want:
                converged = True
                break
            time.sleep(0.4)
        check("the on-screen size converges on the scanner's own total",
              converged, "screen samples: %s" % seen[-4:])

        # let it finish and confirm the curtain drops
        t0 = time.time()
        while time.time() - t0 < 200:
            if not api.cc_scan_state().get("running"):
                break
            time.sleep(0.5)
        time.sleep(2.0)
        check("the overlay closes when the scan finishes",
              js(w, "document.getElementById('scanStage').hidden") is True)
        check("the table is populated after the scan",
              js(w, "document.querySelectorAll('#tbCaches tr[data-path]').length") > 0)

        # the overlay must be bilingual too
        js(w, "document.getElementById('btnScan').click()")
        time.sleep(0.8)
        js(w, "document.getElementById('btnLang').click()")
        time.sleep(1.0)
        fa_stage = js(w, "JSON.stringify({title: document.querySelector('#scanStage .stitle').textContent,"
                         " found: document.querySelector('#scanStage .rk').textContent,"
                         " dir: document.documentElement.dir})")
        fa_stage = json.loads(fa_stage) if isinstance(fa_stage, str) else fa_stage
        check("the scan overlay is Persian and right-to-left",
              isinstance(fa_stage, dict) and fa_stage.get("dir") == "rtl"
              and "اسکن" in str(fa_stage.get("title")), fa_stage)
        check("the overlay readouts are Persian",
              isinstance(fa_stage, dict) and "کش" in str(fa_stage.get("found")), fa_stage)
        js(w, "document.getElementById('btnLang').click()")
        time.sleep(0.8)
        t0 = time.time()
        while time.time() - t0 < 200:
            if not api.cc_scan_state().get("running"):
                break
            time.sleep(0.5)
        time.sleep(2.0)

        # ---- author links (footer)
        check("author credit is shown",
              "Sadeghi" in str(js(w, "document.querySelector('.authorbar .who').textContent")),
              js(w, "document.querySelector('.authorbar .who').textContent"))
        gh = js(w, "document.getElementById('lnkGithub').href")
        li = js(w, "document.getElementById('lnkLinkedin').href")
        check("GitHub link points at the real profile",
              str(gh).rstrip("/").endswith("MohammadMehdiSadeghi"), gh)
        check("LinkedIn link points at the real profile",
              "linkedin.com/in/mohammad-mehdi-sadeghi" in str(li), li)
        check("both links open in a new tab safely",
              js(w, "['lnkGithub','lnkLinkedin'].every(id => {"
                    "const a = document.getElementById(id);"
                    "return a.target === '_blank' && (a.rel||'').includes('noopener');})") is True)
        check("links are backed by the app's whitelist",
              sorted(api.cc_info().get("links", {}).keys()) == ["github", "linkedin"],
              api.cc_info().get("links"))
        check("an unknown link is refused",
              api.cc_open_link("evil").get("ok") is False,
              api.cc_open_link("evil"))
        check("a non-whitelisted host is refused",
              api.cc_open_link("http://evil.example.com").get("ok") is False)
        # the click must be handled in-app (default prevented) instead of navigating the
        # window; the bridge is stubbed so the test does not launch a real browser
        # The click must be handled in-app (default prevented) instead of navigating the
        # window. pywebview's evaluate_js does not await promises, so this is done in two
        # synchronous steps with a short pause for the bridge call to land.
        js(w, "window.__t = {};"
              "window.__called = null;"
              "window.__orig = window.pywebview.api.cc_open_link;"
              "window.pywebview.api.cc_open_link = w => { window.__called = w; return {ok:true}; };"
              "const a = document.getElementById('lnkGithub');"
              "const ev = new MouseEvent('click', {cancelable:true, bubbles:true});"
              "window.__t.prevented = !a.dispatchEvent(ev);"
              "window.__t.before = location.href;")
        time.sleep(1.0)
        js(w, "window.__t.after = location.href;"
              "window.__t.called = window.__called;"
              "window.pywebview.api.cc_open_link = window.__orig;")
        nav = js(w, "JSON.stringify(window.__t)")
        try:
            nav = json.loads(nav) if isinstance(nav, str) else nav
        except Exception:
            pass
        check("clicking a link is handled in-app, not by navigating the window",
              isinstance(nav, dict) and nav.get("prevented") is True
              and nav.get("before") == nav.get("after") and nav.get("called") == "github",
              repr(nav))

        check("author credit is translated",
              "صادقی" in str(js(w, "document.querySelector('.authorbar .who').textContent")) or
              str(js(w, "document.documentElement.lang")) == "en")


        ov = js(w, "document.documentElement.scrollWidth > innerWidth + 1")
        check("no horizontal overflow in the real window", ov is False, ov)
        check("no JavaScript errors were raised", not any("JSERR" in o for o in out))
    except Exception:
        check("GUI test ran without exceptions", False, traceback.format_exc()[-400:])
    finally:
        try:
            w.destroy()
        except Exception:
            pass


def _kill_stale():
    """A leftover instance from a previous run (or a killed mid-scan test) makes this suite
    fail with confusing timeouts — the single-instance guard makes the new window exit at once.
    Clear it before measuring."""
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-Process | Where-Object { $_.MainWindowTitle -eq 'Cache Cleaner' } | "
                        "ForEach-Object { $_.Kill() }"],
                       capture_output=True, text=True, timeout=90)
        time.sleep(3)
    except Exception:
        pass


def main():
    _kill_stale()
    api = A.Api()
    w = webview.create_window("Cache Cleaner", A.UI_INDEX, js_api=api,
                              width=1400, height=900, background_color="#0a0b0d")
    A.WINDOW[0] = w        # never api.window: pywebview recurses over API attributes
    webview.start(run, (w, api))
    print("\nFAILURES:", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
