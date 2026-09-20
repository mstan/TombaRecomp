#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${BUILD_DIR:-"$root/build-appimage"}
appdir=$build_dir/AppDir
# Single source of truth: VERSION. A hardcoded copy here is how a packager
# ends up naming an artifact for the wrong build.
version=$(tr -d " \t\r\n" < "$root/VERSION")
[ -n "$version" ] || { echo "VERSION is empty" >&2; exit 1; }
output=${OUTPUT:-"$root/TombaRecomp-v$version-linux-x86_64.AppImage"}
tools_dir=$build_dir/appimage-tools
fw=$root/psxrecomp

# shellcheck source=/dev/null
. "$fw/tools/release_overlay_stage.sh"
psx_release_stage_init "$fw"

linuxdeploy_url=https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
linuxdeploy_sha=36a2d7e274d12e1050d0e9ecfe11d339ed54720b2bec464c286d53f8b07f5c62
appimagetool_url=https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
appimagetool_sha=a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0

if [ ! -f "$root/generated/SCUS_942.36_dispatch.c" ]; then
    echo "Missing generated game sources. Run tools/regen.sh first." >&2
    exit 1
fi

bios_build=${PSXRECOMP_BIOS_BUILD:-recompiler/build-linux}
if [ ! -x "$fw/$bios_build/psxrecomp-game" ] || [ ! -x "$fw/$bios_build/psxrecomp-bios" ]; then
    cmake -S "$fw/recompiler" -B "$fw/$bios_build" -G Ninja -DCMAKE_BUILD_TYPE=Release
    cmake --build "$fw/$bios_build" --target psxrecomp-game psxrecomp-bios -j "${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}"
fi

if [ -f "$fw/bios/openbios.bin" ] && [ ! -f "$fw/generated/OpenBIOS_dispatch.c" ]; then
    (cd "$fw" && PSXRECOMP_BIOS_BUILD="$bios_build" tools/regen_bios.sh --config bios/OpenBIOS.toml)
fi

if [ "${SKIP_RUNTIME_BUILD:-0}" != 1 ]; then
# CMAKE_EXTRA_ARGS: host-specific configure flags, word-split on purpose.
# Needed because a host can satisfy find_package(SDL3) with a system SDL3 the
# compiler cannot actually link the check against, which trips the runtime's
# own SDL3 guard. -DCMAKE_DISABLE_FIND_PACKAGE_SDL3=TRUE skips the system copy
# and lets PSX_SDL3_FETCH build the pinned SDL3 from source.
# shellcheck disable=SC2086
cmake -S "$root" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER_LAUNCHER= \
    -DCMAKE_CXX_COMPILER_LAUNCHER= \
    -DPSX_DEBUG_TOOLS=OFF \
    -DPSX_SDL_BACKEND=SDL3 \
    -DPSX_PGXP_VARIANT=OFF \
    ${CMAKE_EXTRA_ARGS:-}
cmake --build "$build_dir" --target psx-runtime -j "${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}"
fi

