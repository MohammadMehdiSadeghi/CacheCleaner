#!/bin/sh
# Download the lucide glyphs used by tools/make_icon.py (ISC licensed).
# jsdelivr is reachable directly from this machine; no proxy needed.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)/glyphs"
mkdir -p "$DIR"
for g in sparkles eraser layers database hard-drive zap wind; do
  curl -sS -m 30 -o "$DIR/$g.svg" \
    "https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/$g.svg"
  printf '%-12s %s bytes\n' "$g" "$(wc -c < "$DIR/$g.svg")"
done
