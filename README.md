# TombaRecomp

> _This recompilation is a **byproduct of developing
> [psxrecomp](https://github.com/mstan/psxrecomp)** — the games are the proving ground, the framework is the
> goal, and depth will keep landing over months, not days. My time for any one
> title is limited, so I ask for your patience. Contributions are welcome —
> testing, issues, and PRs to the game or framework all help and will
> accelerate this game's polish. More on the why at:
> [Recomp + AI: 5 Months Later »](https://1379.tech/recomp-ai-5-months-later/)_

Tomba! (USA, SCUS-94236) statically recompiled to a native PC executable with
[PSXRecomp](https://github.com/mstan/psxrecomp).

[![PSXRecomp demo](https://img.youtube.com/vi/CID9oVhgCyY/maxresdefault.jpg)](https://www.youtube.com/watch?v=CID9oVhgCyY)

## What This Is

This repository contains the game-specific configuration, seeds, tools, and
build glue for running Tomba on the PSXRecomp framework. Tomba's MIPS code is
machine-translated ("recompiled") ahead of time into native C, then compiled
into a real Windows/macOS/Linux program that runs the game's own logic on a
faithful simulation of the PS1 hardware (GPU, SPU, GTE, memory cards) plus the
real, recompiled PS1 BIOS — no high-level emulation shims.

It does **not** contain the Tomba disc image, the PS1 BIOS, generated game
code, or any decompiled Tomba C. Those are produced locally from your own
legally obtained assets.

Important files:

- `game.toml`: Tomba runtime / recompiler / video / controller / widescreen config.
- `game_options.toml`: in-game OPTION settings that persist across launches.
- `seeds/`: Ghidra-derived function starts and game-specific seed data.
- `tools/regen.ps1`: regenerates the Tomba recompiled C output.
- `tools/package_release.ps1`: builds the redistributable release zip.
- `psxrecomp/`: the [PSXRecomp](https://github.com/mstan/psxrecomp) framework,
  pulled in as a **git submodule** pinned to a known-good commit.
- `ISSUES.md`: game-specific issue log.

## Status

The game is playable from BIOS boot through gameplay. Latest release:
**v0.2.0-alpha** (2026-06-16).

| Area | State |
|---|---|
| PS1 BIOS boot | Works (real recompiled BIOS) |
| Disc-detect / license screen | Works |
| Whoopee Camp + intro FMV | Works (intro skippable; optional auto-skip) |
| Title menu / OPTIONS | Works (settings persist across launches) |
| NEW GAME / LOAD GAME | Works |
| Memory-card save & load | Works (standard `.mcd`, emulator-compatible) |
| Gameplay | Playable; known crashes tracked in `ISSUES.md` |
| Renderers | Software **and** OpenGL (GPU); OpenGL is the default |
| Widescreen 16:9 | Experimental, opt-in (true wider FOV) |
| Controller | Seamless analog + D-pad; DualShock on by default |

## Features

- **Two renderers.** A CPU software rasterizer and a GPU-authoritative OpenGL
  backend (default). OpenGL moves rasterization and supersampling onto the GPU
  so fill-heavy scenes (e.g. the mushroom forest) hold 59.94 fps. Falls back to
  software automatically if GL init fails.
- **Supersampling + anti-aliasing.** Internal-resolution SSAA (2×–4×) with
  optional linear present filtering for clean edges. Ships at 2×.
- **Optional texture filtering.** Nearest (native PSX look) or bilinear.
- **Experimental widescreen (16:9).** A genuine wider field of view — the GTE
  projection is widened so you see more of the world at the sides, not a
  stretched picture. Works on both renderers. Opt-in; some 2D HUD/menu/FMV
  elements and the occasional background seam can look off. 21:9 is not ready.
- **Seamless analog + D-pad controller.** The left analog stick (variable run
  speed) and the D-pad both work at once with no mode toggle. DualShock/analog
  is on by default on both player slots. Adjustable stick deadzone.
- **Persistent in-game settings.** Your OPTION choices — text speed, sound,
  vibration, screen adjust — are saved and restored on every launch.
- **Graphical launcher.** Pick your BIOS, disc, and memory cards; verify the
  disc; configure renderer / supersampling / widescreen / controller, all with
  live settings persistence — then press Launch.
- **Self-growing native cache.** Areas you visit are converted to fast native
  code as you play and reused on later launches (see "Help make your game
  faster" below).

## Setup

### Release Package (recommended)

1. Download `TombaRecomp-v*-windows-x64.zip` from Releases and extract it.
2. Run `TombaRecomp.exe`. A **launcher window** opens.
3. Set your PlayStation **BIOS**: select your legally obtained `SCPH1001.BIN`
   (a 512 KB file dumped from your own console).
4. Set the game **disc**: select your legally obtained Tomba! (USA, SCUS-94236)
   disc image. The launcher verifies the ISO9660 header, region, and serial.
5. Optionally adjust renderer, supersampling, screen look, widescreen, and
   controller settings, then press **Launch**. Your choices are remembered.

Accepted disc formats: `.cue` + `.bin` (preferred — pick the `.cue`), direct
`.bin`, and `.iso`. If the header or game ID does not match `SCUS-94236`, the
launcher warns and tries to run the image anyway.

Selected paths persist next to the executable (`bios.cfg` / `disc.cfg` and
`settings.toml`). Delete those to pick different files or reset settings.

### Building From Source

Builds on **Windows (MSVC/MinGW)**, **macOS (Apple Silicon & Intel)**, and **Linux**.

Requirements:

- A C/C++ toolchain (MSVC/MinGW, Apple Clang, or Clang/GCC) and CMake 3.20+.
- Tomba! (USA, SCUS-94236) disc image (`.cue` + `.bin`, `.bin`, or `.iso`). Not included.
- Sony SCPH1001 BIOS ROM (`SCPH1001.BIN`). Not included.
- SDL2: bundled on Windows (MSYS2 `mingw-w64-x86_64` toolchain); `brew install sdl2 pkg-config ninja` on macOS; `libsdl2-dev` + `ninja` on Linux.
- The `psxrecomp` framework, which comes in as a **git submodule** at
  `psxrecomp/` (clone with `--recurse-submodules`, below), plus a recompiled
  BIOS in `psxrecomp/generated/` (see the framework README).

Clone with the framework submodule:

```sh
git clone --recurse-submodules https://github.com/mstan/TombaRecomp.git
# or, in an existing clone:
git submodule update --init --recursive
```

Example local layout:

```sh
TombaRecomp/psxrecomp/            # framework submodule (pinned commit)
TombaRecomp/psxrecomp/bios/SCPH1001.BIN
TombaRecomp/tomba/tomba.cue
TombaRecomp/tomba/tomba.bin
```

> **Sharing one framework checkout across games (optional dev setup).** If you
> hack on several game repos plus the framework at once, replace each game's
> `psxrecomp/` submodule directory with a junction/symlink to a single shared
> framework checkout so you don't keep N copies — see the framework's
> [`docs/BUILDING.md`](https://github.com/mstan/psxrecomp/blob/master/docs/BUILDING.md#linking-the-framework).

The recompiler needs the game's PS-X EXE extracted from the disc. A
cross-platform helper is included:

```sh
python3 tools/extract_psx_exe.py tomba/tomba.bin SCUS_942.36 tomba/SCUS_942.36
```

Generate the recompiled C, then build and run:

```sh
# Regenerate generated/SCUS_942.36_{full,dispatch}.c from the disc/EXE by
# invoking the framework recompiler directly (all platforms):
#   psxrecomp/recompiler/build/psxrecomp-game --config game.toml
# This also emits the settings-persistence hook (game_options.toml) and the
# widescreen sites, so a regen is required after changing those.
# (build the recompiler first: see psxrecomp/docs/BUILDING.md)

# Windows (MSYS2/MinGW)
cmake -S . -B build -G "Unix Makefiles" && cmake --build build -j16 && ./build/psx-runtime.exe

# macOS / Linux (Ninja)
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && ninja -C build psx-runtime
./build/psx-runtime --game game.toml --disc tomba/tomba.cue
```

To build the redistributable Windows release (regens, builds with the launcher,
bundles assets + cache, and zips it): `pwsh tools/package_release.ps1`.

## Configuration

Most options are exposed in the launcher and persist to `settings.toml`. The
underlying defaults live in `game.toml`:

- `[video]` — `renderer` (`opengl` / `software`), `supersampling` (1–4),
  `antialiasing`, `texture_filtering` (`nearest` / `bilinear`), `aspect_ratio`
  (`4:3` / `16:9`), `auto_skip_fmv`.
- `[controller]` — `default_analog` (DualShock on by default), `deadzone`.
- `[runtime]` — `disc_speed`, `turbo_loads` (compressed loading screens),
  `fast_boot`, `overlay_cache`.
- `[widescreen]*` — widescreen projection / culling / backdrop hooks (gen-time;
  changing these requires a regen and overlay-cache rebuild).

## Controls

| PSX button | Keyboard |
|---|---|
| D-Pad Up / Down / Left / Right | Arrow keys |
| Cross | X |
| Square | Z |
| Circle | S |
| Triangle | A |
| L1 / R1 | Q / W |
| L2 / R2 | E / R |
| Start | Enter |
| Select | Right Shift |
| Turbo | Tab (hold) |
| Fullscreen | F11 / Alt+Enter / Cmd+F |

A game controller (Xbox, PlayStation, or any SDL-recognized pad) is supported on
all platforms via SDL when connected. The left analog stick gives variable run
speed and the D-pad works at the same time — no mode toggle.

| PSX button | Xbox controller |
|---|---|
| D-Pad Up / Down / Left / Right | D-pad or left stick |
| Cross | A |
| Circle | B |
| Square | X |
| Triangle | Y |
| L1 / R1 | LB / RB |
| L2 / R2 | LT / RT |
| Start | Menu |
| Select | View / Back |

Release builds include `input.ini` next to `TombaRecomp.exe`. Edit it to change
controller device index, deadzone, or button mapping; the analog deadzone is
also adjustable in the launcher (Settings → Controller).

## Memory Cards

Runtime memory-card files are local artifacts and must not be committed. The
runtime uses raw PS1 memory-card images compatible with DuckStation,
PCSX-Redux, Mednafen, ePSXe, and similar emulators. Cards are stored in the
`saves` directory and managed in the launcher's Player/memory-card cards.

## Help make your game faster — just by playing

**Why isn't the game already at full speed everywhere?** Most of Tomba's
code is converted ("recompiled") into a fast native program ahead of time.
But PlayStation games don't keep all of their code in memory at once — they
stream extra chunks of code off the disc as you reach new areas (these
chunks are called *overlays*). We can't convert a chunk we've never seen,
and the only way to see it is for someone to actually visit that area.
Until then, that area's code runs in a slower compatibility mode.

**Releases ship a head start.** The `cache` folder next to the executable
contains pre-converted native code for every area players have contributed
so far. Those areas run at full speed from the first moment you arrive, and
that work is now **reused across launches** — spots that hitched the first
time run smoothly afterward.

**It grows on its own, just by playing.** While you play, TombaRecomp
quietly notices which areas are still running in the slow mode and records
them into a file next to the executable called `overlay_captures.json`.
Your own cache is built from it automatically, so areas you visit get
faster for you without doing anything.

**Please do not post `overlay_captures.json` publicly.** The file contains
verbatim snapshots of the game's code read from your disc, which is
copyrighted material — keep it on your own machine, alongside your disc
image. A metadata-only contribution format (addresses and checksums, no
game code) is planned so discoveries can be shared safely in the future.

## Development Rules

- Use the real recompiled BIOS and real hardware simulation in PSXRecomp.
- No HLE BIOS shims, no stubs, no fake events, no hand-edited generated files.
- Framework changes go in `mstan/psxrecomp`, not here.
- Game binaries, generated code, memory cards, Ghidra databases, and build
  outputs stay local.
- See `CLAUDE.md` for project-specific rules.

## License

PolyForm Noncommercial 1.0.0. See `LICENSE`.

Tomba! is copyright Whoopee Camp / Sony Computer Entertainment. This
repository contains none of Tomba's original binaries or assets. Release
packages contain no game assets, no disc data, and no BIOS image — those
are always read from files you supply. The release executable and the
bundled `cache` folder do contain statically recompiled (machine-translated)
builds of the game's code, the same distribution model used by other static
recompilation projects such as N64: Recompiled.

---

<p align="center">
  <sub><b>R.A.I.D. — Retro AI Development</b> · a Discord for AI-assisted retro reverse-engineering, decomp &amp; recomp</sub>
</p>

<p align="center">
  <a href="https://discord.gg/Ad9BwSzctP"><img src=".github/raid-discord.png" alt="Join the Retro AI Development (R.A.I.D.) Discord" width="200"></a>
</p>