case "$appdir" in
    "$build_dir"/*) ;;
    *) echo "Refusing unsafe AppDir path: $appdir" >&2; exit 1 ;;
esac
rm -rf -- "$appdir"
mkdir -p "$appdir/usr/bin" "$appdir/usr/share/tombarecomp"

install -m 0755 "$build_dir/Tomba__Recompiled" \
    "$appdir/usr/bin/Tomba__Recompiled"
install -m 0755 "$root/packaging/linux/AppRun" "$appdir/AppRun"
install -m 0644 "$root/packaging/linux/io.github.mstan.TombaRecomp.desktop" \
    "$appdir/io.github.mstan.TombaRecomp.desktop"

payload=$appdir/usr/share/tombarecomp
cp -a "$build_dir/assets" "$payload/assets"
cp -a "$build_dir/bios" "$payload/bios"
psx_add_mod_catalog --build-path "$build_dir" --stage "$payload" \
                    --runtime-target psx-runtime

game_id=SCUS-94236
recompiler_bin=$fw/$bios_build/psxrecomp-game
"${PSX_RELEASE_STAGE_PYTHON:-python3}" "$fw/tools/aot_overlay_pipeline.py" release \
    --profile "$root/aot/overlays.json" --game-toml "$root/game.toml" \
    --runtime-config "$root/packaging/release/game.toml" \
    --recompiler "$recompiler_bin" --runtime-build-dir "$build_dir" --runtime-target psx-runtime \
    --work-dir "$build_dir/aot-release" \
    --stage "$payload" --gcc "${AOT_GCC:-gcc}" --workers "${AOT_WORKERS:-3}"
mkdir -p "$payload/licenses"
cp "$root/psxrecomp/runtime/licenses/libchdr-NOTICES.txt" "$payload/licenses/"
cp "$root/packaging/release/game.toml" "$payload/game.toml"
cp "$root/game_options.toml" "$payload/game_options.toml"
cp "$root/packaging/release/input.ini" "$payload/input.ini"
cp "$root/packaging/release/START_HERE.txt" "$payload/START_HERE.txt"
cp "$root/LICENSE" "$root/README.md" "$root/RELEASE_NOTES.md" "$payload/"
cp "$root/packaging/linux/README.md" "$payload/APPIMAGE_README.md"
psx_add_overlay_toolchain --stage "$payload" \
                          --recomp-dir "$(dirname -- "$recompiler_bin")" \
                          --recomp-tools "$fw/tools" \
                          --recomp-include "$fw/runtime/include" \
                          --dl-cache "$tools_dir" \
                          --platform linux

# recomp-ui loads fonts and textures through SDL_GetBasePath(), which resolves
# the real ELF location inside the mounted AppImage rather than psxrecomp's
# writable argv[0] anchor. Keep those immutable assets reachable beside the ELF.
ln -s ../share/tombarecomp/assets "$appdir/usr/bin/assets"

if command -v magick >/dev/null 2>&1; then
    image_tool=magick
elif command -v convert >/dev/null 2>&1; then
    image_tool=convert
else
    echo "ImageMagick is required to create the AppImage icon." >&2
    exit 1
fi
"$image_tool" "$root/launcher_assets/img/boxart.tga" \
    -resize 240x240 -background transparent -gravity center -extent 256x256 \
    "$appdir/io.github.mstan.TombaRecomp.png"
ln -s io.github.mstan.TombaRecomp.png "$appdir/.DirIcon"

mkdir -p "$tools_dir"
fetch_tool() {
    url=$1
    sha=$2
    dest=$3
    if [ ! -f "$dest" ] || \
       [ "$(sha256sum "$dest" | awk '{print $1}')" != "$sha" ]; then
        curl -fL --retry 3 "$url" -o "$dest.tmp"
        printf '%s  %s\n' "$sha" "$dest.tmp" | sha256sum -c -
        mv "$dest.tmp" "$dest"
    fi
    chmod 0755 "$dest"
}

linuxdeploy=$tools_dir/linuxdeploy-x86_64.AppImage
appimagetool=$tools_dir/appimagetool-x86_64.AppImage
fetch_tool "$linuxdeploy_url" "$linuxdeploy_sha" "$linuxdeploy"
fetch_tool "$appimagetool_url" "$appimagetool_sha" "$appimagetool"

export NO_STRIP=1
"$linuxdeploy" --appimage-extract-and-run \
    --appdir "$appdir" \
    --executable "$appdir/usr/bin/Tomba__Recompiled" \
    --desktop-file "$appdir/io.github.mstan.TombaRecomp.desktop" \
    --icon-file "$appdir/io.github.mstan.TombaRecomp.png"

# Prune libraries the app cannot actually reach.
#
# linuxdeploy copies the whole transitive closure it sees on the BUILD host,
# including libraries pulled in only by host-side dependencies we do NOT
# bundle (freetype/harfbuzz drag in glib, pcre2, png16, brotli, bz2,
# graphite2). Those copies are unreachable through the binary's own RUNPATH
# ($ORIGIN/../lib); the only way to make the loader prefer them is a global
# LD_LIBRARY_PATH, which is exactly what AppRun must not set -- it reaches
# every child process, so a host zenity/kdialog spawned for the file picker
# would load OUR glib against the host GTK and die on start. That was the dead
# Browse button.
#
# The rule is general: bundle a library only if everything above it in the
# chain is bundled too. Resolve the closure with LD_LIBRARY_PATH unset -- which
# is exactly what the shipped AppRun gives the loader -- and drop whatever the
# loader did not choose.
if [ -d "$appdir/usr/lib" ]; then
    keep=$build_dir/appdir-keep.txt
    env -u LD_LIBRARY_PATH ldd "$appdir/usr/bin/Tomba__Recompiled" \
        | awk '{ for (i = 1; i <= NF; i++) if ($i ~ /^\//) print $i }' \
        | while read -r p; do readlink -f "$p" 2>/dev/null || true; done \
        | sort -u > "$keep"
    pruned=0
    for f in "$appdir"/usr/lib/*; do
        [ -e "$f" ] || continue
        real=$(readlink -f "$f")
        if ! grep -qxF "$real" "$keep"; then
            echo "  prune unreachable bundled lib: $(basename "$f")"
            rm -f "$f"
            pruned=$((pruned + 1))
        fi
    done
    echo "  pruned $pruned unreachable libraries from usr/lib"
    # Whatever survived must resolve without LD_LIBRARY_PATH, or the AppImage
    # would only work by poisoning its children's environment.
    if env -u LD_LIBRARY_PATH ldd "$appdir/usr/bin/Tomba__Recompiled" \
            | grep -q "not found"; then
        echo "binary has unresolved libraries without LD_LIBRARY_PATH" >&2
        env -u LD_LIBRARY_PATH ldd "$appdir/usr/bin/Tomba__Recompiled" \
            | grep "not found" >&2
        exit 1
    fi
fi

rm -f -- "$output"
ARCH=x86_64 "$appimagetool" --appimage-extract-and-run "$appdir" "$output"
chmod 0755 "$output"

(cd "$(dirname -- "$output")" && sha256sum "$(basename -- "$output")") > "$output.sha256"
cat "$output.sha256"
