#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${BUILD_DIR:-"$root/build-appimage"}
appdir=$build_dir/AppDir
output=${OUTPUT:-"$root/TombaRecomp-v0.11.2-alpha-linux-x86_64.AppImage"}
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

cmake -S "$root" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER_LAUNCHER= \
    -DCMAKE_CXX_COMPILER_LAUNCHER= \
    -DPSX_DEBUG_TOOLS=OFF \
    -DPSX_SDL_BACKEND=SDL2
cmake --build "$build_dir" --target psx-runtime -j "${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}"

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
cg_tag=$(psx_overlay_cg_tag \
    --runtime-include "$fw/runtime/include" \
    --recompiler "$recompiler_bin" \
    --game-toml "$root/packaging/release/game.toml" \
    --flavor-from-build "$build_dir" \
    --runtime-target psx-runtime)
[ -n "$cg_tag" ] || { echo "could not compute codegen tag" >&2; exit 1; }
cache_src_root=${OVERLAY_CACHE_DIR:-"$root/build-linux-cache/cache"}
psx_add_overlay_cache --game-id "$game_id" \
                      --cache-src-root "$cache_src_root" \
                      --stage "$payload" \
                      --cg-tag "$cg_tag"
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
"$image_tool" "$root/recomp/launcher/boxart.tga" \
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

rm -f -- "$output"
ARCH=x86_64 "$appimagetool" --appimage-extract-and-run "$appdir" "$output"
chmod 0755 "$output"

sha256sum "$output"
