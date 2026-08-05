#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${BUILD_DIR:-"$root/build-appimage"}
appdir=$build_dir/AppDir
output=${OUTPUT:-"$root/TombaRecomp-v0.11.2-alpha-linux-x86_64.AppImage"}
tools_dir=$build_dir/appimage-tools

linuxdeploy_url=https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
linuxdeploy_sha=421ca71d5c69ea97c6309276232990d43df1dcece0edfaa26bbf926ff96ed12e
appimagetool_url=https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
appimagetool_sha=a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0

if [ ! -f "$root/generated/SCUS_942.36_dispatch.c" ]; then
    echo "Missing generated game sources. Run tools/regen.sh first." >&2
    exit 1
fi

cmake -S "$root" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
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
cp -a "$build_dir/mods" "$payload/mods"

# Prebuilt overlay cache. Without it every player's first session runs overlays
# interpreted. Linux shards are .so under gcc/linux-x64 (overlay_loader.c's
# OVERLAY_SHARED_EXT), and only THIS build's codegen tag is usable -- the tag
# folds in a hash of the packaged game.toml, so a cache built against the dev
# config lands elsewhere and the loader ignores it. Fail rather than silently
# ship a slow package.
game_id=SCUS-94236
cache_src=${OVERLAY_CACHE_DIR:-"$root/build-linux-cache/cache"}/$game_id
cg_tag=$(python3 - "$root" <<'PY'
import importlib.util, os, sys
root = sys.argv[1]
spec = importlib.util.spec_from_file_location(
    'co', os.path.join(root, 'psxrecomp/tools/compile_overlays.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
inc = os.path.join(root, 'psxrecomp/runtime/include')
exe = os.path.join(root, 'psxrecomp/recompiler/build-linux/psxrecomp-game')
gt  = os.path.join(root, 'packaging/release/game.toml')
print('cg%d_%08x_gc%08x' % (m.codegen_ver(inc), m.codegen_hash(inc),
                            m.overlay_config_hash(exe, gt)))
PY
)
shards=$(find "$cache_src" -path "*/$cg_tag/*" \
    \( -name '*.so' -o -name '*.ranges' -o -name '*.resident' \) 2>/dev/null | wc -l)
if [ "${ALLOW_NO_CACHE:-0}" != "1" ] && [ "$shards" -eq 0 ]; then
    echo "No overlay cache for tag $cg_tag under $cache_src." >&2
    echo "Build one with compile_overlays.py against the PACKAGED game.toml," >&2
    echo "or set ALLOW_NO_CACHE=1 to ship without one." >&2
    exit 1
fi
if [ "$shards" -gt 0 ]; then
    mkdir -p "$payload/cache/$game_id"
    ( cd "$cache_src" && find . -path "*/$cg_tag/*" -type f \
        \( -name '*.so' -o -name '*.ranges' -o -name '*.resident' \) \
        -exec cp --parents {} "$payload/cache/$game_id/" \; )
    echo "Bundled overlay cache: $(find "$payload/cache" -name '*.so' | wc -l) native overlay .so"
fi
mkdir -p "$payload/licenses"
cp "$root/psxrecomp/runtime/licenses/libchdr-NOTICES.txt" "$payload/licenses/"
cp "$root/packaging/release/game.toml" "$payload/game.toml"
cp "$root/game_options.toml" "$payload/game_options.toml"
cp "$root/packaging/release/input.ini" "$payload/input.ini"
cp "$root/packaging/release/START_HERE.txt" "$payload/START_HERE.txt"
cp "$root/LICENSE" "$root/README.md" "$root/RELEASE_NOTES.md" "$payload/"
cp "$root/packaging/linux/README.md" "$payload/APPIMAGE_README.md"

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
