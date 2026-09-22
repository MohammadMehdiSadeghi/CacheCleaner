# -*- coding: utf-8 -*-
"""i18n_rules.py — Persian strings for the cache rules.

Keyed by the English `app` value in cc_rules.RULES, so a rule can never drift out of
sync silently: tests/test_i18n.py asserts every rule has an entry here, and that every entry
here matches a real rule.

Brand names stay in their official Latin spelling (Spotify, Discord, npm, ...) — that is
how Persian software UIs normally present them. Everything descriptive is translated.
"""

FA = {
    # ---------- browsers ----------
    "Google Chrome": dict(
        app="گوگل کروم", kind="کش مرورگر",
        desc="فایل‌های صفحه‌های دیده‌شده (HTML/CSS/JS/تصویر)، جاوااسکریپت کامپایل‌شده، "
             "شیدر گرافیک و بافرهای رسانه‌ای. بعد از پاک کردن، سایت‌ها بار اول کمی کندتر "
             "باز می‌شوند. بوک‌مارک، رمز و کوکی جای دیگری ذخیره‌اند و دست‌نخورده می‌مانند."),
    "Microsoft Edge": dict(
        app="مایکروسافت اج", kind="کش مرورگر",
        desc="فایل‌های صفحه‌های دیده‌شده، جاوااسکریپت کامپایل‌شده و شیدرهای گرافیک اج. "
             "علاقه‌مندی‌ها، رمزها و کوکی‌ها داخل این پوشه‌ها نیستند."),
    "Brave": dict(
        app="Brave", kind="کش مرورگر",
        desc="فایل‌های صفحه‌های دیده‌شده و کش شیدر گرافیک Brave."),
    "Opera / Opera GX": dict(
        app="Opera / Opera GX", kind="کش مرورگر",
        desc="فایل‌های صفحه‌های دیده‌شده و جاوااسکریپت کامپایل‌شده Opera و Opera GX."),
    "Vivaldi": dict(
        app="Vivaldi", kind="کش مرورگر",
        desc="فایل‌های صفحه‌های دیده‌شده Vivaldi."),
    "Mozilla Firefox": dict(
        app="موزیلا فایرفاکس", kind="کش",
        desc="کش HTTP (cache2)، کش راه‌اندازی، کش شیدر و کش تصویر بندانگشتی. "
             "پروفایل، بوک‌مارک‌ها و اطلاعات ورود بیرون این پوشه‌ها هستند."),

    # ---------- messaging ----------
    "Telegram Desktop": dict(
        app="تلگرام دسکتاپ", kind="کش رسانه",
        desc="عکس‌ها و ویدیوهای کش‌شدهٔ چت‌ها به‌همراه ست ایموجی. پیام‌ها، حساب کاربری و "
             "فایل‌های دانلودشده (tdata و media) دست نمی‌خورند."),
    "Discord": dict(
        app="Discord", kind="کش الکترون",
        desc="فایل‌های صفحه‌های دیده‌شده، جاوااسکریپت کامپایل‌شده و شیدرهای گرافیک کلاینت Discord."),
    "Slack": dict(
        app="Slack", kind="کش الکترون",
        desc="فایل‌های صفحه‌های دیده‌شده و فایل‌های موقت کلاینت Slack."),
    "WhatsApp Desktop": dict(
        app="واتس‌اپ دسکتاپ", kind="کش اپ استور",
        desc="کش داخلی نسخهٔ مایکروسافت استور واتس‌اپ. چت‌هایت در LocalState هستند و "
             "دست نمی‌خورند."),
    "Microsoft Teams": dict(
        app="مایکروسافت تیمز", kind="کش الکترون",
        desc="فایل‌های صفحه‌های دیده‌شده، جاوااسکریپت کامپایل‌شده و لاگ‌های Teams قدیمی و جدید."),

    # ---------- media ----------
    "Spotify": dict(
        app="Spotify", kind="کش صدای آفلاین",
        desc="آهنگ‌های دانلودشده برای پخش آفلاین به‌همراه کاور آلبوم‌های کش‌شده. "
             "قطعه‌ها وقتی دوباره پخششان کنی از نو دانلود می‌شوند."),
    "VLC": dict(
        app="VLC", kind="کش افزونه",
        desc="کش افزونه‌ها و فایل‌های موقت ساخته‌شده توسط VLC."),
    "Adobe Premiere / After Effects": dict(
        app="ادوبی پریمیر / افترافکت", kind="کش رسانه",
        desc="کش رسانه و فایل‌های Peak پروژه‌های ادوبی. در صورت نیاز از نو ساخته می‌شوند، "
             "پس باز کردن یک پروژهٔ قدیمی بعد از پاک کردن کمی کندتر است."),
    "Adobe Camera Raw": dict(
        app="ادوبی کمرا راو", kind="کش مدل هوش مصنوعی",
        desc="مدل‌های هوش مصنوعی ادوبی برای کاهش نویز، انتخاب سوژه و حذف بازتاب. "
             "هر قابلیت، مدلش را دفعهٔ بعد که استفاده کنی از نو دانلود می‌کند."),

    # ---------- developer ----------
    "Visual Studio Code": dict(
        app="Visual Studio Code", kind="کش ادیتور",
        desc="کش جاوااسکریپت کامپایل‌شده، کش گرافیک و لاگ‌ها. افزونه‌ها و تنظیمات داخل این "
             "پوشه‌ها نیستند. شامل نصب‌کننده‌های کش‌شدهٔ افزونه (VSIX) هم می‌شود."),
    "Cursor": dict(
        app="Cursor", kind="کش ادیتور",
        desc="کش جاوااسکریپت کامپایل‌شده، کش گرافیک و لاگ‌های ادیتور Cursor."),
    "JetBrains IDEs": dict(
        app="محیط‌های JetBrains", kind="کش ایندکس",
        desc="ایندکس پروژه‌ها، کش‌ها، لاگ‌ها و فایل‌های موقت محیط‌های مبتنی بر IntelliJ. "
             "پروژه‌ها دفعهٔ بعد که بازشان کنی از نو ایندکس می‌شوند."),
    "npm": dict(
        app="npm", kind="کش پکیج",
        desc="پکیج‌های دانلودشدهٔ npm. دفعهٔ بعد `npm install` فقط چیزهایی که لازم دارد را "
             "از نو دانلود می‌کند."),
    "pip (Python)": dict(
        app="pip (پایتون)", kind="کش پکیج",
        desc="فایل‌های wheel و آرشیوهای سورس دانلودشده توسط pip."),
    "Yarn": dict(
        app="Yarn", kind="کش پکیج",
        desc="کش پکیج‌های Yarn (کلاسیک و Berry)."),
    "pnpm": dict(
        app="pnpm", kind="مخزن پکیج",
        desc="مخزن محتوا-محور pnpm. پاک کردنش بی‌خطر است، ولی هر پروژه باید پکیج‌هایش را "
             "از نو لینک یا دانلود کند."),
    "uv (Python)": dict(
        app="uv (پایتون)", kind="کش پکیج",
        desc="فایل‌های wheel و خروجی‌های ساخت که uv کش کرده است."),
    "NuGet / .NET": dict(
        app="NuGet / .NET", kind="کش پکیج",
        desc="پکیج‌های NuGet و فایل‌های موقت. بیلد بعدی هرچه لازم دارد را از نو دانلود می‌کند."),
    "Gradle / Maven": dict(
        app="Gradle / Maven", kind="کش بیلد",
        desc="کش وابستگی‌ها و بیلد جاوا. بیلد بعدی آن‌ها را از نو دانلود می‌کند."),
    "Docker Desktop": dict(
        app="Docker Desktop", kind="لاگ کانتینر",
        desc="لاگ‌های daemon و کش دانلود ایمیج‌ها. ایمیج‌ها و volumeهایت دست نمی‌خورند."),

    # ---------- Windows ----------
    "Windows — User temp": dict(
        app="ویندوز — فایل‌های موقت کاربر", kind="فایل موقت",
        desc="فایل‌های موقتی که برنامه‌ها می‌سازند. فایل‌هایی که هنوز در استفاده‌اند قفل‌اند "
             "و خودکار رد می‌شوند."),
    "Windows — System temp": dict(
        app="ویندوز — فایل‌های موقت سیستم", kind="فایل موقت",
        desc="فایل‌های موقت کل سیستم. به دسترسی ادمین نیاز دارد."),
    "Windows — Crash dumps": dict(
        app="ویندوز — دامپ‌های کرش", kind="دامپ کرش",
        desc="دامپ‌های حافظه که وقتی برنامه‌ای کرش می‌کند نوشته می‌شوند."),
    "Windows — Error reports": dict(
        app="ویندوز — گزارش خطا", kind="گزارش خطا",
        desc="صف‌های گزارش خطای ویندوز که منتظر ارسال به مایکروسافت هستند."),
    "Windows — Internet & Web cache": dict(
        app="ویندوز — کش اینترنت و وب", kind="کش سیستم",
        desc="کش‌های WinINet/WebView، کش آیکون‌ها و کش تصویر ریموت دسکتاپ."),
    "Windows — Icon & thumbnail cache": dict(
        app="ویندوز — کش آیکون و بندانگشتی", kind="کش آیکون",
        desc="دیتابیس آیکون و تصویر بندانگشتی اکسپلورر. ویندوز تا وقتی اکسپلورر باز است "
             "قفلشان می‌کند، پس فایل‌های قفل‌شده رد می‌شوند مگر اکسپلورر اول بسته شود."),
    "Windows — DirectX shader cache": dict(
        app="ویندوز — کش شیدر DirectX", kind="کش گرافیک",
        desc="شیدرهای کامپایل‌شدهٔ DirectX. بازی‌ها و برنامه‌های گرافیکی بار اول کمی "
             "کندتر بالا می‌آیند."),
    "NVIDIA": dict(
        app="NVIDIA", kind="کش گرافیک",
        desc="کش شیدرهای NVIDIA (DirectX و OpenGL) و کش دانلود درایور."),
    "Windows Update": dict(
        app="Windows Update", kind="کش آپدیت",
        desc="آپدیت‌های ویندوز که قبلاً دانلود شده‌اند. وقتی آپدیتی در حال نصب است یا "
             "منتظر ری‌استارت است این را پاک نکن."),
    "Windows — Prefetch": dict(
        app="ویندوز — Prefetch", kind="کش راه‌اندازی",
        desc="ردپاهایی که ویندوز برای سریع‌تر باز کردن برنامه‌ها استفاده می‌کند. تا وقتی "
             "این ردپاها از نو ساخته شوند، برنامه‌ها کمی کندتر باز می‌شوند."),
    "Windows — Delivery Optimization": dict(
        app="ویندوز — Delivery Optimization", kind="کش آپدیت",
        desc="کش دانلود آپدیت به‌صورت همتا-به-همتا که بین کامپیوترهای شبکه‌ات به اشتراک "
             "گذاشته می‌شود."),
    "OneDrive": dict(
        app="OneDrive", kind="لاگ",
        desc="لاگ‌های عیب‌یابی OneDrive. فایل‌های سینک‌شده و پوشهٔ محلی OneDrive دست نمی‌خورند."),
    "Microsoft Office": dict(
        app="مایکروسافت آفیس", kind="کش فایل",
        desc="کش فایل‌های آفیس: نسخه‌های اخیر اسناد که برای باز شدن سریع و بازیابی نگه داشته "
             "می‌شوند."),
    "Xbox / Game Bar": dict(
        app="Xbox / Game Bar", kind="کش اپ استور",
        desc="کش‌های داخلی اپ‌های Xbox، Game Bar و مایکروسافت استور."),

    # ---------- launchers ----------
    "Steam": dict(
        app="Steam", kind="کش لانچر",
        desc="مرورگر داخلی Steam، کش شیدر، لاگ‌ها و مانیفست‌های دانلود. "
             "بازی‌های نصب‌شده دست نمی‌خورند."),
    "Epic Games Launcher": dict(
        app="Epic Games Launcher", kind="کش لانچر",
        desc="کش وب و لاگ‌های Epic Games Launcher."),

    # ---------- local tooling ----------
    "XAMPP (Apache)": dict(
        app="XAMPP (آپاچی)", kind="لاگ سرور",
        desc="لاگ‌های دسترسی و خطای آپاچی. فایل‌های سایت و تنظیماتت دست نمی‌خورند."),
    "MongoDB": dict(
        app="MongoDB", kind="لاگ دیتابیس",
        desc="لاگ‌های سرور MongoDB. دیتابیس‌هایت دست نمی‌خورند."),
    "Installer temp folders": dict(
        app="پوشه‌های موقت نصب‌کننده‌ها", kind="فایل موقت",
        desc="پوشه‌های موقتی که نصب‌کننده‌ها و پکیج‌منیجرها جا می‌گذارند."),
}
