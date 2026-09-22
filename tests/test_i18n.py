# -*- coding: utf-8 -*-
"""test_i18n.py — proves the Persian layer stays complete.

Every rule must have a Persian entry, every entry must match a real rule, and no
translation may be left as the English string (which would silently look "done").
Run: python tests/test_i18n.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cc_rules as R
import i18n_rules as I

fails = 0


def check(name, cond, extra=""):
    global fails
    print(("OK   " if cond else "FAIL ") + name + ("  " + str(extra) if extra else ""))
    if not cond:
        fails += 1


apps = [r["app"] for r in R.RULES]
missing = [a for a in apps if a not in I.FA]
extra = [k for k in I.FA if k not in apps]
check("every rule has a Persian entry", not missing, missing)
check("no orphan Persian entries", not extra, extra)

malformed = [k for k, v in I.FA.items() if set(v) != {"app", "kind", "desc"}]
check("every entry has app/kind/desc", not malformed, malformed)

empty = [k for k, v in I.FA.items() if not all(str(x).strip() for x in v.values())]
check("no empty translations", not empty, empty)

# A translation identical to the English source means it was never translated.
same_kind = [k for k, v in I.FA.items()
             if v["kind"] == next(r["kind"] for r in R.RULES if r["app"] == k)]
check("every cache type is translated", not same_kind, same_kind)

same_desc = [k for k, v in I.FA.items()
             if v["desc"] == next(r["desc"] for r in R.RULES if r["app"] == k)]
check("every description is translated", not same_desc, same_desc)

# Persian text must actually contain Persian characters.
FA_RANGE = re.compile(r"[\u0600-\u06FF]")
no_persian = [k for k, v in I.FA.items() if not FA_RANGE.search(v["kind"] + v["desc"])]
check("translations really are Persian", not no_persian, no_persian)

# Rule text must stay English (that is the default language).
en_persian = [r["app"] for r in R.RULES if FA_RANGE.search(r["kind"] + r["desc"])]
check("rule text stays English", not en_persian, en_persian)

# Brand names keep their Latin spelling in both languages.
brands = ["Spotify", "Discord", "Slack", "Steam", "npm", "pnpm", "Yarn", "VLC",
          "MongoDB", "OneDrive", "NVIDIA", "Cursor", "Docker Desktop", "Xbox / Game Bar"]
bad_brand = [b for b in brands if I.FA.get(b, {}).get("app") != b]
check("brand names keep their Latin spelling", not bad_brand, bad_brand)

print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
