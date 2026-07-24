#!/usr/bin/env sh
# Regenerate Tomba's recompiled C (generated/SCUS_942.36_{full,dispatch}.c) from
# your disc/EXE via the framework recompiler. Cross-platform companion to
# tools/regen.ps1 (Windows). Safe to run from any directory.
#
# Prerequisite: build the recompiler tool once (see psxrecomp/docs/BUILDING.md):
#   cmake -S psxrecomp/recompiler -B psxrecomp/recompiler/build -G Ninja -DCMAKE_BUILD_TYPE=Release
#   cmake --build psxrecomp/recompiler/build
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FRAMEWORK="$ROOT/psxrecomp"
CONFIG="$ROOT/game.toml"

# Recompiler binary: no extension on macOS/Linux, .exe under MSYS2/MinGW.
TOOL="$FRAMEWORK/recompiler/build/psxrecomp-game"
if [ ! -f "$TOOL" ] && [ -f "$TOOL.exe" ]; then
    TOOL="$TOOL.exe"
fi

if [ ! -f "$TOOL" ]; then
    echo "error: recompiler tool not built:" >&2
    echo "         $FRAMEWORK/recompiler/build/psxrecomp-game[.exe]" >&2
    echo >&2
    echo "Build it first (one time):" >&2
    echo "  cmake -S \"$FRAMEWORK/recompiler\" -B \"$FRAMEWORK/recompiler/build\" -G Ninja -DCMAKE_BUILD_TYPE=Release" >&2
    echo "  cmake --build \"$FRAMEWORK/recompiler/build\"" >&2
    echo "See psxrecomp/docs/BUILDING.md (\"Build and run a game\")." >&2
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    echo "error: game.toml not found: $CONFIG" >&2
    exit 1
fi

echo "Regenerating recompiled C from $CONFIG ..."
cd "$ROOT"
"$TOOL" --config "$CONFIG"

echo
echo "Done. generated/ now holds the recompiled C. Build the game with:"
echo "  cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && cmake --build build --target psx-runtime"
