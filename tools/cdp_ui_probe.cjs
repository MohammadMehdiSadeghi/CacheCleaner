// cdp_ui_probe.cjs — read the real DOM of the UI through headless Edge over CDP.
// Usage: node cdp_ui_probe.cjs <file-url> [extra-js]
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const url = process.argv[2];
const extra = process.argv[3] || "";
const port = 9333 + Math.floor(Math.random() * 400);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "ccprobe-"));

const child = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--remote-debugging-port=" + port, "--user-data-dir=" + profile,
  "--window-size=1500,950", "--disk-cache-size=1", url,
], { stdio: "ignore" });

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  let list = null;
  for (let i = 0; i < 60; i++) {
    await sleep(400);
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/list`);
      const j = await r.json();
      const page = j.find(t => t.type === "page" && t.webSocketDebuggerUrl);
      if (page) { list = page; break; }
    } catch (e) { /* not up yet */ }
  }
  if (!list) { console.log("NO_TARGET"); child.kill(); process.exit(1); }

  const ws = new WebSocket(list.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const send = (method, params = {}) => new Promise((res) => {
    const myId = ++id;
    pending.set(myId, res);
    ws.send(JSON.stringify({ id: myId, method, params }));
  });
  const logs = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
    else if (m.method === "Runtime.consoleAPICalled") {
      logs.push(m.params.type + ": " + m.params.args.map(a => a.value ?? a.description ?? "").join(" "));
    } else if (m.method === "Runtime.exceptionThrown") {
      logs.push("EXCEPTION: " + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    }
  };
  await new Promise(r => ws.onopen = r);
  await send("Runtime.enable");
  await send("Page.enable");
  await sleep(2200);

  const expr = `(() => {
    const o = {};
    const box = s => { const e = document.querySelector(s); if (!e) return null;
      const r = e.getBoundingClientRect(); return {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.left), y: Math.round(r.top)}; };
    o.viewport = {w: innerWidth, h: innerHeight};
    o.scroll = {sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight};
    o.header = box('header.top'); o.stats = box('.stats'); o.toolbar = box('.toolbar');
    o.split = box('.split'); o.detail = box('.detail'); o.list = box('.list');
    o.statusbar = box('.statusbar'); o.tablewrap = box('.tablewrap');
    o.rows = document.querySelectorAll('#tbCaches tr[data-path]').length;
    o.fontBody = getComputedStyle(document.body).fontFamily;
    o.fontMono = (() => { const e = document.querySelector('.appcell span'); return e ? getComputedStyle(e).fontFamily : null; })();
    o.fontLoaded = [...document.fonts].map(f => f.family + ':' + f.status);
    o.appNames = [...document.querySelectorAll('#tbCaches tr[data-path] .appcell b')].slice(0,6).map(e => e.textContent);
    o.sizes = [...document.querySelectorAll('#tbCaches .size .n')].slice(0,6).map(e => e.textContent);
    o.hOverflow = document.documentElement.scrollWidth > innerWidth + 1;
    o.over = [];
    document.querySelectorAll('.split *').forEach(e => {
      if (e.scrollWidth - e.clientWidth > 4 && getComputedStyle(e).overflow === 'visible')
        o.over.push((e.className || e.tagName) + ':' + e.scrollWidth + '/' + e.clientWidth);
    });
    o.over = o.over.slice(0, 6);
    o.tabsVisible = getComputedStyle(document.getElementById('tblCaches')).display;
    o.status = document.getElementById('status').textContent;
    ${extra}
    return o;
  })()`;
  const res = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  console.log(JSON.stringify(res.result?.value ?? res, null, 1));
  console.log("CONSOLE:", logs.length ? logs.join(" | ").slice(0, 1500) : "(clean)");
  ws.close();
  child.kill();
  setTimeout(() => process.exit(0), 400);
}
main().catch(e => { console.log("ERR", e.message); child.kill(); process.exit(1); });
