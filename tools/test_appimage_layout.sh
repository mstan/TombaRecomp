#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 /path/to/AppDir" >&2
    exit 2
fi

appdir=$(CDPATH= cd -- "$1" && pwd)
tmp=$(mktemp -d)
trap 'chmod -R u+w "$appdir" "$tmp" 2>/dev/null || true; rm -rf "$tmp"' EXIT HUP INT TERM

chmod -R a-w "$appdir"
APPDIR=$appdir \
APPIMAGE=$tmp/TombaRecomp.AppImage \
TOMBA_RECOMP_DATA_DIR=$tmp/state \
TOMBA_RECOMP_SEED_ONLY=1 \
"$appdir/AppRun" > "$tmp/seed-path"

test "$(cat "$tmp/seed-path")" = "$tmp/state"
test -f "$tmp/state/game.toml"
test -f "$tmp/state/input.ini"
test -f "$tmp/state/bios/openbios.bin"
test -f "$tmp/state/mods/bundled/psx.enhancement.fast-loading/1.0.0/manifest.toml"
test ! -e "$appdir/settings.toml"

printf 'user-owned\n' > "$tmp/state/input.ini"
APPDIR=$appdir \
APPIMAGE=$tmp/moved.AppImage \
TOMBA_RECOMP_DATA_DIR=$tmp/state \
TOMBA_RECOMP_SEED_ONLY=1 \
"$appdir/AppRun" >/dev/null
test "$(cat "$tmp/state/input.ini")" = "user-owned"

test ! -d "$tmp/state/mods/packages"
test -f "$tmp/state/AOT_CACHE_AUDIT.json"
count=$(find "$tmp/state/mods/bundled" -mindepth 1 -maxdepth 1 -type d | wc -l)
expected=$(find "$appdir/usr/share/tombarecomp/mods/bundled" -mindepth 1 -maxdepth 1 -type d | wc -l)
test "$count" -eq "$expected"
test "$count" -gt 0

echo "AppImage layout test passed: read-only payload, persistent writable state, $count bundled packages and an AOT audit receipt"
