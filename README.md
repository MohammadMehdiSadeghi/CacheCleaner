# Cache Cleaner

A Windows cache cleaner with a real GUI. It finds what every application keeps in its
cache, shows how much space each one uses, and deletes the contents — only after you
confirm it. Everything is read-only until you press the delete button.

Interface: English, with a Persian (right-to-left) mode. Dark and keyboard-friendly.

**To run the app, open `CacheCleaner.exe`** — the file in the
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

* **Scans** ~490 cache locations in seconds and reports the size of each one, plus free
  space on every drive.
* **Lists installed software** so you can see which program owns each cache.
* **Explains the contents**: click a row to see the biggest files and subfolders inside
  that cache before you remove anything.
* **Deletes safely**: only the *contents* of a cache folder are emptied — the folder
  stays, so applications keep working. Every deletion needs confirmation, and running
  apps are flagged.
* **Search, filter, sort** — including a size band (default: 25 MB and up) and a
  one-click "show all". Choices persist between launches.
* **Command line** for scripts and scheduled tasks: `report.py`.

## What is never touched

Enforced in code and unit-tested (`tests/test_guard.py`). Never deleted:

* Bookmarks, saved passwords, cookies, sessions, browser profiles
* Telegram/Discord account data, chats, messages
* Documents, Desktop, Downloads, Pictures, Videos, Music
* `.ssh`, keys, cloud-sync folders, OneDrive
* Installation files, and the cache folders themselves (only their contents)

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

## Using the app

The first scan starts by itself — press **Rescan** in the header to run it again. Each
part of the window:

* **Header** — free space per drive, admin chip, language button (FA/EN), **Help**, **Rescan**
* **Stats** — total cache found, current selection, free space, last cleaned
* **Toolbar** — tabs (**Caches** / **Installed software**), search box, filters, Size
  band in MB, **Select low-risk**, **Clean selected**
* **Table** — one row per cache: checkbox, application, path, size, risk
* **Detail panel** — the selected cache explained: description, biggest files inside,
  folder path, open-in-Explorer and delete buttons
* **Status bar** — progress messages, rows shown, "show all" chip for small caches
* **Footer** — author credit with the GitHub and LinkedIn links

Tick a row and press **Clean selected** — a confirmation dialog appears first; nothing
is ever deleted without it.

## License

Released under the **MIT License** — full text in [`LICENSE`](LICENSE).

Free to use, copy, modify, publish and distribute, as long as the copyright notice and
the license text stay with the software. Provided "as is", without warranty.

------------------------------------------------------

یک پاک‌کننده کش ویندوز با رابط گرافیکی واقعی. این برنامه محل نگهداری کش برنامه‌های مختلف را پیدا می‌کند، حجم استفاده‌شده توسط هرکدام را نمایش می‌دهد و فقط پس از تأیید شما محتویات کش را حذف می‌کند. تا زمانی که دکمه حذف را فشار ندهید، هیچ چیزی تغییر نمی‌کند و تمام عملیات در حالت فقط‌خواندنی انجام می‌شود.

رابط کاربری به‌صورت پیش‌فرض انگلیسی است و از حالت فارسی **راست‌به‌چپ (RTL)** نیز پشتیبانی می‌کند. رابط برنامه تاریک و مناسب استفاده با کیبورد طراحی شده است.

**برای اجرای برنامه، فایل `CacheCleaner.exe` را باز کنید** — این فایل در ریشه پروژه قرار دارد. کافی است روی آن دوبار کلیک کنید تا برنامه اجرا شود.

**نیازمندی‌ها:** Windows 10/11 · Python 3.10+ · `pywebview` · WebView2

## شروع سریع

**فایل `CacheCleaner.exe` را اجرا کنید.** برنامه به‌صورت خودکار یک Python را که `pywebview` روی آن نصب شده پیدا کرده و برنامه را اجرا می‌کند. (`CacheCleaner.bat` نیز همین کار را از طریق خط فرمان انجام می‌دهد.)

اگر `pywebview` نصب نباشد، فقط برای اولین اجرا:

```bat
python -m pip install pywebview
```

ساخت میانبر روی دسکتاپ:

```bat
python make_shortcut.py
```

## برنامه چه کاری انجام می‌دهد؟

* **اسکن کش‌ها** — حدود ۴۹۰ محل احتمالی کش را در چند ثانیه بررسی می‌کند و حجم هرکدام را نمایش می‌دهد. فضای خالی هر درایو نیز نمایش داده می‌شود.
* **نمایش نرم‌افزارهای نصب‌شده** — مشخص می‌کند هر کش متعلق به کدام برنامه است.
* **بررسی محتویات کش** — با کلیک روی هر ردیف می‌توانید قبل از حذف، بزرگ‌ترین فایل‌ها و پوشه‌های داخل آن کش را مشاهده کنید.
* **حذف ایمن** — فقط *محتویات* پوشه کش حذف می‌شوند و خود پوشه باقی می‌ماند تا برنامه‌ها همچنان بدون مشکل کار کنند. هر عملیات حذف نیاز به تأیید دارد و برنامه‌های در حال اجرا نیز مشخص می‌شوند.
* **جستجو، فیلتر و مرتب‌سازی** — شامل فیلتر بازه حجم، که به‌صورت پیش‌فرض کش‌های ۲۵ مگابایت و بیشتر را نمایش می‌دهد، و گزینه یک‌کلیکی **نمایش همه**. تنظیمات انتخاب‌شده بین اجراهای مختلف برنامه ذخیره می‌شوند.
* **خط فرمان** — مناسب برای اسکریپت‌ها و وظایف زمان‌بندی‌شده با استفاده از `report.py`.

