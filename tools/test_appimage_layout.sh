#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 /path/to/AppDir" >&2
    exit 2
fi

appdir=$(CDPATH= cd -- "$1" && pwd)
tmp=$(mktemp -d)
trap 'chmod -R u+w "$appdir" "$tmp" 2>/dev/null || true; rm -rf "$tmp"' EXIT HUP INT TERM

# --- the file picker must not be poisoned by the bundle ---------------------
# AppRun must NOT export a bundle LD_LIBRARY_PATH. Every child process inherits
# it, including the host zenity/kdialog the launcher spawns for Browse; that
# child then loads OUR glib/pcre2 against the host GTK it is linked against and
# dies before drawing. The launcher read that as a plain cancel, so the button
# did nothing at all. The binary carries RUNPATH $ORIGIN/../lib and does not
# need the variable.
if grep -Eq '^[[:space:]]*export[[:space:]]+LD_LIBRARY_PATH=' "$appdir/AppRun"; then
    echo "AppRun exports a global LD_LIBRARY_PATH; it leaks into spawned host tools" >&2
    grep -n 'LD_LIBRARY_PATH' "$appdir/AppRun" >&2
    exit 1
fi
grep -q 'RECOMP_HOST_LD_LIBRARY_PATH' "$appdir/AppRun" || {
    echo "AppRun does not record the host LD_LIBRARY_PATH for spawned tools" >&2
    exit 1
}

runtime_bin=$appdir/usr/bin/Tomba__Recompiled

# Everything the binary needs must resolve with LD_LIBRARY_PATH unset -- that
# is exactly what the shipped AppRun gives the loader.
if env -u LD_LIBRARY_PATH ldd "$runtime_bin" | grep -q 'not found'; then
    echo "binary has unresolved libraries without LD_LIBRARY_PATH" >&2
    env -u LD_LIBRARY_PATH ldd "$runtime_bin" | grep 'not found' >&2
    exit 1
fi

# ...and nothing may sit in usr/lib that the loader will not actually choose.
# An unreachable copy is only reachable by setting the global LD_LIBRARY_PATH
# above, so leaving one there invites the bug straight back.
if [ -d "$appdir/usr/lib" ]; then
    reach=$(env -u LD_LIBRARY_PATH ldd "$runtime_bin" \
              | awk '{ for (i = 1; i <= NF; i++) if ($i ~ /^\//) print $i }' \
              | while read -r p; do readlink -f "$p" 2>/dev/null || true; done \
              | sort -u)
    for f in "$appdir"/usr/lib/*; do
        [ -e "$f" ] || continue
        real=$(readlink -f "$f")
        printf '%s\n' "$reach" | grep -qxF "$real" || {
            echo "unreachable library bundled in usr/lib: $(basename "$f")" >&2
            echo "(nothing loads it without a global LD_LIBRARY_PATH)" >&2
            exit 1
        }
    done
fi

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

# --- the picker, exercised through the real AppRun --------------------------
# RECOMP_UI_PICKER_SELFTEST makes the shipped binary run one native pick and
# report the tri-state outcome on stdout, before any window or GL work. So this
# drives the REAL AppRun environment against a stub backend, with nobody
# clicking Browse. The run is killed by timeout afterwards (the runtime goes on
# to boot without a disc); only the self-test lines matter.
chmod -R u+w "$appdir" 2>/dev/null || true
stubbin=$tmp/stubbin
rec=$tmp/picker.env
mkdir -p "$stubbin"
cat > "$stubbin/zenity" <<STUB
#!/bin/sh
/usr/bin/env > "$rec"
exit \${STUB_ZENITY_EXIT:-1}
STUB
chmod +x "$stubbin/zenity"

picker_run() {  # $1 = stub exit code -> stdout of the run
    rm -f "$rec"
    pickdir=$tmp/pick$1
    mkdir -p "$pickdir"
    ( APPDIR=$appdir \
      APPIMAGE=$pickdir/TombaRecomp.AppImage \
      TOMBA_RECOMP_DATA_DIR=$pickdir/state \
      PATH="$stubbin:$PATH" \
      STUB_ZENITY_EXIT="$1" \
      RECOMP_UI_PICKER_SELFTEST=1 \
      SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
      timeout 60 "$appdir/AppRun" 2>&1 ) || true
}

# 1. The backend really was reached, and it was NOT handed the bundle's library
#    path. That inheritance is the root cause of the dead Browse button.
out1=$(picker_run 1)
printf '%s\n' "$out1" | grep -q '\[picker-selftest\] native_available=1' || {
    echo "picker self-test did not see the stub backend" >&2
    printf '%s\n' "$out1" | tail -20 >&2
    exit 1
}
test -f "$rec" || { echo "stub picker backend never ran" >&2; exit 1; }
if grep -q '^LD_LIBRARY_PATH=' "$rec"; then
    echo "spawned picker backend inherited LD_LIBRARY_PATH:" >&2
    grep '^LD_LIBRARY_PATH=' "$rec" >&2
    exit 1
fi
for poison in LD_PRELOAD APPDIR APPIMAGE; do
    if grep -q "^$poison=" "$rec"; then
        echo "spawned picker backend inherited $poison" >&2
        exit 1
    fi
done
# exit 1 is a genuine cancel: no fallback, and no path.
printf '%s\n' "$out1" | grep -q '\[picker-selftest\] result=0' || {
    echo "backend exit 1 was not read as a cancel" >&2
    printf '%s\n' "$out1" | grep picker-selftest >&2
    exit 1
}
printf '%s\n' "$out1" | grep -q '\[picker-selftest\] builtin_fallback=no' || {
    echo "a cancel must not fall back to the built-in picker" >&2
    exit 1
}

# 2. Any other exit code means the backend is unusable -> the built-in picker
#    takes over. This used to be mapped to "cancel", and the click did nothing.
out2=$(picker_run 2)
printf '%s\n' "$out2" | grep -q '\[picker-selftest\] result=-1' || {
    echo "backend exit 2 was not reported as unusable" >&2
    printf '%s\n' "$out2" | grep picker-selftest >&2
    exit 1
}
printf '%s\n' "$out2" | grep -q '\[picker-selftest\] builtin_fallback=yes' || {
    echo "a failed backend did not fall back to the built-in picker" >&2
    printf '%s\n' "$out2" | grep picker-selftest >&2
    exit 1
}

echo "picker test passed: host environment for spawned dialogs, cancel and failure told apart, built-in fallback armed"

echo "AppImage layout test passed: read-only payload, persistent writable state, $count bundled packages and an AOT audit receipt"
