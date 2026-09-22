# Cache Cleaner

A Windows cache cleaner with a real GUI. It finds what every application keeps in its
cache, shows how much space each one uses, and deletes the contents — only after you
confirm it. Everything is read-only until you press the delete button.

Interface: English, with a Persian (right-to-left) mode. Dark and keyboard-friendly.

**To run the app, open `CacheCleaner.exe`** — the file with the sparkles icon in the
project root. Double-click it; the window opens by itself.

**Requires:** Windows 10/11 · Python 3.10+ · `pywebview` · WebView2

## Quick start

**Open `CacheCleaner.exe`.** It finds a Python that has `pywebview` installed and
starts the app. (`CacheCleaner.bat` is the same thing for the command line.)

First time only, if pywebview is missing:

```bat
python -m pip install pywebview
```

Desktop shortcut: `python make_shortcut.py`

## What it does

- **Scans** ~490 cache locations in seconds and reports the size of each one, plus free
  space on every drive.
- **Lists installed software** so you can see which program owns each cache.
- **Explains the contents**: click a row to see the biggest files and subfolders inside
  that cache before you remove anything.
- **Deletes safely**: only the *contents* of a cache folder are emptied — the folder
  stays, so applications keep working. Every deletion needs confirmation, and running
  apps are flagged.
- **Search, filter, sort** — including a size band (default: 25 MB and up) and a
  one-click "show all". Choices persist between launches.
- **Command line** for scripts and scheduled tasks: `report.py`.

## What is never touched

Enforced in code and unit-tested (`tests/test_guard.py`). Never deleted:

- Bookmarks, saved passwords, cookies, sessions, browser profiles
- Telegram/Discord account data, chats, messages
- Documents, Desktop, Downloads, Pictures, Videos, Music
- `.ssh`, keys, cloud-sync folders, OneDrive
- Installation files, and the cache folders themselves (only their contents)

## Language

English by default. The button in the header switches to Persian (full RTL, including
tables and dialogs) and the choice is saved to `config.json`.

## Command line

```bat
python report.py                    full report, largest first
python report.py --top 30           top 30 only
python report.py --apps             installed software
python report.py --json out.json    JSON output

python cleaner.py --list                    what could be cleaned
python cleaner.py --app spotify --dry-run   what would be deleted
python cleaner.py --app spotify --yes       delete (asks nothing)
python cleaner.py --all-low --yes           delete every low-risk cache
```

`report.py` never deletes anything. `cleaner.py` is the only module that does, and it
runs the same guard as the GUI.

## Tests

```bat
python tests/test_guard.py      rem protected paths can never be deleted
python tests/test_clean.py      rem deletion engine + dry-run
python tests/test_api.py        rem the Python API the GUI calls
python tests/test_gui.py        rem the real window
python tests/test_i18n.py       rem Persian translations complete
python tests/test_shutdown.py   rem no leftover process, no duplicate instance
python tests/test_taskbar.py    rem the window/taskbar icon is ours
```

Each prints `FAILURES: 0` and exits 0. The last three open the real window, so they
take about a minute together.

## License

Released under the **MIT License** — full text in [`LICENSE`](LICENSE).

Free to use, copy, modify, publish and distribute, as long as the copyright notice and
the license text stay with the software. Provided "as is", without warranty.
