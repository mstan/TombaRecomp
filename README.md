# TombaRecomp

Tomba! (USA, SCUS-94236) running on
[PSXRecomp](https://github.com/mstan/psxrecomp)

[![PSXRecomp demo](https://img.youtube.com/vi/CID9oVhgCyY/maxresdefault.jpg)](https://www.youtube.com/watch?v=CID9oVhgCyY)

## What This Is

This repository contains the game-specific configuration, seeds, tools, and
build glue for running Tomba on the PSXRecomp framework.

It does not contain the Tomba disc image, the PS1 BIOS, generated game code, or
any decompiled Tomba C. Those are generated locally from your own legally
obtained assets.

Important files:

- `game.toml`: Tomba runtime/recompiler configuration.
- `seeds/`: Ghidra-derived function starts and game-specific seed data.
- `tools/regen.ps1`: regenerates the Tomba recompiled C output.
- `psxrecomp-v4.pin`: framework commit this project is known against.
- `ISSUES.md`: game-specific issue log.

## Status

Current milestone as of 2026-05-18:

| Area | State |
|---|---|
| PS1 BIOS boot | Works |
| Disc-detected / license screen | Works |
| Whoopee Camp FMV | Works |
| Intro FMV | Works and is skippable |
| Title menu | Works |
| OPTIONS | Works |
| NEW GAME | Works |
| Save prompt / memory-card save | Works |
| LOAD GAME / memory-card load | Works |
| Gameplay | First area is believed playable |

Known follow-up work:

- No currently observed visual or progression blockers in the first area.
- BIOS logo, title/menu text seams, dialog/pause panel seams, terrain shading,
  and shaded textured branch rendering are fixed on `codex/visual-fixes`.
- Xbox-style controllers are supported through SDL/XInput and configurable via
  `input.ini`.
- Some audio/SPU behavior is partial.
- The title menu intentionally returns to the attract/demo flow after idling.
- The historical Windows "Not Responding" hang is mitigated but should remain
  under observation during longer in-game sessions.

## Setup

### Release Package

1. Download `TombaRecomp-v*-windows-x64.zip` from Releases.
2. Extract it and run `TombaRecomp.exe`.
3. Select your legally obtained `SCPH1001.BIN` BIOS when prompted.
4. Select your legally obtained Tomba! (USA, SCUS-94236) disc image when
   prompted.

Accepted disc formats are `.cue` + `.bin`, direct `.bin`, and `.iso`. The
launcher validates the ISO9660 header and expected `SCUS_942.36` game ID when
possible. If the header is missing or the ID does not match, it warns and tries
to run the image anyway.

The selected paths are saved next to the executable as `bios.cfg` and
`disc.cfg`. Delete those files to pick different files.

### Building From Source

Builds on **Windows (MSVC/MinGW)**, **macOS (Apple Silicon & Intel)**, and **Linux**.

Requirements:

- A C/C++ toolchain (MSVC/MinGW, Apple Clang, or Clang/GCC) and CMake 3.20+.
- Tomba! (USA, SCUS-94236) disc image (`.cue` + `.bin`, `.bin`, or `.iso`). Not included.
- Sony SCPH1001 BIOS ROM (`SCPH1001.BIN`). Not included.
- SDL2: bundled on Windows (MSYS2 `mingw-w64-x86_64` toolchain); `brew install sdl2 pkg-config ninja` on macOS; `libsdl2-dev` + `ninja` on Linux.
- The `psxrecomp` framework cloned in as a sibling subdir `psxrecomp-v4/` at the pinned SHA (gitignored from this repo), plus a recompiled BIOS in `psxrecomp-v4/generated/` (see the framework README).

Example local layout:

```sh
TombaRecomp/psxrecomp-v4/            # framework, at psxrecomp-v4.pin SHA
TombaRecomp/psxrecomp-v4/bios/SCPH1001.BIN
TombaRecomp/tomba/tomba.cue
TombaRecomp/tomba/tomba.bin
```

The recompiler needs the game's PS-X EXE extracted from the disc. A
cross-platform helper is included:

```sh
python3 tools/extract_psx_exe.py tomba/tomba.bin SCUS_942.36 tomba/SCUS_942.36
```

Generate the recompiled C, then build and run:

```sh
# Regenerate generated/SCUS_942.36_{full,dispatch}.c from the disc/EXE
#   Windows:       pwsh tools/regen.ps1
#   macOS / Linux: ../psxrecomp-v4/recompiler/build/psxrecomp-game --config game.toml

# Windows (MSYS2/MinGW)
cmake -S . -B build -G "Unix Makefiles" && cmake --build build -j16 && ./build/psx-runtime.exe

# macOS / Linux (Ninja)
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && ninja -C build psx-runtime
./build/psx-runtime --game game.toml --disc tomba/tomba.cue
```

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

A game controller (Xbox, PlayStation, or any SDL-recognized pad) is supported on all platforms via SDL when connected:

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

Release builds include `input.ini` next to `TombaRecomp.exe`. Edit that file
to change controller device index, deadzone, or button mapping.

## Memory Cards

Runtime memory-card files are local artifacts and must not be committed. The
current runtime uses raw PS1 memory-card images compatible with DuckStation,
PCSX-Redux, Mednafen, ePSXe, and similar emulators.

## Development Rules

- Use the real recompiled BIOS and real hardware simulation in PSXRecomp v4.
- No HLE BIOS shims, no stubs, no fake events, no hand-edited generated files.
- Framework changes go in `mstan/psxrecomp`, not here.
- Game binaries, generated code, memory cards, Ghidra databases, and build
  outputs stay local.
- See `CLAUDE.md` for project-specific rules.

## License

PolyForm Noncommercial 1.0.0. See `LICENSE`.

Tomba! is copyright Whoopee Camp / Sony Computer Entertainment. This
repository contains none of Tomba's copyrighted content.