## چه چیزهایی هرگز دستکاری نمی‌شوند؟

این محدودیت‌ها در کد برنامه اعمال شده‌اند و با تست‌های واحد نیز بررسی می‌شوند (`tests/test_guard.py`).

موارد زیر **هرگز حذف نمی‌شوند**:

* بوکمارک‌ها، رمزهای عبور ذخیره‌شده، کوکی‌ها، نشست‌ها و پروفایل مرورگرها
* اطلاعات حساب Telegram و Discord، چت‌ها و پیام‌ها
* پوشه‌های Documents، Desktop، Downloads، Pictures، Videos و Music
* `.ssh`، کلیدهای امنیتی، پوشه‌های همگام‌سازی ابری و OneDrive
* فایل‌های نصب برنامه‌ها
* خود پوشه‌های کش — فقط محتویات آن‌ها قابل حذف است

## زبان

زبان پیش‌فرض برنامه انگلیسی است.

دکمه موجود در هدر برنامه امکان تغییر زبان به فارسی را فراهم می‌کند. حالت فارسی به‌صورت کامل از **راست‌به‌چپ (RTL)** پشتیبانی می‌کند؛ از جمله جدول‌ها و پنجره‌های گفت‌وگو.

انتخاب زبان در `config.json` ذخیره می‌شود و در اجرای بعدی نیز حفظ خواهد شد.

## خط فرمان

```bat
python report.py                    گزارش کامل، از بزرگ‌ترین موارد به کوچک‌ترین
python report.py --top 30           فقط ۳۰ مورد اول
python report.py --apps             نمایش نرم‌افزارهای نصب‌شده
python report.py --json out.json    خروجی JSON

python cleaner.py --list                    نمایش موارد قابل پاک‌سازی
python cleaner.py --app spotify --dry-run   نمایش مواردی که حذف خواهند شد
python cleaner.py --app spotify --yes       حذف بدون درخواست تأیید
python cleaner.py --all-low --yes           حذف تمام کش‌های کم‌خطر
```

`report.py` هیچ فایلی را حذف نمی‌کند.

تنها ماژولی که عملیات حذف را انجام می‌دهد `cleaner.py` است و این ماژول نیز از همان سیستم محافظتی استفاده می‌کند که در رابط گرافیکی برنامه به کار رفته است.

## تست‌ها

```bat
python tests/test_guard.py      rem مسیرهای محافظت‌شده هرگز نباید حذف شوند
python tests/test_clean.py      rem موتور حذف + حالت dry-run
python tests/test_api.py        rem API پایتون که رابط گرافیکی استفاده می‌کند
python tests/test_gui.py        rem پنجره واقعی برنامه
python tests/test_i18n.py       rem کامل بودن ترجمه‌های فارسی
python tests/test_shutdown.py   rem نبود پردازش اضافی و جلوگیری از اجرای هم‌زمان
python tests/test_taskbar.py    rem بررسی آیکون پنجره و نوار وظیفه
```

هر تست در صورت موفقیت `FAILURES: 0` چاپ کرده و با کد خروجی `0` پایان می‌یابد.

سه تست آخر پنجره واقعی برنامه را باز می‌کنند؛ بنابراین اجرای مجموع آن‌ها حدود یک دقیقه زمان می‌برد.

## استفاده از برنامه

اولین اسکن به‌صورت خودکار شروع می‌شود. برای اجرای مجدد اسکن، روی **Rescan** در هدر کلیک کنید.

بخش‌های مختلف پنجره:

* **Header** — فضای خالی هر درایو، وضعیت دسترسی Administrator، دکمه تغییر زبان (FA/EN)، **Help** و **Rescan**
* **Stats** — مجموع کش‌های پیدا‌شده، موارد انتخاب‌شده، فضای خالی و آخرین پاک‌سازی انجام‌شده
* **Toolbar** — تب‌های **Caches / Installed software**، کادر جستجو، فیلترها، محدوده حجم بر اساس MB، گزینه **Select low-risk** و دکمه **Clean selected**
* **Table** — یک ردیف برای هر کش شامل چک‌باکس، نام برنامه، مسیر، حجم و سطح ریسک
* **Detail panel** — نمایش جزئیات کش انتخاب‌شده شامل توضیحات، بزرگ‌ترین فایل‌های موجود، مسیر پوشه، دکمه باز کردن در Explorer و دکمه حذف
* **Status bar** — پیام‌های مربوط به وضعیت و پیشرفت عملیات، تعداد ردیف‌های نمایش‌داده‌شده و گزینه **show all** برای کش‌های کوچک
* **Footer** — اطلاعات سازنده به همراه لینک‌های GitHub و LinkedIn

یک ردیف را انتخاب کنید و روی **Clean selected** کلیک کنید. ابتدا پنجره تأیید نمایش داده می‌شود و **هیچ فایلی بدون تأیید شما حذف نخواهد شد.**

## مجوز

این پروژه تحت **مجوز MIT** منتشر شده است. متن کامل مجوز در فایل [`LICENSE`](LICENSE) قرار دارد.

استفاده، کپی، تغییر، انتشار و توزیع این نرم‌افزار آزاد است؛ مشروط بر اینکه اطلاعیه کپی‌رایت و متن مجوز همراه نرم‌افزار باقی بماند.

این نرم‌افزار **«همان‌طور که هست» (AS IS)** ارائه می‌شود و هیچ ضمانتی در قبال آن وجود ندارد.
